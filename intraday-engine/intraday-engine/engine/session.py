"""Control layer and session clock (architecture section 5).

Control layer: alive while the app is open. Heartbeat, connection check, auto-start, and the
state snapshot the UI reads. Session: one trading-day run, started by START or auto-start,
ended by STOP. Phase 1 has the state machine and the clock only, no market logic.
"""
from datetime import datetime
import json
import threading
import time

from engine import sysmem
from engine.bars import (
    Context,
    compute_rr_metrics,
    evaluate_strategy_bar,
    fetch_armed_bars,
    load_strategy_plug,
)
from engine.config import parse_hhmm
from engine.dryrun import get_dryrun_options, run_dry_session
from engine.exits import evaluate_position_exit
from engine.feed import Feed
from engine.levels import kept_by_symbol, load_or_build_levels, sector_eligibility
from engine.oa import IST, run_connection_check
from engine.orders import OrderManager
from engine.portfolio import check_entry_gates, compute_position_mtm, compute_position_size, summarize_today
from engine.regime import compute_breadth, evaluate_regime
from engine.s3_archive import (
    MIN_ENTRY_CONDITION_TEXT,
    build_all_stocks_rows,
    build_scan_document,
    build_signal_checks,
    compute_check_breakdown,
    fetch_activity_s3,
    fetch_s3_scan,
    finalize_signal_checks,
    list_s3_scans,
    make_scan_names,
    make_signal_ids,
    save_activity_s3,
    save_scan_doc,
    strategy_meta_dict,
    summarize_signal_checks,
)
from engine.scanner import scan_candidates
from engine.sector import rank_sectors
from engine.socket_manager import (
    apply_plug_strategy,
    apply_unplug_strategy,
    delete_strategy_file,
    get_socket_reference,
    qualify_strategy_file,
    upload_strategy_file,
    verify_with_openrouter,
)

STATES = ("idle", "warming up", "live", "view only", "market closed", "halted")


def clock_state(now, cfg, trading_day):
    """Pure: which step of the day a running session is in."""
    if not trading_day:
        return "market closed"
    t = now.time()
    if t < cfg.market_open:
        return "warming up"
    if t < cfg.no_new_entries_after:
        return "live"
    if t < cfg.square_off:
        return "view only"
    return "market closed"


def state_line(state, cfg):
    return {
        "idle": "No session is running. Press START.",
        "warming up": f"Session is on. The market opens at {cfg.market_open:%H:%M}.",
        "live": f"Market is open. New entries are allowed until {cfg.no_new_entries_after:%H:%M}.",
        "view only": f"After {cfg.no_new_entries_after:%H:%M}: view only, no new entries. "
                     f"Square-off is at {cfg.square_off:%H:%M}.",
        "market closed": "Market is closed. Live panels are idle.",
        "halted": "Session is halted. No order is sent.",
    }[state]


