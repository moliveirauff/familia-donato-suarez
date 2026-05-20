#!/usr/bin/env python3
"""
Gera fluxo de caixa mensal de opções no formato CORRETO para dashboards
Estrutura esperada por opcoes.html e outros consumidores
"""

import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Caminhos
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
OPCOES_BR = DATA_DIR / "opcoes_br.json"
OPCOES_US = DATA_DIR / "opcoes_intl.json"
OUTPUT = DATA_DIR / "fluxo_caixa_opcoes_mensal.json"


def calcular_fluxo_br(opcoes):
    """Calcula fluxo de caixa BR por mês"""
    fluxo = defaultdict(float)
    
    for op in opcoes:
        # ABERTURA
        mes_abertura = op['data_operacao'][:7]
        preco_ab = op.get('preco_opcao_abertura', 0)
        qtd = op.get('quantidade', 0)
        taxa_ab = op.get('taxas_abertura', 0) or 3.5
        
        if op['operacao'] == 'Venda':
            # Venda: recebe - taxa
            fluxo[mes_abertura] += (preco_ab * qtd) - taxa_ab
        else:  # Compra
            # Compra: paga + taxa
            fluxo[mes_abertura] -= (preco_ab * qtd) + taxa_ab
        
        # FECHAMENTO
        if op['status'] == 'fechada' and op.get('data_fechamento'):
            mes_fech = op['data_fechamento'][:7]
            preco_fech = op.get('preco_opcao_fechamento', 0)
            taxa_fech = op.get('taxas_fechamento', 0) or 3.5
            
            if op['operacao'] == 'Venda':
                # Venda precisa recomprar: paga + taxa
                fluxo[mes_fech] -= (preco_fech * qtd) + taxa_fech
            else:  # Compra
                # Compra revende: recebe - taxa
                fluxo[mes_fech] += (preco_fech * qtd) - taxa_fech
    
    return fluxo


CRIPTO_TICKERS = {'IBIT', 'ETHA'}


def _buscar_cotacao(data_str, cache):
    """Busca PTAX de venda no Bacen de forma determinística.

    Regra operacional: usar a PTAX do dia da operação. Se a data não tiver
    cotação Bacen (fim de semana/feriado), usar o último dia útil anterior.
    Nunca usar fallback fixo silencioso, pois isso altera o fluxo histórico.
    """
    import requests
    import time
    from datetime import timedelta

    if data_str in cache:
        return cache[data_str]

    data_obj = datetime.strptime(data_str, '%Y-%m-%d')
    erros = []

    for back in range(0, 8):
        data_consulta = data_obj - timedelta(days=back)
        data_bacen = data_consulta.strftime('%m-%d-%Y')
        data_cache = data_consulta.strftime('%Y-%m-%d')
        url = (
            f"https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
            f"CotacaoDolarDia(dataCotacao=@dataCotacao)?@dataCotacao='{data_bacen}'&$format=json"
        )

        erro_de_rede = None
        for tentativa in range(4):
            try:
                resp = requests.get(url, timeout=20)
                resp.raise_for_status()
                data = resp.json()
                erro_de_rede = None
                if data.get('value'):
                    cotacao = round(float(data['value'][0]['cotacaoVenda']), 4)
                    cache[data_str] = cotacao
                    sufixo = '' if data_cache == data_str else f' (última útil: {data_cache})'
                    print(f"  Cotação {data_str}: R$ {cotacao:.4f}{sufixo}")
                    return cotacao
                break
            except Exception as e:
                erro_de_rede = e
                erros.append(f'{data_cache} tentativa {tentativa + 1}: {e}')
                time.sleep(0.5 * (tentativa + 1))
        if erro_de_rede is not None:
            raise RuntimeError(
                f"Falha de rede/API ao buscar PTAX de {data_cache}; "
                f"não vou recuar para data anterior por timeout. Erro: {erro_de_rede}"
            )

    raise RuntimeError(
        f"PTAX não encontrada para {data_str}; sem fallback fixo. "
        f"Erros: {' | '.join(erros[-5:])}"
    )


