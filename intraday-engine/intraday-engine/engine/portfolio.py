"""Pure sizing, portfolio caps, cost calculation, MTM and daily loss limits (Phase 4)."""
import math

from core.cost_model import lookup as lookup_cost_block


def notional_cap(cfg) -> float:
    return (float(cfg.capital) * float(cfg.leverage)) / max(1, int(cfg.max_open_positions))


def compute_position_size(cfg, entry_price: float, stop_loss: float):
    """Return (qty, actual_risk_rs, reject_reason)."""
    if entry_price is None or stop_loss is None or entry_price <= 0:
        return 0, 0.0, "Invalid entry or stop price"
    r_per_share = abs(float(entry_price) - float(stop_loss))
    if r_per_share <= 0:
        return 0, 0.0, "Zero stop distance"

    raw_qty = math.floor(float(cfg.risk_per_trade_rs) / r_per_share)
    cap_rs = notional_cap(cfg)
    max_qty_by_cap = math.floor(cap_rs / float(entry_price))
    qty = min(raw_qty, max_qty_by_cap)
    actual_risk = round(qty * r_per_share, 2)

    if qty <= 0:
        return 0, 0.0, f"Notional cap ₹{cap_rs:,.0f} allows 0 shares at ₹{entry_price:.2f}"
    if actual_risk < float(cfg.min_achievable_risk_rs):
        return 0, actual_risk, (
            f"Notional cap leaves risk ₹{actual_risk:.0f} < min ₹{cfg.min_achievable_risk_rs:.0f}"
        )
    return int(qty), actual_risk, ""


def estimate_round_trip_cost(
    entry_price: float,
    exit_price: float,
    qty: int,
    product: str = "MIS",
    exchange: str = "NSE",
    gst_rate: float = 0.18,
) -> float:
    """Round-trip brokerage + 18% GST + statutory fees using vendor core.cost_model."""
    if qty <= 0 or entry_price <= 0 or exit_price <= 0:
        return 0.0
    block = lookup_cost_block(product, exchange)
    entry_turn = float(entry_price) * int(qty)
    exit_turn = float(exit_price) * int(qty)
    statutory = (entry_turn + exit_turn) * float(block.fees)
    brokerage = float(block.fixed_fees) * 2.0 * (1.0 + float(gst_rate))
    return round(statutory + brokerage, 2)


def compute_position_mtm(pos: dict, ltp: float | None):
    """Return (gross_pnl_rs, r_multiple) for an open position at ltp."""
    entry = float(pos["entry_price"])
    qty = int(pos["qty"])
    init_stop = float(pos.get("initial_stop") or pos["stop_loss"])
    r_per_share = abs(entry - init_stop)
    if ltp is None or ltp <= 0:
        return 0.0, 0.0
    sign = 1.0 if pos["side"] == "LONG" else -1.0
    pnl = sign * (float(ltp) - entry) * qty
    r_mult = (sign * (float(ltp) - entry) / r_per_share) if r_per_share > 0 else 0.0
    return round(pnl, 2), round(r_mult, 2)


def check_entry_gates(
    cfg,
    open_positions: list,
    today_summary: dict,
    symbol: str,
    sector: str,
    side: str,
    ltp: float | None,
    decision_price: float,
    atr: float,
    traded_symbols_today: set,
    free_ram_mb: float | None,
    analyze_ok: bool,
    oa_ok: bool,
):
    """Pure: verify engine-side entry limits and no-chase before placing a paper entry."""
    if not oa_ok:
        return False, "OpenAlgo unreachable"
    if not analyze_ok:
        return False, "Analyze mode not ON"
    if free_ram_mb is not None and free_ram_mb < float(cfg.block_free_mb):
        return False, f"Free RAM {free_ram_mb:.0f} MB < {cfg.block_free_mb} MB"
    if len(open_positions) >= int(cfg.max_open_positions):
        return False, f"Max open positions ({cfg.max_open_positions}) reached"
    sec_count = sum(1 for p in open_positions if p.get("sector") == sector)
    if sec_count >= int(cfg.max_positions_per_sector):
        return False, f"Sector cap ({cfg.max_positions_per_sector} in {sector}) reached"
    if any(p.get("symbol") == symbol for p in open_positions):
        return False, f"Already open in {symbol}"
    if symbol in traded_symbols_today:
        return False, f"Already traded {symbol} today"
    if today_summary["trades_taken"] >= int(cfg.max_trades_per_day):
        return False, f"Max trades/day ({cfg.max_trades_per_day}) reached"
    if today_summary["loss_limit_hit"]:
        return False, f"Daily loss limit (₹{cfg.daily_loss_limit_rs:.0f}) reached"

    if ltp is None or ltp <= 0:
        return False, "No live LTP at order time"
    max_chase_atr = float(cfg.strategy_params.get("max_chase_atr", 0.5))
    if atr and atr > 0 and max_chase_atr > 0:
        moved = (ltp - decision_price) if side == "LONG" else (decision_price - ltp)
        if moved > max_chase_atr * float(atr):
            return False, f"No-chase at order time: LTP {ltp:.2f} moved {moved / atr:.2f} ATR"

    return True, ""


def summarize_today(cfg, open_positions: list, closed_trades: list, prices: dict):
    """Compute today's trade counts, realised P&L, open MTM, costs, net P&L in ₹ and R."""
    realized_gross = sum(float(t.get("gross_pnl") or 0.0) for t in closed_trades)
    costs = sum(float(t.get("costs") or 0.0) for t in closed_trades)

    open_mtm = 0.0
    for p in open_positions:
        ltp = (prices.get(p["symbol"]) or {}).get("ltp")
        pnl, _ = compute_position_mtm(p, ltp)
        open_mtm += pnl

    net_pnl = round(realized_gross + open_mtm - costs, 2)
    risk_unit = max(1.0, float(cfg.risk_per_trade_rs))
    net_r = round(net_pnl / risk_unit, 2)

    trades_taken = len(open_positions) + len(closed_trades)
    max_trades = int(cfg.max_trades_per_day)
    trades_left = max(0, max_trades - trades_taken)

    loss_limit = float(cfg.daily_loss_limit_rs)
    loss_limit_hit = net_pnl <= -loss_limit
    loss_remaining = round(max(0.0, loss_limit + net_pnl), 2)

    return {
        "trades_taken": trades_taken,
        "max_trades": max_trades,
        "trades_left": trades_left,
        "open_count": len(open_positions),
        "closed_count": len(closed_trades),
        "realized_pnl": round(realized_gross - costs, 2),
        "open_mtm": round(open_mtm, 2),
        "costs": round(costs, 2),
        "net_pnl": net_pnl,
        "net_r": net_r,
        "loss_limit_rs": loss_limit,
        "loss_limit_hit": loss_limit_hit,
        "loss_remaining_rs": loss_remaining,
    }
