"""SQLite store: one file.

The vendor StrategyState opens the file and owns its four tables (position, daily_counter,
fill, signal_marker). Our extra tables live in the same file and never touch those.
"""
from collections import deque
import json
import time

from core.state import StrategyState

_EXTRA = """
CREATE TABLE IF NOT EXISTS activity (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    ts    REAL NOT NULL,
    level TEXT NOT NULL,
    text  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS health (
    ts          REAL PRIMARY KEY,
    oa_ok       INTEGER,
    analyze_on  INTEGER,
    latency_ms  REAL,
    free_ram_mb REAL,
    engine_mb   REAL
);
CREATE TABLE IF NOT EXISTS setting (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS daily_levels (
    day         TEXT NOT NULL,
    symbol      TEXT NOT NULL,
    sector      TEXT NOT NULL,
    pdh         REAL,
    pdl         REAL,
    pdc         REAL,
    atr         REAL,
    atr_pct     REAL,
    avg_vol     REAL,
    avg_val_cr  REAL,
    kept        INTEGER NOT NULL,
    drop_reason TEXT NOT NULL,
    PRIMARY KEY (day, symbol)
);
CREATE TABLE IF NOT EXISTS decisions (
    day          TEXT NOT NULL,
    bar_time     TEXT NOT NULL,
    regime_json  TEXT NOT NULL,
    sectors_json TEXT NOT NULL,
    scanner_json TEXT NOT NULL,
    summary      TEXT NOT NULL,
    ts           REAL NOT NULL,
    PRIMARY KEY (day, bar_time)
);
CREATE TABLE IF NOT EXISTS signals (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    day         TEXT NOT NULL,
    bar_time    TEXT NOT NULL,
    ready_time  TEXT NOT NULL,
    symbol      TEXT NOT NULL,
    sector      TEXT NOT NULL,
    side        TEXT NOT NULL,
    entry_price REAL,
    stop_loss   REAL,
    target      REAL,
    rvol        REAL,
    slot_mult   REAL,
    status      TEXT NOT NULL,
    reason      TEXT NOT NULL,
    mode        TEXT NOT NULL,
    ts          REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS paper_trades (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    day             TEXT NOT NULL,
    symbol          TEXT NOT NULL,
    sector          TEXT NOT NULL,
    side            TEXT NOT NULL,
    qty             INTEGER NOT NULL,
    entry_order_id  TEXT,
    exit_order_id   TEXT,
    bar_time        TEXT NOT NULL,
    order_time      TEXT NOT NULL,
    decision_price  REAL NOT NULL,
    entry_price     REAL NOT NULL,
    entry_epoch     REAL NOT NULL,
    stop_loss       REAL NOT NULL,
    initial_stop    REAL NOT NULL,
    target          REAL,
    watermark       REAL NOT NULL,
    breakeven_moved INTEGER NOT NULL DEFAULT 0,
    exit_price      REAL,
    exit_time       TEXT,
    exit_reason     TEXT,
    gross_pnl       REAL,
    costs           REAL,
    net_pnl         REAL,
    r_multiple      REAL,
    tick_age_s      REAL,
    stale_flag      INTEGER NOT NULL DEFAULT 0,
    status          TEXT NOT NULL,
    ts              REAL NOT NULL
);
"""

FEED_LEN = 200          # lines the UI shows
HEALTH_KEEP_DAYS = 7


