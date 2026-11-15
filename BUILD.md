# BUILD.md — start here

This file is the entry point for building `intraday-engine`. It is written for the AI coding agent that will do the build, and for Sunil, who will check each phase.

**To start the build, give the agent this message:**

> Read BUILD.md fully, then docs/STRATEGY_SPEC_v2.md, docs/ARCHITECTURE_v2.md and docs/STRATEGY_SOCKET.md. Build Phase 1 only. Stop when Phase 1's "You should see" list is true and PROGRESS.md is updated.

For later phases: "Read BUILD.md and PROGRESS.md. Build Phase N only."

---

## 1. What we are building

A single-process Python engine that paper-trades an intraday breakout strategy on NSE stocks through OpenAlgo Desktop (broker: Groww) in Analyze mode, with a one-page web UI that shows what the system is doing and lets the user start and stop it.

The user runs it on a 5-year-old laptop with about 1 GB of free RAM. He has a day job, so the engine often runs unattended and he reads the result in the evening. Both facts shape the design: memory is tight, and the UI must still tell the full story of the day after the session has ended.

## 2. Files and who decides what

| File | Decides |
|---|---|
| BUILD.md (this file) | Scope, order, phases, rules for the build |
| docs/STRATEGY_SPEC_v2.md | Every trading rule and number |
| docs/ARCHITECTURE_v2.md | Structure: process, threads, modules, UI, OpenAlgo link, storage |
| docs/STRATEGY_SOCKET.md | Contract between engine and strategy file (update it in Phase 3, see §6) |
| PROGRESS.md | Created in Phase 1, updated at the end of every phase |

If two files disagree: this file wins on scope and order, the spec wins on trading rules, the architecture wins on structure. `docs/STRATEGY_SPEC.md` (v1) is superseded; delete it in Phase 1.

## 3. Rules for the whole build

1. **Paper only.** Never turn Analyze mode off, never call the analyzer toggle. The engine checks the mode before a session starts and every 30 seconds, and sends no order of any kind if it is off. Reason: OpenAlgo routes orders to the live broker the moment that switch is off.
2. **One phase per run.** Finish the phase, update PROGRESS.md, tell the user in plain words what to click to see it, then stop. Do not begin the next phase until asked. Reason: the user reviews each phase in the UI before more is built on it.
3. **No test suite.** No unit tests, no test framework, no test files, no CI. This is the user's decision. The only check in the project is the connection check in the UI (architecture §4). A phase is done when its "You should see" list is true.
4. **One process, small footprint.** Engine at or under 150 MB. Dependencies are exactly: openalgo, pandas, numpy, PyYAML, python-dotenv (add tzdata only if the machine is Windows). No web framework, no scheduler library, no chart library, no Node, no build step.
5. **Only `engine/oa` talks to OpenAlgo.** Every REST call, the stream, and every order goes through it. Reason: one place for timeouts, throttling, error messages and the heartbeat.
6. **`vendor/` is read-only, and reuse comes first.** Before writing a function, check the reuse map (§7). If the zip or the SDK already has it, import it. Do not copy vendor code into `engine/`, and do not edit `vendor/`.
7. **Nothing from spec §12 is hard-coded.** It comes from config.yaml.
8. **No market-data archive.** Store only what architecture §3 lists.
9. **Trading logic is pure.** Regime, sector, scanner, strategy and sizing take data in and return a decision, with no network or disk access inside. Dry run depends on this.
10. **When the spec cannot be followed as written** — for example an assumption tagged [A] turns out false on the real OpenAlgo — stop, write it under "Open points" in PROGRESS.md, and ask. Do not quietly change a trading rule.
11. **Secrets** stay in `.env`. The API key is never printed in the UI or the logs.
12. **UI text** is short plain sentences. Every red or amber state says what is wrong and what to do about it.

## 4. Phases

Each phase ends with something the user can see in the UI. Panels that belong to a later phase are present from Phase 1 but greyed, labelled "comes in Phase N", so the page itself shows what is left.

### Phase 1 — Shell, UI and the OpenAlgo link

Build: `engine/app`, `config`, `oa` (wrapper, connection check, heartbeat), `store`, `ui`, `session` (state machine and clock only, no market logic), a double-click launcher, PROGRESS.md.
Also: move the two v2 docs into `docs/`, delete the v1 spec, rewrite `config.example.yaml` to match spec §12, trim `requirements.txt` to rule 4, refresh README.

