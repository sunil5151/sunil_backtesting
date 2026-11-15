# ARCHITECTURE v2.1 — intraday-engine, 1 GB free RAM

Scope: design only, no code. Read with STRATEGY_SPEC_v2.md. Build order and phases are in BUILD.md.
Tags: **[V]** verified from a source on 13 Nov 2026 · **[M]** measured · **[A]** assumption.

Changes in v2.1: simple web UI replaces Telegram · start by button at any time, auto-start optional ·
no market-data archive · no test suite, only the connection check · budget is 1 GB **free** RAM ·
one OpenAlgo link layer that everything goes through.

---

## 1. Findings on the current skeleton

| # | Where | Finding | Action |
|---|---|---|---|
| F1 | engine/feed.py plan | "Build 5m bars from ticks for 133 symbols". Groww's stream gives price and timestamp only, no volume **[V]**. | Stream for price only. Volume from 5m history for armed symbols. |
| F2 | vendor risk_manager | Built for one position. Each instance sets its own LTP callback, but the SDK keeps one LTP callback per client **[M]**. With 3 positions only the last gets ticks. | One engine-side exit monitor for all positions. |
| F3 | vendor risk_manager | Commits to SQLite on every favourable tick inside the tick callback. | No disk writes on ticks. |
| F4 | vendor BarCloseWatcher | One thread per symbol polling history every 15 s. 120 symbols = 480 calls/min, above Groww's 300/min **[V]**. | Not used. One session loop. |
| F5 | vendor reconnect_ws | SDK 2.1.1 already auto-reconnects and replays subscriptions **[M]**. | Use the SDK's. Add a stale-tick watchdog only. |
| F6 | vendor sizing | No leverage, wrong inputs, returns quantity 1 when a data call fails. | Sizing in engine/portfolio. On data failure: no order. |
| F7 | vendor strategy_loader | Expects `signals(df)` + vectorbt; the socket is a `Strategy` class with `on_bar`. | Reuse only the dynamic import. |
| F8 | vendor portfolio_runner | One OS process per strategy. | Not used. Single process. |
| F9 | No safety gate | Nothing checks Analyze mode before an order. | Checked before start and every 30 s. |
| F10 | sector_map.json | 104 unique symbols, 14 repeated, stale symbols. | Spec §3. |
| F11 | config vs spec | Times and caps disagree. | Spec §12 is the authority. |

The `openalgo` SDK 2.1.1 needs only httpx, numpy, pandas, websocket-client; numba is not loaded **[M]**.

---

## 2. Capacity budget (1 GB free)

| Item | Memory | Tag |
|---|---|---|
| Engine process (Python + numpy + pandas + SDK + data) | ~100–130 MB, hard target ≤ 150 MB | M |
| UI server inside the engine (standard library) | ~2 MB | A |
| One browser tab showing the UI | ~150–300 MB | A |
| OpenAlgo Desktop | unknown, shown by the connection check as "free RAM now" | A |
| Headroom to keep | ≥ 200 MB | — |

Rules:
1. **One Python process.** UI server, feed, logic and orders all live in it.
2. **UI page is plain HTML + a little script.** No framework, no chart library, no build step, no Node.
3. The UI can be opened from the phone on the same Wi-Fi instead of a laptop tab. That saves the browser memory.
4. During market hours keep closed: code editor, AI coding agent, extra browser tabs.
5. Engine warns in the UI when free RAM drops below 200 MB and blocks new entries below 100 MB.

CPU: per tick the engine updates one number and checks at most 3 positions (3.6 µs measured here **[M]**; assume 10× slower on the laptop). Per 5-minute cycle the logic is a few array operations. The delay that matters is network round-trips through OpenAlgo. Target: order sent within 10 s of bar close, logged every time.

Broker budget: Groww live-data limit is 10 requests/s and 300/min **[V]**. Engine ceiling in market hours: 2 calls/s, 60/min.

| Phase of day | Calls |
|---|---|
| Session start: daily levels | ~105 daily-history calls at 2/s ≈ 1 min |
| Session start: NIFTY warm-up | 1 |
| Each 5m cycle | 0–3 history calls for armed symbols (cap 5) |
| Heartbeat | 1 light call every 30 s |
| Orders | ≤ 12 per day plus status polls |

