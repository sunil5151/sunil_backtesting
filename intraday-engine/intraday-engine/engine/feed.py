"""Live price feed, NIFTY 5m price bars, stale-tick watchdog and multiquotes fallback.

Architecture section 7 rule: the WebSocket tick callback (T1) never calls the network and never
writes to disk. It only updates in-memory prices and the current NIFTY 5m candle.
"""
from datetime import datetime, timedelta
import threading
import time

import pandas as pd

from core.data_router import fetch_backtest_data

from engine.oa import IST, explain


def _floor_5m(dt):
    return dt.replace(minute=(dt.minute // 5) * 5, second=0, microsecond=0)


class Feed:
    def __init__(self, cfg, link, log):
        self.cfg = cfg
        self.link = link
        self.log = log
        self._lock = threading.RLock()

        self._prices = {}          # symbol -> float ltp
        self._instruments = []     # [{"exchange": ..., "symbol": ...}, ...]
        self._nifty_bars = pd.DataFrame(columns=["open", "high", "low", "close"])
        self._nifty_pdc = None

        self.active = False
        self.stream_ok = False
        self.stream_err = ""
        self.last_tick_at = None
        self.last_ws_tick_at = None
        self.last_poll_at = 0.0
        self.polling_fallback = False

    def start(self, kept_symbols):
        """Warm up NIFTY 5m bars + previous close, seed quotes, and start LTP stream."""
        now = datetime.now(IST)
        today_dt = now.date()
        today = today_dt.isoformat()
        start_5m = (today_dt - timedelta(days=self.cfg.warmup_days)).isoformat()
        start_d = (today_dt - timedelta(days=10)).isoformat()

        # 1. NIFTY previous day close
        try:
            df_nd = fetch_backtest_data(
                self.link, self.cfg.index_symbol, self.cfg.index_exchange, "D", start_d, today, source="api"
            )
            if df_nd is not None and len(df_nd) > 0:
                prev_d = df_nd[df_nd.index.date < today_dt]
                if len(prev_d) > 0:
                    self._nifty_pdc = float(prev_d["close"].iloc[-1])
        except Exception:
            self.log.exception("NIFTY daily warm-up failed")

        # 2. NIFTY 5m bars (prior sessions + today so far)
        try:
            df_n5 = fetch_backtest_data(
                self.link, self.cfg.index_symbol, self.cfg.index_exchange, "5m", start_5m, today, source="api"
            )
            if df_n5 is not None and len(df_n5) > 0:
                bars = df_n5[["open", "high", "low", "close"]].copy()
                if bars.index.tz is None:
                    bars.index = bars.index.tz_localize(IST)
                else:
                    bars.index = bars.index.tz_convert(IST)
                with self._lock:
                    self._nifty_bars = bars
        except Exception:
            self.log.exception("NIFTY 5m warm-up failed")

        # 3. Build instrument list and seed initial prices via multiquotes
        instruments = [{"exchange": self.cfg.index_exchange, "symbol": self.cfg.index_symbol}]
        instruments.extend({"exchange": self.cfg.exchange, "symbol": s} for s in sorted(kept_symbols))
        self._instruments = instruments
        self._seed_multiquotes(instruments)

        # 4. Start WebSocket stream
        ok, err = self.link.start_stream(instruments, self._on_tick)
        with self._lock:
            self.active = True
            self.stream_ok = ok
            self.stream_err = err
            self.polling_fallback = not ok
        return ok, err

    def stop(self):
        with self._lock:
            self.active = False
            self.stream_ok = False
            self.polling_fallback = False
        self.link.stop_stream()

    def _seed_multiquotes(self, instruments):
        # Batch in chunks of 100 just in case
        for i in range(0, len(instruments), 100):
            batch = instruments[i:i + 100]
            resp = self.link.multiquotes(symbols=batch)
            if explain(resp)[0] != "ok":
                continue
            now_ts = time.time()
            now_dt = datetime.now(IST)
            with self._lock:
                for row in resp.get("results") or []:
                    sym = row.get("symbol")
                    ltp = (row.get("data") or {}).get("ltp")
                    if sym and ltp:
                        val = float(ltp)
                        if val > 0:
                            self._prices[sym] = val
                            if sym == self.cfg.index_symbol:
                                self._update_nifty_bar_locked(val, now_dt)
                self.last_tick_at = self.last_tick_at or now_ts
                self.last_poll_at = now_ts

    # --- T1 tick callback (no network, no disk!) ------------------------------
    def _on_tick(self, msg):
        try:
            sym = msg.get("symbol")
            ltp = (msg.get("data") or {}).get("ltp")
            if not sym or ltp is None:
                return
            val = float(ltp)
            if val <= 0:
                return
            now_ts = time.time()
            now_dt = datetime.fromtimestamp(now_ts, IST)
            with self._lock:
                self._prices[sym] = val
                self.last_tick_at = now_ts
                self.last_ws_tick_at = now_ts
                self.stream_ok = True
                self.stream_err = ""
                self.polling_fallback = False
                if sym == self.cfg.index_symbol:
                    self._update_nifty_bar_locked(val, now_dt)
        except Exception:
            pass

    def _update_nifty_bar_locked(self, ltp, dt):
        bar_ts = _floor_5m(dt)
        if bar_ts in self._nifty_bars.index:
            self._nifty_bars.at[bar_ts, "high"] = max(float(self._nifty_bars.at[bar_ts, "high"]), ltp)
            self._nifty_bars.at[bar_ts, "low"] = min(float(self._nifty_bars.at[bar_ts, "low"]), ltp)
            self._nifty_bars.at[bar_ts, "close"] = ltp
        else:
            row = pd.DataFrame(
                {"open": [ltp], "high": [ltp], "low": [ltp], "close": [ltp]},
                index=pd.DatetimeIndex([bar_ts]),
            )
            if len(self._nifty_bars) == 0:
                self._nifty_bars = row
            else:
                self._nifty_bars = pd.concat([self._nifty_bars, row]).sort_index()

    # --- watchdog & snapshots ------------------------------------------------
    def check_stale_and_poll(self, now_dt):
        """Called by control/session loop. Falls back to multiquotes if stream is silent."""
        if not self.active or not self._instruments:
            return False
        now_ts = time.time()
        ws_age = None if self.last_ws_tick_at is None else (now_ts - self.last_ws_tick_at)
        stale = (ws_age is None and now_ts - self.last_poll_at > self.cfg.stale_seconds) or (
            ws_age is not None and ws_age > self.cfg.stale_seconds
        )
        if stale:
            with self._lock:
                self.polling_fallback = True
            if now_ts - self.last_poll_at >= self.cfg.poll_interval_seconds:
                self._seed_multiquotes(self._instruments)
        return stale

    def tick_age_seconds(self):
        with self._lock:
            if self.last_tick_at is None:
                return None
            return max(0, int(time.time() - self.last_tick_at))

    def snapshot_prices(self):
        with self._lock:
            return dict(self._prices)

    def nifty_pct_change(self):
        with self._lock:
            ltp = self._prices.get(self.cfg.index_symbol)
            pdc = self._nifty_pdc
        if ltp and pdc and pdc > 0:
            return round((ltp - pdc) / pdc * 100.0, 2)
        return None

    def closed_nifty_bars(self, boundary_dt):
        """Return copy of NIFTY 5m bars strictly before boundary_dt."""
        with self._lock:
            if len(self._nifty_bars) == 0:
                return self._nifty_bars.copy()
            return self._nifty_bars[self._nifty_bars.index < boundary_dt].copy()
