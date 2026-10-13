import math
import random
from datetime import datetime, timedelta, timezone

import pytest

BRT = -10800


def ts(day: str, hhmm: str) -> int:
    d = datetime.fromisoformat(f"{day}T{hhmm}:00").replace(tzinfo=timezone.utc)
    return int(d.timestamp()) - BRT


def yahoo_payload(rows, offset=BRT):
    """rows: [(epoch, o, h, l, c, v)] -> resposta no formato do /v8/chart."""
    cols = list(zip(*rows)) if rows else [[]] * 6
    return {"chart": {"result": [{
        "meta": {"symbol": "TEST.SA", "gmtoffset": offset, "exchangeTimezoneName": "America/Sao_Paulo"},
        "timestamp": list(cols[0]),
        "indicators": {"quote": [{"open": list(cols[1]), "high": list(cols[2]), "low": list(cols[3]),
                                  "close": list(cols[4]), "volume": list(cols[5])}]},
    }], "error": None}}


def session_rows(day, start=10.0, n=84, vol=1000, seed=1, drift=0.0):
    r = random.Random(seed)
    out, p = [], start
    t0 = ts(day, "10:00")
    for i in range(n):
        o = p
        c = o * (1 + drift + r.gauss(0, 0.002))
        h, l = max(o, c) * 1.001, min(o, c) * 0.999
        out.append((t0 + 300 * i, o, h, l, c, vol))
        p = c
    return out


def synthetic_items(n=30, seed=7):
    """Itens já normalizados (formato /api/scan) com cenários variados."""
    r = random.Random(seed)
    items = []
    for j in range(n):
        pc = 10 + r.random() * 50
        p, bars = pc * (1 + r.gauss(0, 0.004)), []
        drift = r.gauss(0, 0.0006)
        for _ in range(r.choice([1, 2, 30, 84])):
            o = p
            c = o * (1 + drift + r.gauss(0, 0.002))
            h = max(o, c) * (1 + abs(r.gauss(0, 0.001)))
            l = min(o, c) * (1 - abs(r.gauss(0, 0.001)))
            bars.append({"o": o, "h": h, "l": l, "c": c, "v": float(r.randint(0, 50000))})
            p = c
        items.append({"ticker": f"T{j:02d}", "sector": f"S{j % 5}", "prevClose": pc,
                      "prevHigh": pc * 1.015, "prevLow": pc * 0.985, "relVol": round(r.uniform(0.3, 4), 3),
                      "bars": bars})
    return items


@pytest.fixture
def items():
    return synthetic_items()
