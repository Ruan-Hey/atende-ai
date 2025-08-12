#!/usr/bin/env python3
"""
Teste para buscar diretamente na API da Trinks os serviços realizados pela Dra. Amabile
"""

import os
import sys
import json
import requests
from datetime import datetime, date
from typing import Dict, Any, List

# Adicionar o diretório backend ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_trinks_servicos_amabile():
    """Testa a busca de serviços realizados pela Dra. Amabile na API da Trinks"""
    
    print("🧪 Testando busca de serviços da Dra. Amabile na API da Trinks")
    print("🏢 Usando credenciais da empresa: GINESTÉTICA")
    print("=" * 70)
    
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
    
    # 1. Buscar todos os serviços disponíveis no estabelecimento
    print("\n1️⃣ Buscando todos os serviços disponíveis no estabelecimento...")
    try:
        response = requests.get(
            f"{empresa_config['trinks_base_url']}/servicos",
            headers=headers,
            timeout=30
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                servicos = response.json()
                print(f"   ✅ Sucesso! Encontrados {len(servicos.get('data', []))} serviços")
                
                # Mostrar estrutura dos dados
                if isinstance(servicos, dict):
                    print(f"   📊 Estrutura da resposta:")
                    for key, value in servicos.items():
                        if isinstance(value, list):
                            print(f"      {key}: {len(value)} itens")
                        else:
                            print(f"      {key}: {value}")
                
                # Listar todos os serviços
                if servicos.get('data'):
                    print(f"\n   📋 Lista completa de serviços disponíveis:")
                    for i, servico in enumerate(servicos['data'], 1):
                        print(f"      {i:2d}. {servico.get('nome', 'N/A')}")
                        print(f"          ID: {servico.get('id', 'N/A')}")
                        print(f"          Categoria: {servico.get('categoria', 'N/A')}")
                        print(f"          Duração: {servico.get('duracaoEmMinutos', 'N/A')} min")
                        print(f"          Valor: R$ {servico.get('valor', 'N/A')}")
                        print(f"          Ativo: {servico.get('ativo', 'N/A')}")
                        print()
                
            except json.JSONDecodeError as e:
                print(f"   ❌ Erro ao decodificar JSON: {e}")
                print(f"   Resposta bruta: {response.text[:500]}")
        else:
            print(f"   ❌ Erro na API: {response.status_code}")
            print(f"   Resposta: {response.text[:500]}")
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Erro na requisição: {e}")
    
    # 2. Buscar serviços específicos da Dra. Amabile
    print("\n2️⃣ Buscando serviços específicos realizados pela Dra. Amabile...")
    try:
        # Primeiro, buscar a Dra. Amabile
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
                
                # Buscar serviços específicos da Dra. Amabile
                print(f"\n   🔍 Buscando serviços realizados pela Dra. Amabile...")
                
                # Tentar buscar serviços por profissional
                response_servicos_amabile = requests.get(
                    f"{empresa_config['trinks_base_url']}/servicos",
                    headers=headers,
                    params={
                        'profissionalId': dra_amabile.get('id')
                    },
                    timeout=30
                )
                
                print(f"      Status: {response_servicos_amabile.status_code}")
                
                if response_servicos_amabile.status_code == 200:
                    try:
                        servicos_amabile = response_servicos_amabile.json()
                        servicos_data = servicos_amabile.get('data', [])
                        
                        if servicos_data:
                            print(f"      ✅ Encontrados {len(servicos_data)} serviços da Dra. Amabile")
                            
                            print(f"\n      📋 Serviços realizados pela Dra. Amabile:")
                            for i, servico in enumerate(servicos_data, 1):
                                print(f"\n         {i}. {servico.get('nome', 'N/A')}")
                                print(f"            ID: {servico.get('id', 'N/A')}")
                                print(f"            Categoria: {servico.get('categoria', 'N/A')}")
                                print(f"            Duração: {servico.get('duracaoEmMinutos', 'N/A')} min")
                                print(f"            Valor: R$ {servico.get('valor', 'N/A')}")
                                print(f"            Descrição: {servico.get('descricao', 'N/A')}")
                                print(f"            Ativo: {servico.get('ativo', 'N/A')}")
                        else:
                            print(f"      ⚠️ Nenhum serviço específico encontrado para a Dra. Amabile")
                            
                    except json.JSONDecodeError as e:
                        print(f"      ❌ Erro ao decodificar JSON: {e}")
                else:
                    print(f"      ❌ Erro na busca de serviços: {response_servicos_amabile.status_code}")
                    
            else:
                print(f"   ❌ Dra. Amabile não encontrada")
        else:
            print(f"   ❌ Erro ao buscar profissionais: {response_prof.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Erro na requisição: {e}")
    
    # 3. Buscar histórico de serviços realizados pela Dra. Amabile
    print("\n3️⃣ Buscando histórico de serviços realizados pela Dra. Amabile...")
    try:
        # Buscar agendamentos da Dra. Amabile para ver histórico
        response_historico = requests.get(
            f"{empresa_config['trinks_base_url']}/agendamentos",
            headers=headers,
            params={
                'profissionalId': dra_amabile.get('id') if dra_amabile else None
            },
            timeout=30
        )
        
        print(f"   Status: {response_historico.status_code}")
        
        if response_historico.status_code == 200:
            try:
                historico = response_historico.json()
                agendamentos = historico.get('data', [])
                
                if agendamentos:
                    print(f"   ✅ Encontrados {len(agendamentos)} agendamentos da Dra. Amabile")
                    
                    # Agrupar por tipo de serviço
                    servicos_realizados = {}
                    for agendamento in agendamentos:
                        servico = agendamento.get('servico', {})
                        servico_nome = servico.get('nome', 'Serviço não identificado')
                        
                        if servico_nome not in servicos_realizados:
                            servicos_realizados[servico_nome] = {
                                'count': 0,
                                'valor_total': 0,
                                'duracao_total': 0,
                                'exemplos': []
                            }
                        
                        servicos_realizados[servico_nome]['count'] += 1
                        servicos_realizados[servico_nome]['valor_total'] += agendamento.get('valor', 0)
                        servicos_realizados[servico_nome]['duracao_total'] += agendamento.get('duracaoEmMinutos', 0)
                        
                        # Guardar exemplo de agendamento
                        if len(servicos_realizados[servico_nome]['exemplos']) < 3:
                            servicos_realizados[servico_nome]['exemplos'].append({
                                'cliente': agendamento.get('cliente', {}).get('nome', 'N/A'),
                                'data': agendamento.get('dataHoraInicio', 'N/A'),
                                'status': agendamento.get('status', {}).get('nome', 'N/A')
                            })
                    
                    print(f"\n   📊 Resumo dos serviços realizados pela Dra. Amabile:")
                    for servico_nome, dados in servicos_realizados.items():
                        print(f"\n      🎯 {servico_nome}")
                        print(f"         Total de agendamentos: {dados['count']}")
                        print(f"         Valor total: R$ {dados['valor_total']:.2f}")
                        print(f"         Duração total: {dados['duracao_total']} min")
                        print(f"         Valor médio: R$ {(dados['valor_total'] / dados['count']):.2f}")
                        print(f"         Duração média: {dados['duracao_total'] / dados['count']:.1f} min")
                        print(f"         Exemplos de clientes:")
                        for exemplo in dados['exemplos']:
                            print(f"            - {exemplo['cliente']} ({exemplo['data'][:10]}) - {exemplo['status']}")
                
            except json.JSONDecodeError as e:
                print(f"   ❌ Erro ao decodificar JSON: {e}")
        else:
            print(f"   ❌ Erro na busca de histórico: {response_historico.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Erro na requisição: {e}")
    
    print("\n" + "=" * 70)
    print("🏁 Teste de serviços concluído!")
    
    # Resumo das credenciais usadas
    print("\n📋 Credenciais utilizadas (empresa Ginestética):")
    print(f"   API Key: {empresa_config['trinks_api_key']}")
    print(f"   Estabelecimento ID: {empresa_config['trinks_estabelecimento_id']}")
    print(f"   Base URL: {empresa_config['trinks_base_url']}")

if __name__ == "__main__":
    test_trinks_servicos_amabile() 