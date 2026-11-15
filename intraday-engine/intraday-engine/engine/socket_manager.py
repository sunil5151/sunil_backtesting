"""Strategy Socket Manager: upfront rules/parameters, qualification suite, OpenRouter AI check, plug/unplug/upload."""
import ast
from datetime import datetime, timedelta
import json
from pathlib import Path
import re
import urllib.error
import urllib.request

import pandas as pd

from core.strategy_loader import load_strategy

from engine.bars import Context, compute_rr_metrics, load_strategy_plug
from engine.config import save_openrouter_env, save_strategy_config
from engine.oa import IST

DEFAULT_AI_MODEL = "GLM 5.3 Flash"
OPENROUTER_MODEL_ALIASES = {
    "glm 5.3 flash": "z-ai/glm-5.3-flash",
    "glm-5.3-flash": "z-ai/glm-5.3-flash",
}

QUALIFICATION_CODE_SNIPPET = '''# Engine Qualification Test Harness (runs automatically on Upload / Plug / Verify)
# 1. AST Syntax & Safety: No direct OpenAlgo order APIs (placeorder/closeposition) or time.sleep().
# 2. Metadata Check: NAME, TIMEFRAME, MARKET_TYPE, REGIMES, SIDES, PARAMS, CHECKS_SCHEMA.
# 3. Transparent Contract: Strategy.evaluate_signal(symbol, bars, ctx) -> {passed, signal, checks, rr_ratio, error}
# 4. Choppy Market Test: Pass synthetic 5m bars with ctx.regime = "CHOPPY".
#    - If "CHOPPY" not in REGIMES -> strategy must block trade (signal is None).
#    - If "CHOPPY" in REGIMES     -> strategy must handle CHOPPY cleanly without crashing.
# 5. Trending Market Test: Pass TREND_UP breakout & TREND_DOWN breakdown 5m bars.
#    - Verify LONG / SHORT signal generation or transparent ctx.record_rejection / checks[].
# 6. Risk-to-Reward (R:R) Check: Mandatory stop_loss > 0, valid target, R:R = |target-entry| / |entry-stop|.
# Note: SOFT GATE — Even if a check fails/warns, engine shows full report and still lets you run it.'''

STARTER_STRATEGY_TEMPLATE = '''"""Custom Intraday Strategy Template for intraday-engine Strategy Socket."""
from engine.bars import Signal, StrategyChecklistEvaluator

NAME = "my_custom_strategy"
TIMEFRAME = "5m"
LOOKBACK_BARS = 50
MARKET_TYPE = "NSE_INTRADAY_EQUITY"
REGIMES = ("TREND_UP", "TREND_DOWN")   # Add "CHOPPY" if your strategy trades range/choppy markets
SIDES = ("LONG", "SHORT")
CHOPPY_TREATMENT = "Blocks all new entries when ctx.regime == 'CHOPPY'."
TRENDING_TREATMENT = "TREND_UP -> LONG above PDH; TREND_DOWN -> SHORT below PDL."

PARAMS = {
    "vol_mult": 1.2,
    "rvol_min": 1.0,
    "min_stop_pct": 0.006,
    "target_r": 2.0,
}

CHECKS_SCHEMA = [
    {"step": 1, "name": "Market Regime", "required": "TREND_UP or TREND_DOWN", "code": "ctx.regime in ('TREND_UP', 'TREND_DOWN')"},
    {"step": 2, "name": "Breakout Level", "required": "Close > ctx.pdh (LONG) or < ctx.pdl (SHORT)", "code": "close > ctx.pdh"},
    {"step": 3, "name": "VWAP Filter", "required": "Close on trend side of ctx.vwap", "code": "close > ctx.vwap"},
    {"step": 4, "name": "Volume & RVOL", "required": "5m Vol > vol_mult * slot_avg and RVOL >= rvol_min", "code": "vol > vol_mult * ctx.slot_volume_avg"},
]


class Strategy:
    def __init__(self, params: dict):
        self.params = dict(PARAMS)
        if params:
            self.params.update(params)

    def evaluate_signal(self, symbol: str, bars, ctx) -> dict:
        p = self.params
        ev = StrategyChecklistEvaluator(NAME)
        side = "LONG" if ctx.regime == "TREND_UP" else ("SHORT" if ctx.regime == "TREND_DOWN" else "LONG")

        ev.add_rule(
            1, "Market Regime", ctx.regime in ("TREND_UP", "TREND_DOWN"),
            ctx.regime, "TREND_UP / TREND_DOWN",
            f"Market Regime '{ctx.regime}' hai; trend strategy sirf TREND_UP/TREND_DOWN me trade leti hai.",
        )
        if bars is None or len(bars) == 0:
            ev.add_rule(2, "5m Bars", False, "0 bars", ">= 1 bar", "No 5m bars available")
            return ev.result(side=side, entry_price=ctx.ltp or 0.0, stop_loss=None, target=None)

        last = bars.iloc[-1]
        close, high, low, vol = float(last["close"]), float(last["high"]), float(last["low"]), float(last["volume"])
        if side == "LONG":
            stop = min(low * 0.9995, close * (1.0 - p["min_stop_pct"]))
            target = close + p["target_r"] * (close - stop)
            brk_ok = close > ctx.pdh
            vwap_ok = close > ctx.vwap
        else:
            stop = max(high * 1.0005, close * (1.0 + p["min_stop_pct"]))
            target = close - p["target_r"] * (stop - close)
            brk_ok = close < ctx.pdl
            vwap_ok = close < ctx.vwap

        ev.add_rule(2, "Breakout Level", brk_ok, f"Close {close:.2f}", f"PDH {ctx.pdh:.2f} / PDL {ctx.pdl:.2f}", f"Close {close:.2f} ne level cross nahi kiya.")
        ev.add_rule(3, "VWAP Filter", vwap_ok, f"Close {close:.2f} vs VWAP {ctx.vwap:.2f}", "Trend side of VWAP", "Close VWAP ke galat side tha.")
        slot_avg = float(ctx.slot_volume_avg or 0.0)
        vol_ok = slot_avg > 0 and vol > p["vol_mult"] * slot_avg and ctx.rvol >= p["rvol_min"]
        ev.add_rule(4, "Volume & RVOL", vol_ok, f"Vol {int(vol)}, Avg {int(slot_avg)}, RVOL {ctx.rvol:.2f}x", f">{p['vol_mult']}x slot & RVOL>={p['rvol_min']}", "Volume ya RVOL minimum threshold se kam tha.")

        res = ev.result(side=side, entry_price=close, stop_loss=stop, target=target)
        if not res["passed"]:
            ctx.record_rejection(side, stop, target, res["reason"])
        return res

    def on_bar(self, symbol: str, bars, ctx):
        if ctx.regime not in ("TREND_UP", "TREND_DOWN"):
            return None
        return self.evaluate_signal(symbol, bars, ctx)["signal"]
'''

