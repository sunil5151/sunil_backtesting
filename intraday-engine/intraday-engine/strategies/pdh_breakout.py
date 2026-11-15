"""Strategy plug: PDH/PDL Breakout (spec section 7, docs/STRATEGY_SOCKET.md).

Pure trading logic: no OpenAlgo calls, no disk writes, no sleeping inside on_bar / evaluate_signal.
"""
from engine.bars import Signal, StrategyChecklistEvaluator

NAME = "pdh_breakout"
TIMEFRAME = "5m"
LOOKBACK_BARS = 50
MARKET_TYPE = "NSE_INTRADAY_EQUITY"
REGIMES = ("TREND_UP", "TREND_DOWN")
SIDES = ("LONG", "SHORT")
CHOPPY_TREATMENT = "Blocks all new entries when ctx.regime == 'CHOPPY' (zero trades in choppy market)."
TRENDING_TREATMENT = "TREND_UP -> LONG breakout above PDH+0.1%; TREND_DOWN -> SHORT breakdown below PDL-0.1%."
PARAMS = {
    "vwap_filter": True,
    "buffer_pct": 0.001,
    "vol_mult": 1.5,
    "vol_baseline_sessions": 5,
    "rvol_min": 1.0,
    "max_chase_atr": 0.5,
    "stop_bar_buffer_pct": 0.0005,
    "min_stop_pct": 0.006,
    "max_stop_pct": 0.015,
    "target_r": 2.0,
    "breakeven_at_r": 1.0,
}

CHECKS_SCHEMA = [
    {"step": 1, "name": "Market Regime", "required": "TREND_UP (LONG) / TREND_DOWN (SHORT)",
     "code": "ctx.regime in ('TREND_UP', 'TREND_DOWN')"},
    {"step": 2, "name": "Sector Strength", "required": "STRONG (LONG) / WEAK (SHORT)",
     "code": "(side=='LONG' and ctx.sector_bias>=1) or (side=='SHORT' and ctx.sector_bias<=-1)"},
    {"step": 3, "name": "Breakout Candle", "required": "Close > PDH+0.1% (LONG) or < PDL-0.1% (SHORT)",
     "code": "close > pdh*(1+buffer_pct) or close < pdl*(1-buffer_pct)"},
    {"step": 4, "name": "VWAP Filter", "required": "Close on trend side of Session VWAP",
     "code": "close > ctx.vwap (LONG) or close < ctx.vwap (SHORT)"},
    {"step": 5, "name": "5m Slot Volume", "required": "> 1.5x 5-day same-slot avg volume",
     "code": "vol > vol_mult * ctx.slot_volume_avg"},
    {"step": 6, "name": "Day RVOL", "required": "Cumulative Day RVOL >= 1.0x",
     "code": "ctx.rvol >= rvol_min"},
    {"step": 7, "name": "Gap, No-Chase & Risk", "required": "No gap-trap, chase <= 0.5 ATR, stop <= 1.5%, not traded today",
     "code": "gap_ok and ext < max_chase_atr and stop_pct <= max_stop_pct and not ctx.traded_today"},
]

MIN_CONDITION_TEXT = (
    "Entry lene ke liye 8 me se 8 conditions (100% Mandatory) pass hona zaroori hai: "
    "(1) Market Regime Trend me ho, (2) Sector Strong/Weak ho, (3) 5m Close PDH/PDL ± 0.1% cross kare, "
    "(4) Close VWAP ke sahi side ho, (5) 5m Volume > 1.5x 5-day slot avg ho, (6) Day RVOL >= 1.0x ho, "
    "(7) No Gap-trap, Chase <= 0.5 ATR, Stop <= 1.5% & Fresh stock ho, (8) Time 09:30–14:15 & Risk limit OK ho."
)


