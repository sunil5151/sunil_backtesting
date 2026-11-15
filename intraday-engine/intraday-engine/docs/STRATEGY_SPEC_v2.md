# STRATEGY_SPEC v2.1 — Regime + Sector filtered PDH/PDL Breakout (NSE intraday, MIS)

Status: REVIEWED DRAFT. Paper trading only (OpenAlgo Analyze mode). Still not tested on data.
Supersedes v1. Companion docs: ARCHITECTURE_v2.md (structure), BUILD.md (build order).

v2.1 changes: session starts by button at any time (auto-start optional) · report goes to the UI, no Telegram ·
no market-data archive; shadow comparison fetches the day's bars on demand · historical backtest is outside this build.

Tags used below: **[V]** verified from a source on 13 Nov 2026 · **[M]** measured/calculated · **[A]** assumption; the connection check or the first sessions will confirm it.

---

## A. What changed from v1, and why

### Critical (v1 would have produced wrong results or penalties)

| # | v1 said | Problem | v2 fix |
|---|---|---|---|
| C1 | Square-off 15:10 | Since 3 Aug 2026 NSE runs a Closing Auction Session: continuous trading in F&O stocks ends 15:15, and Groww auto-squares MIS in F&O-enabled stocks at **15:05**, ₹50 + GST per position **[V]**. 15:10 is after the broker's cut-off. | Square-off **14:55**, verify flat at 15:00. Last entry 14:15. Session = 360 min / 72 five-minute bars. |
| C2 | Cost ≈ ₹55–70 ≈ 0.12R | Wrong. Slippage was left out and cost in R depends on stop width. At ₹500 risk the model's own numbers give **0.19R–0.46R** **[M]** (table §9). At a 0.4% stop a 2R-target system needs ~49% wins just to break even. | Stop floor raised 0.4% → **0.6%**. Hurdle restated in §9. Cost in R logged per trade. |
| C3 | Build bars, VWAP and volume from live ticks | Groww's live LTP stream carries only price and timestamp, no volume **[V]**. Volume-based rules cannot come from the stream. | Volume, VWAP and exact bar OHLC come from 5m history (REST) for the few symbols that are about to trigger. Scanner uses price only. |
| C4 | Regime uses NIFTY 50 session VWAP | An index has no traded volume, so it has no VWAP. | Use **session mean price** of NIFTY (running average of 5m typical price). Same role, defined without volume. |
| C5 | Measure filtered trades for 20 days | The hypothesis is "filtered breakouts work, unfiltered do not", but v1 never records the unfiltered ones, so it cannot be tested. 20 days gives maybe 20–40 trades; at 30 trades the win-rate error band is about ±18 points **[M]**. | Shadow log of every raw signal (no order) evaluated at end of day. Decision gate at **≥100 closed trades or 60 trading days**, whichever is later. §11. |
| C6 | 12 sectors × 10 = 120 stocks | File has **104 unique** symbols **[M]**. Commodities has no stock of its own (all 10 repeat elsewhere); RELIANCE and COALINDIA sit in 3 sectors. Overlap defeats "max 2 per sector". TATAMOTORS is now TMPV (CV arm is TMCV) **[V]**. Non-F&O names can lock in a circuit, which is dangerous for intraday shorts. | One stock = one sector. F&O stocks only. Drop Commodities. A sector counts only if ≥5 members pass the pre-filter. Validate every symbol against the broker master at startup. §3, §5. |
| C7 | "Paper trading only" (statement) | Nothing enforces it. Sandbox default capital is ₹1 crore **[V]**, so "cap by available margin" does nothing. Sandbox does not model slippage or partial fills **[V]**, so "expected vs filled" slippage from paper is not evidence. | Engine refuses to start unless Analyze mode is ON. Sandbox capital set to ₹50,000. Notional cap computed in the engine. Paper slippage treated as a lower bound; results also reported at 10 bps stress. |

### Important

