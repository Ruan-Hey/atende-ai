#!/usr/bin/env python3
"""
Script de teste para forçar erro no fluxo Trinks e testar notificações
"""

import asyncio
import json
from datetime import datetime, timedelta
from agents.smart_agent import SmartAgent

async def test_trinks_error():
    """Testa erro no fluxo Trinks sem service_id"""
    
    print("🚀 Iniciando teste de erro no fluxo Trinks...")
    
    # Configuração da empresa ginestetica
    empresa_config = {
        'empresa_id': 4,
        'nome': 'ginestetica',
        'slug': 'ginestetica',
        'trinks_api_key': 'test_key',
        'trinks_base_url': 'https://api.trinks.com'
    }
    
    # Criar instância do SmartAgent
    agent = SmartAgent(empresa_config)
    
    # Simular mensagem do usuário
    user_message = "Quero agendar um horário para amanhã às 14h"
    
    print(f"📱 Mensagem do usuário: {user_message}")
    print(f"🏢 Empresa: {empresa_config['nome']}")
    
    try:
        # Processar mensagem (vai dar erro no fluxo Trinks)
        response = await agent.process_message(user_message)
        print(f"✅ Resposta: {response}")
        
    except Exception as e:
        print(f"❌ Erro capturado: {e}")
        print("🔔 Este erro deveria ter disparado uma notificação!")
        
        # Forçar erro específico do Trinks
        try:
            # Simular erro no fluxo de agendamento
            await agent._force_trinks_error()
        except Exception as trinks_error:
            print(f"🚨 Erro Trinks forçado: {trinks_error}")
    
    print("🏁 Teste concluído!")

async def test_agent_error():
    """Testa erro geral do agente"""
    
    print("\n🚀 Iniciando teste de erro geral do agente...")
    
    empresa_config = {
        'empresa_id': 4,
        'nome': 'ginestetica',
        'slug': 'ginestetica'
    }
    
    agent = SmartAgent(empresa_config)
    
    try:
        # Forçar erro no agente
        await agent._force_agent_error()
    except Exception as e:
        print(f"❌ Erro do agente: {e}")
        print("🔔 Este erro deveria ter disparado uma notificação!")

if __name__ == "__main__":
    print("🧪 TESTE DE NOTIFICAÇÕES - ERRO NO AGENTE")
    print("=" * 50)
    
    # Executar testes
    asyncio.run(test_trinks_error())
    asyncio.run(test_agent_error())
    
    print("\n🎯 Verifique os logs do backend para ver se as notificações foram disparadas!")
    print("📊 Verifique também a tabela notifications.notification_logs no banco!")
