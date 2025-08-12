#!/usr/bin/env python3
"""
Teste para buscar agendamentos de hoje da Dra. Amabile na API da Trinks
Usando credenciais reais da empresa Ginestética
"""

import os
import sys
import json
import requests
from datetime import datetime, date
from typing import Dict, Any, List

# Adicionar o diretório backend ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_trinks_agendamentos_hoje():
    """Testa a busca de agendamentos de hoje na API da Trinks"""
    
    print("🧪 Testando busca de agendamentos de hoje na API da Trinks")
    print("🏢 Usando credenciais da empresa: GINESTÉTICA")
    print("=" * 60)
    
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
    
    # Data de hoje
    hoje = date.today().strftime('%Y-%m-%d')
    print(f"\n📅 Buscando agendamentos para: {hoje}")
    
    # 1. Testar endpoint de listar agendamentos
    print("\n1️⃣ Testando endpoint /agendamentos...")
    try:
        headers = {
            'X-API-KEY': empresa_config["trinks_api_key"],  # Trinks usa X-API-KEY
            'estabelecimentoId': empresa_config['trinks_estabelecimento_id'],
            'Content-Type': 'application/json'
        }
        
        # Buscar todos os agendamentos
        response = requests.get(
            f"{empresa_config['trinks_base_url']}/agendamentos",
            headers=headers,
            timeout=30
        )
        
        print(f"   Status: {response.status_code}")
        print(f"   Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                agendamentos = response.json()
                print(f"   ✅ Sucesso! Encontrados {len(agendamentos.get('data', []))} agendamentos")
                
                # Filtrar agendamentos de hoje
                agendamentos_hoje = []
                for agendamento in agendamentos.get('data', []):
                    if 'dataHoraInicio' in agendamento:
                        data_agendamento = agendamento['dataHoraInicio'][:10]  # YYYY-MM-DD
                        if data_agendamento == hoje:
                            agendamentos_hoje.append(agendamento)
                
                print(f"   📋 Agendamentos de hoje: {len(agendamentos_hoje)}")
                
                # Mostrar detalhes dos agendamentos de hoje
                for i, agendamento in enumerate(agendamentos_hoje, 1):
                    print(f"\n   📝 Agendamento {i}:")
                    print(f"      ID: {agendamento.get('id', 'N/A')}")
                    print(f"      Cliente: {agendamento.get('cliente', {}).get('nome', 'N/A')}")
                    print(f"      Serviço: {agendamento.get('servico', {}).get('nome', 'N/A')}")
                    print(f"      Profissional: {agendamento.get('profissional', {}).get('nome', 'N/A')}")
                    print(f"      Horário: {agendamento.get('dataHoraInicio', 'N/A')}")
                    print(f"      Duração: {agendamento.get('duracaoEmMinutos', 'N/A')} min")
                    print(f"      Status: {agendamento.get('status', 'N/A')}")
                    print(f"      Valor: R$ {agendamento.get('valor', 'N/A')}")
                
            except json.JSONDecodeError as e:
                print(f"   ❌ Erro ao decodificar JSON: {e}")
                print(f"   Resposta bruta: {response.text[:500]}")
        else:
            print(f"   ❌ Erro na API: {response.status_code}")
            print(f"   Resposta: {response.text[:500]}")
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Erro na requisição: {e}")
    
    # 2. Testar endpoint específico para profissionais em uma data
    print(f"\n2️⃣ Testando endpoint /agendamentos/profissionais/{hoje}...")
    try:
        headers = {
            'X-API-KEY': empresa_config["trinks_api_key"],
            'estabelecimentoId': empresa_config['trinks_estabelecimento_id'],
            'Content-Type': 'application/json'
        }
        
        response = requests.get(
            f"{empresa_config['trinks_base_url']}/agendamentos/profissionais/{hoje}",
            headers=headers,
            timeout=30
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                dados = response.json()
                print(f"   ✅ Sucesso! Dados recebidos")
                print(f"   Estrutura: {list(dados.keys()) if isinstance(dados, dict) else 'Lista'}")
                
                # Mostrar estrutura dos dados
                if isinstance(dados, dict):
                    for key, value in dados.items():
                        if isinstance(value, list):
                            print(f"   {key}: {len(value)} itens")
                        else:
                            print(f"   {key}: {value}")
                elif isinstance(dados, list):
                    print(f"   Lista com {len(dados)} itens")
                    if dados:
                        print(f"   Primeiro item: {list(dados[0].keys()) if isinstance(dados[0], dict) else dados[0]}")
                
            except json.JSONDecodeError as e:
                print(f"   ❌ Erro ao decodificar JSON: {e}")
                print(f"   Resposta bruta: {response.text[:500]}")
        else:
            print(f"   ❌ Erro na API: {response.status_code}")
            print(f"   Resposta: {response.text[:500]}")
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Erro na requisição: {e}")
    
    # 3. Testar busca específica por profissional (Dra. Amabile)
    print(f"\n3️⃣ Testando busca por profissional 'Dra. Amabile'...")
    try:
        # Primeiro, buscar profissionais
        headers = {
            'X-API-KEY': empresa_config["trinks_api_key"],
            'estabelecimentoId': empresa_config['trinks_estabelecimento_id'],
            'Content-Type': 'application/json'
        }
        
        response = requests.get(
            f"{empresa_config['trinks_base_url']}/profissionais",
            headers=headers,
            timeout=30
        )
        
        print(f"   Status busca profissionais: {response.status_code}")
        
        if response.status_code == 200:
            try:
                profissionais = response.json()
                print(f"   ✅ Encontrados {len(profissionais.get('data', []))} profissionais")
                
                # Procurar pela Dra. Amabile
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
                    
                    # Buscar agendamentos específicos da Dra. Amabile para hoje
                    print(f"\n   📅 Buscando agendamentos da Dra. Amabile para hoje...")
                    
                    # Tentar endpoint com filtro por profissional
                    response_agendamentos = requests.get(
                        f"{empresa_config['trinks_base_url']}/agendamentos",
                        headers=headers,
                        params={
                            'profissionalId': dra_amabile.get('id'),
                            'data': hoje
                        },
                        timeout=30
                    )
                    
                    print(f"      Status: {response_agendamentos.status_code}")
                    
                    if response_agendamentos.status_code == 200:
                        try:
                            agendamentos_amabile = response_agendamentos.json()
                            agendamentos_hoje_amabile = agendamentos_amabile.get('data', [])
                            
                            print(f"      ✅ Encontrados {len(agendamentos_hoje_amabile)} agendamentos da Dra. Amabile para hoje")
                            
                            for i, agendamento in enumerate(agendamentos_hoje_amabile, 1):
                                print(f"\n      📝 Agendamento {i}:")
                                print(f"         Cliente: {agendamento.get('cliente', {}).get('nome', 'N/A')}")
                                print(f"         Serviço: {agendamento.get('servico', {}).get('nome', 'N/A')}")
                                print(f"         Horário: {agendamento.get('dataHoraInicio', 'N/A')}")
                                print(f"         Duração: {agendamento.get('duracaoEmMinutos', 'N/A')} min")
                                print(f"         Status: {agendamento.get('status', 'N/A')}")
                                
                        except json.JSONDecodeError as e:
                            print(f"      ❌ Erro ao decodificar JSON: {e}")
                    else:
                        print(f"      ❌ Erro na busca: {response_agendamentos.status_code}")
                        
                else:
                    print(f"   ❌ Dra. Amabile não encontrada na lista de profissionais")
                    print(f"   Profissionais disponíveis:")
                    for prof in profissionais.get('data', [])[:5]:  # Mostrar apenas os primeiros 5
                        print(f"      - {prof.get('nome', 'N/A')}")
                
            except json.JSONDecodeError as e:
                print(f"   ❌ Erro ao decodificar JSON: {e}")
        else:
            print(f"   ❌ Erro na busca de profissionais: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Erro na requisição: {e}")
    
    print("\n" + "=" * 60)
    print("🏁 Teste concluído!")
    
    # Resumo das credenciais usadas
    print("\n📋 Credenciais utilizadas (empresa Ginestética):")
    print(f"   API Key: {empresa_config['trinks_api_key']}")
    print(f"   Estabelecimento ID: {empresa_config['trinks_estabelecimento_id']}")
    print(f"   Base URL: {empresa_config['trinks_base_url']}")

if __name__ == "__main__":
    test_trinks_agendamentos_hoje() 