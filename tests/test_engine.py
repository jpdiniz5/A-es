import pytest

from radar_b3.engine import analyze


def bar(o, h, l, c, v):
    return {"o": o, "h": h, "l": l, "c": c, "v": v}


def item(bars, prev=(10.0, 10.2, 9.8), rel=1.0, t="AAAA3"):
    return {"ticker": t, "sector": "X", "prevClose": prev[0], "prevHigh": prev[1], "prevLow": prev[2],
            "relVol": rel, "bars": bars}


def test_vwap_delta_and_pivots_hand_computed():
    # fecha na máxima: delta = +volume; fecha na mínima: delta = −volume
    bars = [bar(10, 10.5, 10, 10.5, 100), bar(10.5, 11, 10.5, 10.5, 300)]
    (x,) = analyze([item(bars)])
    tp1, tp2 = (10.5 + 10 + 10.5) / 3, (11 + 10.5 + 10.5) / 3
    assert x["vwap"] == pytest.approx((tp1 * 100 + tp2 * 300) / 400)
    assert x["delta"] == pytest.approx(100 - 300)
    assert x["dr"] == pytest.approx(-0.5)
    assert x["chg"] == pytest.approx(0.05)
    P = (10.2 + 9.8 + 10) / 3
    assert x["P"] == pytest.approx(P)
    assert x["R1"] == pytest.approx(2 * P - 9.8)
    assert x["S1"] == pytest.approx(2 * P - 10.2)
    assert x["R2"] == pytest.approx(P + 0.4) and x["S2"] == pytest.approx(P - 0.4)
    assert x["bull"] and x["cls"] == "Alta sem fluxo"  # subiu, mas o fluxo foi vendedor


@pytest.mark.parametrize("closes,dr_sign,cls", [
    ((10.1, 10.3), +1, "Acumulação compradora"),
    ((9.9, 9.7), -1, "Distribuição vendedora"),
])
def test_classification(closes, dr_sign, cls):
    # fechamento colado na máxima (alta) ou na mínima (queda)
    bars = [bar(10, c, 10, c, 1000) if dr_sign > 0 else bar(10, 10, c, c, 1000) for c in closes]
    (x,) = analyze([item(bars)])
    assert x["cls"] == cls


def test_target_and_stop_bracket_price(items):
    for x in analyze(items):
        if x["bull"]:
            assert x["tgt"] > x["last"] and x["stop"] <= x["last"]
        else:
            assert x["tgt"] < x["last"] and x["stop"] >= x["last"]
        assert x["rr"] >= 0
        assert x["zone"][0] <= x["zone"][1]


def test_scores_in_range_and_sorted(items):
    rows = analyze(items)
    assert len(rows) == len(items)
    s = [r["score"] for r in rows]
    assert all(0 <= v <= 100 for v in s)
    assert s == sorted(s, reverse=True)


def test_degenerate_inputs():
    flat = [bar(10, 10, 10, 10, 0)]  # sem amplitude e sem volume
    (x,) = analyze([item(flat)])
    assert x["vwap"] == 10 and x["dr"] == 0 and x["score"] >= 0
    assert analyze([]) == []
    assert analyze([item([])]) == []  # ativo sem candles é ignorado


def test_breakdown_below_all_levels_keeps_target_below_price():
    # derreteu 8%: abaixo de S1/S2/S3 e da VWAP — alvo não pode ficar acima do preço
    bars = [bar(10, 10, 9.6, 9.6, 1000), bar(9.6, 9.6, 9.2, 9.2, 1000)]
    (x,) = analyze([item(bars, prev=(10.0, 10.05, 9.95))])
    assert x["last"] < x["S3"]
    assert x["tgt"] < x["last"] < x["stop"]
    assert x["rr"] == pytest.approx(1.0)
