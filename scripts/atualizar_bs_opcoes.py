#!/usr/bin/env python3
"""
atualizar_bs_opcoes.py
Atualiza spot_atual, iv_calculada, preco_teorico nas posições abertas de opções.
Imprime JSON com resumo das operações vencendo em 7 dias.
"""
import json, math, sys, requests
from datetime import date, timedelta
from scipy import optimize
from scipy.stats import norm
import yfinance as yf

REPO = "/root/.openclaw/familia-donato-suarez"
BRAPI_TOKEN = "nNUwfcCiufU2N3EUEB16ix"
R_SELIC = 0.1325

def bs(S, K, T, r, sigma, tipo):
    if T <= 1/365:
        return max(0.0, S - K) if tipo == "CALL" else max(0.0, K - S)
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if tipo == "CALL":
        return S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    return K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

def calc_iv(S, K, T, r, mkt_price, tipo):
    intrinsic = max(0.0, S - K) if tipo == "CALL" else max(0.0, K - S)
    if mkt_price <= intrinsic + 0.001:
        return None
    try:
        return optimize.brentq(lambda s: bs(S, K, T, r, s, tipo) - mkt_price, 0.001, 10.0, xtol=1e-6, maxiter=300)
    except Exception:
        return None

def get_spot_br(ticker):
    try:
        r = requests.get(f"https://brapi.dev/api/quote/{ticker}?token={BRAPI_TOKEN}", timeout=10).json()
        return r["results"][0]["regularMarketPrice"]
    except Exception:
        return None

def get_chain_br(acao, vencimento):
    url = f"https://opcoes.net.br/listaopcoes/completa?idAcao={acao}&cotacoes=true&vencimentos={vencimento}"
    try:
        data = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10).json()
        return {str(o[0]).upper(): {"strike": o[5], "tipo": o[2], "ultimo": o[8]} for o in data["data"]["cotacoesOpcoes"]}
    except Exception:
        return {}

def get_tbill():
    try:
        return yf.Ticker("^IRX").fast_info["lastPrice"] / 100
    except Exception:
        return 0.0435

def main():
    today = date.today()
    r_tbill = get_tbill()
    ts = today.isoformat()

    with open(f"{REPO}/data/opcoes_br.json") as f:
        br_json = json.load(f)
    with open(f"{REPO}/data/opcoes_intl.json") as f:
        intl_json = json.load(f)

    abertas_br   = [o for o in br_json["operacoes"]   if o["status"] == "aberta"]
    abertas_intl = [o for o in intl_json["operacoes"] if o["status"] == "aberta"]

    # Cache de spots e chains BR
    spots_br, chain_cache = {}, {}
    for o in abertas_br:
        acao = o["acao"]
        venc = o["vencimento"]
        if acao not in spots_br:
            spots_br[acao] = get_spot_br(acao)
        if (acao, venc) not in chain_cache:
            chain_cache[(acao, venc)] = get_chain_br(acao, venc)

        S = spots_br[acao]
        strike = o["strike"]
        tipo = o["tipo_contrato"]
        T = (date.fromisoformat(venc) - today).days / 365
        o["spot_atual"] = S
        o["bs_data_calculo"] = ts

        if S is None or T < 0:
            o["iv_calculada"] = None
            o["preco_teorico"] = None
            continue

        chain = chain_cache[(acao, venc)]
        ticker_b = o["ticker_opcao"].upper().replace("_2026","").replace("_2025","")
        mkt = None
        for k, v in chain.items():
            if k.replace("_2026","").replace("_2025","") == ticker_b:
                mkt = v["ultimo"]; break
        if mkt is None:
            for k, v in chain.items():
                if abs(v["strike"] - strike) < 0.01 and v["tipo"] == tipo:
                    mkt = v["ultimo"]; break

        iv = calc_iv(S, strike, T, R_SELIC, mkt, tipo) if (mkt and mkt > 0) else None
        teorico = round(bs(S, strike, T, R_SELIC, iv, tipo), 2) if iv else (round(mkt, 2) if mkt else None)
        o["iv_calculada"] = round(iv, 4) if iv else None
        o["preco_teorico"] = teorico

    # US
    spots_us = {}
    for o in abertas_intl:
        sym = o["ticker"]
        if sym not in spots_us:
            try: spots_us[sym] = yf.Ticker(sym).fast_info["lastPrice"]
            except: spots_us[sym] = None

        S = spots_us.get(sym)
        strike = o["strike"]
        tipo = o["tipo_contrato"]
        venc = o["vencimento"]
        T = (date.fromisoformat(venc) - today).days / 365
        o["spot_atual"] = round(S, 2) if S else None
        o["bs_data_calculo"] = ts

        if S is None or T < 0:
            o["iv_calculada"] = None
            o["preco_teorico"] = None
            continue

        mkt, iv = None, None
        try:
            chain = yf.Ticker(sym).option_chain(venc)
            df = chain.calls if tipo == "CALL" else chain.puts
            row = df[abs(df["strike"] - strike) < 0.5]
            if not row.empty:
                bid  = float(row.iloc[0].get("bid", 0) or 0)
                ask  = float(row.iloc[0].get("ask", 0) or 0)
                last = float(row.iloc[0]["lastPrice"] or 0)
                # mid-price quando mercado aberto; lastPrice como fallback (bid/ask=0 fora do horário)
                mkt = (bid + ask) / 2 if bid > 0 and ask > 0 else last
        except Exception:
            pass

        # Sempre calcular IV via bisection — nunca usar impliedVolatility do yfinance (lixo fora do horário)
        if mkt and mkt > 0:
            iv = calc_iv(S, strike, T, r_tbill, mkt, tipo)
        teorico = round(bs(S, strike, T, r_tbill, iv, tipo), 2) if iv else None
        o["iv_calculada"] = round(iv, 4) if iv else None
        o["preco_teorico"] = teorico

    with open(f"{REPO}/data/opcoes_br.json", "w") as f:
        json.dump(br_json, f, ensure_ascii=False, indent=2)
    with open(f"{REPO}/data/opcoes_intl.json", "w") as f:
        json.dump(intl_json, f, ensure_ascii=False, indent=2)

    # Resumo 7 dias
    limite = today + timedelta(days=7)
    resumo = []
    for o in abertas_br + abertas_intl:
        venc = date.fromisoformat(o["vencimento"])
        if venc > limite:
            continue
        mercado = "BR" if "acao" in o else "US"
        acao    = o.get("acao", o.get("ticker"))
        S       = o.get("spot_atual")
        strike  = o["strike"]
        tipo    = o["tipo_contrato"]
        itm     = bool(S and ((tipo == "CALL" and S > strike) or (tipo == "PUT" and S < strike)))
        resumo.append({
            "mercado": mercado, "acao": acao,
            "ticker": o.get("ticker_opcao", o.get("ticker")),
            "tipo": tipo, "strike": strike, "spot": S,
            "vencimento": o["vencimento"], "dias": (venc - today).days,
            "abertura": o["preco_opcao_abertura"],
            "teorico": o.get("preco_teorico"),
            "itm": itm, "quantidade": o["quantidade"],
        })

    resumo.sort(key=lambda x: (x["vencimento"], x["mercado"], x["acao"]))
    print(json.dumps({"data": ts, "r_selic": R_SELIC, "r_tbill": r_tbill, "vencendo_7d": resumo}, ensure_ascii=False))

if __name__ == "__main__":
    main()
