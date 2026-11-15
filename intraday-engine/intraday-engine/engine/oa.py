"""OpenAlgo link. The ONLY module that talks to OpenAlgo (BUILD.md rule 5).

- OALink: wrapper around the SDK client. Timeout on every call, throttle, one retry for reads,
  latency per call, errors turned into short messages. It also runs the heartbeat.
  Its methods have the same shape as the SDK's, so vendor functions accept it as `client`.
- run_connection_check: the 11 checks of architecture section 4.

Paper only (BUILD.md rule 1): this module has no call that changes Analyze mode, and every
order path added in Phase 4 must ask OALink.orders_allowed() first.
"""
from collections import deque
from datetime import datetime, timedelta
import json
import threading
import time
from zoneinfo import ZoneInfo

from openalgo import api as _SdkClient

from core.data_router import fetch_backtest_data
from core.preflight import PreflightError, run_preflight

from engine import sysmem
from engine.config import reload_api_key

IST = ZoneInfo("Asia/Kolkata")


# ---------------------------------------------------------------------------
# Error text
# ---------------------------------------------------------------------------

def _short(msg, limit=160):
    msg = str(msg or "").strip()
    brace = msg.find("{")
    if msg.startswith("HTTP ") and brace > 0:          # 'HTTP 403: {"message": "..."}'
        try:
            inner = json.loads(msg[brace:]).get("message")
            if inner:
                msg = inner if isinstance(inner, str) else json.dumps(inner)
        except ValueError:
            pass
    return msg if len(msg) <= limit else msg[: limit - 1] + "…"


def explain(resp):
    """Turn an SDK response into (kind, short message).
    kind: ok | unreachable | timeout | bad_key | error"""
    if not isinstance(resp, dict):                      # history() returns a DataFrame on success
        return "ok", ""
    if resp.get("status") == "success":
        return "ok", ""
    etype = resp.get("error_type")
    msg = str(resp.get("message", ""))
    if etype == "connection_error":
        return "unreachable", "OpenAlgo is not answering."
    if etype == "timeout_error":
        return "timeout", "OpenAlgo took too long to answer."
    if resp.get("code") == 403 or "apikey" in msg.lower():
        return "bad_key", "OpenAlgo did not accept the API key."
    return "error", _short(msg) or "OpenAlgo returned an error."


def _is_true(v):
    """Strict: only a real true counts. Anything unclear is treated as not true (fail closed)."""
    if isinstance(v, str):
        return v.strip().lower() == "true"
    return v is True or v == 1


# ---------------------------------------------------------------------------
# Wrapper
# ---------------------------------------------------------------------------