def calcular_fluxo_us(opcoes):
    """
    Calcula fluxo de caixa US por mês (em USD e BRL),
    separando ETFs tradicionais (US) de ETFs de cripto (IBIT, ETHA).
    Retorna (fluxo_us_usd, fluxo_us_brl, fluxo_cripto_usd, fluxo_cripto_brl).
    """
    fluxo_us_usd = defaultdict(float)
    fluxo_us_brl = defaultdict(float)
    fluxo_cripto_usd = defaultdict(float)
    fluxo_cripto_brl = defaultdict(float)
    cache_cotacoes = {}

    for op in opcoes:
        ticker = op.get('ticker', op.get('underlying', '')).upper()
        is_cripto = ticker in CRIPTO_TICKERS

        target_usd = fluxo_cripto_usd if is_cripto else fluxo_us_usd
        target_brl = fluxo_cripto_brl if is_cripto else fluxo_us_brl

        data_abertura = op['data_operacao']
        mes_abertura = data_abertura[:7]
        cotacao = float(op.get('ptax_abertura') or _buscar_cotacao(data_abertura, cache_cotacoes))

        preco_ab = op.get('preco_opcao_abertura', 0)
        qtd = op.get('quantidade', 0)
        taxa_ab = op.get('taxas_abertura', 0)

        # ABERTURA
        if op['operacao'] == 'Venda':
            val = (preco_ab * qtd) - taxa_ab
            target_usd[mes_abertura] += val
            target_brl[mes_abertura] += val * cotacao
        else:  # Compra
            val = (preco_ab * qtd) + taxa_ab
            target_usd[mes_abertura] -= val
            target_brl[mes_abertura] -= val * cotacao

        # FECHAMENTO: usar PTAX da data do fechamento (data efetiva do caixa)
        if op['status'] == 'fechada' and op.get('data_fechamento'):
            data_fechamento = op['data_fechamento']
            mes_fech = data_fechamento[:7]
            cotacao_fechamento = float(op.get('ptax_fechamento') or _buscar_cotacao(data_fechamento, cache_cotacoes))
            preco_fech = op.get('preco_opcao_fechamento', 0)
            taxa_fech = op.get('taxas_fechamento', 0)

            if op['operacao'] == 'Venda':
                val = (preco_fech * qtd) + taxa_fech
                target_usd[mes_fech] -= val
                target_brl[mes_fech] -= val * cotacao_fechamento
            else:  # Compra
                val = (preco_fech * qtd) - taxa_fech
                target_usd[mes_fech] += val
                target_brl[mes_fech] += val * cotacao_fechamento

    return fluxo_us_usd, fluxo_us_brl, fluxo_cripto_usd, fluxo_cripto_brl


def main():
    print("📊 Gerando Fluxo de Caixa Mensal (formato dashboard)\n")
    
    # Carregar JSONs
    with open(OPCOES_BR, 'r') as f:
        br_data = json.load(f)
    
    with open(OPCOES_US, 'r') as f:
        us_data = json.load(f)
    
    # Calcular fluxos
    print("📈 Processando Opções BR...")
    fluxo_br = calcular_fluxo_br(br_data['operacoes'])
    
    print("\n📈 Processando Opções US...")
    fluxo_us_usd, fluxo_us_brl, fluxo_cripto_usd, fluxo_cripto_brl = calcular_fluxo_us(us_data['operacoes'])
    
    # Consolidar por mês
    todos_meses = sorted(set(
        list(fluxo_br.keys()) + 
        list(fluxo_us_brl.keys()) +
        list(fluxo_cripto_brl.keys())
    ))
    
    fluxo_mensal = []
    total_br = 0
    total_us_usd = 0
    total_us_brl = 0
    total_cripto_usd = 0
    total_cripto_brl = 0
    
    for mes in todos_meses:
        br = fluxo_br.get(mes, 0)
        us_usd = fluxo_us_usd.get(mes, 0)
        us_brl = fluxo_us_brl.get(mes, 0)
        cr_usd = fluxo_cripto_usd.get(mes, 0)
        cr_brl = fluxo_cripto_brl.get(mes, 0)
        total = br + us_brl + cr_brl
        
        total_br += br
        total_us_usd += us_usd
        total_us_brl += us_brl
        total_cripto_usd += cr_usd
        total_cripto_brl += cr_brl
        
        fluxo_mensal.append({
            "mes": mes,
            "br_brl": round(br, 2),
            "us_usd": round(us_usd, 2),
            "us_brl": round(us_brl, 2),
            "cripto_usd": round(cr_usd, 2),
            "cripto_brl": round(cr_brl, 2),
            "total_brl": round(total, 2)
        })
    
    # Montar JSON FINAL (formato esperado pelo dashboard)
    output = {
        "versao": "1.1",
        "data_geracao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "descricao": "Fluxo de caixa mensal de operações de opções (BR + US + Cripto)",
        "observacao": "Valores positivos = entrada de caixa, valores negativos = saída de caixa. Cripto = ETFs IBIT e ETHA",
        "totais": {
            "br_total_brl": round(total_br, 2),
            "us_total_usd": round(total_us_usd, 2),
            "us_total_brl": round(total_us_brl, 2),
            "cripto_total_usd": round(total_cripto_usd, 2),
            "cripto_total_brl": round(total_cripto_brl, 2),
            "total_geral_brl": round(total_br + total_us_brl + total_cripto_brl, 2)
        },
        "fluxo_mensal": fluxo_mensal
    }
    
    # Salvar
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Salvo em: {OUTPUT}")
    print(f"\n📊 Totais:")
    print(f"  BR: R$ {total_br:,.2f}")
    print(f"  US: $ {total_us_usd:,.2f} = R$ {total_us_brl:,.2f}")
    print(f"  Cripto: $ {total_cripto_usd:,.2f} = R$ {total_cripto_brl:,.2f}")
    print(f"  TOTAL GERAL: R$ {total_br + total_us_brl + total_cripto_brl:,.2f}")


if __name__ == "__main__":
    main()
