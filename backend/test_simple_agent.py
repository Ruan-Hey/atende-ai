#!/usr/bin/env python3
"""
Teste simples do agent para verificar se as tools estão sendo carregadas
"""

import asyncio
import logging
from agents.base_agent import BaseAgent

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_simple_agent():
    """Testa se o agent está sendo inicializado corretamente"""
    
    # Configuração de teste
    empresa_config = {
        'slug': 'tinyteams',
        'nome': 'TinyTeams',
        'prompt': 'Você é um assistente virtual da TinyTeams.',
        'openai_key': 'test-key',  # Chave de teste
        'google_calendar_client_id': None,
        'google_calendar_client_secret': None,
        'google_sheets_id': None,
        'mensagem_quebrada': False
    }
    
    print("🧪 Testando inicialização do agent...")
    
    try:
        # Criar agent
        agent = BaseAgent(empresa_config)
        
        print(f"✅ Agent criado com sucesso!")
        print(f"📊 Número de tools: {len(agent.tools)}")
        
        # Listar tools
        for i, tool in enumerate(agent.tools, 1):
            print(f"   {i}. {tool.name}: {tool.description}")
        
        # Testar processamento simples
        context = {
            'cliente_id': 'test-user',
            'cliente_name': 'Usuário Teste',
            'empresa': 'tinyteams',
            'cliente_info': {'info': 'Cliente de teste'},
            'channel': 'whatsapp'
        }
        
        print("\n🧪 Testando processamento...")
        result = await agent.process_message("Olá, como você está?", context)
        print(f"✅ Resultado: {result}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_simple_agent()) 