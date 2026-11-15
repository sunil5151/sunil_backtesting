# Codebase Health Report — `sunil_backtesting`

> Generated on **2026-11-15 09:48 IST** | Mode: **Semi-Automatic** (Read-Only Scan — no application files modified)

## 1. Executive Summary

| Metric | Result | Target / Policy |
|---|---|---|
| **Overall Status** | **PASS WITH WARNINGS** | Zero syntax/safety errors; keep modules modular |
| **Active Modules (`engine/` + `strategies/`)** | 24 files (9,060 Python lines) | Clean separation per `ARCHITECTURE_v2.md` |
| **AST Syntax Check** | 37/37 Python files valid | 100% valid syntax |
| **Paper-Only & OpenAlgo Gateway Rules** | 0 violations | 0 violations (`BUILD.md` Rules 1 & 5) |
| **Bloated Files (`>400` lines)** | 6 critical (`>700`L), 3 warning | Keep modules under 400 lines |
| **Oversized Functions (`>80` lines)** | 23 functions | Split functions > 80 lines |
| **Missing `requirements.txt` Packages** | 1 package(s) | Every import declared |
| **Git Version Control** | Initialized | Tracked on `main` |
| **Runtime Artifacts** | `engine.db`: 544.0 KB, `engine.log`: 98.5 KB | Gitignored locally |

> Note on tests: `BUILD.md` Rule 3 intentionally omits a test framework (`No test suite`). Automated verification currently relies on AST syntax/safety checks and the UI's 11-point connection check.

## 2. Bloated & Monolithic Files

| Severity | File | Lines | Suggested Split |
|---|---|---:|---|
| `CRITICAL` | `engine/page.html` | 1755 | Separate CSS/JS into `engine/static/` or component partials while keeping zero-build vanilla JS |
| `CRITICAL` | `engine/macro_report.py` | 1567 | Split into data compiler, markdown renderer, PDF renderer, and CLI entry |
| `CRITICAL` | `engine/session.py` | 1250 | Extract 5m cycle runner, live armed evaluator, and worker lifecycle helpers |
| `CRITICAL` | `engine/dryrun.py` | 894 | Break `run_dry_session` (593 lines!) into bar replay loop, position simulator, and summary builder |
| `CRITICAL` | `engine/s3_archive.py` | 844 | Separate AWS SigV4 HTTP client from scan document builders |
| `CRITICAL` | `engine/socket_manager.py` | 706 | Separate qualification harness, OpenRouter verifier, and starter template strings |
| `WARN` | `engine/oa.py` | 582 | Extract the 11-step `run_connection_check` into dedicated check helpers |
| `WARN` | `engine/bars.py` | 464 | Separate OHLCV bar builder from strategy context & RVOL evaluator |
| `WARN` | `engine/store.py` | 417 | Split schema migrations from query/read/write repository methods |

## 3. Largest Functions (`>80` lines)

| File | Function | Lines | Range |
|---|---|---:|---|
| `engine/dryrun.py` | `run_dry_session` | 593 | L302-L894 |
| `engine/macro_report.py` | `compile_macro_data` | 387 | L218-L604 |
| `engine/macro_report.py` | `render_macro_pdf` | 349 | L998-L1346 |
| `engine/oa.py` | `run_connection_check` | 247 | L336-L582 |
| `engine/session.py` | `Controller._build` | 245 | L1002-L1246 |
| `engine/socket_manager.py` | `qualify_strategy_file` | 243 | L271-L513 |
| `engine/macro_report.py` | `render_macro_markdown` | 233 | L607-L839 |
| `engine/session.py` | `Controller._evaluate_armed_live` | 212 | L406-L617 |
| `strategies/pdh_breakout.py` | `Strategy.evaluate_signal` | 159 | L60-L218 |
| `engine/s3_archive.py` | `build_all_stocks_rows` | 152 | L212-L363 |
| `engine/bars.py` | `evaluate_strategy_bar` | 149 | L209-L357 |
| `engine/ui.py` | `make_server` | 136 | L37-L172 |
| `engine/dryrun.py` | `_step_open_positions` | 132 | L168-L299 |
| `engine/config.py` | `load_config` | 123 | L140-L262 |
| `engine/macro_report.py` | `generate_and_save_macro_report` | 121 | L1408-L1528 |

## 4. Dependency, Hygiene & Structure Findings

- **[HIGH] Undeclared dependency `fpdf` (`pip install fpdf2`)**: imported in `engine/macro_report.py` but missing from `requirements.txt`.
- **[LOW] Double-nested directory**: application sits at `intraday-engine/intraday-engine/` (keep in mind when running scripts or commands).
- **[LOW] Duplicate generated exports at repo root**: 5 files (`MACRO_DRYRUN_2026-11-11_09-40_to_16-00_22Scans_56Signals_1Passed.md, MACRO_DRYRUN_2026-11-11_09-40_to_16-00_22Scans_56Signals_1Passed.pdf, MACRO_DRYRUN_2026-11-13_11-10_to_15-30_52Scans_101Signals_0Passed.md`...) duplicate `data/scan_archive/` outputs (gitignored at root).

## 5. Actionable Recommendations (Copy-Paste Prompts for AI)

### Recommendation #1 — Fix Missing `fpdf2` Dependency in `requirements.txt` `[LOW RISK]`
```text
In intraday-engine/intraday-engine/requirements.txt, add fpdf2 (required by engine/macro_report.py) and update BUILD.md Rule 4 note if approved so fresh installs don't fail with ModuleNotFoundError.
```

### Recommendation #2 — Modularize `engine/dryrun.py` (`run_dry_session` = 593 lines) `[MEDIUM RISK]`
```text
Refactor run_dry_session in intraday-engine/intraday-engine/engine/dryrun.py into small single-purpose helper functions (bar preparation, armed evaluation, simulated exits, and archive/report output) without changing dry-run numbers or output format.
```

### Recommendation #3 — Split `engine/macro_report.py` (1,567 lines) & `engine/session.py` (1,250 lines) `[MEDIUM RISK]`
```text
Split engine/macro_report.py into compilation vs Markdown/PDF rendering modules, and split Controller._build / _evaluate_armed_live in engine/session.py into focused helpers while keeping runtime behavior identical.
```
