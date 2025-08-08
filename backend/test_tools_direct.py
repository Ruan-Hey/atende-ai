#!/usr/bin/env python3
"""
Teste direto das tools para verificar se estão funcionando
"""

import logging
from tools.calendar_tools import CalendarTools
from tools.cliente_tools import ClienteTools
from tools.message_tools import MessageTools

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_tools_directly():
    """Testa as tools diretamente"""
    
    print("🧪 Testando tools diretamente...")
    
    # Configuração de teste
    empresa_config = {
        'slug': 'tinyteams',
        'nome': 'TinyTeams',
        'google_calendar_client_id': None,  # Google Calendar não configurado
        'google_calendar_client_secret': None,
        'google_sheets_id': None,
        'trinks_enabled': True,  # Trinks configurado
        'trinks_config': {
            'api_key': 'test-trinks-key',
            'base_url': 'https://api.trinks.com'
        }
    }
    
    try:
        # Testar CalendarTools
        print("\n📅 Testando CalendarTools...")
        calendar_tools = CalendarTools()
        
        # Teste 1: Sem Google Calendar configurado
        result1 = calendar_tools.verificar_disponibilidade("2024-01-15", empresa_config)
        print(f"✅ Teste 1 (sem Google Calendar): {result1}")
        
        # Teste 2: Com Trinks configurado
        result2 = calendar_tools.verificar_disponibilidade("2024-01-15", empresa_config)
        print(f"✅ Teste 2 (com Trinks): {result2}")
        
        # Testar ClienteTools
        print("\n👤 Testando ClienteTools...")
        cliente_tools = ClienteTools()
        
        # Teste 3: Buscar cliente
        result3 = cliente_tools.buscar_cliente_info("test-user-123", 1)
        print(f"✅ Teste 3 (buscar cliente): {result3}")
        
        # Testar MessageTools
        print("\n💬 Testando MessageTools...")
        message_tools = MessageTools()
        
        # Teste 4: Enviar mensagem (sem Twilio configurado)
        result4 = message_tools.enviar_resposta("Teste de mensagem", "test-user-123", empresa_config)
        print(f"✅ Teste 4 (enviar mensagem): {result4}")
        
        print("\n🎯 Todos os testes concluídos!")
        
        # Resumo dos resultados
        print("\n📊 Resumo dos Testes:")
        print(f"✅ CalendarTools: {'Funcionando' if 'Nenhuma API de agenda' in result1 or 'Trinks' in result2 else 'Problema'}")
        print(f"✅ ClienteTools: {'Funcionando' if 'Cliente' in result3 else 'Problema'}")
        print(f"✅ MessageTools: {'Funcionando' if 'Twilio não configurado' in result4 else 'Problema'}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_tools_directly() 