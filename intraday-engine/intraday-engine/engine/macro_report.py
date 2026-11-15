"""Dual-format Giant Macro Dry-Run Report compiler & renderer (.md + .pdf).

Triggered only at the end of a Dry Run (never during live market hours).
Compiles all Micro 5-minute scan documents and ACTIVITY items for the testing
window once via `compile_macro_data`, then renders both:
  1. GitHub-Flavored Markdown (.md) via `render_macro_markdown`
  2. Visual A4 Giant PDF (.pdf) via `render_macro_pdf`

Saves copies locally (data/scan_archive/<YYYY-MM-DD>/) and uploads both files
to AWS S3 (`scans/<YYYY-MM-DD>/MACRO_DRYRUN_...md` and `.pdf`), registering them
in `INDEX.json` under `macro_report` and `macro_reports`.
"""
import argparse
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from fpdf import FPDF

from engine.s3_archive import (
    _load_local_index_obj,
    _local_dir,
    _s3_get_json,
    _s3_head_or_get_meta,
    _s3_put_bytes,
    _s3_put_json,
)

IST = ZoneInfo("Asia/Kolkata")


def make_macro_filenames(
    day: str,
    start_hhmm: str,
    end_hhmm: str,
    scan_count: int,
    sig_count: int,
    pass_count: int,
) -> tuple[str, str, str]:
    """Build deterministic Macro base name, Markdown filename, and PDF filename."""
    s_clean = str(start_hhmm or "09:15").replace(":", "-")
    e_clean = str(end_hhmm or "15:30").replace(":", "-")
    base_name = (
        f"MACRO_DRYRUN_{day}_{s_clean}_to_{e_clean}_"
        f"{int(scan_count)}Scans_{int(sig_count)}Signals_{int(pass_count)}Passed"
    )
    return base_name, f"{base_name}.md", f"{base_name}.pdf"


def safe(text: Any) -> str:
    """Convert text to clean Latin-1 ASCII-safe string for standard PDF Helvetica font."""
    if text is None:
        return "-"
    s = str(text)
    repl = {
        "₹": "Rs.",
        "→": "->",
        "←": "<-",
        "↔": "<->",
        "±": "+/-",
        "–": "-",
        "—": "-",
        "−": "-",
        "≥": ">=",
        "≤": "<=",
        "×": "x",
        "•": "*",
        "·": "|",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "…": "...",
        "\u00a0": " ",
    }
    for k, v in repl.items():
        s = s.replace(k, v)
    return s.encode("latin-1", "replace").decode("latin-1")


def _md_cell(val: Any) -> str:
    """Escape pipes and collapse newlines cleanly for Markdown table cells."""
    if val is None:
        return "-"
    s = str(val).strip()
    if not s:
        return "-"
    s = s.replace("|", "\\|").replace("\r\n", "\n").replace("\n", "<br>")
    return s


def _md_table(headers: list[str], rows: list[list[Any]], aligns: list[str] | None = None) -> list[str]:
    """Render a GitHub-Flavored Markdown table from headers and row values."""
    lines = [
        "| " + " | ".join(_md_cell(h) for h in headers) + " |",
    ]
    seps = []
    for i in range(len(headers)):
        al = aligns[i] if aligns and i < len(aligns) else "L"
        if al == "R":
            seps.append("---:")
        elif al == "C":
            seps.append(":---:")
        else:
            seps.append(":---")
    lines.append("| " + " | ".join(seps) + " |")
    for row in rows:
        lines.append("| " + " | ".join(_md_cell(v) for v in row) + " |")
    lines.append("")
    return lines


def describe_regime_why(mc: dict) -> str:
    """Build exact 'Kyun Samjha' explanation from regime.py rules and market_calculation inputs."""
    act = mc.get("regime") or "CHOPPY"
    raw = mc.get("raw_regime") or "CHOPPY"
    adx = mc.get("adx14")
    cr = mc.get("crosses")
    br = mc.get("breadth")
    sm = mc.get("session_mean")

    hits = []
    if adx is not None and adx < 20:
        hits.append(f"ADX {adx}<20")
    if cr is not None and cr >= 4:
        hits.append(f"Cross {cr}>=4")
    if br is not None and 0.80 <= br <= 1.25:
        hits.append(f"Breadth {br:.3f} in 0.80-1.25")
    hit_n = len(hits)

    parts = []
    if hit_n >= 2:
        parts.append(f"{hit_n}/3 Choppy votes ({', '.join(hits)}) -> Raw=CHOPPY.")
    elif raw == "TREND_UP":
        parts.append(
            f"Choppy {hit_n}/3 (<2); NIFTY > SessMean ({sm}) & Breadth {br} > 1.0 -> Raw=TREND_UP."
        )
    elif raw == "TREND_DOWN":
        parts.append(
            f"Choppy {hit_n}/3 (<2); NIFTY < SessMean ({sm}) & Breadth {br} < 1.0 -> Raw=TREND_DOWN."
        )
    else:
        side_hint = (
            f"NIFTY Close bounced above SessMean {sm} while Breadth {br} < 1.0"
            if (br is not None and br < 1.0)
            else f"NIFTY Close slipped below SessMean {sm} while Breadth {br} > 1.0"
        )
        parts.append(f"Choppy {hit_n}/3 (<2), par {side_hint} -> 'else' branch se Raw=CHOPPY.")

    if adx is not None and adx < 20 and raw != "CHOPPY":
        parts.append(f"[Note: ADX={adx}<20 tha, fir bhi TREND mana kyunki 2/3 votes nahi lage]")
    if act != raw:
        parts.append(f"[2-Bar Confirm: Raw {raw} abhi 1st bar pe hai, isliye Active {act} raha]")
    return " ".join(parts)


def describe_sector_why(sec_row: dict, nifty_pct: float | None) -> str:
    """Build exact 'Kyun Samjha' explanation for sector classification."""
    rs = float(sec_row.get("rs_pct") or 0.0)
    ret = float(sec_row.get("return_pct") or 0.0)
    mark = sec_row.get("mark") or "NEUTRAL"
    rank = sec_row.get("rank", "-")
    npct = float(nifty_pct or 0.0)
    if mark == "STRONG":
        return f"Rank #{rank} (Top-3) & RS {rs:+.2f}% > +0.25% (Ret {ret:+.2f}% vs NIFTY {npct:+.2f}%) -> STRONG (LONG allowed)"
    if mark == "WEAK":
        return f"Rank #{rank} (Bottom-3) & RS {rs:+.2f}% < -0.25% (Ret {ret:+.2f}% vs NIFTY {npct:+.2f}%) -> WEAK (SHORT allowed)"
    return f"Rank #{rank}, RS {rs:+.2f}% threshold (+/-0.25%) ya Top-3/Bottom-3 cut ke bahar -> NEUTRAL (Filtered)"


def time_bucket(bar_time: str) -> str:
    """Bucket HH:MM IST timestamps into Morning, Midday, Afternoon, or Post-Close."""
    if bar_time < "11:30":
        return "Morning (09:15 - 11:30)"
    if bar_time < "13:30":
        return "Midday (11:30 - 13:30)"
    if bar_time <= "15:30":
        return "Afternoon (13:30 - 15:30)"
    return "Post-Close (> 15:30)"


def _derive_scans_meta(docs: list[dict], index_scans: list[dict] | None = None) -> list[dict]:
    """Build chronological scan metadata rows from INDEX.json entries or full scan docs."""
    by_bar = {m.get("bar_time"): m for m in (index_scans or []) if m.get("bar_time")}
    meta_rows = []
    for d in docs:
        bt = d.get("bar_time", "-")
        existing = by_bar.get(bt)
        if existing:
            meta_rows.append(existing)
            continue
        fc = d.get("funnel_counts", {})
        sigs = d.get("signals_section", [])
        passed = sum(1 for s in sigs if s.get("status") == "would trade")
        ev = len(sigs)
        meta_rows.append({
            "scan_id": d.get("scan_id", ""),
            "scan_file": d.get("scan_file", "-"),
            "day": d.get("day", ""),
            "bar_time": bt,
            "checked_at": d.get("checked_at", "-"),
            "duration_ms": int(d.get("duration_ms") or 0),
            "mode": d.get("mode", "dryrun"),
            "regime": d.get("market_calculation", {}).get("regime", "-"),
            "kept": int(fc.get("prefilter_kept") or len(d.get("all_stocks_table", []))),
            "armed": int(fc.get("armed") or 0),
            "signals_evaluated": int(fc.get("signals_evaluated", ev)),
            "signals_passed": int(fc.get("signals_passed", passed)),
            "signals_rejected": int(fc.get("signals_rejected", max(0, ev - passed))),
            "symbols": [f"{s.get('signal_no')} ({s.get('status')})" for s in sigs],
        })
    return sorted(meta_rows, key=lambda x: x.get("bar_time", ""))


