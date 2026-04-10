#!/usr/bin/env python3
import json
import sys

# Carregar arquivo
with open('opcoes_intl.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Encontrar a operação SPY CALL 693 aberta para fechar
found = False
for i, op in enumerate(data['operacoes']):
    if (op['ticker'] == 'SPY' and op.get('status') == 'aberta' and 
        op['strike'] == 693.0 and op['vencimento'] == '2026-04-17'):
        
        print(f"Encontrada operação para fechar (índice {i}):")
        print(f"  Aberta em: {op['data_operacao']}")
        print(f"  Preço abertura: {op['preco_opcao_abertura']}")
        print(f"  Taxas abertura: {op['taxas_abertura']}")
        
        # Atualizar com fechamento
        op['data_fechamento'] = '2026-04-07'
        op['preco_acao_fechamento'] = 656.0
        op['preco_opcao_fechamento'] = 0.18
        op['taxas_fechamento'] = 0.12
        op['taxas_total'] = op['taxas_abertura'] + 0.12
        
        # Calcular resultado
        # Receita: preco_opcao_abertura × quantidade (preço por ação)
        # Despesa: preco_opcao_fechamento × quantidade + taxas_total
        receita = op['preco_opcao_abertura'] * op['quantidade']  # já é por ação
        despesa = op['preco_opcao_fechamento'] * op['quantidade'] + op['taxas_total']
        op['resultado'] = receita - despesa
        
        op['status'] = 'fechada'
        
        print(f"  Fechamento registrado:")
        print(f"    Data: {op['data_fechamento']}")
        print(f"    Preço ação fechamento: {op['preco_acao_fechamento']}")
        print(f"    Preço opção fechamento: {op['preco_opcao_fechamento']}")
        print(f"    Taxas fechamento: {op['taxas_fechamento']}")
        print(f"    Taxas total: {op['taxas_total']}")
        print(f"    Resultado: {op['resultado']:.2f}")
        
        found = True
        break

if not found:
    print("ERRO: Operação SPY CALL 693 aberta não encontrada!")
    sys.exit(1)

# Adicionar nova operação SPY CALL 688
nova_operacao = {
    "ticker": "SPY",
    "data_operacao": "2026-04-07",
    "preco_acao_na_operacao": 656.0,
    "operacao": "Venda",
    "tipo_contrato": "CALL",
    "vencimento": "2026-05-15",
    "strike": 688.0,
    "quantidade": 100,
    "preco_opcao_abertura": 4.41,  # por ação
    "data_fechamento": None,
    "preco_acao_fechamento": None,
    "preco_opcao_fechamento": None,
    "taxas_abertura": 1.13,  # $1,00 commission + $0,13 fees
    "taxas_fechamento": None,
    "taxas_total": 1.13,
    "resultado": None,
    "status": "aberta",
    "ptax_abertura": 5.15
}

data['operacoes'].append(nova_operacao)
print(f"\nNova operação adicionada:")
print(f"  SPY CALL 688 exp 2026-05-15")
print(f"  Preço abertura: {nova_operacao['preco_opcao_abertura']} (por ação)")
print(f"  Taxas abertura: {nova_operacao['taxas_abertura']}")
print(f"  PTAX: {nova_operacao['ptax_abertura']}")

# Atualizar estatísticas
total_ops = len(data['operacoes'])
abertas = sum(1 for op in data['operacoes'] if op.get('status') == 'aberta')
fechadas = total_ops - abertas

# Contar vitórias/derrotas
vitorias = sum(1 for op in data['operacoes'] if op.get('resultado') is not None and op['resultado'] > 0)
derrotas = sum(1 for op in data['operacoes'] if op.get('resultado') is not None and op['resultado'] < 0)

# Resultado total realizado (apenas fechadas)
resultado_total = sum(op['resultado'] for op in data['operacoes'] if op.get('status') == 'fechada' and op.get('resultado') is not None)

data['estatisticas'] = {
    "total_operacoes": total_ops,
    "operacoes_fechadas": fechadas,
    "operacoes_abertas": abertas,
    "resultado_total_realizado_usd": round(resultado_total, 2),
    "vitorias": vitorias,
    "derrotas": derrotas,
    "win_rate_percentual": round((vitorias / (vitorias + derrotas) * 100) if (vitorias + derrotas) > 0 else 0, 1)
}

data['data_atualizacao'] = '2026-04-07'

print(f"\nEstatísticas atualizadas:")
print(f"  Total operações: {total_ops}")
print(f"  Abertas: {abertas}")
print(f"  Fechadas: {fechadas}")
print(f"  Resultado total: ${resultado_total:.2f}")
print(f"  Vitórias: {vitorias}, Derrotas: {derrotas}")
print(f"  Win Rate: {data['estatisticas']['win_rate_percentual']}%")

# Salvar backup
with open('opcoes_intl.json.backup_pre_update', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

# Salvar arquivo atualizado
with open('opcoes_intl.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("\n✅ Arquivo atualizado com sucesso!")