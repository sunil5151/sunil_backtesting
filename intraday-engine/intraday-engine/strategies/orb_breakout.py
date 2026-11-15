"""Strategy plug: Opening Range Breakout (adapted from vendor/reference_strategies/opening_range.py).

Pure trading logic using the StrategyChecklistEvaluator contract (evaluate_signal + on_bar).
"""
from datetime import time as dtime

from engine.bars import Signal, StrategyChecklistEvaluator

NAME = "orb_breakout"
TIMEFRAME = "5m"
LOOKBACK_BARS = 50
MARKET_TYPE = "NSE_INTRADAY_EQUITY"
REGIMES = ("TREND_UP", "TREND_DOWN")
SIDES = ("LONG", "SHORT")
CHOPPY_TREATMENT = "Blocks all entries when ctx.regime == 'CHOPPY' to avoid opening-range whipsaws."
TRENDING_TREATMENT = "TREND_UP -> LONG above 09:15-09:30 OR High; TREND_DOWN -> SHORT below 09:15-09:30 OR Low."
PARAMS = {
    "or_start_hhmm": "09:15",
    "or_end_hhmm": "09:30",
    "buffer_pct": 0.0005,
    "vwap_filter": True,
    "rvol_min": 1.0,
    "min_stop_pct": 0.005,
    "max_stop_pct": 0.015,
    "target_r": 2.0,
    "breakeven_at_r": 1.0,
}

CHECKS_SCHEMA = [
    {"step": 1, "name": "Market Regime", "required": "TREND_UP (LONG) / TREND_DOWN (SHORT)",
     "code": "ctx.regime in ('TREND_UP', 'TREND_DOWN')"},
    {"step": 2, "name": "Opening Range Ready", "required": "Time after 09:30 and OR High/Low computed",
     "code": "len(or_bars) >= 1 and bar_time > OR_END"},
    {"step": 3, "name": "OR Breakout Candle", "required": "Close > OR_HIGH+0.05% (LONG) or < OR_LOW-0.05% (SHORT)",
     "code": "close > or_high*(1+buf) or close < or_low*(1-buf)"},
    {"step": 4, "name": "VWAP Filter", "required": "Close on trend side of Session VWAP",
     "code": "close > ctx.vwap (LONG) or close < ctx.vwap (SHORT)"},
    {"step": 5, "name": "Day RVOL", "required": "Cumulative Day RVOL >= 1.0x",
     "code": "ctx.rvol >= rvol_min"},
    {"step": 6, "name": "Stop Width & Fresh", "required": "Stop <= 1.5% and not already traded today",
     "code": "stop_pct <= max_stop_pct and not ctx.traded_today"},
]

MIN_CONDITION_TEXT = (
    "ORB Entry ke liye 7 me se 7 checks pass hona zaroori hai: "
    "(1) Market Regime Trend me ho, (2) 09:15-09:30 Opening Range complete ho, "
    "(3) 5m Close OR High/Low break kare, (4) Close VWAP ke sahi side ho, "
    "(5) RVOL >= 1.0x ho, (6) Stop <= 1.5% & fresh symbol ho, (7) Timing & Risk Gate OK ho."
)


def _hhmm_to_time(s: str) -> dtime:
    hh, mm = str(s).strip().split(":")
    return dtime(int(hh), int(mm))


