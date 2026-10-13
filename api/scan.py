"""Função serverless da Vercel: GET /api/scan devolve a varredura (cache de 60 s na CDN)."""

import json
from http.server import BaseHTTPRequestHandler

from radar_b3.sources import yahoo
from radar_b3.tickers import UNIVERSE


class handler(BaseHTTPRequestHandler):  # noqa: N801 — nome exigido pela Vercel
    def do_GET(self):  # noqa: N802
        try:
            code, body = 200, yahoo.fetch(UNIVERSE, workers=12)
            cache = "public, s-maxage=60, stale-while-revalidate=300"
        except Exception as exc:  # noqa: BLE001
            code, body, cache = 502, {"error": str(exc)}, "no-store"
        data = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", cache)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
