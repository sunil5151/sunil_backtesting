"""Load and validate config.yaml and .env. Nothing else reads these files."""
from dataclasses import dataclass, field
from datetime import time as dtime
import json
import os
from pathlib import Path
import shutil

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
PLACEHOLDER_KEY = "paste_your_key_here"


class ConfigError(Exception):
    """config.yaml is missing something or has a bad value. The message says what to fix."""


@dataclass
class Config:
    root: Path
    api_key: str            # never print or log this
    host: str
    ws_url: str
    strategy_name: str
    strategy_file: str
    strategy_params: dict
    dryrun_enabled: bool
    universe_file: Path
    clean_universe_file: Path
    exchange: str
    index_symbol: str
    index_exchange: str
    drop_sectors: list
    symbol_aliases: dict
    capital: float
    market_open: dtime
    no_entry_before: dtime
    no_new_entries_after: dtime
    square_off: dtime
    market_close: dtime
    auto_start_time: str
    rescan_minutes: int
    bars_per_day: int
    # prefilter
    min_price: float
    max_price: float
    min_traded_value_cr: float
    min_atr_pct: float
    fno_only: bool
    min_members_per_sector: int
    atr_period: int
    avg_days: int
    # regime
    adx_period: int
    adx_below: float
    crosses_min: int
    crosses_lookback: int
    breadth_low: float
    breadth_high: float
    confirm_bars: int
    warmup_days: int
    # sector
    rs_threshold_pct: float
    sector_top_n: int
    # scanner
    proximity_max_atr: float
    shortlist_size: int
    arm_buffer_pct: float
    # feed
    stale_seconds: float
    poll_interval_seconds: float
    timeout_seconds: float
    max_calls_per_second: float
    heartbeat_seconds: float
    retry_when_down_seconds: float
    check_stock: str
    funds_tolerance_pct: float
    stream_wait_seconds: float
    warn_free_mb: int
    block_free_mb: int
    engine_target_mb: int
    ui_port: int
    open_browser: bool
    lan_access: bool
    access_code: str
    db_file: Path
    keep_activity_days: int
    # risk & paper trading (Phase 4)
    product: str = "MIS"
    risk_per_trade_rs: float = 500.0
    leverage: float = 5.0
    min_achievable_risk_rs: float = 300.0
    max_open_positions: int = 3
    max_positions_per_sector: int = 2
    max_trades_per_day: int = 6
    daily_loss_limit_rs: float = 1500.0
    gst_rate: float = 0.18
    reconcile_interval_seconds: float = 30.0
    square_off_confirm_time: dtime = dtime(15, 0)
    s3_bucket: str = ""
    s3_region: str = "ap-south-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    openrouter_api_key: str = ""
    openrouter_model: str = "GLM 5.3 Flash"
    notes: list = field(default_factory=list)   # first-run messages for the activity feed

    @property
    def has_key(self) -> bool:
        return bool(self.api_key) and self.api_key != PLACEHOLDER_KEY

    @property
    def has_s3(self) -> bool:
        return bool(self.s3_bucket and self.s3_region and self.aws_access_key_id and self.aws_secret_access_key)

    @property
    def has_openrouter(self) -> bool:
        return bool(self.openrouter_api_key) and not self.openrouter_api_key.startswith("paste_")


def parse_hhmm(value, name="time") -> dtime:
    try:
        hh, mm = str(value).strip().split(":")
        return dtime(int(hh), int(mm))
    except Exception:
        raise ConfigError(f'{name} must look like "09:15", got "{value}".')


def _get(cfg: dict, path: str):
    node = cfg
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            raise ConfigError(f"config.yaml is missing '{path}'. Copy it from config.example.yaml.")
        node = node[part]
    return node