AI_BUILDER_PROMPT = """Build or verify an intraday Python strategy for the intraday-engine Strategy Socket.

1. DATA SCOPE PROVIDED BY ENGINE:
   - Universe: ~72 liquid NSE stocks (pre-filtered from 104 stocks: Price Rs 100-5000, 20d Avg Value >= Rs 50 Cr, ATR% >= 1.2%).
   - Daily levels: 20 trading days (PDH, PDL, PDC, 14-day Daily ATR).
   - Intraday bars (`bars` DataFrame): Last 5 trading sessions + today's closed 5-minute OHLCV candles (~375-450 rows; columns: open, high, low, close, volume; IST index).

2. ALL 18 CONTEXT PARAMETERS AVAILABLE ON `ctx`:
   - `ctx.now` (IST datetime), `ctx.regime` ("TREND_UP" | "TREND_DOWN" | "CHOPPY")
   - `ctx.sector` (str), `ctx.sector_rank` (int, 1=strongest), `ctx.sector_bias` (+1 STRONG / -1 WEAK / 0 NEUTRAL)
   - `ctx.pdh`, `ctx.pdl`, `ctx.pdc` (Previous Day High/Low/Close), `ctx.vwap` (today's session VWAP), `ctx.atr` (Daily ATR 14)
   - `ctx.day_open`, `ctx.day_high`, `ctx.day_low`, `ctx.ltp`
   - `ctx.slot_volume_avg` (5-day same 5m time-slot average volume), `ctx.rvol` (cumulative RVOL)
   - `ctx.traded_today` (bool), `ctx.has_position(symbol)` (bool)

3. REQUIRED MODULE METADATA & TRANSPARENT RETURN CONTRACT:
   - Declare: NAME, TIMEFRAME="5m", MARKET_TYPE="NSE_INTRADAY_EQUITY", REGIMES=("TREND_UP", "TREND_DOWN"), CHOPPY_TREATMENT, TRENDING_TREATMENT, SIDES, PARAMS, CHECKS_SCHEMA.
   - Implement `Strategy.evaluate_signal(self, symbol, bars, ctx) -> dict` using `from engine.bars import Signal, StrategyChecklistEvaluator`.
   - Evaluate EVERY rule (do NOT early-return before checking remaining rules) so `checks`, `passed_checks`, `failed_checks`, `total_checks`, and `rr_ratio` are 100% transparent.
   - Always include mandatory `stop_loss` and `target` (clear Risk-to-Reward, e.g. 1:2.0). Never call OpenAlgo order APIs or sleep/file-write inside strategy code.
   - Keep `on_bar(self, symbol, bars, ctx)` calling `evaluate_signal(symbol, bars, ctx)["signal"]`.
"""

