#!/usr/bin/env python3
"""
Teste do fluxo completo de cancelamento:
1. buscar_cliente_por_cpf
2. listar_agendamentos_cliente  
3. cancelar_agendamento
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.trinks_intelligent_tools import TrinksIntelligentTools
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_fluxo_cancelamento():
    """Testa o fluxo completo de cancelamento"""
    
    print("🧪 TESTANDO FLUXO COMPLETO DE CANCELAMENTO")
    print("=" * 60)
    
    # Configuração simulada da empresa
    empresa_config = {
        'trinks_base_url': 'https://api.trinks.com/v1',
        'trinks_api_key': 'test_key',
        'trinks_estabelecimento_id': '12345',
        'trinks_user_id': 1  # ID para "quemCancelou"
    }
    
    # Instanciar tools
    tools = TrinksIntelligentTools()
    
    # Simular dados do usuário
    cpf_cliente = "123.456.789-00"
    data_mencoada = "25/12"
    horario_mencoado = "14:30"
    motivo_cancelamento = "Cliente solicitou cancelamento"
    
    print(f"📋 Dados de teste:")
    print(f"   CPF: {cpf_cliente}")
    print(f"   Data: {data_mencoada}")
    print(f"   Horário: {horario_mencoado}")
    print(f"   Motivo: {motivo_cancelamento}")
    print()
    
    # ====================
    # PASSO 1: Buscar Cliente
    # ====================
    print("🔍 PASSO 1: Buscando cliente por CPF")
    print("-" * 40)
    
    try:
        resultado_cliente = tools.buscar_cliente_por_cpf(cpf_cliente, empresa_config)
        print(f"✅ Resultado busca cliente: {resultado_cliente}")
        
        if resultado_cliente.get('found'):
            cliente_id = resultado_cliente.get('cliente_id')
            nome_cliente = resultado_cliente.get('nome')
            print(f"✅ Cliente encontrado: {nome_cliente} (ID: {cliente_id})")
            
            # Verificar cache_instructions
            if resultado_cliente.get('cache_instructions'):
                print(f"📋 Cache instructions: {resultado_cliente['cache_instructions']}")
            
        else:
            print(f"❌ Cliente não encontrado: {resultado_cliente.get('error', 'N/A')}")
            return
            
    except Exception as e:
        print(f"❌ Erro ao buscar cliente: {e}")
        return
    
    print()
    
    # ====================
    # PASSO 2: Listar Agendamentos
    # ====================
    print("📅 PASSO 2: Listando agendamentos do cliente")
    print("-" * 40)
    
    try:
        resultado_agendamentos = tools.listar_agendamentos_cliente(
            cliente_id, 
            data_mencoada, 
            horario_mencoado, 
            empresa_config
        )
        print(f"✅ Resultado listar agendamentos: {resultado_agendamentos}")
        
        if resultado_agendamentos.get('found'):
            agendamento_id = resultado_agendamentos.get('agendamento_id')
            data_hora = resultado_agendamentos.get('data_hora')
            servico = resultado_agendamentos.get('servico')
            profissional = resultado_agendamentos.get('profissional')
            
            print(f"✅ Agendamento encontrado:")
            print(f"   ID: {agendamento_id}")
            print(f"   Data/Hora: {data_hora}")
            print(f"   Serviço: {servico}")
            print(f"   Profissional: {profissional}")
            
            # Verificar cache_instructions
            if resultado_agendamentos.get('cache_instructions'):
                print(f"📋 Cache instructions: {resultado_agendamentos['cache_instructions']}")
                
        else:
            print(f"❌ Agendamento não encontrado: {resultado_agendamentos.get('message', 'N/A')}")
            
            # Se tem múltiplos agendamentos, mostrar opções
            if resultado_agendamentos.get('agendamentos_disponiveis'):
                print(f"📋 Agendamentos disponíveis:")
                for ag in resultado_agendamentos['agendamentos_disponiveis']:
                    print(f"   - ID: {ag['id']}, Data: {ag['data_hora']}, Serviço: {ag['servico']}")
            return
            
    except Exception as e:
        print(f"❌ Erro ao listar agendamentos: {e}")
        return
    
    print()
    
    # ====================
    # PASSO 3: Cancelar Agendamento
    # ====================
    print("❌ PASSO 3: Cancelando agendamento")
    print("-" * 40)
    
    try:
        resultado_cancelamento = tools.cancelar_agendamento(
            agendamento_id, 
            motivo_cancelamento, 
            empresa_config
        )
        print(f"✅ Resultado cancelamento: {resultado_cancelamento}")
        
        if resultado_cancelamento.get('success'):
            print(f"✅ Agendamento cancelado com sucesso!")
            print(f"   ID: {resultado_cancelamento.get('agendamento_id')}")
            print(f"   Motivo: {resultado_cancelamento.get('motivo')}")
            
            # Verificar cache_instructions
            if resultado_cancelamento.get('cache_instructions'):
                print(f"📋 Cache instructions: {resultado_cancelamento['cache_instructions']}")
                
        else:
            print(f"❌ Falha no cancelamento: {resultado_cancelamento.get('error', 'N/A')}")
            
    except Exception as e:
        print(f"❌ Erro ao cancelar agendamento: {e}")
        return
    
    print()
    print("🎯 FLUXO COMPLETO TESTADO!")
    print("=" * 60)

def test_cache_instructions():
    """Testa especificamente as cache_instructions"""
    
    print("\n🧪 TESTANDO CACHE_INSTRUCTIONS")
    print("=" * 40)
    
    # Simular resultado de buscar_cliente
    resultado_cliente = {
        "found": True,
        "cliente_id": "67890",
        "nome": "João Silva",
        "cache_instructions": {
            "update_fields": {
                "cliente_id": "67890",
                "nome": "João Silva"
            }
        }
    }
    
    print(f"📋 Cache instructions do cliente: {resultado_cliente['cache_instructions']}")
    
    # Simular resultado de listar_agendamentos
    resultado_agendamentos = {
        "found": True,
        "agendamento_id": "12345",
        "data_hora": "2024-12-25T14:30:00Z",
        "cache_instructions": {
            "update_fields": {
                "agendamento_id": "12345",
                "data_hora": "2024-12-25T14:30:00Z",
                "cliente_id": "67890"
            }
        }
    }
    
    print(f"📋 Cache instructions dos agendamentos: {resultado_agendamentos['cache_instructions']}")
    
    # Simular resultado de cancelar_agendamento
    resultado_cancelamento = {
        "success": True,
        "cache_instructions": {
            "clear_fields": ["agendamento_id", "data_hora"],
            "update_fields": {
                "status": "cancelado",
                "motivo_cancelamento": "Cliente solicitou"
            }
        }
    }
    
    print(f"📋 Cache instructions do cancelamento: {resultado_cancelamento['cache_instructions']}")

if __name__ == "__main__":
    try:
        # Testar fluxo principal
        test_fluxo_cancelamento()
        
        # Testar cache_instructions
        test_cache_instructions()
        
    except Exception as e:
        print(f"❌ Erro geral no teste: {e}")
        import traceback
        traceback.print_exc()

