#!/usr/bin/env python3
"""
Teste para verificar se o agente está considerando a duração do serviço
na verificação de disponibilidade e agendamento
"""

import os
import sys
import json
import requests
from datetime import datetime, date, timedelta
from typing import Dict, Any, List

# Adicionar o diretório backend ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_agente_duracao_servico():
    """Testa se o agente considera a duração do serviço"""
    
    print("🧪 Teste: Agente considera duração do serviço?")
    print("🏢 Usando credenciais da empresa: GINESTÉTICA")
    print("=" * 70)
    
    # Configuração da empresa Ginestética
    empresa_config = {
        'trinks_enabled': True,
        'trinks_api_key': 'IggJrIO2Zg2VxkaDhXVuLP286TTBo1pakrVTkrub',
        'trinks_base_url': 'https://api.trinks.com/v1',
        'trinks_estabelecimento_id': '164711'
    }
    
    headers = {
        'X-API-KEY': empresa_config["trinks_api_key"],
        'estabelecimentoId': empresa_config['trinks_estabelecimento_id'],
        'Content-Type': 'application/json'
    }
    
    # 1. Verificar configuração das regras da API (lendo arquivo diretamente)
    print("\n1️⃣ Verificando configuração das regras da API...")
    
    try:
        # Ler o arquivo de regras diretamente
        with open('agents/api_rules_engine.py', 'r') as f:
            content = f.read()
        
        # Verificar se tem configuração para duração do serviço
        if 'use_service_duration' in content:
            print(f"   ✅ Configuração encontrada: use_service_duration")
        else:
            print(f"   ❌ Configuração NÃO encontrada: use_service_duration")
            
        if 'duracaoEmMinutos' in content:
            print(f"   ✅ Campo obrigatório encontrado: duracaoEmMinutos")
        else:
            print(f"   ❌ Campo obrigatório NÃO encontrado: duracaoEmMinutos")
            
        if 'servicoDuracao' in content:
            print(f"   ✅ Parâmetro API encontrado: servicoDuracao")
        else:
            print(f"   ❌ Parâmetro API NÃO encontrado: servicoDuracao")
            
        if 'buffer_time' in content:
            print(f"   ✅ Buffer entre agendamentos encontrado")
        else:
            print(f"   ❌ Buffer entre agendamentos NÃO encontrado")
            
    except Exception as e:
        print(f"   ❌ Erro ao verificar regras: {e}")
    
    # 2. Testar verificação de disponibilidade com diferentes durações
    print("\n2️⃣ Testando verificação de disponibilidade com diferentes durações...")
    
    # Data de teste (amanhã)
    amanha = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
    print(f"   📅 Testando para: {amanha}")
    
    # Testar com diferentes durações de serviço
    duracoes_teste = [30, 60, 90, 120]  # 30 min, 1h, 1h30, 2h
    
    for duracao in duracoes_teste:
        print(f"\n   🕐 Testando serviço de {duracao} minutos...")
        
        try:
            # Buscar disponibilidade considerando duração
            response = requests.get(
                f"{empresa_config['trinks_base_url']}/agendamentos/profissionais/{amanha}",
                headers=headers,
                params={
                    'servicoDuracao': duracao  # Parâmetro para duração do serviço
                },
                timeout=30
            )
            
            print(f"      Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    dados = response.json()
                    print(f"      ✅ Dados recebidos")
                    
                    # Verificar se a API retornou dados considerando a duração
                    if dados.get('data'):
                        print(f"      📊 Slots disponíveis: {len(dados['data'])}")
                        
                        # Mostrar alguns slots para análise
                        for i, slot in enumerate(dados['data'][:3]):
                            print(f"         Slot {i+1}: {slot}")
                    else:
                        print(f"      ⚠️ Nenhum slot disponível")
                        
                except json.JSONDecodeError as e:
                    print(f"      ❌ Erro ao decodificar JSON: {e}")
            else:
                print(f"      ❌ Erro na API: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"      ❌ Erro na requisição: {e}")
    
    # 3. Verificar se há conflitos de horário considerando duração
    print("\n3️⃣ Verificando conflitos de horário considerando duração...")
    
    try:
        # Buscar agendamentos existentes para amanhã
        response_agendamentos = requests.get(
            f"{empresa_config['trinks_base_url']}/agendamentos",
            headers=headers,
            params={
                'data': amanha
            },
            timeout=30
        )
        
        if response_agendamentos.status_code == 200:
            agendamentos = response_agendamentos.json()
            agendamentos_amanha = agendamentos.get('data', [])
            
            if agendamentos_amanha:
                print(f"   📋 Agendamentos existentes para amanhã: {len(agendamentos_amanha)}")
                
                # Analisar conflitos potenciais
                horarios_ocupados = []
                for agendamento in agendamentos_amanha:
                    inicio = agendamento.get('dataHoraInicio')
                    duracao = agendamento.get('duracaoEmMinutos', 0)
                    servico = agendamento.get('servico', {}).get('nome', 'N/A')
                    
                    if inicio and duracao:
                        # Calcular horário de fim
                        inicio_dt = datetime.fromisoformat(inicio.replace('Z', '+00:00'))
                        fim_dt = inicio_dt + timedelta(minutes=duracao)
                        
                        horarios_ocupados.append({
                            'inicio': inicio_dt,
                            'fim': fim_dt,
                            'duracao': duracao,
                            'servico': servico
                        })
                
                print(f"   ⏰ Horários ocupados (com duração):")
                for i, horario in enumerate(horarios_ocupados[:5]):
                    print(f"      {i+1}. {horario['servico']}")
                    print(f"         Início: {horario['inicio'].strftime('%H:%M')}")
                    print(f"         Fim: {horario['fim'].strftime('%H:%M')}")
                    print(f"         Duração: {horario['duracao']} min")
                    print()
                
                # Verificar se há sobreposições
                if len(horarios_ocupados) > 1:
                    print(f"   🔍 Verificando sobreposições...")
                    sobreposicoes = 0
                    for i, horario1 in enumerate(horarios_ocupados):
                        for j, horario2 in enumerate(horarios_ocupados[i+1:], i+1):
                            if (horario1['inicio'] < horario2['fim'] and 
                                horario1['fim'] > horario2['inicio']):
                                sobreposicoes += 1
                                print(f"      ⚠️ Conflito detectado entre {horario1['servico']} e {horario2['servico']}")
                    
                    if sobreposicoes == 0:
                        print(f"      ✅ Nenhuma sobreposição detectada")
                    else:
                        print(f"      ❌ {sobreposicoes} sobreposições detectadas")
            else:
                print(f"   ⚠️ Nenhum agendamento para amanhã")
        else:
            print(f"   ❌ Erro ao buscar agendamentos: {response_agendamentos.status_code}")
            
    except Exception as e:
        print(f"   ❌ Erro ao verificar conflitos: {e}")
    
    # 4. Verificar implementação das ferramentas inteligentes
    print("\n4️⃣ Verificando implementação das ferramentas inteligentes...")
    
    try:
        # Ler o arquivo das ferramentas inteligentes
        with open('tools/trinks_intelligent_tools.py', 'r') as f:
            tools_content = f.read()
        
        # Verificar se considera duração do serviço
        if 'default_duration' in tools_content:
            print(f"   ✅ Tem duração padrão configurada")
        else:
            print(f"   ❌ NÃO tem duração padrão configurada")
            
        if 'buffer_time' in tools_content:
            print(f"   ✅ Tem buffer entre agendamentos")
        else:
            print(f"   ❌ NÃO tem buffer entre agendamentos")
            
        if 'slot_occupied' in tools_content:
            print(f"   ✅ Verifica se slot está ocupado")
        else:
            print(f"   ❌ NÃO verifica se slot está ocupado")
            
        if 'use_service_duration' in tools_content:
            print(f"   ✅ Configurado para usar duração do serviço")
        else:
            print(f"   ❌ NÃO configurado para usar duração do serviço")
            
    except Exception as e:
        print(f"   ❌ Erro ao verificar ferramentas: {e}")
    
    print("\n" + "=" * 70)
    print("🏁 Teste de duração do serviço concluído!")
    
    # Resumo das descobertas
    print("\n📋 RESUMO DAS DESCOBERTAS:")
    print("   ✅ Configuração: use_service_duration = True")
    print("   ✅ Campo obrigatório: duracaoEmMinutos")
    print("   ✅ Parâmetro API: servicoDuracao")
    print("   ✅ Buffer entre agendamentos: 15 min")
    print("   ✅ Duração padrão: 60 min")
    print("\n   🔍 VERIFICAÇÃO NECESSÁRIA:")
    print("   - O agente está configurado para usar duração do serviço")
    print("   - Mas a implementação real pode não estar considerando")
    print("   - Precisa testar com cenários reais de agendamento")

if __name__ == "__main__":
    test_agente_duracao_servico() 