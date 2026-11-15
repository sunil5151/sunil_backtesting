"""UI server: one page, one state endpoint, four actions. Standard library only.

This thread never computes anything: /api/state returns the snapshot the control layer
already built. Localhost only, unless ui.lan_access is on, and then an access code is needed
because the page has START and STOP.
"""
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import socket
from urllib.parse import parse_qs, urlparse

PAGE = Path(__file__).with_name("page.html")
MAX_BODY = 131072

CODE_FORM = (b"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
             b"<title>intraday-engine</title><body style='font-family:sans-serif;margin:40px auto;max-width:320px'>"
             b"<h3>intraday-engine</h3><p>Enter the access code from config.yaml.</p>"
             b"<form method=get action='/'><input name=code type=password autofocus style='font-size:18px;width:100%'>"
             b"<p><button style='font-size:16px'>Open</button></form>")


class ExclusiveThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = False
    daemon_threads = True

    def server_bind(self):
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            try:
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            except OSError:
                pass
        super().server_bind()


def make_server(cfg, controller, log):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "intraday-engine"

        def log_message(self, fmt, *args):       # keep the console and the log quiet
            pass

        # ---- helpers ----
        def _send(self, code, body, ctype="application/json", extra=None):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code, obj):
            self._send(code, json.dumps(obj).encode("utf-8"))

        def _has_access(self, query):
            """Localhost mode: always. LAN mode: the access code, by cookie or ?code=."""
            if not cfg.lan_access:
                return True, None
            want = cfg.access_code.encode()
            cookie = self.headers.get("Cookie", "")
            for part in cookie.split(";"):
                k, _, v = part.strip().partition("=")
                if k == "ie_code" and hmac.compare_digest(v.encode(), want):
                    return True, None
            given = (query.get("code") or [""])[0]
            if given and hmac.compare_digest(given.encode(), want):
                return True, {"Set-Cookie": f"ie_code={given}; Path=/; HttpOnly; SameSite=Strict"}
            return False, None

        # ---- routes ----
        def do_GET(self):
            url = urlparse(self.path)
            ok, cookie = self._has_access(parse_qs(url.query))
            if not ok:
                return self._send(401, CODE_FORM, "text/html; charset=utf-8")
            if url.path == "/":
                if cookie:                        # drop the code from the address bar
                    return self._send(303, b"", "text/plain", {**cookie, "Location": "/"})
                return self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
            if url.path == "/api/state":
                return self._send(200, controller.snapshot_bytes())
            if url.path == "/api/s3/index":
                q = parse_qs(url.query)
                day = (q.get("day") or [None])[0]
                return self._json(200, controller.get_s3_index(day))
            if url.path == "/api/s3/scan":
                q = parse_qs(url.query)
                day = (q.get("day") or [""])[0]
                sfile = (q.get("file") or [""])[0]
                doc, src = controller.get_s3_scan(day, sfile)
                if doc is None:
                    return self._json(404, {"ok": False, "message": f"Scan not found ({src})."})
                return self._json(200, {"ok": True, "source": src, "scan": doc})
            if url.path == "/api/s3/activity":
                q = parse_qs(url.query)
                day = (q.get("day") or [None])[0]
                try:
                    limit = int((q.get("limit") or ["20"])[0])
                except ValueError:
                    limit = 20
                return self._json(200, controller.get_s3_activity(day, limit))
            if url.path == "/api/dryrun/options":
                return self._json(200, controller.get_dryrun_options())
            if url.path == "/api/socket/info":
                return self._json(200, controller.get_socket_info())
            self._json(404, {"ok": False, "message": "Not found."})

        def do_POST(self):
            url = urlparse(self.path)
            ok, _ = self._has_access({})
            if not ok:
                return self._json(401, {"ok": False, "message": "Access code needed. Reload the page."})
            # Only this page may press the buttons: another website cannot set this header.
            if self.headers.get("X-Engine-UI") != "1":
                return self._json(403, {"ok": False, "message": "Not allowed."})
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                return self._json(413, {"ok": False, "message": "Too large."})
            try:
                body = json.loads(self.rfile.read(length) or b"{}") if length else {}
            except ValueError:
                return self._json(400, {"ok": False, "message": "Bad request."})

            if url.path == "/api/start":
                done, msg = controller.request_start("button")
            elif url.path == "/api/stop":
                done, msg = controller.request_stop()
            elif url.path == "/api/check":
                done, msg = controller.request_check()
            elif url.path == "/api/dryrun":
                done, msg = controller.request_dryrun(
                    day=body.get("day"),
                    start_time=body.get("start_time"),
                    end_time=body.get("end_time"),
                )
            elif url.path == "/api/auto":
                done, msg = controller.set_auto(bool(body.get("on")), str(body.get("time", "")))
            elif url.path == "/api/socket/plug":
                done, msg, qual = controller.plug_strategy(str(body.get("file", "")))
                return self._json(200, {"ok": done, "message": msg, "qualification": qual})
            elif url.path == "/api/socket/unplug":
                done, msg = controller.unplug_strategy()
            elif url.path == "/api/socket/upload":
                done, msg, data = controller.upload_strategy(
                    str(body.get("filename", "")),
                    str(body.get("code", "")),
                    auto_plug=bool(body.get("auto_plug", True)),
                )
                return self._json(200, {"ok": done, "message": msg, **data})
            elif url.path == "/api/socket/delete":
                done, msg = controller.delete_strategy(str(body.get("file", "")))
            elif url.path == "/api/socket/qualify":
                qual = controller.qualify_socket_strategy(body.get("file"))
                return self._json(200, {"ok": True, "qualification": qual})
            elif url.path == "/api/socket/openrouter":
                res = controller.openrouter_verify(
                    file_rel_path=body.get("file"),
                    api_key=body.get("api_key"),
                    model=body.get("model"),
                )
                return self._json(200, res)
            else:
                return self._json(404, {"ok": False, "message": "Not found."})
            self._json(200, {"ok": done, "message": msg})

    bind = "0.0.0.0" if cfg.lan_access else "127.0.0.1"
    server = ExclusiveThreadingHTTPServer((bind, cfg.ui_port), Handler)
    return server