| # | v1 | Problem | v2 fix |
|---|---|---|---|
| I1 | Scanner every 15 min | A stock that breaks out at 09:50 is not on the 09:45 list; by 10:00 the no-chase rule may exclude it. | Scanner every 5 min. It is price-only, so it costs nothing. |
| I2 | Bar volume > 1.5 × avg of previous 20 bars | The 20-bar window mixes in the opening and closing bars, which are always the heaviest. Threshold drifts through the day. | Compare with the **same time slot averaged over the last 5 sessions**. |
| I3 | RVOL = cum volume ÷ (20d avg × fraction of session) | Volume is U-shaped; linear fraction overstates morning RVOL. | RVOL = today's cumulative volume ÷ average cumulative volume at the same time over last 5 sessions. Computed at signal time, logged, used as a gate. |
| I4 | Regime recomputed every 5 min, no memory | Flip-flops between TREND and CHOPPY on single bars. | A regime change takes effect only after **2 consecutive bars** agree. |
| I5 | Breakeven at +1R fixed | Breakouts often retest the level. A breakeven stop turns those into scratches that still pay costs. Untested either way. | Keep as default, but it is a parameter. Shadow log scores three exit variants side by side (§11). |
| I6 | Daily loss ₹1,500 | Not defined whether open losses and costs count. | Realised P&L + open MTM − costs. |
| I7 | Timeline: scanner stops 14:15, entries till 14:30 | Inconsistent. | Both 14:15. |
| I8 | config.example.yaml | Disagrees with the spec: no-entry-before 09:20 (spec 09:30); no per-sector cap; no pre-filter, sector, stop or leverage keys. | §12 lists the keys. Spec is the authority. |
| I9 | Stop only in the engine | If the laptop hangs, a live position has no stop. Fine for paper. | Before any live trading: broker-side SL-M order as backstop. Not in v1 scope. |

---

## 0. Purpose

Trade only in the direction of the day's market, only in the day's strongest (long) or weakest (short)
sectors, only when a stock breaks yesterday's high (long) or low (short) with volume, and cap losses hard.

Hypothesis: breakouts aligned with market regime and sector strength have positive expectancy after costs;
breakouts on choppy days or against sector flow do not. **Both halves are measured** (§11).

## 1. Constants

| Item | Value |
|---|---|
| Capital | ₹50,000 (also set as sandbox capital) |
| Product / exchange | MIS / NSE cash equity. No F&O instruments traded. |
| Universe | sector_map.json after clean-up (§3). F&O-eligible stocks only. |
| Bar size | 5-minute. Session 09:15–15:15 = 72 bars. |
| Risk per trade | ₹500 (1%) |
| Leverage assumed | 5× (sandbox default **[V]**; Groww live margin differs per stock **[A]**) |
| Notional cap per position | capital × leverage ÷ max positions = ₹83,333 |
| Minimum achievable risk | ₹300. If the notional cap forces less, skip the trade. |
| Max open positions | 3 |
| Max positions per sector | 2 |
| Max trades per day | 6 |
| Daily loss limit | ₹1,500 (realised + open MTM − costs) → no new entries |
| No entry before / after | 09:30 / 14:15 |
| Square-off | 14:55 all positions; 15:00 confirm flat |

## 2. Daily timeline

A session starts when START is pressed in the UI, or at 08:45 if auto-start is on.
The steps below run in order; a session started late does the start-up steps at once and joins at the next 5m boundary.

