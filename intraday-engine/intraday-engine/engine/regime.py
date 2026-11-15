"""Pure market regime calculation on NIFTY 5m bars + universe breadth (spec section 4)."""
import math

import numpy as np
from openalgo import ta


def compute_breadth(kept_levels, last_prices):
    """Return (advancers, decliners, ad_ratio) vs previous day close."""
    adv = dec = 0
    for sym, row in kept_levels.items():
        ltp = last_prices.get(sym)
        pdc = row.get("pdc")
        if ltp and pdc and pdc > 0:
            if ltp > pdc:
                adv += 1
            elif ltp < pdc:
                dec += 1
    if adv == 0 and dec == 0:
        return 0, 0, None
    ratio = float(adv) if dec == 0 else adv / dec
    return adv, dec, round(ratio, 3)


def _count_crosses(diff_series):
    """Count sign changes in close - session_mean across consecutive bars."""
    vals = [float(v) for v in diff_series if not math.isnan(v) and v != 0.0]
    crosses = 0
    for i in range(1, len(vals)):
        if (vals[i - 1] > 0) != (vals[i] > 0):
            crosses += 1
    return crosses


def _eval_one_bar(nifty_bars, breadth, cfg, state):
    """Evaluate a single closed NIFTY 5m bar and update confirmation state."""
    adx_val = None
    if len(nifty_bars) >= cfg.adx_period * 2:
        try:
            adx_res = ta.adx(nifty_bars["high"], nifty_bars["low"], nifty_bars["close"], cfg.adx_period)
            last_adx = float(adx_res[2].iloc[-1])
            if not math.isnan(last_adx):
                adx_val = round(last_adx, 2)
        except Exception:
            adx_val = None

    today_date = nifty_bars.index[-1].date()
    today_bars = nifty_bars[nifty_bars.index.date == today_date]
    if len(today_bars) == 0:
        today_bars = nifty_bars.tail(1)

    tp = (today_bars["high"] + today_bars["low"] + today_bars["close"]) / 3.0
    sess_mean_series = tp.expanding().mean()
    sess_mean = float(sess_mean_series.iloc[-1])
    nifty_close = float(today_bars["close"].iloc[-1])

    diff = today_bars["close"] - sess_mean_series
    crosses = _count_crosses(diff.tail(cfg.crosses_lookback))

    day_open = float(today_bars["open"].iloc[0])
    day_high = float(today_bars["high"].max())
    day_low = float(today_bars["low"].min())
    day_eff = round(abs(nifty_close - day_open) / (day_high - day_low), 3) if day_high > day_low else 0.0

    choppy_hits = 0
    if adx_val is not None and adx_val < cfg.adx_below:
        choppy_hits += 1
    if crosses >= cfg.crosses_min:
        choppy_hits += 1
    if breadth is not None and cfg.breadth_low <= breadth <= cfg.breadth_high:
        choppy_hits += 1

    if choppy_hits >= 2:
        raw = "CHOPPY"
    elif nifty_close > sess_mean and breadth is not None and breadth > 1.0:
        raw = "TREND_UP"
    elif nifty_close < sess_mean and breadth is not None and breadth < 1.0:
        raw = "TREND_DOWN"
    else:
        raw = "CHOPPY"

    active = state["active"]
    pending_raw = state["pending_raw"]
    pending_count = state["pending_count"]

    if raw == active:
        pending_raw = None
        pending_count = 0
    else:
        if raw == pending_raw:
            pending_count += 1
        else:
            pending_raw = raw
            pending_count = 1
        if pending_count >= cfg.confirm_bars:
            active = raw
            pending_raw = None
            pending_count = 0

    next_state = {"active": active, "pending_raw": pending_raw, "pending_count": pending_count}
    return {
        "active": active,
        "raw": raw,
        "pending_raw": pending_raw,
        "pending_count": pending_count,
        "adx": adx_val,
        "session_mean": round(sess_mean, 2),
        "nifty_close": round(nifty_close, 2),
        "crosses": crosses,
        "breadth": breadth,
        "day_efficiency": day_eff,
    }, next_state


def evaluate_regime(nifty_bars, breadth, cfg, prev_state=None):
    """Pure: compute 4 regime inputs, raw state, and 2-bar confirmed active regime.

    When prev_state is None, warms up confirmation across the last confirm_bars of today.
    Returns (regime_dict, next_state).
    """
    if nifty_bars is None or len(nifty_bars) == 0:
        state = dict(prev_state or {"active": "CHOPPY", "pending_raw": None, "pending_count": 0})
        return {
            "active": state["active"], "raw": "CHOPPY",
            "pending_raw": state["pending_raw"], "pending_count": state["pending_count"],
            "adx": None, "session_mean": None, "nifty_close": None,
            "crosses": 0, "breadth": breadth, "day_efficiency": None,
        }, state

    if prev_state is None:
        today_date = nifty_bars.index[-1].date()
        n_today = int((nifty_bars.index.date == today_date).sum())
        steps = max(1, min(n_today, cfg.confirm_bars))
        state = {"active": "CHOPPY", "pending_raw": None, "pending_count": 0}
        res = None
        for k in range(steps - 1, -1, -1):
            sub = nifty_bars.iloc[: len(nifty_bars) - k] if k > 0 else nifty_bars
            res, state = _eval_one_bar(sub, breadth, cfg, state)
        return res, state

    return _eval_one_bar(nifty_bars, breadth, cfg, dict(prev_state))