---

## 3. What is stored, and why

**Market data is not archived.** Prices live in memory and are gone when the process stops.

| Kept | Why | Size |
|---|---|---|
| Today's daily levels (PDH, PDL, ATR, averages) | So a restart during the day does not refetch 105 calls. Overwritten every day. | < 1 MB |
| Decisions: regime, sector rank, shortlist per bar | This is what the UI shows as "what the system did and why". | small |
| Signals, orders, fills, positions, daily totals | Trade record. Needed after a restart, and it is the result of the whole exercise. | small |
| Activity log (plain sentences) | UI feed. | small |
| Health: connection status, latency, free RAM | UI status and fault finding. | small |

Without the trade and decision record there is nothing to judge the strategy on. That is the only "old data" kept.

One SQLite file. Decision rows older than 30 days are deleted; trade rows are kept.

Not kept: 5m bars, tick history, year-long datasets. Historical backtesting is a separate project.

---

## 4. OpenAlgo link (one layer, everything passes through it)

No other module talks to OpenAlgo directly.

**Wrapper duties:** timeout on every call · one retry for reads, none for entry orders · throttle to 2 calls/s ·
latency recorded per call · every error turned into a short message the UI can show.

**Connection check** — the only test in this project. Runs on the UI button and automatically before every session start.

| # | Check | If it fails |
|---|---|---|
| 1 | OpenAlgo REST reachable at configured host | BLOCK. "Start OpenAlgo Desktop." |
| 2 | API key accepted | BLOCK. "Paste the key from OpenAlgo into .env." |
| 3 | Broker session alive (funds call succeeds) | BLOCK. "Log in to Groww inside OpenAlgo." |
| 4 | Analyze mode is ON | BLOCK. "Switch OpenAlgo to Analyze mode." |
| 5 | Sandbox funds close to configured capital | Warn |
| 6 | Quote for NIFTY and one stock | Warn |
| 7 | 5m history for one stock: rows returned, volume present, time of last bar | Warn |
| 8 | Stream: connect, subscribe NIFTY + one stock, tick within 10 s | Warn. Skipped when market is closed. |
| 9 | Every universe symbol resolves | Warn, list the failures |
| 10 | Market open today (holiday / timings) | Info |
| 11 | Free RAM now | Warn below 200 MB |

**Heartbeat** every 30 s while the process runs: Analyze-mode status call. It proves OpenAlgo is alive and re-checks the mode.
- OpenAlgo unreachable → red banner, no new entries, keep retrying, resume by itself.
- Analyze mode found OFF → all order sending blocked at once, session halted, red banner. No order of any kind is sent.
- Stream silent for 5 s on a symbol with an open position → that symbol switches to quote polling until ticks return.

**Reconcile** every 60 s and on every start: compare stored positions with OpenAlgo's position book. Differences are shown in the UI.

Orders carry the strategy name as tag, so the same orders are visible in OpenAlgo's own order and trade book. The UI has a link to it.

---

## 5. Start, stop and the session clock

The process has two layers.

- **Control layer**: alive whenever the app is open. UI server, OpenAlgo heartbeat, connection check. Idle and cheap.
- **Session**: one trading-day run. Started by the **START** button, or by auto-start at 08:45 if the toggle is on. Ended by **STOP**, or by itself after the day report.

START works at any time. The session looks at the clock and joins at the right step:

| Started at | What happens |
|---|---|
| Before 09:15 | Connection check → levels → warm-up → wait for open → normal day |
| 09:15–14:15 | Connection check → levels → warm-up using today's bars so far → join at the next 5m boundary |
| 14:15–14:55 | Same, but view only: no new entries; manages positions already open |
| After 14:55, weekend, holiday | "Market closed" mode: connection check, levels, universe table. Live panels idle. Dry run of the last session is offered (from Phase 3). |
| Restart on the same day | Loads today's positions, trade count and P&L from the store, reconciles, continues |

STOP = no new entries, square off open paper positions, end the session. The control layer stays up.

