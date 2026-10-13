"""O motor do navegador (web/index.html) e o engine.py precisam concordar."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from radar_b3.engine import analyze
from radar_b3.tickers import UNIVERSE

HTML = Path(__file__).resolve().parent.parent / "web" / "index.html"

RUNNER = r"""
const vm=require("vm"), fs=require("fs");
const html=fs.readFileSync(process.argv[2],"utf8");
const src=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)][0][1];
const ctx={module:{exports:{}}}; vm.createContext(ctx);
try{vm.runInContext(src,ctx)}catch(e){if(e!==0)throw e}
const items=JSON.parse(fs.readFileSync(0,"utf8"));
process.stdout.write(JSON.stringify({rows:ctx.module.exports.analyze(items),universe:ctx.module.exports.UNIVERSE}));
"""


@pytest.mark.skipif(not shutil.which("node"), reason="node não instalado")
def test_js_and_python_engines_agree(items, tmp_path):
    runner = tmp_path / "run.js"
    runner.write_text(RUNNER)
    out = subprocess.run(["node", str(runner), str(HTML)], input=json.dumps(items),
                         capture_output=True, text=True, check=True).stdout
    res = json.loads(out)
    js, py = res["rows"], analyze(items)
    assert res["universe"] == UNIVERSE  # mesma lista de ativos no painel e no backend
    assert [r["ticker"] for r in js] == [r["ticker"] for r in py]
    for a, b in zip(js, py):
        assert a["score"] == b["score"] and a["cls"] == b["cls"], a["ticker"]
        for k in ("vwap", "dr", "chg", "tgt", "stop", "rr", "P", "R1", "S1"):
            assert a[k] == pytest.approx(b[k], rel=1e-9, abs=1e-12), (a["ticker"], k)
        assert a["zone"] == pytest.approx(b["zone"])
