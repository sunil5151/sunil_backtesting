"""Universe clean-up, daily levels (PDH/PDL/PDC/ATR/20d avg), pre-filter and sector eligibility.

Reads data/sector_map.json (read-only) and writes the deduplicated universe to
cfg.clean_universe_file (data/universe_clean.json). Never edits sector_map.json.
"""
from collections import Counter
from datetime import datetime, timedelta
import json

from core.data_router import fetch_backtest_data
from core.indicator_adapter import get_indicators

from engine.oa import IST, explain


def clean_universe(cfg):
    """Deduplicate sector_map.json per spec section 3 and write cfg.clean_universe_file.

    Returns (cleaned_dict, stock_list) where stock_list is [{"symbol", "orig_symbol", "sector", "weight"}, ...].
    """
    raw = json.loads(cfg.universe_file.read_text(encoding="utf-8"))
    drop_sectors = set(cfg.drop_sectors)
    aliases = cfg.symbol_aliases

    # Pick the single highest-weight sector for each stock across remaining sectors.
    best = {}  # mapped_symbol -> (sector_name, sector_key, weight, orig_symbol, company_name)
    for skey, sinfo in raw.items():
        if skey in drop_sectors:
            continue
        sname = sinfo["name"]
        for h in sinfo.get("holdings", []):
            orig = h["symbol"]
            sym = aliases.get(orig, orig)
            w = float(h.get("weight", 0.0))
            if sym not in best or w > best[sym][2]:
                best[sym] = (sname, skey, w, orig, h.get("name", sym))

    cleaned = {}
    stocks = []
    for sym, (sname, skey, w, orig, cname) in best.items():
        sec = cleaned.setdefault(skey, {"name": sname, "holdings": []})
        sec["holdings"].append({"symbol": sym, "orig_symbol": orig, "name": cname, "weight": w})
        stocks.append({"symbol": sym, "orig_symbol": orig, "sector": sname, "weight": w})

    for sec in cleaned.values():
        sec["holdings"].sort(key=lambda x: x["weight"], reverse=True)
    stocks.sort(key=lambda x: (x["sector"], x["symbol"]))

    cfg.clean_universe_file.parent.mkdir(parents=True, exist_ok=True)
    cfg.clean_universe_file.write_text(json.dumps(cleaned, indent=2), encoding="utf-8")
    return cleaned, stocks


def _fno_names(link):
    """Return set of underlying names that have NFO equity futures."""
    names = set()
    now = datetime.now(IST)
    # Query the next 3 monthly expiries (e.g. NOVFUT, DECFUT, JANFUT) to avoid the 500-row search cap.
    for offset in range(3):
        m = (now.month - 1 + offset) % 12 + 1
        mon = datetime(2000, m, 1).strftime("%b").upper()
        resp = link.search(query=f"{mon}FUT", exchange="NFO")
        if explain(resp)[0] == "ok":
            for item in resp.get("data") or []:
                if item.get("instrumenttype") == "FUT" and item.get("name"):
                    names.add(item["name"])
    return names


