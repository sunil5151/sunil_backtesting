"""Consolidated per-candle scan & signal analysis archive for AWS S3 (with local fallback).

Strict anti-spam rule:
- ONE consolidated JSON file per candle bar:
  scans/<YYYY-MM-DD>/<HH-MM>_Scan_<N>Stocks_<S>Signals_<P>Passed.json
- ONE lightweight daily index per date folder: scans/<YYYY-MM-DD>/INDEX.json
- ONE activity log per date folder: scans/<YYYY-MM-DD>/ACTIVITY.json
Never creates separate files per stock or per second, and removes local scan JSON once S3 upload succeeds.
"""
from datetime import datetime, timezone
import hashlib
import hmac
import json
from pathlib import Path
from urllib.parse import quote
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET


def _sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _sigv4_headers(cfg, method: str, uri_path: str, query: str = "", body: bytes = b"", content_type: str = ""):
    now = datetime.now(timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")
    host = f"{cfg.s3_bucket}.s3.{cfg.s3_region}.amazonaws.com"
    payload_hash = hashlib.sha256(body).hexdigest()

    hdrs = {
        "host": host,
        "x-amz-content-sha256": payload_hash,
        "x-amz-date": amz_date,
    }
    if content_type:
        hdrs["content-type"] = content_type

    signed_keys = sorted(hdrs.keys())
    canonical_headers = "".join(f"{k}:{hdrs[k]}\n" for k in signed_keys)
    signed_headers = ";".join(signed_keys)
    canonical_request = f"{method}\n{uri_path}\n{query}\n{canonical_headers}\n{signed_headers}\n{payload_hash}"

    scope = f"{date_stamp}/{cfg.s3_region}/s3/aws4_request"
    string_to_sign = (
        f"AWS4-HMAC-SHA256\n{amz_date}\n{scope}\n"
        + hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
    )
    k_date = _sign(("AWS4" + cfg.aws_secret_access_key).encode("utf-8"), date_stamp)
    k_region = _sign(k_date, cfg.s3_region)
    k_svc = _sign(k_region, "s3")
    k_sign = _sign(k_svc, "aws4_request")
    sig = hmac.new(k_sign, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    out = {
        "x-amz-date": amz_date,
        "x-amz-content-sha256": payload_hash,
        "Authorization": f"AWS4-HMAC-SHA256 Credential={cfg.aws_access_key_id}/{scope}, SignedHeaders={signed_headers}, Signature={sig}",
    }
    if content_type:
        out["Content-Type"] = content_type
    url = f"https://{host}{uri_path}" + (f"?{query}" if query else "")
    return url, out


def _s3_put_bytes(cfg, key: str, body: bytes, content_type: str = "application/octet-stream", timeout: int = 20) -> tuple[bool, str]:
    """Upload raw bytes (PDF, Markdown, JSON, etc.) to S3 using SigV4."""
    if not cfg.has_s3:
        return False, "S3 credentials not configured"
    uri = "/" + quote(key.lstrip("/"), safe="/-_.~")
    url, hdrs = _sign_request(cfg, "PUT", uri, body=body, content_type=content_type)
    req = urllib.request.Request(url, data=body, method="PUT", headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 300, f"HTTP {resp.status}"
    except urllib.error.HTTPError as e:
        return False, f"S3 PUT HTTP {e.code}"
    except Exception as e:
        return False, f"S3 PUT failed: {type(e).__name__}"


def _s3_head_or_get_meta(cfg, key: str, timeout: int = 10) -> tuple[bool, int, str]:
    """Check whether an S3 object exists and return (ok, content_length, detail)."""
    if not cfg.has_s3:
        return False, 0, "S3 not configured"
    uri = "/" + quote(key.lstrip("/"), safe="/-_.~")
    url, hdrs = _sign_request(cfg, "HEAD", uri)
    req = urllib.request.Request(url, method="HEAD", headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            size = int(resp.headers.get("Content-Length") or 0)
            ctype = resp.headers.get("Content-Type", "")
            return 200 <= resp.status < 300, size, f"HTTP {resp.status} ({ctype})"
    except urllib.error.HTTPError as e:
        return False, 0, f"HTTP {e.code}"
    except Exception as e:
        return False, 0, f"{type(e).__name__}: {e}"


def _s3_put_json(cfg, key: str, obj: dict):
    if not cfg.has_s3:
        return False, "S3 credentials not configured"
    body = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return _s3_put_bytes(cfg, key, body, content_type="application/json", timeout=8)


def _sign_request(cfg, method, uri, query="", body=b"", content_type=""):
    return _sigv4_headers(cfg, method, uri, query=query, body=body, content_type=content_type)


def _s3_get_json(cfg, key: str):
    if not cfg.has_s3:
        return None, "S3 not configured"
    uri = "/" + quote(key.lstrip("/"), safe="/-_.~")
    url, hdrs = _sigv4_headers(cfg, "GET", uri)
    req = urllib.request.Request(url, method="GET", headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read().decode("utf-8")), "ok"
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def _s3_list_prefixes(cfg, prefix: str = "scans/"):
    if not cfg.has_s3:
        return []
    q_parts = [
        f"delimiter={quote('/', safe='')}",
        "list-type=2",
        f"prefix={quote(prefix, safe='')}",
    ]
    query = "&".join(q_parts)
    url, hdrs = _sigv4_headers(cfg, "GET", "/", query=query)
    req = urllib.request.Request(url, method="GET", headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            xml_text = resp.read().decode("utf-8")
        root = ET.fromstring(xml_text)
        ns = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
        out = []
        for cp in root.findall("s3:CommonPrefixes", ns):
            p = cp.findtext("s3:Prefix", default="", namespaces=ns)
            day = p.rstrip("/").split("/")[-1]
            if day:
                out.append(day)
        return sorted(out, reverse=True)
    except Exception:
        return []


def make_signal_ids(day: str, bar_time: str, symbol: str, side: str, idx_1based: int):
    """Build compact display signal_no and full searchable signal_id."""
    clean_side = (side or "NA").upper()
    sig_no = f"{bar_time}-{symbol}-#{idx_1based}"
    sig_id = f"{day}_{bar_time}_{symbol}_{clean_side}_#{idx_1based}"
    return sig_no, sig_id


def make_scan_names(day: str, bar_time: str, kept_count: int, sig_count: int, passed_count: int):
    """Build self-describing S3 filename and scan ID (no '#' in S3 object key)."""
    hhmm = bar_time.replace(":", "-")
    scan_file = f"{hhmm}_Scan_{int(kept_count)}Stocks_{int(sig_count)}Signals_{int(passed_count)}Passed.json"
    scan_id = f"{day}_{bar_time}_Scan_{int(kept_count)}Stocks_{int(sig_count)}Signals"
    return scan_file, scan_id


def strategy_meta_dict(cfg, strategy_mod=None, strategy=None, qualification=None):
    has_on_bar = bool(strategy is not None and callable(getattr(strategy, "on_bar", None)))
    has_eval = bool(strategy is not None and callable(getattr(strategy, "evaluate_signal", None)))
    has_exit = bool(strategy is not None and callable(getattr(strategy, "on_exit_check", None)))
    unplugged = strategy is None or not str(cfg.strategy_file or "").strip()
    return {
        "name": cfg.strategy_name or ("unplugged" if unplugged else "custom"),
        "file": cfg.strategy_file,
        "unplugged": unplugged,
        "socket_available": (has_on_bar or has_eval) and not unplugged,
        "hooks": [h for h, ok in (("evaluate_signal", has_eval), ("on_bar", has_on_bar), ("on_exit_check", has_exit)) if ok],
        "timeframe": getattr(strategy_mod, "TIMEFRAME", "5m") if strategy_mod else "5m",
        "lookback_bars": getattr(strategy_mod, "LOOKBACK_BARS", 50) if strategy_mod else 50,
        "market_type": getattr(strategy_mod, "MARKET_TYPE", "NSE_INTRADAY_EQUITY") if strategy_mod else "NSE_INTRADAY_EQUITY",
        "regimes": list(getattr(strategy_mod, "REGIMES", ("TREND_UP", "TREND_DOWN"))) if strategy_mod else [],
        "choppy_treatment": getattr(strategy_mod, "CHOPPY_TREATMENT", "Not declared") if strategy_mod else "Socket empty",
        "trending_treatment": getattr(strategy_mod, "TRENDING_TREATMENT", "Not declared") if strategy_mod else "Socket empty",
        "checks_schema": list(getattr(strategy_mod, "CHECKS_SCHEMA", [])) if strategy_mod else [],
        "sides": list(getattr(strategy_mod, "SIDES", ("LONG", "SHORT"))) if strategy_mod else ["LONG", "SHORT"],
        "params": dict(getattr(strategy, "params", cfg.strategy_params or {})) if strategy is not None else {},
        "qualification": qualification,
        "risk": {
            "capital_rs": cfg.capital,
            "product": cfg.product,
            "risk_per_trade_rs": cfg.risk_per_trade_rs,
            "leverage": cfg.leverage,
            "notional_cap_rs": round((cfg.capital * cfg.leverage) / max(1, cfg.max_open_positions), 0),
            "min_achievable_risk_rs": cfg.min_achievable_risk_rs,
            "max_open_positions": cfg.max_open_positions,
            "max_positions_per_sector": cfg.max_positions_per_sector,
            "max_trades_per_day": cfg.max_trades_per_day,
            "daily_loss_limit_rs": cfg.daily_loss_limit_rs,
        },
    }


def _local_dir(cfg, day: str) -> Path:
    d = cfg.root / "data" / "scan_archive" / day
    d.mkdir(parents=True, exist_ok=True)
    return d


def build_all_stocks_rows(
    day_levels: dict,
    prices: dict,
    sectors: list,
    scanner: dict,
    armed_syms: list,
    signals_section: list | None = None,
    bar_time: str = "",
):
    """Classify every kept stock in this candle so the consolidated file explains all 72."""
    sec_map = {s["sector"]: s for s in (sectors or [])}
    short_map = {x["symbol"]: x for x in (scanner.get("shortlist") or [])}
    sig_by_sym = {s["symbol"]: s for s in (signals_section or []) if s.get("symbol")}
    armed_set = set(armed_syms or [])
    side = scanner.get("side")
    want_mark = "STRONG" if side == "LONG" else ("WEAK" if side == "SHORT" else None)

    rows = []
    counts = {
        "prefilter_kept": len(day_levels),
        "no_price": 0,
        "sector_filtered": 0,
        "far_from_level": 0,
        "near_level": 0,
        "shortlisted": len(short_map),
        "armed": len(armed_set),
    }

    for sym in sorted(day_levels.keys()):
        lv = day_levels[sym]
        sec = lv["sector"]
        sm = sec_map.get(sec, {})
        mark = sm.get("mark", "")
        ltp = prices.get(sym)
        pdh = float(lv["pdh"])
        pdl = float(lv["pdl"])
        atr = float(lv.get("atr") or 0.0)

        if side == "SHORT":
            min_cond = (
                f"SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), "
                f"(2) LTP PDL ₹{pdl:.2f} ke 0.5 ATR (₹{0.5 * atr:.2f}) ke andar ho, "
                f"(3) Top-5 score me aaye aur PDL+0.1% (₹{pdl * 1.001:.2f}) ke paas arm ho, "
                f"(4) 8/8 signal checks pass kare."
            )
        elif side == "LONG":
            min_cond = (
                f"LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), "
                f"(2) LTP PDH ₹{pdh:.2f} ke 0.5 ATR (₹{0.5 * atr:.2f}) ke andar ho, "
                f"(3) Top-5 score me aaye aur PDH-0.1% (₹{pdh * 0.999:.2f}) ke paas arm ho, "
                f"(4) 8/8 signal checks pass kare."
            )
        else:
            min_cond = "Market Regime TREND_UP ya TREND_DOWN hona zaroori hai (abhi CHOPPY hai)."

        if ltp is None or ltp <= 0:
            stage = "NO_PRICE"
            priority_order = 6
            detail = "No price tick/bar in this candle"
            why_not_taken = "Is 5m candle me is stock ka live price / bar nahi mila."
            counts["no_price"] += 1
        elif sym in armed_set:
            sl = short_map.get(sym, {})
            stage = "ARMED"
            priority_order = 1
            detail = f"Top-5 shortlist & within 0.1% arm buffer of {sl.get('level', '')} (prox {sl.get('proximity', '')} ATR)"
            sg = sig_by_sym.get(sym)
            if sg:
                if sg.get("status") == "would trade":
                    why_not_taken = f"PASSED ({sg.get('passed_checks', 8)}/{sg.get('total_checks', 8)} checks): Entry signal pass hua ({sg.get('reason', '')})."
                else:
                    freasons = sg.get("failed_reasons") or [sg.get("reason", "")]
                    why_not_taken = (
                        f"ARMED par Signal REJECTED ({sg.get('passed_checks', 0)}/{sg.get('total_checks', 8)} checks pass, "
                        f"{sg.get('failed_checks', 0)} fail): " + " | ".join(freasons)
                    )
            else:
                why_not_taken = "Stock ARMED hua tha; 5m bar signal checks run hue."
        elif sym in short_map:
            sl = short_map[sym]
            stage = "SHORTLIST"
            priority_order = 2
            detail = f"Top-5 shortlist (score {sl.get('score', '')}, prox {sl.get('proximity', '')} ATR), not armed yet"
            arm_lvl = round(pdh * 0.999, 2) if side == "LONG" else round(pdl * 1.001, 2)
            op_txt = ">=" if side == "LONG" else "<="
            why_not_taken = (
                f"Top-5 Shortlist me tha (Score {sl.get('score', '')}, Prox {sl.get('proximity', '')} ATR), "
                f"par Armed nahi hua kyunki LTP ₹{ltp:.2f} abhi arm level ({op_txt} ₹{arm_lvl:.2f}) tak nahi pahuncha."
            )
        elif want_mark is None:
            stage = "REGIME_CHOPPY"
            priority_order = 5
            detail = "Market regime is CHOPPY (no directional entries)"
            why_not_taken = "Market Regime CHOPPY tha, isliye kisi bhi stock me trade allowed nahi tha."
            counts["sector_filtered"] += 1
        elif mark != want_mark:
            stage = "SECTOR_FILTERED"
            priority_order = 5
            detail = f"Sector {sec} is {mark or 'NEUTRAL'} (need {want_mark})"
            why_not_taken = (
                f"Sector '{sec}' abhi {mark or 'NEUTRAL'} hai (Rank #{sm.get('rank', '-')}, RS {sm.get('rs_pct', 0)}%). "
                f"{side} trade ke liye sirf {want_mark} sector ke stocks allow hain."
            )
            counts["sector_filtered"] += 1
        else:
            lvl = float(pdh if side == "LONG" else pdl)
            prox = abs(ltp - lvl) / atr if atr > 0 else 99.0
            if prox <= 0.5:
                stage = "OUTSIDE_TOP5"
                priority_order = 3
                detail = f"Within 0.5 ATR ({prox:.2f} ATR from {lvl:.2f}) but ranked outside top-5"
                why_not_taken = f"Level ke paas tha ({prox:.2f} ATR <= 0.50 ATR), par Top-5 Shortlist score me nahi aaya (aur stocks zyada paas the)."
                counts["near_level"] += 1
            else:
                stage = "FAR_FROM_LEVEL"
                priority_order = 4
                detail = f"{prox:.2f} ATR away from {'PDH' if side == 'LONG' else 'PDL'} {lvl:.2f} (> 0.5 ATR limit)"
                why_not_taken = (
                    f"Breakout level ({'PDH' if side == 'LONG' else 'PDL'} ₹{lvl:.2f}) se bahut door tha: "
                    f"Actual distance {prox:.2f} ATR (₹{abs(ltp - lvl):.2f}), jabki Shortlist ke liye <= 0.50 ATR (<= ₹{0.5 * atr:.2f}) chahiye."
                )
                counts["far_from_level"] += 1

        priority_group = "TOP_PRIORITY" if stage in ("ARMED", "SHORTLIST", "OUTSIDE_TOP5") else "OTHER_STOCKS"
        rows.append({
            "symbol": sym,
            "sector": sec,
            "sector_mark": mark or "NEUTRAL",
            "ltp": round(float(ltp), 2) if ltp else None,
            "pdh": round(pdh, 2),
            "pdl": round(pdl, 2),
            "atr": round(atr, 2),
            "stage": stage,
            "priority_order": priority_order,
            "priority_group": priority_group,
            "min_condition": min_cond,
            "detail": detail,
            "why_not_taken": why_not_taken,
        })

    rows.sort(key=lambda r: (r["priority_order"], r["symbol"]))
    total_n = len(rows)
    tag_time = bar_time or "SCAN"
    for idx, r in enumerate(rows, 1):
        ltp_str = f"₹{r['ltp']:.2f}" if r["ltp"] is not None else "–"
        r["try_order"] = idx
        r["log_line"] = (
            f"[{tag_time}] #{idx:02d}/{total_n} Tried {r['symbol']} ({r['sector']}) | "
            f"LTP {ltp_str} (PDH ₹{r['pdh']:.2f}, PDL ₹{r['pdl']:.2f}) | "
            f"Stage: {r['stage']} | Why: {r['why_not_taken']}"
        )
    return rows, counts


def build_signal_checks(cfg, regime_res: dict, sector_meta: dict, metrics: dict, row: dict, side: str, qty: int | None, gate_reason: str, final_status: str, final_reason: str):
    """Build step-by-step calculation checklist explaining why a signal passed or failed."""
    p = cfg.strategy_params or {}
    bar_close = float(metrics.get("bar_close") or 0.0)
    bar_vol = float(metrics.get("bar_volume") or 0.0)
    slot_avg = float(metrics.get("slot_volume_avg") or 0.0)
    slot_mult = round(bar_vol / slot_avg, 2) if slot_avg > 0 else 0.0
    vwap = float(metrics.get("vwap") or 0.0)
    rvol = float(metrics.get("rvol") or 0.0)
    atr = float(row.get("atr") or 1.0)
    pdh = float(row.get("pdh") or 0.0)
    pdl = float(row.get("pdl") or 0.0)
    day_open = float(metrics.get("day_open") or 0.0)

    buf = float(p.get("buffer_pct", 0.001))
    vol_mult = float(p.get("vol_mult", 1.5))
    rvol_min = float(p.get("rvol_min", 1.0))
    max_chase = float(p.get("max_chase_atr", 0.5))

    if side == "SHORT":
        brk_lvl = round(pdl * (1.0 - buf), 2)
        brk_ok = bar_close < brk_lvl
        brk_req = f"Close < {brk_lvl:.2f} (PDL-{buf*100:.1f}%)"
        vwap_ok = bar_close < vwap
        vwap_req = f"Close < VWAP ({vwap:.2f})"
        gap_ok = day_open > pdl
        gap_req = f"Open > PDL ({pdl:.2f})"
        chase = (brk_lvl - bar_close) / atr if atr > 0 else 0.0
    else:
        brk_lvl = round(pdh * (1.0 + buf), 2)
        brk_ok = bar_close > brk_lvl
        brk_req = f"Close > {brk_lvl:.2f} (PDH+{buf*100:.1f}%)"
        vwap_ok = bar_close > vwap
        vwap_req = f"Close > VWAP ({vwap:.2f})"
        gap_ok = day_open < pdh
        gap_req = f"Open < PDH ({pdh:.2f})"
        chase = (bar_close - brk_lvl) / atr if atr > 0 else 0.0

    chase_ok = chase <= max_chase
    vol_ok = slot_avg > 0 and slot_mult > vol_mult
    rvol_ok = rvol >= rvol_min
    reg_active = regime_res.get("active", "CHOPPY")
    reg_ok = (side == "LONG" and reg_active == "TREND_UP") or (side == "SHORT" and reg_active == "TREND_DOWN")
    sec_mark = sector_meta.get("mark", "")
    sec_ok = (side == "LONG" and sec_mark == "STRONG") or (side == "SHORT" and sec_mark == "WEAK")
    vwap_enabled = bool(p.get("vwap_filter", True))
    vwap_pass = vwap_ok or (not vwap_enabled)
    gap_chase_ok = gap_ok and chase_ok
    gate_ok = final_status == "would trade" and not gate_reason

    want_reg = "TREND_UP" if side == "LONG" else "TREND_DOWN"
    want_sec = "STRONG" if side == "LONG" else "WEAK"

    why1 = "" if reg_ok else f"Market Regime '{reg_active}' tha; {side} entry ke liye {want_reg} hona zaroori tha."
    why2 = "" if sec_ok else f"Sector ({row.get('sector')}) '{sec_mark or 'NEUTRAL'}' (Rank #{sector_meta.get('rank', '-')}, RS {sector_meta.get('rs_pct', 0)}%) tha; {side} ke liye {want_sec} sector chahiye tha."
    why3 = "" if brk_ok else f"5m Candle Close ₹{bar_close:.2f} ne breakout level ({brk_req}) cross nahi kiya."
    why4 = "" if vwap_pass else f"Candle Close ₹{bar_close:.2f} VWAP (₹{vwap:.2f}) ke galat side tha ({vwap_req} chahiye tha)."
    if vol_ok:
        why5 = ""
    elif slot_avg <= 0:
        why5 = f"5-day same-slot average volume data missing/zero hai; actual 5m volume {int(bar_vol):,} shares tha."
    else:
        why5 = f"5m Candle Volume kam tha: Minimum > {int(slot_avg * vol_mult):,} shares ({vol_mult:.1f}x of 5-day avg {int(slot_avg):,}) chahiye tha, par actual sirf {int(bar_vol):,} shares ({slot_mult:.2f}x) aaya."
    why6 = "" if rvol_ok else f"Din ka cumulative RVOL kam tha: Minimum >= {rvol_min:.1f}x chahiye tha, par actual sirf {rvol:.2f}x tha."
    if gap_chase_ok:
        why7 = ""
    elif not gap_ok:
        why7 = f"Day Open ₹{day_open:.2f} pehle hi level cross kar chuka tha ({gap_req} chahiye)."
    else:
        why7 = f"Breakout level se {chase:.2f} ATR door tha (max allowed {max_chase:.1f} ATR)."
    why8 = "" if gate_ok else f"Entry Gate / Timing / Sizing rukawat: {gate_reason or final_reason} (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai)."

    return [
        {"step": 1, "name": "Market Regime", "passed": reg_ok,
         "actual": f"{reg_active} (ADX {regime_res.get('adx')}, Breadth {regime_res.get('breadth')})",
         "required": "TREND_UP (LONG) / TREND_DOWN (SHORT)", "why_failed": why1},
        {"step": 2, "name": "Sector Strength", "passed": sec_ok,
         "actual": f"Rank #{sector_meta.get('rank', '-')} {sec_mark or 'NEUTRAL'} (RS {sector_meta.get('rs_pct', 0)}%)",
         "required": "STRONG (LONG) / WEAK (SHORT)", "why_failed": why2},
        {"step": 3, "name": "Breakout Candle", "passed": brk_ok,
         "actual": f"Close {bar_close:.2f}",
         "required": brk_req, "why_failed": why3},
        {"step": 4, "name": "VWAP Filter", "passed": vwap_pass,
         "actual": f"Close {bar_close:.2f} vs VWAP {vwap:.2f}",
         "required": vwap_req if vwap_enabled else "Disabled", "why_failed": why4},
        {"step": 5, "name": "5m Slot Volume", "passed": vol_ok,
         "actual": f"{int(bar_vol):,} vs avg {int(slot_avg):,} ({slot_mult:.2f}x)",
         "required": f"> {vol_mult:.1f}x 5-day same-slot avg", "why_failed": why5},
        {"step": 6, "name": "Day RVOL", "passed": rvol_ok,
         "actual": f"{rvol:.2f}x cumulative",
         "required": f">= {rvol_min:.1f}x", "why_failed": why6},
        {"step": 7, "name": "Gap & No-Chase", "passed": gap_chase_ok,
         "actual": f"Open {day_open:.2f}, chase {chase:.2f} ATR",
         "required": f"{gap_req}, chase <= {max_chase:.1f} ATR", "why_failed": why7},
        {"step": 8, "name": "Sizing & Risk Gate", "passed": gate_ok,
         "actual": f"Qty {qty if qty is not None else '-'} | {final_status.upper()}: {final_reason}",
         "required": f"Qty > 0 (risk ₹{cfg.risk_per_trade_rs:.0f}, cap ₹83,333), limits OK", "why_failed": why8},
    ]


MIN_ENTRY_CONDITION_TEXT = (
    "Entry lene ke liye 8 me se 8 conditions (100% Mandatory) pass hona zaroori hai: "
    "(1) Market Regime Trend me ho, (2) Sector Strong/Weak ho, (3) 5m Close PDH/PDL ± 0.1% cross kare, "
    "(4) Close VWAP ke sahi side ho, (5) 5m Volume > 1.5x 5-day slot avg ho, (6) Day RVOL >= 1.0x ho, "
    "(7) No Gap-trap & Chase <= 0.5 ATR ho, (8) Time 09:30–14:15 ke beech ho aur Position/Risk limit OK ho."
)


def finalize_signal_checks(
    native_checks: list | None,
    cfg,
    regime_res: dict,
    sector_meta: dict,
    metrics: dict,
    row: dict,
    side: str,
    qty: int | None,
    gate_reason: str,
    final_status: str,
    final_reason: str,
) -> list:
    """Use strategy's own transparent checks + append Engine Sizing & Risk Gate; fallback to build_signal_checks."""
    if not native_checks:
        return build_signal_checks(
            cfg, regime_res, sector_meta, metrics, row, side, qty, gate_reason, final_status, final_reason
        )
    out = []
    for idx, c in enumerate(native_checks, 1):
        item = dict(c)
        item["step"] = idx
        out.append(item)
    strategy_ok = all(c.get("passed") for c in out)
    gate_ok = (final_status == "would trade") and (not gate_reason) and strategy_ok and (qty is not None and qty > 0)
    why_gate = ""
    if not gate_ok:
        if gate_reason:
            why_gate = f"Entry Gate / Timing: {gate_reason}"
        elif final_status != "would trade" and strategy_ok:
            why_gate = f"Sizing / Portfolio Gate: {final_reason}"
        elif qty is not None and qty <= 0:
            why_gate = f"Sizing Gate: Calculated qty={qty} (Risk/Notional cap check failed)"
        else:
            why_gate = f"Entry Gate / Timing / Sizing rukawat: {final_reason}"
    cap_rs = round((float(cfg.capital) * float(cfg.leverage)) / max(1, int(cfg.max_open_positions)), 0)
    out.append({
        "step": len(out) + 1,
        "name": "Sizing & Risk Gate",
        "passed": gate_ok,
        "actual": f"Qty {qty if qty is not None else '-'} | {final_status.upper()}",
        "required": f"Qty > 0 (risk ₹{cfg.risk_per_trade_rs:.0f}, cap ₹{cap_rs:,.0f}), time {cfg.no_entry_before:%H:%M}–{cfg.no_new_entries_after:%H:%M}, limits OK",
        "why_failed": why_gate,
        "error": False,
    })
    return out


def summarize_signal_checks(checks: list, min_condition_override: str | None = None) -> dict:
    passed_checks = sum(1 for c in (checks or []) if c.get("passed"))
    total_checks = len(checks or [])
    failed_checks = max(0, total_checks - passed_checks)
    failed_reasons = [
        f"#{c['step']} {c['name']}: {c['why_failed']}"
        for c in (checks or [])
        if not c.get("passed") and c.get("why_failed")
    ]
    has_error = any(bool(c.get("error")) for c in (checks or []))
    if min_condition_override:
        min_cond = min_condition_override
    elif checks:
        names = ", ".join(f"({c['step']}) {c['name']}" for c in checks)
        min_cond = f"Entry lene ke liye {total_checks} me se {total_checks} checks pass hona zaroori hai: {names}."
    else:
        min_cond = MIN_ENTRY_CONDITION_TEXT
    return {
        "passed_checks": passed_checks,
        "total_checks": total_checks,
        "failed_checks": failed_checks,
        "failed_reasons": failed_reasons,
        "min_condition": min_cond,
        "has_error": has_error,
    }


def compute_check_breakdown(signals_list: list) -> list:
    """Aggregate pass/fail counts per check step across all generated signals."""
    by_step = {}
    for s in (signals_list or []):
        for c in (s.get("checks") or []):
            step = int(c.get("step") or 0)
            if not step:
                continue
            entry = by_step.setdefault(step, {
                "step": step,
                "name": c.get("name") or f"Check {step}",
                "passed": 0,
                "failed": 0,
                "errors": 0,
                "total": 0,
            })
            entry["total"] += 1
            if c.get("passed"):
                entry["passed"] += 1
            else:
                entry["failed"] += 1
            if c.get("error"):
                entry["errors"] += 1
    out = sorted(by_step.values(), key=lambda x: x["step"])
    for x in out:
        x["pass_pct"] = round(x["passed"] / x["total"] * 100.0, 1) if x["total"] else 0.0
    return out


def build_scan_document(
    cfg,
    *,
    day: str,
    bar_time: str,
    checked_at: str,
    duration_ms: int,
    mode: str,
    universe_total: int,
    regime_res: dict,
    sectors: list,
    scanner: dict,
    day_levels: dict,
    prices: dict,
    signals_section: list,
    strategy_meta: dict,
):
    passed_cnt = sum(1 for s in signals_section if s.get("status") == "would trade")
    rej_cnt = len(signals_section) - passed_cnt
    scan_file, scan_id = make_scan_names(day, bar_time, len(day_levels), len(signals_section), passed_cnt)

    for s in signals_section:
        s["scan_file"] = scan_file
        s["scan_id"] = scan_id

    all_stocks, stage_counts = build_all_stocks_rows(
        day_levels, prices, sectors, scanner, scanner.get("armed") or [],
        signals_section=signals_section, bar_time=bar_time,
    )

    funnel = {
        "universe_total": universe_total,
        "prefilter_kept": len(day_levels),
        "prefilter_dropped": max(0, universe_total - len(day_levels)),
        **stage_counts,
        "signals_evaluated": len(signals_section),
        "signals_passed": passed_cnt,
        "signals_rejected": rej_cnt,
    }

    doc = {
        "scan_id": scan_id,
        "scan_file": scan_file,
        "day": day,
        "bar_time": bar_time,
        "checked_at": checked_at,
        "duration_ms": int(duration_ms),
        "mode": mode,
        "strategy": strategy_meta,
        "min_condition_to_enter": MIN_ENTRY_CONDITION_TEXT,
        "market_calculation": {
            "regime": regime_res.get("active"),
            "raw_regime": regime_res.get("raw"),
            "nifty_pct": regime_res.get("nifty_pct"),
            "adx14": regime_res.get("adx"),
            "session_mean": regime_res.get("session_mean"),
            "crosses": regime_res.get("crosses"),
            "advancers": regime_res.get("advancers"),
            "decliners": regime_res.get("decliners"),
            "breadth": regime_res.get("breadth"),
            "reason": regime_res.get("reason", ""),
        },
        "sectors_calculation": sectors,
        "funnel_counts": funnel,
        "signals_section": signals_section,
        "all_stocks_table": all_stocks,
    }

    index_entry = {
        "scan_id": scan_id,
        "scan_file": scan_file,
        "day": day,
        "bar_time": bar_time,
        "checked_at": checked_at,
        "duration_ms": int(duration_ms),
        "mode": mode,
        "regime": regime_res.get("active"),
        "kept": len(day_levels),
        "armed": len(scanner.get("armed") or []),
        "signals_evaluated": len(signals_section),
        "signals_passed": passed_cnt,
        "signals_rejected": rej_cnt,
        "symbols": [f"{s['signal_no']} ({s['status']})" for s in signals_section],
    }
    return doc, index_entry


def _cleanup_local_scans(ldir: Path):
    """Remove per-candle JSON files from laptop disk once uploaded to S3."""
    for p in ldir.glob("*.json"):
        if p.name != "INDEX.json":
            try:
                p.unlink()
            except Exception:
                pass


def _merge_index_entries(existing: list, new_entries: list) -> list:
    by_bar = {}
    for x in existing:
        bt = x.get("bar_time") or x.get("scan_file")
        # Prefer new naming format over legacy SCAN_*.json if same bar_time
        sf = x.get("scan_file", "")
        if bt not in by_bar or not sf.startswith("SCAN_"):
            by_bar[bt] = x
    for e in new_entries:
        bt = e.get("bar_time") or e.get("scan_file")
        by_bar[bt] = e
    return sorted(by_bar.values(), key=lambda x: x.get("bar_time", ""), reverse=True)


def _load_local_index_obj(idx_path: Path) -> dict:
    if idx_path.exists():
        try:
            obj = json.loads(idx_path.read_text(encoding="utf-8"))
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass
    return {}


def _build_index_obj(cfg, day: str, ordered: list, prev_obj: dict | None = None) -> dict:
    idx_obj = {"day": day, "bucket": cfg.s3_bucket, "region": cfg.s3_region, "scans": ordered}
    if isinstance(prev_obj, dict):
        if "macro_report" in prev_obj and prev_obj["macro_report"] is not None:
            idx_obj["macro_report"] = prev_obj["macro_report"]
        if "macro_reports" in prev_obj and isinstance(prev_obj["macro_reports"], list):
            idx_obj["macro_reports"] = prev_obj["macro_reports"]
    return idx_obj


def save_scan_doc(cfg, doc: dict, index_entry: dict, update_index: bool = True):
    day = doc["day"]
    scan_file = doc["scan_file"]
    ldir = _local_dir(cfg, day)

    s3_key = f"scans/{day}/{scan_file}"
    ok, msg = _s3_put_json(cfg, s3_key, doc)
    if ok:
        # Remove local scan files so laptop disk does not fill up
        local_scan = ldir / scan_file
        if local_scan.exists():
            try:
                local_scan.unlink()
            except Exception:
                pass
        _cleanup_local_scans(ldir)
    else:
        # Local fallback only when S3 upload fails
        (ldir / scan_file).write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")

    if update_index:
        idx_path = ldir / "INDEX.json"
        prev_obj = _load_local_index_obj(idx_path)
        existing = prev_obj.get("scans", []) if isinstance(prev_obj.get("scans"), list) else []
        ordered = _merge_index_entries(existing, [index_entry])
        idx_obj = _build_index_obj(cfg, day, ordered, prev_obj)
        idx_path.write_text(json.dumps(idx_obj, ensure_ascii=False), encoding="utf-8")
        if ok:
            _s3_put_json(cfg, f"scans/{day}/INDEX.json", idx_obj)

    return s3_key, ok, msg


def flush_day_index(cfg, day: str, index_entries: list):
    if not index_entries:
        return "", True, "empty"
    ldir = _local_dir(cfg, day)
    idx_path = ldir / "INDEX.json"
    prev_obj = _load_local_index_obj(idx_path)
    existing = prev_obj.get("scans", []) if isinstance(prev_obj.get("scans"), list) else []
    ordered = _merge_index_entries(existing, index_entries)
    idx_obj = _build_index_obj(cfg, day, ordered, prev_obj)
    idx_path.write_text(json.dumps(idx_obj, ensure_ascii=False), encoding="utf-8")
    key = f"scans/{day}/INDEX.json"
    ok, msg = _s3_put_json(cfg, key, idx_obj)
    if ok:
        _cleanup_local_scans(ldir)
    return key, ok, msg


def save_activity_s3(cfg, day: str, items: list):
    if not day:
        return False, "missing day"
    payload = {
        "day": day,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(items),
        "items": list(items),
    }
    return _s3_put_json(cfg, f"scans/{day}/ACTIVITY.json", payload)


def fetch_activity_s3(cfg, day: str, limit: int = 20, fallback_items: list | None = None):
    limit = max(1, min(int(limit or 20), 200))
    doc, msg = _s3_get_json(cfg, f"scans/{day}/ACTIVITY.json") if day else (None, "no day")
    if doc and isinstance(doc.get("items"), list):
        items = doc["items"]
        return {
            "ok": True,
            "day": day,
            "limit": limit,
            "total": len(items),
            "source": "s3",
            "items": items[:limit],
        }
    fb = list(fallback_items or [])
    return {
        "ok": True,
        "day": day,
        "limit": limit,
        "total": len(fb),
        "source": "local",
        "note": msg,
        "items": fb[:limit],
    }


def list_s3_scans(cfg, day: str | None = None):
    days = set(_s3_list_prefixes(cfg, "scans/"))
    local_root = cfg.root / "data" / "scan_archive"
    if local_root.exists():
        for p in local_root.iterdir():
            if p.is_dir():
                days.add(p.name)
    day_list = sorted(days, reverse=True)
    target = day or (day_list[0] if day_list else None)
    scans = []
    source = "none"
    if target:
        s3_idx, _ = _s3_get_json(cfg, f"scans/{target}/INDEX.json")
        if s3_idx and isinstance(s3_idx.get("scans"), list):
            scans = s3_idx["scans"]
            source = "s3"
        else:
            p = local_root / target / "INDEX.json"
            if p.exists():
                try:
                    scans = json.loads(p.read_text(encoding="utf-8")).get("scans", [])
                    source = "local"
                except Exception:
                    scans = []
    return {
        "bucket": cfg.s3_bucket,
        "region": cfg.s3_region,
        "configured": cfg.has_s3,
        "days": day_list,
        "day": target,
        "source": source,
        "scans": scans,
    }


def fetch_s3_scan(cfg, day: str, scan_file: str):
    if not day or not scan_file:
        return None, "missing"
    doc, msg = _s3_get_json(cfg, f"scans/{day}/{scan_file}")
    if doc is not None:
        return doc, "s3"
    p = cfg.root / "data" / "scan_archive" / day / scan_file
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8")), "local"
        except Exception:
            pass
    return None, msg
