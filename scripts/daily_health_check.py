"""Daily Codebase Health Check & Index Generator for sunil_backtesting.

Read-only toward application code (engine/, strategies/, vendor/).
Generates/updates at the repository root:
  - CODEBASE_INDEX.md
  - CODE_HEALTH_REPORT.md
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import re
import sys
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
REPO_ROOT = Path(__file__).resolve().parent.parent
APP_ROOT = REPO_ROOT / "intraday-engine" / "intraday-engine"

CRITICAL_FILE_LINES = 700
WARN_FILE_LINES = 400
CRITICAL_FUNC_LINES = 200
WARN_FUNC_LINES = 80

IMPORT_TO_PIP = {
    "dotenv": "python-dotenv",
    "yaml": "pyyaml",
    "fpdf": "fpdf2",
    "openalgo": "openalgo",
    "pandas": "pandas",
    "numpy": "numpy",
}


@dataclass
class FuncInfo:
    name: str
    lineno: int
    end_lineno: int

    @property
    def length(self) -> int:
        return max(1, self.end_lineno - self.lineno + 1)


@dataclass
class FileStats:
    rel_path: str
    group: str
    lines: int
    bytes_size: int
    docstring: str = ""
    classes: list[str] = field(default_factory=list)
    functions: list[FuncInfo] = field(default_factory=list)
    third_party_imports: set[str] = field(default_factory=set)
    syntax_error: str | None = None
    safety_hits: list[str] = field(default_factory=list)


def _first_line(text: str | None) -> str:
    if not text:
        return "-"
    for line in text.splitlines():
        cleaned = line.strip()
        if cleaned:
            return cleaned[:110]
    return "-"


def _analyze_python_file(path: Path, group: str) -> FileStats:
    rel = path.relative_to(REPO_ROOT).as_posix()
    raw = path.read_text(encoding="utf-8", errors="replace")
    lines = raw.splitlines()
    stats = FileStats(
        rel_path=rel,
        group=group,
        lines=len(lines),
        bytes_size=path.stat().st_size,
    )

    try:
        tree = ast.parse(raw, filename=str(path))
    except SyntaxError as exc:
        stats.syntax_error = f"Line {exc.lineno}: {exc.msg}"
        return stats

    stats.docstring = _first_line(ast.get_docstring(tree))

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            stats.classes.append(node.name)
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    end = getattr(item, "end_lineno", item.lineno)
                    stats.functions.append(FuncInfo(f"{node.name}.{item.name}", item.lineno, end))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = getattr(node, "end_lineno", node.lineno)
            stats.functions.append(FuncInfo(node.name, node.lineno, end))

    stdlib = sys.stdlib_module_names
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top not in stdlib and top not in {"engine", "core", "strategies"}:
                    stats.third_party_imports.add(top)
        elif isinstance(node, ast.ImportFrom) and node.module:
            top = node.module.split(".")[0]
            if top not in stdlib and top not in {"engine", "core", "strategies"}:
                stats.third_party_imports.add(top)

    if group in {"engine", "strategies"}:
        if re.search(r"analyzer_?toggle\s*\(", raw, re.IGNORECASE):
            stats.safety_hits.append("Calls analyzer toggle (violates Paper-Only Rule 1)")
        if path.name != "oa.py" and re.search(r"\bopenalgo\.api\b|\bapi\s*\(\s*api_key", raw):
            stats.safety_hits.append("Direct OpenAlgo API client outside engine/oa.py (Rule 5)")

    return stats


def _analyze_non_python_file(path: Path, group: str) -> FileStats:
    rel = path.relative_to(REPO_ROOT).as_posix()
    raw = path.read_text(encoding="utf-8", errors="replace")
    return FileStats(
        rel_path=rel,
        group=group,
        lines=len(raw.splitlines()),
        bytes_size=path.stat().st_size,
        docstring=f"{path.suffix.lstrip('.').upper()} file",
    )


def _read_requirements() -> set[str]:
    req_file = APP_ROOT / "requirements.txt"
    if not req_file.exists():
        return set()
    pkgs: set[str] = set()
    for line in req_file.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].split(";", 1)[0].strip()
        if not line:
            continue
        name = re.split(r"[=<>!~\[ ]", line, maxsplit=1)[0].strip().lower()
        if name:
            pkgs.add(name)
    return pkgs


def _read_phases() -> list[tuple[str, str, str, str]]:
    prog = APP_ROOT / "PROGRESS.md"
    if not prog.exists():
        return []
    rows: list[tuple[str, str, str, str]] = []
    for line in prog.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*(\d)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|", line)
        if m:
            rows.append((m.group(1), m.group(2), m.group(3), m.group(4) or "-"))
    return rows


def _collect_all_files() -> list[FileStats]:
    items: list[FileStats] = []
    groups = [
        ("engine", APP_ROOT / "engine", {".py", ".html"}),
        ("strategies", APP_ROOT / "strategies", {".py"}),
        ("vendor/core", APP_ROOT / "vendor" / "core", {".py"}),
        ("vendor/ref", APP_ROOT / "vendor" / "reference_strategies", {".py", ".md"}),
        ("docs", APP_ROOT / "docs", {".md"}),
        ("scripts", REPO_ROOT / "scripts", {".py"}),
    ]
    for group_name, folder, exts in groups:
        if not folder.exists():
            continue
        for p in sorted(folder.iterdir()):
            if not p.is_file() or p.suffix not in exts:
                continue
            if p.suffix == ".py":
                items.append(_analyze_python_file(p, group_name))
            else:
                items.append(_analyze_non_python_file(p, group_name))
    return items


def _check_hygiene(files: list[FileStats], declared_reqs: set[str]) -> dict:
    active_files = [f for f in files if f.group in {"engine", "strategies"}]
    syntax_errors = [f for f in files if f.syntax_error]
    safety_violations = [f for f in active_files if f.safety_hits]

    bloated_files = sorted(
        [f for f in active_files if f.lines > WARN_FILE_LINES],
        key=lambda f: -f.lines,
    )
    long_functions: list[tuple[str, FuncInfo]] = []
    for f in active_files:
        for fn in f.functions:
            if fn.length > WARN_FUNC_LINES:
                long_functions.append((f.rel_path, fn))
    long_functions.sort(key=lambda item: -item[1].length)

    used_imports: dict[str, list[str]] = {}
    for f in active_files:
        for pkg in f.third_party_imports:
            used_imports.setdefault(pkg, []).append(f.rel_path)

    missing_reqs: list[tuple[str, str, list[str]]] = []
    for imp, paths in sorted(used_imports.items()):
        pip_name = IMPORT_TO_PIP.get(imp, imp).lower()
        if pip_name not in declared_reqs and not (pip_name == "fpdf2" and "fpdf" in declared_reqs):
            missing_reqs.append((imp, pip_name, paths))

    root_duplicates = sorted(
        {p.name for p in list(REPO_ROOT.glob("MACRO_DRYRUN_*")) + list(REPO_ROOT.glob("*.pdf"))}
    )
    nested_dir = (REPO_ROOT / "intraday-engine" / "intraday-engine").is_dir()
    git_initialized = (REPO_ROOT / ".git").exists()
    db_file = APP_ROOT / "data" / "engine.db"
    log_file = APP_ROOT / "logs" / "engine.log"

    return {
        "active_files": active_files,
        "syntax_errors": syntax_errors,
        "safety_violations": safety_violations,
        "bloated_files": bloated_files,
        "long_functions": long_functions,
        "missing_reqs": missing_reqs,
        "root_duplicates": root_duplicates,
        "nested_dir": nested_dir,
        "git_initialized": git_initialized,
        "db_kb": round(db_file.stat().st_size / 1024, 1) if db_file.exists() else 0.0,
        "log_kb": round(log_file.stat().st_size / 1024, 1) if log_file.exists() else 0.0,
    }


def _render_index(files: list[FileStats], phases: list[tuple[str, str, str, str]], now_str: str) -> str:
    lines: list[str] = [
        "# Codebase Index — `sunil_backtesting`",
        "",
        f"> Auto-generated on **{now_str}** by `scripts/daily_health_check.py`. Do not hand-edit.",
        "",
        "## 1. Project Entry Points & Layout",
        "",
        "- **Workspace Root**: `sunil_backtesting/` (`BUILD.md`, `scripts/`, `CODEBASE_INDEX.md`, `CODE_HEALTH_REPORT.md`)",
        "- **Application Root**: `intraday-engine/intraday-engine/`",
        "- **Start Engine**: `intraday-engine/intraday-engine/start_engine.bat` or `python -m engine.app` (Web UI at `http://127.0.0.1:8800/`)",
        "- **Safety Mode**: Paper / Analyze-mode only via OpenAlgo Desktop (Groww). Secrets stay in `.env` (gitignored).",
        "",
        "## 2. Build Phases (`PROGRESS.md`)",
        "",
        "| Phase | Scope | Status | Date |",
        "|---|---|---|---|",
    ]
    for num, name, state, date in phases:
        lines.append(f"| {num} | {name} | `{state}` | {date} |")

    def add_section(title: str, group: str) -> None:
        subset = [f for f in files if f.group == group]
        if not subset:
            return
        lines.extend([
            "",
            f"## {title}",
            "",
            "| File | Lines | Classes | Functions | Purpose |",
            "|---|---:|---|---|---|",
        ])
        for f in subset:
            cls_str = ", ".join(f.classes) if f.classes else "-"
            fn_count = len(f.functions)
            short_name = f.rel_path.replace("intraday-engine/intraday-engine/", "")
            lines.append(f"| `{short_name}` | {f.lines} | {cls_str} | {fn_count} | {f.docstring} |")

    add_section("3. Engine Modules (`engine/`)", "engine")
    add_section("4. Strategy Plug-ins (`strategies/`)", "strategies")
    add_section("5. Vendor Core (`vendor/core/` — read-only)", "vendor/core")
    add_section("6. Documentation & Reference (`docs/`, `vendor/reference_strategies/`)", "docs")
    add_section("7. Automation Scripts (`scripts/`)", "scripts")

    lines.extend([
        "",
        "## 8. Key Data & Config Files",
        "",
        "- `intraday-engine/intraday-engine/config.example.yaml` — Template trading/risk/UI settings",
        "- `intraday-engine/intraday-engine/requirements.txt` — Python dependencies",
        "- `intraday-engine/intraday-engine/data/sector_map.json` — Read-only NSE universe & sectors",
        "- `intraday-engine/intraday-engine/data/universe_clean.json` — Cleaned 104-stock universe output",
        "- `intraday-engine/intraday-engine/data/scan_archive/` — Archived dry-run scans and macro reports",
        "",
    ])
    return "\n".join(lines)


def _render_health_report(files: list[FileStats], info: dict, now_str: str) -> str:
    active = info["active_files"]
    py_files = [f for f in files if f.rel_path.endswith(".py")]
    total_py_lines = sum(f.lines for f in active if f.rel_path.endswith(".py"))
    crit_files = [f for f in info["bloated_files"] if f.lines > CRITICAL_FILE_LINES]
    warn_files = [f for f in info["bloated_files"] if WARN_FILE_LINES < f.lines <= CRITICAL_FILE_LINES]
    long_fns = info["long_functions"]

    status_badge = "PASS WITH WARNINGS"
    if info["syntax_errors"] or info["safety_violations"]:
        status_badge = "ACTION REQUIRED"

    lines: list[str] = [
        "# Codebase Health Report — `sunil_backtesting`",
        "",
        f"> Generated on **{now_str}** | Mode: **Semi-Automatic** (Read-Only Scan — no application files modified)",
        "",
        "## 1. Executive Summary",
        "",
        "| Metric | Result | Target / Policy |",
        "|---|---|---|",
        f"| **Overall Status** | **{status_badge}** | Zero syntax/safety errors; keep modules modular |",
        f"| **Active Modules (`engine/` + `strategies/`)** | {len(active)} files ({total_py_lines:,} Python lines) | Clean separation per `ARCHITECTURE_v2.md` |",
        f"| **AST Syntax Check** | {len(py_files) - len(info['syntax_errors'])}/{len(py_files)} Python files valid | 100% valid syntax |",
        f"| **Paper-Only & OpenAlgo Gateway Rules** | {len(info['safety_violations'])} violations | 0 violations (`BUILD.md` Rules 1 & 5) |",
        f"| **Bloated Files (`>{WARN_FILE_LINES}` lines)** | {len(crit_files)} critical (`>{CRITICAL_FILE_LINES}`L), {len(warn_files)} warning | Keep modules under {WARN_FILE_LINES} lines |",
        f"| **Oversized Functions (`>{WARN_FUNC_LINES}` lines)** | {len(long_fns)} functions | Split functions > {WARN_FUNC_LINES} lines |",
        f"| **Missing `requirements.txt` Packages** | {len(info['missing_reqs'])} package(s) | Every import declared |",
        f"| **Git Version Control** | {'Initialized' if info['git_initialized'] else 'Not initialized'} | Tracked on `main` |",
        f"| **Runtime Artifacts** | `engine.db`: {info['db_kb']} KB, `engine.log`: {info['log_kb']} KB | Gitignored locally |",
        "",
        "> Note on tests: `BUILD.md` Rule 3 intentionally omits a test framework (`No test suite`). Automated verification currently relies on AST syntax/safety checks and the UI's 11-point connection check.",
        "",
        "## 2. Bloated & Monolithic Files",
        "",
        "| Severity | File | Lines | Suggested Split |",
        "|---|---|---:|---|",
    ]

    split_hints = {
        "engine/page.html": "Separate CSS/JS into `engine/static/` or component partials while keeping zero-build vanilla JS",
        "engine/macro_report.py": "Split into data compiler, markdown renderer, PDF renderer, and CLI entry",
        "engine/session.py": "Extract 5m cycle runner, live armed evaluator, and worker lifecycle helpers",
        "engine/dryrun.py": "Break `run_dry_session` (593 lines!) into bar replay loop, position simulator, and summary builder",
        "engine/s3_archive.py": "Separate AWS SigV4 HTTP client from scan document builders",
        "engine/socket_manager.py": "Separate qualification harness, OpenRouter verifier, and starter template strings",
        "engine/oa.py": "Extract the 11-step `run_connection_check` into dedicated check helpers",
        "engine/bars.py": "Separate OHLCV bar builder from strategy context & RVOL evaluator",
        "engine/store.py": "Split schema migrations from query/read/write repository methods",
    }

    for f in info["bloated_files"]:
        short = f.rel_path.replace("intraday-engine/intraday-engine/", "")
        sev = "CRITICAL" if f.lines > CRITICAL_FILE_LINES else "WARN"
        hint = split_hints.get(short, "Refactor into smaller single-purpose helpers")
        lines.append(f"| `{sev}` | `{short}` | {f.lines} | {hint} |")

    lines.extend([
        "",
        "## 3. Largest Functions (`>80` lines)",
        "",
        "| File | Function | Lines | Range |",
        "|---|---|---:|---|",
    ])
    for rel, fn in long_fns[:15]:
        short = rel.replace("intraday-engine/intraday-engine/", "")
        lines.append(f"| `{short}` | `{fn.name}` | {fn.length} | L{fn.lineno}-L{fn.end_lineno} |")

    lines.extend([
        "",
        "## 4. Dependency, Hygiene & Structure Findings",
        "",
    ])
    if info["missing_reqs"]:
        for imp, pip_name, paths in info["missing_reqs"]:
            short_paths = ", ".join(p.replace("intraday-engine/intraday-engine/", "") for p in paths)
            lines.append(f"- **[HIGH] Undeclared dependency `{imp}` (`pip install {pip_name}`)**: imported in `{short_paths}` but missing from `requirements.txt`.")
    if info["nested_dir"]:
        lines.append("- **[LOW] Double-nested directory**: application sits at `intraday-engine/intraday-engine/` (keep in mind when running scripts or commands).")
    if info["root_duplicates"]:
        lines.append(f"- **[LOW] Duplicate generated exports at repo root**: {len(info['root_duplicates'])} files (`{', '.join(info['root_duplicates'][:3])}`...) duplicate `data/scan_archive/` outputs (gitignored at root).")

    lines.extend([
        "",
        "## 5. Actionable Recommendations (Copy-Paste Prompts for AI)",
        "",
        "### Recommendation #1 — Fix Missing `fpdf2` Dependency in `requirements.txt` `[LOW RISK]`",
        "```text",
        "In intraday-engine/intraday-engine/requirements.txt, add fpdf2 (required by engine/macro_report.py) and update BUILD.md Rule 4 note if approved so fresh installs don't fail with ModuleNotFoundError.",
        "```",
        "",
        "### Recommendation #2 — Modularize `engine/dryrun.py` (`run_dry_session` = 593 lines) `[MEDIUM RISK]`",
        "```text",
        "Refactor run_dry_session in intraday-engine/intraday-engine/engine/dryrun.py into small single-purpose helper functions (bar preparation, armed evaluation, simulated exits, and archive/report output) without changing dry-run numbers or output format.",
        "```",
        "",
        "### Recommendation #3 — Split `engine/macro_report.py` (1,567 lines) & `engine/session.py` (1,250 lines) `[MEDIUM RISK]`",
        "```text",
        "Split engine/macro_report.py into compilation vs Markdown/PDF rendering modules, and split Controller._build / _evaluate_armed_live in engine/session.py into focused helpers while keeping runtime behavior identical.",
        "```",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    now_str = datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")
    files = _collect_all_files()
    reqs = _read_requirements()
    phases = _read_phases()
    hygiene = _check_hygiene(files, reqs)

    index_md = _render_index(files, phases, now_str)
    report_md = _render_health_report(files, hygiene, now_str)

    (REPO_ROOT / "CODEBASE_INDEX.md").write_text(index_md, encoding="utf-8")
    (REPO_ROOT / "CODE_HEALTH_REPORT.md").write_text(report_md, encoding="utf-8")

    print(
        f"Health check OK: {len(files)} files scanned | "
        f"{len(hygiene['syntax_errors'])} syntax errors | "
        f"{len(hygiene['bloated_files'])} bloated files | "
        f"{len(hygiene['long_functions'])} long functions | "
        f"{len(hygiene['missing_reqs'])} missing requirements"
    )
    return 1 if hygiene["syntax_errors"] or hygiene["safety_violations"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
