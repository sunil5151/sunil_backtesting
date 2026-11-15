"""Pure sector relative strength ranking (spec section 5)."""
from statistics import median


def rank_sectors(kept_levels, last_prices, nifty_pct, cfg):
    """Return list of eligible sectors ranked by RS vs NIFTY descending.

    Each item: {"rank", "sector", "members", "return_pct", "rs_pct", "mark"}
    where mark is "STRONG", "WEAK", or "".
    """
    if nifty_pct is None:
        return []

    by_sector = {}
    for sym, row in kept_levels.items():
        ltp = last_prices.get(sym)
        pdc = row.get("pdc")
        if ltp and pdc and pdc > 0:
            pct = (ltp - pdc) / pdc * 100.0
            by_sector.setdefault(row["sector"], []).append(pct)

    ranked = []
    for sec, pcts in by_sector.items():
        if len(pcts) < cfg.min_members_per_sector:
            continue
        med = median(pcts)
        rs = med - nifty_pct
        ranked.append({
            "sector": sec,
            "members": len(pcts),
            "return_pct": round(med, 2),
            "rs_pct": round(rs, 2),
            "mark": "",
        })

    ranked.sort(key=lambda x: x["rs_pct"], reverse=True)
    for i, item in enumerate(ranked, 1):
        item["rank"] = i

    strong_count = 0
    for item in ranked:
        if item["rs_pct"] > cfg.rs_threshold_pct and strong_count < cfg.sector_top_n:
            item["mark"] = "STRONG"
            strong_count += 1

    weak_count = 0
    for item in reversed(ranked):
        if item["rs_pct"] < -cfg.rs_threshold_pct and weak_count < cfg.sector_top_n:
            if item["mark"] == "":
                item["mark"] = "WEAK"
                weak_count += 1

    return ranked
