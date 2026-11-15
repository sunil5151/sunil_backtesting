# Strategy Socket — contract every strategy file must follow

The engine is fixed. A strategy is a plug-in `.py` file in `strategies/`.
Switch strategy = change one line in `config.yaml` (`strategy.file: strategies/<file>.py`).
The same file must run in **live/paper** (engine) and **dry run** (and later in backtest).

## 1. Required module-level metadata

```python
NAME          = "pdh_breakout"   # unique id, used as OpenAlgo strategy tag
TIMEFRAME     = "5m"             # bar size the engine feeds to on_bar
LOOKBACK_BARS = 50               # bars of history the engine warms up per symbol
SIDES         = ("LONG", "SHORT")  # which directions this strategy can signal
PARAMS        = {                # tunable, overridable from config.yaml
    "vwap_filter": True,
    "buffer_pct": 0.001,
    "vol_mult": 1.5,
    "vol_baseline_sessions": 5,
    "rvol_min": 1.0,
    "max_chase_atr": 0.5,
    "stop_bar_buffer_pct": 0.0005,
    "min_stop_pct": 0.006,
    "max_stop_pct": 0.015,
    "target_r": 2.0,
    "breakeven_at_r": 1.0,
}
```

## 2. Required class

```python
class Strategy:
    def __init__(self, params: dict): ...

    def on_bar(self, symbol: str, bars: "pd.DataFrame", ctx: "Context") -> "Signal | None":
        """Called on a CLOSED bar only for ARMED symbols (spec §6), not the whole shortlist.
        bars: 5m OHLCV for the last 5 sessions including today; last row = just-closed bar.
        Return a Signal or None."""

    def on_exit_check(self, position: "OpenPosition", bars, ctx) -> "Exit | None":
        """OPTIONAL. Custom exit (e.g. close below VWAP). Engine already enforces SL/target/time."""
```

## 3. Context (read-only, provided by engine)

| field | meaning |
|---|---|
| `ctx.now` | current IST datetime (bar close boundary) |
| `ctx.regime` | `"TREND_UP"`, `"TREND_DOWN"`, `"CHOPPY"` (NIFTY-based, 2-bar confirmed) |
| `ctx.sector` | stock's sector name, e.g. `"Metal"` |
| `ctx.sector_rank` | 1 = strongest vs NIFTY today |
| `ctx.sector_bias` | `-2..+2` (price RS; + AI bias in v2) |
| `ctx.pdh`, `ctx.pdl`, `ctx.pdc` | previous day high / low / close |
| `ctx.vwap` | stock's session VWAP from today's 5m bars |
| `ctx.atr` | daily ATR(14) |
| `ctx.day_open`, `ctx.day_high`, `ctx.day_low` | today's intraday levels |
| `ctx.slot_volume_avg` | average volume of the same 5m time slot over the last 5 sessions |
| `ctx.rvol` | today's cumulative volume ÷ 5-session average cumulative volume at this time |
| `ctx.ltp` | latest price from WebSocket |
| `ctx.traded_today` | True if symbol was already signaled/traded today |
| `ctx.has_position(symbol)` | True if engine already holds it |

## 4. Output types

```python
Signal(side="LONG"|"SHORT", entry="MARKET"|"LIMIT", limit_price=None,
       stop_loss=<price>, target=<price or None>, reason="<text for log>")
Exit(reason="<text>")
```

## 5. Hard rules (engine enforces; strategy must not try)

1. Strategy **never** calls OpenAlgo order APIs. It only returns Signal/Exit.
2. Strategy **never** decides quantity. Engine sizes: `qty = risk_per_trade / |entry - stop_loss|`.
3. `stop_loss` is mandatory. Signal without it is rejected.
4. No network calls, no file writes, no sleeping inside `on_bar` (must return fast).
5. No state outside `self`. Engine may restart; strategy must tolerate it.
6. Engine drops signals when: regime = CHOPPY, risk caps hit, outside entry window (`09:30`–`14:15`),
   symbol already held, side conflicts with sector bias (LONG in weak sector / SHORT in strong),
   notional cap leaves risk under the minimum (`₹300`), stale data, Analyze mode off, or free RAM too low (`< 100 MB`).

## 6. Engine responsibilities (not strategy)

Data feed (WebSocket + 5m history for armed symbols) · regime · sector ranking · top-5 shortlist scanner & arming ·
position sizing · risk caps · order placement (Analyzer/Live per OpenAlgo mode) ·
SL/target monitoring · `14:55` square-off · logging.