def load_config() -> Config:
    notes = []
    cfg_path = ROOT / "config.yaml"
    env_path = ROOT / ".env"
    if not cfg_path.exists():
        shutil.copyfile(ROOT / "config.example.yaml", cfg_path)
        notes.append("config.yaml was missing, so it was created from config.example.yaml.")
    if not env_path.exists():
        shutil.copyfile(ROOT / ".env.example", env_path)
        notes.append("The .env file was missing, so it was created. Paste your OpenAlgo API key into it.")

    for extra_env in (ROOT.parent.parent / ".env", ROOT.parent / ".env"):
        if extra_env.exists():
            load_dotenv(extra_env, override=True, encoding="utf-8-sig")
    load_dotenv(env_path, override=True, encoding="utf-8-sig")
    try:
        raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8-sig")) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"config.yaml cannot be read: {e}")

    g = lambda p: _get(raw, p)
    cfg = Config(
        root=ROOT,
        api_key=os.getenv("OPENALGO_API_KEY", "").strip(),
        host=os.getenv("OPENALGO_HOST", "http://127.0.0.1:5000").strip().rstrip("/"),
        ws_url=os.getenv("WEBSOCKET_URL", "ws://127.0.0.1:8765").strip(),
        strategy_name=str(g("strategy.name")),
        strategy_file=str(g("strategy.file")),
        strategy_params=dict(g("strategy.params") or {}),
        dryrun_enabled=bool(g("dryrun.enabled")),
        universe_file=ROOT / str(g("universe.file")),
        clean_universe_file=ROOT / str(g("universe.clean_file")),
        exchange=str(g("universe.exchange")),
        index_symbol=str(g("universe.index_symbol")),
        index_exchange=str(g("universe.index_exchange")),
        drop_sectors=[str(s) for s in (g("universe.drop_sectors") or [])],
        symbol_aliases={str(k): str(v) for k, v in (g("universe.symbol_aliases") or {}).items()},
        capital=float(g("capital")),
        market_open=parse_hhmm(g("session.market_open"), "session.market_open"),
        no_entry_before=parse_hhmm(g("session.no_entry_before"), "session.no_entry_before"),
        no_new_entries_after=parse_hhmm(g("session.no_new_entries_after"), "session.no_new_entries_after"),
        square_off=parse_hhmm(g("session.square_off"), "session.square_off"),
        market_close=parse_hhmm(g("session.market_close"), "session.market_close"),
        auto_start_time=str(g("session.auto_start_time")),
        rescan_minutes=int(g("session.rescan_minutes")),
        bars_per_day=int(g("session.bars_per_day")),
        min_price=float(g("prefilter.min_price")),
        max_price=float(g("prefilter.max_price")),
        min_traded_value_cr=float(g("prefilter.min_traded_value_cr")),
        min_atr_pct=float(g("prefilter.min_atr_pct")),
        fno_only=bool(g("prefilter.fno_only")),
        min_members_per_sector=int(g("prefilter.min_members_per_sector")),
        atr_period=int(g("prefilter.atr_period")),
        avg_days=int(g("prefilter.avg_days")),
        adx_period=int(g("regime.adx_period")),
        adx_below=float(g("regime.adx_below")),
        crosses_min=int(g("regime.crosses_min")),
        crosses_lookback=int(g("regime.crosses_lookback")),
        breadth_low=float(g("regime.breadth_low")),
        breadth_high=float(g("regime.breadth_high")),
        confirm_bars=int(g("regime.confirm_bars")),
        warmup_days=int(g("regime.warmup_days")),
        rs_threshold_pct=float(g("sector.rs_threshold_pct")),
        sector_top_n=int(g("sector.top_n")),
        proximity_max_atr=float(g("scanner.proximity_max_atr")),
        shortlist_size=int(g("scanner.shortlist_size")),
        arm_buffer_pct=float(g("scanner.arm_buffer_pct")),
        stale_seconds=float(g("feed.stale_seconds")),
        poll_interval_seconds=float(g("feed.poll_interval_seconds")),
        timeout_seconds=float(g("openalgo.timeout_seconds")),
        max_calls_per_second=float(g("openalgo.max_calls_per_second")),
        heartbeat_seconds=float(g("openalgo.heartbeat_seconds")),
        retry_when_down_seconds=float(g("openalgo.retry_when_down_seconds")),
        check_stock=str(g("check.stock_symbol")),
        funds_tolerance_pct=float(g("check.funds_tolerance_pct")),
        stream_wait_seconds=float(g("check.stream_wait_seconds")),
        warn_free_mb=int(g("memory.warn_free_mb")),
        block_free_mb=int(g("memory.block_free_mb")),
        engine_target_mb=int(g("memory.engine_target_mb")),
        ui_port=int(g("ui.port")),
        open_browser=bool(g("ui.open_browser")),
        lan_access=bool(g("ui.lan_access")),
        access_code=str(g("ui.access_code") or ""),
        db_file=ROOT / str(g("store.db_file")),
        keep_activity_days=int(g("store.keep_activity_days")),
        product=str((raw.get("risk") or {}).get("product", "MIS")).upper(),
        risk_per_trade_rs=float((raw.get("risk") or {}).get("risk_per_trade_rs", 500.0)),
        leverage=float((raw.get("risk") or {}).get("leverage", 5.0)),
        min_achievable_risk_rs=float((raw.get("risk") or {}).get("min_achievable_risk_rs", 300.0)),
        max_open_positions=int((raw.get("risk") or {}).get("max_open_positions", 3)),
        max_positions_per_sector=int((raw.get("risk") or {}).get("max_positions_per_sector", 2)),
        max_trades_per_day=int((raw.get("risk") or {}).get("max_trades_per_day", 6)),
        daily_loss_limit_rs=float((raw.get("risk") or {}).get("daily_loss_limit_rs", 1500.0)),
        gst_rate=float((raw.get("risk") or {}).get("gst_rate", 0.18)),
        reconcile_interval_seconds=float((raw.get("risk") or {}).get("reconcile_interval_seconds", 30.0)),
        square_off_confirm_time=parse_hhmm((raw.get("risk") or {}).get("square_off_confirm_time", "15:00"), "risk.square_off_confirm_time"),
        s3_bucket=(os.getenv("S3_BUCKET_NAME") or os.getenv("AWS_S3_BUCKET") or "").strip(),
        s3_region=(os.getenv("S3_REGION") or os.getenv("AWS_REGION") or "ap-south-1").strip(),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "").strip(),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "").strip(),
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", "").strip(),
        openrouter_model=(os.getenv("OPENROUTER_MODEL", "GLM 5.3 Flash").strip() or "GLM 5.3 Flash"),
        notes=notes,
    )

    parse_hhmm(cfg.auto_start_time, "session.auto_start_time")
    if not (cfg.market_open < cfg.no_entry_before < cfg.no_new_entries_after < cfg.square_off <= cfg.market_close):
        raise ConfigError("session times must be in order: market_open, no_entry_before, "
                          "no_new_entries_after, square_off, market_close.")
    if cfg.capital <= 0:
        raise ConfigError("capital must be above zero.")
    if cfg.max_calls_per_second <= 0:
        raise ConfigError("openalgo.max_calls_per_second must be above zero.")
    if not cfg.universe_file.exists():
        raise ConfigError(f"Universe file not found: {cfg.universe_file}")
    if cfg.strategy_file and cfg.strategy_file.strip().lower() not in ("none", "unplugged"):
        if not (ROOT / cfg.strategy_file).exists():
            raise ConfigError(f"Strategy file not found: {ROOT / cfg.strategy_file}")
    if cfg.lan_access and not cfg.access_code:
        cfg.lan_access = False
        notes.append("ui.lan_access is on but ui.access_code is empty, so the page stays on this laptop only. "
                     "Set an access code in config.yaml to open it from the phone.")
    return cfg


