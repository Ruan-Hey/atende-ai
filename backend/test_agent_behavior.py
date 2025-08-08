#!/usr/bin/env python3
"""
Teste do comportamento do agent simulando respostas
"""

import asyncio
import logging
from unittest.mock import Mock, patch
from agents.base_agent import BaseAgent

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_agent_behavior():
    """Testa o comportamento do agent com diferentes cenários"""
    
    # Configuração de teste
    empresa_config = {
        'slug': 'tinyteams',
        'nome': 'TinyTeams',
        'prompt': 'Você é um assistente virtual da TinyTeams.',
        'openai_key': 'test-key',
        'google_calendar_client_id': None,  # Google Calendar não configurado
        'google_calendar_client_secret': None,
        'google_sheets_id': None,
        'trinks_enabled': True,  # Trinks configurado
        'trinks_config': {
            'api_key': 'test-trinks-key',
            'base_url': 'https://api.trinks.com'
        },
        'mensagem_quebrada': False
    }
    
    print("🧪 Testando comportamento do agent...")
    
    # Simular respostas da OpenAI
    mock_responses = {
        "Você consegue ver os horários disponíveis?": "Vou verificar os horários disponíveis usando a ferramenta verificar_calendario.",
        "Quero agendar uma reunião para amanhã às 10h": "Vou primeiro verificar a disponibilidade e depois fazer a reserva.",
        "Olá, como você está?": "Olá! Estou funcionando perfeitamente. Como posso ajudá-lo hoje?"
    }
    
    try:
        # Criar agent
        agent = BaseAgent(empresa_config)
        
        print(f"✅ Agent criado com {len(agent.tools)} tools")
        
        # Testar diferentes cenários
        test_cases = [
            {
                'message': "Você consegue ver os horários disponíveis?",
                'expected_behavior': 'Deve usar verificar_calendario ou dizer que não está configurado'
            },
            {
                'message': "Quero agendar uma reunião para amanhã às 10h",
                'expected_behavior': 'Deve usar verificar_calendario primeiro, depois fazer_reserva'
            },
            {
                'message': "Olá, como você está?",
                'expected_behavior': 'Deve responder cordialmente sem usar ferramentas'
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n--- Teste {i}: {test_case['message']} ---")
            print(f"Comportamento esperado: {test_case['expected_behavior']}")
            
            # Simular resposta da OpenAI
            mock_response = mock_responses.get(test_case['message'], "Resposta padrão")
            
            with patch.object(agent.llm, 'agenerate') as mock_generate:
                mock_generate.return_value.generations = [[Mock(text=mock_response)]]
                
                context = {
                    'cliente_id': 'test-user-123',
                    'cliente_name': 'Usuário Teste',
                    'empresa': 'tinyteams',
                    'cliente_info': {'info': 'Cliente de teste'},
                    'channel': 'whatsapp'
                }
                
                result = await agent.process_message(test_case['message'], context)
                print(f"✅ Resultado: {result}")
        
        print("\n🎯 Teste de comportamento concluído!")
        
        # Testar especificamente as tools
        print("\n🔧 Testando tools diretamente...")
        
        # Testar verificar_calendario
        from tools.calendar_tools import CalendarTools
        calendar_tools = CalendarTools()
        
        # Teste sem Google Calendar configurado
        result = calendar_tools.verificar_disponibilidade("2024-01-15", empresa_config)
        print(f"📅 Verificar disponibilidade (sem Google Calendar): {result}")
        
        # Teste com Trinks configurado
        result = calendar_tools.verificar_disponibilidade("2024-01-15", empresa_config)
        print(f"📅 Verificar disponibilidade (com Trinks): {result}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_agent_behavior()) 