CTX_PARAMETERS_DOC = [
    {"name": "ctx.now", "type": "datetime", "desc": "Bar close IST datetime (e.g. 2026-11-11 10:25:00)"},
    {"name": "ctx.regime", "type": "str", "desc": "'TREND_UP', 'TREND_DOWN', or 'CHOPPY' (NIFTY 2-bar confirmed)"},
    {"name": "ctx.sector", "type": "str", "desc": "Stock sector name (e.g. 'Metal', 'Auto', 'Bank')"},
    {"name": "ctx.sector_rank", "type": "int", "desc": "Sector rank vs NIFTY today (1 = strongest)"},
    {"name": "ctx.sector_bias", "type": "int", "desc": "+1 (STRONG), -1 (WEAK), 0 (NEUTRAL)"},
    {"name": "ctx.pdh / pdl / pdc", "type": "float", "desc": "Previous Day High, Low, and Close (Rs)"},
    {"name": "ctx.vwap", "type": "float", "desc": "Stock intraday session VWAP from today's 5m bars (Rs)"},
    {"name": "ctx.atr", "type": "float", "desc": "14-day Daily Average True Range (Rs)"},
    {"name": "ctx.day_open / high / low", "type": "float", "desc": "Today's session open, high, and low (Rs)"},
    {"name": "ctx.slot_volume_avg", "type": "float", "desc": "5-day average volume for this exact 5m time slot"},
    {"name": "ctx.rvol", "type": "float", "desc": "Cumulative Relative Volume vs 5-session average at this time"},
    {"name": "ctx.ltp", "type": "float", "desc": "Latest traded price (Rs)"},
    {"name": "ctx.traded_today", "type": "bool", "desc": "True if symbol was already signaled/traded today"},
    {"name": "ctx.has_position(sym)", "type": "bool", "desc": "True if engine already holds an open position in sym"},
]


def _resolve_model_slug(model_name: str | None) -> str:
    m = (model_name or DEFAULT_AI_MODEL).strip()
    if not m:
        m = DEFAULT_AI_MODEL
    return OPENROUTER_MODEL_ALIASES.get(m.lower(), m)


def _strategies_dir(cfg) -> Path:
    d = cfg.root / "strategies"
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_strategies(cfg) -> list[dict]:
    """List all .py strategy files in strategies/ with basic metadata."""
    sdir = _strategies_dir(cfg)
    active_rel = str(cfg.strategy_file or "").replace("\\", "/").strip()
    out = []
    for p in sorted(sdir.glob("*.py")):
        if p.name.startswith("__"):
            continue
        rel = f"strategies/{p.name}"
        meta = {"file": rel, "filename": p.name, "name": p.stem, "active": rel == active_rel, "builtin": p.name in ("pdh_breakout.py", "orb_breakout.py")}
        try:
            src = p.read_text(encoding="utf-8-sig")
            tree = ast.parse(src)
            for node in tree.body:
                if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                    k = node.targets[0].id
                    if k in ("NAME", "MARKET_TYPE", "TIMEFRAME"):
                        try:
                            meta[k.lower()] = ast.literal_eval(node.value)
                        except Exception:
                            pass
            meta["lines"] = len(src.splitlines())
        except Exception:
            meta["lines"] = 0
        out.append(meta)
    return out