def save_strategy_config(cfg: Config, strategy_name: str, strategy_file: str, strategy_params: dict | None = None):
    """Persist active strategy.name, strategy.file (and optional params) to config.yaml and cfg."""
    cfg_path = cfg.root / "config.yaml"
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8-sig")) or {}
    strat = raw.setdefault("strategy", {})
    strat["name"] = str(strategy_name or "")
    strat["file"] = str(strategy_file or "")
    if strategy_params is not None:
        strat["params"] = dict(strategy_params)
        cfg.strategy_params = dict(strategy_params)
    cfg_path.write_text(yaml.safe_dump(raw, sort_keys=False, allow_unicode=True), encoding="utf-8")
    cfg.strategy_name = str(strategy_name or "")
    cfg.strategy_file = str(strategy_file or "")


def save_openrouter_env(cfg: Config, api_key: str | None = None, model: str | None = None):
    """Update OPENROUTER_API_KEY / OPENROUTER_MODEL in .env and refresh cfg in memory."""
    env_path = cfg.root / ".env"
    lines = env_path.read_text(encoding="utf-8-sig").splitlines() if env_path.exists() else []
    updates = {}
    if api_key is not None:
        updates["OPENROUTER_API_KEY"] = api_key.strip()
        cfg.openrouter_api_key = api_key.strip()
    if model is not None:
        mval = model.strip() or "GLM 5.3 Flash"
        updates["OPENROUTER_MODEL"] = mval
        cfg.openrouter_model = mval
    seen = set()
    out_lines = []
    for line in lines:
        k, sep, _ = line.partition("=")
        k_clean = k.strip()
        if sep and k_clean in updates:
            out_lines.append(f"{k_clean}={updates[k_clean]}")
            seen.add(k_clean)
        else:
            out_lines.append(line)
    for k, v in updates.items():
        if k not in seen:
            out_lines.append(f"{k}={v}")
    env_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")


def reload_api_key(cfg: Config) -> bool:
    """Read the key from .env again. True if it changed (so a pasted key works without a restart)."""
    load_dotenv(cfg.root / ".env", override=True, encoding="utf-8-sig")
    key = os.getenv("OPENALGO_API_KEY", "").strip()
    if key == cfg.api_key:
        return False
    cfg.api_key = key
    return True


def universe_symbols(cfg: Config) -> list:
    """Unique stock symbols in the universe file (after drop_sectors and symbol_aliases), in file order."""
    data = json.loads(cfg.universe_file.read_text(encoding="utf-8"))
    drop = set(cfg.drop_sectors)
    aliases = cfg.symbol_aliases
    seen = {}
    for skey, sector in data.items():
        if skey in drop:
            continue
        for h in sector.get("holdings", []):
            orig = h["symbol"]
            sym = aliases.get(orig, orig)
            seen.setdefault(sym, None)
    return list(seen)
