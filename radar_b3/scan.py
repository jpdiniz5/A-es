"""Varredura pela linha de comando.

  python -m radar_b3.scan                       # imprime o ranking
  python -m radar_b3.scan --out data/snapshot.json
  python -m radar_b3.scan --from data/snapshot.json   # reanalisa um snapshot salvo
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .engine import analyze
from .sources import yahoo
from .tickers import UNIVERSE


def table(rows: list[dict], top: int) -> str:
    out = []
    for side, title in ((True, "FLUXO COMPRADOR"), (False, "FLUXO VENDEDOR")):
        out.append(f"\n{title}")
        out.append(f"{'#':>2}  {'ativo':<7} {'var%':>7} {'último':>9} {'VWAP':>9} {'delta%':>7} {'vol.rel':>7} {'score':>5}  classe")
        for i, x in enumerate([r for r in rows if r["bull"] == side][:top], 1):
            out.append(f"{i:>2}  {x['ticker']:<7} {x['chg']*100:>+7.2f} {x['last']:>9.2f} {x['vwap']:>9.2f} "
                       f"{x['dr']*100:>+7.0f} {x['relVol']:>7.2f} {x['score']:>5}  {x['cls']}")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Radar de fluxo B3")
    ap.add_argument("--out", type=Path, help="salva o snapshot (formato do /api/scan)")
    ap.add_argument("--from", dest="src", type=Path, help="usa um snapshot salvo em vez de buscar")
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--min-items", type=int, default=1, help="sai com erro se vierem menos ativos que isso")
    a = ap.parse_args(argv)

    snap = json.loads(a.src.read_text()) if a.src else yahoo.fetch(UNIVERSE)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(snap, ensure_ascii=False, separators=(",", ":")))

    rows = analyze(snap["items"])
    up = sum(r["bull"] for r in rows)
    print(f"{snap['source']} · pregão {snap.get('session')} · {snap.get('updated')} · "
          f"{len(rows)} ativos ({up} ↑ / {len(rows) - up} ↓)")
    print(table(rows, a.top))
    if snap.get("errors"):
        print("\nSem dados: " + ", ".join(f"{k} ({v})" for k, v in sorted(snap["errors"].items())))
    return 0 if len(rows) >= a.min_items else 1


if __name__ == "__main__":
    sys.exit(main())
