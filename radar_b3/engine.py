"""Motor de fluxo: VWAP, delta estimado, pivôs, zona de volume (POC) e score.

Espelha a função analyze() de web/index.html; tests/test_parity.py garante
que as duas implementações dão o mesmo resultado.

Entrada: itens no formato do /api/scan
  {ticker, sector, prevClose, prevHigh, prevLow, relVol, bars:[{o,h,l,c,v}, ...]}
"""

from __future__ import annotations

import math


def clamp(x: float, a: float, b: float) -> float:
    return max(a, min(b, x))


def _one(d: dict) -> dict:
    b = d["bars"]
    last = b[-1]["c"]
    pv = vv = dl = 0.0
    for k in b:
        tp = (k["h"] + k["l"] + k["c"]) / 3
        pv += tp * k["v"]
        vv += k["v"]
        rg = k["h"] - k["l"]
        if rg > 0:
            dl += k["v"] * ((k["c"] - k["l"]) - (k["h"] - k["c"])) / rg
    vwap = pv / vv if vv else last
    dr = dl / vv if vv else 0.0
    chg = last / d["prevClose"] - 1

    ph, pl, pc = d["prevHigh"], d["prevLow"], d["prevClose"]
    P = (ph + pl + pc) / 3
    R1, S1 = 2 * P - pl, 2 * P - ph
    R2, S2 = P + (ph - pl), P - (ph - pl)
    R3, S3 = ph + 2 * (P - pl), pl - 2 * (ph - P)

    # zona = faixa de maior volume do dia (POC em 24 faixas)
    lo = min(k["l"] for k in b)
    hi = max(k["h"] for k in b)
    nb = 24
    st = (hi - lo) / nb or 1
    hist = [0.0] * nb
    for k in b:
        i = int(clamp(math.floor(((k["h"] + k["l"] + k["c"]) / 3 - lo) / st), 0, nb - 1))
        hist[i] += k["v"]
    pi = hist.index(max(hist))
    zone = [lo + pi * st, lo + (pi + 1) * st]

    bull = chg >= 0
    if bull:
        cls = "Acumulação compradora" if dr > 0.08 else "Alta sem fluxo"
    else:
        cls = "Distribuição vendedora" if dr < -0.08 else "Realização"

    levels = sorted([S3, S2, S1, P, R1, R2, R3, vwap])
    above = [x for x in levels if x > last * 1.0005]
    below = [x for x in levels if x < last * 0.9995]
    # preço além de todos os níveis: projeta o alvo em 1:1 a partir do stop
    if bull:
        stop = below[-1] if below else S3
        tgt = above[0] if above else last + abs(last - stop)
    else:
        stop = above[0] if above else R3
        tgt = below[-1] if below else last - abs(stop - last)
    rr = abs(tgt - last) / max(abs(last - stop), 1e-6)

    rel = d.get("relVol")
    if rel is None:
        rel = d.get("relVolRaw", 1.0)
    return {**d, "last": last, "chg": chg, "vwap": vwap, "dr": dr, "delta": dl, "vol": vv,
            "relVol": rel, "P": P, "R1": R1, "R2": R2, "S1": S1, "S2": S2, "R3": R3, "S3": S3, "zone": zone,
            "bull": bull, "cls": cls, "rr": rr, "tgt": tgt, "stop": stop}


def analyze(raw: list[dict]) -> list[dict]:
    rows = [_one(d) for d in raw if d.get("bars")]
    if not rows:
        return []
    absd = sorted(abs(x["chg"]) for x in rows)
    den = max(len(absd) - 1, 1)
    for x in rows:
        a = abs(x["chg"])
        pr = next(i for i, v in enumerate(absd) if v >= a) / den
        sgn = 1 if x["bull"] else -1
        d_al = clamp(x["dr"] * sgn / 0.4, 0, 1)
        rv = clamp((x["relVol"] - 0.8) / 2.2, 0, 1)
        vw = 1 if (x["last"] - x["vwap"]) * sgn > 0 else 0
        # JS Math.round arredonda .5 para cima; round() do Python é bancário
        x["score"] = math.floor(100 * (0.35 * pr + 0.30 * d_al + 0.20 * rv + 0.15 * vw) + 0.5)
    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows
