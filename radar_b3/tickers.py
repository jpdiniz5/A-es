"""Universo de ativos do radar, agrupado por setor.

Mudanças de código em relação à primeira versão:
  CCRO3 -> MOTV3 (CCR virou Motiva), ELET3 -> AXIA3 (Eletrobras virou Axia),
  BRFS3 + MRFG3 -> MBRF3 (fusão BRF/Marfrig).
"""

UNIVERSE: dict[str, str] = {
    "ITUB4": "Bancos", "BBDC4": "Bancos", "BBAS3": "Bancos", "SANB11": "Bancos", "BPAC11": "Bancos",
    "B3SA3": "Financeiro",
    "BBSE3": "Seguros", "CXSE3": "Seguros",
    "PETR4": "Petróleo", "PETR3": "Petróleo", "PRIO3": "Petróleo", "RECV3": "Petróleo",
    "UGPA3": "Petróleo", "VBBR3": "Petróleo", "CSAN3": "Petróleo",
    "VALE3": "Mineração", "CMIN3": "Mineração",
    "GGBR4": "Siderurgia", "CSNA3": "Siderurgia", "USIM5": "Siderurgia", "GOAU4": "Siderurgia",
    "AXIA3": "Energia", "EQTL3": "Energia", "CPFE3": "Energia", "CMIG4": "Energia",
    "EGIE3": "Energia", "TAEE11": "Energia", "ENGI11": "Energia",
    "SBSP3": "Saneamento",
    "ABEV3": "Consumo", "NATU3": "Consumo",
    "MGLU3": "Varejo", "LREN3": "Varejo", "ASAI3": "Varejo",
    "RADL3": "Saúde", "HAPV3": "Saúde", "RDOR3": "Saúde",
    "WEGE3": "Indústria", "EMBR3": "Indústria",
    "RAIL3": "Logística", "AZUL4": "Logística", "MOTV3": "Logística",
    "SUZB3": "Papel e Celulose", "KLBN11": "Papel e Celulose",
    "JBSS3": "Alimentos", "MBRF3": "Alimentos",
    "SLCE3": "Agro",
    "CYRE3": "Construção", "MRVE3": "Construção", "EZTC3": "Construção",
    "TOTS3": "Tecnologia",
    "VIVT3": "Telecom", "TIMS3": "Telecom",
}
