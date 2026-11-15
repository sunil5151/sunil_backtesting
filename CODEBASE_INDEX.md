# Codebase Index — `sunil_backtesting`

> Auto-generated on **2026-11-15 09:48 IST** by `scripts/daily_health_check.py`. Do not hand-edit.

## 1. Project Entry Points & Layout

- **Workspace Root**: `sunil_backtesting/` (`BUILD.md`, `scripts/`, `CODEBASE_INDEX.md`, `CODE_HEALTH_REPORT.md`)
- **Application Root**: `intraday-engine/intraday-engine/`
- **Start Engine**: `intraday-engine/intraday-engine/start_engine.bat` or `python -m engine.app` (Web UI at `http://127.0.0.1:8800/`)
- **Safety Mode**: Paper / Analyze-mode only via OpenAlgo Desktop (Groww). Secrets stay in `.env` (gitignored).

## 2. Build Phases (`PROGRESS.md`)

| Phase | Scope | Status | Date |
|---|---|---|---|
| 1 | Shell, UI and the OpenAlgo link | `done` | 2026-11-13 |
| 2 | Market view | `done` | 2026-11-13 |
| 3 | Signals and dry run | `done` | 2026-11-13 |
| 4 | Paper trading | `done` | 2026-11-13 |
| 5 | Report, LLM and shadow comparison | `not started` | - |

## 3. Engine Modules (`engine/`)

| File | Lines | Classes | Functions | Purpose |
|---|---:|---|---|---|
| `engine/__init__.py` | 0 | - | 0 | - |
| `engine/app.py` | 108 | - | 4 | Process entry and control layer. Run from the project folder:  python -m engine.app |
| `engine/bars.py` | 464 | Signal, Exit, Context, StrategyChecklistEvaluator | 13 | 5m bar fetch for armed symbols, session VWAP, slot-volume baseline, RVOL and strategy socket. |
| `engine/config.py` | 331 | ConfigError, Config | 10 | Load and validate config.yaml and .env. Nothing else reads these files. |
| `engine/dryrun.py` | 894 | - | 6 | On-demand dry run of any selected (or last completed) session with full trade simulation. |
| `engine/exits.py` | 97 | - | 1 | Pure tick-level exit and +1R breakeven evaluation for open paper positions (Phase 4). |
| `engine/feed.py` | 201 | Feed | 12 | Live price feed, NIFTY 5m price bars, stale-tick watchdog and multiquotes fallback. |
| `engine/levels.py` | 191 | - | 5 | Universe clean-up, daily levels (PDH/PDL/PDC/ATR/20d avg), pre-filter and sector eligibility. |
| `engine/macro_report.py` | 1567 | MacroReportPDF | 21 | Dual-format Giant Macro Dry-Run Report compiler & renderer (.md + .pdf). |
| `engine/oa.py` | 582 | OALink | 32 | OpenAlgo link. The ONLY module that talks to OpenAlgo (BUILD.md rule 5). |
| `engine/orders.py` | 339 | OrderManager | 13 | Order queue, fill-price polling, broker reconcile and restart recovery (Phase 4). |
| `engine/page.html` | 1755 | - | 0 | HTML file |
| `engine/portfolio.py` | 151 | - | 6 | Pure sizing, portfolio caps, cost calculation, MTM and daily loss limits (Phase 4). |
| `engine/regime.py` | 141 | - | 4 | Pure market regime calculation on NIFTY 5m bars + universe breadth (spec section 4). |
| `engine/s3_archive.py` | 844 | - | 28 | Consolidated per-candle scan & signal analysis archive for AWS S3 (with local fallback). |
| `engine/scanner.py` | 70 | - | 2 | Pure scanner: candidates, proximity gate, z-score ranking, shortlist and armed set (spec section 6). |
| `engine/sector.py` | 53 | - | 1 | Pure sector relative strength ranking (spec section 5). |
| `engine/session.py` | 1250 | Controller | 41 | Control layer and session clock (architecture section 5). |
| `engine/socket_manager.py` | 706 | - | 12 | Strategy Socket Manager: upfront rules/parameters, qualification suite, OpenRouter AI check, plug/unplug/uploa |
| `engine/store.py` | 417 | Store | 23 | SQLite store: one file. |
| `engine/sysmem.py` | 65 | - | 0 | Free RAM on the machine and memory used by this process, standard library only. |
| `engine/ui.py` | 172 | ExclusiveThreadingHTTPServer | 2 | UI server: one page, one state endpoint, four actions. Standard library only. |