def _make_synthetic_bars(mode: str) -> tuple[pd.DataFrame, Context]:
    """Create 6 sessions of synthetic 5m OHLCV bars for qualification testing."""
    base_day = datetime(2026, 11, 11, 9, 15, tzinfo=IST)
    rows = []
    idx = []
    for d_off in range(-5, 1):
        day_dt = base_day + timedelta(days=d_off)
        n_bars = 75 if d_off < 0 else 18   # today up to 10:45
        for b in range(n_bars):
            ts = day_dt + timedelta(minutes=5 * b)
            px = 98.5 + (0.01 * b)
            vol = 1000.0
            if d_off == 0 and b == n_bars - 1:
                if mode == "TREND_UP":
                    rows.append((100.1, 101.4, 99.9, 101.2, 3200.0))
                elif mode == "TREND_DOWN":
                    rows.append((94.9, 95.1, 93.6, 93.8, 3200.0))
                elif mode == "CHOPPY":
                    rows.append((100.1, 101.4, 99.9, 101.2, 3200.0))
                else:  # LOW_VOL_REJECT
                    rows.append((100.1, 100.8, 99.9, 100.5, 250.0))
            else:
                rows.append((px, px + 0.4, px - 0.4, px + 0.1, vol))
            idx.append(ts)
    df = pd.DataFrame(rows, index=pd.DatetimeIndex(idx), columns=["open", "high", "low", "close", "volume"])
    last_ts = idx[-1] + timedelta(minutes=5)
    if mode == "TREND_UP":
        ctx = Context(
            now=last_ts, regime="TREND_UP", sector="Metal", sector_rank=1, sector_bias=1,
            pdh=100.0, pdl=95.0, pdc=99.0, vwap=99.5, atr=2.8,
            day_open=99.2, day_high=101.4, day_low=98.5,
            slot_volume_avg=1000.0, rvol=1.8, ltp=101.2, traded_today=False,
        )
    elif mode == "TREND_DOWN":
        ctx = Context(
            now=last_ts, regime="TREND_DOWN", sector="Metal", sector_rank=8, sector_bias=-1,
            pdh=100.0, pdl=95.0, pdc=96.0, vwap=95.4, atr=2.8,
            day_open=95.6, day_high=96.2, day_low=93.6,
            slot_volume_avg=1000.0, rvol=1.8, ltp=93.8, traded_today=False,
        )
    elif mode == "CHOPPY":
        ctx = Context(
            now=last_ts, regime="CHOPPY", sector="Metal", sector_rank=1, sector_bias=1,
            pdh=100.0, pdl=95.0, pdc=99.0, vwap=99.5, atr=2.8,
            day_open=99.2, day_high=101.4, day_low=98.5,
            slot_volume_avg=1000.0, rvol=1.8, ltp=101.2, traded_today=False,
        )
    else:
        ctx = Context(
            now=last_ts, regime="TREND_UP", sector="Metal", sector_rank=1, sector_bias=1,
            pdh=100.0, pdl=95.0, pdc=99.0, vwap=99.5, atr=2.8,
            day_open=99.2, day_high=100.8, day_low=98.5,
            slot_volume_avg=1000.0, rvol=0.4, ltp=100.5, traded_today=False,
        )
    return df, ctx


def _extract_ast_checks(src: str) -> list[dict]:
    """Static AST scan to find declared CHECKS_SCHEMA or if-conditions inside strategy."""
    gates = []
    try:
        tree = ast.parse(src)
    except Exception:
        return gates
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            try:
                cond_txt = ast.unparse(node.test)
            except Exception:
                cond_txt = "condition"
            if len(cond_txt) > 90:
                cond_txt = cond_txt[:87] + "..."
            gates.append({"line": getattr(node, "lineno", 0), "code": cond_txt})
    return gates[:25]