class Strategy:
    def __init__(self, params: dict):
        self.params = dict(PARAMS)
        if params:
            self.params.update(params)

    def evaluate_signal(self, symbol: str, bars, ctx) -> dict:
        p = self.params
        ev = StrategyChecklistEvaluator(NAME)

        if ctx.regime == "TREND_UP":
            side = "LONG"
            reg_ok = True
        elif ctx.regime == "TREND_DOWN":
            side = "SHORT"
            reg_ok = True
        else:
            side = "LONG" if (ctx.ltp or 0) >= (ctx.pdh or 0) else "SHORT"
            reg_ok = False

        ev.add_rule(
            1, "Market Regime", reg_ok,
            f"{ctx.regime}",
            "TREND_UP (LONG) / TREND_DOWN (SHORT)",
            "" if reg_ok else f"Market Regime '{ctx.regime}' tha; trade ke liye TREND_UP ya TREND_DOWN chahiye.",
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
        vol = float(last["volume"])

        if side == "LONG":
            stop_bar = low * (1.0 - p["stop_bar_buffer_pct"])
            stop_floor = close * (1.0 - p["min_stop_pct"])
            stop = min(stop_bar, stop_floor)
            r_pts = close - stop
            target = close + p["target_r"] * r_pts
        else:
            stop_bar = high * (1.0 + p["stop_bar_buffer_pct"])
            stop_floor = close * (1.0 + p["min_stop_pct"])
            stop = max(stop_bar, stop_floor)
            r_pts = stop - close
            target = close - p["target_r"] * r_pts

        # Check 2: Sector Strength alignment
        sec_ok = (side == "LONG" and ctx.sector_bias >= 1) or (side == "SHORT" and ctx.sector_bias <= -1)
        want_sec = "STRONG (+1)" if side == "LONG" else "WEAK (-1)"
        ev.add_rule(
            2, "Sector Strength", sec_ok,
            f"{ctx.sector} (Rank #{ctx.sector_rank}, bias {ctx.sector_bias:+d})",
            want_sec,
            "" if sec_ok else f"Sector {ctx.sector} alignment {ctx.sector_bias:+d} hai; {side} ke liye {want_sec} chahiye.",
            code="ctx.sector_bias",
        )

        # Check 3: Breakout Candle Close
        if side == "LONG":
            trig = ctx.pdh * (1.0 + p["buffer_pct"])
            brk_ok = close > trig
            brk_req = f"Close > {trig:.2f} (PDH+{p['buffer_pct']*100:.1f}%)"
            brk_why = f"Bar close ₹{close:.2f} ne PDH+{p['buffer_pct']*100:.1f}% (₹{trig:.2f}) cross nahi kiya."
        else:
            trig = ctx.pdl * (1.0 - p["buffer_pct"])
            brk_ok = close < trig
            brk_req = f"Close < {trig:.2f} (PDL-{p['buffer_pct']*100:.1f}%)"
            brk_why = f"Bar close ₹{close:.2f} ne PDL-{p['buffer_pct']*100:.1f}% (₹{trig:.2f}) break nahi kiya."
        ev.add_rule(
            3, "Breakout Candle", brk_ok,
            f"Close {close:.2f}",
            brk_req,
            "" if brk_ok else brk_why,
            code="close > pdh*(1+buf) / close < pdl*(1-buf)",
        )

        # Check 4: VWAP Filter
        if p["vwap_filter"]:
            vwap_ok = (close > ctx.vwap) if side == "LONG" else (close < ctx.vwap)
            vwap_req = f"Close {'>' if side == 'LONG' else '<'} VWAP ({ctx.vwap:.2f})"
            vwap_why = f"Close ₹{close:.2f} VWAP (₹{ctx.vwap:.2f}) ke galat side tha ({vwap_req} chahiye)."
        else:
            vwap_ok = True
            vwap_req = "Disabled"
            vwap_why = ""
        ev.add_rule(
            4, "VWAP Filter", vwap_ok,
            f"Close {close:.2f} vs VWAP {ctx.vwap:.2f}",
            vwap_req,
            vwap_why,
            code="close > ctx.vwap / close < ctx.vwap",
        )

        # Check 5: 5m Slot Volume
        slot_avg = float(ctx.slot_volume_avg or 0.0)
        ratio = (vol / slot_avg) if slot_avg > 0 else 0.0
        vol_ok = slot_avg > 0 and vol > p["vol_mult"] * slot_avg
        if slot_avg <= 0:
            vol_why = f"5-day same-slot avg volume missing/zero hai (actual {int(vol):,} shares)."
        else:
            vol_why = (
                f"5m Candle Volume kam tha: Minimum > {int(slot_avg * p['vol_mult']):,} shares "
                f"({p['vol_mult']:.1f}x of 5-day avg {int(slot_avg):,}) chahiye tha, par actual sirf {int(vol):,} ({ratio:.2f}x) aaya."
            )
        ev.add_rule(
            5, "5m Slot Volume", vol_ok,
            f"{int(vol):,} vs avg {int(slot_avg):,} ({ratio:.2f}x)",
            f"> {p['vol_mult']:.1f}x 5-day same-slot avg",
            "" if vol_ok else vol_why,
            code="vol > vol_mult * ctx.slot_volume_avg",
        )

        # Check 6: Day RVOL
        rvol_ok = ctx.rvol >= p["rvol_min"]
        ev.add_rule(
            6, "Day RVOL", rvol_ok,
            f"{ctx.rvol:.2f}x cumulative",
            f">= {p['rvol_min']:.1f}x",
            "" if rvol_ok else f"Din ka cumulative RVOL kam tha: Minimum >= {p['rvol_min']:.1f}x chahiye, actual {ctx.rvol:.2f}x tha.",
            code="ctx.rvol >= rvol_min",
        )

        # Check 7: Gap-Trap, No-Chase, Stop Width & Fresh Symbol
        gap_ok = (ctx.day_open < ctx.pdh) if side == "LONG" else (ctx.day_open > ctx.pdl)
        ext = ((close - ctx.pdh) / ctx.atr) if side == "LONG" else ((ctx.pdl - close) / ctx.atr) if ctx.atr > 0 else 99.0
        chase_ok = ext < p["max_chase_atr"]
        stop_pct = (r_pts / close) if close > 0 else 1.0
        stop_ok = stop_pct <= p["max_stop_pct"]
        fresh_ok = not (ctx.traded_today or ctx.has_position(symbol))
        gate7_ok = gap_ok and chase_ok and stop_ok and fresh_ok
        gate7_whys = []
        if not fresh_ok:
            gate7_whys.append("Already signaled/traded today")
        if not gap_ok:
            lvl_nm = "PDH" if side == "LONG" else "PDL"
            lvl_val = ctx.pdh if side == "LONG" else ctx.pdl
            gate7_whys.append(f"Day Open ₹{ctx.day_open:.2f} pehle hi {lvl_nm} (₹{lvl_val:.2f}) cross kar chuka tha")
        if not chase_ok:
            gate7_whys.append(f"Extended {ext:.2f} ATR >= {p['max_chase_atr']:.1f} ATR max chase")
        if not stop_ok:
            gate7_whys.append(f"Stop width {stop_pct * 100:.2f}% > {p['max_stop_pct'] * 100:.1f}% max")
        ev.add_rule(
            7, "Gap, No-Chase & Stop Risk", gate7_ok,
            f"Open {ctx.day_open:.2f}, ext {ext:.2f} ATR, stop {stop_pct * 100:.2f}%",
            f"No gap-trap, ext < {p['max_chase_atr']:.1f} ATR, stop <= {p['max_stop_pct']*100:.1f}%, fresh",
            "; ".join(gate7_whys),
            code="gap_ok and ext < max_chase_atr and stop_pct <= max_stop_pct",
        )

        all_ok = all(c["passed"] for c in ev.checks)
        reason_txt = (
            f"{side} breakout: vol {ratio:.1f}x slot, RVOL {ctx.rvol:.2f}, stop {stop_pct * 100:.2f}%, R:R 1:{p['target_r']:.1f}"
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
        res = self.evaluate_signal(symbol, bars, ctx)
        return res["signal"]

    def on_exit_check(self, position, bars, ctx):
        return None
