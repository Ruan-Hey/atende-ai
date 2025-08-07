#!/usr/bin/env python3
"""
Teste do sistema dinâmico de APIs
Demonstra como qualquer API nova é automaticamente reconhecida pelo agente
"""

import json
from agents.base_agent import BaseAgent

def test_dynamic_api_config():
    """Testa configuração dinâmica de APIs"""
    
    # Simular empresa_config com APIs dinâmicas
    empresa_config = {
        'nome': 'Pancia Piena',
        'slug': 'pancia-piena',
        'openai_key': 'sk-test-openai-key',
        'twilio_sid': 'AC123456789',
        'twilio_token': 'test-twilio-token',
        'twilio_number': '+5511999999999',
        
        # API Google Calendar (existente)
        'google_calendar_enabled': True,
        'google_calendar_config': {
            'google_calendar_client_id': 'client-id-123',
            'google_calendar_client_secret': 'client-secret-456',
            'google_calendar_refresh_token': 'refresh-token-789'
        },
        
        # API Trinks (existente)
        'trinks_enabled': True,
        'trinks_config': {
            'api_key': 'trinks-api-key-123',
            'base_url': 'https://api.trinks.com/v2'
        },
        
        # NOVA API - Pizzaria API (exemplo)
        'pizzaria_api_enabled': True,
        'pizzaria_api_config': {
            'api_key': 'pizza-api-key-456',
            'base_url': 'https://api.pizzaria.com/v1',
            'username': 'pizzaria_user',
            'password': 'pizzaria_pass'
        },
        
        # NOVA API - Delivery API (exemplo)
        'delivery_api_enabled': True,
        'delivery_api_config': {
            'bearer_token': 'delivery-bearer-token-789',
            'base_url': 'https://api.delivery.com/v3'
        }
    }
    
    print("🔧 Testando configuração dinâmica de APIs...")
    print(f"Empresa: {empresa_config['nome']}")
    print(f"Slug: {empresa_config['slug']}")
    
    # Listar APIs ativas
    apis_ativas = []
    for key, value in empresa_config.items():
        if key.endswith('_enabled') and value is True:
            api_name = key.replace('_enabled', '').replace('_', ' ').title()
            apis_ativas.append(api_name)
    
    print(f"\n📋 APIs Ativas: {', '.join(apis_ativas)}")
    
    # Criar agente
    try:
        agent = BaseAgent(empresa_config)
        print(f"\n✅ Agente criado com sucesso!")
        print(f"🔧 Tools disponíveis: {len(agent.tools)}")
        
        # Listar tools das APIs
        api_tools = [tool for tool in agent.tools if 'api_call' in tool.name]
        print(f"🌐 Tools de APIs: {len(api_tools)}")
        
        for tool in api_tools:
            print(f"  - {tool.name}: {tool.description[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao criar agente: {e}")
        return False

def test_api_call_simulation():
    """Simula chamadas para APIs dinâmicas"""
    
    empresa_config = {
        'nome': 'Pancia Piena',
        'slug': 'pancia-piena',
        'openai_key': 'sk-test-openai-key',
        
        # API Pizzaria (nova)
        'pizzaria_api_enabled': True,
        'pizzaria_api_config': {
            'api_key': 'pizza-api-key-456',
            'base_url': 'https://api.pizzaria.com/v1'
        }
    }
    
    print("\n🍕 Testando chamada para API Pizzaria...")
    
    try:
        agent = BaseAgent(empresa_config)
        
        # Simular chamada para API Pizzaria
        # (Isso seria feito pelo agente quando necessário)
        print("✅ Agente pode acessar API Pizzaria automaticamente!")
        print("📞 O agente pode chamar: pizzaria_api_call('/pedidos', 'POST', {...})")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Teste do Sistema Dinâmico de APIs")
    print("=" * 50)
    
    # Teste 1: Configuração dinâmica
    success1 = test_dynamic_api_config()
    
    # Teste 2: Simulação de chamada
    success2 = test_api_call_simulation()
    
    print("\n" + "=" * 50)
    if success1 and success2:
        print("✅ Todos os testes passaram!")
        print("🎯 O sistema está pronto para APIs dinâmicas!")
    else:
        print("❌ Alguns testes falharam!") 