def qualify_strategy_file(cfg, file_rel_path: str | None) -> dict:
    """Run 6-point qualification suite (Syntax, Metadata, Contract, Choppy, Trending, R:R) with Soft Gate."""
    if not file_rel_path or str(file_rel_path).strip().lower() in ("", "none", "unplugged"):
        return {
            "file": "",
            "name": "unplugged",
            "can_use": False,
            "status": "SOCKET EMPTY (UNPLUGGED)",
            "passed_count": 0,
            "failed_count": 0,
            "total_count": 0,
            "checks": [],
            "strategy_checks": [],
            "ast_gates": [],
            "summary": "No strategy is currently plugged into the socket.",
        }

    p = (cfg.root / file_rel_path).resolve()
    if not p.exists():
        return {
            "file": file_rel_path,
            "name": Path(file_rel_path).stem,
            "can_use": False,
            "status": "FILE NOT FOUND",
            "passed_count": 0,
            "failed_count": 1,
            "total_count": 1,
            "checks": [{"step": 1, "name": "Strategy File Exists", "passed": False, "actual": "Missing", "required": str(p), "why_failed": "File not found"}],
            "strategy_checks": [],
            "ast_gates": [],
            "summary": f"Strategy file missing: {file_rel_path}",
        }

    src = p.read_text(encoding="utf-8-sig")
    q_checks = []

    # 1. Syntax & Safety
    syntax_ok = True
    syntax_err = ""
    forbidden_hits = []
    try:
        ast.parse(src)
        for bad in ("placeorder", "placesmartorder", "closeposition", "cancelorder", "time.sleep("):
            if bad in src:
                forbidden_hits.append(bad)
    except SyntaxError as e:
        syntax_ok = False
        syntax_err = f"Line {e.lineno}: {e.msg}"

    c1_ok = syntax_ok and not forbidden_hits
    q_checks.append({
        "step": 1,
        "name": "Syntax & Socket Safety",
        "passed": c1_ok,
        "actual": "Clean Python AST" if c1_ok else (syntax_err or f"Forbidden calls: {', '.join(forbidden_hits)}"),
        "required": "Valid Python, no direct broker order APIs or sleep()",
        "why_failed": "" if c1_ok else (syntax_err or f"Direct broker/sleep calls found: {', '.join(forbidden_hits)}"),
    })

    if not syntax_ok:
        return {
            "file": file_rel_path, "name": p.stem, "can_use": True,
            "status": "WARNING (Soft Gate — Syntax Error Detected)",
            "passed_count": 0, "failed_count": 1, "total_count": 1,
            "checks": q_checks, "strategy_checks": [], "ast_gates": [],
            "summary": f"Syntax error in {file_rel_path}: {syntax_err}",
        }

    ast_gates = _extract_ast_checks(src)

    # Load module
    try:
        mod = load_strategy(p)
        params = dict(getattr(mod, "PARAMS", {}))
        strat = mod.Strategy(params)
    except Exception as e:
        q_checks.append({
            "step": 2, "name": "Strategy Class Load", "passed": False,
            "actual": f"{type(e).__name__}: {e}", "required": "Class Strategy(params) instantiates cleanly",
            "why_failed": f"Could not load Strategy class: {e}",
        })
        return {
            "file": file_rel_path, "name": p.stem, "can_use": True,
            "status": "WARNING (Soft Gate — Load Failed)",
            "passed_count": sum(1 for c in q_checks if c["passed"]),
            "failed_count": sum(1 for c in q_checks if not c["passed"]),
            "total_count": len(q_checks),
            "checks": q_checks, "strategy_checks": [], "ast_gates": ast_gates,
            "summary": f"Load failed: {e}",
        }

    name = str(getattr(mod, "NAME", p.stem))
    market_type = getattr(mod, "MARKET_TYPE", None)
    regimes = getattr(mod, "REGIMES", None)
    timeframe = getattr(mod, "TIMEFRAME", None)
    sides = getattr(mod, "SIDES", None)
    choppy_txt = getattr(mod, "CHOPPY_TREATMENT", None)
    trending_txt = getattr(mod, "TRENDING_TREATMENT", None)

    # 2. Market Type & Regime Declaration
    c2_ok = bool(market_type and regimes and timeframe and sides)
    q_checks.append({
        "step": 2,
        "name": "Market Type & Regimes Metadata",
        "passed": c2_ok,
        "actual": f"Market={market_type or 'MISSING'}, Regimes={regimes or 'MISSING'}, TF={timeframe or 'MISSING'}",
        "required": "Declare NAME, TIMEFRAME, MARKET_TYPE, REGIMES, SIDES",
        "why_failed": "" if c2_ok else "Missing MARKET_TYPE, REGIMES, TIMEFRAME, or SIDES constant(s).",
    })

    # 3. Transparent Check Function
    has_eval = callable(getattr(strat, "evaluate_signal", None))
    has_on_bar = callable(getattr(strat, "on_bar", None))
    c3_ok = has_eval
    q_checks.append({
        "step": 3,
        "name": "Transparent Checklist Contract",
        "passed": c3_ok,
        "actual": "evaluate_signal() + on_bar()" if (has_eval and has_on_bar) else ("on_bar() only" if has_on_bar else "Missing"),
        "required": "evaluate_signal(symbol, bars, ctx) returning checks[]",
        "why_failed": "" if c3_ok else "evaluate_signal() missing — engine will wrap on_bar() with basic 4-check telemetry.",
    })

    # Helper to invoke strategy on synthetic test data
    def _run_case(mode_key: str):
        df, ctx = _make_synthetic_bars(mode_key)
        if has_eval:
            out = strat.evaluate_signal("TESTSYM", df, ctx)
            return out.get("signal"), out
        sig_res = strat.on_bar("TESTSYM", df, ctx)
        return sig_res, {"signal": sig_res, "checks": [], "reason": (ctx.rejected or {}).get("reason", "")}

    # 4. Choppy Market Treatment Test
    regimes_norm = tuple(str(r).upper() for r in (regimes or ("TREND_UP", "TREND_DOWN")))
    allows_choppy = "CHOPPY" in regimes_norm
    choppy_err = ""
    choppy_sig = None
    try:
        choppy_sig, _ = _run_case("CHOPPY")
        if not allows_choppy and choppy_sig is not None:
            c4_ok = False
            choppy_err = f"Trend strategy took a {choppy_sig.side} trade during CHOPPY regime!"
        else:
            c4_ok = True
    except Exception as e:
        c4_ok = False
        choppy_err = f"Crashed on CHOPPY bar: {type(e).__name__}: {e}"
    q_checks.append({
        "step": 4,
        "name": "Choppy Market Treatment Test",
        "passed": c4_ok,
        "actual": ("Blocked trade (Safe)" if choppy_sig is None else f"Signaled {choppy_sig.side}") if not choppy_err else "ERROR",
        "required": "Handle CHOPPY regime safely (Block if trend-only; or explicit choppy rule)" + (f" [{choppy_txt}]" if choppy_txt else ""),
        "why_failed": choppy_err,
    })

    # 5. Trending Market Treatment Test (UP & DOWN + Low-Vol Reject)
    trend_err = ""
    up_sig = down_sig = rej_sig = None
    up_out = down_out = rej_out = {}
    try:
        up_sig, up_out = _run_case("TREND_UP")
        down_sig, down_out = _run_case("TREND_DOWN")
        rej_sig, rej_out = _run_case("LOW_VOL_REJECT")
        c5_ok = (up_sig is not None or down_sig is not None)
        if not c5_ok:
            trend_err = f"Produced no signal on TREND_UP ({up_out.get('reason')}) or TREND_DOWN ({down_out.get('reason')})."
    except Exception as e:
        c5_ok = False
        trend_err = f"Crashed on TRENDING bar: {type(e).__name__}: {e}"
    q_checks.append({
        "step": 5,
        "name": "Trending Market Test (UP/DOWN)",
        "passed": c5_ok,
        "actual": f"TREND_UP={'SIGNAL ' + up_sig.side if up_sig else 'NONE'}, TREND_DOWN={'SIGNAL ' + down_sig.side if down_sig else 'NONE'}, LowVol={'REJECTED' if not rej_sig else 'SIGNAL'}",
        "required": "Respond to TREND_UP / TREND_DOWN breakout & reject weak conditions",
        "why_failed": trend_err,
    })

    # 6. Risk-to-Reward & Stop-Loss Check
    sample_sig = up_sig or down_sig
    rr_ratio = None
    if sample_sig and sample_sig.stop_loss and sample_sig.stop_loss > 0:
        sample_entry = 101.2 if sample_sig is up_sig else 93.8
        rr_info = compute_rr_metrics(sample_entry, sample_sig.stop_loss, sample_sig.target)
        rr_ratio = rr_info["rr_ratio"]
        c6_ok = rr_ratio is None or rr_ratio >= 1.0
        c6_act = f"SL={sample_sig.stop_loss:.2f}, Tgt={sample_sig.target or 'None'}, R:R=1:{rr_ratio:.2f}" if rr_ratio else f"SL={sample_sig.stop_loss:.2f}, Target=None"
        c6_why = "" if c6_ok else f"Risk-to-Reward 1:{rr_ratio:.2f} < 1:1.0"
    elif isinstance(up_out, dict) and up_out.get("rr_ratio"):
        rr_ratio = up_out.get("rr_ratio")
        c6_ok = rr_ratio >= 1.0
        c6_act = f"Declared R:R=1:{rr_ratio:.2f}"
        c6_why = "" if c6_ok else f"R:R 1:{rr_ratio:.2f} < 1:1.0"
    else:
        c6_ok = False
        c6_act = "No Stop-Loss / Target signal produced in test"
        c6_why = "Could not verify Stop-Loss & Risk-to-Reward ratio on synthetic breakout."
    q_checks.append({
        "step": 6,
        "name": "Stop-Loss & Risk-to-Reward (R:R)",
        "passed": c6_ok,
        "actual": c6_act,
        "required": "Mandatory stop_loss > 0 and R:R >= 1:1.0",
        "why_failed": c6_why,
    })

    # Extract strategy's own checks schema (either CHECKS_SCHEMA, live evaluate_signal checks, or AST gates)
    strat_checks = list(getattr(mod, "CHECKS_SCHEMA", []) or [])
    if not strat_checks and isinstance(up_out, dict) and up_out.get("checks"):
        strat_checks = [
            {"step": c["step"], "name": c["name"], "required": c["required"], "code": c.get("code", "")}
            for c in up_out["checks"]
        ]
    if not strat_checks and ast_gates:
        strat_checks = [
            {"step": i, "name": f"Code Gate (Line {g['line']})", "required": g["code"], "code": g["code"]}
            for i, g in enumerate(ast_gates[:10], 1)
        ]

    passed_cnt = sum(1 for c in q_checks if c["passed"])
    failed_cnt = len(q_checks) - passed_cnt
    status_txt = "PASSED (All Qualification Checks OK)" if failed_cnt == 0 else f"WARNING ({passed_cnt}/{len(q_checks)} Passed — Soft Gate: Runnable)"

    return {
        "file": file_rel_path,
        "name": name,
        "can_use": True,
        "status": status_txt,
        "passed_count": passed_cnt,
        "failed_count": failed_cnt,
        "total_count": len(q_checks),
        "checks": q_checks,
        "strategy_checks": strat_checks,
        "ast_gates": ast_gates,
        "rr_ratio": rr_ratio,
        "market_type": market_type or "Undeclared",
        "regimes": list(regimes) if regimes else [],
        "choppy_treatment": choppy_txt or ("Blocked" if not allows_choppy else "Allowed"),
        "trending_treatment": trending_txt or "Undeclared",
        "summary": f"{name}: {status_txt}. Detected {len(strat_checks)} strategy check(s) + 1 engine gate.",
        "code_lines": len(src.splitlines()),
    }


