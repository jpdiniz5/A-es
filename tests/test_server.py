import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from radar_b3.build_page import embed
from radar_b3.server import WEB, Scanner, make_handler


@pytest.fixture
def server(items):
    calls = []

    def loader():
        calls.append(1)
        return {"source": "teste", "updated": "09/10 16:55", "items": items, "errors": {}}

    srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(Scanner(loader, ttl=60)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}", calls
    srv.shutdown()


def get(url):
    with urllib.request.urlopen(url) as r:
        return r.status, r.headers["Content-Type"], r.read()


def test_serves_page_and_cached_scan(server):
    base, calls = server
    st, ct, body = get(base + "/")
    assert st == 200 and "text/html" in ct and b"RADAR" in body
    for _ in range(3):
        st, ct, body = get(base + "/api/scan")
    data = json.loads(body)
    assert st == 200 and data["source"] == "teste" and len(data["items"]) == 30
    assert len(calls) == 1  # cache de 60 s


def test_404(server):
    with pytest.raises(urllib.error.HTTPError) as e:
        get(server[0] + "/nada")
    assert e.value.code == 404


def test_embed_snapshot_escapes_script_close():
    html = embed(WEB.read_text(), {"source": "x</script><b>", "items": []})
    assert "x<\\/script><b>" in html
    assert html.count('<script id="snapshot"') == 1