class OALink:
    def __init__(self, cfg, log):
        self.cfg = cfg
        self.log = log
        self._throttle = threading.Lock()
        self._next_call = 0.0
        self._min_gap = 1.0 / cfg.max_calls_per_second
        self._latencies = deque(maxlen=20)
        self.latency_ms = None
        self.last_error = {}            # call name -> last short error message
        self.on_heartbeat = None        # set by the control layer
        self._stream_lock = threading.Lock()
        self._stream_active = False
        self._stream_instruments = []
        self._client = None
        self.rebuild()

        # heartbeat state (None = not known yet)
        self.reachable = None
        self.key_ok = None
        self.analyze_on = None
        self.hb_ok_at = None            # time of the last good heartbeat
        self.hb_message = ""

    def rebuild(self):
        """(Re)create the SDK client, for example after the key in .env changed."""
        old = self._client
        self._client = _SdkClient(
            api_key=self.cfg.api_key or "missing",
            host=self.cfg.host,
            ws_url=self.cfg.ws_url,
            timeout=self.cfg.timeout_seconds,
        )
        if old is not None:
            try:
                old.close()
            except Exception:
                pass

    # --- one door for every REST call -----------------------------------------
    def _wait_turn(self):
        with self._throttle:
            now = time.monotonic()
            wait = self._next_call - now
            if wait > 0:
                time.sleep(wait)
            self._next_call = max(now, self._next_call) + self._min_gap

    def _call(self, name, retry=True, **kwargs):
        attempts = 2 if retry else 1
        resp, msg = None, ""
        for attempt in range(attempts):
            self._wait_turn()
            t0 = time.perf_counter()
            try:
                resp = getattr(self._client, name)(**kwargs)
            except Exception as e:                       # the SDK should not raise, but never trust it
                resp = {"status": "error", "error_type": "unknown_error",
                        "message": f"{type(e).__name__}: {e}"}
            ms = (time.perf_counter() - t0) * 1000.0
            self.latency_ms = ms
            self._latencies.append(ms)

            kind, msg = explain(resp)
            if kind == "ok":
                self.last_error.pop(name, None)
                return resp
            self.last_error[name] = msg
            server_side = kind == "error" and (resp.get("code") or 500) >= 500
            if not (kind == "timeout" or server_side):
                break                                    # bad key, bad symbol, not reachable: a retry will not help
            if attempt + 1 < attempts:
                time.sleep(0.5)
        self.log.warning("OpenAlgo call %s failed: %s", name, msg)
        return resp

    @property
    def latency_avg_ms(self):
        return sum(self._latencies) / len(self._latencies) if self._latencies else None

    # --- reads (same shape as the SDK) -----------------------------------------
    def analyzerstatus(self):
        return self._call("analyzerstatus")

    def funds(self):
        return self._call("funds")

    def quotes(self, *, symbol, exchange):
        return self._call("quotes", symbol=symbol, exchange=exchange)

    def multiquotes(self, *, symbols):
        return self._call("multiquotes", symbols=symbols)

    def search(self, *, query, exchange):
        return self._call("search", query=query, exchange=exchange)

    def history(self, *, symbol, exchange, interval, start_date, end_date, source="api"):
        return self._call("history", symbol=symbol, exchange=exchange, interval=interval,
                          start_date=start_date, end_date=end_date, source=source)

    def symbol(self, *, symbol, exchange):
        return self._call("symbol", symbol=symbol, exchange=exchange)

    def timings(self, date=None):
        return self._call("timings", date=date)

    def holidays(self, year=None):
        return self._call("holidays", year=year)

    def positionbook(self):
        return self._call("positionbook")

    def orderbook(self):
        return self._call("orderbook")

    def tradebook(self):
        return self._call("tradebook")

    def orderstatus(self, *, order_id, strategy):
        return self._call("orderstatus", order_id=order_id, strategy=strategy)

    def placeorder(self, *, strategy, symbol, action, exchange, price_type="MARKET", product="MIS", quantity=1):
        if not self.orders_allowed():
            return {"status": "error", "message": "Analyze mode is not confirmed ON."}
        return self._call(
            "placeorder", retry=False,
            strategy=strategy, symbol=symbol, action=action, exchange=exchange,
            price_type=price_type, product=product, quantity=int(quantity),
        )

    def closeposition(self, *, strategy):
        if not self.orders_allowed():
            return {"status": "error", "message": "Analyze mode is not confirmed ON."}
        return self._call("closeposition", retry=False, strategy=strategy)

    # --- heartbeat -------------------------------------------------------------
    def heartbeat(self):
        """One Analyze-mode status call. Proves OpenAlgo is alive and re-checks the mode."""
        if not self.cfg.has_key or self.key_ok is False:
            if reload_api_key(self.cfg):                 # a key pasted into .env works without a restart
                self.rebuild()
        resp = self._call("analyzerstatus", retry=False)
        kind, msg = explain(resp)
        if kind == "ok":
            self.reachable, self.key_ok = True, True
            self.analyze_on = _is_true((resp.get("data") or {}).get("analyze_mode"))
            self.hb_ok_at = time.time()
        elif kind == "bad_key":
            self.reachable, self.key_ok, self.analyze_on = True, False, None
        elif kind in ("unreachable", "timeout"):
            self.reachable, self.analyze_on = False, None
        else:
            self.reachable, self.analyze_on = True, None
        self.hb_message = msg
        if self.on_heartbeat:
            try:
                self.on_heartbeat(kind)
            except Exception:
                self.log.exception("heartbeat hook failed")
        return kind

    def orders_allowed(self):
        """True only when a recent heartbeat saw Analyze mode ON. Unknown counts as OFF."""
        return (self.analyze_on is True and self.hb_ok_at is not None
                and time.time() - self.hb_ok_at < 3 * self.cfg.heartbeat_seconds)

    # --- stream ----------------------------------------------------------------
    def start_stream(self, instruments, on_tick):
        """Connect and subscribe to LTP ticks for live session feed."""
        with self._stream_lock:
            self._stop_stream_locked()
            try:
                if not self._client.connect():
                    return False, "The price stream refused the connection."
                self._client.subscribe_ltp(instruments, on_data_received=on_tick)
                self._stream_active = True
                self._stream_instruments = list(instruments)
                return True, ""
            except Exception as e:
                self._stream_active = False
                self._stream_instruments = []
                return False, f"Stream error: {type(e).__name__}."

    def stop_stream(self):
        with self._stream_lock:
            self._stop_stream_locked()

    def _stop_stream_locked(self):
        if self._stream_active:
            try:
                if self._stream_instruments:
                    self._client.unsubscribe_ltp(self._stream_instruments)
                self._client.disconnect()
            except Exception:
                pass
            self._stream_active = False
            self._stream_instruments = []

    def stream_probe(self, instruments, wait_s):
        """Connect, subscribe to last price, wait for one tick per instrument, disconnect.
        Returns ({(exchange, symbol): ltp}, error text)."""
        if self._stream_active:
            return {(i["exchange"], i["symbol"]): 1.0 for i in instruments}, ""
        got = {}

        def on_tick(msg):
            try:
                got[(msg.get("exchange"), msg.get("symbol"))] = (msg.get("data") or {}).get("ltp")
            except Exception:
                pass

        want = {(i["exchange"], i["symbol"]) for i in instruments}
        client = self._client
        with self._stream_lock:
            try:
                if not client.connect():
                    return None, "The price stream refused the connection."
                client.subscribe_ltp(instruments, on_data_received=on_tick)
                end = time.monotonic() + wait_s
                while time.monotonic() < end and not want.issubset(got):
                    time.sleep(0.2)
                return dict(got), ""
            except Exception as e:
                return None, f"Stream error: {type(e).__name__}."
            finally:
                try:
                    client.unsubscribe_ltp(instruments)
                    client.disconnect()
                except Exception:
                    pass

    def close(self):
        try:
            self._client.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Connection check (architecture section 4). The only test in this project.