def verify_with_openrouter(cfg, store, file_rel_path: str, api_key: str | None = None, model: str | None = None) -> dict:
    """Call OpenRouter (default GLM 5.3 Flash) to inspect strategy code & extract structured checks."""
    key = (api_key if api_key is not None else cfg.openrouter_api_key or "").strip()
    display_model = (model or cfg.openrouter_model or DEFAULT_AI_MODEL).strip() or DEFAULT_AI_MODEL
    model_slug = _resolve_model_slug(display_model)

    if api_key is not None or model is not None:
        save_openrouter_env(cfg, api_key=api_key, model=display_model)

    qual = qualify_strategy_file(cfg, file_rel_path)
    p = (cfg.root / file_rel_path).resolve()
    if not p.exists():
        return {"ok": False, "message": f"File not found: {file_rel_path}", "qualification": qual}

    if not key:
        return {
            "ok": False,
            "needs_key": True,
            "model_display": display_model,
            "model_slug": model_slug,
            "message": "OpenRouter API key abhi set nahi hai. Jab aap key add karenge, AI Agent poori strategy code verify karke checks extract karega.",
            "qualification": qual,
        }

    code_text = p.read_text(encoding="utf-8-sig")[:12000]
    prompt = (
        "You are inspecting an intraday NSE trading strategy file for a transparent Strategy Socket.\n"
        "Return ONLY valid JSON with keys:\n"
        "{\n"
        '  "verdict": "PASS" or "WARN",\n'
        '  "summary": "short Hinglish/English explanation of what this strategy does",\n'
        '  "market_type": "e.g. NSE_INTRADAY_EQUITY",\n'
        '  "choppy_treatment": "exact behavior when regime is CHOPPY",\n'
        '  "trending_treatment": "exact behavior when regime is TREND_UP/TREND_DOWN",\n'
        '  "rr_assessment": "stop-loss and risk-to-reward evaluation",\n'
        '  "extracted_checks": [{"step": 1, "name": "...", "code": "...", "required": "..."}]\n'
        "}\n\n"
        f"Strategy file: {file_rel_path}\n"
        f"Local Qualification Summary: {qual.get('summary')}\n\n"
        f"```python\n{code_text}\n```"
    )

    payload = {
        "model": model_slug,
        "messages": [
            {"role": "system", "content": "You are a strict quantitative code auditor. Respond in pure JSON only."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
    }
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8800",
            "X-Title": "intraday-engine Strategy Socket",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
        content = raw["choices"][0]["message"]["content"].strip()
        m = re.search(r"\{.*\}", content, re.DOTALL)
        parsed = json.loads(m.group(0) if m else content)
        ai_res = {
            "ok": True,
            "model_display": display_model,
            "model_slug": model_slug,
            "ai": parsed,
            "qualification": qual,
            "checked_at": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST"),
        }
        if store is not None:
            store.set_setting(f"ai_checks:{file_rel_path}", ai_res)
        return ai_res
    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode("utf-8")[:240]
        except Exception:
            pass
        return {"ok": False, "model_display": display_model, "model_slug": model_slug,
                "message": f"OpenRouter HTTP {e.code}: {err_body}", "qualification": qual}
    except Exception as e:
        return {"ok": False, "model_display": display_model, "model_slug": model_slug,
                "message": f"OpenRouter request failed: {type(e).__name__}: {e}", "qualification": qual}


def upload_strategy_file(cfg, filename: str, code_text: str) -> tuple[bool, str, str]:
    """Validate filename and write strategy code into strategies/."""
    clean = re.sub(r"[^a-zA-Z0-9_-]", "_", Path(str(filename or "")).stem).strip("_").lower()
    if not clean:
        return False, "Please provide a valid strategy filename (letters, numbers, underscores).", ""
    if not code_text or not str(code_text).strip():
        return False, "Strategy code cannot be empty.", ""
    rel = f"strategies/{clean}.py"
    target = _strategies_dir(cfg) / f"{clean}.py"
    target.write_text(str(code_text), encoding="utf-8")
    return True, f"Uploaded {rel}.", rel


def delete_strategy_file(cfg, file_rel_path: str) -> tuple[bool, str]:
    """Delete a strategy file from strategies/ safely (never allows path traversal)."""
    sdir = _strategies_dir(cfg).resolve()
    target = (cfg.root / file_rel_path).resolve()
    if target.parent != sdir or target.suffix != ".py":
        return False, "Can only delete .py files inside strategies/."
    if target.name == "pdh_breakout.py":
        return False, "Built-in default pdh_breakout.py cannot be deleted (you can unplug it instead)."
    if not target.exists():
        return False, f"File not found: {file_rel_path}"
    target.unlink()
    return True, f"Deleted {file_rel_path}."


def get_socket_reference(cfg, store=None, qual_cache: dict | None = None) -> dict:
    """Return full Socket UI payload: active status, list of strategies, AI status, and upfront docs."""
    cur_file = str(cfg.strategy_file or "").replace("\\", "/").strip()
    qual = qual_cache if qual_cache is not None else qualify_strategy_file(cfg, cur_file)
    ai_saved = store.get_setting(f"ai_checks:{cur_file}") if (store and cur_file) else None
    return {
        "active_file": cur_file,
        "active_name": cfg.strategy_name or ("unplugged" if not cur_file else Path(cur_file).stem),
        "strategies": list_strategies(cfg),
        "qualification": qual,
        "ai_verification": ai_saved,
        "openrouter": {
            "has_key": cfg.has_openrouter,
            "model": cfg.openrouter_model or DEFAULT_AI_MODEL,
            "default_model": DEFAULT_AI_MODEL,
            "model_slug": _resolve_model_slug(cfg.openrouter_model),
        },
        "reference": {
            "data_scope": {
                "universe": "104 NSE stocks (11 sectors) -> Daily pre-filter keeps ~72 liquid stocks (Price ₹100-₹5000, 20d Avg Value >= ₹50 Cr, ATR% >= 1.2%, >=5 stocks/sector).",
                "daily_history": "20 trading days daily OHLCV -> PDH, PDL, PDC, 14-day Daily ATR.",
                "intraday_bars": "5-minute OHLCV DataFrame: Last 5 trading sessions + today's closed bars (~375 to 450 bars per armed stock; 72-75 bars/day 09:15-15:15 IST).",
            },
            "parameters_available": CTX_PARAMETERS_DOC,
            "function_contract": "evaluate_signal(self, symbol: str, bars: pd.DataFrame, ctx: Context) -> dict   (and optional fallback on_bar)",
            "qualification_code": QUALIFICATION_CODE_SNIPPET,
            "starter_template": STARTER_STRATEGY_TEMPLATE,
            "ai_builder_prompt": AI_BUILDER_PROMPT,
        },
    }


def apply_plug_strategy(controller, file_rel_path: str) -> tuple[bool, str, dict]:
    """Load a strategy into controller (Soft Gate: warns on issues but still plugs in)."""
    rel = str(file_rel_path or "").replace("\\", "/").strip()
    if not rel:
        return False, "Missing strategy file path.", {}
    p = (controller.cfg.root / rel).resolve()
    if not p.exists():
        return False, f"Strategy file not found: {rel}", {}

    qual = qualify_strategy_file(controller.cfg, rel)
    try:
        mod, strat = load_strategy_plug(controller.cfg, file_override=rel)
    except Exception as e:
        return False, f"Cannot load {rel}: {type(e).__name__}: {e}", qual

    name = str(getattr(mod, "NAME", p.stem))
    mod_params = dict(getattr(mod, "PARAMS", {}))
    save_strategy_config(controller.cfg, name, rel, strategy_params=mod_params)
    with controller._lock:
        controller.strategy_mod = mod
        controller.strategy = strat
        controller.last_qualification = qual
    controller.store.add_activity(
        f"Strategy plugged into socket: {name} ({rel}) — {qual.get('status')}",
        "good" if qual.get("failed_count", 0) == 0 else "warn",
    )
    controller._refresh()
    return True, qual.get("summary") or f"Plugged {name}.", qual


def apply_unplug_strategy(controller) -> tuple[bool, str]:
    """Remove/unplug the active strategy from the socket without deleting its file."""
    with controller._lock:
        prev = controller.cfg.strategy_name or controller.cfg.strategy_file or "none"
        controller.strategy_mod = None
        controller.strategy = None
        controller.last_qualification = None
    save_strategy_config(controller.cfg, "", "")
    controller.store.add_activity(f"Strategy unplugged from socket (was {prev}). Socket is now EMPTY.", "warn")
    controller._refresh()
    return True, f"Strategy '{prev}' removed from socket."
