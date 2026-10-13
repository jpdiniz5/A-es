import json

import pytest

from radar_b3.sources import yahoo
from tests.conftest import session_rows, ts, yahoo_payload


def daily(rows):
    return yahoo_payload([(ts(d, "10:00"), o, h, l, c, v) for d, o, h, l, c, v in rows])


def test_parse_skips_null_candles():
    rows = session_rows("2026-10-09", n=5)
    p = yahoo_payload(rows)
    p["chart"]["result"][0]["indicators"]["quote"][0]["close"][2] = None
    bars, off = yahoo.parse_chart(p)
    assert len(bars) == 4 and off == -10800


def test_parse_error_payload():
    with pytest.raises(ValueError, match="delisted"):
        yahoo.parse_chart({"chart": {"result": None, "error": {"code": "Not Found", "description": "No data found, symbol may be delisted"}}})


def test_build_item_uses_last_session_and_previous_daily_bar():
    intraday = yahoo_payload(session_rows("2026-10-08", vol=1000, seed=1) + session_rows("2026-10-09", vol=2000, seed=2))
    d = daily([("2026-10-07", 9, 9.5, 8.9, 9.2, 1), ("2026-10-08", 9.2, 10.4, 9.1, 10.0, 1), ("2026-10-09", 10, 11, 9, 10.5, 1)])
    it = yahoo.build_item("PETR4", "Petróleo", intraday, d)
    assert it["session"] == "2026-10-09"
    assert len(it["bars"]) == 84 and it["lastTime"] == "16:55"
    assert (it["prevClose"], it["prevHigh"], it["prevLow"]) == (10.0, 10.4, 9.1)
    assert it["relVol"] == pytest.approx(2.0)  # dobro do volume no mesmo horário
    json.dumps(it)  # serializável para o /api/scan


def test_relvol_matches_time_of_day_midsession():
    prev = session_rows("2026-10-08", vol=1000)
    today = session_rows("2026-10-09", vol=1000, n=12)  # só até 10:55
    it = yahoo.build_item("X", "Y", yahoo_payload(prev + today), None)
    assert it["relVol"] == pytest.approx(1.0)  # compara 12 candles com 12 candles, não com o dia inteiro


def test_fallback_to_intraday_previous_session_without_daily():
    prev = session_rows("2026-10-08", start=20, seed=3)
    it = yahoo.build_item("X", "Y", yahoo_payload(prev + session_rows("2026-10-09")), None)
    assert it["prevClose"] == pytest.approx(prev[-1][4])
    assert it["prevHigh"] == pytest.approx(max(r[2] for r in prev))


class FakeHTTP:
    """Simula o Yahoo: um ativo ok, um deslistado (404) e um parado num pregão antigo."""

    def __init__(self):
        self.calls = 0

    def get(self, url, params, headers, timeout):
        self.calls += 1
        sym = url.rsplit("/", 1)[1]
        if sym == "DEAD3.SA":
            return Resp(404, {"chart": {"result": None, "error": {"code": "Not Found", "description": "No data found, symbol may be delisted"}}})
        day = "2026-10-01" if sym == "OLD3.SA" else "2026-10-09"
        if params["interval"] == "1d":
            return Resp(200, daily([("2026-09-30", 9, 10, 8, 9.5, 1), ("2026-10-08", 9, 10, 8, 9.5, 1)]))
        return Resp(200, yahoo_payload(session_rows("2026-09-30") + session_rows(day)))


class Resp:
    def __init__(self, code, body):
        self.status_code, self._b = code, body

    def json(self):
        return self._b

    def raise_for_status(self):
        if self.status_code >= 400:
            raise yahoo.requests.HTTPError(str(self.status_code))


def test_fetch_collects_errors_without_failing():
    snap = yahoo.fetch({"GOOD3": "A", "DEAD3": "B", "OLD3": "C"}, workers=2, http=FakeHTTP())
    assert [x["ticker"] for x in snap["items"]] == ["GOOD3"]
    assert "delisted" in snap["errors"]["DEAD3"]
    assert snap["errors"]["OLD3"] == "último pregão 2026-10-01"
    assert snap["session"] == "2026-10-09" and snap["updated"] == "09/10 16:55"