| Time | Step | Who |
|---|---|---|
| at start | Connection check: OpenAlgo reachable, key, broker login, Analyze mode ON, funds, data, free RAM | Code |
| at start | Pre-market brief (log only; skipped if started after 09:15) | LLM-1 |
| at start | Daily levels: PDH, PDL, PDC, ATR(14), 20-day avg volume and traded value. Symbol validation. Pre-filter (§3). | Code |
| at start | NIFTY 5m warm-up (3 sessions, plus today so far). Subscribe price stream. | Code |
| 09:15–09:30 | Observe only | Code |
| every 5m, 09:30–14:15 | Regime (§4) → sector rank (§5) → scanner (§6) → strategy on armed symbols (§7) | Code |
| every price tick | Exits for open positions: stop, target, breakeven (§8) | Code |
| 14:15 | No new entries | Code |
| 14:55 | Square-off; 15:00 confirm flat, retry if not | Code |
| after 15:40 | Shadow comparison (§11), if enabled | Code |
| 15:50 | Plain-language day report, shown in the UI | LLM-2 |

Late and off-hours starts:
- Started 09:15–14:15: trades from the next 5m boundary. Signals that fired before the start are not chased.
- Started 14:15–14:55: view only, no new entries.
- Started after 14:55, on a weekend or a holiday: market-closed mode. No trading; levels and universe are shown.
- Restarted on the same day: today's trade count, P&L and "already traded" symbols are loaded from the record, not reset.

## 3. Universe and pre-filter (once, at session start)

Universe clean-up (one-time, then weekly check):
- Each stock belongs to exactly one sector: the one where its listed weight is highest.
- Remove the Commodities sector (no unique members).
- Keep only stocks that have stock futures listed (F&O-eligible). **[A]** derive from the broker master.
- Validate every symbol against the OpenAlgo/Groww master. Known stale: TATAMOTORS. Suspected, to check: PVR, TV18BRDCST, IBREALEST, LTIM **[A]**.

Daily drop rule — drop a stock if any is true:
price < ₹100 or > ₹5,000 · 20-day avg traded value < ₹50 crore · daily ATR(14)% < 1.2% ·
not MIS-allowed · symbol failed validation · (v2 only) on LLM-1 avoid-list.

A sector is **eligible** for ranking only if at least 5 of its members survive the pre-filter.

## 4. Regime (NIFTY 50, 5m bars) — deterministic

Inputs:
- ADX(14) on NIFTY 5m bars, warmed with the prior 3 sessions.
- Session mean = running average of NIFTY 5m typical price since 09:15.
- Crosses = number of NIFTY 5m closes that crossed the session mean in the last 12 bars.
- Breadth A/D = advancers ÷ decliners in the pre-filtered universe versus previous close.

Raw state each bar:
- CHOPPY if at least 2 of: ADX < 20 · crosses ≥ 4 · 0.8 ≤ A/D ≤ 1.25
- else TREND_UP if NIFTY > session mean and A/D > 1
- else TREND_DOWN if NIFTY < session mean and A/D < 1
- else CHOPPY

Active regime changes only when the raw state has been the same for **2 consecutive bars**.

Effect: CHOPPY → no new entries. TREND_UP → longs only. TREND_DOWN → shorts only.
Open positions are not closed on regime change.

Logged but not used in v1: day efficiency = |NIFTY − day open| ÷ (day high − day low).

## 5. Sector rank — deterministic

Sector return = **median % change from previous close of its eligible members**.
RS = sector return − NIFTY % change from previous close.
Rank eligible sectors by RS. Strong = top 3 with RS > +0.25%. Weak = bottom 3 with RS < −0.25%.

Why median of members and not the official index: it needs no extra data feed, it cannot be
dominated by stocks we do not trade, and stale index weights stop mattering.
Logged for comparison: official sector index RS (if the feed provides it) and RS measured from today's open.

## 6. Scanner — deterministic, price only, every 5 minutes

Candidates: long = stocks in Strong sectors; short = stocks in Weak sectors. Only the side allowed by regime.

For each candidate:
1. Stock RS = stock % change − NIFTY % change (long: higher is better; short: lower is better).
2. Proximity = (PDH − LTP) ÷ daily ATR for long; (LTP − PDL) ÷ daily ATR for short.
   Gate: keep only −0.5 ≤ proximity ≤ +0.5. Score: smaller absolute value is better.

