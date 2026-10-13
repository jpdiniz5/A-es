# Radar de Fluxo B3

Varredura intradiária de ~50 ações líquidas da B3: separa fluxo comprador e vendedor,
calcula VWAP, delta estimado, volume relativo, pivôs (S1–S3 / R1–R3), zona de maior
volume (POC) e um score de 0 a 100. É um filtro de varredura, não recomendação.

## Uso

```bash
pip install -r requirements.txt

python -m radar_b3.scan                          # ranking no terminal (Yahoo, atraso ~15 min)
python -m radar_b3.scan --out data/snapshot.json # salva o snapshot
python -m radar_b3.server                        # painel em http://localhost:8000
python -m radar_b3.server --snapshot data/snapshot.json   # painel com snapshot salvo
python -m radar_b3.build_page data/snapshot.json -o dist/radar.html  # página autônoma
```

## Estrutura

| Arquivo | O que faz |
|---|---|
| `radar_b3/tickers.py` | universo de ativos por setor |
| `radar_b3/sources/yahoo.py` | busca candles de 5 min (5 pregões) e diários; normaliza para o formato do `/api/scan` |
| `radar_b3/engine.py` | motor de fluxo (mesma lógica do `analyze()` em `web/index.html`) |
| `radar_b3/server.py` | serve o painel e `/api/scan` com cache de 60 s |
| `web/index.html` | painel; sem servidor roda em modo demo ou com snapshot embutido |

### Dados

- **Volume relativo**: volume acumulado do pregão ÷ média dos 4 pregões anteriores
  *até o mesmo horário* (não contra o dia inteiro, que distorcia o início do pregão).
- **Pivôs**: máxima/mínima/fechamento do pregão anterior, pelo candle diário.
- Ativos sem negócio no pregão mais recente (suspensos, deslistados, código trocado)
  saem da varredura e aparecem em `errors` (chip "N sem dados" no painel).
- Limitação do Yahoo: os candles dos leilões de abertura e fechamento vêm com volume 0,
  então o volume dos leilões fica fora da VWAP e do delta (o preço de fechamento entra).

## Testes

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

`tests/test_parity.py` roda o motor do navegador no Node e confere que ele dá o mesmo
resultado do `engine.py`.

## GitHub Actions

`.github/workflows/radar.yml` roda os testes e uma varredura real a cada push, a cada
30 min durante o pregão e sob demanda. O snapshot e a página autônoma vão para o
branch `snapshot` e ficam como artefato do run.
