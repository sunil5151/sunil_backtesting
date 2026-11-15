"""On-demand dry run of any selected (or last completed) session with full trade simulation.

Fetches the target session's 5m bars on demand, replays bars through the exact same pure
functions (regime -> sector -> scanner -> strategy -> sizing -> exits), opens & closes simulated
paper positions, calculates Risk-to-Reward (R:R), Net P&L, Trade Journey analysis, and
Check-by-Check breakdown, sends zero broker orders, and discards all 5m bars when done.
"""
from datetime import date, datetime, time as dtime, timedelta
import gc
import time

from core.data_router import fetch_backtest_data

from engine.bars import Context, compute_rr_metrics, evaluate_strategy_bar, prepare_bar_metrics
from engine.config import parse_hhmm
from engine.exits import evaluate_position_exit
from engine.levels import kept_by_symbol, load_or_build_levels
from engine.oa import IST
from engine.portfolio import (
    check_entry_gates,
    compute_position_mtm,
    compute_position_size,
    estimate_round_trip_cost,
    summarize_today,
)
from engine.regime import compute_breadth, evaluate_regime
from engine.s3_archive import (
    build_scan_document,
    compute_check_breakdown,
    finalize_signal_checks,
    flush_day_index,
    make_scan_names,
    make_signal_ids,
    save_activity_s3,
    save_scan_doc,
    strategy_meta_dict,
    summarize_signal_checks,
)
from engine.macro_report import generate_and_save_macro_report
from engine.scanner import scan_candidates
from engine.sector import rank_sectors


def _norm_ist(df):
    if df is None or not hasattr(df, "columns") or len(df) == 0:
        return None
    out = df[["open", "high", "low", "close", "volume"]].copy()
    if out.index.tz is None:
        out.index = out.index.tz_localize(IST)
    else:
        out.index = out.index.tz_convert(IST)
    return out


def _pick_target_day(nifty_df, cfg, now):
    """Pick today if session is finished (after square_off), else the latest completed prior day."""
    today = now.date()
    counts = {}
    for d in nifty_df.index.date:
        counts[d] = counts.get(d, 0) + 1
    full_days = sorted(d for d, n in counts.items() if n >= 15)
    if not full_days:
        return None
    if today in full_days and now.time() >= cfg.square_off:
        return today
    prior = [d for d in full_days if d < today]
    return prior[-1] if prior else full_days[-1]


def get_dryrun_options(cfg, store) -> dict:
    """Return recent selectable weekdays and archived days for the Dry Run Date/Time picker."""
    now = datetime.now(IST)
    today = now.date()
    days = []
    seen = set()
    # Include days already archived locally
    arch_dir = cfg.root / "data" / "scan_archive"
    if arch_dir.exists():
        for p in sorted(arch_dir.iterdir(), reverse=True):
            if p.is_dir() and len(p.name) == 10:
                seen.add(p.name)
                days.append(p.name)
    # Include last 10 weekdays up to today (skipping today if before square_off)
    cur = today if now.time() >= cfg.square_off else (today - timedelta(days=1))
    added = 0
    while added < 10:
        if cur.weekday() < 5:
            ds = cur.isoformat()
            if ds not in seen:
                seen.add(ds)
                days.append(ds)
            added += 1
        cur -= timedelta(days=1)
    days = sorted(set(days), reverse=True)
    default_day = days[0] if days else today.isoformat()
    return {
        "days": days,
        "default_day": default_day,
        "default_start_time": f"{cfg.market_open:%H:%M}",
        "default_end_time": f"{cfg.market_close:%H:%M}",
        "preset_times": ["09:15", "09:30", "10:00", "10:30", "11:00", "12:00", "13:00", "14:00"],
    }