class Strategy:
    def __init__(self, params: dict):
        self.params = dict(PARAMS)
        if params:
            self.params.update(params)

    def evaluate_signal(self, symbol: str, bars, ctx) -> dict:
        p = self.params
        ev = StrategyChecklistEvaluator(NAME)

        if ctx.regime == "TREND_UP":
            side, reg_ok = "LONG", True
        elif ctx.regime == "TREND_DOWN":
            side, reg_ok = "SHORT", True
        else:
            side, reg_ok = ("LONG" if (ctx.ltp or 0) >= (ctx.vwap or 0) else "SHORT"), False

        ev.add_rule(
            1, "Market Regime", reg_ok,
            f"{ctx.regime}",
            "TREND_UP (LONG) / TREND_DOWN (SHORT)",
            "" if reg_ok else f"Market Regime '{ctx.regime}' tha; ORB breakout ke liye TREND_UP ya TREND_DOWN chahiye.",
            code="ctx.regime in ('TREND_UP', 'TREND_DOWN')",
        )

        if bars is None or len(bars) == 0:
            ev.add_rule(2, "5m Bar Data", False, "0 bars", ">= 1 bar", "No 5m bars available")
            ctx.record_rejection(side, 0.0, 0.0, "No 5m bars available")
            return ev.result(side=side, entry_price=ctx.ltp or 0.0, stop_loss=None, target=None, reason="No 5m bars available")

        last = bars.iloc[-1]
        close = float(last["close"])
        high = float(last["high"])
        low = float(last["low"])

        today_dt = ctx.now.date()
        today_bars = bars[bars.index.date == today_dt] if hasattr(bars.index, "date") else bars.tail(1)
        or_start = _hhmm_to_time(p["or_start_hhmm"])
        or_end = _hhmm_to_time(p["or_end_hhmm"])
        or_bars = today_bars[(today_bars.index.time >= or_start) & (today_bars.index.time < or_end)] if hasattr(today_bars.index, "time") else today_bars.head(3)

        or_ready = len(or_bars) >= 1 and ctx.now.time() >= or_end
        or_high = float(or_bars["high"].max()) if len(or_bars) > 0 else float(ctx.day_high or high)
        or_low = float(or_bars["low"].min()) if len(or_bars) > 0 else float(ctx.day_low or low)
        ev.add_rule(
            2, "Opening Range Ready", or_ready,
            f"OR {or_low:.2f}–{or_high:.2f} ({len(or_bars)} bars)",
            f"Complete after {p['or_end_hhmm']}",
            "" if or_ready else f"Opening range ({p['or_start_hhmm']}-{p['or_end_hhmm']}) abhi complete nahi hua.",
            code="len(or_bars) >= 1 and ctx.now.time() >= OR_END",
        )

        if side == "LONG":
            stop = min(low * 0.9995, close * (1.0 - p["min_stop_pct"]))
            r_pts = close - stop
            target = close + p["target_r"] * r_pts
            trig = or_high * (1.0 + p["buffer_pct"])
            brk_ok = close > trig
            brk_req = f"Close > {trig:.2f} (OR High+{p['buffer_pct']*100:.2f}%)"
            brk_why = f"Bar close ₹{close:.2f} <= OR High trigger ₹{trig:.2f}."
        else:
            stop = max(high * 1.0005, close * (1.0 + p["min_stop_pct"]))
            r_pts = stop - close
            target = close - p["target_r"] * r_pts
            trig = or_low * (1.0 - p["buffer_pct"])
            brk_ok = close < trig
            brk_req = f"Close < {trig:.2f} (OR Low-{p['buffer_pct']*100:.2f}%)"
            brk_why = f"Bar close ₹{close:.2f} >= OR Low trigger ₹{trig:.2f}."

        ev.add_rule(
            3, "OR Breakout Candle", brk_ok,
            f"Close {close:.2f}",
            brk_req,
            "" if brk_ok else brk_why,
            code="close > or_high*(1+buf) / close < or_low*(1-buf)",
        )

        if p["vwap_filter"]:
            vwap_ok = (close > ctx.vwap) if side == "LONG" else (close < ctx.vwap)
            vwap_req = f"Close {'>' if side == 'LONG' else '<'} VWAP ({ctx.vwap:.2f})"
            vwap_why = f"Close ₹{close:.2f} VWAP (₹{ctx.vwap:.2f}) ke galat side tha."
        else:
            vwap_ok, vwap_req, vwap_why = True, "Disabled", ""
        ev.add_rule(
            4, "VWAP Filter", vwap_ok,
            f"Close {close:.2f} vs VWAP {ctx.vwap:.2f}",
            vwap_req,
            vwap_why,
            code="close > ctx.vwap / close < ctx.vwap",
        )

        rvol_ok = ctx.rvol >= p["rvol_min"]
        ev.add_rule(
            5, "Day RVOL", rvol_ok,
            f"{ctx.rvol:.2f}x",
            f">= {p['rvol_min']:.1f}x",
            "" if rvol_ok else f"RVOL {ctx.rvol:.2f}x < {p['rvol_min']:.1f}x minimum.",
            code="ctx.rvol >= rvol_min",
        )

        stop_pct = (r_pts / close) if close > 0 else 1.0
        fresh_ok = not (ctx.traded_today or ctx.has_position(symbol))
        risk_ok = stop_pct <= p["max_stop_pct"] and fresh_ok
        r_whys = []
        if not fresh_ok:
            r_whys.append("Already traded today")
        if stop_pct > p["max_stop_pct"]:
            r_whys.append(f"Stop width {stop_pct*100:.2f}% > {p['max_stop_pct']*100:.1f}% max")
        ev.add_rule(
            6, "Stop Width & Fresh", risk_ok,
            f"Stop {stop_pct*100:.2f}%, traded={ctx.traded_today}",
            f"<= {p['max_stop_pct']*100:.1f}%, fresh symbol",
            "; ".join(r_whys),
            code="stop_pct <= max_stop_pct and not ctx.traded_today",
        )

        all_ok = all(c["passed"] for c in ev.checks)
        reason_txt = (
            f"{side} ORB breakout: OR {or_low:.2f}–{or_high:.2f}, RVOL {ctx.rvol:.2f}x, R:R 1:{p['target_r']:.1f}"
            if all_ok
            else " | ".join(c["why_failed"] for c in ev.checks if not c["passed"] and c["why_failed"])
        )
        res = ev.result(side=side, entry_price=close, stop_loss=stop, target=target, reason=reason_txt)
        if not res["passed"]:
            ctx.record_rejection(side, stop, target, reason_txt)
        return res

    def on_bar(self, symbol: str, bars, ctx) -> Signal | None:
        if ctx.regime not in ("TREND_UP", "TREND_DOWN"):
            return None
        return self.evaluate_signal(symbol, bars, ctx)["signal"]

    def on_exit_check(self, position, bars, ctx):
        return None
