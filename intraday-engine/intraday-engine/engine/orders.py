"""Order queue, fill-price polling, broker reconcile and restart recovery (Phase 4)."""
from datetime import datetime
import queue
import threading
import time

from core.cost_model import SlippageTracker
from core.preflight import find_pending_orders
from core.state import StoredPosition, reconcile_with_broker

from engine.oa import IST
from engine.portfolio import estimate_round_trip_cost


def _extract_order_id(resp):
    if not isinstance(resp, dict):
        return None
    if resp.get("orderid"):
        return str(resp["orderid"])
    data = resp.get("data")
    if isinstance(data, dict) and data.get("orderid"):
        return str(data["orderid"])
    return None


def _extract_status_and_price(resp):
    if not isinstance(resp, dict):
        return "", None, ""
    data = resp.get("data")
    node = data if isinstance(data, dict) else resp
    st = str(node.get("order_status") or node.get("status") or "").lower()
    avg = node.get("average_price") or node.get("price")
    try:
        avg_f = float(avg) if avg not in (None, "", 0, "0") else None
    except (TypeError, ValueError):
        avg_f = None
    rej = str(node.get("rejection_reason") or resp.get("message") or "")
    return st, avg_f, rej


class OrderManager:
    """Single-worker order queue + reconcile helper."""

    def __init__(self, cfg, link, store, log, on_change=None):
        self.cfg = cfg
        self.link = link
        self.store = store
        self.log = log
        self.on_change = on_change
        self.slippage = SlippageTracker(assumed_pct=0.05)
        self._q = queue.Queue()
        self._stop = threading.Event()
        self._thread = None
        self._lock = threading.Lock()
        self._exiting_ids = set()
        self.reconcile_mismatches = []
        self.external_positions = []
        self.last_reconcile_at = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._worker, name="orders", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._q.put(None)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)

    def submit_entry(self, req: dict):
        self._q.put({"kind": "ENTRY", **req})

    def submit_exit(self, trade_id: int, reason: str, decision_price: float, tick_age_s: float = 0.0, stale_flag: bool = False):
        with self._lock:
            if trade_id in self._exiting_ids:
                return False
            self._exiting_ids.add(trade_id)
        self._q.put({
            "kind": "EXIT",
            "trade_id": int(trade_id),
            "reason": reason,
            "decision_price": float(decision_price or 0.0),
            "tick_age_s": float(tick_age_s or 0.0),
            "stale_flag": bool(stale_flag),
        })
        return True

    def _notify(self):
        if self.on_change:
            try:
                self.on_change()
            except Exception:
                self.log.exception("orders on_change failed")

    def _worker(self):
        while not self._stop.is_set():
            try:
                item = self._q.get(timeout=1.0)
            except queue.Empty:
                continue
            if item is None:
                break
            try:
                if item["kind"] == "ENTRY":
                    self._handle_entry(item)
                elif item["kind"] == "EXIT":
                    self._handle_exit(item)
            except Exception:
                self.log.exception("order worker failed on %s", item)
            finally:
                self._q.task_done()

    def _poll_fill(self, order_id: str, fallback_price: float):
        """Poll orderstatus up to ~4s for complete status and average fill price."""
        for _ in range(8):
            if self._stop.is_set():
                break
            resp = self.link.orderstatus(order_id=order_id, strategy=self.cfg.strategy_name)
            st, avg, rej = _extract_status_and_price(resp)
            if st in ("complete", "filled", "executed"):
                return "complete", (avg if avg and avg > 0 else fallback_price), ""
            if st in ("rejected", "cancelled", "canceled", "failed"):
                return "rejected", None, rej or "Order rejected"
            time.sleep(0.5)
        return "complete", fallback_price, ""

    def _handle_entry(self, item: dict):
        symbol = item["symbol"]
        bar_time = item["bar_time"]
        day = item["day"]
        marker_key = f"{day}:{symbol}"
        if self.store.state.signal_already_acted(marker_key, bar_time):
            return
        if self.store.state.has_open_position(symbol, self.cfg.exchange):
            return

        action = "BUY" if item["side"] == "LONG" else "SELL"
        qty = int(item["qty"])
        decision_price = float(item["decision_price"])
        order_time = datetime.now(IST).strftime("%H:%M:%S")

        resp = self.link.placeorder(
            strategy=self.cfg.strategy_name,
            symbol=symbol,
            action=action,
            exchange=self.cfg.exchange,
            price_type="MARKET",
            product=self.cfg.product,
            quantity=qty,
        )
        if not isinstance(resp, dict) or resp.get("status") != "success":
            msg = (resp.get("message") if isinstance(resp, dict) else None) or "Order failed"
            self.store.add_activity(f"Entry order rejected for {symbol} ({action} {qty}): {msg}", "bad")
            self._notify()
            return

        order_id = _extract_order_id(resp) or f"paper-{int(time.time() * 1000)}"
        st, fill_price, rej = self._poll_fill(order_id, decision_price)
        if st == "rejected":
            self.store.add_activity(f"Entry order rejected for {symbol} ({action} {qty}): {rej}", "bad")
            self._notify()
            return

        fill_price = float(fill_price or decision_price)
        entry_epoch = time.time()
        self.store.state.mark_signal_acted(marker_key, bar_time)
        self.store.state.record_fill(order_id, symbol, action, qty, decision_price=decision_price, fill_price=fill_price)
        self.slippage.record(decision_price, fill_price, qty=qty, side=action)

        self.store.state.save_position(StoredPosition(
            symbol=symbol,
            exchange=self.cfg.exchange,
            side=action,
            qty=qty,
            entry_price=fill_price,
            entry_time=entry_epoch,
            product=self.cfg.product,
            watermark=fill_price,
            closed=False,
        ))

        self.store.add_paper_trade({
            "day": day,
            "symbol": symbol,
            "sector": item["sector"],
            "side": item["side"],
            "qty": qty,
            "entry_order_id": order_id,
            "bar_time": bar_time,
            "order_time": order_time,
            "decision_price": decision_price,
            "entry_price": fill_price,
            "entry_epoch": entry_epoch,
            "stop_loss": float(item["stop_loss"]),
            "initial_stop": float(item["stop_loss"]),
            "target": item.get("target"),
            "watermark": fill_price,
            "tick_age_s": item.get("tick_age_s"),
            "stale_flag": False,
            "status": "OPEN",
        })
        self.store.add_activity(
            f"{order_time} PAPER ENTRY {item['side']} {symbol} qty {qty} @ ₹{fill_price:.2f} "
            f"(SL ₹{item['stop_loss']:.2f}, Tgt ₹{(item.get('target') or 0):.2f})",
            "good",
        )
        self._notify()

    def _handle_exit(self, item: dict):
        trade_id = int(item["trade_id"])
        open_rows = {t["id"]: t for t in self.store.get_open_paper_trades()}
        t = open_rows.get(trade_id)
        if not t:
            with self._lock:
                self._exiting_ids.discard(trade_id)
            return

        symbol = t["symbol"]
        qty = int(t["qty"])
        action = "SELL" if t["side"] == "LONG" else "BUY"
        decision_price = float(item["decision_price"] or t["entry_price"])

        resp = self.link.placeorder(
            strategy=self.cfg.strategy_name,
            symbol=symbol,
            action=action,
            exchange=self.cfg.exchange,
            price_type="MARKET",
            product=self.cfg.product,
            quantity=qty,
        )
        if not isinstance(resp, dict) or resp.get("status") != "success":
            msg = (resp.get("message") if isinstance(resp, dict) else None) or "Exit order failed"
            self.store.add_activity(f"Exit retry needed for {symbol} ({item['reason']}): {msg}", "bad")
            with self._lock:
                self._exiting_ids.discard(trade_id)
            self._notify()
            return

        order_id = _extract_order_id(resp) or f"exit-{int(time.time() * 1000)}"
        st, fill_price, rej = self._poll_fill(order_id, decision_price)
        if st == "rejected":
            self.store.add_activity(f"Exit rejected for {symbol} ({item['reason']}), will retry: {rej}", "bad")
            with self._lock:
                self._exiting_ids.discard(trade_id)
            self._notify()
            return

        fill_price = float(fill_price or decision_price)
        exit_time = datetime.now(IST).strftime("%H:%M:%S")
        sign = 1.0 if t["side"] == "LONG" else -1.0
        gross_pnl = round(sign * (fill_price - float(t["entry_price"])) * qty, 2)
        costs = estimate_round_trip_cost(
            float(t["entry_price"]), fill_price, qty,
            product=self.cfg.product, exchange=self.cfg.exchange, gst_rate=self.cfg.gst_rate,
        )
        net_pnl = round(gross_pnl - costs, 2)
        r_per_share = abs(float(t["entry_price"]) - float(t["initial_stop"]))
        r_mult = round((sign * (fill_price - float(t["entry_price"])) / r_per_share), 2) if r_per_share > 0 else 0.0

        self.store.state.record_fill(order_id, symbol, action, qty, decision_price=decision_price, fill_price=fill_price)
        self.slippage.record(decision_price, fill_price, qty=qty, side=action)
        self.store.state.mark_closed(symbol, self.cfg.exchange, float(t["entry_epoch"]))
        self.store.state.update_daily(t["day"], net_pnl, trades_delta=1)
        self.store.close_paper_trade(
            trade_id=trade_id,
            exit_order_id=order_id,
            exit_price=fill_price,
            exit_time=exit_time,
            exit_reason=item["reason"],
            gross_pnl=gross_pnl,
            costs=costs,
            net_pnl=net_pnl,
            r_multiple=r_mult,
            tick_age_s=item.get("tick_age_s"),
            stale_flag=item.get("stale_flag"),
        )
        with self._lock:
            self._exiting_ids.discard(trade_id)
        stale_note = " [STALE TICK]" if item.get("stale_flag") else ""
        lvl = "good" if net_pnl >= 0 else "warn"
        self.store.add_activity(
            f"{exit_time} PAPER EXIT {symbol} ({item['reason']}{stale_note}) @ ₹{fill_price:.2f} | "
            f"Net ₹{net_pnl:+.2f} ({r_mult:+.2f}R)",
            lvl,
        )
        self._notify()

    def reconcile(self):
        """Compare engine open paper_trades with OpenAlgo positionbook()."""
        mismatches = []
        open_trades = self.store.get_open_paper_trades()
        for t in open_trades:
            reconcile_with_broker(self.store.state, self.link, t["symbol"], self.cfg.exchange)

        pb = self.link.positionbook()
        if not isinstance(pb, dict) or pb.get("status") != "success":
            return ["Could not read OpenAlgo positionbook for reconcile."]

        broker_map = {}
        for r in (pb.get("data") or []):
            if r.get("exchange") != self.cfg.exchange:
                continue
            try:
                q = int(float(r.get("quantity", 0) or 0))
            except (TypeError, ValueError):
                q = 0
            if q != 0:
                broker_map[r.get("symbol")] = broker_map.get(r.get("symbol"), 0) + q

        engine_map = {}
        for t in open_trades:
            signed_q = int(t["qty"]) if t["side"] == "LONG" else -int(t["qty"])
            engine_map[t["symbol"]] = engine_map.get(t["symbol"], 0) + signed_q

        external = []
        for sym in sorted(set(broker_map) | set(engine_map)):
            bq = broker_map.get(sym, 0)
            eq = engine_map.get(sym, 0)
            if sym in engine_map:
                if bq != eq:
                    mismatches.append(f"{sym}: engine qty {eq}, OpenAlgo qty {bq}")
            elif bq != 0:
                external.append(f"{sym} (qty {bq})")

        pending = [
            o for o in find_pending_orders(self.link, self.cfg.strategy_name)
            if o.get("strategy") == self.cfg.strategy_name
        ]
        if pending:
            mismatches.append(f"{len(pending)} pending order(s) in OpenAlgo orderbook")

        self.reconcile_mismatches = mismatches
        self.external_positions = external
        self.last_reconcile_at = time.time()
        return mismatches
