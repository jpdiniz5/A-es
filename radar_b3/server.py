"""Servidor local: entrega web/index.html e /api/scan (cache de 60 s).

  python -m radar_b3.server                    # dados do Yahoo, http://localhost:8000
  python -m radar_b3.server --snapshot data/snapshot.json   # serve um snapshot salvo
"""

from __future__ import annotations

import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .sources import yahoo
from .tickers import UNIVERSE

WEB = Path(__file__).resolve().parent.parent / "web" / "index.html"


class Scanner:
    def __init__(self, loader, ttl: float = 60):
        self.loader, self.ttl = loader, ttl
        self._lock = threading.Lock()
        self._data: dict | None = None
        self._at = 0.0

    def get(self) -> dict:
        with self._lock:  # uma busca por vez; pedidos simultâneos reaproveitam o resultado
            if self._data is None or time.monotonic() - self._at > self.ttl:
                self._data = self.loader()
                self._at = time.monotonic()
            return self._data


def make_handler(scanner: Scanner):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code: int, body: bytes, ctype: str):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):  # noqa: N802
            path = self.path.split("?", 1)[0]
            if path in ("/", "/index.html"):
                self._send(200, WEB.read_bytes(), "text/html; charset=utf-8")
            elif path == "/api/scan":
                try:
                    body = json.dumps(scanner.get(), ensure_ascii=False).encode()
                    self._send(200, body, "application/json; charset=utf-8")
                except Exception as exc:  # noqa: BLE001
                    self._send(502, json.dumps({"error": str(exc)}).encode(), "application/json")
            else:
                self._send(404, b"not found", "text/plain")

        def log_message(self, fmt, *args):
            pass

    return Handler


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--snapshot", type=Path)
    a = ap.parse_args(argv)
    loader = (lambda: json.loads(a.snapshot.read_text())) if a.snapshot else (lambda: yahoo.fetch(UNIVERSE))
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), make_handler(Scanner(loader)))
    print(f"Radar B3 em http://localhost:{a.port}")
    srv.serve_forever()


if __name__ == "__main__":
    main()