class Controller:
    def __init__(self, cfg, store, link, universe, phases, log):
        self.cfg, self.store, self.link, self.universe, self.phases, self.log = \
            cfg, store, link, universe, phases, log
        self._lock = threading.RLock()
        self._stop = threading.Event()

        self.session = None                 # {"day", "started_at", "source", "halted"}
        self.busy = ""                      # text while a start or a check is running
        self.refusal = None                 # {"text", "fix"} when START was refused
        self.check = store.get_setting("last_check") or {"running": False, "ran_at": None, "items": []}
        self.check["running"] = False
        self.market = {"day": None, "open": None, "note": ""}
        self.auto_on = bool(store.get_setting("auto_on", False))
        self.auto_time = store.get_setting("auto_time", cfg.auto_start_time)

        self._resolved, self._resolved_day = set(), None
        self._prev_state = "idle"
        self._prev_hb = {"reachable": None, "key_ok": None, "analyze_on": None}
        self._prev_ram = "ok"
        self._last_tick = datetime.now(IST)
        self._free_mb, self._engine_mb = sysmem.free_ram_mb(), sysmem.engine_mb()
        self._ticks = 0
        self._snapshot = b"{}"
        link.on_heartbeat = self._after_heartbeat

        # Phase 2: levels, feed, and market view (survives STOP / evening view)
        today = datetime.now(IST).date().isoformat()
        self.levels_rows = store.get_daily_levels(today)
        if self.levels_rows:
            self._resolved = {r["symbol"] for r in self.levels_rows if r["drop_reason"] != "Symbol not found"}
            self._resolved_day = today
        self.feed = Feed(cfg, link, log)
        self._regime_state = None
        self._last_bar_key = None
        latest = store.get_latest_decision()
        if latest and latest["day"] == today and latest.get("regime"):
            r = latest["regime"]
            self._regime_state = {
                "active": r.get("active", "CHOPPY"),
                "pending_raw": r.get("pending_raw"),
                "pending_count": r.get("pending_count", 0),
            }
        self.market_view = {
            "day": latest["day"], "bar_time": latest["bar_time"],
            "nifty_pct": (latest.get("regime") or {}).get("nifty_pct"),
            "regime": latest["regime"], "sectors": latest["sectors"], "scanner": latest["scanner"],
        } if latest else {
            "day": None, "bar_time": None, "nifty_pct": None,
            "regime": None, "sectors": [], "scanner": {"side": None, "shortlist": [], "armed": []},
        }

        # Phase 3: strategy plug, qualification, signals and dry run
        self.strategy_mod, self.strategy = load_strategy_plug(cfg)
        self.last_qualification = qualify_strategy_file(cfg, cfg.strategy_file) if cfg.strategy_file else None
        self.signals = store.get_signals()
        self._signaled_today = {
            s["symbol"] for s in self.signals
            if s["day"] == today and s["mode"] == "live" and s["status"] == "would trade"
        }
        self._signaled_day = today
        self.dryrun_summary = None
        self._dryrun_req = {}
        self._view_source = "live"

        # Phase 4: orders, positions, reconcile
        self.orders = OrderManager(cfg, link, store, log, on_change=self._sync_positions)
        self.open_positions = store.get_open_paper_trades(today)
        self.closed_trades = store.get_closed_paper_trades(today)
        self._last_reconcile_ts = 0.0
        self._square_off_sent_day = None
        self._square_off_confirmed_day = None
        self.last_s3_key = ""
        self.last_s3_status = "Connected" if cfg.has_s3 else "Not configured"
        self.latest_stock_reasons = {}

    def get_s3_index(self, day=None):
        return list_s3_scans(self.cfg, day)

    def get_s3_scan(self, day, sfile):
        return fetch_s3_scan(self.cfg, day, sfile)

    def get_s3_activity(self, day=None, limit=20):
        target = day or (self.market_view.get("day") or datetime.now(IST).date().isoformat())
        return fetch_activity_s3(self.cfg, target, limit=limit, fallback_items=self.store.feed_newest_first())

    def _sync_positions(self):
        today = datetime.now(IST).date().isoformat()
        with self._lock:
            self.open_positions = self.store.get_open_paper_trades(today)
            self.closed_trades = self.store.get_closed_paper_trades(today)
            self._signaled_today = self.store.get_traded_symbols(today)

    # ------------------------------------------------------------------ threads
    def start_threads(self):
        self._refresh()
        self.orders.start()
        threading.Thread(target=self._heartbeat_loop, name="oa-heartbeat", daemon=True).start()
        threading.Thread(target=self._control_loop, name="control", daemon=True).start()
        threading.Thread(target=self._session_loop, name="session-loop", daemon=True).start()

    def shutdown(self):
        self._stop.set()
        self.orders.stop()
        self.feed.stop()

    def _heartbeat_loop(self):
        while not self._stop.is_set():
            try:
                self.link.heartbeat()
                self.store.add_health(self.link.reachable and self.link.key_ok, self.link.analyze_on,
                                      self.link.latency_ms, self._free_mb, self._engine_mb)
            except Exception:
                self.log.exception("heartbeat loop error")
            ok = self.link.reachable and self.link.key_ok
            self._stop.wait(self.cfg.heartbeat_seconds if ok else self.cfg.retry_when_down_seconds)

    def _control_loop(self):
        while not self._stop.wait(1.0):
            try:
                self._refresh()
            except Exception:
                self.log.exception("control loop error")

    def _session_loop(self):
        """T2 loop: stale-tick watchdog, tick exits, square-off, reconcile and 5m cycle."""
        while not self._stop.wait(1.0):
            try:
                now = datetime.now(IST)
                with self._lock:
                    sess = self.session
                    busy = self.busy
                    state = self._state(now)
                if not sess or busy:
                    continue
                if state == "market closed":
                    if self.feed.active:
                        self.feed.stop()
                    self._check_square_off_and_confirm(now)
                    continue
                if self.feed.active:
                    self.feed.check_stale_and_poll(now)
                self._check_exits_tick(now)
                if time.time() - self._last_reconcile_ts >= self.cfg.reconcile_interval_seconds:
                    self._run_reconcile()
                if now.time() >= self.cfg.market_open and now.minute % self.cfg.rescan_minutes == 0:
                    boundary = now.replace(second=0, microsecond=0)
                    bar_key = boundary.strftime("%Y-%m-%d %H:%M")
                    if bar_key != self._last_bar_key:
                        self._run_5m_cycle(now)
            except Exception:
                self.log.exception("session loop error")

    def _run_reconcile(self):
        self._last_reconcile_ts = time.time()
        mismatches = self.orders.reconcile()
        self._sync_positions()
        return mismatches

    def _check_exits_tick(self, now):
        with self._lock:
            open_pos = list(self.open_positions)
        if not open_pos:
            return
        prices = self.feed.snapshot_prices()
        tick_age_s = self.feed.tick_age_seconds() or 0.0
        be_at_r = float(self.cfg.strategy_params.get("breakeven_at_r", 1.0))

        for pos in open_pos:
            ltp = prices.get(pos["symbol"])
            ev = evaluate_position_exit(
                pos, ltp, now.time(), self.cfg.square_off,
                breakeven_at_r=be_at_r,
                tick_age_s=tick_age_s,
                stale_seconds=self.cfg.stale_seconds,
            )
            if ev["breakeven_triggered"]:
                self.store.update_paper_trade_stop(
                    pos["id"], ev["new_stop"], True, ev["new_watermark"]
                )
                self._sync_positions()
                self.store.add_activity(
                    f"{now:%H:%M:%S} {pos['symbol']} reached +{be_at_r:.1f}R: stop moved to entry ₹{ev['new_stop']:.2f}.",
                    "good",
                )
            elif ev["new_watermark"] is not None:
                self.store.update_paper_trade_watermark(pos["id"], ev["new_watermark"])
                self.store.state.update_watermark(pos["symbol"], self.cfg.exchange, float(pos["entry_epoch"]), ev["new_watermark"])

            if ev["exit_reason"]:
                self.orders.submit_exit(
                    pos["id"], ev["exit_reason"], ltp or pos["entry_price"],
                    tick_age_s=tick_age_s, stale_flag=ev["stale_flag"],
                )

    def _check_square_off_and_confirm(self, now):
        day = now.date().isoformat()
        with self._lock:
            open_pos = list(self.open_positions)
        if now.time() >= self.cfg.square_off and self._square_off_sent_day != day:
            self._square_off_sent_day = day
            if open_pos:
                prices = self.feed.snapshot_prices()
                tick_age_s = self.feed.tick_age_seconds() or 0.0
                for pos in open_pos:
                    self.orders.submit_exit(pos["id"], "SQUARE_OFF", prices.get(pos["symbol"]) or pos["entry_price"], tick_age_s=tick_age_s)
                self.store.add_activity(f"{now:%H:%M:%S} Square-off triggered for {len(open_pos)} open position(s).", "warn")
            else:
                self.store.add_activity(f"{now:%H:%M:%S} Square-off time reached: all positions already flat.", "info")

        if now.time() >= self.cfg.square_off_confirm_time and self._square_off_confirmed_day != day:
            self._square_off_confirmed_day = day
            if open_pos:
                self.link.closeposition(strategy=self.cfg.strategy_name)
                self._run_reconcile()
                with self._lock:
                    rem = len(self.open_positions)
                if rem == 0:
                    self.store.add_activity(f"{now:%H:%M:%S} 15:00 square-off confirmed: all positions flat.", "good")
                else:
                    self.store.add_activity(f"{now:%H:%M:%S} 15:00 square-off: {rem} position(s) still open, retrying.", "bad")
                    self._square_off_confirmed_day = None
            else:
                self.store.add_activity(f"{now:%H:%M:%S} 15:00 square-off confirmed: all positions flat.", "good")

    def _run_5m_cycle(self, now):
        """Run regime -> sector -> scanner on the latest closed 5m boundary."""
        scan_t0 = time.perf_counter()
        minute = (now.minute // self.cfg.rescan_minutes) * self.cfg.rescan_minutes
        boundary = now.replace(minute=minute, second=0, microsecond=0)
        bar_key = boundary.strftime("%Y-%m-%d %H:%M")
        bar_hhmm = boundary.strftime("%H:%M")
        day = boundary.date().isoformat()
        self._last_bar_key = bar_key

        with self._lock:
            rows = list(self.levels_rows)
        kept_map = kept_by_symbol(rows, self.cfg.min_members_per_sector)
        if not kept_map:
            return

        prices = self.feed.snapshot_prices()
        nifty_pct = self.feed.nifty_pct_change()
        nifty_bars = self.feed.closed_nifty_bars(boundary)

        adv, dec, breadth = compute_breadth(kept_map, prices)
        regime_res, self._regime_state = evaluate_regime(nifty_bars, breadth, self.cfg, self._regime_state)
        regime_res["advancers"] = adv
        regime_res["decliners"] = dec
        regime_res["nifty_pct"] = nifty_pct

        sectors = rank_sectors(kept_map, prices, nifty_pct, self.cfg)
        scanner = scan_candidates(regime_res["active"], sectors, kept_map, prices, nifty_pct, self.cfg)

        strong = [s["sector"] for s in sectors if s["mark"] == "STRONG"]
        weak = [s["sector"] for s in sectors if s["mark"] == "WEAK"]
        if regime_res["active"] == "TREND_UP":
            sec_txt = (", ".join(strong) + " strong") if strong else "no strong sectors"
        elif regime_res["active"] == "TREND_DOWN":
            sec_txt = (", ".join(weak) + " weak") if weak else "no weak sectors"
        else:
            parts = []
            if strong:
                parts.append(", ".join(strong) + " strong")
            if weak:
                parts.append(", ".join(weak) + " weak")
            sec_txt = "; ".join(parts) if parts else "no strong/weak sectors"

        armed_n = len(scanner["armed"])
        armed_txt = f" ({', '.join(scanner['armed'])})" if armed_n else ""
        summary = f"{bar_hhmm} {regime_res['active']}. {sec_txt}. {armed_n} armed{armed_txt}."

        self.store.save_decision(day, bar_hhmm, regime_res, sectors, scanner, summary)
        self.store.add_activity(summary, "info")

        sigs_sec = []
        if scanner["armed"]:
            sigs_sec = self._evaluate_armed_live(
                boundary, day, bar_hhmm, regime_res, sectors, scanner, kept_map, prices,
                scan_t0=scan_t0,
            )

        dur_ms = int((time.perf_counter() - scan_t0) * 1000)
        strat_meta = strategy_meta_dict(self.cfg, self.strategy_mod, self.strategy, qualification=self.last_qualification)
        doc, idx_entry = build_scan_document(
            self.cfg,
            day=day,
            bar_time=bar_hhmm,
            checked_at=datetime.now(IST).strftime("%H:%M:%S"),
            duration_ms=dur_ms,
            mode="live",
            universe_total=len(rows),
            regime_res=regime_res,
            sectors=sectors,
            scanner=scanner,
            day_levels=kept_map,
            prices=prices,
            signals_section=sigs_sec,
            strategy_meta=strat_meta,
        )
        # Update live signals inserted in this cycle with exact S3 scan_file & scan_id
        for sr in self.signals[:len(sigs_sec)]:
            if sr.get("day") == day and sr.get("bar_time") == bar_hhmm:
                sr["scan_file"] = doc["scan_file"]
                sr["scan_id"] = doc["scan_id"]

        s3_key, ok_s3, msg_s3 = save_scan_doc(self.cfg, doc, idx_entry, update_index=True)
        save_activity_s3(self.cfg, day, self.store.feed_newest_first())

        with self._lock:
            self.last_s3_key = s3_key
            self.last_s3_status = "Saved to S3" if ok_s3 else f"Local ({msg_s3})"
            self.latest_stock_reasons = {r["symbol"]: r for r in doc.get("all_stocks_table", [])}
            self.market_view = {
                "day": day, "bar_time": bar_hhmm, "nifty_pct": nifty_pct,
                "regime": regime_res, "sectors": sectors, "scanner": scanner,
            }
        self._refresh()

    def _evaluate_armed_live(self, boundary, day, bar_hhmm, regime_res, sectors, scanner, kept_map, prices, scan_t0=None):
        """Phase 3/4: fetch 5m history for armed symbols only and run strategy.on_bar."""
        if self._signaled_day != day:
            self._signaled_today, self._signaled_day = set(), day

        sigs_sec = []
        sig_rows_bar = []
        sec_info = {s["sector"]: s for s in sectors}
        gate_reason = ""
        if boundary.time() < self.cfg.no_entry_before:
            gate_reason = f"Before entry window ({self.cfg.no_entry_before:%H:%M})"
        elif boundary.time() > self.cfg.no_new_entries_after:
            gate_reason = f"After entry cutoff ({self.cfg.no_new_entries_after:%H:%M})"
        elif not self.link.orders_allowed():
            gate_reason = "Analyze mode is OFF or heartbeat stale"
        elif self._free_mb is not None and self._free_mb < self.cfg.block_free_mb:
            gate_reason = f"Free RAM below {self.cfg.block_free_mb} MB"

        for sym in scanner["armed"]:
            row = kept_map.get(sym)
            if not row:
                continue
            metrics, fetch_err = fetch_armed_bars(self.link, self.cfg, sym, boundary, wait_retry_s=5.0)
            ready_time = datetime.now(IST).strftime("%H:%M:%S")
            idx_1 = len(sigs_sec) + 1
            dur_ms = int((time.perf_counter() - scan_t0) * 1000) if scan_t0 else 0
            if metrics is None:
                side_miss = scanner["side"] or ""
                sig_no, sig_full_id = make_signal_ids(day, bar_hhmm, sym, side_miss, idx_1)
                miss_reason = fetch_err or "5m bar data missing"
                chk_sum = {
                    "passed_checks": 0, "total_checks": 8, "failed_checks": 1,
                    "failed_reasons": [f"Data missing: {miss_reason}"],
                    "min_condition": MIN_ENTRY_CONDITION_TEXT,
                }
                sig_row = {
                    "day": day, "bar_time": bar_hhmm, "ready_time": ready_time,
                    "symbol": sym, "sector": row["sector"], "side": side_miss,
                    "entry_price": prices.get(sym), "stop_loss": None, "target": None,
                    "rvol": None, "slot_mult": None, "status": "rejected",
                    "reason": miss_reason, "mode": "live",
                    "qty": None, "scan_id": "", "signal_no": sig_no, "signal_id": sig_full_id,
                    "scan_file": "", "duration_ms": dur_ms,
                    "rr_ratio": None, "risk_rs": None, "reward_rs": None, "error": None, **chk_sum,
                }
                sig_rows_bar.append(sig_row)
                self.store.add_activity(f"{bar_hhmm} {sym}: signal rejected ({miss_reason}).", "warn")
                sigs_sec.append({
                    "signal_no": sig_no, "signal_id": sig_full_id,
                    "symbol": sym, "sector": row["sector"], "side": side_miss,
                    "status": "rejected", "reason": miss_reason, "qty": None,
                    "entry_price": prices.get(sym), "stop_loss": None, "target": None,
                    "rvol": None, "slot_mult": None,
                    "rr_ratio": None, "risk_rs": None, "reward_rs": None, "error": None,
                    "checks": [], **chk_sum,
                })
                continue

            s_meta = sec_info.get(row["sector"], {})
            s_rank = int(s_meta.get("rank", 99))
            mark = s_meta.get("mark", "")
            s_bias = 1 if mark == "STRONG" else (-1 if mark == "WEAK" else 0)
            with self._lock:
                open_pos = list(self.open_positions)
                closed_pos = list(self.closed_trades)
                traded_today = set(self._signaled_today)
                free_mb = self._free_mb
            ctx = Context(
                now=boundary,
                regime=regime_res["active"],
                sector=row["sector"],
                sector_rank=s_rank,
                sector_bias=s_bias,
                pdh=float(row["pdh"]),
                pdl=float(row["pdl"]),
                pdc=float(row["pdc"]),
                vwap=float(metrics["vwap"]),
                atr=float(row["atr"]),
                day_open=float(metrics["day_open"]),
                day_high=float(metrics["day_high"]),
                day_low=float(metrics["day_low"]),
                slot_volume_avg=float(metrics["slot_volume_avg"]),
                rvol=float(metrics["rvol"]),
                ltp=float(prices.get(sym, metrics["bar_close"])),
                traded_today=(sym in traded_today),
                _held_symbols={p["symbol"] for p in open_pos},
            )
            sig, eval_out = evaluate_strategy_bar(
                self.strategy, self.strategy_mod, sym, metrics["bars"], ctx, self.cfg,
                regime_res=regime_res, s_meta=s_meta, metrics=metrics, row=row,
                gate_reason=gate_reason,
            )
            ready_time = datetime.now(IST).strftime("%H:%M:%S")
            slot_mult = round(metrics["bar_volume"] / metrics["slot_volume_avg"], 2) if metrics["slot_volume_avg"] > 0 else 0.0

            entry_px = round(metrics["bar_close"], 2)
            side = eval_out.get("side") or (scanner["side"] or "")
            stop_loss = eval_out.get("stop_loss")
            target = eval_out.get("target")
            qty = None
            if sig is not None and not gate_reason and not eval_out.get("error"):
                qty_calc, _, size_reason = compute_position_size(self.cfg, metrics["bar_close"], sig.stop_loss)
                if qty_calc <= 0:
                    status = "rejected"
                    side = sig.side
                    stop_loss = sig.stop_loss
                    target = sig.target
                    qty = 0
                    reason = size_reason
                else:
                    today_sum = summarize_today(self.cfg, open_pos, closed_pos, {k: {"ltp": v} for k, v in prices.items()})
                    ltp_now = self.feed.snapshot_prices().get(sym) or prices.get(sym, metrics["bar_close"])
                    gate_ok, gate_err = check_entry_gates(
                        self.cfg, open_pos, today_sum, sym, row["sector"], sig.side,
                        ltp_now, metrics["bar_close"], float(row["atr"]), traded_today,
                        free_mb, self.link.orders_allowed(), bool(self.link.reachable),
                    )
                    if not gate_ok:
                        status = "rejected"
                        side = sig.side
                        stop_loss = sig.stop_loss
                        target = sig.target
                        qty = qty_calc
                        reason = gate_err
                    else:
                        status = "would trade"
                        reason = sig.reason
                        side = sig.side
                        stop_loss = sig.stop_loss
                        target = sig.target
                        qty = qty_calc
                        self._signaled_today.add(sym)
                        self.orders.submit_entry({
                            "day": day,
                            "bar_time": bar_hhmm,
                            "symbol": sym,
                            "sector": row["sector"],
                            "side": side,
                            "qty": qty,
                            "decision_price": float(ltp_now),
                            "stop_loss": float(stop_loss),
                            "target": target,
                            "tick_age_s": self.feed.tick_age_seconds(),
                        })
            else:
                status = "rejected"
                if stop_loss:
                    qty, _, _ = compute_position_size(self.cfg, metrics["bar_close"], stop_loss)
                if gate_reason:
                    reason = gate_reason if sig is not None else f"{gate_reason}; {eval_out.get('reason', '')}".strip("; ")
                else:
                    reason = eval_out.get("reason") or eval_out.get("error") or "Rejected by strategy"

            sig_no, sig_full_id = make_signal_ids(day, bar_hhmm, sym, side, idx_1)
            checks = finalize_signal_checks(
                eval_out.get("checks"), self.cfg, regime_res, s_meta, metrics, row,
                side, qty, gate_reason, status, reason,
            )
            chk_sum = summarize_signal_checks(checks, min_condition_override=eval_out.get("min_condition"))
            rr_m = compute_rr_metrics(entry_px, stop_loss, target, qty=qty)

            sig_row = {
                "day": day, "bar_time": bar_hhmm, "ready_time": ready_time,
                "symbol": sym, "sector": row["sector"], "side": side,
                "entry_price": entry_px,
                "stop_loss": stop_loss, "target": target,
                "rvol": metrics["rvol"], "slot_mult": slot_mult,
                "status": status, "reason": reason, "mode": "live", "qty": qty,
                "scan_id": "", "signal_no": sig_no, "signal_id": sig_full_id,
                "scan_file": "", "duration_ms": dur_ms,
                "checks": checks,
                "rr_ratio": rr_m["rr_ratio"],
                "risk_rs": rr_m["risk_rs"],
                "reward_rs": rr_m["reward_rs"],
                "error": eval_out.get("error"), **chk_sum,
            }
            sig_rows_bar.append(sig_row)
            self.store.add_activity(
                f"{bar_hhmm} {sym} {side}: {status} — {reason}",
                "good" if status == "would trade" else ("bad" if eval_out.get("error") else "info"),
            )
            sigs_sec.append({
                "signal_no": sig_no,
                "signal_id": sig_full_id,
                "symbol": sym,
                "sector": row["sector"],
                "side": side,
                "status": status,
                "reason": reason,
                "qty": qty,
                "entry_price": entry_px,
                "stop_loss": stop_loss,
                "target": target,
                "rvol": metrics["rvol"],
                "slot_mult": slot_mult,
                "rr_ratio": rr_m["rr_ratio"],
                "risk_rs": rr_m["risk_rs"],
                "reward_rs": rr_m["reward_rs"],
                "error": eval_out.get("error"),
                "checks": checks,
                **chk_sum,
            })

        passed_bar = sum(1 for s in sig_rows_bar if s["status"] == "would trade")
        scan_file, scan_id = make_scan_names(day, bar_hhmm, len(kept_map), len(sig_rows_bar), passed_bar)
        for sr in sig_rows_bar:
            sr["scan_file"] = scan_file
            sr["scan_id"] = scan_id
            self.store.add_signal(sr)
            with self._lock:
                self.signals.insert(0, sr)
        return sigs_sec

    # ---------------------------------------------------------------- heartbeat
    def _after_heartbeat(self, kind):
        link, prev = self.link, self._prev_hb
        say = self.store.add_activity
        with self._lock:
            if link.reachable is False and prev["reachable"] is not False:
                say("OpenAlgo is not answering. Start OpenAlgo Desktop. The engine keeps retrying.", "bad")
            if link.reachable and prev["reachable"] is False:
                say("OpenAlgo is answering again.", "good")
            if link.reachable and link.key_ok is False and prev["key_ok"] is not False:
                say("OpenAlgo did not accept the API key. Paste the right key into .env." if self.cfg.has_key
                    else "The API key is missing. Paste the key from OpenAlgo into the .env file.", "bad")
            if link.key_ok and prev["key_ok"] is not True:
                say("Connected to OpenAlgo. The API key is accepted.", "good")
            if link.analyze_on is False and prev["analyze_on"] is not False:
                say("Analyze mode is OFF in OpenAlgo. The engine sends no orders.", "bad")
                if self.session and not self.session["halted"]:
                    self.session["halted"] = "Analyze mode was switched off."
                    say("Session halted. Switch Analyze mode back on, then press STOP and START.", "bad")
            if link.analyze_on is True and prev["analyze_on"] is not True:
                say("Analyze mode is ON. Orders can only go to the sandbox.", "good")
            self._prev_hb = {"reachable": link.reachable, "key_ok": link.key_ok,
                             "analyze_on": link.analyze_on}

    # ------------------------------------------------------------------ actions
    def request_start(self, source="button"):
        with self._lock:
            if self.session:
                return False, "A session is already running."
            if self.busy:
                return False, "Please wait: " + self.busy
            self.busy = "Starting: running the connection check"
            self.refusal = None
        threading.Thread(target=self._start_worker, args=(source,), name="start", daemon=True).start()
        return True, "Starting."

    def _start_worker(self, source):
        try:
            items = self._do_check()
            failed = [i for i in items if i["block"] and i["status"] != "green"]
            now = datetime.now(IST)
            with self._lock:
                if failed:
                    f = failed[0]
                    text = f"START refused. Check {f['n']} failed: {f['name']}. {f['text']}"
                    self.refusal = {"text": text, "fix": f["fix"]}
                    self.store.add_activity(text + " " + f["fix"], "bad")
                    return
                self.session = {"day": now.date().isoformat(), "started_at": time.time(),
                                "source": source, "halted": None}
                self._view_source = "live"
                state = self._state(now)
                self._prev_state = state
                self._last_bar_key = None
                self._regime_state = None
                how = "auto-start" if source == "auto" else "the START button"
                self.store.add_activity(f"Session started by {how}. {state_line(state, self.cfg)}", "good")

            # Phase 2: daily levels & pre-filter
            def on_lvl_prog(idx, total, sym):
                with self._lock:
                    self.busy = f"Loading daily levels ({idx}/{total}: {sym})"

            rows, from_cache = load_or_build_levels(
                self.cfg, self.link, self.store, on_progress=on_lvl_prog, stop_event=self._stop
            )
            elig = sector_eligibility(rows, self.cfg.min_members_per_sector)
            kept_map = kept_by_symbol(rows, self.cfg.min_members_per_sector)
            elig_count = sum(1 for v in elig.values() if v["eligible"])
            with self._lock:
                self.levels_rows = rows
                self._resolved.update(r["symbol"] for r in rows if r["drop_reason"] != "Symbol not found")
                self._resolved_day = now.date().isoformat()
            src_note = "from store" if from_cache else "from OpenAlgo"
            self.store.add_activity(
                f"Universe ready ({src_note}): {len(kept_map)} kept in {elig_count} eligible sectors, "
                f"{len(rows) - len(kept_map)} dropped.", "info",
            )

            # Phase 4: reconcile & restart recovery
            mismatches = self._run_reconcile()
            if mismatches:
                self.store.add_activity(
                    "Position reconcile mismatch: " + "; ".join(mismatches), "bad"
                )
            elif self.open_positions:
                self.store.add_activity(
                    f"Recovered {len(self.open_positions)} open paper position(s) from store.", "info"
                )

            # Start live price stream only if market is not closed
            if state != "market closed" and kept_map:
                with self._lock:
                    self.busy = "Starting price stream"
                ok, err = self.feed.start(list(kept_map.keys()))
                if ok:
                    self.store.add_activity(
                        f"Price stream started for {self.cfg.index_symbol} and {len(kept_map)} stocks.", "good"
                    )
                else:
                    self.store.add_activity(
                        f"Price stream unavailable ({err}). Using quote polling fallback.", "warn"
                    )
                # Run an immediate evaluation if market is already past 09:20
                now_after = datetime.now(IST)
                if now_after.time() >= self.cfg.market_open:
                    self._run_5m_cycle(now_after)
            elif state == "market closed" and self.cfg.dryrun_enabled:
                self.store.add_activity("Market is closed. You can run 'Dry run: last session' from the top bar.", "info")
        except Exception:
            self.log.exception("start failed")
            self.store.add_activity("START failed with an internal error. See logs/engine.log.", "bad")
        finally:
            with self._lock:
                self.busy = ""
            self._refresh()

    def request_stop(self):
        with self._lock:
            if not self.session:
                return False, "No session is running."
            self.session = None
            self.refusal = None
            self._prev_state = "idle"
            self.store.add_activity("Session stopped by the STOP button. The page stays up.", "info")
        self.feed.stop()
        self._refresh()
        return True, "Stopped."

    def request_check(self):
        with self._lock:
            if self.busy:
                return False, "Please wait: " + self.busy
            self.busy = "Running the connection check"
        threading.Thread(target=self._check_worker, name="check", daemon=True).start()
        return True, "Check started."

    def get_dryrun_options(self):
        return get_dryrun_options(self.cfg, self.store)

    def request_dryrun(self, day=None, start_time=None, end_time=None):
        now = datetime.now(IST)
        clean_day = str(day or "").strip() or None
        clean_start = str(start_time or "").strip() or None
        clean_end = str(end_time or "").strip() or None
        if clean_start:
            try:
                t_st = parse_hhmm(clean_start, "Start time")
                clean_start = f"{t_st:%H:%M}"
            except Exception as e:
                return False, str(e)
        if clean_end:
            try:
                t_en = parse_hhmm(clean_end, "End time")
                clean_end = f"{t_en:%H:%M}"
            except Exception as e:
                return False, str(e)
        with self._lock:
            if not self.cfg.dryrun_enabled:
                return False, "Dry run is disabled in config.yaml."
            if self.busy:
                return False, "Please wait: " + self.busy
            if self.session and self._state(now) != "market closed":
                return False, "Stop the live session first before running a dry run."
            day_lbl = clean_day or "last session"
            tm_lbl = f"{clean_start or f'{self.cfg.market_open:%H:%M}'}–{clean_end or f'{self.cfg.market_close:%H:%M}'}"
            self._dryrun_req = {"day": clean_day, "start_time": clean_start, "end_time": clean_end}
            self.busy = f"Dry run ({day_lbl}, {tm_lbl}): preparing"
        threading.Thread(target=self._dryrun_worker, name="dryrun", daemon=True).start()
        return True, f"Dry run started for {day_lbl} ({tm_lbl})."

    def _dryrun_worker(self):
        try:
            def on_prog(msg):
                with self._lock:
                    self.busy = msg
            with self._lock:
                rows = list(self.levels_rows)
                req = dict(self._dryrun_req)
                strat = self.strategy
                strat_mod = self.strategy_mod
            summary, last_mv, sigs = run_dry_session(
                self.cfg, self.link, self.store, strat,
                levels_rows=rows, on_progress=on_prog, stop_event=self._stop,
                target_day_req=req.get("day"),
                start_time_req=req.get("start_time"),
                end_time_req=req.get("end_time"),
                strategy_mod=strat_mod,
            )
            with self._lock:
                self.dryrun_summary = summary
                if summary:
                    self._view_source = "dryrun"
                    self.last_s3_key = summary.get("s3_key") or self.last_s3_key
                    self.last_s3_status = summary.get("s3_status") or self.last_s3_status
                if last_mv:
                    self.market_view = last_mv
                    self.latest_stock_reasons = last_mv.get("stock_reasons") or {}
                if sigs is not None:
                    self.signals = sigs
                if not self.levels_rows:
                    self.levels_rows = self.store.get_daily_levels(datetime.now(IST).date().isoformat())
        except Exception:
            self.log.exception("dryrun failed")
            self.store.add_activity("Dry run failed with an internal error. See logs/engine.log.", "bad")
        finally:
            with self._lock:
                self.busy = ""
            self._refresh()

    # -------------------------------------------------------- Strategy Socket
    def get_socket_info(self):
        with self._lock:
            qual = self.last_qualification
        return get_socket_reference(self.cfg, store=self.store, qual_cache=qual)

    def plug_strategy(self, file_rel_path: str):
        with self._lock:
            if self.busy:
                return False, "Please wait: " + self.busy, {}
        return apply_plug_strategy(self, file_rel_path)

    def unplug_strategy(self):
        with self._lock:
            if self.busy:
                return False, "Please wait: " + self.busy
        return apply_unplug_strategy(self)

    def upload_strategy(self, filename: str, code_text: str, auto_plug: bool = True):
        with self._lock:
            if self.busy:
                return False, "Please wait: " + self.busy, {}
        ok, msg, rel = upload_strategy_file(self.cfg, filename, code_text)
        if not ok:
            return False, msg, {}
        if auto_plug:
            ok2, msg2, qual = apply_plug_strategy(self, rel)
            return ok2, msg2, {"file": rel, "qualification": qual}
        qual = qualify_strategy_file(self.cfg, rel)
        self._refresh()
        return True, msg, {"file": rel, "qualification": qual}

    def delete_strategy(self, file_rel_path: str):
        with self._lock:
            if self.busy:
                return False, "Please wait: " + self.busy
        rel = str(file_rel_path or "").replace("\\", "/").strip()
        cur_rel = str(self.cfg.strategy_file or "").replace("\\", "/").strip()
        if rel and rel == cur_rel:
            apply_unplug_strategy(self)
        ok, msg = delete_strategy_file(self.cfg, rel)
        self._refresh()
        return ok, msg

    def qualify_socket_strategy(self, file_rel_path: str | None = None):
        target = str(file_rel_path or self.cfg.strategy_file or "").replace("\\", "/").strip()
        qual = qualify_strategy_file(self.cfg, target)
        cur_rel = str(self.cfg.strategy_file or "").replace("\\", "/").strip()
        if target and target == cur_rel:
            with self._lock:
                self.last_qualification = qual
            self._refresh()
        return qual

    def openrouter_verify(self, file_rel_path: str | None = None, api_key: str | None = None, model: str | None = None):
        target = str(file_rel_path or self.cfg.strategy_file or "").replace("\\", "/").strip()
        if not target:
            return {"ok": False, "message": "No strategy plugged or selected to verify."}
        res = verify_with_openrouter(self.cfg, self.store, target, api_key=api_key, model=model)
        cur_rel = str(self.cfg.strategy_file or "").replace("\\", "/").strip()
        if target == cur_rel and res.get("qualification"):
            with self._lock:
                self.last_qualification = res["qualification"]
        self._refresh()
        return res

    def _check_worker(self):
        try:
            self._do_check()
        except Exception:
            self.log.exception("check failed")
            self.store.add_activity("The connection check failed with an internal error. See logs/engine.log.", "bad")
        finally:
            with self._lock:
                self.busy = ""
            self._refresh()

    def _do_check(self):
        today = datetime.now(IST).date().isoformat()
        if self._resolved_day != today:
            self._resolved, self._resolved_day = set(), today
        with self._lock:
            self.check = {"running": True, "ran_at": None, "items": []}

        def on_update(items):
            with self._lock:
                self.check["items"] = [dict(i) for i in items]

        items, market = run_connection_check(self.link, self.cfg, self.universe, self._resolved, on_update)
        result = {"running": False, "ran_at": time.time(), "items": items}
        with self._lock:
            self.check = result
            self.market = market
        self.store.set_setting("last_check", result)
        count = {s: sum(1 for i in items if i["status"] == s) for s in ("green", "amber", "red")}
        level = "bad" if count["red"] else ("warn" if count["amber"] else "good")
        self.store.add_activity(
            f"Connection check: {count['green']} green, {count['amber']} amber, {count['red']} red.", level)
        return items

    def set_auto(self, on, time_text):
        try:
            t = parse_hhmm(time_text, "Auto-start time")
        except Exception as e:
            return False, str(e)
        with self._lock:
            self.auto_on, self.auto_time = bool(on), f"{t:%H:%M}"
            self.store.set_setting("auto_on", self.auto_on)
            self.store.set_setting("auto_time", self.auto_time)
            self.store.add_activity(
                f"Auto-start is ON at {self.auto_time} on weekdays. The engine must be running at that time."
                if self.auto_on else "Auto-start is OFF.", "info")
        self._refresh()
        return True, "Saved."

    # ------------------------------------------------------------- state + clock
    def _trading_day(self, now):
        if self.market["day"] == now.date().isoformat() and self.market["open"] is not None:
            return self.market["open"]
        return now.weekday() < 5

    def _state(self, now):
        if not self.session:
            return "idle"
        if self.session["halted"]:
            return "halted"
        return clock_state(now, self.cfg, self._trading_day(now))

    def _refresh(self):
        """One control tick: clock, auto-start, RAM, then rebuild the snapshot the UI reads."""
        now = datetime.now(IST)
        with self._lock:
            say = self.store.add_activity
            if self.session and self.session["day"] != now.date().isoformat():
                say(f"The session of {self.session['day']} ended: the day is over.", "info")
                self.session = None

            state = self._state(now)
            if state != self._prev_state:
                if self.session and state != "halted":
                    say(state_line(state, self.cfg), "info")
                self._prev_state = state

            target = datetime.combine(now.date(), parse_hhmm(self.auto_time), tzinfo=IST)
            crossed = self._last_tick < target <= now
            self._last_tick = now
            if crossed and self.auto_on and now.weekday() < 5:
                if self.session or self.busy:
                    say("Auto-start time reached, but a session is already running or starting.", "info")
                else:
                    say(f"Auto-start time {self.auto_time} reached.", "info")
                    self.request_start("auto")

            self._ticks += 1
            if self._ticks % 5 == 1:
                self._free_mb, self._engine_mb = sysmem.free_ram_mb(), sysmem.engine_mb()
                ram = "ok"
                if self._free_mb is not None:
                    ram = ("block" if self._free_mb < self.cfg.block_free_mb
                           else "warn" if self._free_mb < self.cfg.warn_free_mb else "ok")
                if ram != self._prev_ram:
                    if ram == "ok":
                        say(f"Free RAM is back to {self._free_mb} MB.", "good")
                    else:
                        say(f"Free RAM is low: {self._free_mb} MB. Close the editor and extra browser tabs.", "warn")
                    self._prev_ram = ram

            self._snapshot = json.dumps(self._build(now, state)).encode("utf-8")

    def snapshot_bytes(self):
        return self._snapshot

    # ----------------------------------------------------------------- snapshot
    def _build(self, now, state):
        cfg, link = self.cfg, self.link
        banners = []
        if link.reachable is False:
            banners.append({"level": "red", "text": "OpenAlgo is not answering.",
                            "fix": "Start OpenAlgo Desktop. This page reconnects by itself within about 30 seconds."})
        if not cfg.has_key:
            banners.append({"level": "red", "text": "The API key is missing.",
                            "fix": "Open the .env file in the engine folder, paste the API key from OpenAlgo "
                                   "after OPENALGO_API_KEY=, and save. The engine picks it up within about 30 seconds."})
        elif link.reachable and link.key_ok is False:
            banners.append({"level": "red", "text": "OpenAlgo did not accept the API key.",
                            "fix": "Copy the key from the API Key page in OpenAlgo into .env and save."})
        if link.analyze_on is False:
            banners.append({"level": "red", "text": "Analyze mode is OFF in OpenAlgo. The engine sends no orders.",
                            "fix": "Switch OpenAlgo to Analyze mode with its own toggle."
                                   + (" Then press STOP and START." if state == "halted" else "")})
        elif state == "halted":
            banners.append({"level": "red", "text": "The session is halted: " + self.session["halted"],
                            "fix": "Press STOP, then START to begin again."})
        if self._free_mb is not None and self._free_mb < cfg.block_free_mb:
            banners.append({"level": "amber",
                            "text": f"Free RAM is {self._free_mb} MB. New entries are blocked below {cfg.block_free_mb} MB.",
                            "fix": "Close the code editor, the AI agent and extra browser tabs."})
        elif self._free_mb is not None and self._free_mb < cfg.warn_free_mb:
            banners.append({"level": "amber", "text": f"Free RAM is low: {self._free_mb} MB.",
                            "fix": "Close the code editor, the AI agent and extra browser tabs."})
        if self.feed.active and self.feed.polling_fallback:
            banners.append({"level": "amber", "text": "Price stream is silent. Using quote polling fallback.",
                            "fix": "Check OpenAlgo WebSocket status if ticks do not resume."})
        if self.orders.reconcile_mismatches:
            banners.append({
                "level": "red",
                "text": "Position mismatch with OpenAlgo: " + "; ".join(self.orders.reconcile_mismatches),
                "fix": "Check OpenAlgo Positions / Orderbook vs engine Positions.",
            })

        elig = sector_eligibility(self.levels_rows, cfg.min_members_per_sector) if self.levels_rows else {}
        kept_count = sum(1 for r in self.levels_rows if r["kept"] and elig.get(r["sector"], {}).get("eligible", False))

        live_prices = self.feed.snapshot_prices()
        prices_map = {k: {"ltp": v} for k, v in live_prices.items()}
        if self._view_source == "dryrun" and self.dryrun_summary and not self.session:
            ds = self.dryrun_summary
            pos_rows = list(ds.get("open_positions") or [])
            today_sum = dict(ds.get("today") or summarize_today(cfg, [], [], {}))
            closed_list = list(ds.get("closed_trades") or [])[:20]
            today_mode = "dryrun"
        else:
            pos_rows = []
            for p in self.open_positions:
                ltp = live_prices.get(p["symbol"])
                pnl_rs, r_mult = compute_position_mtm(p, ltp)
                pos_rows.append({**p, "ltp": ltp, "pnl_rs": pnl_rs, "r_mult": r_mult})
            today_sum = summarize_today(cfg, self.open_positions, self.closed_trades, prices_map)
            closed_list = self.closed_trades[:20]
            today_mode = "live"

        sigs_list = self.signals[:100]
        sig_total = len(self.signals)
        sig_wt = sum(1 for x in self.signals if x.get("status") == "would trade")
        sig_rej = sig_total - sig_wt
        sig_errs = sum(1 for x in self.signals if x.get("error") or x.get("has_error"))
        sig_bars = len({x.get("bar_time") for x in self.signals if x.get("bar_time")})
        sig_morning = sum(1 for x in self.signals if "09:15" <= (x.get("bar_time") or "") < "11:30")
        sig_midday = sum(1 for x in self.signals if "11:30" <= (x.get("bar_time") or "") < "13:30")
        sig_afternoon = sum(1 for x in self.signals if (x.get("bar_time") or "") >= "13:30")
        min_cond_txt = (
            self.signals[0].get("min_condition")
            if (self.signals and self.signals[0].get("min_condition"))
            else (getattr(self.strategy_mod, "MIN_CONDITION_TEXT", None) or MIN_ENTRY_CONDITION_TEXT)
        )
        sigs_summary = {
            "day": (self.signals[0]["day"] if self.signals else now.date().isoformat()),
            "total": sig_total,
            "would_trade": sig_wt,
            "rejected": sig_rej,
            "errors_count": sig_errs,
            "distinct_bars": sig_bars,
            "morning_0915_1130": sig_morning,
            "midday_1130_1330": sig_midday,
            "afternoon_1330_1530": sig_afternoon,
            "min_condition": min_cond_txt,
            "check_breakdown": compute_check_breakdown(self.signals),
        }

        # Build per-stock dissection reasons (keeps clickable [Why?] working for every KEPT & DROP stock)
        stock_reasons = dict(self.latest_stock_reasons)
        mv = self.market_view or {}
        if not stock_reasons and self.levels_rows and mv.get("regime"):
            kept_lv = {
                r["symbol"]: r for r in self.levels_rows
                if r["kept"] and elig.get(r["sector"], {}).get("eligible", False)
            }
            sc = mv.get("scanner") or {}
            sl_prices = {x["symbol"]: x["ltp"] for x in (sc.get("shortlist") or []) if x.get("ltp")}
            merged_prices = {**sl_prices, **live_prices}
            rows_all, _ = build_all_stocks_rows(
                kept_lv, merged_prices, mv.get("sectors") or [], sc, sc.get("armed") or [],
                signals_section=[x for x in sigs_list if x.get("bar_time") == mv.get("bar_time")],
                bar_time=mv.get("bar_time") or "",
            )
            stock_reasons = {r["symbol"]: r for r in rows_all}
        for r in self.levels_rows:
            sym = r["symbol"]
            if sym not in stock_reasons:
                eff_kept = bool(r["kept"] and elig.get(r["sector"], {}).get("eligible", False))
                drop_why = r["drop_reason"] if not r["kept"] else (
                    "" if eff_kept else f"Sector '{r['sector']}' me < {cfg.min_members_per_sector} qualified stocks the."
                )
                stock_reasons[sym] = {
                    "symbol": sym,
                    "sector": r["sector"],
                    "sector_mark": "DROPPED" if not eff_kept else "NEUTRAL",
                    "ltp": live_prices.get(sym),
                    "pdh": r.get("pdh"),
                    "pdl": r.get("pdl"),
                    "atr": r.get("atr"),
                    "atr_pct": r.get("atr_pct"),
                    "avg_val_cr": r.get("avg_val_cr"),
                    "stage": "KEPT_PREFILTER" if eff_kept else "PREFILTER_DROPPED",
                    "min_condition": (
                        f"Pre-filter pass hone ke liye: Daily Avg Value >= ₹{cfg.min_traded_value_cr} Cr, "
                        f"ATR% >= {cfg.min_atr_pct}%, aur Sector me >= {cfg.min_members_per_sector} valid stocks zaroori hain."
                    ),
                    "why_not_taken": (
                        "Pre-filter pass hai; latest 5m scan run hone par detailed calculation dikhega."
                        if eff_kept else f"Pre-filter DROP hua: {drop_why} (20d Val: ₹{r.get('avg_val_cr') or 0} Cr, ATR%: {r.get('atr_pct') or 0}%)."
                    ),
                }

        all_feed = self.store.feed_newest_first()
        t = time.time()
        if str(self.busy).startswith("Dry run"):
            s_line = "Dry run replay in progress (0 real orders) — Do NOT press START until replay finishes."
        elif state == "idle" and self._view_source == "dryrun" and self.dryrun_summary and not self.session:
            ds = self.dryrun_summary
            s_line = (
                f"Dry run loaded for {ds['day']} ({ds.get('start_time', '09:15')}–{ds.get('end_time', '15:15')}) "
                f"with '{ds.get('strategy')}'. Inspect signals, simulated trades & P&L below, or press START for live paper session."
            )
        else:
            s_line = state_line(state, cfg)
        return {
            "now_epoch": t,
            "now": now.strftime("%a %d %b %Y, %H:%M:%S"),
            "state": state,
            "state_line": s_line,
            "busy": self.busy,
            "refusal": self.refusal,
            "session": None if not self.session else {
                "day": self.session["day"],
                "started": datetime.fromtimestamp(self.session["started_at"], IST).strftime("%H:%M:%S"),
                "source": self.session["source"],
            },
            "banners": banners,
            "auto": {"on": self.auto_on, "time": self.auto_time},
            "times": {"open": f"{cfg.market_open:%H:%M}", "last_entry": f"{cfg.no_new_entries_after:%H:%M}",
                      "square_off": f"{cfg.square_off:%H:%M}"},
            "conn": {
                "reachable": link.reachable, "key_ok": link.key_ok, "analyze_on": link.analyze_on,
                "heartbeat_age_s": None if link.hb_ok_at is None else int(t - link.hb_ok_at),
                "heartbeat_every_s": cfg.heartbeat_seconds,
                "latency_ms": _r(link.latency_ms), "latency_avg_ms": _r(link.latency_avg_ms),
                "free_ram_mb": self._free_mb, "engine_mb": self._engine_mb,
                "engine_target_mb": cfg.engine_target_mb, "warn_free_mb": cfg.warn_free_mb,
                "openalgo_url": cfg.host,
                "last_tick_age_s": self.feed.tick_age_seconds(),
                "stream_active": self.feed.active,
                "stream_stale": self.feed.polling_fallback,
                "stale_seconds": cfg.stale_seconds,
            },
            "check": self.check,
            "activity": all_feed[:5],
            "activity_total": len(all_feed),
            "phases": self.phases,
            "strategy": cfg.strategy_name,
            "universe": {
                "total": len(self.levels_rows),
                "kept": kept_count,
                "dropped": len(self.levels_rows) - kept_count,
                "eligible_sectors": sum(1 for v in elig.values() if v["eligible"]),
                "sectors": elig,
                "rows": [
                    {
                        **r,
                        "sector_eligible": elig.get(r["sector"], {}).get("eligible", False),
                        "effective_kept": bool(r["kept"] and elig.get(r["sector"], {}).get("eligible", False)),
                        "effective_reason": r["drop_reason"] if not r["kept"] else (
                            "" if elig.get(r["sector"], {}).get("eligible", False)
                            else f"Sector < {cfg.min_members_per_sector} kept"
                        ),
                    }
                    for r in self.levels_rows
                ],
            },
            "market_view": self.market_view,
            "stock_reasons": stock_reasons,
            "signals": sigs_list,
            "signals_summary": sigs_summary,
            "dryrun": {
                "enabled": cfg.dryrun_enabled,
                "can_run": cfg.dryrun_enabled and (not self.session or state == "market closed") and not self.busy,
                "running": str(self.busy).startswith("Dry run"),
                "active_req": self._dryrun_req,
                "summary": self.dryrun_summary,
            },
            "positions": pos_rows,
            "today": {**today_sum, "closed": closed_list, "mode": today_mode},
            "reconcile": {
                "mismatches": list(self.orders.reconcile_mismatches),
                "external": list(self.orders.external_positions),
                "checked_at": self.orders.last_reconcile_at,
            },
            "strategy_info": strategy_meta_dict(cfg, self.strategy_mod, self.strategy, qualification=self.last_qualification),
            "visibility": {
                "total_stocks": len(self.levels_rows),
                "kept_stocks": kept_count,
                "dropped_stocks": len(self.levels_rows) - kept_count,
                "eligible_sectors": sum(1 for v in elig.values() if v["eligible"]),
                "live_prices_count": len(live_prices),
                "cadence": {
                    "ticks_exits": "Every 1s (WebSocket + 5s fallback)",
                    "market_scan": f"Every {cfg.rescan_minutes}m bar ({cfg.no_entry_before:%H:%M}–{cfg.no_new_entries_after:%H:%M})",
                    "heartbeat_reconcile": f"Every {int(cfg.heartbeat_seconds)}s",
                },
                "limits": {
                    "capital_rs": cfg.capital,
                    "risk_per_trade_rs": cfg.risk_per_trade_rs,
                    "notional_cap_rs": round((cfg.capital * cfg.leverage) / max(1, cfg.max_open_positions), 0),
                    "max_open_positions": cfg.max_open_positions,
                    "max_per_sector": cfg.max_positions_per_sector,
                    "max_trades_day": cfg.max_trades_per_day,
                    "daily_loss_limit_rs": cfg.daily_loss_limit_rs,
                },
                "external_positions": list(self.orders.external_positions),
            },
            "s3": {
                "configured": cfg.has_s3,
                "bucket": cfg.s3_bucket,
                "region": cfg.s3_region,
                "last_key": self.last_s3_key,
                "last_status": self.last_s3_status,
            },
        }


def _r(v):
    return None if v is None else round(v)
