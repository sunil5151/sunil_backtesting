"""Process entry and control layer. Run from the project folder:  python -m engine.app

One process: UI server (this thread), heartbeat thread, control thread. See docs/ARCHITECTURE_v2.md.
"""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import re
import socket
import sys
import webbrowser

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "vendor"))        # vendor files import each other as core.*

from engine.config import ConfigError, load_config, universe_symbols   # noqa: E402

PHASE_NAMES = {1: "Shell, UI and the OpenAlgo link", 2: "Market view", 3: "Signals and dry run",
               4: "Paper trading", 5: "Report, LLM and shadow comparison"}


def read_phases():
    """Phase states come from the phase table in PROGRESS.md, so the UI strip and the file agree."""
    found = {}
    try:
        for line in (ROOT / "PROGRESS.md").read_text(encoding="utf-8").splitlines():
            m = re.match(r"\|\s*(\d)\s*\|[^|]*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|", line)
            if m:
                found[int(m.group(1))] = (m.group(2).lower(), m.group(3))
    except OSError:
        pass
    return [{"n": n, "name": name, "state": found.get(n, ("not started", ""))[0],
             "date": found.get(n, ("", ""))[1]} for n, name in PHASE_NAMES.items()]


def setup_logging():
    (ROOT / "logs").mkdir(exist_ok=True)
    handler = RotatingFileHandler(ROOT / "logs" / "engine.log", maxBytes=1_000_000, backupCount=3,
                                  encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    for noisy in ("httpx", "httpcore", "websocket"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    return logging.getLogger("engine")


def port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", port)) == 0


def main():
    log = setup_logging()
    try:
        cfg = load_config()
    except ConfigError as e:
        print(f"\nConfig problem: {e}\n")
        return 1

    url = f"http://127.0.0.1:{cfg.ui_port}/"
    if port_in_use(cfg.ui_port):
        print(f"The engine is already running. Opening {url}")
        webbrowser.open(url)
        return 0

    # Imported here, after vendor/ is on the path and the config is known to be good.
    from engine.oa import OALink
    from engine.session import Controller
    from engine.store import Store
    from engine.ui import make_server

    store = Store(cfg.db_file, cfg.keep_activity_days)
    link = OALink(cfg, logging.getLogger("engine.oa"))
    controller = Controller(cfg, store, link, universe_symbols(cfg), read_phases(), log)
    server = make_server(cfg, controller, log)

    store.add_activity("Engine started. Paper only.", "info")
    for note in cfg.notes:
        store.add_activity(note, "warn")
    controller.start_threads()

    print(f"intraday-engine is running. Page: {url}")
    if cfg.lan_access:
        print(f"From the phone on the same Wi-Fi: http://<this laptop's IP>:{cfg.ui_port}/  (access code needed)")
    print("Keep this window open. Close it (or press Ctrl+C) to stop the engine.")
    log.info("engine started, ui on port %s", cfg.ui_port)
    if cfg.open_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        controller.shutdown()
        store.add_activity("Engine closed.", "info")
        server.server_close()
        link.close()
        store.close()
        log.info("engine stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