Launch: one command, plus a double-click launcher file. Auto-start needs the process to be running already.

---

## 6. Data design

| Tier | What | Source | When | Used for |
|---|---|---|---|---|
| 0. Price stream | Last price for NIFTY + pre-filtered stocks (~100; Groww allows 1000 **[V]**) | WebSocket, LTP mode | continuous | Breadth, returns, proximity, arming, exits, NIFTY 5m price bars |
| 1. Bar fetch | 5m OHLCV, last 5 sessions | REST history | only for **armed** symbols, once per closed bar | Close, bar low/high, VWAP, slot volume, RVOL |
| 2. Daily levels | PDH, PDL, PDC, ATR(14), 20-day averages | REST daily history | once per session start | Pre-filter, scanner, strategy context |

Fallback if the stream is unstable **[A]**: batch quotes for the universe every 60 s, single quotes for open positions every 2–3 s.

---

## 7. Process and thread model

One process, four threads.

```
   Browser (laptop or phone)                OpenAlgo Desktop (Analyze)  <-- Groww
        |  HTTP, poll every 3 s                  ^ REST            ^ WebSocket
        v                                        |                 |
 +-------------------------- engine process (single) -----------------------------+
 |                                                                                |
 |  T4 UI server        GET page, GET state snapshot                              |
 |  (control layer)     POST start / stop / connection-check / auto toggle        |
 |                                                                                |
 |  OpenAlgo link       the only door to OpenAlgo: wrapper, heartbeat, reconcile  |
 |                                                                                |
 |  T1 stream thread    last_price[symbol] = ltp                                  |
 |  (SDK-owned)         open position? check stop / target / breakeven            |
 |                        -> EXIT job on queue                                    |
 |                                                                                |
 |  T2 session loop     clock-driven steps (section 5)                            |
 |                      every 5m: regime -> sector -> scanner -> arm ->           |
 |                        bar fetch -> strategy -> portfolio -> ENTRY job         |
 |                      after each step: refresh the state snapshot               |
 |                                                                                |
 |  T3 order worker     one queue, exits before entries                           |
 |                      the only thread that sends orders                         |
 |                                                                                |
 |  SQLite (one file)        logs/ (rotating)                                     |
 +--------------------------------------------------------------------------------+
```

Rules:
- T1 never calls the network and never writes to disk.
- T3 is the only sender of orders.
- T4 never computes anything. It returns a ready-made snapshot that T2 refreshes.
- Regime, sector, scanner, strategy and sizing are **pure**: data in, decision out, no I/O.

---

## 8. UI (one page)

Served at localhost by default. LAN access is an opt-in config switch and then needs a simple access code, because the page has Start and Stop.

| Area | Shows |
|---|---|
| Top bar | START / STOP · auto-start toggle and time · session state (idle, warming up, live, view only, market closed, halted) · clock |
| Connection | The 11 checks as green / amber / red with the fix text · "Run check" button · heartbeat age · last tick age · API latency · free RAM · link to OpenAlgo |
| Market | Regime with its inputs · sector table with RS and strong/weak marks |
| Scanner | Shortlist, scores, which symbols are armed |
| Signals | Each signal: taken, or rejected with the reason |
| Positions | Open positions: entry, stop, target, R so far |
| Today | Trades, P&L in rupees and R, costs, trades left, loss-limit state |
| Activity | Plain-sentence feed, newest first: "10:05 Regime TREND_UP. Auto and Metal strong." |
| Report | Day report text (Phase 5) |
| Build status | Which phases are built. Panels of phases not built yet are greyed with "comes in Phase N". |

Page polls one state endpoint every 3 s. No live charts.
After a session ends the page keeps showing that day's final state and the full activity feed, so the day can be read in the evening.

---

## 9. Module map

`vendor/` stays untouched. `engine/` is ours.