def load_or_build_levels(cfg, link, store, on_progress=None, stop_event=None):
    """Load today's daily levels from SQLite, or fetch & pre-filter from OpenAlgo once per day.

    Returns (rows, from_cache) where each row is a dict with symbol, sector, pdh, pdl, pdc,
    atr, atr_pct, avg_vol, avg_val_cr, kept, drop_reason.
    """
    today_dt = datetime.now(IST).date()
    today = today_dt.isoformat()

    cached = store.get_daily_levels(today)
    if cached:
        # Ensure cleaned file also exists on disk.
        if not cfg.clean_universe_file.exists():
            clean_universe(cfg)
        return cached, True

    _, stocks = clean_universe(cfg)
    fno_set = _fno_names(link) if cfg.fno_only else None
    ind = get_indicators()
    start = (today_dt - timedelta(days=55)).isoformat()

    rows = []
    total = len(stocks)
    for idx, st in enumerate(stocks, 1):
        if stop_event and stop_event.is_set():
            break
        sym = st["symbol"]
        sec = st["sector"]
        if on_progress and (idx == 1 or idx % 10 == 0 or idx == total):
            on_progress(idx, total, sym)

        base = {
            "symbol": sym, "sector": sec,
            "pdh": None, "pdl": None, "pdc": None,
            "atr": None, "atr_pct": None, "avg_vol": None, "avg_val_cr": None,
            "kept": False, "drop_reason": "",
        }

        if fno_set is not None and sym not in fno_set:
            base["drop_reason"] = "Not in F&O"
            rows.append(base)
            continue

        sresp = link.symbol(symbol=sym, exchange=cfg.exchange)
        if explain(sresp)[0] != "ok" or not sresp.get("data"):
            base["drop_reason"] = "Symbol not found"
            rows.append(base)
            continue

        try:
            df = fetch_backtest_data(link, sym, cfg.exchange, "D", start, today, source="api")
        except Exception:
            df = None

        if df is None or not hasattr(df, "columns") or len(df) == 0:
            base["drop_reason"] = "No daily history"
            rows.append(base)
            continue

        # Exclude today's live/incomplete daily bar so PDH/PDL/PDC come from completed sessions only.
        prev = df[df.index.date < today_dt]
        if len(prev) < max(cfg.atr_period + 1, cfg.avg_days):
            base["drop_reason"] = f"Short history ({len(prev)}d)"
            rows.append(base)
            continue

        pdh = float(prev["high"].iloc[-1])
        pdl = float(prev["low"].iloc[-1])
        pdc = float(prev["close"].iloc[-1])
        atr_s = ind.atr(prev["high"], prev["low"], prev["close"], cfg.atr_period)
        atr = float(atr_s.iloc[-1])
        atr_pct = (atr / pdc * 100.0) if pdc > 0 else 0.0
        tail = prev.tail(cfg.avg_days)
        avg_vol = float(tail["volume"].mean())
        avg_val_cr = float((tail["close"] * tail["volume"]).mean() / 1e7)

        reasons = []
        if pdc < cfg.min_price:
            reasons.append(f"Price ₹{pdc:.0f} < ₹{cfg.min_price:.0f}")
        elif pdc > cfg.max_price:
            reasons.append(f"Price ₹{pdc:.0f} > ₹{cfg.max_price:.0f}")
        if avg_val_cr < cfg.min_traded_value_cr:
            reasons.append(f"20d val ₹{avg_val_cr:.1f}Cr < ₹{cfg.min_traded_value_cr:.0f}Cr")
        if atr_pct < cfg.min_atr_pct:
            reasons.append(f"ATR {atr_pct:.2f}% < {cfg.min_atr_pct:.1f}%")

        base.update({
            "pdh": round(pdh, 2), "pdl": round(pdl, 2), "pdc": round(pdc, 2),
            "atr": round(atr, 2), "atr_pct": round(atr_pct, 2),
            "avg_vol": round(avg_vol, 0), "avg_val_cr": round(avg_val_cr, 2),
            "kept": len(reasons) == 0,
            "drop_reason": "; ".join(reasons),
        })
        rows.append(base)

    if rows and not (stop_event and stop_event.is_set()):
        store.save_daily_levels(today, rows)
    return rows, False


def sector_eligibility(rows, min_members):
    """Return {sector_name: {"kept": int, "total": int, "eligible": bool}}."""
    counts = {}
    for r in rows:
        sec = r["sector"]
        entry = counts.setdefault(sec, {"kept": 0, "total": 0, "eligible": False})
        entry["total"] += 1
        if r["kept"]:
            entry["kept"] += 1
    for entry in counts.values():
        entry["eligible"] = entry["kept"] >= min_members
    return counts


def kept_by_symbol(rows, min_members):
    """Return {symbol: level_row} for kept stocks in eligible sectors only."""
    elig = sector_eligibility(rows, min_members)
    return {
        r["symbol"]: r
        for r in rows
        if r["kept"] and elig.get(r["sector"], {}).get("eligible", False)
    }
