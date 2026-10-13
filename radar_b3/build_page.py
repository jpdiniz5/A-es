"""Gera uma página autônoma com um snapshot embutido (para publicar sem servidor).

  python -m radar_b3.build_page data/snapshot.json -o dist/radar.html
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "web" / "index.html"
SLOT = re.compile(r'(<script id="snapshot" type="application/json">)(.*?)(</script>)', re.S)


def embed(html: str, snap: dict) -> str:
    data = json.dumps(snap, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    out, n = SLOT.subn(lambda m: m.group(1) + data + m.group(3), html, count=1)
    if n != 1:
        raise ValueError("slot do snapshot não encontrado em index.html")
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("snapshot", type=Path)
    ap.add_argument("-o", "--out", type=Path, required=True)
    a = ap.parse_args(argv)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(embed(WEB.read_text(), json.loads(a.snapshot.read_text())))
    print(a.out)


if __name__ == "__main__":
    main()
