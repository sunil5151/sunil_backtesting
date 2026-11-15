# intraday-engine

Paper-trades an intraday breakout strategy on NSE stocks through OpenAlgo Desktop (broker: Groww)
in **Analyze mode only**. One Python process, one web page. Built phase by phase, see `PROGRESS.md`.

## Run

1. Start OpenAlgo Desktop, log in to Groww inside it, switch it to **Analyze mode**.
2. Put your OpenAlgo API key in `.env` in **this** folder (`OPENALGO_API_KEY=...`).
3. Double-click `start_engine.bat`. The page opens at http://127.0.0.1:8800/
   (or run `python -m engine.app` from this folder). Keep the black window open.
4. Press **Run check**, then **START**.

No virtual environment is used. Packages are installed into the laptop's Python:
`pip install -r requirements.txt`.

## Folders

| Path | What |
|---|---|
| `engine/` | Our code. `app` (entry), `config`, `oa` (the only door to OpenAlgo), `store` (SQLite), `session` (clock, START/STOP, auto-start), `ui` + `page.html` |
| `strategies/` | Strategy plug-ins (Phase 3) |
| `vendor/` | Open-source parts (MIT). Read-only, imported, never edited |
| `data/` | `sector_map.json` (universe), `engine.db` (store, created on first run) |
| `docs/` | `ARCHITECTURE_v2.md`, `STRATEGY_SOCKET.md` |
| `logs/` | `engine.log` (rotating) |
| `config.yaml` | Settings (created from `config.example.yaml` on first run) |
| `.env` | API key and OpenAlgo address. Never shared, never shown in the UI |

## Safety

- The engine never switches Analyze mode. It checks the mode before START and every 30 s.
  If it is OFF, START is refused and a running session is halted.
- No market data is archived. Only decisions, trades, the activity feed and health are stored.

## Licenses
- `vendor/core`, `vendor/reference_strategies`: MIT © Rajandran R / Marketcalls (see `vendor/LICENSE-*`)
- `data/sector_map.json`: MIT © OpenAlgo (see `data/LICENSE-*`)
