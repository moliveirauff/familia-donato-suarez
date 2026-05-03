#!/usr/bin/env python3
import json
from collections import defaultdict
from datetime import datetime

def carregar_operacoes(caminho):
    with open(caminho, 'r', encoding='utf-8') as f:
        return json.load(f)

def processar_opcoes_us():
    print("=== FLUXO DE CAIXA POR ATIVO - ABRIL 2026 (OPÇÕES US) ===\n")
    
    dados = carregar_operacoes('opcoes_intl.json')
    
    # Filtrar operações de abril/2026
    operacoes_abril = []
    for op in dados['operacoes']:
        if not op.get('data_operacao'):
            continue
        if op['data_operacao'].startswith('2026-04'):
            operacoes_abril.append(op)
    
    print(f"Total de operações US em abril/2026: {len(operacoes_abril)}")
    
    # Agrupar por ticker
    fluxo_por_ativo = defaultdict(lambda: {'entrada_usd': 0, 'saida_usd': 0, 'net_usd': 0})
    
    for op in operacoes_abril:
        ticker = op['ticker']
        quantidade = op['quantidade']
        preco_abertura = op['preco_opcao_abertura']
        taxas_abertura = op.get('taxas_abertura', 0) or 0
        
        # Determinar se é entrada (+) ou saída (-)
        # VENDA = entrada de caixa (+), COMPRA = saída de caixa (-)
        if op['operacao'] == 'Venda':
            # Entrada: prêmio recebido menos taxas
            valor = preco_abertura * quantidade
            fluxo_por_ativo[ticker]['entrada_usd'] += valor
            fluxo_por_ativo[ticker]['saida_usd'] += taxas_abertura  # taxas são saída
        else:  # Compra
            # Saída: prêmio pago mais taxas
            valor = preco_abertura * quantidade
            fluxo_por_ativo[ticker]['saida_usd'] += valor + taxas_abertura
        
        # Se houver fechamento em abril
        if op.get('data_fechamento') and op['data_fechamento'].startswith('2026-04'):
            preco_fechamento = op.get('preco_opcao_fechamento') or 0
            taxas_fechamento = op.get('taxas_fechamento', 0) or 0
            
            # Inverter lógica: fechamento de VENDA = saída, fechamento de COMPRA = entrada
            if op['operacao'] == 'Venda':
                # Fechar venda: pagar para recomprar = saída
                valor_fechamento = preco_fechamento * quantidade
                fluxo_por_ativo[ticker]['saida_usd'] += valor_fechamento + taxas_fechamento
            else:  # Compra
                # Fechar compra: vender = entrada
                valor_fechamento = preco_fechamento * quantidade
                fluxo_por_ativo[ticker]['entrada_usd'] += valor_fechamento
                fluxo_por_ativo[ticker]['saida_usd'] += taxas_fechamento
    
    # Calcular net e converter para BRL (usar PTAX de abertura ou 5.15 como default)
    ptax_abril = 5.15  # aproximação
    
    resultados = []
    for ticker, fluxo in fluxo_por_ativo.items():
        net_usd = fluxo['entrada_usd'] - fluxo['saida_usd']
        net_brl = net_usd * ptax_abril
        fluxo['net_usd'] = net_usd
        fluxo['net_brl'] = net_brl
        resultados.append((ticker, fluxo))
    
    # Ordenar por maior net BRL
    resultados.sort(key=lambda x: x[1]['net_brl'], reverse=True)
    
    print(f"{'Ativo':<10} {'Entrada USD':>12} {'Saída USD':>12} {'Net USD':>12} {'Net BRL':>12}")
    print("-" * 60)
    
    total_entrada_usd = 0
    total_saida_usd = 0
    total_net_usd = 0
    total_net_brl = 0
    
    for ticker, fluxo in resultados:
        if fluxo['entrada_usd'] == 0 and fluxo['saida_usd'] == 0:
            continue
        print(f"{ticker:<10} {fluxo['entrada_usd']:>12.2f} {fluxo['saida_usd']:>12.2f} {fluxo['net_usd']:>12.2f} {fluxo['net_brl']:>12.2f}")
        total_entrada_usd += fluxo['entrada_usd']
        total_saida_usd += fluxo['saida_usd']
        total_net_usd += fluxo['net_usd']
        total_net_brl += fluxo['net_brl']
    
    print("-" * 60)
    print(f"{'TOTAL':<10} {total_entrada_usd:>12.2f} {total_saida_usd:>12.2f} {total_net_usd:>12.2f} {total_net_brl:>12.2f}")
    
    # Mostrar operações individuais
    print("\n=== DETALHES DAS OPERAÇÕES ABRIL/2026 ===")
    for op in operacoes_abril:
        status = op.get('status', 'N/A')
        fechamento = f", Fechamento: {op.get('data_fechamento')}" if op.get('data_fechamento') else ""
        print(f"{op['data_operacao']} - {op['ticker']} {op['operacao']} {op['tipo_contrato']} {op['strike']} "
              f"exp {op['vencimento']}, Qtd: {op['quantidade']}, Preço: {op['preco_opcao_abertura']}, "
              f"Status: {status}{fechamento}")

def main():
    processar_opcoes_us()
    # Poderia adicionar processamento de opções BR aqui

if __name__ == '__main__':
    main()