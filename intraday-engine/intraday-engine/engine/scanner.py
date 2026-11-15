"""Pure scanner: candidates, proximity gate, z-score ranking, shortlist and armed set (spec section 6)."""
import numpy as np


def _zscores(values):
    if len(values) < 2:
        return [0.0] * len(values)
    arr = np.array(values, dtype=float)
    std = float(arr.std(ddof=0))
    if std <= 1e-12:
        return [0.0] * len(values)
    mean = float(arr.mean())
    return [float((v - mean) / std) for v in arr]


def scan_candidates(regime_active, sectors, kept_levels, last_prices, nifty_pct, cfg):
    """Return {"side": "LONG"|"SHORT"|None, "shortlist": [...], "armed": [...]}."""
    if regime_active not in ("TREND_UP", "TREND_DOWN") or nifty_pct is None:
        return {"side": None, "shortlist": [], "armed": []}

    side = "LONG" if regime_active == "TREND_UP" else "SHORT"
    want_mark = "STRONG" if side == "LONG" else "WEAK"
    allowed_sectors = {s["sector"] for s in sectors if s["mark"] == want_mark}
    if not allowed_sectors:
        return {"side": side, "shortlist": [], "armed": []}

    candidates = []
    for sym, row in kept_levels.items():
        if row["sector"] not in allowed_sectors:
            continue
        ltp = last_prices.get(sym)
        pdc, pdh, pdl, atr = row.get("pdc"), row.get("pdh"), row.get("pdl"), row.get("atr")
        if not (ltp and pdc and pdh and pdl and atr and pdc > 0 and atr > 0):
            continue

        stock_pct = (ltp - pdc) / pdc * 100.0
        stock_rs = stock_pct - nifty_pct
        prox = (pdh - ltp) / atr if side == "LONG" else (ltp - pdl) / atr
        if not (-cfg.proximity_max_atr <= prox <= cfg.proximity_max_atr):
            continue

        signed_rs = stock_rs if side == "LONG" else -stock_rs
        armed = (ltp > pdh * (1.0 + cfg.arm_buffer_pct)) if side == "LONG" else (ltp < pdl * (1.0 - cfg.arm_buffer_pct))
        candidates.append({
            "symbol": sym,
            "sector": row["sector"],
            "side": side,
            "ltp": round(ltp, 2),
            "level": round(pdh if side == "LONG" else pdl, 2),
            "stock_rs": round(stock_rs, 2),
            "proximity": round(prox, 3),
            "signed_rs": signed_rs,
            "abs_prox": abs(prox),
            "armed": armed,
        })

    if not candidates:
        return {"side": side, "shortlist": [], "armed": []}

    z_rs = _zscores([c["signed_rs"] for c in candidates])
    z_prox = _zscores([c["abs_prox"] for c in candidates])
    for c, zr, zp in zip(candidates, z_rs, z_prox):
        c["score"] = round(zr - zp, 2)
        c.pop("signed_rs", None)
        c.pop("abs_prox", None)

    candidates.sort(key=lambda x: x["score"], reverse=True)
    shortlist = candidates[: cfg.shortlist_size]
    armed = [c["symbol"] for c in shortlist if c["armed"]]
    return {"side": side, "shortlist": shortlist, "armed": armed}
