"""Fonte Yahoo Finance (endpoint público v8/chart, sem chave, atraso ~15 min).

Por ativo são duas chamadas:
  - 5 min / 5 pregões: candles do pregão mais recente e volume relativo
    comparado aos pregões anteriores no mesmo horário;
  - diário / 1 mês: máxima, mínima e fechamento do pregão anterior (pivôs).
"""

from __future__ import annotations

from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import requests

BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) radar-b3/1.0"}
NAME = "Yahoo Finance"


def parse_chart(payload: dict) -> tuple[list[dict], int]:
    """Converte a resposta do /v8/chart em candles {t,o,h,l,c,v}.

    Candles com algum campo nulo (o Yahoo devolve null em minutos sem negócio) são descartados.
    Devolve também o gmtoffset da bolsa, em segundos.
    """
    chart = payload.get("chart") or {}
    if chart.get("error"):
        err = chart["error"]
        raise ValueError(err.get("description") or err.get("code") or str(err))
    result = (chart.get("result") or [None])[0]
    if not result:
        raise ValueError("resposta sem dados")
    offset = int(result.get("meta", {}).get("gmtoffset", -10800))
    ts = result.get("timestamp") or []
    q = (result.get("indicators", {}).get("quote") or [{}])[0]
    bars = []
    for i, t in enumerate(ts):
        vals = [q.get(f, [None] * len(ts))[i] for f in ("open", "high", "low", "close", "volume")]
        if any(v is None for v in vals):
            continue
        o, h, l, c, v = vals
        bars.append({"t": int(t), "o": float(o), "h": float(h), "l": float(l), "c": float(c), "v": float(v)})
    return bars, offset


def _local(t: int, offset: int) -> datetime:
    return datetime.fromtimestamp(t + offset, tz=timezone.utc).replace(tzinfo=None)


def _minutes(t: int, offset: int) -> int:
    d = _local(t, offset)
    return d.hour * 60 + d.minute


def split_sessions(bars: list[dict], offset: int) -> "OrderedDict[str, list[dict]]":
    out: OrderedDict[str, list[dict]] = OrderedDict()
    for b in sorted(bars, key=lambda b: b["t"]):
        out.setdefault(_local(b["t"], offset).date().isoformat(), []).append(b)
    return out


def relative_volume(sessions: "OrderedDict[str, list[dict]]", offset: int) -> float | None:
    """Volume acumulado hoje ÷ média dos pregões anteriores até o mesmo horário."""
    days = list(sessions.values())
    if len(days) < 2:
        return None
    today = days[-1]
    cutoff = _minutes(today[-1]["t"], offset)
    now = sum(b["v"] for b in today)
    past = []
    for day in days[:-1]:
        acc = sum(b["v"] for b in day if _minutes(b["t"], offset) <= cutoff)
        if acc > 0:
            past.append(acc)
    if not past:
        return None
    return now / (sum(past) / len(past))


def build_item(ticker: str, sector: str, intraday: dict, daily: dict | None) -> dict:
    bars, offset = parse_chart(intraday)
    sessions = split_sessions(bars, offset)
    if not sessions:
        raise ValueError("sem candles intradiários")
    session, today = next(reversed(sessions.items()))

    prev = None
    if daily is not None:
        dbars, doff = parse_chart(daily)
        before = [b for b in dbars if _local(b["t"], doff).date().isoformat() < session]
        if before:
            prev = before[-1]
    if prev is None:  # sem diário: usa o pregão intradiário anterior
        days = list(sessions.values())
        if len(days) < 2:
            raise ValueError("sem pregão anterior para os pivôs")
        p = days[-2]
        prev = {"h": max(b["h"] for b in p), "l": min(b["l"] for b in p), "c": p[-1]["c"]}

    rel = relative_volume(sessions, offset)
    return {
        "ticker": ticker,
        "sector": sector,
        "session": session,
        "prevClose": prev["c"],
        "prevHigh": max(prev["h"], prev["c"]),
        "prevLow": min(prev["l"], prev["c"]),
        "relVol": round(rel, 3) if rel is not None else 1.0,
        "bars": [{k: b[k] for k in ("o", "h", "l", "c", "v")} for b in today],
        "lastTime": _local(today[-1]["t"], offset).strftime("%H:%M"),
    }


def _get(http: requests.Session, symbol: str, interval: str, rng: str) -> dict:
    last_exc: Exception | None = None
    for _ in range(3):
        try:
            r = http.get(BASE_URL.format(symbol=symbol), params={"interval": interval, "range": rng},
                         headers=HEADERS, timeout=15)
            if r.status_code == 404:
                return r.json()  # Yahoo explica o motivo em chart.error
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as exc:
            last_exc = exc
    raise RuntimeError(f"falha ao buscar {symbol}: {last_exc}")


def fetch(universe: dict[str, str], workers: int = 8, http: requests.Session | None = None) -> dict:
    http = http or requests.Session()
    errors: dict[str, str] = {}

    def one(item):
        ticker, sector = item
        sym = ticker + ".SA"
        try:
            intraday = _get(http, sym, "5m", "5d")
            try:
                daily = _get(http, sym, "1d", "1mo")
            except RuntimeError:
                daily = None
            return build_item(ticker, sector, intraday, daily)
        except Exception as exc:  # noqa: BLE001 — um ativo com problema não derruba a varredura
            errors[ticker] = str(exc)
            return None

    with ThreadPoolExecutor(max_workers=workers) as ex:
        items = [x for x in ex.map(one, universe.items()) if x]

    session = max((x["session"] for x in items), default=None)
    # descarta ativos sem negócio no pregão mais recente (suspensos, deslistados)
    stale = [x for x in items if x["session"] != session]
    for x in stale:
        errors[x["ticker"]] = f"último pregão {x['session']}"
    items = [x for x in items if x["session"] == session]
    last = max((x["lastTime"] for x in items), default="")
    return {
        "source": NAME,
        "session": session,
        "updated": (f"{session[8:10]}/{session[5:7]} {last}" if session else ""),
        "fetchedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "items": items,
        "errors": errors,
    }
