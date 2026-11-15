"""5m bar fetch for armed symbols, session VWAP, slot-volume baseline, RVOL and strategy socket."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import math
import time
import traceback

from openalgo import ta

from core.data_router import fetch_backtest_data
from core.strategy_loader import load_strategy

from engine.oa import IST


@dataclass
class Signal:
    side: str                  # "LONG" | "SHORT"
    entry: str = "MARKET"      # "MARKET" | "LIMIT"
    limit_price: float | None = None
    stop_loss: float = 0.0
    target: float | None = None
    reason: str = ""


@dataclass
class Exit:
    reason: str = ""


@dataclass
class Context:
    now: datetime
    regime: str
    sector: str
    sector_rank: int
    sector_bias: int
    pdh: float
    pdl: float
    pdc: float
    vwap: float
    atr: float
    day_open: float
    day_high: float
    day_low: float
    slot_volume_avg: float
    rvol: float
    ltp: float
    traded_today: bool = False
    _held_symbols: set = field(default_factory=set)
    rejected: dict | None = None

    def has_position(self, symbol: str) -> bool:
        return symbol in self._held_symbols

    def record_rejection(self, side: str, stop_loss: float, target: float, reason: str):
        self.rejected = {
            "side": side,
            "stop_loss": round(float(stop_loss), 2) if stop_loss else None,
            "target": round(float(target), 2) if target else None,
            "reason": reason,
        }


class StrategyChecklistEvaluator:
    """Transparent rule-checklist evaluator so every strategy signal exposes exact pass/fail checks."""

    def __init__(self, strategy_name: str = ""):
        self.strategy_name = strategy_name
        self.checks = []
        self.errors = []

    def add_rule(
        self,
        step: int,
        name: str,
        passed: bool,
        actual: str,
        required: str,
        why_failed: str = "",
        code: str = "",
    ) -> bool:
        ok = bool(passed)
        self.checks.append({
            "step": int(step),
            "name": str(name),
            "passed": ok,
            "actual": str(actual),
            "required": str(required),
            "why_failed": "" if ok else str(why_failed or f"{name} condition failed"),
            "code": str(code),
            "error": False,
        })
        return ok

    def check_rule(
        self,
        step: int,
        name: str,
        fn,
        actual_fn,
        required: str,
        why_failed_fn=None,
        code: str = "",
    ) -> bool:
        try:
            ok = bool(fn())
            actual = str(actual_fn()) if callable(actual_fn) else str(actual_fn)
            why = ""
            if not ok:
                why = str(why_failed_fn()) if callable(why_failed_fn) else str(why_failed_fn or f"{name} failed")
            return self.add_rule(step, name, ok, actual, required, why, code=code)
        except Exception as e:
            err_txt = f"CODE ERROR in Check #{step} ({name}): {type(e).__name__}: {e}"
            self.errors.append(err_txt)
            self.checks.append({
                "step": int(step),
                "name": str(name),
                "passed": False,
                "actual": f"EXCEPTION: {type(e).__name__}",
                "required": str(required),
                "why_failed": err_txt,
                "code": str(code),
                "error": True,
            })
            return False

    def result(
        self,
        *,
        side: str,
        entry_price: float,
        stop_loss: float | None,
        target: float | None,
        reason: str = "",
    ) -> dict:
        all_passed = bool(self.checks) and all(c["passed"] for c in self.checks)
        rr = compute_rr_metrics(entry_price, stop_loss, target)
        failed = [c for c in self.checks if not c["passed"]]
        if not reason:
            reason = (
                f"{side} passed all {len(self.checks)} checks (R:R 1:{rr['rr_ratio']:.2f})"
                if all_passed and rr["rr_ratio"] is not None
                else (failed[0]["why_failed"] if failed else "Rejected by strategy")
            )
        sig_obj = (
            Signal(
                side=side,
                entry="MARKET",
                stop_loss=round(float(stop_loss), 2),
                target=round(float(target), 2) if target is not None else None,
                reason=reason,
            )
            if all_passed and stop_loss and stop_loss > 0
            else None
        )
        return {
            "passed": bool(sig_obj is not None),
            "signal": sig_obj,
            "side": side,
            "entry_price": round(float(entry_price), 2) if entry_price else None,
            "stop_loss": round(float(stop_loss), 2) if stop_loss else None,
            "target": round(float(target), 2) if target is not None else None,
            "rr_ratio": rr["rr_ratio"],
            "risk_per_share": rr["risk_per_share"],
            "reward_per_share": rr["reward_per_share"],
            "reason": reason,
            "total_checks": len(self.checks),
            "passed_checks": sum(1 for c in self.checks if c["passed"]),
            "failed_checks": sum(1 for c in self.checks if not c["passed"]),
            "checks": list(self.checks),
            "error": "; ".join(self.errors) if self.errors else None,
        }


def compute_rr_metrics(entry_price, stop_loss, target, qty=None) -> dict:
    """Compute Risk-to-Reward ratio and rupee risk/reward from entry, stop_loss, target."""
    if not entry_price or not stop_loss or float(entry_price) <= 0 or float(stop_loss) <= 0:
        return {"risk_per_share": None, "reward_per_share": None, "rr_ratio": None, "risk_rs": None, "reward_rs": None}
    ep = float(entry_price)
    sl = float(stop_loss)
    risk_ps = abs(ep - sl)
    if risk_ps <= 0:
        return {"risk_per_share": 0.0, "reward_per_share": None, "rr_ratio": None, "risk_rs": None, "reward_rs": None}
    reward_ps = abs(float(target) - ep) if target is not None and float(target) > 0 else None
    rr_ratio = round(reward_ps / risk_ps, 2) if reward_ps is not None else None
    q = int(qty) if qty is not None and qty > 0 else None
    return {
        "risk_per_share": round(risk_ps, 2),
        "reward_per_share": round(reward_ps, 2) if reward_ps is not None else None,
        "rr_ratio": rr_ratio,
        "risk_rs": round(q * risk_ps, 2) if q else None,
        "reward_rs": round(q * reward_ps, 2) if (q and reward_ps is not None) else None,
    }


def load_strategy_plug(cfg, file_override=None):
    """Load the configured strategy file via vendor strategy_loader and instantiate Strategy."""
    rel = cfg.strategy_file if file_override is None else str(file_override)
    if not rel or str(rel).strip().lower() in ("", "none", "unplugged"):
        return None, None
    mod = load_strategy(cfg.root / rel)
    params = dict(getattr(mod, "PARAMS", {}))
    if file_override is None:
        params.update(cfg.strategy_params)
    return mod, mod.Strategy(params)


def evaluate_strategy_bar(
    strategy,
    strategy_mod,
    symbol: str,
    bars,
    ctx: Context,
    cfg,
    *,
    regime_res: dict,
    s_meta: dict,
    metrics: dict,
    row: dict,
    gate_reason: str = "",
):
    """Run active strategy transparently (prefer evaluate_signal, fallback to on_bar) with crash capture."""
    entry_px = round(float(metrics.get("bar_close") or ctx.ltp or 0.0), 2)
    if strategy is None:
        checks = [{
            "step": 1,
            "name": "Strategy Socket",
            "passed": False,
            "actual": "UNPLUGGED",
            "required": "Strategy plugged into socket",
            "why_failed": "Strategy socket khali (UNPLUGGED) hai. Strategy & Socket button se strategy plug karein.",
            "error": False,
        }]
        return None, {
            "passed": False, "side": "", "entry_price": entry_px, "stop_loss": None, "target": None,
            "rr_ratio": None, "reason": checks[0]["why_failed"], "checks": checks,
            "error": "Strategy socket unplugged", "has_native_checks": True,
        }

    sig = None
    eval_res = None
    crash_err = None
    has_eval = callable(getattr(strategy, "evaluate_signal", None))

    if has_eval:
        try:
            eval_res = strategy.evaluate_signal(symbol, bars, ctx)
            if isinstance(eval_res, dict):
                sig = eval_res.get("signal")
                if sig is None and eval_res.get("passed") and eval_res.get("stop_loss"):
                    sig = Signal(
                        side=eval_res.get("side") or ("LONG" if ctx.regime == "TREND_UP" else "SHORT"),
                        entry="MARKET",
                        stop_loss=float(eval_res["stop_loss"]),
                        target=float(eval_res["target"]) if eval_res.get("target") is not None else None,
                        reason=eval_res.get("reason") or "Signal passed evaluate_signal",
                    )
        except Exception as e:
            tb_lines = traceback.format_exc().strip().splitlines()
            loc = tb_lines[-2].strip() if len(tb_lines) >= 2 else ""
            crash_err = f"evaluate_signal crashed: {type(e).__name__}: {e}" + (f" ({loc})" if loc else "")
    else:
        try:
            sig = strategy.on_bar(symbol, bars, ctx)
        except Exception as e:
            tb_lines = traceback.format_exc().strip().splitlines()
            loc = tb_lines[-2].strip() if len(tb_lines) >= 2 else ""
            crash_err = f"on_bar crashed: {type(e).__name__}: {e}" + (f" ({loc})" if loc else "")

    checks = []
    has_native_checks = False
    if isinstance(eval_res, dict) and isinstance(eval_res.get("checks"), list) and eval_res["checks"]:
        checks = [dict(c) for c in eval_res["checks"]]
        has_native_checks = True
        if eval_res.get("error"):
            crash_err = str(eval_res["error"])

    if crash_err and not any(c.get("error") for c in checks):
        checks.append({
            "step": len(checks) + 1,
            "name": "Strategy Code Execution",
            "passed": False,
            "actual": "CRASH / EXCEPTION",
            "required": "Zero runtime errors in strategy",
            "why_failed": f"System/Strategy code error: {crash_err}",
            "error": True,
        })
        has_native_checks = True

    if isinstance(eval_res, dict):
        side = eval_res.get("side") or (sig.side if sig is not None else "")
        stop_loss = eval_res.get("stop_loss") if eval_res.get("stop_loss") is not None else (sig.stop_loss if sig else None)
        target = eval_res.get("target") if eval_res.get("target") is not None else (sig.target if sig else None)
        reason = eval_res.get("reason") or (sig.reason if sig else "")
    else:
        rej = ctx.rejected or {}
        side = sig.side if sig is not None else (rej.get("side") or "")
        stop_loss = sig.stop_loss if sig is not None else rej.get("stop_loss")
        target = sig.target if sig is not None else rej.get("target")
        reason = sig.reason if sig is not None else (rej.get("reason") or crash_err or "Rejected by strategy")

    if not has_native_checks and strategy_mod is not None and getattr(strategy_mod, "NAME", "") != "pdh_breakout":
        # Generic transparent checks for custom on_bar()-only strategies
        reg_decl = tuple(getattr(strategy_mod, "REGIMES", ("TREND_UP", "TREND_DOWN")))
        reg_ok = ctx.regime in reg_decl
        rr_info = compute_rr_metrics(entry_px, stop_loss, target)
        sl_ok = bool(stop_loss and float(stop_loss) > 0)
        sig_ok = sig is not None and not crash_err
        checks = [
            {
                "step": 1, "name": "Strategy Runtime", "passed": crash_err is None,
                "actual": "OK" if crash_err is None else "CRASH",
                "required": "No runtime errors",
                "why_failed": "" if crash_err is None else crash_err,
                "error": bool(crash_err),
            },
            {
                "step": 2, "name": "Market Regime Compatibility", "passed": reg_ok,
                "actual": ctx.regime,
                "required": f"Regime in {', '.join(reg_decl)}",
                "why_failed": "" if reg_ok else f"Market regime {ctx.regime} is not in declared REGIMES {reg_decl}",
                "error": False,
            },
            {
                "step": 3, "name": "Strategy Entry Rule (on_bar)", "passed": sig_ok,
                "actual": f"Signal {side}" if sig_ok else "None (Rejected)",
                "required": "Valid Signal returned by on_bar()",
                "why_failed": "" if sig_ok else (reason or "on_bar() returned None"),
                "error": False,
            },
            {
                "step": 4, "name": "Stop-Loss & R:R Valid", "passed": sl_ok,
                "actual": f"SL {stop_loss or 'None'} | Tgt {target or 'None'} | R:R {('1:' + str(rr_info['rr_ratio'])) if rr_info['rr_ratio'] else '–'}",
                "required": "Mandatory stop_loss > 0",
                "why_failed": "" if sl_ok else "Strategy ne stop_loss nahi diya (mandatory hai)",
                "error": False,
            },
        ]
        has_native_checks = True

    rr_info = compute_rr_metrics(entry_px, stop_loss, target)
    return sig, {
        "passed": sig is not None and crash_err is None and not gate_reason,
        "side": side,
        "entry_price": entry_px,
        "stop_loss": round(float(stop_loss), 2) if stop_loss else None,
        "target": round(float(target), 2) if target is not None else None,
        "rr_ratio": rr_info["rr_ratio"],
        "risk_per_share": rr_info["risk_per_share"],
        "reward_per_share": rr_info["reward_per_share"],
        "reason": reason,
        "checks": checks,
        "has_native_checks": has_native_checks,
        "error": crash_err,
        "min_condition": getattr(strategy_mod, "MIN_CONDITION_TEXT", None),
    }


def _fallback_vwap(today_bars):
    vol = today_bars["volume"].astype(float)
    total_v = float(vol.sum())
    if total_v <= 0:
        return float(today_bars["close"].iloc[-1])
    tp = (today_bars["high"].astype(float) + today_bars["low"].astype(float) + today_bars["close"].astype(float)) / 3.0
    return float((tp * vol).sum() / total_v)


def prepare_bar_metrics(df_all, boundary_dt, baseline_sessions=5):
    """Pure: slice last 5 sessions + today up to boundary_dt and compute VWAP, slot vol avg, RVOL."""
    if df_all is None or len(df_all) == 0:
        return None
    df = df_all[df_all.index < boundary_dt]
    if len(df) == 0:
        return None

    today_date = boundary_dt.date()
    today_bars = df[df.index.date == today_date]
    if len(today_bars) == 0:
        return None

    all_dates = sorted({d for d in df.index.date if d < today_date})
    prior_dates = all_dates[-baseline_sessions:]
    keep_dates = set(prior_dates) | {today_date}
    bars_5s = df[[d in keep_dates for d in df.index.date]].copy()

    vwap_val = None
    try:
        vw = ta.vwap(
            bars_5s["high"], bars_5s["low"], bars_5s["close"], bars_5s["volume"],
            anchor="Session", timestamps=bars_5s.index,
        )
        cand = float(vw.iloc[-1])
        if not math.isnan(cand) and cand > 0:
            vwap_val = cand
    except Exception:
        vwap_val = None
    if vwap_val is None:
        vwap_val = _fallback_vwap(today_bars)

    slot_time = today_bars.index[-1].time()
    prior_bars = df[[d in set(prior_dates) for d in df.index.date]]
    slot_rows = prior_bars[prior_bars.index.time == slot_time]
    slot_vol_avg = float(slot_rows["volume"].mean()) if len(slot_rows) > 0 else 0.0

    today_cum_vol = float(today_bars["volume"].sum())
    prior_cums = []
    for d in prior_dates:
        d_bars = prior_bars[(prior_bars.index.date == d) & (prior_bars.index.time <= slot_time)]
        c = float(d_bars["volume"].sum())
        if c > 0:
            prior_cums.append(c)
    avg_prior_cum = (sum(prior_cums) / len(prior_cums)) if prior_cums else 0.0
    rvol = (today_cum_vol / avg_prior_cum) if avg_prior_cum > 0 else 0.0

    return {
        "bars": bars_5s,
        "vwap": round(vwap_val, 2),
        "slot_volume_avg": round(slot_vol_avg, 1),
        "rvol": round(rvol, 2),
        "day_open": float(today_bars["open"].iloc[0]),
        "day_high": float(today_bars["high"].max()),
        "day_low": float(today_bars["low"].min()),
        "last_bar_open_ts": today_bars.index[-1],
        "bar_close": float(today_bars["close"].iloc[-1]),
        "bar_volume": float(today_bars["volume"].iloc[-1]),
    }


def _normalize_ist(df):
    if df is None or not hasattr(df, "columns") or len(df) == 0:
        return None
    out = df.copy()
    if out.index.tz is None:
        out.index = out.index.tz_localize(IST)
    else:
        out.index = out.index.tz_convert(IST)
    return out


def fetch_armed_bars(link, cfg, symbol, boundary_dt, wait_retry_s=5.0):
    """Fetch 5m history for one armed symbol with 1 retry after 5s if the bar is missing."""
    expected_bar_ts = boundary_dt - timedelta(minutes=cfg.rescan_minutes)
    start = (boundary_dt.date() - timedelta(days=12)).isoformat()
    end = boundary_dt.date().isoformat()
    baseline_sessions = int(cfg.strategy_params.get("vol_baseline_sessions", 5))

    for attempt in range(2):
        try:
            raw = fetch_backtest_data(link, symbol, cfg.exchange, "5m", start, end, source="api")
        except Exception:
            raw = None
        df = _normalize_ist(raw)
        metrics = prepare_bar_metrics(df, boundary_dt, baseline_sessions=baseline_sessions) if df is not None else None
        if metrics is not None and metrics["last_bar_open_ts"] >= expected_bar_ts and metrics["bar_volume"] > 0:
            return metrics, ""
        if attempt == 0:
            time.sleep(wait_retry_s)

    if metrics is not None:
        if metrics["bar_volume"] <= 0:
            return None, "Closed bar has zero volume"
        return metrics, ""
    return None, "5m history fetch failed or bar missing"