You should see:
- Launcher opens the UI in the browser.
- "Run check" lists the 11 checks, each green, amber or red, with a fix line on anything not green.
- With OpenAlgo Desktop closed, the top banner is red and says to start it. Open it again and the banner clears within about 30 seconds without restarting the engine.
- With Analyze mode switched off in OpenAlgo, START is refused and the page says why.
- START works at any time of day. The session state shown matches the clock: warming up, live, view only, or market closed.
- STOP ends the session; the page stays up.
- Auto-start toggle and time can be set and survive a restart.
- Activity feed shows what happened in plain sentences.
- Free RAM, heartbeat age and API latency are visible.

Not in this phase: any market data beyond the check, any strategy logic.

### Phase 2 — Market view (no signals, no orders)

Build: `levels` (daily levels, universe clean-up per spec §3, pre-filter, sector eligibility), `feed`, `regime`, `sector`, `scanner`.
The cleaned universe is written to a new file; `data/sector_map.json` itself is not edited.

You should see:
- Universe table: every symbol, kept or dropped, with the reason; each kept stock in exactly one sector.
- In market hours: regime with its four inputs, updating every 5 minutes; sector table with RS and strong/weak marks; shortlist with scores; armed symbols marked.
- Activity feed gets a line per 5-minute bar, for example "10:05 TREND_UP. Auto, Metal strong. 2 armed."
- In the evening: the page still shows that day's last state and the whole feed, so the day can be read after work.
- Last tick age stays small; if the stream stops, the page says so.

Not in this phase: volume, VWAP, signals.

### Phase 3 — Signals and dry run (no orders)

Build: `bars`, `strategies/pdh_breakout`, strategy loading through the socket, `dryrun`. Update docs/STRATEGY_SOCKET.md (§6 below).

You should see:
- Signals panel: every signal with time, symbol, side, stop, target, and either "would trade" or "rejected" with the reason.
- For each signal: bar close time and the time the decision was ready.
- Pressing START when the market is closed offers **Dry run: last session**. It fetches that session on demand, runs all 72 bars through the same logic, fills the Market, Scanner and Signals panels and the feed with bar times, sends no orders, and keeps no bars.

Not in this phase: sizing, orders, exits.

### Phase 4 — Paper trading

Build: `portfolio`, `orders`, `exits`, square-off, reconcile, restart recovery, daily limits.

You should see:
- A taken signal becomes an order. The same order, with the same quantity, appears in OpenAlgo's sandbox order book.
- Positions panel: entry, stop, target, R so far. Stop moves to entry at +1R.
- Today panel: trades, P&L in rupees and R, costs, trades left, loss-limit state.
- All positions flat by 15:00, with the square-off shown in the feed.
- Closing and reopening the engine mid-session brings the open positions and today's counts back.
- Any difference between the engine's positions and OpenAlgo's is shown in red.
- Dry run now also shows the size each signal would have had.

### Phase 5 — Report, LLM and shadow comparison

Build: `report`, `llm`, shadow comparison (spec §11). Each can be switched off in config.

You should see:
- Report panel after the close: what was traded and why, in plain language.
- Pre-market brief logged and viewable; it changes no decision.
- Shadow table: raw signals with filters off, and how each exit variant would have done.
- A running summary across days: trades so far, net expectancy in R, progress toward the decision gate.

## 5. PROGRESS.md

Created in Phase 1, rewritten at the end of every phase, kept short.

| Section | Content |
|---|---|
| Phase table | Phases 1–5, each: not started / in progress / done, with the date |
| What you can see now | Bullet list of what works, and what to click to see it |
| What is left | The remaining phases in one line each |
| Open points | Assumptions that turned out false, questions waiting for the user |
| How to run | The launch step and where the UI is |

The UI's build-status strip shows the same phase states.

## 6. Changes to make in docs/STRATEGY_SOCKET.md (Phase 3)

- `on_bar` is called only for **armed** symbols (spec §6), not the whole shortlist.
- `bars` holds 5m bars for the last 5 sessions including today.
- Context gains `slot_volume_avg` and `rvol`; `vwap` is the stock's session VWAP from today's bars.
- Shortlist is top 5 for the side the regime allows, not top 10.
- Engine may also drop a signal for: notional cap leaving risk under the minimum, stale data, Analyze mode off, free RAM too low.

## 7. Reuse map — import, do not rewrite

The zip already contains working code (`vendor/core`, MIT) and the `openalgo` SDK 2.1.1 ships more. Before writing any function, check this table. **Import it; never copy vendor code into `engine/`.**

Import path: put `vendor/` on `sys.path` once in `engine/app`, then `from core.state import StrategyState`. Vendor files import each other as `core.*`, so this is required.

### Use as-is