def _build_trade_analysis(pos: dict, exit_price: float | None, exit_time: str | None, exit_reason: str | None, net_pnl: float, r_mult: float, costs: float) -> dict:
    """Plain-language post-trade report: What happened vs What should have happened."""
    side = pos["side"]
    entry = float(pos["entry_price"])
    init_stop = float(pos["initial_stop"])
    target = float(pos["target"]) if pos.get("target") is not None else None
    rr = pos.get("rr_ratio")
    rr_txt = f"1:{rr:.2f}" if rr else "N/A"
    risk_rs = pos.get("risk_rs")
    reward_rs = pos.get("reward_rs")
    max_fav_r = float(pos.get("max_favorable_r") or 0.0)
    max_adv_r = float(pos.get("max_adverse_r") or 0.0)
    be_txt = f"Yes (moved SL to ₹{entry:.2f} at {pos.get('breakeven_time')})" if pos.get("breakeven_moved") else "No (never reached +1.0R)"

    sig_summary = (
        f"{pos['bar_time']} {side} {pos['symbol']} x{pos['qty']} @ ₹{entry:.2f} | "
        f"SL ₹{init_stop:.2f} | Target {('₹' + format(target, '.2f')) if target else '–'} | "
        f"R:R {rr_txt} (Risk ₹{risk_rs or 0:.0f} → Reward ₹{reward_rs or 0:.0f})"
    )

    if exit_reason:
        what_happened = (
            f"Peak profit reached +{max_fav_r:.2f}R (₹{pos.get('best_price', entry):.2f}); "
            f"worst drawdown was {max_adv_r:.2f}R (₹{pos.get('worst_price', entry):.2f}). "
            f"+1R Breakeven triggered: {be_txt}. "
            f"Closed via {exit_reason} at {exit_time} @ ₹{exit_price:.2f} → "
            f"Net P&L ₹{net_pnl:+.2f} ({r_mult:+.2f}R) after ₹{costs:.2f} brokerage/STT/GST."
        )
        if exit_reason == "TARGET":
            should_have = f"Strategy plan worked as designed: captured full target {rr_txt} (+₹{net_pnl:.2f} net)."
        elif exit_reason == "BREAKEVEN":
            should_have = (
                f"Trade reached +{max_fav_r:.2f}R so +1R breakeven lock protected capital, "
                f"then pulled back to entry (small cost loss ₹{abs(net_pnl):.2f} instead of -1R)."
            )
        elif exit_reason == "STOP":
            should_have = (
                f"Setup failed and hit initial stop-loss at ₹{init_stop:.2f} (peak was +{max_fav_r:.2f}R). "
                f"Stop capped loss at ₹{abs(net_pnl):.2f}."
            )
        else:
            should_have = (
                f"Neither stop nor target hit before {exit_time}; closed at ₹{exit_price:.2f} "
                f"(Net ₹{net_pnl:+.2f}, {r_mult:+.2f}R)."
            )
    else:
        what_happened = (
            f"Still OPEN at end of window. Peak +{max_fav_r:.2f}R, drawdown {max_adv_r:.2f}R, "
            f"Breakeven: {be_txt}."
        )
        should_have = "Extend end time to 15:15 to observe full exit/square-off outcome."

    return {
        "signal_summary": sig_summary,
        "what_happened": what_happened,
        "what_should_have_happened": should_have,
        "max_favorable_r": round(max_fav_r, 2),
        "max_adverse_r": round(max_adv_r, 2),
        "breakeven_triggered": bool(pos.get("breakeven_moved")),
        "breakeven_time": pos.get("breakeven_time"),
    }