| Module | Responsibility | Phase |
|---|---|---|
| engine/app | Process entry, control layer, launch | 1 |
| engine/config | Load and validate config.yaml and .env | 1 |
| engine/oa | OpenAlgo link: wrapper, connection check, heartbeat, reconcile | 1 |
| engine/store | SQLite tables and writes | 1 |
| engine/ui | HTTP server, one page, state and action endpoints | 1 |
| engine/session | Session clock and state machine, start/stop, auto-start | 1 |
| engine/levels | Daily levels, universe clean-up, pre-filter, sector eligibility | 2 |
| engine/feed | Stream, last prices, NIFTY 5m price bars, stale watchdog, polling fallback | 2 |
| engine/regime | Regime with 2-bar confirmation (pure) | 2 |
| engine/sector | Median member return, RS, strong/weak (pure) | 2 |
| engine/scanner | Candidates, gate, score, shortlist, armed set (pure) | 2 |
| engine/bars | 5m history for armed symbols; VWAP, slot volume, RVOL | 3 |
| strategies/pdh_breakout | The plug, per STRATEGY_SOCKET.md | 3 |
| engine/portfolio | Sizing, caps, daily loss incl. MTM (pure) | 4 |
| engine/orders | Queue and worker; entry, exit, square-off; fill-price poll | 4 |
| engine/exits | Multi-position stop / target / breakeven on ticks | 4 |
| engine/report | Day report from the store | 5 |
| engine/llm | Two OpenRouter calls with timeout, log only | 5 |
| engine/dryrun | Fetch one past session on demand, run it through the same pure functions, orders off | 3 |

Vendor and SDK reuse: function-by-function table in BUILD.md §7. That table is the authority.
Short form: data_router (normalise, history fetch) · state (StrategyState, reconcile) · preflight (funds, holiday, symbol,
open position, pending orders) · cost_model (constants, slippage tracker; GST added in engine) · indicator_adapter (ATR only —
its ADX breaks with SDK 2.1.1) · strategy_loader (load_strategy only). SDK: ta.adx, ta.vwap, get_ltp, multiquotes,
analyzerstatus, timings, placesmartorder, closeposition, orderstatus.
Reference only: risk_manager, sizing, portfolio_runner, reference_strategies.

Dependencies: openalgo, pandas, numpy, PyYAML, python-dotenv. Nothing else. No web framework, no scheduler library, no test library.

---

## 10. Failure handling

| Failure | Behaviour |
|---|---|
| A BLOCK check fails at start | Session does not start. UI shows which check and the fix. |
| Analyze mode goes OFF mid-session | Order sending blocked, session halted, red banner. |
| OpenAlgo unreachable mid-session | Red banner, no new entries, retry, resume automatically. |
| Stream drop | SDK reconnects. Open positions fall back to quote polling after 5 s. |
| History fetch fails or bar missing | One retry after 5 s, then skip the signal and show it as rejected. |
| Entry order rejected | Logged and shown. No retry. |
| Exit not filled | Retry until flat. Shown in red until flat. |
| Engine crash and restart | Load store, reconcile, re-arm exits. No entries for the current bar. |
| Free RAM < 100 MB | No new entries. Amber banner. |
| Exit decided on a tick older than 5 s | Trade is flagged in the record. |

Square-off is 14:55, ten minutes before Groww's 15:05 cut-off **[V]**. Set the sandbox square-off to 15:05 to mirror it.

Limit of this design: stops live in the engine. Fine for paper. Before real money, add a broker-side stop order per position.

---

## 11. Dry run (Phase 3) and shadow comparison (Phase 5) — nothing archived

- **Dry run**: for evenings and weekends. Fetches the last session's 5m bars on demand, plays them through the same pure functions, shows the result in the same UI panels, sends no orders, then discards the bars.
- **Shadow comparison**: after the close, fetch that day's 5m bars for the pre-filtered universe, run the strategy with regime and sector filters off, save only the resulting signal rows with outcomes (spec §11). The bars are discarded.

Both process one day at a time, about 7,000 rows. Both can be switched off in config.

## Sources (checked 13 Nov 2026)

- Groww API rate limits: https://groww.in/trade-api/docs/python-sdk
- Groww feed payload and subscription limit: https://groww.in/trade-api/docs/python-sdk/feed
- OpenAlgo Analyzer mode: https://docs.openalgo.in/new-features/api-analyzer
- Groww MIS cut-off after Closing Auction Session: https://groww.in/blog/closing-auction-session