def compile_macro_data(
    day: str,
    docs: list[dict],
    activity_items: list[dict] | None = None,
    bucket: str = "sunil-trading-signals",
    region: str = "ap-south-2",
    cross_day_note: str = "",
    index_scans: list[dict] | None = None,
) -> dict[str, Any]:
    """Compile all 6 sections of Macro report data from Micro docs and activity log."""
    sorted_docs = sorted(docs, key=lambda d: d.get("bar_time", ""))
    if not sorted_docs:
        raise ValueError(f"No scan documents provided for {day}")

    start_hhmm = sorted_docs[0].get("bar_time", "09:15")
    end_hhmm = sorted_docs[-1].get("bar_time", "15:30")
    scan_count = len(sorted_docs)

    all_signals = []
    for d in sorted_docs:
        for s in d.get("signals_section", []):
            all_signals.append((d.get("bar_time", "-"), d.get("scan_file", "-"), d.get("market_calculation", {}), s))

    sig_count = len(all_signals)
    pass_count = sum(1 for _, _, _, s in all_signals if s.get("status") == "would trade")
    rej_count = sig_count - pass_count

    base_name, md_file, pdf_file = make_macro_filenames(
        day, start_hhmm, end_hhmm, scan_count, sig_count, pass_count
    )

    strat = sorted_docs[-1].get("strategy", {}) or {}
    risk = strat.get("risk", {}) or {}
    params = strat.get("params", {}) or {}
    regimes_list = strat.get("regimes") or ["TREND_UP", "TREND_DOWN"]

    kept_per_scan = int(
        sorted_docs[-1].get("funnel_counts", {}).get("prefilter_kept")
        or len(sorted_docs[-1].get("all_stocks_table", []))
        or 72
    )
    uni_total = int(sorted_docs[-1].get("funnel_counts", {}).get("universe_total") or 104)

    # Section 1: KPIs, Simulated Trade Outcome, Time-of-day, 8-Check Bottleneck
    act_items = activity_items or []
    act_lines_day = [it.get("text", "") for it in act_items if day in str(it.get("text", ""))]
    dry_complete_lines = [t for t in act_lines_day if "Dry run complete" in t]
    trade_lines = [t for t in act_lines_day if ("OPENED" in t or "CLOSED" in t or "breakeven" in t)]

    sim_lines = []
    if trade_lines or dry_complete_lines:
        for t in reversed(trade_lines):
            sim_lines.append(f"Trade Event: {t}")
        for t in dry_complete_lines[:2]:
            sim_lines.append(f"Session Summary Log: {t}")
    else:
        sim_lines.append(
            "Is testing window me 0 signals ne 8/8 checks pass kiye, isliye 0 simulated paper orders open hue (Net P&L: Rs.0.00 / 0.00R)."
        )

    reg_counts = Counter(d.get("market_calculation", {}).get("regime", "-") for d in sorted_docs)
    regimes_observed_str = ", ".join(f"{k}:{v}" for k, v in reg_counts.items())

    buckets = Counter()
    bucket_pass = Counter()
    bucket_scans = Counter()
    for d in sorted_docs:
        tb = time_bucket(d.get("bar_time", ""))
        bucket_scans[tb] += 1
    for bt, _, _, s in all_signals:
        tb = time_bucket(bt)
        buckets[tb] += 1
        if s.get("status") == "would trade":
            bucket_pass[tb] += 1

    tod_order = ["Morning (09:15 - 11:30)", "Midday (11:30 - 13:30)", "Afternoon (13:30 - 15:30)", "Post-Close (> 15:30)"]
    tod_rows = []
    for tb in tod_order:
        sc = bucket_scans.get(tb, 0)
        sg = buckets.get(tb, 0)
        ps = bucket_pass.get(tb, 0)
        rj = sg - ps
        if sc or sg:
            tod_rows.append([tb, str(sc), str(sg), str(ps), str(rj), f"{(ps / sg * 100 if sg else 0):.1f}%"])

    step_stats: dict[int, dict[str, Any]] = {}
    for bt, _, _, s in all_signals:
        for c in s.get("checks", []):
            st = int(c.get("step") or 0)
            ent = step_stats.setdefault(
                st,
                {"step": st, "name": c.get("name", f"Check {st}"), "pass": 0, "fail": 0, "pre_fail": 0, "post_fail": 0},
            )
            if c.get("passed"):
                ent["pass"] += 1
            else:
                ent["fail"] += 1
                if bt <= "14:15":
                    ent["pre_fail"] += 1
                else:
                    ent["post_fail"] += 1

    bottleneck_rows = []
    for st in sorted(step_stats.keys()):
        e = step_stats[st]
        tot = e["pass"] + e["fail"]
        pct = (e["pass"] / tot * 100.0) if tot else 0.0
        if e["fail"] == 0:
            insight = "100% pass - koi rukawat nahi aayi"
            severity = "pass"
        elif pct < 25.0:
            insight = f"MAIN BOTTLENECK ({e['fail']} fails: {e['pre_fail']} <=14:15, {e['post_fail']} >14:15)"
            severity = "fail"
        else:
            insight = f"Moderate filter ({e['fail']} fails: {e['pre_fail']} <=14:15, {e['post_fail']} >14:15)"
            severity = "warn"
        bottleneck_rows.append({
            "step": e["step"],
            "name": e["name"],
            "pass": e["pass"],
            "fail": e["fail"],
            "pct": pct,
            "insight": insight,
            "severity": severity,
        })

    # Section 2: Market Regime Dissection
    low_adx_trend = [
        d for d in sorted_docs
        if (d.get("market_calculation", {}).get("adx14") or 99) < 20
        and d.get("market_calculation", {}).get("regime") != "CHOPPY"
    ]
    mismatch_raw = [
        d for d in sorted_docs
        if d.get("market_calculation", {}).get("regime") != d.get("market_calculation", {}).get("raw_regime")
    ]
    else_choppy = [
        d for d in sorted_docs
        if d.get("market_calculation", {}).get("raw_regime") == "CHOPPY"
        and (
            (1 if (d.get("market_calculation", {}).get("adx14") or 99) < 20 else 0)
            + (1 if (d.get("market_calculation", {}).get("crosses") or 0) >= 4 else 0)
            + (
                1
                if d.get("market_calculation", {}).get("breadth") is not None
                and 0.80 <= d.get("market_calculation", {}).get("breadth") <= 1.25
                else 0
            )
        ) < 2
    ]

    quirk_lines = [
        f"1. Low-ADX Trend Calls: Is period me {len(low_adx_trend)}/{scan_count} scans me ADX(14) < 20 tha, fir bhi engine ne market ko TREND mana (kyunki Crosses < 4 aur Breadth 0.80-1.25 ke bahar tha, so sirf 1/3 choppy vote laga).",
        f"2. Raw vs Active (2-Bar Delay): {len(mismatch_raw)}/{scan_count} scans me Raw Regime Active Regime se alag tha ({', '.join(d['bar_time'] + ' (' + d['market_calculation']['regime'] + ' vs raw ' + d['market_calculation']['raw_regime'] + ')' for d in mismatch_raw) or 'None'}).",
        f"3. 'Else' Branch CHOPPY Triggers: {len(else_choppy)}/{scan_count} scans me Choppy Votes < 2 hone ke bawajood Raw=CHOPPY aaya kyunki NIFTY Close Session Mean ke doosri taraf gaya jabki Breadth alag side thi ({', '.join(d['bar_time'] for d in else_choppy) or 'None'}).",
        "4. Note on Missing Bar Gaps: Jahan 5m bar par 0 stocks ARMED the (ya regime CHOPPY tha), wahan S3 me alag signal-scan JSON save nahi hota (isliye activity feed me unka summary dikhta hai, aur last bar hamesha save hota hai).",
    ]

    reg_rows = []
    for d in sorted_docs:
        mc = d.get("market_calculation", {})
        act = mc.get("regime", "-")
        raw = mc.get("raw_regime", "-")
        npct = mc.get("nifty_pct")
        adx = mc.get("adx14")
        sm = mc.get("session_mean")
        cr = mc.get("crosses")
        br = mc.get("breadth")
        adv = mc.get("advancers")
        dec = mc.get("decliners")
        why = describe_regime_why(mc)
        reg_rows.append({
            "bar_time": d.get("bar_time", "-"),
            "nifty_str": f"{npct:+.2f}%" if npct is not None else "-",
            "adx_str": f"{adx:.2f}" if adx is not None else "-",
            "sm_str": f"{sm:.1f}" if sm is not None else "-",
            "cross_str": str(cr if cr is not None else "-"),
            "breadth_str": f"{br:.3f} ({adv}/{dec})" if br is not None else "-",
            "act": act,
            "raw": raw,
            "kya": f"Active: {act}\n(Raw: {raw})",
            "why": why,
        })

    # Section 3: Sector Rotation Dissection
    sec_freq: dict[str, dict[str, Any]] = {}
    for d in sorted_docs:
        for sr in d.get("sectors_calculation", []):
            nm = sr["sector"]
            e = sec_freq.setdefault(nm, {"STRONG": 0, "WEAK": 0, "NEUTRAL": 0, "rs_list": []})
            mk = sr.get("mark") or "NEUTRAL"
            e[mk] = e.get(mk, 0) + 1
            e["rs_list"].append(float(sr.get("rs_pct") or 0.0))

    sector_summary_rows = []
    for nm, e in sorted(
        sec_freq.items(),
        key=lambda kv: sum(kv[1]["rs_list"]) / max(1, len(kv[1]["rs_list"])),
        reverse=True,
    ):
        rsl = e["rs_list"]
        avg_rs = sum(rsl) / max(1, len(rsl))
        sector_summary_rows.append([
            nm,
            str(e["STRONG"]),
            str(e["WEAK"]),
            str(e["NEUTRAL"]),
            f"{min(rsl):+.2f}% to {max(rsl):+.2f}%" if rsl else "-",
            f"{avg_rs:+.2f}%",
        ])

    pass_docs = [d for d in sorted_docs if any(s.get("status") == "would trade" for s in d.get("signals_section", []))]
    mid_doc = pass_docs[0] if pass_docs else sorted_docs[len(sorted_docs) // 2]
    snap_docs = []
    seen_bt = set()
    for d in [sorted_docs[0], mid_doc, sorted_docs[-1]]:
        bt = d.get("bar_time")
        if bt not in seen_bt:
            seen_bt.add(bt)
            snap_docs.append(d)

    sector_snapshots = []
    for sd in snap_docs:
        npct = sd.get("market_calculation", {}).get("nifty_pct") or 0.0
        reg_act = sd.get("market_calculation", {}).get("regime", "-")
        rows = []
        for sr in sd.get("sectors_calculation", []):
            mk = sr.get("mark") or "NEUTRAL"
            rows.append({
                "rank": f"#{sr.get('rank', '-')}",
                "sector": sr.get("sector", "-"),
                "members": str(sr.get("members", "-")),
                "ret_str": f"{float(sr.get('return_pct') or 0):+.2f}%",
                "rs_str": f"{float(sr.get('rs_pct') or 0):+.2f}%",
                "mark": mk,
                "why": describe_sector_why(sr, npct),
            })
        sector_snapshots.append({
            "bar_time": sd.get("bar_time", "-"),
            "regime": reg_act,
            "nifty_pct": npct,
            "rows": rows,
        })

    # Section 4: Scanner Funnel & 72-Stock Dissection
    focus_doc = sorted_docs[-1]
    if all(r.get("stage") == "REGIME_CHOPPY" for r in focus_doc.get("all_stocks_table", [])) and pass_docs:
        focus_doc = pass_docs[0]
        focus_note = (
            f"Showing active TREND scan @ {focus_doc['bar_time']} "
            f"(kyunki closing scan @ {sorted_docs[-1]['bar_time']} par Regime CHOPPY hone se saare {kept_per_scan} stocks REGIME_CHOPPY stage me the)."
        )
    else:
        focus_note = f"Showing full {kept_per_scan}-stock dissection for closing scan @ {focus_doc['bar_time']} IST."

    arm_freq = Counter()
    short_freq = Counter()
    for d in sorted_docs:
        for r in d.get("all_stocks_table", []):
            if r.get("stage") == "ARMED":
                arm_freq[r["symbol"]] += 1
            elif r.get("stage") == "SHORTLIST":
                short_freq[r["symbol"]] += 1

    top_arm_txt = ", ".join(f"{sym} ({cnt}x)" for sym, cnt in arm_freq.most_common(12)) or "None"
    top_short_txt = ", ".join(f"{sym} ({cnt}x)" for sym, cnt in short_freq.most_common(12)) or "None"
    fc = focus_doc.get("funnel_counts", {})

    stock_rows = []
    for r in focus_doc.get("all_stocks_table", []):
        st = r.get("stage", "-")
        ltp_s = f"{r['ltp']:.2f}" if r.get("ltp") is not None else "-"
        stock_rows.append({
            "try_order": f"#{r.get('try_order', '-')}",
            "symbol": r.get("symbol", "-"),
            "sector": r.get("sector", "-"),
            "sector_mark": r.get("sector_mark", "-"),
            "stage": st,
            "ltp_s": ltp_s,
            "pdh": r.get("pdh", "-"),
            "pdl": r.get("pdl", "-"),
            "atr": r.get("atr", "-"),
            "why_not_taken": r.get("why_not_taken", ""),
            "min_condition": r.get("min_condition", ""),
        })

    # Section 5: Signals
    signal_cards = []
    for s_idx, (bt, sfile, mc, sig) in enumerate(all_signals, 1):
        status = (sig.get("status") or "rejected").upper()
        is_pass = sig.get("status") == "would trade"
        checks = sig.get("checks") or []
        p_cnt = sig.get("passed_checks", sum(1 for c in checks if c.get("passed")))
        t_cnt = sig.get("total_checks", len(checks))
        f_cnt = sig.get("failed_checks", t_cnt - p_cnt)
        rr = sig.get("rr_ratio")
        qty_s = sig.get("qty") if sig.get("qty") is not None else "-"
        sl_s = f"Rs.{sig['stop_loss']:.2f}" if sig.get("stop_loss") is not None else "-"
        tgt_s = f"Rs.{sig['target']:.2f}" if sig.get("target") is not None else "-"
        ent_s = f"Rs.{sig['entry_price']:.2f}" if sig.get("entry_price") is not None else "-"
        rr_part = ""
        if rr is not None and sig.get("risk_rs") is not None and sig.get("reward_rs") is not None:
            rr_part = f" | R:R 1:{rr:.2f} | Risk Rs.{sig['risk_rs']:.0f} -> Reward Rs.{sig['reward_rs']:.0f}"
        if is_pass:
            kya_kyun = f"Kya & Kyun Samjha (PASSED): {sig.get('reason')}"
        else:
            freasons = sig.get("failed_reasons") or [sig.get("reason", "")]
            kya_kyun = f"Kya & Kyun Samjha (FAILED {f_cnt}/{t_cnt}): " + " | ".join(freasons)

        chk_list = []
        for c in checks:
            ok = bool(c.get("passed"))
            why_c = c.get("why_failed") or ("Condition satisfied" if ok else sig.get("reason", "-"))
            chk_list.append({
                "step": f"#{c.get('step')}",
                "name": c.get("name", "-"),
                "passed": ok,
                "result": "PASS" if ok else "FAIL",
                "actual": c.get("actual", "-"),
                "required": c.get("required", "-"),
                "why_failed": why_c if not ok else "-",
            })

        signal_cards.append({
            "idx": s_idx,
            "bar_time": bt,
            "scan_file": sfile,
            "signal_no": sig.get("signal_no", "-"),
            "signal_id": sig.get("signal_id", "-"),
            "symbol": sig.get("symbol", "-"),
            "sector": sig.get("sector", "-"),
            "side": sig.get("side", "-"),
            "status": status,
            "is_pass": is_pass,
            "p_cnt": p_cnt,
            "t_cnt": t_cnt,
            "f_cnt": f_cnt,
            "id_line": f"Full ID: {sig.get('signal_id')}  |  Micro S3 File: scans/{day}/{sfile}",
            "specs_line": (
                f"Order Specs: Qty {qty_s} | Entry {ent_s} | SL {sl_s} | Target {tgt_s}{rr_part} | "
                f"Slot Vol {sig.get('slot_mult', '-')}x | Day RVOL {sig.get('rvol', '-')}x"
            ),
            "kya_kyun_line": kya_kyun,
            "checks": chk_list,
        })

    # Section 6: Micro Inventory
    scans_meta = _derive_scans_meta(sorted_docs, index_scans=index_scans)

    return {
        "day": day,
        "start_hhmm": start_hhmm,
        "end_hhmm": end_hhmm,
        "scan_count": scan_count,
        "sig_count": sig_count,
        "pass_count": pass_count,
        "rej_count": rej_count,
        "kept_per_scan": kept_per_scan,
        "universe_total": uni_total,
        "base_name": base_name,
        "md_file": md_file,
        "pdf_file": pdf_file,
        "bucket": bucket,
        "region": region,
        "cross_day_note": cross_day_note or f"Compiled from {scan_count} Micro 5m S3 scans for {day} ({start_hhmm}-{end_hhmm} IST).",
        "strategy": strat,
        "risk": risk,
        "params": params,
        "regimes_list": regimes_list,
        "has_trade_outcome": bool(trade_lines or dry_complete_lines),
        "sim_lines": sim_lines,
        "regimes_observed_str": regimes_observed_str,
        "tod_rows": tod_rows,
        "bottleneck_rows": bottleneck_rows,
        "quirk_lines": quirk_lines,
        "reg_rows": reg_rows,
        "sector_summary_rows": sector_summary_rows,
        "sector_snapshots": sector_snapshots,
        "focus_bar_time": focus_doc.get("bar_time", "-"),
        "focus_note": focus_note,
        "focus_funnel": fc,
        "top_arm_txt": top_arm_txt,
        "top_short_txt": top_short_txt,
        "stock_rows": stock_rows,
        "signal_cards": signal_cards,
        "scans_meta": scans_meta,
    }


def render_macro_markdown(data: dict[str, Any]) -> str:
    """Render all 6 sections of compiled Macro dry-run data into GitHub-Flavored Markdown."""
    day = data["day"]
    start_hhmm = data["start_hhmm"]
    end_hhmm = data["end_hhmm"]
    scan_count = data["scan_count"]
    sig_count = data["sig_count"]
    pass_count = data["pass_count"]
    rej_count = data["rej_count"]
    kept_n = data["kept_per_scan"]
    strat = data["strategy"]
    risk = data["risk"]
    params = data["params"]

    lines: list[str] = []
    lines.append(f"# AWS S3 MACRO COMPILED DRY-TESTING REPORT — {day} ({start_hhmm} to {end_hhmm} IST)")
    lines.append("")
    lines.append(
        f"> **Mode:** `DRYRUN` | **Testing Date:** `{day}` | **Window:** `{start_hhmm} IST` to `{end_hhmm} IST` | "
        f"**S3 Bucket:** `{data['bucket']}` (`{data['region']}`)"
    )
    lines.append("")

    # Architecture & Strategy Config
    lines.append("## Architecture, File Naming & Strategy Configuration")
    lines.append("")
    lines.append(f"- **Macro PDF File (Compiled):** `scans/{day}/{data['pdf_file']}`")
    lines.append(f"- **Macro Markdown File (Compiled):** `scans/{day}/{data['md_file']}`")
    lines.append(
        f"- **Micro S3 Files (Alag-Alag Har 5m Candle):** `scans/{day}/<HH-MM>_Scan_{kept_n}Stocks_<S>Signals_<P>Passed.json` "
        f"(Total `{scan_count}` Micro JSON files)"
    )
    lines.append(
        "- **Live vs Dry Testing Rule:** Live trading candle-by-candle real time chalta hai, isliye live me sirf Micro files banti hain (Macro nahi). "
        "Dry Testing me poora date + time period replay hota hai, isliye Micro files ke saath ye Macro `.md` + `.pdf` files banti hain."
    )
    lines.append(f"- **Context Note:** {data['cross_day_note']}")
    lines.append("")
    lines.append(
        f"### Strategy: `{strat.get('name', 'pdh_breakout')}` (`{strat.get('file', 'strategies/pdh_breakout.py')}`)"
    )
    lines.append("")
    lines.append(
        f"- **Timeframe / Lookback:** `{strat.get('timeframe', '5m')}` | Lookback `{strat.get('lookback_bars', 50)}` bars | "
        f"Sides `{', '.join(strat.get('sides', ['LONG', 'SHORT']))}` | Active Regimes `{', '.join(data['regimes_list'])}` (`CHOPPY` blocked)"
    )
    lines.append(
        f"- **Strategy Params:** `vwap_filter={params.get('vwap_filter')}`, `buffer_pct={params.get('buffer_pct')}`, "
        f"`vol_mult={params.get('vol_mult')}x`, `rvol_min={params.get('rvol_min')}x`, `max_chase_atr={params.get('max_chase_atr')}`, "
        f"`min_stop_pct={params.get('min_stop_pct')}`, `max_stop_pct={params.get('max_stop_pct')}`, "
        f"`target_r=1:{params.get('target_r')}`, `breakeven_at_r=+{params.get('breakeven_at_r')}R`"
    )
    lines.append(
        f"- **Risk Rules:** Capital `Rs.{risk.get('capital_rs', 50000):,.0f}` | Product `{risk.get('product', 'MIS')}` (`{risk.get('leverage', 5)}x`) | "
        f"Risk/Trade `Rs.{risk.get('risk_per_trade_rs', 500):,.0f}` (Min `Rs.{risk.get('min_achievable_risk_rs', 300):,.0f}`) | "
        f"Notional Cap `Rs.{risk.get('notional_cap_rs', 83333):,.0f}` | Max Open `{risk.get('max_open_positions', 3)}` | "
        f"Max/Sector `{risk.get('max_positions_per_sector', 2)}` | Max/Day `{risk.get('max_trades_per_day', 6)}` | "
        f"Daily Loss Limit `Rs.{risk.get('daily_loss_limit_rs', 1500):,.0f}`"
    )
    lines.append("")

    # Section 1
    lines.append("## 1. Macro Executive Summary & 8-Check Bottleneck Analysis")
    lines.append("")
    kpi_rows = [
        ["Testing Date & Window", f"{day} ({start_hhmm} - {end_hhmm} IST)", "Micro S3 Scans Compiled", f"{scan_count} JSON files ({kept_n} kept stocks/scan)"],
        ["Total Signals Evaluated", f"{sig_count} signals", "Passed (WOULD TRADE)", f"{pass_count} signal(s) ({(pass_count / sig_count * 100 if sig_count else 0):.1f}%)"],
        ["Rejected Signals", f"{rej_count} signals ({(rej_count / sig_count * 100 if sig_count else 0):.1f}%)", "Regimes Observed", data["regimes_observed_str"]],
    ]
    lines.extend(_md_table(["Metric", "Value", "Metric", "Value"], kpi_rows))

    lines.append("### Simulated Trade Execution & Outcome")
    lines.append("")
    for sl in data["sim_lines"]:
        lines.append(f"- {sl}")
    lines.append("")

    if data["tod_rows"]:
        lines.append("### Time-of-Day Breakdown (IST)")
        lines.append("")
        lines.extend(_md_table(
            ["Time Period (IST)", "S3 Scans", "Signals Eval", "Passed", "Rejected", "Pass %"],
            data["tod_rows"],
            aligns=["L", "R", "R", "R", "R", "R"],
        ))

    if data["bottleneck_rows"]:
        lines.append("### 8-Check Bottleneck Analysis (All Signals Combined)")
        lines.append("")
        bn_md_rows = [
            [f"#{r['step']}", r["name"], str(r["pass"]), str(r["fail"]), f"{r['pct']:.1f}%", r["insight"]]
            for r in data["bottleneck_rows"]
        ]
        lines.extend(_md_table(
            ["Step", "Check Name", "Passed", "Failed", "Pass %", "Kya Samjha (Bottleneck Insight)"],
            bn_md_rows,
            aligns=["C", "L", "R", "R", "R", "L"],
        ))

    # Section 2
    lines.append("## 2. Market Regime Dissection — Engine Ne Market Ko 'Kya Samjha' Aur 'Kyun Samjha'")
    lines.append("")
    lines.append("### Box A: Engine Ka Current Formula / Approach (`engine/regime.py` + `config.yaml`)")
    lines.append("")
    lines.append("1. **ADX(14) on 5m NIFTY:** Agar `ADX < 20` ho → Weak Trend / Choppy Vote #1.")
    lines.append("2. **Session Mean & Crosses(12):** Typical Price `(H+L+C)/3` ka expanding mean from `09:15`. Last 12 bars me close `>= 4` baar Session Mean cross kare → Choppy Vote #2.")
    lines.append("3. **Universe Breadth (Adv/Dec vs PDC):** Agar `0.80 <= Breadth <= 1.25` ho → Choppy Vote #3 (`>1.0` Bullish, `<1.0` Bearish).")
    lines.append("4. **Decision Rule:** Agar `>= 2` Choppy Votes lage → `Raw = CHOPPY`. Warna agar `NIFTY Close > Session Mean & Breadth > 1.0` → `Raw = TREND_UP`; agar `NIFTY Close < Session Mean & Breadth < 1.0` → `Raw = TREND_DOWN`; warna (dono disagree karein) → `Raw = CHOPPY`.")
    lines.append("5. **2-Bar Confirmation:** Active Regime tabhi badalta hai jab naya Raw Regime lagatar `2` consecutive 5m bars (`confirm_bars=2`) par aaye.")
    lines.append("")
    lines.append("### Box B: Real Data Se Nikle Key Approach Insights (Baad Me Tune Karne Ke Liye)")
    lines.append("")
    for ql in data["quirk_lines"]:
        lines.append(f"- {ql}")
    lines.append("")

    reg_md_rows = [
        [r["bar_time"], r["nifty_str"], r["adx_str"], r["sm_str"], r["cross_str"], r["breadth_str"], r["kya"], r["why"]]
        for r in data["reg_rows"]
    ]
    lines.extend(_md_table(
        ["Time", "NIFTY%", "ADX14", "SessMean", "Cross", "Breadth (A/D)", "Kya Samjha", "Kyun Samjha (Exact Inputs & Rule)"],
        reg_md_rows,
        aligns=["C", "R", "R", "R", "C", "C", "L", "L"],
    ))

    # Section 3
    lines.append("## 3. Sector Rotation Dissection — Engine Ne Sectors Ko 'Kya Samjha' Aur 'Kyun Samjha'")
    lines.append("")
    lines.append("> `Sector Return % = median(member return vs PDC)` | `RS % = Sector Return % - NIFTY %` | `Top-3 > +0.25% = STRONG`, `Bottom-3 < -0.25% = WEAK`.")
    lines.append("")
    lines.extend(_md_table(
        ["Sector (Eligible)", "STRONG Scans", "WEAK Scans", "NEUTRAL Scans", "RS % Range (Period)", "Avg RS %"],
        data["sector_summary_rows"],
        aligns=["L", "R", "R", "R", "C", "R"],
    ))

    for snap in data["sector_snapshots"]:
        lines.append(f"### Sector Snapshot @ {snap['bar_time']} IST | Regime: `{snap['regime']}` | NIFTY: `{snap['nifty_pct']:+.2f}%`")
        lines.append("")
        snap_md_rows = [
            [r["rank"], r["sector"], r["members"], r["ret_str"], r["rs_str"], r["mark"], r["why"]]
            for r in snap["rows"]
        ]
        lines.extend(_md_table(
            ["Rank", "Sector", "Stocks", "Med Ret%", "RS %", "Kya Samjha", "Kyun Samjha (RS Formula & Cut)"],
            snap_md_rows,
            aligns=["C", "L", "R", "R", "R", "C", "L"],
        ))

    # Section 4
    lines.append(f"## 4. Scanner Funnel & Complete {kept_n}-Stock Dissection ('Kya Samjha' & 'Kyun Samjha')")
    lines.append("")
    lines.append(f"> {data['focus_note']}")
    lines.append("")
    fc = data["focus_funnel"]
    lines.append(
        f"- **Funnel @ {data['focus_bar_time']}:** Universe `{fc.get('universe_total', data['universe_total'])}` -> "
        f"Kept `{fc.get('prefilter_kept', kept_n)}` (Dropped `{fc.get('prefilter_dropped', 0)}`) -> "
        f"Sector Filtered `{fc.get('sector_filtered', 0)}` -> Far (>0.5 ATR) `{fc.get('far_from_level', 0)}` -> "
        f"Outside Top-5 `{fc.get('near_level', 0)}` -> Shortlisted `{fc.get('shortlisted', 0)}` -> "
        f"Armed `{fc.get('armed', 0)}` -> Evaluated `{fc.get('signals_evaluated', 0)}` (`{fc.get('signals_passed', 0)}` Passed)"
    )
    lines.append(f"- **Most Frequently ARMED Stocks ({scan_count} Scans):** {data['top_arm_txt']}")
    lines.append(f"- **Most Frequently SHORTLISTED (Near Arm) Stocks:** {data['top_short_txt']}")
    lines.append("")

    stock_md_rows = []
    for r in data["stock_rows"]:
        stock_md_rows.append([
            r["try_order"],
            f"{r['symbol']}\n({r['sector']}: {r['sector_mark']})",
            r["stage"],
            f"LTP: {r['ltp_s']}\nPDH: {r['pdh']}\nPDL: {r['pdl']}\nATR: {r['atr']}",
            f"{r['why_not_taken']}\n[Min Cond: {r['min_condition']}]",
        ])
    lines.extend(_md_table(
        ["Try#", "Symbol (Sector)", "Stage (Kya)", "Levels (Rs.)", "Kyun Samjha (Why Taken / Why Not Taken) + Min Condition"],
        stock_md_rows,
        aligns=["C", "L", "C", "L", "L"],
    ))

    # Section 5
    lines.append(f"## 5. Complete Chronological Signal-by-Signal Dissection (All {sig_count} Signals)")
    lines.append("")
    if not data["signal_cards"]:
        lines.append("_Is testing window me 0 signals evaluate hue._")
        lines.append("")
    else:
        for sc in data["signal_cards"]:
            lines.append(
                f"### [{sc['idx']}/{sig_count}] {sc['signal_no']} ({sc['symbol']} | {sc['sector']} | {sc['side']}) "
                f"— **{sc['status']}** ({sc['p_cnt']}/{sc['t_cnt']} Pass, {sc['f_cnt']} Fail)"
            )
            lines.append("")
            lines.append(f"- {sc['id_line']}")
            lines.append(f"- {sc['specs_line']}")
            lines.append(f"- **{sc['kya_kyun_line']}**")
            lines.append("")
            chk_md_rows = [
                [c["step"], c["name"], c["result"], c["actual"], c["required"], c["why_failed"]]
                for c in sc["checks"]
            ]
            lines.extend(_md_table(
                ["#", "Check", "Result", "Actual", "Minimum Required", "Why Failed"],
                chk_md_rows,
                aligns=["C", "L", "C", "L", "L", "L"],
            ))

    # Section 6
    lines.append(f"## 6. Complete AWS S3 Micro Scan File Inventory ({scan_count} Compiled Micro Files)")
    lines.append("")
    inv_md_rows = []
    for m in data["scans_meta"]:
        ps = int(m.get("signals_passed") or 0)
        ev = int(m.get("signals_evaluated") or 0)
        syms = ", ".join(m.get("symbols") or []) or "-"
        inv_md_rows.append([
            m.get("bar_time", "-"),
            m.get("scan_file", "-"),
            m.get("checked_at", "-"),
            f"{m.get('duration_ms', 0)} ms",
            m.get("regime", "-"),
            str(m.get("armed", 0)),
            f"{ev} ({ps}P / {m.get('signals_rejected', 0)}R)",
            syms,
        ])
    lines.extend(_md_table(
        ["Bar", "Micro S3 File Name", "Checked", "Speed", "Regime", "Arm", "Eval (P/R)", "Evaluated Signals"],
        inv_md_rows,
        aligns=["C", "L", "C", "R", "L", "R", "C", "L"],
    ))
    return "\n".join(lines)


class MacroReportPDF(FPDF):
    """A4 PDF layout helper with repeating table headers, safe wrapping, and color-coded boxes."""

    def __init__(self, day: str, start_hhmm: str, end_hhmm: str, scan_count: int, sig_count: int, pass_count: int, bucket: str, region: str):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.day = day
        self.start_hhmm = start_hhmm
        self.end_hhmm = end_hhmm
        self.scan_count = scan_count
        self.sig_count = sig_count
        self.pass_count = pass_count
        self.bucket = bucket
        self.region = region
        self.set_margins(12, 14, 12)
        self.set_auto_page_break(auto=True, margin=14)
        self.alias_nb_pages()

    def header(self):
        if self.page_no() == 1:
            return
        self.set_y(6)
        self.set_font("helvetica", "B", 7.5)
        self.set_text_color(70, 82, 100)
        self.cell(
            0, 4,
            safe(
                f"AWS S3 MACRO COMPILED DRY-TEST REPORT | Date: {self.day} | "
                f"Window: {self.start_hhmm} - {self.end_hhmm} IST | "
                f"{self.scan_count} Scans, {self.sig_count} Signals, {self.pass_count} Passed"
            ),
            border=0, ln=1, align="L",
        )
        self.set_draw_color(205, 214, 226)
        self.line(12, 11, 198, 11)
        self.set_y(13.5)

    def footer(self):
        self.set_y(-10.5)
        self.set_draw_color(210, 218, 228)
        self.line(12, self.get_y(), 198, self.get_y())
        self.set_font("helvetica", "", 7.5)
        self.set_text_color(100, 110, 125)
        self.cell(
            130, 5,
            safe(f"S3 Bucket: {self.bucket} ({self.region}) | Mode: DRYRUN Macro Compiled | Micro JSONs kept separate"),
            border=0, align="L",
        )
        self.cell(0, 5, safe(f"Page {self.page_no()} / {{nb}}"), border=0, align="R")

    def section_banner(self, num: str, title: str, subtitle: str = ""):
        if self.get_y() > 235:
            self.add_page()
        self.ln(2)
        self.set_fill_color(22, 44, 80)
        self.set_text_color(255, 255, 255)
        self.set_font("helvetica", "B", 10.5)
        self.cell(0, 7.5, safe(f"  {num}. {title}"), border=0, ln=1, fill=True)
        if subtitle:
            self.set_fill_color(238, 243, 250)
            self.set_text_color(45, 58, 78)
            self.set_font("helvetica", "I", 8)
            self.multi_cell(0, 4.5, safe(f"  {subtitle}"), border="LRB", fill=True)
        self.ln(2)

    def info_box(self, title: str, lines: list[str], fill=(244, 247, 252), border_col=(185, 198, 218), title_col=(22, 44, 80)):
        w = 186
        self.set_font("helvetica", "B", 8.5)
        est_h = 7.0
        self.set_font("helvetica", "", 8)
        for ln in lines:
            wrapped = self.multi_cell(w - 6, 4.2, safe(ln), dry_run=True, output="LINES")
            est_h += max(1, len(wrapped)) * 4.2 + 0.6
        if self.get_y() + est_h > 280:
            self.add_page()
        y0 = self.get_y()
        self.set_fill_color(*fill)
        self.set_draw_color(*border_col)
        self.rect(12, y0, w, est_h + 2, style="DF")
        self.set_xy(15, y0 + 1.8)
        self.set_font("helvetica", "B", 8.5)
        self.set_text_color(*title_col)
        self.cell(w - 6, 4.8, safe(title), ln=1)
        self.set_font("helvetica", "", 8)
        self.set_text_color(35, 42, 54)
        for ln in lines:
            self.set_x(15)
            self.multi_cell(w - 6, 4.2, safe(ln))
            self.set_y(self.get_y() + 0.5)
        self.set_y(y0 + est_h + 4)

    def draw_table(self, headers: list[str], widths: list[float], rows: list[list], aligns: list[str] | None = None, font_size: float = 7.2, row_colors: list | None = None):
        """Draw a multi-line wrapping table with consistent row heights and page-break header repeat."""
        assert abs(sum(widths) - 186.0) < 0.2, f"Widths sum {sum(widths)} != 186"
        line_h = 3.8 if font_size <= 7.2 else 4.2

        def _draw_hdr():
            self.set_fill_color(32, 58, 98)
            self.set_text_color(255, 255, 255)
            self.set_draw_color(190, 200, 215)
            self.set_font("helvetica", "B", font_size)
            y_h = self.get_y()
            max_lines = 1
            hdr_lines = []
            for h_txt, cw in zip(headers, widths):
                ls = self.multi_cell(cw - 2, line_h, safe(h_txt), dry_run=True, output="LINES")
                hdr_lines.append(ls)
                max_lines = max(max_lines, len(ls))
            rh = max_lines * line_h + 2.2
            x = 12.0
            for ls, cw in zip(hdr_lines, widths):
                self.rect(x, y_h, cw, rh, style="DF")
                self.set_xy(x + 1, y_h + 1.1)
                self.multi_cell(cw - 2, line_h, "\n".join(ls), align="L")
                x += cw
            self.set_y(y_h + rh)

        if self.get_y() + 14 > 280:
            self.add_page()
        _draw_hdr()

        for idx, row in enumerate(rows):
            self.set_font("helvetica", "", font_size)
            cell_lines = []
            max_lines = 1
            for val, cw in zip(row, widths):
                ls = self.multi_cell(cw - 2, line_h, safe(val), dry_run=True, output="LINES")
                if not ls:
                    ls = [""]
                cell_lines.append(ls)
                max_lines = max(max_lines, len(ls))
            rh = max_lines * line_h + 2.0
            if self.get_y() + rh > 281:
                self.add_page()
                _draw_hdr()
                self.set_font("helvetica", "", font_size)

            y_r = self.get_y()
            if row_colors and row_colors[idx] is not None:
                bg = row_colors[idx]
            else:
                bg = (248, 250, 253) if idx % 2 == 1 else (255, 255, 255)

            x = 12.0
            self.set_draw_color(214, 221, 232)
            for c_idx, (ls, cw) in enumerate(zip(cell_lines, widths)):
                self.set_fill_color(*bg)
                self.rect(x, y_r, cw, rh, style="DF")
                self.set_text_color(30, 36, 46)
                al = aligns[c_idx] if aligns and c_idx < len(aligns) else "L"
                self.set_xy(x + 1, y_r + 1.0)
                self.multi_cell(cw - 2, line_h, "\n".join(ls), align=al)
                x += cw
            self.set_y(y_r + rh)
        self.ln(2.5)


def render_macro_pdf(data: dict[str, Any]) -> bytes:
    """Render compiled Macro dry-run data into a visual A4 PDF and return raw PDF bytes."""
    day = data["day"]
    start_hhmm = data["start_hhmm"]
    end_hhmm = data["end_hhmm"]
    scan_count = data["scan_count"]
    sig_count = data["sig_count"]
    pass_count = data["pass_count"]
    rej_count = data["rej_count"]
    kept_n = data["kept_per_scan"]
    strat = data["strategy"]
    risk = data["risk"]
    params = data["params"]

    pdf = MacroReportPDF(
        day, start_hhmm, end_hhmm, scan_count, sig_count, pass_count,
        data["bucket"], data["region"],
    )
    pdf.add_page()

    # Cover banner
    pdf.set_fill_color(18, 36, 66)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("helvetica", "B", 14)
    pdf.cell(0, 10, safe("  AWS S3 MACRO COMPILED DRY-TESTING REPORT (GIANT PDF)"), ln=1, fill=True)

    pdf.set_fill_color(34, 62, 106)
    pdf.set_font("helvetica", "B", 9.5)
    pdf.cell(
        0, 6.5,
        safe(f"  Testing Date: {day}  |  Testing Time Period: {start_hhmm} IST to {end_hhmm} IST  |  Mode: DRYRUN"),
        ln=1, fill=True,
    )
    pdf.ln(3)

    pdf.info_box(
        "Macro vs Micro Architecture & File Naming Convention (Sirf Dry Testing me Macro PDF + MD)",
        [
            f"Macro PDF File Name (Compiled): {data['pdf_file']}",
            f"Macro S3 Keys (PDF & MD): scans/{day}/{data['pdf_file']}  |  scans/{day}/{data['md_file']}",
            f"Micro S3 Files (Alag-Alag Har 5m Candle): scans/{day}/<HH-MM>_Scan_{kept_n}Stocks_<S>Signals_<P>Passed.json (Total {scan_count} Micro files in S3)",
            "Live vs Dry Testing Rule: Live trading candle-by-candle real time chalta hai, isliye live me sirf Micro files banti hain (Macro nahi). Dry Testing me poora date + time period replay hota hai, isliye Micro files ke saath ye Macro .md + .pdf files banti hain.",
            f"Data Source: AWS S3 Bucket '{data['bucket']}' ({data['region']}) | Context: {data['cross_day_note']}",
        ],
        fill=(238, 244, 252), border_col=(140, 165, 205),
    )

    pdf.info_box(
        f"Loaded Strategy & Risk Configuration: {strat.get('name', 'pdh_breakout')} ({strat.get('file', 'strategies/pdh_breakout.py')})",
        [
            f"Timeframe: {strat.get('timeframe', '5m')} | Lookback: {strat.get('lookback_bars', 50)} bars | Sides: {', '.join(strat.get('sides', ['LONG', 'SHORT']))} | Active Regimes: {', '.join(data['regimes_list'])} (CHOPPY blocked)",
            f"Strategy Params: vwap_filter={params.get('vwap_filter')} | buffer_pct={params.get('buffer_pct')} (0.1%) | vol_mult={params.get('vol_mult')}x (5d slot avg) | rvol_min={params.get('rvol_min')}x | max_chase_atr={params.get('max_chase_atr')} | min_stop={params.get('min_stop_pct')} (0.6%) | max_stop={params.get('max_stop_pct')} (1.5%) | target_r=1:{params.get('target_r')} | breakeven_at=+{params.get('breakeven_at_r')}R",
            f"Risk Rules: Capital Rs.{risk.get('capital_rs', 50000):,.0f} | Product {risk.get('product', 'MIS')} ({risk.get('leverage', 5)}x) | Risk/Trade Rs.{risk.get('risk_per_trade_rs', 500):,.0f} (Min Rs.{risk.get('min_achievable_risk_rs', 300):,.0f}) | Notional Cap Rs.{risk.get('notional_cap_rs', 83333):,.0f} | Max Open {risk.get('max_open_positions', 3)} | Max/Sector {risk.get('max_positions_per_sector', 2)} | Max/Day {risk.get('max_trades_per_day', 6)} | Daily Loss Limit Rs.{risk.get('daily_loss_limit_rs', 1500):,.0f}",
        ],
        fill=(248, 250, 253), border_col=(200, 210, 224),
    )

    # Section 1
    pdf.section_banner(
        "1",
        "Macro Executive Summary & 8-Check Bottleneck Analysis",
        f"Poore testing period ({start_hhmm} to {end_hhmm}) me total signals, time-of-day stats, simulated P&L aur har filter ka pass/fail breakdown",
    )

    kpi_rows = [
        ["Testing Date & Window", f"{day} ({start_hhmm} - {end_hhmm} IST)", "Micro S3 Scans Compiled", f"{scan_count} JSON files ({kept_n} kept stocks/scan)"],
        ["Total Signals Evaluated", f"{sig_count} signals", "Passed (WOULD TRADE)", f"{pass_count} signal(s) ({(pass_count / sig_count * 100 if sig_count else 0):.1f}%)"],
        ["Rejected Signals", f"{rej_count} signals ({(rej_count / sig_count * 100 if sig_count else 0):.1f}%)", "Regimes Observed", data["regimes_observed_str"]],
    ]
    pdf.draw_table(["Metric", "Value", "Metric", "Value"], [42.0, 51.0, 42.0, 51.0], kpi_rows, font_size=7.6)

    pdf.info_box(
        "Simulated Trade Execution & Outcome (From AWS S3 ACTIVITY.json)" if data["has_trade_outcome"] else "Simulated Trade Execution & Outcome",
        data["sim_lines"],
        fill=(255, 248, 232) if pass_count > 0 else (246, 248, 252),
        border_col=(215, 175, 95) if pass_count > 0 else (195, 205, 220),
    )

    if data["tod_rows"]:
        pdf.draw_table(
            ["Time Period (IST)", "S3 Scans", "Signals Eval", "Passed", "Rejected", "Pass %"],
            [56.0, 22.0, 28.0, 24.0, 28.0, 28.0],
            data["tod_rows"],
            aligns=["L", "R", "R", "R", "R", "R"],
            font_size=7.6,
        )

    if data["bottleneck_rows"]:
        bn_rows = []
        bn_colors = []
        for r in data["bottleneck_rows"]:
            bn_rows.append([f"#{r['step']}", r["name"], str(r["pass"]), str(r["fail"]), f"{r['pct']:.1f}%", r["insight"]])
            if r["severity"] == "pass":
                bn_colors.append((236, 248, 239))
            elif r["severity"] == "fail":
                bn_colors.append((253, 238, 238))
            else:
                bn_colors.append((255, 248, 230))
        pdf.draw_table(
            ["Step", "Check Name", "Passed", "Failed", "Pass %", "Kya Samjha (Bottleneck Insight)"],
            [12.0, 40.0, 16.0, 16.0, 16.0, 86.0],
            bn_rows,
            aligns=["C", "L", "R", "R", "R", "L"],
            font_size=7.4,
            row_colors=bn_colors,
        )

    # Section 2
    pdf.section_banner(
        "2",
        "Market Regime Dissection - Engine Ne Market Ko 'Kya Samjha' Aur 'Kyun Samjha'",
        "NIFTY 5m ADX(14), Session Mean, Crosses(12), Universe Breadth aur 2-Bar Confirmation ka poora hisab",
    )

    pdf.info_box(
        "Box A: Engine Ka Current Formula / Approach (engine/regime.py + config.yaml)",
        [
            "Input 1 - ADX(14) on 5m NIFTY: Agar ADX < 20 ho -> Weak Trend / Choppy Vote #1.",
            "Input 2 - Session Mean & Crosses(12): Typical Price (H+L+C)/3 ka expanding mean from 09:15. Last 12 bars me close >= 4 baar Session Mean cross kare -> Choppy Vote #2.",
            "Input 3 - Universe Breadth (Adv/Dec vs PDC): Agar 0.80 <= Breadth <= 1.25 ho -> Choppy Vote #3. (>1.0 Bullish, <1.0 Bearish).",
            "Decision Rule: Agar >= 2 Choppy Votes lage -> Raw = CHOPPY. Warna agar NIFTY Close > Session Mean & Breadth > 1.0 -> Raw = TREND_UP; agar NIFTY Close < Session Mean & Breadth < 1.0 -> Raw = TREND_DOWN; warna (dono disagree karein) -> Raw = CHOPPY.",
            "2-Bar Confirmation: Active Regime tabhi badalta hai jab naya Raw Regime lagatar 2 consecutive 5m bars (confirm_bars=2) par aaye.",
        ],
        fill=(242, 246, 252), border_col=(165, 185, 215),
    )

    pdf.info_box(
        "Box B: Real AWS Data Se Nikle Key Approach Insights (Baad Me Tune Karne Ke Liye)",
        data["quirk_lines"],
        fill=(255, 248, 232), border_col=(215, 175, 95), title_col=(135, 80, 10),
    )

    reg_table_rows = []
    reg_colors = []
    for r in data["reg_rows"]:
        reg_table_rows.append([
            r["bar_time"], r["nifty_str"], r["adx_str"], r["sm_str"], r["cross_str"], r["breadth_str"], r["kya"], r["why"],
        ])
        if r["act"] != r["raw"]:
            reg_colors.append((255, 246, 224))
        elif r["act"] == "CHOPPY":
            reg_colors.append((244, 244, 248))
        elif r["act"] == "TREND_UP":
            reg_colors.append((238, 249, 241))
        else:
            reg_colors.append((253, 242, 242))

    pdf.draw_table(
        ["Time", "NIFTY%", "ADX14", "SessMean", "Cross", "Breadth (A/D)", "Kya Samjha", "Kyun Samjha (Exact Inputs & Rule)"],
        [12.0, 14.0, 13.0, 17.0, 11.0, 24.0, 26.0, 69.0],
        reg_table_rows,
        aligns=["C", "R", "R", "R", "C", "C", "L", "L"],
        font_size=6.8,
        row_colors=reg_colors,
    )

    # Section 3
    pdf.section_banner(
        "3",
        "Sector Rotation Dissection - Engine Ne 9 Sectors Ko 'Kya Samjha' Aur 'Kyun Samjha'",
        "Sector Return % = median(member return vs PDC) | RS % = Sector Return % - NIFTY % | Top-3 > +0.25% = STRONG, Bottom-3 < -0.25% = WEAK",
    )

    pdf.draw_table(
        ["Sector (Eligible)", "STRONG Scans", "WEAK Scans", "NEUTRAL Scans", "RS % Range (Period)", "Avg RS %"],
        [44.0, 26.0, 26.0, 28.0, 38.0, 24.0],
        data["sector_summary_rows"],
        aligns=["L", "R", "R", "R", "C", "R"],
        font_size=7.4,
    )

    for snap in data["sector_snapshots"]:
        pdf.set_font("helvetica", "B", 8.5)
        pdf.set_text_color(22, 44, 80)
        pdf.cell(0, 5.5, safe(f"Sector Snapshot @ {snap['bar_time']} IST | Regime: {snap['regime']} | NIFTY: {snap['nifty_pct']:+.2f}%"), ln=1)
        s_rows = []
        s_cols = []
        for r in snap["rows"]:
            mk = r["mark"]
            s_rows.append([r["rank"], r["sector"], r["members"], r["ret_str"], r["rs_str"], mk, r["why"]])
            if mk == "STRONG":
                s_cols.append((236, 248, 239))
            elif mk == "WEAK":
                s_cols.append((253, 238, 238))
            else:
                s_cols.append((247, 248, 250))
        pdf.draw_table(
            ["Rank", "Sector", "Stocks", "Med Ret%", "RS %", "Kya Samjha", "Kyun Samjha (RS Formula & Cut)"],
            [11.0, 24.0, 14.0, 17.0, 15.0, 20.0, 85.0],
            s_rows,
            aligns=["C", "L", "R", "R", "R", "C", "L"],
            font_size=7.0,
            row_colors=s_cols,
        )

    # Section 4
    pdf.section_banner(
        "4",
        f"Scanner Funnel & Complete {kept_n}-Stock Dissection ('Kya Samjha' & 'Kyun Samjha')",
        f"{data['universe_total']} Universe -> {kept_n} Kept -> Allowed Sector -> Proximity <= 0.5 ATR -> Top-5 Z-Score -> Armed (0.1%). {data['focus_note']}",
    )

    fc = data["focus_funnel"]
    pdf.info_box(
        f"{kept_n}-Stock Funnel Summary @ {data['focus_bar_time']} & Whole-Period Armed Leaderboard",
        [
            f"Funnel @ {data['focus_bar_time']}: Universe {fc.get('universe_total', data['universe_total'])} -> Kept {fc.get('prefilter_kept', kept_n)} (Dropped {fc.get('prefilter_dropped', 0)}) -> Sector Filtered {fc.get('sector_filtered', 0)} -> Far (>0.5 ATR) {fc.get('far_from_level', 0)} -> Outside Top-5 {fc.get('near_level', 0)} -> Shortlisted {fc.get('shortlisted', 0)} -> Armed {fc.get('armed', 0)} -> Evaluated {fc.get('signals_evaluated', 0)} ({fc.get('signals_passed', 0)} Passed)",
            f"Most Frequently ARMED Stocks (Across {scan_count} Scans): {data['top_arm_txt']}",
            f"Most Frequently SHORTLISTED (Near Arm) Stocks: {data['top_short_txt']}",
        ],
        fill=(242, 246, 252), border_col=(165, 185, 215),
    )

    all_rows = []
    all_cols = []
    for r in data["stock_rows"]:
        st = r["stage"]
        levels_s = f"LTP: {r['ltp_s']}\nPDH: {r['pdh']}\nPDL: {r['pdl']}\nATR: {r['atr']}"
        sym_sec = f"{r['symbol']}\n({r['sector']}: {r['sector_mark']})"
        why_txt = f"{r['why_not_taken']}\n[Min Cond: {r['min_condition']}]"
        all_rows.append([r["try_order"], sym_sec, st, levels_s, why_txt])
        if st == "ARMED":
            all_cols.append((255, 244, 224))
        elif st == "SHORTLIST":
            all_cols.append((238, 246, 255))
        elif st == "OUTSIDE_TOP5":
            all_cols.append((245, 249, 245))
        else:
            all_cols.append(None)

    pdf.draw_table(
        ["Try#", "Symbol (Sector)", "Stage (Kya)", "Levels (Rs.)", "Kyun Samjha (Why Taken / Why Not Taken) + Min Condition"],
        [10.0, 31.0, 29.0, 26.0, 90.0],
        all_rows,
        aligns=["C", "L", "C", "L", "L"],
        font_size=6.5,
        row_colors=all_cols,
    )

    # Section 5
    pdf.add_page()
    pdf.section_banner(
        "5",
        f"Complete Chronological Signal-by-Signal Dissection (All {sig_count} Signals)",
        f"Testing period ({start_hhmm} - {end_hhmm}) me evaluate hua har signal: Order Specs, Exact Failure/Pass Reasons, aur 8/8 Checks",
    )

    if not data["signal_cards"]:
        pdf.info_box(
            "Signal Evaluations",
            ["Is testing window me 0 signals evaluate hue."],
            fill=(246, 248, 252), border_col=(195, 205, 220),
        )
    else:
        col_ws = [8.0, 29.0, 12.0, 42.0, 43.0, 52.0]
        for sc in data["signal_cards"]:
            summary_lines = [sc["id_line"], sc["specs_line"], sc["kya_kyun_line"]]
            chk_rows = []
            chk_cols = []
            for c in sc["checks"]:
                chk_rows.append([c["step"], c["name"], c["result"], c["actual"], c["required"], c["why_failed"]])
                chk_cols.append((240, 250, 242) if c["passed"] else (254, 236, 236))

            est_h = 14.0
            pdf.set_font("helvetica", "", 7.2)
            for line_txt in summary_lines:
                est_h += max(1, len(pdf.multi_cell(184, 4.0, safe(line_txt), dry_run=True, output="LINES"))) * 4.0
            pdf.set_font("helvetica", "", 6.5)
            for cr_row in chk_rows:
                ml = 1
                for val, cw in zip(cr_row, col_ws):
                    ml = max(ml, len(pdf.multi_cell(cw - 2, 3.8, safe(val), dry_run=True, output="LINES")))
                est_h += ml * 3.8 + 2.0
            if pdf.get_y() + est_h > 280 and pdf.get_y() > 25:
                pdf.add_page()

            hdr_fill = (20, 120, 55) if sc["is_pass"] else (155, 36, 36)
            pdf.set_fill_color(*hdr_fill)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("helvetica", "B", 8.2)
            pdf.cell(
                0, 6.0,
                safe(
                    f"  [{sc['idx']}/{sig_count}] {sc['signal_no']} ({sc['symbol']} | {sc['sector']} | {sc['side']}) "
                    f"- {sc['status']} ({sc['p_cnt']}/{sc['t_cnt']} Pass, {sc['f_cnt']} Fail)"
                ),
                ln=1, fill=True,
            )

            sub_fill = (236, 248, 239) if sc["is_pass"] else (253, 242, 242)
            pdf.set_fill_color(*sub_fill)
            pdf.set_text_color(30, 36, 46)
            pdf.set_draw_color(200, 210, 222)
            pdf.set_font("helvetica", "", 7.2)
            for line_txt in summary_lines:
                pdf.set_x(12)
                pdf.multi_cell(186, 4.0, safe(line_txt), border="LR", fill=True)

            pdf.draw_table(
                ["#", "Check", "Result", "Actual", "Minimum Required", "Why Failed"],
                col_ws,
                chk_rows,
                aligns=["C", "L", "C", "L", "L", "L"],
                font_size=6.5,
                row_colors=chk_cols,
            )

    # Section 6
    pdf.add_page()
    pdf.section_banner(
        "6",
        f"Complete AWS S3 Micro Scan File Inventory ({scan_count} Compiled Micro Files)",
        f"Ye saari alag-alag Micro JSON files AWS S3 folder scans/{day}/ me safe hain, aur upar unhi ka Macro compilation hai",
    )

    inv_rows = []
    inv_cols = []
    for m in data["scans_meta"]:
        ps = int(m.get("signals_passed") or 0)
        ev = int(m.get("signals_evaluated") or 0)
        syms = ", ".join(m.get("symbols") or []) or "-"
        inv_rows.append([
            m.get("bar_time", "-"),
            m.get("scan_file", "-"),
            m.get("checked_at", "-"),
            f"{m.get('duration_ms', 0)} ms",
            m.get("regime", "-"),
            str(m.get("armed", 0)),
            f"{ev} ({ps}P / {m.get('signals_rejected', 0)}R)",
            syms,
        ])
        if ps > 0:
            inv_cols.append((232, 248, 236))
        elif ev > 0:
            inv_cols.append((255, 250, 245))
        else:
            inv_cols.append((245, 246, 250))

    pdf.draw_table(
        ["Bar", "Micro S3 File Name", "Checked", "Speed", "Regime", "Arm", "Eval (P/R)", "Evaluated Signals"],
        [11.0, 52.0, 14.0, 12.0, 21.0, 9.0, 18.0, 49.0],
        inv_rows,
        aligns=["C", "L", "C", "R", "L", "R", "C", "L"],
        font_size=6.4,
        row_colors=inv_cols,
    )

    data["pdf_pages"] = pdf.page_no()
    return bytes(pdf.output())


def _load_json_file(path: Path) -> dict | None:
    if path.exists():
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass
    return None


def _load_day_inputs(
    cfg,
    day: str,
    cache_dir: Path | None = None,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Load Micro scan docs, INDEX scans list, and ACTIVITY items from cache/local/S3."""
    ldir = _local_dir(cfg, day)
    cdir = (cache_dir / day) if cache_dir else None

    idx_obj = None
    if cdir:
        idx_obj = _load_json_file(cdir / "INDEX.json")
    if idx_obj is None:
        s3_idx, _ = _s3_get_json(cfg, f"scans/{day}/INDEX.json")
        if isinstance(s3_idx, dict):
            idx_obj = s3_idx
    if idx_obj is None:
        idx_obj = _load_local_index_obj(ldir / "INDEX.json")

    scans_meta = sorted(idx_obj.get("scans", []) if isinstance(idx_obj, dict) else [], key=lambda x: x.get("bar_time", ""))

    docs: list[dict] = []
    for m in scans_meta:
        sf = m.get("scan_file")
        if not sf:
            continue
        doc = _load_json_file(cdir / sf) if cdir else None
        if doc is None:
            doc = _load_json_file(ldir / sf)
        if doc is None:
            doc, _ = _s3_get_json(cfg, f"scans/{day}/{sf}")
        if isinstance(doc, dict):
            docs.append(doc)

    # Also fallback to scanning local JSONs if INDEX.json was absent
    if not docs:
        for p in sorted(ldir.glob("*_Scan_*.json")):
            doc = _load_json_file(p)
            if doc:
                docs.append(doc)

    act_obj = _load_json_file(cdir / "ACTIVITY.json") if cdir else None
    if act_obj is None:
        act_obj, _ = _s3_get_json(cfg, f"scans/{day}/ACTIVITY.json")
    act_items = act_obj.get("items", []) if isinstance(act_obj, dict) else []
    return docs, scans_meta, act_items


def generate_and_save_macro_report(
    cfg,
    day: str,
    docs: list[dict] | None = None,
    activity_items: list[dict] | None = None,
    cache_dir: Path | None = None,
    extra_out_dir: Path | None = None,
    cross_day_note: str = "",
) -> dict[str, Any]:
    """Compile Dry-Run data, render .md + .pdf, save locally + upload to S3, and update INDEX.json."""
    index_scans: list[dict] | None = None
    if docs is None:
        docs, index_scans, fetched_act = _load_day_inputs(cfg, day, cache_dir=cache_dir)
        if activity_items is None:
            activity_items = fetched_act
    elif activity_items is None:
        _, _, activity_items = _load_day_inputs(cfg, day, cache_dir=cache_dir)

    if not docs:
        return {"ok": False, "day": day, "error": f"No scan documents found for {day}"}

    data = compile_macro_data(
        day=day,
        docs=docs,
        activity_items=activity_items,
        bucket=cfg.s3_bucket or "sunil-trading-signals",
        region=cfg.s3_region or "ap-south-2",
        cross_day_note=cross_day_note,
        index_scans=index_scans,
    )

    md_bytes = render_macro_markdown(data).encode("utf-8")
    pdf_bytes = render_macro_pdf(data)

    md_file = data["md_file"]
    pdf_file = data["pdf_file"]
    ldir = _local_dir(cfg, day)
    local_md_path = ldir / md_file
    local_pdf_path = ldir / pdf_file
    local_md_path.write_bytes(md_bytes)
    local_pdf_path.write_bytes(pdf_bytes)

    if extra_out_dir is not None:
        edir = Path(extra_out_dir)
        edir.mkdir(parents=True, exist_ok=True)
        (edir / md_file).write_bytes(md_bytes)
        (edir / pdf_file).write_bytes(pdf_bytes)

    md_s3_key = f"scans/{day}/{md_file}"
    pdf_s3_key = f"scans/{day}/{pdf_file}"
    ok_md, msg_md = _s3_put_bytes(cfg, md_s3_key, md_bytes, content_type="text/markdown; charset=utf-8", timeout=25)
    ok_pdf, msg_pdf = _s3_put_bytes(cfg, pdf_s3_key, pdf_bytes, content_type="application/pdf", timeout=30)

    # Load existing INDEX.json (prefer S3 so micro scan entries stay authoritative, then local/cache)
    idx_path = ldir / "INDEX.json"
    s3_idx, _ = _s3_get_json(cfg, f"scans/{day}/INDEX.json")
    prev_idx = s3_idx if isinstance(s3_idx, dict) else _load_local_index_obj(idx_path)
    if (not prev_idx or not prev_idx.get("scans")) and cache_dir:
        cached_idx = _load_json_file(Path(cache_dir) / day / "INDEX.json")
        if cached_idx:
            prev_idx = cached_idx

    scans_list = prev_idx.get("scans", []) if isinstance(prev_idx.get("scans"), list) else []
    if not scans_list:
        scans_list = list(reversed(data["scans_meta"]))

    macro_entry = {
        "base_name": data["base_name"],
        "md_file": md_file,
        "pdf_file": pdf_file,
        "md_s3_key": md_s3_key,
        "pdf_s3_key": pdf_s3_key,
        "md_size_bytes": len(md_bytes),
        "pdf_size_bytes": len(pdf_bytes),
        "pdf_pages": data.get("pdf_pages", 0),
        "ok_md_s3": ok_md,
        "ok_pdf_s3": ok_pdf,
        "start_time": data["start_hhmm"],
        "end_time": data["end_hhmm"],
        "scans_count": data["scan_count"],
        "signals_count": data["sig_count"],
        "passed_count": data["pass_count"],
        "generated_at": datetime.now(IST).isoformat(),
    }

    existing_macros = prev_idx.get("macro_reports", []) if isinstance(prev_idx.get("macro_reports"), list) else []
    deduped = [macro_entry] + [
        m for m in existing_macros
        if isinstance(m, dict) and m.get("base_name") != macro_entry["base_name"]
    ]
    idx_obj = {
        "day": day,
        "bucket": cfg.s3_bucket,
        "region": cfg.s3_region,
        "scans": scans_list,
        "macro_report": macro_entry,
        "macro_reports": deduped,
    }
    idx_path.write_text(json.dumps(idx_obj, ensure_ascii=False), encoding="utf-8")
    ok_idx, msg_idx = _s3_put_json(cfg, f"scans/{day}/INDEX.json", idx_obj)

    return {
        "ok": ok_md and ok_pdf,
        "day": day,
        "base_name": data["base_name"],
        "md_file": md_file,
        "pdf_file": pdf_file,
        "md_s3_key": md_s3_key,
        "pdf_s3_key": pdf_s3_key,
        "ok_md": ok_md,
        "msg_md": msg_md,
        "ok_pdf": ok_pdf,
        "msg_pdf": msg_pdf,
        "ok_index": ok_idx,
        "msg_index": msg_idx,
        "md_size_bytes": len(md_bytes),
        "pdf_size_bytes": len(pdf_bytes),
        "pdf_pages": data.get("pdf_pages", 0),
        "local_md_path": str(local_md_path),
        "local_pdf_path": str(local_pdf_path),
    }


def _main():
    from engine.config import load_config

    parser = argparse.ArgumentParser(description="Generate & upload Macro Dry-Run reports (.md + .pdf) to AWS S3.")
    parser.add_argument("--days", nargs="+", default=["2026-11-13", "2026-11-11"], help="Dates (YYYY-MM-DD) to process.")
    parser.add_argument("--cache-dir", type=Path, default=None, help="Optional cached Micro JSON folder.")
    parser.add_argument("--out-dir", type=Path, default=None, help="Optional extra folder to copy .md and .pdf outputs.")
    parser.add_argument("--verify", action="store_true", help="Verify uploaded S3 objects via HEAD and INDEX.json GET.")
    args = parser.parse_args()

    cfg = load_config()
    cross_notes = {
        "2026-11-13": "2026-11-11 (22 scans, 56 signals, 1 WOULD TRADE: 12:05 BHARATFORG LONG) bhi separate Giant Macro PDF + MD me compiled hai.",
        "2026-11-11": "2026-11-13 (52 scans, 101 signals, 0 WOULD TRADE) bhi separate Giant Macro PDF + MD me compiled hai.",
    }

    for day in args.days:
        res = generate_and_save_macro_report(
            cfg,
            day=day,
            cache_dir=args.cache_dir,
            extra_out_dir=args.out_dir,
            cross_day_note=cross_notes.get(day, ""),
        )
        print(json.dumps(res, indent=2))
        if args.verify and res.get("ok"):
            h_md = _s3_head_or_get_meta(cfg, res["md_s3_key"])
            h_pdf = _s3_head_or_get_meta(cfg, res["pdf_s3_key"])
            idx_doc, idx_msg = _s3_get_json(cfg, f"scans/{day}/INDEX.json")
            macro_meta = (idx_doc or {}).get("macro_report")
            print(f"[VERIFY {day}] HEAD MD:  {h_md}")
            print(f"[VERIFY {day}] HEAD PDF: {h_pdf}")
            print(f"[VERIFY {day}] S3 INDEX macro_report ({idx_msg}): {json.dumps(macro_meta)}")


if __name__ == "__main__":
    _main()