def _step_open_positions(
    sim_open: list,
    sim_closed: list,
    stock_bars: dict,
    open_ts,
    boundary,
    b_idx: int,
    cfg,
    be_at_r: float,
    target_day_str: str,
    store,
):
    """Advance all open dry-run positions across bar [open_ts, boundary] using engine.exits."""
    b_hhmm = boundary.strftime("%H:%M")
    still_open = []
    for pos in sim_open:
        if pos["entry_bar_idx"] >= b_idx:
            still_open.append(pos)
            continue
        df = stock_bars.get(pos["symbol"])
        if df is None:
            still_open.append(pos)
            continue
        bar_rows = df[df.index == open_ts]
        if len(bar_rows) == 0:
            still_open.append(pos)
            continue

        bar = bar_rows.iloc[0]
        b_open = float(bar["open"])
        b_high = float(bar["high"])
        b_low = float(bar["low"])
        b_close = float(bar["close"])
        side = pos["side"]
        entry = float(pos["entry_price"])
        init_stop = float(pos["initial_stop"])
        r_per_share = abs(entry - init_stop)

        # Track MFE / MAE extremes
        if side == "LONG":
            pos["best_price"] = max(float(pos.get("best_price") or entry), b_high)
            pos["worst_price"] = min(float(pos.get("worst_price") or entry), b_low)
            fav_r = (pos["best_price"] - entry) / r_per_share if r_per_share > 0 else 0.0
            adv_r = (pos["worst_price"] - entry) / r_per_share if r_per_share > 0 else 0.0
            probes = [b_low, b_high, b_close]
        else:
            pos["best_price"] = min(float(pos.get("best_price") or entry), b_low)
            pos["worst_price"] = max(float(pos.get("worst_price") or entry), b_high)
            fav_r = (entry - pos["best_price"]) / r_per_share if r_per_share > 0 else 0.0
            adv_r = (entry - pos["worst_price"]) / r_per_share if r_per_share > 0 else 0.0
            probes = [b_high, b_low, b_close]
        pos["max_favorable_r"] = round(max(float(pos.get("max_favorable_r") or 0.0), fav_r), 2)
        pos["max_adverse_r"] = round(min(float(pos.get("max_adverse_r") or 0.0), adv_r), 2)

        exited = False
        exit_reason = None
        exit_price = b_close
        prev_time = open_ts.time()

        # Probe adverse extreme then favorable extreme before square-off clock
        for probe_idx, probe_px in enumerate(probes):
            check_t = boundary.time() if probe_idx == 2 else prev_time
            ev = evaluate_position_exit(
                pos, probe_px, check_t, cfg.square_off,
                breakeven_at_r=be_at_r, tick_age_s=0.0, stale_seconds=cfg.stale_seconds,
            )
            if ev["breakeven_triggered"]:
                pos["stop_loss"] = ev["new_stop"]
                pos["breakeven_moved"] = True
                pos["breakeven_time"] = b_hhmm
                store.add_activity(
                    f"[Dry run {target_day_str}] {b_hhmm} {pos['symbol']} reached +{be_at_r:.1f}R: "
                    f"stop moved to breakeven ₹{ev['new_stop']:.2f}.",
                    "good",
                )
            if ev["new_watermark"] is not None:
                pos["watermark"] = ev["new_watermark"]
            if ev["exit_reason"]:
                exit_reason = ev["exit_reason"]
                if exit_reason == "TARGET" and pos.get("target") is not None:
                    exit_price = float(pos["target"])
                elif exit_reason in ("STOP", "BREAKEVEN"):
                    stop_lvl = float(pos["stop_loss"])
                    if side == "LONG" and b_open < stop_lvl:
                        exit_price = b_open
                    elif side == "SHORT" and b_open > stop_lvl:
                        exit_price = b_open
                    else:
                        exit_price = stop_lvl
                else:
                    exit_price = b_close
                exited = True
                break

        if exited:
            sign = 1.0 if side == "LONG" else -1.0
            gross_pnl = round(sign * (exit_price - entry) * int(pos["qty"]), 2)
            costs = estimate_round_trip_cost(
                entry, exit_price, int(pos["qty"]),
                product=cfg.product, exchange=cfg.exchange, gst_rate=cfg.gst_rate,
            )
            net_pnl = round(gross_pnl - costs, 2)
            r_mult = round(sign * (exit_price - entry) / r_per_share, 2) if r_per_share > 0 else 0.0
            closed = {
                **pos,
                "ltp": round(exit_price, 2),
                "exit_price": round(exit_price, 2),
                "exit_time": b_hhmm,
                "exit_reason": exit_reason,
                "gross_pnl": gross_pnl,
                "costs": costs,
                "net_pnl": net_pnl,
                "r_multiple": r_mult,
                "stale_flag": False,
                "status": "CLOSED",
            }
            closed["analysis"] = _build_trade_analysis(pos, exit_price, b_hhmm, exit_reason, net_pnl, r_mult, costs)
            sim_closed.append(closed)
            lvl = "good" if net_pnl > 0 else ("warn" if exit_reason == "BREAKEVEN" else "bad")
            store.add_activity(
                f"[Dry run {target_day_str}] {b_hhmm} CLOSED {side} {pos['symbol']} ({exit_reason}) "
                f"In ₹{entry:.2f} → Out ₹{exit_price:.2f} | Net ₹{net_pnl:+.2f} ({r_mult:+.2f}R)",
                lvl,
            )
        else:
            pnl_now, r_now = compute_position_mtm(pos, b_close)
            pos["ltp"] = round(b_close, 2)
            pos["pnl_rs"] = pnl_now
            pos["r_mult"] = r_now
            still_open.append(pos)

    return still_open


