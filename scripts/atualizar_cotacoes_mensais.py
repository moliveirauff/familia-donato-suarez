#!/usr/bin/env python3
"""
atualizar_cotacoes_mensais.py
Atualiza cotações do mês corrente para todos os ativos com preço disponível na internet.
Imprime JSON com: atualizados, falhos, manual_needed.
"""
import json, sys, requests
from datetime import date, datetime
import yfinance as yf

REPO = "/root/.openclaw/familia-donato-suarez"
BRAPI_TOKEN = "nNUwfcCiufU2N3EUEB16ix"

# Tickers que precisam de envio manual pelo Mauricio (sem preço público automático)
MANUAL_NEEDED = [
    "Icatu Previ",
    "Vitreo Superprev 2",
    "XP Superprev 2",
    "Arca Previ",
    "Arca Grão RF Previ",
    "Quest Luce Previ",
    "Tesouro IPCA+ 2050",
    "Tesouro Educa+ 2043",
]

# Tickers US (yfinance)
US_TICKERS = [
    "ETHA", "IBIT", "SGOV", "SPY", "VNQ",
    "QQQM", "QQQ", "NOBL", "IJS", "VTV",
    "SPYM", "VEU",
]

# PTAX último dia útil anterior via Bacen
def get_ptax():
    from datetime import timedelta
    for delta in range(5):
        d = date.today() - timedelta(days=delta)
        ds = d.strftime("%m-%d-%Y")
        try:
            r = requests.get(
                f"https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
                f"CotacaoDolarDia(dataCotacao=@dataCotacao)?@dataCotacao='{ds}'&$format=json",
                timeout=10
            ).json()
            vals = r.get("value", [])
            if vals:
                return float(vals[-1]["cotacaoVenda"])
        except Exception:
            continue
    return None

# Spots BR via brapi (batch)
def get_spots_br(tickers):
    result = {}
    # brapi aceita lista separada por vírgula
    batch = ",".join(tickers)
    try:
        r = requests.get(
            f"https://brapi.dev/api/quote/{batch}?token={BRAPI_TOKEN}",
            timeout=15
        ).json()
        for item in r.get("results", []):
            sym = item.get("symbol")
            price = item.get("regularMarketPrice")
            if sym and price:
                result[sym] = price
    except Exception:
        pass
    # fallback individual para os que falharam
    for t in tickers:
        if t not in result:
            try:
                r = requests.get(
                    f"https://brapi.dev/api/quote/{t}?token={BRAPI_TOKEN}", timeout=10
                ).json()
                p = r["results"][0]["regularMarketPrice"]
                result[t] = p
            except Exception:
                result[t] = None
    return result

def main():
    today = date.today()
    MESES_PT = {1:"jan",2:"fev",3:"mar",4:"abr",5:"mai",6:"jun",7:"jul",8:"ago",9:"set",10:"out",11:"nov",12:"dez"}
    mes = f"{MESES_PT[today.month]}/{today.year}"  # ex: "mar/2026" (formato PT obrigatorio)

    with open(f"{REPO}/data/invest_cotacoes_mensais.json") as f:
        cotacoes = json.load(f)
    with open(f"{REPO}/data/ativos_financeiros.json") as f:
        af = json.load(f)

    # Mapa ticker → macro_classe
    classe_map = {}
    for a in af.get("ativos", []):
        key = a.get("ticker") or a.get("nome")
        if key:
            classe_map[key] = a.get("macro_classe", "")

    # Identificar clean tickers (sem sufixo _YYYY.MM.DD)
    import re
    dated_re = re.compile(r"_\d{4}\.\d{2}\.\d{2}$")

    clean_tickers = [k for k in cotacoes.keys()
                     if not dated_re.search(k)
                     and k not in ("data_atualizacao", "versao")
                     and k not in MANUAL_NEEDED]

    # Separar por tipo
    br_tickers  = [t for t in clean_tickers if t not in US_TICKERS and t not in MANUAL_NEEDED]
    us_tickers  = [t for t in clean_tickers if t in US_TICKERS]

    atualizados = []
    falhos = []

    # ── PTAX ──────────────────────────────────────────────────────────────────
    ptax = get_ptax()

    # ── BR via brapi ──────────────────────────────────────────────────────────
    spots_br = get_spots_br(br_tickers)
    for ticker in br_tickers:
        price = spots_br.get(ticker)
        if price and isinstance(cotacoes.get(ticker), dict):
            cotacoes[ticker][mes] = round(price, 2)
            atualizados.append({"ticker": ticker, "mercado": "BR", "preco": round(price, 2), "moeda": "BRL"})
        else:
            falhos.append({"ticker": ticker, "mercado": "BR", "erro": "brapi sem retorno"})

    # ── US via yfinance ───────────────────────────────────────────────────────
    for ticker in us_tickers:
        try:
            price_usd = yf.Ticker(ticker).fast_info["lastPrice"]
            if price_usd and ptax:
                price_brl = round(price_usd * ptax, 2)
                if isinstance(cotacoes.get(ticker), dict):
                    cotacoes[ticker][mes] = price_brl
                    atualizados.append({
                        "ticker": ticker, "mercado": "US",
                        "preco_usd": round(price_usd, 4),
                        "ptax": ptax,
                        "preco_brl": price_brl, "moeda": "BRL"
                    })
            elif price_usd:
                falhos.append({"ticker": ticker, "mercado": "US", "erro": "PTAX indisponível"})
        except Exception as e:
            falhos.append({"ticker": ticker, "mercado": "US", "erro": str(e)})

    # Atualizar timestamp
    cotacoes["data_atualizacao"] = today.isoformat()

    with open(f"{REPO}/data/invest_cotacoes_mensais.json", "w") as f:
        json.dump(cotacoes, f, ensure_ascii=False, indent=2)

    # Manual needed: verificar quais têm mes corrente ainda como None/ausente
    manual_report = []
    for t in MANUAL_NEEDED:
        if t in cotacoes and isinstance(cotacoes[t], dict):
            val = cotacoes[t].get(mes)
            manual_report.append({"ticker": t, "valor_atual": val})

    print(json.dumps({
        "mes": mes,
        "data": today.isoformat(),
        "ptax": ptax,
        "atualizados": len(atualizados),
        "falhos": len(falhos),
        "manual_needed": len(manual_report),
        "detalhes_atualizados": atualizados,
        "detalhes_falhos": falhos,
        "detalhes_manual": manual_report,
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
