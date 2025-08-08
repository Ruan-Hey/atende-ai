#!/usr/bin/env python3
"""
Teste para debugar o agente e ver como está chamando as tools
"""

import asyncio
import logging
from unittest.mock import Mock, patch
from agents.base_agent import BaseAgent

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_agent_debug():
    """Testa o agente para ver como está chamando as tools"""
    
    # Configuração de teste
    empresa_config = {
        'slug': 'tinyteams',
        'nome': 'TinyTeams',
        'empresa_id': 1,
        'prompt': 'Você é um assistente virtual da TinyTeams.',
        'openai_key': 'test-key',
        'google_calendar_client_id': None,
        'google_calendar_client_secret': None,
        'google_sheets_id': None,
        'mensagem_quebrada': False
    }
    
    print("🧪 Testando debug do agent...")
    
    try:
        # Criar agent
        agent = BaseAgent(empresa_config)
        
        print(f"✅ Agent criado com {len(agent.tools)} tools")
        
        # Listar tools
        for i, tool in enumerate(agent.tools, 1):
            print(f"   {i}. {tool.name}: {tool.description}")
        
        # Testar wrapper diretamente
        print("\n🔧 Testando wrappers diretamente...")
        
        # Teste 1: buscar_cliente
        print("\n--- Teste buscar_cliente ---")
        agent.current_context = {'cliente_id': 'test-user-123'}
        result1 = agent.tools[0].func('{"cliente_id": "test-user-123"}')
        print(f"Resultado: {result1}")
        
        # Teste 2: verificar_calendario
        print("\n--- Teste verificar_calendario ---")
        result2 = agent.tools[1].func('{"data": "2024-01-15"}')
        print(f"Resultado: {result2}")
        
        # Teste 3: fazer_reserva
        print("\n--- Teste fazer_reserva ---")
        agent.current_context = {'cliente_id': 'test-user-123', 'cliente_name': 'João'}
        result3 = agent.tools[2].func('{"data": "2024-01-15", "hora": "10:00", "cliente": "João"}')
        print(f"Resultado: {result3}")
        
        # Teste 4: enviar_mensagem
        print("\n--- Teste enviar_mensagem ---")
        result4 = agent.tools[3].func('{"mensagem": "Teste", "cliente_id": "test-user-123"}')
        print(f"Resultado: {result4}")
        
        print("\n🎯 Teste de debug concluído!")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_agent_debug()) 