# ---------------------------------------------------------------------------

CHECKS = [  # (number, name, BLOCK?)
    (1, "OpenAlgo is reachable", True),
    (2, "API key is accepted", True),
    (3, "Broker session is alive", True),
    (4, "Analyze mode is ON", True),
    (5, "Sandbox funds match the configured capital", False),
    (6, "Quotes for the index and one stock", False),
    (7, "5-minute history for one stock", False),
    (8, "Price stream delivers ticks", False),
    (9, "Every universe symbol resolves", False),
    (10, "Market is open today", False),
    (11, "Free RAM", False),
]


def _hhmm_from_ms(ms):
    return datetime.fromtimestamp(float(ms) / 1000.0, IST).strftime("%H:%M")


def run_connection_check(link, cfg, universe, resolved, on_update):
    """Run the 11 checks in order. Calls on_update(items) as results come in.

    resolved: a set of symbols already known to resolve today (so a second run is quick).
    Returns (items, market) where market = {"day", "open": True/False/None, "note"}.
    """
    items = [{"n": n, "name": name, "block": block, "status": "pending", "text": "", "fix": ""}
             for n, name, block in CHECKS]
    now = datetime.now(IST)
    today = now.date().isoformat()
    market = {"day": today, "open": None, "note": ""}

    def put(n, status, text, fix=""):
        items[n - 1].update(status=status, text=text, fix=fix)
        on_update(items)

    def running(n, text="Checking…"):
        items[n - 1].update(status="running", text=text, fix="")
        on_update(items)

    def not_run(numbers, because):
        for n in numbers:
            if items[n - 1]["status"] in ("pending", "running"):
                put(n, "amber", "Not run.", f"Fix check {because} first, then run the check again.")

    def guarded(n, fn):
        try:
            fn()
        except Exception as e:
            link.log.exception("connection check %s crashed", n)
            put(n, "red" if items[n - 1]["block"] else "amber",
                f"This check could not run ({type(e).__name__}).",
                "Run the check again. If it repeats, look at logs/engine.log.")

    # ---- 11: free RAM (local, so it runs even when OpenAlgo is down) ----
    def check_ram():
        free, eng = sysmem.free_ram_mb(), sysmem.engine_mb()
        if free is None:
            put(11, "amber", "Free RAM could not be read on this machine.", "Watch the Task Manager instead.")
        elif free < cfg.warn_free_mb:
            put(11, "amber", f"Only {free} MB free. The engine uses {eng} MB.",
                "Close the code editor, the AI agent and extra browser tabs.")
        else:
            put(11, "green", f"{free} MB free. The engine uses {eng} MB.")
    guarded(11, check_ram)

    # ---- 1, 2, 4: one status call answers all three ----
    running(1)
    if reload_api_key(cfg):
        link.rebuild()
    kind = link.heartbeat()
    if kind in ("unreachable", "timeout"):
        put(1, "red", f"No answer from {cfg.host}.",
            "Start OpenAlgo Desktop, wait until it is open, then run the check again.")
        not_run(range(2, 11), 1)
        return items, market
    put(1, "green", f"Answered at {cfg.host} in {link.latency_ms:.0f} ms.")

    if not cfg.has_key:
        put(2, "red", "There is no API key in the .env file.",
            "Open .env in the engine folder, paste the API key from OpenAlgo after OPENALGO_API_KEY=, "
            "save, then run the check again.")
        not_run(range(3, 11), 2)
        return items, market
    if kind == "bad_key":
        put(2, "red", "OpenAlgo rejected the API key.",
            "Copy the key from the API Key page in OpenAlgo, paste it into .env after "
            "OPENALGO_API_KEY=, save, then run the check again.")
        not_run(range(3, 11), 2)
        return items, market
    if kind != "ok":
        put(2, "red", f"OpenAlgo answered with an error: {link.hb_message}",
            "Restart OpenAlgo Desktop, then run the check again.")
        not_run(range(3, 11), 2)
        return items, market
    put(2, "green", "Key accepted.")

    if link.analyze_on:
        put(4, "green", "Analyze mode is ON. Orders go to the sandbox only.")
    else:
        put(4, "red", "Analyze mode is OFF. Orders would go to the real broker.",
            "Switch OpenAlgo to Analyze mode with its own toggle. The engine never changes this switch.")

    # ---- 3: broker session (vendor preflight: funds call + one symbol lookup) ----
    cash = [None]

    def check_broker():
        running(3)
        try:
            res = run_preflight(link, symbol=cfg.check_stock, exchange=cfg.exchange,
                                min_cash=0, fail_on_holiday=False)
            cash[0] = res.get("available_cash")
            put(3, "green", "The funds call succeeded.")
        except PreflightError as e:
            put(3, "red", "The funds call failed: " + (link.last_error.get("funds") or _short(e)),
                "Log in to Groww inside OpenAlgo, then run the check again.")
    guarded(3, check_broker)
    broker_ok = items[2]["status"] == "green"

    # ---- 10: market open today (run early: check 8 needs the answer) ----
    def check_market():
        running(10)
        resp = link.timings(date=today)
        kind_t, msg_t = explain(resp)
        if kind_t != "ok":
            put(10, "amber", f"Market timings could not be read: {msg_t}",
                "Nothing to do. The engine goes by the weekday and the clock instead.")
            return
        row = next((r for r in (resp.get("data") or []) if r.get("exchange") == cfg.exchange), None)
        if row:
            market["open"] = True
            market["note"] = f"{_hhmm_from_ms(row['start_time'])} to {_hhmm_from_ms(row['end_time'])}"
            put(10, "green", f"{cfg.exchange} is open today, {market['note']}.")
            return
        market["open"] = False
        reason = "weekend" if now.weekday() >= 5 else "holiday"
        if reason == "holiday" and broker_ok:
            try:                                          # vendor holiday check gives the holiday's name
                run_preflight(link, exchange=cfg.exchange, min_cash=0)
            except PreflightError as e:
                reason = _short(e)
        market["note"] = reason
        put(10, "amber", f"{cfg.exchange} is closed today ({reason}).",
            "Nothing to fix. START still works and shows the market-closed mode.")
    guarded(10, check_market)

    if not broker_ok:
        not_run([5, 6, 7, 8, 9], 3)
        return items, market

    # ---- 5: sandbox funds ----
    def check_funds():
        c = cash[0]
        if c is None:
            put(5, "amber", "Funds were not returned.", "Run the check again.")
            return
        diff_pct = abs(c - cfg.capital) / cfg.capital * 100.0
        text = f"Sandbox funds ₹{c:,.0f}. Capital in config.yaml ₹{cfg.capital:,.0f}."
        if diff_pct <= cfg.funds_tolerance_pct:
            put(5, "green", text)
        else:
            put(5, "amber", text + f" They differ by {diff_pct:.0f}%.",
                f"Set the sandbox capital in OpenAlgo to ₹{cfg.capital:,.0f}, "
                "or change 'capital' in config.yaml to match.")
    guarded(5, check_funds)

    # ---- 6: quotes ----
    def check_quotes():
        running(6)
        parts, bad = [], []
        for sym, exch in ((cfg.index_symbol, cfg.index_exchange), (cfg.check_stock, cfg.exchange)):
            resp = link.quotes(symbol=sym, exchange=exch)
            kind_q, msg_q = explain(resp)
            ltp = 0.0
            if kind_q == "ok":
                try:
                    ltp = float((resp.get("data") or {}).get("ltp") or 0)
                except (TypeError, ValueError):
                    ltp = 0.0
            if ltp > 0:
                parts.append(f"{sym} {ltp:,.2f}")
            else:
                bad.append(f"{sym}: {msg_q or 'no price returned'}")
        if not bad:
            put(6, "green", ", ".join(parts) + ".")
        else:
            put(6, "amber", "No quote for " + "; ".join(bad),
                "Check that Groww is logged in inside OpenAlgo and that the symbol names in "
                "config.yaml are right.")
    guarded(6, check_quotes)

    # ---- 7: 5m history (vendor fetch + normalise) ----
    def check_history():
        running(7)
        start = (now - timedelta(days=7)).date().isoformat()
        try:
            df = fetch_backtest_data(link, cfg.check_stock, cfg.exchange, "5m", start, today, source="api")
        except Exception:
            df = None                                     # the vendor function trips on an error reply
        if df is None or not hasattr(df, "columns") or len(df) == 0:
            put(7, "amber", "No 5-minute bars came back: "
                + (link.last_error.get("history") or "empty reply") ,
                "Check the Groww data connection inside OpenAlgo, then run the check again.")
            return
        has_volume = "volume" in df.columns and float(df["volume"].sum()) > 0
        last = df.index[-1]
        text = f"{len(df)} bars for {cfg.check_stock}. Last bar {last:%d %b %H:%M}."
        if has_volume:
            put(7, "green", text + " Volume is present.")
        else:
            put(7, "amber", text + " Volume is missing.",
                "Signals need volume (Phase 3). Check the Groww data connection inside OpenAlgo.")
    guarded(7, check_history)

    # ---- 8: stream ----
    def check_stream():
        in_hours = cfg.market_open <= now.time() < cfg.market_close
        trading_day = market["open"] if market["open"] is not None else now.weekday() < 5
        if not (in_hours and trading_day):
            put(8, "amber", "Skipped: the market is closed now, so no ticks are expected.",
                f"Run the check again on a trading day between {cfg.market_open:%H:%M} "
                f"and {cfg.market_close:%H:%M}.")
            return
        running(8, f"Waiting up to {cfg.stream_wait_seconds:.0f} s for ticks…")
        want = [(cfg.index_exchange, cfg.index_symbol), (cfg.exchange, cfg.check_stock)]
        got, err = link.stream_probe([{"exchange": e, "symbol": s} for e, s in want],
                                     cfg.stream_wait_seconds)
        fix = ("Check WEBSOCKET_URL in .env and that OpenAlgo's WebSocket is running. "
               "The engine can fall back to polling quotes (Phase 2).")
        if got is None:
            put(8, "amber", err, fix)
            return
        missing = [s for e, s in want if (e, s) not in got]
        if not missing:
            put(8, "green", f"Ticks arrived for {cfg.index_symbol} and {cfg.check_stock}.")
        else:
            put(8, "amber", f"No tick within {cfg.stream_wait_seconds:.0f} s for: " + ", ".join(missing) + ".", fix)
    guarded(8, check_stream)

    # ---- 9: every universe symbol ----
    def check_universe():
        total = len(universe)
        todo = [s for s in universe if s not in resolved]
        failed = []
        for i, sym in enumerate(todo):
            if i % 4 == 0:
                running(9, f"Checking symbols: {total - len(todo) + i} of {total}…")
            resp = link.symbol(symbol=sym, exchange=cfg.exchange)
            kind_s, _ = explain(resp)
            if kind_s == "ok" and resp.get("data"):
                resolved.add(sym)
            elif kind_s in ("unreachable", "timeout", "bad_key"):
                put(9, "amber", f"Stopped after {i} symbols: OpenAlgo stopped answering.",
                    "Run the check again.")
                return
            else:
                failed.append(sym)
        if not failed:
            put(9, "green", f"All {total} symbols resolve.")
        else:
            put(9, "amber", f"{len(failed)} of {total} symbols do not resolve: " + ", ".join(failed) + ".",
                "These are old or renamed symbols. Nothing to do now: the universe clean-up in "
                "Phase 2 drops or replaces them.")
    guarded(9, check_universe)

    not_run(range(1, 12), "the one above")
    return items, market