def run_dry_session(
    cfg,
    link,
    store,
    strategy,
    levels_rows=None,
    on_progress=None,
    stop_event=None,
    target_day_req=None,
    start_time_req=None,
    end_time_req=None,
    strategy_mod=None,
):
    """Replay selected (or last completed) session across 5m bars with simulated position execution."""
    now = datetime.now(IST)
    today_dt = now.date()

    req_day_dt = None
    if target_day_req and str(target_day_req).strip():
        try:
            req_day_dt = date.fromisoformat(str(target_day_req).strip())
        except Exception:
            req_day_dt = None

    start_hhmm = str(start_time_req or f"{cfg.market_open:%H:%M}").strip()
    end_hhmm = str(end_time_req or f"{cfg.market_close:%H:%M}").strip()
    try:
        start_t = parse_hhmm(start_hhmm, "Dry run start time")
    except Exception:
        start_t = cfg.market_open
        start_hhmm = f"{start_t:%H:%M}"
    try:
        end_t = parse_hhmm(end_hhmm, "Dry run end time")
    except Exception:
        end_t = cfg.market_close
        end_hhmm = f"{end_t:%H:%M}"
    if end_t <= start_t:
        end_t = cfg.market_close
        end_hhmm = f"{end_t:%H:%M}"

    if not levels_rows:
        levels_rows, _ = load_or_build_levels(cfg, link, store, stop_event=stop_event)
    kept_map = kept_by_symbol(levels_rows, cfg.min_members_per_sector)
    if not kept_map:
        return None, None, []

    fetch_end_dt = req_day_dt if req_day_dt else today_dt
    if on_progress:
        on_progress(f"Dry run ({req_day_dt.isoformat() if req_day_dt else 'last session'}, from {start_hhmm}): fetching NIFTY 5m bars")
    start_12d = (fetch_end_dt - timedelta(days=14)).isoformat()
    end_fetch_str = fetch_end_dt.isoformat()
    nifty_5m = _norm_ist(
        fetch_backtest_data(link, cfg.index_symbol, cfg.index_exchange, "5m", start_12d, end_fetch_str, source="api")
    )
    if nifty_5m is None or len(nifty_5m) == 0:
        return None, None, []

    if req_day_dt:
        avail_days = sorted({d for d in nifty_5m.index.date if d <= req_day_dt})
        if req_day_dt in avail_days:
            target_day = req_day_dt
        elif avail_days:
            target_day = avail_days[-1]
            store.add_activity(
                f"Dry run requested {req_day_dt.isoformat()} had no bars (holiday/weekend); using nearest prior trading day {target_day.isoformat()}.",
                "warn",
            )
        else:
            return None, None, []
    else:
        target_day = _pick_target_day(nifty_5m, cfg, now)
        if target_day is None:
            return None, None, []

    target_day_str = target_day.isoformat()

    # NIFTY previous day close for target_day
    nifty_pdc = None
    try:
        df_nd = fetch_backtest_data(
            link, cfg.index_symbol, cfg.index_exchange, "D",
            (target_day - timedelta(days=10)).isoformat(), target_day_str, source="api",
        )
        if df_nd is not None and len(df_nd) > 0:
            prev_nd = df_nd[df_nd.index.date < target_day]
            if len(prev_nd) > 0:
                nifty_pdc = float(prev_nd["close"].iloc[-1])
    except Exception:
        nifty_pdc = None
    if nifty_pdc is None:
        prior_n = nifty_5m[nifty_5m.index.date < target_day]
        if len(prior_n) > 0:
            nifty_pdc = float(prior_n["close"].iloc[-1])

    # Fetch 5m bars for kept universe (on demand; discarded at end of function)
    stock_bars = {}
    syms = sorted(kept_map.keys())
    start_5s = (target_day - timedelta(days=12)).isoformat()
    for idx, sym in enumerate(syms, 1):
        if stop_event and stop_event.is_set():
            break
        if on_progress and (idx == 1 or idx % 8 == 0 or idx == len(syms)):
            on_progress(f"Dry run {target_day_str} ({start_hhmm}–{end_hhmm}): fetching 5m bars ({idx}/{len(syms)}: {sym})")
        try:
            raw = fetch_backtest_data(link, sym, cfg.exchange, "5m", start_5s, target_day_str, source="api")
            df = _norm_ist(raw)
            if df is not None and len(df) > 0:
                stock_bars[sym] = df
        except Exception:
            continue

    if stop_event and stop_event.is_set():
        del stock_bars
        gc.collect()
        return None, None, []

    # Build day-appropriate PDH/PDL/PDC levels for target_day
    day_levels = {}
    for sym, row in kept_map.items():
        r = dict(row)
        df = stock_bars.get(sym)
        if target_day != today_dt and df is not None:
            prior = df[df.index.date < target_day]
            if len(prior) > 0:
                prev_d = prior.index[-1].date()
                prev_day_bars = prior[prior.index.date == prev_d]
                r["pdh"] = round(float(prev_day_bars["high"].max()), 2)
                r["pdl"] = round(float(prev_day_bars["low"].min()), 2)
                r["pdc"] = round(float(prev_day_bars["close"].iloc[-1]), 2)
        day_levels[sym] = r

    # Clear prior dryrun signals for target_day and prepare bar-by-bar replay
    store.clear_signals_for_day(target_day_str, mode="dryrun")
    target_nifty = nifty_5m[nifty_5m.index.date == target_day]
    bar_delta = timedelta(minutes=cfg.rescan_minutes)
    end_cutoff_dt = datetime.combine(target_day, end_t, tzinfo=IST)
    bar_opens = [ts for ts in list(target_nifty.index) if (ts + bar_delta) <= end_cutoff_dt]
    active_params = dict(getattr(strategy, "params", cfg.strategy_params or {})) if strategy is not None else dict(cfg.strategy_params or {})
    baseline_sessions = int(active_params.get("vol_baseline_sessions", 5))
    be_at_r = float(active_params.get("breakeven_at_r", 1.0))

    regime_state = {"active": "CHOPPY", "pending_raw": None, "pending_count": 0}
    prev_active = None
    traded_syms = set()
    signals_out = []
    last_mv = None
    last_summary = ""
    would_count = 0
    rej_count = 0
    index_entries = []
    scan_docs = []
    strat_meta = strategy_meta_dict(cfg, strategy_mod, strategy)
    last_s3_key = ""
    last_s3_status = ""
    last_all_stocks = {}

    sim_open_positions = []
    sim_closed_trades = []
    next_trade_id = 1
    timeline = []
    replayed_bars_count = 0

    store.add_activity(
        f"Dry run started for {target_day_str} (Window {start_hhmm}–{end_hhmm}, {len(bar_opens)} bars, {len(stock_bars)} stocks, strategy: {strat_meta.get('name')}).",
        "info",
    )

    for b_idx, open_ts in enumerate(bar_opens):
        if stop_event and stop_event.is_set():
            break
        bar_t0 = time.perf_counter()
        boundary = open_ts + bar_delta
        b_hhmm = boundary.strftime("%H:%M")
        in_window = (boundary.time() >= start_t) and (boundary.time() <= end_t)
        if in_window:
            replayed_bars_count += 1
            if on_progress:
                on_progress(
                    f"Dry run {target_day_str} ({start_hhmm}–{end_hhmm}): Replaying bar {b_hhmm} "
                    f"({b_idx + 1}/{len(bar_opens)}) · {would_count} trade(s) opened"
                )

        # Advance open simulated positions on this bar before evaluating new bar signals
        if sim_open_positions and boundary.time() >= start_t:
            sim_open_positions = _step_open_positions(
                sim_open_positions, sim_closed_trades, stock_bars,
                open_ts, boundary, b_idx, cfg, be_at_r, target_day_str, store,
            )

        n_slice = nifty_5m[nifty_5m.index < boundary]
        if len(n_slice) == 0:
            continue
        nifty_ltp = float(n_slice["close"].iloc[-1])
        nifty_pct = round((nifty_ltp - nifty_pdc) / nifty_pdc * 100.0, 2) if nifty_pdc and nifty_pdc > 0 else None

        prices = {}
        for sym, df in stock_bars.items():
            sub = df[df.index < boundary]
            if len(sub) > 0 and sub.index[-1].date() == target_day:
                prices[sym] = float(sub["close"].iloc[-1])

        adv, dec, breadth = compute_breadth(day_levels, prices)
        regime_res, regime_state = evaluate_regime(n_slice, breadth, cfg, regime_state)
        regime_res["advancers"] = adv
        regime_res["decliners"] = dec
        regime_res["nifty_pct"] = nifty_pct

        sectors = rank_sectors(day_levels, prices, nifty_pct, cfg)
        sec_info = {s["sector"]: s for s in sectors}
        scanner = scan_candidates(regime_res["active"], sectors, day_levels, prices, nifty_pct, cfg)

        if not in_window:
            continue

        bar_events = []
        bar_sigs_sec = []
        bar_sig_rows = []
        bar_passed_cnt = 0
        for sym in scanner["armed"]:
            df = stock_bars.get(sym)
            metrics = prepare_bar_metrics(df, boundary, baseline_sessions=baseline_sessions)
            if metrics is None:
                continue

            row = day_levels[sym]
            s_meta = sec_info.get(row["sector"], {})
            s_rank = int(s_meta.get("rank", 99))
            mark = s_meta.get("mark", "")
            s_bias = 1 if mark == "STRONG" else (-1 if mark == "WEAK" else 0)

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
                traded_today=(sym in traded_syms),
                _held_symbols={p["symbol"] for p in sim_open_positions},
            )

            gate_reason = ""
            if boundary.time() < cfg.no_entry_before:
                gate_reason = f"Before entry window ({cfg.no_entry_before:%H:%M})"
            elif boundary.time() > cfg.no_new_entries_after:
                gate_reason = f"After entry cutoff ({cfg.no_new_entries_after:%H:%M})"

            sig, eval_out = evaluate_strategy_bar(
                strategy, strategy_mod, sym, metrics["bars"], ctx, cfg,
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
            trade_id = None

            if sig is not None and not gate_reason and not eval_out.get("error"):
                qty_calc, _, size_reason = compute_position_size(cfg, metrics["bar_close"], sig.stop_loss)
                if qty_calc <= 0:
                    status = "rejected"
                    qty = 0
                    reason = size_reason
                    rej_count += 1
                else:
                    today_sum_now = summarize_today(
                        cfg, sim_open_positions, sim_closed_trades, {k: {"ltp": v} for k, v in prices.items()}
                    )
                    gate_ok, gate_err = check_entry_gates(
                        cfg, sim_open_positions, today_sum_now, sym, row["sector"], sig.side,
                        entry_px, metrics["bar_close"], float(row["atr"]), traded_syms,
                        None, True, True,
                    )
                    if not gate_ok:
                        status = "rejected"
                        qty = qty_calc
                        reason = gate_err
                        rej_count += 1
                    else:
                        status = "would trade"
                        reason = sig.reason
                        side = sig.side
                        stop_loss = sig.stop_loss
                        target = sig.target
                        qty = qty_calc
                        traded_syms.add(sym)
                        would_count += 1
                        bar_passed_cnt += 1

                        rr_m = compute_rr_metrics(entry_px, stop_loss, target, qty=qty)
                        trade_id = next_trade_id
                        next_trade_id += 1
                        pos_obj = {
                            "id": trade_id,
                            "day": target_day_str,
                            "symbol": sym,
                            "sector": row["sector"],
                            "side": side,
                            "qty": qty,
                            "bar_time": b_hhmm,
                            "order_time": b_hhmm,
                            "entry_bar_idx": b_idx,
                            "entry_price": entry_px,
                            "stop_loss": float(stop_loss),
                            "initial_stop": float(stop_loss),
                            "target": float(target) if target is not None else None,
                            "watermark": entry_px,
                            "best_price": entry_px,
                            "worst_price": entry_px,
                            "max_favorable_r": 0.0,
                            "max_adverse_r": 0.0,
                            "breakeven_moved": False,
                            "breakeven_time": None,
                            "ltp": entry_px,
                            "pnl_rs": 0.0,
                            "r_mult": 0.0,
                            "rr_ratio": rr_m["rr_ratio"],
                            "risk_rs": rr_m["risk_rs"],
                            "reward_rs": rr_m["reward_rs"],
                            "mode": "dryrun",
                            "status": "OPEN",
                        }
                        pos_obj["analysis"] = _build_trade_analysis(pos_obj, None, None, None, 0.0, 0.0, 0.0)
                        sim_open_positions.append(pos_obj)
                        store.add_activity(
                            f"[Dry run {target_day_str}] {b_hhmm} OPENED {side} {sym} x{qty} @ ₹{entry_px:.2f} "
                            f"(SL ₹{stop_loss:.2f}, Tgt {('₹' + format(target, '.2f')) if target else '–'}, "
                            f"R:R {('1:' + format(rr_m['rr_ratio'], '.2f')) if rr_m['rr_ratio'] else '–'})",
                            "good",
                        )
            else:
                status = "rejected"
                if stop_loss:
                    qty, _, _ = compute_position_size(cfg, metrics["bar_close"], stop_loss)
                if gate_reason:
                    reason = gate_reason if sig is not None else f"{gate_reason}; {eval_out.get('reason', '')}".strip("; ")
                else:
                    reason = eval_out.get("reason") or eval_out.get("error") or "Rejected by strategy"
                rej_count += 1

            idx_1 = len(bar_sigs_sec) + 1
            sig_no, sig_full_id = make_signal_ids(target_day_str, b_hhmm, sym, side, idx_1)
            checks = finalize_signal_checks(
                eval_out.get("checks"), cfg, regime_res, s_meta, metrics, row,
                side, qty, gate_reason, status, reason,
            )
            chk_sum = summarize_signal_checks(checks, min_condition_override=eval_out.get("min_condition"))
            rr_m = compute_rr_metrics(entry_px, stop_loss, target, qty=qty)
            bar_ms = int((time.perf_counter() - bar_t0) * 1000)

            sig_row = {
                "day": target_day_str,
                "bar_time": b_hhmm,
                "ready_time": ready_time,
                "symbol": sym,
                "sector": row["sector"],
                "side": side,
                "entry_price": entry_px,
                "stop_loss": stop_loss,
                "target": target,
                "rvol": metrics["rvol"],
                "slot_mult": slot_mult,
                "status": status,
                "reason": reason,
                "mode": "dryrun",
                "qty": qty,
                "scan_id": "",
                "signal_no": sig_no,
                "signal_id": sig_full_id,
                "scan_file": "",
                "duration_ms": bar_ms,
                "checks": checks,
                "rr_ratio": rr_m["rr_ratio"],
                "risk_rs": rr_m["risk_rs"],
                "reward_rs": rr_m["reward_rs"],
                "error": eval_out.get("error"),
                "trade_id": trade_id,
                **chk_sum,
            }
            bar_sig_rows.append(sig_row)
            bar_events.append(f"{sym} {status} ({reason})")
            bar_sigs_sec.append({
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
                "trade_id": trade_id,
                "checks": checks,
                **chk_sum,
            })

        scan_file, scan_id = make_scan_names(
            target_day_str, b_hhmm, len(day_levels), len(bar_sig_rows), bar_passed_cnt
        )
        for sr in bar_sig_rows:
            sr["scan_file"] = scan_file
            sr["scan_id"] = scan_id
            store.add_signal(sr)
            signals_out.append(sr)

        strong = [s["sector"] for s in sectors if s["mark"] == "STRONG"]
        weak = [s["sector"] for s in sectors if s["mark"] == "WEAK"]
        sec_txt = (
            (", ".join(strong) + " strong") if regime_res["active"] == "TREND_UP" and strong
            else (", ".join(weak) + " weak") if regime_res["active"] == "TREND_DOWN" and weak
            else "; ".join(p for p in (
                (", ".join(strong) + " strong") if strong else "",
                (", ".join(weak) + " weak") if weak else "",
            ) if p) or "no strong/weak sectors"
        )
        armed_n = len(scanner["armed"])
        armed_txt = f" ({', '.join(scanner['armed'])})" if armed_n else ""
        last_summary = f"[Dry run {target_day_str}] {b_hhmm} {regime_res['active']}. {sec_txt}. {armed_n} armed{armed_txt}."

        timeline.append({
            "bar_time": b_hhmm,
            "regime": regime_res["active"],
            "nifty_pct": nifty_pct,
            "armed_count": armed_n,
            "signals_count": len(bar_sig_rows),
            "passed_count": bar_passed_cnt,
            "open_positions": len(sim_open_positions),
            "closed_trades": len(sim_closed_trades),
        })

        regime_changed = prev_active is not None and regime_res["active"] != prev_active
        prev_active = regime_res["active"]
        is_last = (b_idx == len(bar_opens) - 1)
        if bar_sigs_sec or is_last:
            bar_ms = int((time.perf_counter() - bar_t0) * 1000)
            doc, idx_entry = build_scan_document(
                cfg,
                day=target_day_str,
                bar_time=b_hhmm,
                checked_at=datetime.now(IST).strftime("%H:%M:%S"),
                duration_ms=bar_ms,
                mode="dryrun",
                universe_total=len(levels_rows),
                regime_res=regime_res,
                sectors=sectors,
                scanner=scanner,
                day_levels=day_levels,
                prices=prices,
                signals_section=bar_sigs_sec,
                strategy_meta=strat_meta,
            )
            last_all_stocks = {r["symbol"]: r for r in doc.get("all_stocks_table", [])}
            scan_docs.append(doc)
            last_s3_key, ok_s3, msg_s3 = save_scan_doc(cfg, doc, idx_entry, update_index=False)
            last_s3_status = "Saved to S3" if ok_s3 else f"Local only ({msg_s3})"
            index_entries.append(idx_entry)

        if regime_changed or bar_events or is_last or b_idx % 6 == 0:
            line = last_summary + (" — " + "; ".join(bar_events) if bar_events else "")
            store.add_activity(line, "good" if any("would trade" in e for e in bar_events) else "info")

        last_mv = {
            "day": target_day_str, "bar_time": b_hhmm, "nifty_pct": nifty_pct,
            "regime": regime_res, "sectors": sectors, "scanner": scanner,
            "stock_reasons": last_all_stocks,
        }

    # Finalize open MTM & today summary for dry run (respecting end_time cutoff)
    last_prices_map = {}
    last_boundary = (bar_opens[-1] + bar_delta) if bar_opens else None
    if last_mv and last_boundary is not None:
        for sym, df in stock_bars.items():
            sub = df[(df.index.date == target_day) & (df.index < last_boundary)]
            if len(sub) > 0:
                last_prices_map[sym] = {"ltp": float(sub["close"].iloc[-1])}
    for pos in sim_open_positions:
        ltp = (last_prices_map.get(pos["symbol"]) or {}).get("ltp") or pos["entry_price"]
        pnl_now, r_now = compute_position_mtm(pos, ltp)
        pos["ltp"] = round(float(ltp), 2)
        pos["pnl_rs"] = pnl_now
        pos["r_mult"] = r_now
        pos["analysis"] = _build_trade_analysis(pos, None, None, None, pnl_now, r_now, 0.0)

    sim_today = summarize_today(cfg, sim_open_positions, sim_closed_trades, last_prices_map)
    all_trades = list(reversed(sim_closed_trades)) + list(sim_open_positions)
    wins = sum(1 for t in sim_closed_trades if float(t.get("net_pnl") or 0) > 0)
    losses = sum(1 for t in sim_closed_trades if float(t.get("net_pnl") or 0) <= 0)
    rr_vals = [float(t["rr_ratio"]) for t in all_trades if t.get("rr_ratio")]
    avg_rr = round(sum(rr_vals) / len(rr_vals), 2) if rr_vals else None
    check_breakdown = compute_check_breakdown(signals_out)

    if index_entries:
        flush_day_index(cfg, target_day_str, index_entries)

    if last_mv:
        store.save_decision(
            target_day_str, last_mv["bar_time"],
            last_mv["regime"], last_mv["sectors"], last_mv["scanner"], last_summary,
        )

    report_card = {
        "strategy_name": strat_meta.get("name"),
        "day": target_day_str,
        "start_time": start_hhmm,
        "end_time": end_hhmm,
        "universe_total": len(levels_rows),
        "prefilter_kept": len(day_levels),
        "bars_replayed": replayed_bars_count,
        "signals_generated": len(signals_out),
        "signals_passed": would_count,
        "signals_rejected": rej_count,
        "trades_executed": len(all_trades),
        "open_trades": len(sim_open_positions),
        "closed_trades": len(sim_closed_trades),
        "wins": wins,
        "losses": losses,
        "win_rate_pct": round(wins / len(sim_closed_trades) * 100.0, 1) if sim_closed_trades else 0.0,
        "realized_pnl": sim_today["realized_pnl"],
        "open_mtm": sim_today["open_mtm"],
        "costs": sim_today["costs"],
        "net_pnl": sim_today["net_pnl"],
        "net_r": sim_today["net_r"],
        "avg_rr_ratio": avg_rr,
    }

    summary = {
        "day": target_day_str,
        "start_time": start_hhmm,
        "end_time": end_hhmm,
        "strategy": strat_meta.get("name"),
        "bars": replayed_bars_count,
        "total_day_bars": len(bar_opens),
        "stocks": len(stock_bars),
        "would_trade": would_count,
        "rejected": rej_count,
        "s3_key": last_s3_key,
        "s3_status": last_s3_status,
        "open_positions": sim_open_positions,
        "closed_trades": list(reversed(sim_closed_trades)),
        "today": sim_today,
        "check_breakdown": check_breakdown,
        "timeline": timeline,
        "report_card": report_card,
    }
    store.add_activity(
        f"Dry run complete for {target_day_str} ({start_hhmm}–{end_hhmm}): {replayed_bars_count} bars, "
        f"{would_count} would trade, {rej_count} rejected | Trades: {len(all_trades)}, Net P&L: ₹{sim_today['net_pnl']:+.2f} ({sim_today['net_r']:+.2f}R). Bars discarded.",
        "good" if sim_today["net_pnl"] > 0 else ("info" if would_count == 0 else "warn"),
    )
    save_activity_s3(cfg, target_day_str, store.feed_newest_first())

    macro_res = None
    if scan_docs:
        try:
            macro_res = generate_and_save_macro_report(
                cfg,
                target_day_str,
                docs=scan_docs,
                activity_items=store.feed_newest_first(),
            )
        except Exception as e:
            macro_res = {"ok": False, "day": target_day_str, "error": f"{type(e).__name__}: {e}"}
    summary["macro_report"] = macro_res

    # Discard all 5m bars from memory (architecture section 11)
    scan_docs.clear()
    del stock_bars, nifty_5m, scan_docs
    gc.collect()

    return summary, last_mv, list(reversed(signals_out))
