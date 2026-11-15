# PROGRESS

## Phase table

| Phase | What | State | Date |
|---|---|---|---|
| 1 | Shell, UI and the OpenAlgo link | done | 2026-11-13 |
| 2 | Market view | done | 2026-11-13 |
| 3 | Signals and dry run | done | 2026-11-13 |
| 4 | Paper trading | done | 2026-11-13 |
| 5 | Report, LLM and shadow comparison | not started | |

## What you can see now

Everything from Phases 1–3, plus Phase 4:

- **Universe table** (inside **Scanner & Universe**): click *"Universe: 72 kept in 9 eligible sectors, 32 dropped"* to see all 104 deduplicated symbols, each in a single sector, with `PDH`, `PDL`, `ATR%`, and `KEPT` or `DROP` with the exact reason. `data/sector_map.json` is untouched; the cleaned universe is saved to `data/universe_clean.json`.
- **Market panel**: live `Regime` (`CHOPPY`, `TREND_UP`, `TREND_DOWN` with 2-bar confirmation), its 4 inputs (`ADX(14)`, `Session mean`, `Crosses (12)`, `Breadth A/D`), and the **Sector table** with member count, median return %, RS %, and `STRONG` / `WEAK` tags.
- **Scanner panel**: shortlist (top 5 for the regime-allowed side) with `LTP`, breakout level (`PDH`/`PDL`), proximity in ATR, z-score, and `ARMED` badge.
- **Signals panel**: shows every evaluated armed 5m bar with `Bar close`, `Ready at`, `Symbol`, `Side`, `Qty`, `Entry`, `Stop`, `Target`, `RVOL / Vol`, and `WOULD TRADE` (green) or `REJECTED` (red) with the exact reason (saved in `data/engine.db`).
- **Positions panel**: live open paper positions with `Symbol`, `Side`, `Qty`, `Entry`, `Stop` (`(BE)` badge when moved to entry at `+1R`), `Target`, `LTP`, `P&L ₹`, and `R`.
- **Today panel**: trades taken / left (`X / 6`), `Net P&L` (in `₹` and `R`), `Realised / MTM` and estimated round-trip costs (`₹20 + 18% GST` per order + statutory), `Loss limit` (`₹1,500`), closed trades table, and red banner on any OpenAlgo positionbook mismatch.
- **Dry run: last session** button (top bar): replays the last completed session (`POST /api/dryrun`) through the exact same `regime -> sector -> scanner -> bars/strategy` logic with zero orders, populates the Market, Scanner, Signals, and Activity panels with bar times, and frees the 5m bars (`gc.collect()`).
- **Activity feed**: a plain-language summary line every 5-minute bar (e.g. `12:55 TREND_DOWN. Realty, Auto, Pvt Bank weak. 1 armed (ICICIBANK).`).
- **Last tick age meter** (in **Connection**): live WebSocket tick age in seconds (`0–3 s`), with automatic `multiquotes` polling fallback and an amber banner if the stream goes silent.
- **Evening / post-STOP persistence**: daily levels and the latest Market/Scanner/Universe/Signals state are saved in `data/engine.db`, so stopping the session or reopening the page in the evening still shows the day's last state.

Tested on this laptop on 13 Nov 2026 (live market):
- `load_or_build_levels` processed 104 unique NSE stocks: 72 kept in 9 eligible sectors (`Auto`, `Energy`, `FMCG`, `IT`, `Metal`, `PSU Bank`, `Pharma`, `Pvt Bank`, `Realty`); `Infra` (4) and `Media` (3) marked ineligible (< 5 kept). Cached in SQLite for fast same-day restarts (`_do_check` ran in 6.6 s; only `IBREALEST`, `TV18BRDCST` do not resolve).
- Live WebSocket LTP stream connected for `NIFTY` + 72 stocks (`tick age: 0 s`, `73 prices`).
- Mid-day 2-bar regime warm-up + `sector` + `scanner` verified live: `TREND_DOWN` (`ADX 22.49`, `breadth 0.164`), `SHORT` shortlist of 5 candidates with `ICICIBANK` armed.
- Phase 3 socket & strategy: `docs/STRATEGY_SOCKET.md` updated per `BUILD.md` §6; `strategies/pdh_breakout.py` loaded via `core.strategy_loader.load_strategy`. Live 5m bar evaluation verified on `ICICIBANK` (`13:35` boundary: `vwap 1575.53`, `slot_vol_avg 502485.5`, `rvol 0.29`, rejected with `Bar close 1567.00 <= PDH+0.1% (1594.09)`).
- Full dry run via `POST /api/dryrun` replayed `2026-11-11` (`81` bars across `72` kept stocks): `57` signals recorded (`1` `WOULD TRADE`: `12:05 BHARATFORG LONG`, `vol 2.5x slot, RVOL 1.00, stop 0.60%`; `56` `REJECTED` with exact reasons).
- Engine memory after dry run: `107 MB` (target `<= 150 MB`); Phase 2 live baseline `100 MB`, free RAM `1227 MB`.
- Phase 4 paper trading verified:
  - Sizing & gates (`engine/portfolio.py`): `₹500` risk / `₹83,333` notional cap (`50` shares @ `₹1,500` with `₹10` stop; rejects below `₹300` min risk), max 3 open, max 2/sector, max 6/day, `₹1,500` daily loss limit, no-chase at order time, and `core.cost_model.lookup("MIS", "NSE")` + 18% GST (`₹81.17` on 50 shares @ `₹1,500`).
  - Exits (`engine/exits.py`): `+1R` breakeven stop move, `STOP`/`BREAKEVEN`/`TARGET`/`SQUARE_OFF` (`14:55`) + `15:00` flat confirm, and `stale_flag` on ticks older than `5 s`.
  - Live OpenAlgo Analyze round-trip (`engine/orders.py`): `INFY` `qty=1` `BUY` (`orderid 26111327770552`) -> `TARGET` `SELL` (`costs ₹47.71`, `net ₹-48.21`), plus `reconcile` detected external `RELIANCE` `qty=10` mismatch. Engine RAM `100 MB` (`<= 150 MB`).

## What is left

- Phase 5: day report, LLM brief, shadow comparison.

## Open points

1. **F&O filter (`prefilter.fno_only`) is set to `false`** in `config.yaml` per user instruction (cash equity intraday only). Can be toggled back to `true` in `config.yaml` anytime.
2. **Sandbox funds ₹97,316 vs capital ₹50,000** (check 5 is amber). Left as-is per user instruction.
3. **Renamed symbols mapped in `config.yaml`**: `TATAMOTORS -> TMPV`, `LTIM -> LTM`, `PVR -> PVRINOX`. `TV18BRDCST` and `IBREALEST` do not resolve on NSE and are dropped automatically.

## How to run

1. Start OpenAlgo Desktop, log in to Groww, Analyze mode ON.
2. API key goes in `intraday-engine/intraday-engine/.env`.
3. Double-click `start_engine.bat` and keep the black window open. The page is at http://127.0.0.1:8800/.