## 4. Strategy Plug-ins (`strategies/`)

| File | Lines | Classes | Functions | Purpose |
|---|---:|---|---|---|
| `strategies/orb_breakout.py` | 190 | Strategy | 5 | Strategy plug: Opening Range Breakout (adapted from vendor/reference_strategies/opening_range.py). |
| `strategies/pdh_breakout.py` | 227 | Strategy | 4 | Strategy plug: PDH/PDL Breakout (spec section 7, docs/STRATEGY_SOCKET.md). |

## 5. Vendor Core (`vendor/core/` — read-only)

| File | Lines | Classes | Functions | Purpose |
|---|---:|---|---|---|
| `vendor/core/__init__.py` | 0 | - | 0 | - |
| `vendor/core/cost_model.py` | 192 | CostBlock, SlippageTracker | 7 | cost_model.py - Real-world transaction cost and slippage model for Indian markets. |
| `vendor/core/data_router.py` | 393 | BarCloseWatcher | 13 | data_router.py - Unified data access for backtest and live modes. |
| `vendor/core/indicator_adapter.py` | 172 | _OpenAlgoBackend, _TaLibBackend | 38 | indicator_adapter.py - Routes indicator calls to either openalgo.ta or talib. |
| `vendor/core/portfolio_runner.py` | 282 | StrategyProcess, PortfolioRunner | 15 | portfolio_runner.py - Multi-strategy supervisor with portfolio-level risk caps. |
| `vendor/core/preflight.py` | 175 | PreflightError | 4 | preflight.py - Startup checks for live strategies. |
| `vendor/core/risk_manager.py` | 307 | RiskConfig, Position, RiskManager | 10 | risk_manager.py - Per-position risk: stop loss, take profit, trailing stop, time exit. |
| `vendor/core/sizing.py` | 113 | - | 3 | sizing.py - Position sizing helpers. |
| `vendor/core/state.py` | 248 | StoredPosition, StrategyState | 13 | state.py - SQLite-backed strategy state. |
| `vendor/core/strategy_loader.py` | 218 | - | 9 | strategy_loader.py - Dynamic strategy import + parameter patching. |

## 6. Documentation & Reference (`docs/`, `vendor/reference_strategies/`)

| File | Lines | Classes | Functions | Purpose |
|---|---:|---|---|---|
| `docs/ARCHITECTURE_v2.md` | 283 | - | 0 | MD file |
| `docs/STRATEGY_SOCKET.md` | 86 | - | 0 | MD file |
| `docs/STRATEGY_SPEC_v2.md` | 278 | - | 0 | MD file |

## 7. Automation Scripts (`scripts/`)

| File | Lines | Classes | Functions | Purpose |
|---|---:|---|---|---|
| `scripts/daily_health_check.py` | 586 | FuncInfo, FileStats | 14 | Daily Codebase Health Check & Index Generator for sunil_backtesting. |

## 8. Key Data & Config Files

- `intraday-engine/intraday-engine/config.example.yaml` — Template trading/risk/UI settings
- `intraday-engine/intraday-engine/requirements.txt` — Python dependencies
- `intraday-engine/intraday-engine/data/sector_map.json` — Read-only NSE universe & sectors
- `intraday-engine/intraday-engine/data/universe_clean.json` — Cleaned 104-stock universe output
- `intraday-engine/intraday-engine/data/scan_archive/` — Archived dry-run scans and macro reports