Score = z(Stock RS, signed for the side) − z(|proximity|), within the candidate set.
Shortlist = top 5 for the allowed side.

**Armed** = shortlisted symbol whose LTP at the 5m boundary is beyond PDH × 1.001 (long) or PDL × 0.999 (short).
Only armed symbols get a 5m history fetch and a strategy check. Usually 0–3 per bar.

## 7. Strategy plug: `pdh_breakout`

Evaluated on the just-closed 5m bar of an armed symbol, using 5m history of the last 5 sessions.

LONG when ALL true:
- close > PDH × 1.001
- close > stock's session VWAP (from today's 5m bars)
- bar volume > 1.5 × average volume of the same time slot over the last 5 sessions
- RVOL ≥ 1.0 (today's cumulative volume ÷ 5-session average cumulative volume at this time)
- day open < PDH
- close − PDH < 0.5 × daily ATR
- symbol not traded earlier today

SHORT: exact mirror with PDL.

Stop: the **further** of (breakout bar low − 0.05%) and (entry − 0.6%). Short: mirror.
Reject if stop distance > 1.5% of entry.
Target: entry ± 2R, where R = |entry − stop| measured from the actual fill.

## 8. Execution and risk (engine side)

- Quantity = floor(₹500 ÷ R per share), then capped so notional ≤ ₹83,333. If the cap leaves risk < ₹300, skip.
- Entry: MARKET. If LTP at order time has already moved beyond the no-chase limit, skip.
- Record: bar close time, order time, decision price, fill price, tick age.
- At +1R move stop to entry (parameter `breakeven_at_r`, default 1.0; 0 disables).
- Exit on: stop, target, 14:55, or kill switch.
- After the daily loss limit: no new entries; open trades keep their stops.
- On restart: reconcile with the position book, re-arm stops from stored state.

## 9. Costs

Model: ₹20 brokerage per order + 18% GST on it **[A: ₹20 applies at our order sizes; confirm on Groww pricing]** ·
statutory ≈ 0.0225% per side (equity intraday STT is 0.025% on the sell side **[V]**) · slippage 5 bps per side **[A]**.

Round-trip cost at ₹500 risk **[M]**:

| Stop distance | Notional | Cost at 5 bps | In R | Break-even win rate* | Cost at 10 bps stress | In R |
|---|---|---|---|---|---|---|
| 0.4% (v1 floor) | ₹1,25,000 | ₹228 | 0.46R | 48.6% | — | — |
| 0.6% (v2 floor) | ₹83,333 | ₹168 | 0.34R | 44.5% | ₹251 | 0.50R |
| 0.8% | ₹62,500 | ₹138 | 0.28R | 42.5% | ₹200 | 0.40R |
| 1.0% | ₹50,000 | ₹120 | 0.24R | 41.3% | ₹170 | 0.34R |
| 1.5% | ₹33,333 | ₹96 | 0.19R | 39.7% | ₹129 | 0.26R |

*2R target, 1R stop, no breakeven move. With the breakeven move the required win rate is higher.

Reading: tight stops are expensive. The system needs roughly 42–45% full winners to break even, not the ~38% v1 implied.

## 10. LLM placement

| LLM | When | Output | Can it trigger trades? |
|---|---|---|---|
| LLM-1 (web + X search) | session start, before 09:15 | JSON: mood, per-sector bias −2..+2, avoid-list with reasons | v1: No, log only. v2: avoid-list veto, only if logs show it helped. |
| LLM-2 (cheap, fast) | 15:50 | Day summary and why each trade happened | No |

Both calls have a hard timeout and are non-fatal. Model slugs in config are **[A]** — confirm they exist on OpenRouter.
Regime, sector rank, scanner, strategy, sizing, exits = code only.

## 11. What to measure

Per trade: R multiple gross and net, cost in R, stop %, regime, sector rank, RVOL, latency bar-close → order, tick age at exit.
Per day: trades, % of bars CHOPPY, P&L by regime and by sector rank, LLM bias vs actual sector move.

**Shadow log (the control group).** After the close, fetch the day's 5m bars for every pre-filtered stock
on demand, run them through the same strategy with regime and sector filters OFF, save only the resulting
signal rows, and discard the bars. Nothing is archived. For each raw signal store: regime and sector
rank at that moment, whether the live filters would have passed it, and the outcome under three exits:
- A: 1R stop, 2R target, no breakeven
- B: as A, stop to entry at +1R (v1 default)
- C: 1R stop, trail by 1R after +1R, no fixed target
Also score the stop alternative: 0.3 × daily ATR instead of bar-low / 0.6%.
When stop and target fall inside the same bar, count the stop first.

**Decision gate (proposal).** Review at ≥100 closed paper trades or 60 trading days, whichever is later:
- Net expectancy > 0 at 10 bps stress slippage.
- Filtered signals beat unfiltered shadow signals by ≥ 0.15R.
- Max drawdown ≤ 10R. No day worse than −3R.
Early stop: after 50 trades, net expectancy below −0.2R → halt and rethink.
A historical backtest is a separate project and is not part of this build. Until it exists, the paper record
and the shadow log are the only evidence.

## 12. Config keys to add or change

| Key | Value |
|---|---|
| session.no_entry_before | "09:30" |
| session.no_entry_after | "14:15" |
| session.square_off | "14:55" |
| session.bars_per_day | 72 |
| rescan_minutes | 5 |
| risk.max_positions_per_sector | 2 |
| risk.leverage | 5 |
| risk.min_risk_rupees | 300 |
| risk.daily_loss_includes_mtm | true |
| prefilter.* | price band, min traded value, min ATR%, fno_only, min_members_per_sector |
| regime.confirm_bars | 2 |
| sector.rs_threshold_pct | 0.25 |
| strategy_params | buffer 0.001, vol_mult 1.5, vol_baseline_sessions 5, min_stop_pct 0.006, max_stop_pct 0.015, target_r 2, breakeven_at_r 1.0 |
| safety.require_analyzer_mode | true |
| start.auto_enabled | false |
| start.auto_time | "08:45" |
| ui.port | 8800 |
| ui.lan_access | false |
| shadow.enabled | true |
| dryrun.enabled | true |

## 13. v1 open questions — answers

1. **ADX + crosses + breadth as choppy test?** Keep for v1, add the 2-bar confirmation. Do not tune before data. Day efficiency is logged as the challenger.
2. **Shorts on TREND_UP days in very weak sectors?** Not traded in v1. The shadow log records them; decide at the gate.
3. **Bar-low stop too tight?** Yes on cost grounds (§9). Floor is 0.6%. 0.3 × ATR is scored in shadow.
4. **2R fixed vs trailing?** Unknown without data. Variants A, B, C are scored in shadow on the same signals.
5. **Opening-range variant for gap days?** Not now. One strategy until the gate. It is a separate plug later.
6. **₹50 crore liquidity floor?** Adequate. Largest order ₹83k is about 1.2% of an average 5m bar for a ₹50 crore/day stock **[M]**. F&O-only already clears it for most names.

## Sources (checked 13 Nov 2026)

- Groww Closing Auction Session and MIS timings: https://groww.in/blog/closing-auction-session
- Broker square-off times and fees: https://onetradejournal.com/brokers/auto-square-off-times-and-charges
- Groww square-off charge: https://groww.in/help/stocks/sx-margin/what-are-intraday-square-off-charges-1
- Groww feed payload: https://groww.in/trade-api/docs/python-sdk/feed
- OpenAlgo Analyzer (sandbox) behaviour: https://docs.openalgo.in/new-features/api-analyzer
- Tata Motors symbol change: https://www.angelone.in/news/market-updates/tata-motors-demerger-tata-motors-renamed-to-tmpv-commercial-vehicles-listing-update
- STT rates: https://groww.in/blog/what-is-stt
