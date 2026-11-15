"""Pure tick-level exit and +1R breakeven evaluation for open paper positions (Phase 4)."""
from datetime import time as dtime

from engine.portfolio import compute_position_mtm


def evaluate_position_exit(
    pos: dict,
    ltp: float | None,
    now_t: dtime,
    square_off_t: dtime,
    breakeven_at_r: float = 1.0,
    tick_age_s: float = 0.0,
    stale_seconds: float = 5.0,
):
    """Evaluate one open position against current LTP and clock.

    Returns dict:
      {
        "breakeven_triggered": bool,
        "new_stop": float | None,
        "new_watermark": float | None,
        "exit_reason": str | None,      # "STOP" | "BREAKEVEN" | "TARGET" | "SQUARE_OFF"
        "r_now": float,
        "pnl_now": float,
        "stale_flag": bool,
      }
    """
    side = pos["side"]
    entry = float(pos["entry_price"])
    stop = float(pos["stop_loss"])
    target = float(pos["target"]) if pos.get("target") is not None else None
    be_moved = bool(pos.get("breakeven_moved"))
    watermark = float(pos.get("watermark") or entry)

    if now_t >= square_off_t:
        pnl_now, r_now = compute_position_mtm(pos, ltp)
        return {
            "breakeven_triggered": False,
            "new_stop": None,
            "new_watermark": None,
            "exit_reason": "SQUARE_OFF",
            "r_now": r_now,
            "pnl_now": pnl_now,
            "stale_flag": tick_age_s > stale_seconds,
        }

    if ltp is None or ltp <= 0:
        return {
            "breakeven_triggered": False,
            "new_stop": None,
            "new_watermark": None,
            "exit_reason": None,
            "r_now": 0.0,
            "pnl_now": 0.0,
            "stale_flag": False,
        }

    ltp = float(ltp)
    pnl_now, r_now = compute_position_mtm(pos, ltp)

    new_watermark = None
    if side == "LONG" and ltp > watermark:
        new_watermark = ltp
    elif side == "SHORT" and ltp < watermark:
        new_watermark = ltp

    be_triggered = False
    new_stop = None
    if breakeven_at_r and breakeven_at_r > 0 and not be_moved and r_now >= float(breakeven_at_r):
        if (side == "LONG" and entry > stop) or (side == "SHORT" and entry < stop):
            be_triggered = True
            new_stop = round(entry, 2)
            stop = new_stop
            be_moved = True

    exit_reason = None
    if side == "LONG":
        if ltp <= stop:
            exit_reason = "BREAKEVEN" if be_moved and abs(stop - entry) < 1e-6 else "STOP"
        elif target is not None and ltp >= target:
            exit_reason = "TARGET"
    else:
        if ltp >= stop:
            exit_reason = "BREAKEVEN" if be_moved and abs(stop - entry) < 1e-6 else "STOP"
        elif target is not None and ltp <= target:
            exit_reason = "TARGET"

    return {
        "breakeven_triggered": be_triggered,
        "new_stop": new_stop,
        "new_watermark": new_watermark,
        "exit_reason": exit_reason,
        "r_now": r_now,
        "pnl_now": pnl_now,
        "stale_flag": bool(exit_reason and tick_age_s > stale_seconds),
    }