class Store:
    def __init__(self, db_path, keep_activity_days):
        self.state = StrategyState(db_path)          # creates the file and the vendor tables
        self._conn = self.state.conn
        self._lock = self.state._lock                # one connection, one lock, shared with the vendor class
        now = time.time()
        with self._lock:
            self._conn.executescript(_EXTRA)
            cols = {r[1] for r in self._conn.execute("PRAGMA table_info(signals)").fetchall()}
            for cname, ctype in (("qty", "INTEGER"), ("scan_id", "TEXT"), ("signal_no", "TEXT"), ("scan_file", "TEXT"), ("duration_ms", "INTEGER"), ("extra_json", "TEXT")):
                if cname not in cols:
                    self._conn.execute(f"ALTER TABLE signals ADD COLUMN {cname} {ctype}")
            self._conn.execute("DELETE FROM activity WHERE ts < ?", (now - keep_activity_days * 86400,))
            self._conn.execute("DELETE FROM health WHERE ts < ?", (now - HEALTH_KEEP_DAYS * 86400,))
            self._conn.execute("DELETE FROM decisions WHERE ts < ?", (now - keep_activity_days * 86400,))
            self._conn.execute("DELETE FROM signals WHERE ts < ?", (now - keep_activity_days * 86400,))
            self._conn.commit()
            rows = self._conn.execute(
                "SELECT ts, level, text FROM activity ORDER BY id DESC LIMIT ?", (FEED_LEN,)
            ).fetchall()
        self.feed = deque(({"ts": r[0], "level": r[1], "text": r[2]} for r in reversed(rows)), maxlen=FEED_LEN)

    # --- activity feed ---------------------------------------------------------
    def add_activity(self, text, level="info"):
        """level: info | good | warn | bad"""
        ts = time.time()
        with self._lock:
            self._conn.execute("INSERT INTO activity (ts, level, text) VALUES (?,?,?)", (ts, level, text))
            self._conn.commit()
            self.feed.append({"ts": ts, "level": level, "text": text})

    def feed_newest_first(self):
        with self._lock:
            return list(reversed(self.feed))

    # --- health ---------------------------------------------------------------
    def add_health(self, oa_ok, analyze_on, latency_ms, free_ram_mb, engine_mb):
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO health VALUES (?,?,?,?,?,?)",
                (time.time(), _b(oa_ok), _b(analyze_on), latency_ms, free_ram_mb, engine_mb),
            )
            self._conn.commit()

    # --- settings ---------------------------------------------------------------
    def get_setting(self, key, default=None):
        with self._lock:
            row = self._conn.execute("SELECT value FROM setting WHERE key=?", (key,)).fetchone()
        return default if row is None else json.loads(row[0])

    def set_setting(self, key, value):
        with self._lock:
            self._conn.execute("INSERT OR REPLACE INTO setting VALUES (?,?)", (key, json.dumps(value)))
            self._conn.commit()

    # --- daily levels (overwritten each day, architecture section 3) ---------
    def get_daily_levels(self, day):
        with self._lock:
            rows = self._conn.execute(
                "SELECT symbol, sector, pdh, pdl, pdc, atr, atr_pct, avg_vol, avg_val_cr, kept, drop_reason "
                "FROM daily_levels WHERE day=? ORDER BY sector, symbol",
                (day,),
            ).fetchall()
        return [
            {
                "symbol": r[0], "sector": r[1], "pdh": r[2], "pdl": r[3], "pdc": r[4],
                "atr": r[5], "atr_pct": r[6], "avg_vol": r[7], "avg_val_cr": r[8],
                "kept": bool(r[9]), "drop_reason": r[10],
            }
            for r in rows
        ]

    def save_daily_levels(self, day, rows):
        with self._lock:
            self._conn.execute("DELETE FROM daily_levels WHERE day != ?", (day,))
            self._conn.execute("DELETE FROM daily_levels WHERE day = ?", (day,))
            self._conn.executemany(
                "INSERT INTO daily_levels VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                [
                    (
                        day, r["symbol"], r["sector"], r.get("pdh"), r.get("pdl"), r.get("pdc"),
                        r.get("atr"), r.get("atr_pct"), r.get("avg_vol"), r.get("avg_val_cr"),
                        int(bool(r["kept"])), r.get("drop_reason", ""),
                    )
                    for r in rows
                ],
            )
            self._conn.commit()

    # --- decisions (last market/sector/scanner state per bar) -----------------
    def save_decision(self, day, bar_time, regime, sectors, scanner, summary):
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO decisions VALUES (?,?,?,?,?,?,?)",
                (day, bar_time, json.dumps(regime), json.dumps(sectors),
                 json.dumps(scanner), summary, time.time()),
            )
            self._conn.commit()

    def get_latest_decision(self, day=None):
        with self._lock:
            if day:
                row = self._conn.execute(
                    "SELECT day, bar_time, regime_json, sectors_json, scanner_json, summary, ts "
                    "FROM decisions WHERE day=? ORDER BY bar_time DESC LIMIT 1",
                    (day,),
                ).fetchone()
            else:
                row = self._conn.execute(
                    "SELECT day, bar_time, regime_json, sectors_json, scanner_json, summary, ts "
                    "FROM decisions ORDER BY day DESC, bar_time DESC LIMIT 1"
                ).fetchone()
        if not row:
            return None
        return {
            "day": row[0], "bar_time": row[1],
            "regime": json.loads(row[2]),
            "sectors": json.loads(row[3]),
            "scanner": json.loads(row[4]),
            "summary": row[5], "ts": row[6],
        }

    # --- signals (Phase 3) ----------------------------------------------------
    def add_signal(self, s):
        extra_keys = (
            "signal_id", "passed_checks", "total_checks", "failed_checks",
            "failed_reasons", "min_condition", "checks", "rr_ratio",
            "risk_rs", "reward_rs", "error", "trade_id",
        )
        extra = {k: s[k] for k in extra_keys if k in s}
        with self._lock:
            self._conn.execute(
                "INSERT INTO signals (day, bar_time, ready_time, symbol, sector, side, "
                "entry_price, stop_loss, target, rvol, slot_mult, status, reason, mode, ts, qty, "
                "scan_id, signal_no, scan_file, duration_ms, extra_json) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    s["day"], s["bar_time"], s["ready_time"], s["symbol"], s["sector"], s["side"],
                    s.get("entry_price"), s.get("stop_loss"), s.get("target"),
                    s.get("rvol"), s.get("slot_mult"), s["status"], s["reason"],
                    s.get("mode", "live"), time.time(), s.get("qty"),
                    s.get("scan_id"), s.get("signal_no"), s.get("scan_file"), s.get("duration_ms"),
                    json.dumps(extra, ensure_ascii=False),
                ),
            )
            self._conn.commit()

    def clear_signals_for_day(self, day, mode=None):
        with self._lock:
            if mode:
                self._conn.execute("DELETE FROM signals WHERE day=? AND mode=?", (day, mode))
            else:
                self._conn.execute("DELETE FROM signals WHERE day=?", (day,))
            self._conn.commit()

    def get_signals(self, day=None, limit=100):
        with self._lock:
            if day is None:
                row = self._conn.execute("SELECT day FROM signals ORDER BY id DESC LIMIT 1").fetchone()
                day = row[0] if row else None
            if not day:
                return []
            rows = self._conn.execute(
                "SELECT day, bar_time, ready_time, symbol, sector, side, entry_price, stop_loss, "
                "target, rvol, slot_mult, status, reason, mode, qty, scan_id, signal_no, scan_file, duration_ms, extra_json "
                "FROM signals WHERE day=? ORDER BY id DESC LIMIT ?",
                (day, limit),
            ).fetchall()
        out = []
        for r in rows:
            item = {
                "day": r[0], "bar_time": r[1], "ready_time": r[2], "symbol": r[3],
                "sector": r[4], "side": r[5], "entry_price": r[6], "stop_loss": r[7],
                "target": r[8], "rvol": r[9], "slot_mult": r[10], "status": r[11],
                "reason": r[12], "mode": r[13], "qty": r[14],
                "scan_id": r[15], "signal_no": r[16], "scan_file": r[17], "duration_ms": r[18],
            }
            if r[19]:
                try:
                    item.update(json.loads(r[19]))
                except Exception:
                    pass
            out.append(item)
        return out

    # --- Paper trades (Phase 4) -----------------------------------------------
    def add_paper_trade(self, t):
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO paper_trades (day, symbol, sector, side, qty, entry_order_id, "
                "bar_time, order_time, decision_price, entry_price, entry_epoch, stop_loss, "
                "initial_stop, target, watermark, breakeven_moved, tick_age_s, stale_flag, status, ts) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    t["day"], t["symbol"], t["sector"], t["side"], int(t["qty"]),
                    t.get("entry_order_id"), t["bar_time"], t["order_time"],
                    float(t["decision_price"]), float(t["entry_price"]), float(t["entry_epoch"]),
                    float(t["stop_loss"]), float(t["initial_stop"]),
                    None if t.get("target") is None else float(t["target"]),
                    float(t.get("watermark") or t["entry_price"]),
                    int(bool(t.get("breakeven_moved", False))),
                    None if t.get("tick_age_s") is None else float(t["tick_age_s"]),
                    int(bool(t.get("stale_flag", False))),
                    t.get("status", "OPEN"), time.time(),
                ),
            )
            self._conn.commit()
            return cur.lastrowid

    def update_paper_trade_stop(self, trade_id, stop_loss, breakeven_moved, watermark=None):
        with self._lock:
            if watermark is not None:
                self._conn.execute(
                    "UPDATE paper_trades SET stop_loss=?, breakeven_moved=?, watermark=? WHERE id=?",
                    (float(stop_loss), int(bool(breakeven_moved)), float(watermark), int(trade_id)),
                )
            else:
                self._conn.execute(
                    "UPDATE paper_trades SET stop_loss=?, breakeven_moved=? WHERE id=?",
                    (float(stop_loss), int(bool(breakeven_moved)), int(trade_id)),
                )
            self._conn.commit()

    def update_paper_trade_watermark(self, trade_id, watermark):
        with self._lock:
            self._conn.execute(
                "UPDATE paper_trades SET watermark=? WHERE id=?",
                (float(watermark), int(trade_id)),
            )
            self._conn.commit()

    def close_paper_trade(
        self, trade_id, exit_order_id, exit_price, exit_time, exit_reason,
        gross_pnl, costs, net_pnl, r_multiple, tick_age_s, stale_flag,
    ):
        with self._lock:
            self._conn.execute(
                "UPDATE paper_trades SET exit_order_id=?, exit_price=?, exit_time=?, exit_reason=?, "
                "gross_pnl=?, costs=?, net_pnl=?, r_multiple=?, tick_age_s=?, stale_flag=?, status='CLOSED' "
                "WHERE id=?",
                (
                    exit_order_id, float(exit_price), exit_time, exit_reason,
                    float(gross_pnl), float(costs), float(net_pnl), float(r_multiple),
                    None if tick_age_s is None else float(tick_age_s),
                    int(bool(stale_flag)), int(trade_id),
                ),
            )
            self._conn.commit()

    def _row_to_trade(self, r):
        return {
            "id": r[0], "day": r[1], "symbol": r[2], "sector": r[3], "side": r[4],
            "qty": r[5], "entry_order_id": r[6], "exit_order_id": r[7],
            "bar_time": r[8], "order_time": r[9], "decision_price": r[10],
            "entry_price": r[11], "entry_epoch": r[12], "stop_loss": r[13],
            "initial_stop": r[14], "target": r[15], "watermark": r[16],
            "breakeven_moved": bool(r[17]), "exit_price": r[18], "exit_time": r[19],
            "exit_reason": r[20], "gross_pnl": r[21], "costs": r[22], "net_pnl": r[23],
            "r_multiple": r[24], "tick_age_s": r[25], "stale_flag": bool(r[26]), "status": r[27],
        }

    def get_open_paper_trades(self, day=None):
        with self._lock:
            if day:
                rows = self._conn.execute(
                    "SELECT id, day, symbol, sector, side, qty, entry_order_id, exit_order_id, "
                    "bar_time, order_time, decision_price, entry_price, entry_epoch, stop_loss, "
                    "initial_stop, target, watermark, breakeven_moved, exit_price, exit_time, "
                    "exit_reason, gross_pnl, costs, net_pnl, r_multiple, tick_age_s, stale_flag, status "
                    "FROM paper_trades WHERE status='OPEN' AND day=? ORDER BY id ASC",
                    (day,),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT id, day, symbol, sector, side, qty, entry_order_id, exit_order_id, "
                    "bar_time, order_time, decision_price, entry_price, entry_epoch, stop_loss, "
                    "initial_stop, target, watermark, breakeven_moved, exit_price, exit_time, "
                    "exit_reason, gross_pnl, costs, net_pnl, r_multiple, tick_age_s, stale_flag, status "
                    "FROM paper_trades WHERE status='OPEN' ORDER BY id ASC"
                ).fetchall()
        return [self._row_to_trade(r) for r in rows]

    def get_closed_paper_trades(self, day):
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, day, symbol, sector, side, qty, entry_order_id, exit_order_id, "
                "bar_time, order_time, decision_price, entry_price, entry_epoch, stop_loss, "
                "initial_stop, target, watermark, breakeven_moved, exit_price, exit_time, "
                "exit_reason, gross_pnl, costs, net_pnl, r_multiple, tick_age_s, stale_flag, status "
                "FROM paper_trades WHERE status='CLOSED' AND day=? ORDER BY id DESC",
                (day,),
            ).fetchall()
        return [self._row_to_trade(r) for r in rows]

    def get_traded_symbols(self, day):
        with self._lock:
            rows = self._conn.execute(
                "SELECT DISTINCT symbol FROM paper_trades WHERE day=?", (day,)
            ).fetchall()
        return {r[0] for r in rows}

    def close(self):
        self.state.close()


def _b(v):
    return None if v is None else int(bool(v))
