#!/usr/bin/env python3
"""
Teste para verificar se o agente está funcionando sem alucinação
"""

import asyncio
import logging
from agents.whatsapp_agent import WhatsAppAgent

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_agent():
    """Testa o agente com diferentes cenários"""
    
    # Configuração de teste
    empresa_config = {
        'slug': 'tinyteams',
        'nome': 'TinyTeams',
        'prompt': 'Você é um assistente virtual da TinyTeams. Ajude os clientes de forma cordial e profissional.',
        'openai_key': 'test-key',  # Chave de teste
        'google_calendar_client_id': None,  # Não configurado
        'google_calendar_client_secret': None,
        'google_sheets_id': None,
        'mensagem_quebrada': False
    }
    
    # Criar agente
    agent = WhatsAppAgent(empresa_config)
    
    # Cenários de teste
    test_cases = [
        {
            'message': 'Você consegue ver os horários disponíveis?',
            'expected_behavior': 'Deve usar verificar_calendario ou dizer que não está configurado'
        },
        {
            'message': 'Quero agendar uma reunião para amanhã às 10h',
            'expected_behavior': 'Deve usar verificar_calendario primeiro, depois fazer_reserva'
        },
        {
            'message': 'Olá, como você está?',
            'expected_behavior': 'Deve responder cordialmente sem usar ferramentas'
        }
    ]
    
    print("🧪 Testando agente...")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Teste {i}: {test_case['message']} ---")
        print(f"Comportamento esperado: {test_case['expected_behavior']}")
        
        try:
            # Simular webhook data
            webhook_data = {
                'WaId': 'test-user-123',
                'Body': test_case['message'],
                'ProfileName': 'Usuário Teste'
            }
            
            # Processar mensagem
            result = await agent.process_whatsapp_message(webhook_data, empresa_config)
            
            print(f"✅ Resultado: {result.get('message', 'Sem resposta')}")
            
        except Exception as e:
            print(f"❌ Erro no teste {i}: {e}")
    
    print("\n🎯 Teste concluído!")

if __name__ == "__main__":
    asyncio.run(test_agent()) 