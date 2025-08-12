#!/usr/bin/env python3
"""
Teste para identificar EXATAMENTE quais serviços a Dra. Amabile realmente realiza
Baseado nos agendamentos reais, não apenas na lista geral de serviços
"""

import os
import sys
import json
import requests
from datetime import datetime, date
from typing import Dict, Any, List
from collections import defaultdict

# Adicionar o diretório backend ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_servicos_reais_amabile():
    """Testa para identificar exatamente quais serviços a Dra. Amabile realmente realiza"""
    
    print("🧪 Teste para identificar EXATAMENTE os serviços da Dra. Amabile")
    print("🏢 Usando credenciais da empresa: GINESTÉTICA")
    print("=" * 80)
    
    # Configuração da empresa Ginestética (credenciais reais do banco)
    empresa_config = {
        'trinks_enabled': True,
        'trinks_api_key': 'IggJrIO2Zg2VxkaDhXVuLP286TTBo1pakrVTkrub',
        'trinks_base_url': 'https://api.trinks.com/v1',
        'trinks_estabelecimento_id': '164711'
    }
    
    print(f"🔑 API Key: {empresa_config['trinks_api_key'][:10]}...")
    print(f"🏢 Estabelecimento ID: {empresa_config['trinks_estabelecimento_id']}")
    print(f"🌐 Base URL: {empresa_config['trinks_base_url']}")
    
    # Headers padrão
    headers = {
        'X-API-KEY': empresa_config["trinks_api_key"],
        'estabelecimentoId': empresa_config['trinks_estabelecimento_id'],
        'Content-Type': 'application/json'
    }
    
    # 1. Primeiro, buscar a Dra. Amabile
    print("\n1️⃣ Buscando a Dra. Amabile...")
    try:
        response_prof = requests.get(
            f"{empresa_config['trinks_base_url']}/profissionais",
            headers=headers,
            timeout=30
        )
        
        if response_prof.status_code == 200:
            profissionais = response_prof.json()
            dra_amabile = None
            
            for prof in profissionais.get('data', []):
                nome = prof.get('nome', '').lower()
                if 'amabile' in nome or 'dra' in nome or 'doutora' in nome:
                    dra_amabile = prof
                    break
            
            if dra_amabile:
                print(f"   🎯 Dra. Amabile encontrada!")
                print(f"      ID: {dra_amabile.get('id')}")
                print(f"      Nome: {dra_amabile.get('nome')}")
                print(f"      Especialidade: {dra_amabile.get('especialidade', 'N/A')}")
                
                # 2. Buscar TODOS os agendamentos da Dra. Amabile (sem filtro de data)
                print(f"\n2️⃣ Buscando TODOS os agendamentos da Dra. Amabile...")
                
                response_agendamentos = requests.get(
                    f"{empresa_config['trinks_base_url']}/agendamentos",
                    headers=headers,
                    params={
                        'profissionalId': dra_amabile.get('id')
                    },
                    timeout=30
                )
                
                print(f"   Status: {response_agendamentos.status_code}")
                
                if response_agendamentos.status_code == 200:
                    try:
                        agendamentos = response_agendamentos.json()
                        agendamentos_data = agendamentos.get('data', [])
                        
                        if agendamentos_data:
                            print(f"   ✅ Encontrados {len(agendamentos_data)} agendamentos da Dra. Amabile")
                            
                            # 3. Analisar EXATAMENTE quais serviços ela realiza
                            print(f"\n3️⃣ Analisando serviços REALMENTE realizados pela Dra. Amabile...")
                            
                            # Agrupar por serviço
                            servicos_reais = defaultdict(lambda: {
                                'count': 0,
                                'valor_total': 0,
                                'duracao_total': 0,
                                'categoria': '',
                                'descricao': '',
                                'exemplos_clientes': [],
                                'datas': []
                            })
                            
                            for agendamento in agendamentos_data:
                                servico = agendamento.get('servico', {})
                                servico_nome = servico.get('nome', 'Serviço não identificado')
                                servico_id = servico.get('id', 'N/A')
                                
                                # Adicionar dados do serviço
                                servicos_reais[servico_nome]['count'] += 1
                                servicos_reais[servico_nome]['valor_total'] += agendamento.get('valor', 0)
                                servicos_reais[servico_nome]['duracao_total'] += agendamento.get('duracaoEmMinutos', 0)
                                servicos_reais[servico_nome]['categoria'] = servico.get('categoria', 'N/A')
                                servicos_reais[servico_nome]['descricao'] = servico.get('descricao', 'N/A')
                                
                                # Adicionar exemplo de cliente
                                cliente_nome = agendamento.get('cliente', {}).get('nome', 'N/A')
                                data_agendamento = agendamento.get('dataHoraInicio', 'N/A')[:10]
                                status = agendamento.get('status', {}).get('nome', 'N/A')
                                
                                if len(servicos_reais[servico_nome]['exemplos_clientes']) < 3:
                                    servicos_reais[servico_nome]['exemplos_clientes'].append({
                                        'nome': cliente_nome,
                                        'data': data_agendamento,
                                        'status': status
                                    })
                                
                                # Adicionar data
                                if data_agendamento not in servicos_reais[servico_nome]['datas']:
                                    servicos_reais[servico_nome]['datas'].append(data_agendamento)
                            
                            # Mostrar resultados organizados
                            print(f"\n   📊 SERVIÇOS REALMENTE REALIZADOS pela Dra. Amabile:")
                            print(f"   Total de tipos de serviços: {len(servicos_reais)}")
                            
                            # Ordenar por quantidade de agendamentos
                            servicos_ordenados = sorted(servicos_reais.items(), 
                                                      key=lambda x: x[1]['count'], reverse=True)
                            
                            for i, (servico_nome, dados) in enumerate(servicos_ordenados, 1):
                                print(f"\n   {i:2d}. 🎯 {servico_nome}")
                                print(f"       ID do Serviço: {servico_id}")
                                print(f"       Categoria: {dados['categoria']}")
                                print(f"       Total de agendamentos: {dados['count']}")
                                print(f"       Valor total: R$ {dados['valor_total']:.2f}")
                                print(f"       Duração total: {dados['duracao_total']} min")
                                print(f"       Valor médio: R$ {(dados['valor_total'] / dados['count']):.2f}")
                                print(f"       Duração média: {dados['duracao_total'] / dados['count']:.1f} min")
                                print(f"       Período: {min(dados['datas'])} a {max(dados['datas'])}")
                                print(f"       Exemplos de clientes:")
                                for exemplo in dados['exemplos_clientes']:
                                    print(f"          - {exemplo['nome']} ({exemplo['data']}) - {exemplo['status']}")
                                
                                if dados['descricao'] and dados['descricao'] != 'sem descrição':
                                    print(f"       Descrição: {dados['descricao']}")
                            
                            # 4. Verificar se há serviços que ela NÃO realiza
                            print(f"\n4️⃣ Verificando serviços que ela NÃO realiza...")
                            
                            # Buscar todos os serviços do estabelecimento
                            response_todos_servicos = requests.get(
                                f"{empresa_config['trinks_base_url']}/servicos",
                                headers=headers,
                                timeout=30
                            )
                            
                            if response_todos_servicos.status_code == 200:
                                todos_servicos = response_todos_servicos.json()
                                servicos_estabelecimento = [s.get('nome') for s in todos_servicos.get('data', [])]
                                
                                servicos_nao_realizados = [s for s in servicos_estabelecimento if s not in servicos_reais.keys()]
                                
                                print(f"   📋 Total de serviços no estabelecimento: {len(servicos_estabelecimento)}")
                                print(f"   ✅ Serviços que a Dra. Amabile REALIZA: {len(servicos_reais)}")
                                print(f"   ❌ Serviços que a Dra. Amabile NÃO realiza: {len(servicos_nao_realizados)}")
                                
                                if servicos_nao_realizados:
                                    print(f"\n   🚫 Exemplos de serviços que ela NÃO realiza:")
                                    for i, servico in enumerate(servicos_nao_realizados[:10], 1):
                                        print(f"      {i}. {servico}")
                                    if len(servicos_nao_realizados) > 10:
                                        print(f"      ... e mais {len(servicos_nao_realizados) - 10} serviços")
                            
                        else:
                            print(f"   ⚠️ Nenhum agendamento encontrado para a Dra. Amabile")
                            
                    except json.JSONDecodeError as e:
                        print(f"   ❌ Erro ao decodificar JSON: {e}")
                else:
                    print(f"   ❌ Erro na busca de agendamentos: {response_agendamentos.status_code}")
                    
            else:
                print(f"   ❌ Dra. Amabile não encontrada")
        else:
            print(f"   ❌ Erro ao buscar profissionais: {response_prof.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Erro na requisição: {e}")
    
    print("\n" + "=" * 80)
    print("🏁 Teste de serviços reais concluído!")
    
    # Resumo das credenciais usadas
    print("\n📋 Credenciais utilizadas (empresa Ginestética):")
    print(f"   API Key: {empresa_config['trinks_api_key']}")
    print(f"   Estabelecimento ID: {empresa_config['trinks_estabelecimento_id']}")
    print(f"   Base URL: {empresa_config['trinks_base_url']}")

if __name__ == "__main__":
    test_servicos_reais_amabile() 