| Need | Use | Phase |
|---|---|---|
| Normalise any history DataFrame (datetime index, lowercase OHLCV) | `core.data_router.normalize_history` | 2 |
| Fetch daily / 5m history | `core.data_router.fetch_backtest_data(client, symbol, exchange, interval, start, end, source="api")` | 2 |
| Funds + broker-login check | `core.preflight.run_preflight(client, min_cash=...)` — raises `PreflightError` | 1 |
| Holiday check | `core.preflight.run_preflight(..., exchange="NSE")` (calls `_check_holiday`) | 1 |
| Symbol resolves (one symbol) | `core.preflight.run_preflight(..., symbol=s, exchange="NSE")` | 1 |
| Open position for a symbol at broker | `core.preflight.find_existing_open_position` | 4 |
| Pending orders for our strategy tag | `core.preflight.find_pending_orders` | 4 |
| Positions, daily P&L + trade count, fills, per-bar idempotency | `core.state.StrategyState` (tables `position`, `daily_counter`, `fill`, `signal_marker`) | 1 |
| Reconcile one symbol with broker | `core.state.reconcile_with_broker` | 4 |
| Intraday cost constants | `core.cost_model.lookup("MIS", "NSE")` → `INTRADAY_EQ` | 4 |
| Slippage record and report | `core.cost_model.SlippageTracker` | 4 |
| Load strategy file | `core.strategy_loader.load_strategy(path)` → module; engine then builds `mod.Strategy(params)` | 3 |
| ATR | `core.indicator_adapter.get_indicators().atr(...)` | 2 |

### Use from the SDK (`openalgo` 2.1.1) instead of writing it

| Need | Use |
|---|---|
| Stream reconnect + resubscribe | Built in (`auto_reconnect=True`, default). Do not add a reconnect loop. |
| Last price snapshot of all subscribed symbols | `client.get_ltp()` |
| Batch quotes (polling fallback) | `client.multiquotes(symbols=[...])` |
| Analyze-mode status | `client.analyzerstatus()` |
| Market open / special sessions | `client.timings(date)`, `client.holidays(year)` |
| ADX | `openalgo.ta.adx(h, l, c, 14)` → returns **(+DI, −DI, ADX)**; use index 2 |
| Session VWAP | `openalgo.ta.vwap(h, l, c, v, anchor="Session", timestamps=index)` — resets each day (checked) |
| Exit a position | `client.placesmartorder(..., position_size=0)` |
| Square off everything for our tag | `client.closeposition(strategy=NAME)` |
| Fill price | `client.orderstatus(order_id, strategy)` |

### Do not use (and why)

| Vendor piece | Reason |
|---|---|
| `indicator_adapter.adx()` | **Broken with SDK 2.1.1**: SDK returns three arrays, adapter wraps them as one Series → `ValueError` (reproduced). Call `openalgo.ta.adx` directly. |
| `openalgo.ta.rvol` | It is volume ÷ simple average of last N bars. Spec needs same-time-slot RVOL (spec §7). Write that one. |
| `data_router.BarCloseWatcher`, `poll_for_new_bar` | One thread per symbol, too many API calls (architecture F4). |
| `data_router.reconnect_ws` | Duplicates the SDK's auto-reconnect (F5). |
| `data_router.fetch_from_duckdb` and DuckDB paths | No DuckDB on this machine. |
| `risk_manager.RiskManager` | One position only; overwrites the shared LTP callback (F2). |
| `sizing.*` | Wrong model, returns qty 1 on failure (F6). |
| `strategy_loader.run_one_backtest`, `fetch_data_for_*` | Need vectorbt and a `signals(df)` function. |
| `portfolio_runner` | Multi-process (F8). |
| `reference_strategies/*` | Single-symbol examples. Read for patterns only. |

### Write new (nothing in the zip or SDK covers it)

| Item | Note |
|---|---|
| Multi-position exit monitor | Follow `RiskManager._on_tick` / `_place_exit` / `_read_fill_price` pattern: worker thread, smart order to flatten, fill poll at 0.5 s. |
| Extra tables (stop, target, breakeven state, decisions, activity, health) | Add to the **same** SQLite file that `StrategyState` opens; do not change its tables. |
| GST on brokerage | Cost model has no GST. Add 18% on brokerage in engine code. |
| Slot-volume baseline and RVOL | Spec §7. |
| Regime, sector, scanner, portfolio, session clock, UI, OpenAlgo wrapper | The engine itself. |

## 8. Known unknowns

These are tagged [A] in the docs. The connection check or the first live sessions will settle them. If one is false, rule 10 applies.

- OpenAlgo Desktop's own memory use.
- Whether the stream delivers NIFTY index values together with ~100 stock prices.
- How many seconds after a bar closes the 5m history shows that bar with volume.
- Whether history calls count against Groww's 300-per-minute limit.
- Which universe symbols resolve, and which have stock futures.
- What price a sandbox market order fills at.
