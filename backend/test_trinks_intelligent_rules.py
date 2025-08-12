#!/usr/bin/env python3
"""
Teste das regras inteligentes expandidas para Trinks
"""

import sys
import os
from pathlib import Path

# Adicionar o diretório backend ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.api_rules_engine import api_rules_engine
from tools.trinks_intelligent_tools import trinks_intelligent_tools
from config import Config

def test_trinks_rules():
    """Testa as regras expandidas do Trinks"""
    
    print("🧪 Testando Regras Inteligentes do Trinks")
    print("=" * 50)
    
    # Configuração de exemplo para empresa com Trinks
    empresa_config = {
        'empresa_id': 1,
        'trinks_enabled': True,
        'trinks_config': {
            'estabelecimento_id': '12345',
            'api_key': 'test_key',
            'base_url': 'https://api.trinks.com/v1'
        }
    }
    
    try:
        # 1. Testar detecção de API
        print("\n1. 🔍 Testando Detecção de API...")
        api_type = api_rules_engine.detect_active_api(empresa_config)
        print(f"   ✅ API detectada: {api_type.value}")
        
        # 2. Testar regras da API
        print("\n2. 📋 Testando Regras da API...")
        rules = api_rules_engine.get_api_rules(empresa_config)
        print(f"   ✅ Tipo da API: {rules['api_type'].value}")
        print(f"   ✅ Email obrigatório: {rules['email_required']}")
        print(f"   ✅ WaId obrigatório: {rules['waid_required']}")
        
        # 3. Testar regras de busca de cliente
        print("\n3. 👤 Testando Regras de Busca de Cliente...")
        client_rules = api_rules_engine.get_client_search_rules(empresa_config)
        if client_rules:
            print(f"   ✅ Método principal: {client_rules['primary_method']}")
            print(f"   ✅ Endpoint: {client_rules['api_endpoint']}")
            print(f"   ✅ Criar se não encontrar: {client_rules['create_if_not_found']}")
        else:
            print("   ❌ Regras de cliente não encontradas")
        
        # 4. Testar regras de detecção de serviço
        print("\n4. 🧠 Testando Regras de Detecção de Serviço...")
        service_rules = api_rules_engine.get_service_detection_rules(empresa_config)
        if service_rules:
            print(f"   ✅ Usar NLP: {service_rules['use_nlp']}")
            print(f"   ✅ Endpoint: {service_rules['api_endpoint']}")
            print(f"   ✅ Mapeamentos: {len(service_rules['service_mapping'])} serviços")
        else:
            print("   ❌ Regras de serviço não encontradas")
        
        # 5. Testar regras de busca de profissionais
        print("\n5. 👨‍⚕️ Testando Regras de Busca de Profissionais...")
        prof_rules = api_rules_engine.get_professional_search_rules(empresa_config)
        if prof_rules:
            print(f"   ✅ Endpoint: {prof_rules['api_endpoint']}")
            print(f"   ✅ Filtrar por serviço: {prof_rules['filter_by_service']}")
            print(f"   ✅ Verificar disponibilidade: {prof_rules['availability_check']}")
        else:
            print("   ❌ Regras de profissionais não encontradas")
        
        # 6. Testar regras de verificação de disponibilidade
        print("\n6. 📅 Testando Regras de Verificação de Disponibilidade...")
        avail_rules = api_rules_engine.get_availability_check_rules(empresa_config)
        if avail_rules:
            print(f"   ✅ Endpoint: {avail_rules['api_endpoint']}")
            print(f"   ✅ Método: {avail_rules['method']}")
            print(f"   ✅ Buffer time: {avail_rules['slot_calculation']['buffer_time']} min")
        else:
            print("   ❌ Regras de disponibilidade não encontradas")
        
        # 7. Testar regras de criação de reserva
        print("\n7. 🎯 Testando Regras de Criação de Reserva...")
        reservation_rules = api_rules_engine.get_reservation_creation_rules(empresa_config)
        if reservation_rules:
            print(f"   ✅ Endpoint: {reservation_rules['api_endpoint']}")
            print(f"   ✅ Método: {reservation_rules['method']}")
            print(f"   ✅ Campos obrigatórios: {len(reservation_rules['required_fields'])}")
            print(f"   ✅ Auto-confirmação: {reservation_rules['auto_confirmation']}")
        else:
            print("   ❌ Regras de reserva não encontradas")
        
        # 8. Testar se é API Trinks
        print("\n8. ✅ Testando Verificação de API Trinks...")
        is_trinks = api_rules_engine.is_trinks_api(empresa_config)
        print(f"   ✅ É API Trinks: {is_trinks}")
        
        print("\n" + "=" * 50)
        print("🎉 Todos os testes de regras passaram!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Erro nos testes: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_intelligent_tools():
    """Testa as ferramentas inteligentes do Trinks"""
    
    print("\n🧪 Testando Ferramentas Inteligentes do Trinks")
    print("=" * 50)
    
    # Configuração de exemplo
    empresa_config = {
        'empresa_id': 1,
        'trinks_enabled': True,
        'trinks_config': {
            'estabelecimento_id': '12345',
            'api_key': 'test_key',
            'base_url': 'https://api.trinks.com/v1'
        }
    }
    
    try:
        # 1. Testar busca de cliente por CPF
        print("\n1. 🔍 Testando Busca de Cliente por CPF...")
        cpf = "12345678901"
        client_result = trinks_intelligent_tools.search_client_by_cpf(cpf, empresa_config)
        print(f"   ✅ Resultado: {client_result.get('message', 'N/A')}")
        
        # 2. Testar detecção de serviço
        print("\n2. 🧠 Testando Detecção de Serviço...")
        message = "Quero fazer uma massagem relaxante amanhã"
        service_result = trinks_intelligent_tools.detect_service_from_conversation(message, empresa_config)
        print(f"   ✅ Serviço detectado: {service_result.get('detected', False)}")
        print(f"   ✅ Mensagem: {service_result.get('message', 'N/A')}")
        
        # 3. Testar busca de profissionais
        print("\n3. 👨‍⚕️ Testando Busca de Profissionais...")
        service_id = "123"
        prof_result = trinks_intelligent_tools.find_professionals_for_service(service_id, empresa_config)
        print(f"   ✅ Profissionais encontrados: {prof_result.get('found', False)}")
        print(f"   ✅ Mensagem: {prof_result.get('message', 'N/A')}")
        
        # 4. Testar verificação de disponibilidade
        print("\n4. 📅 Testando Verificação de Disponibilidade...")
        data = "2024-01-16"
        availability_result = trinks_intelligent_tools.check_professional_availability(
            data=data,
            service_id="123",
            empresa_config=empresa_config
        )
        print(f"   ✅ Disponibilidade: {availability_result.get('available', False)}")
        print(f"   ✅ Mensagem: {availability_result.get('message', 'N/A')}")
        
        # 5. Testar criação de reserva
        print("\n5. 🎯 Testando Criação de Reserva...")
        reservation_data = {
            "servicold": "123",
            "clienteld": "456",
            "dataHoralnicio": "2024-01-16T14:00:00",
            "duracaoEmMinutos": 60,
            "valor": 80.0
        }
        reservation_result = trinks_intelligent_tools.create_reservation(reservation_data, empresa_config)
        print(f"   ✅ Reserva criada: {reservation_result.get('success', False)}")
        print(f"   ✅ Mensagem: {reservation_result.get('message', 'N/A')}")
        
        print("\n" + "=" * 50)
        print("🎉 Todos os testes de ferramentas passaram!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Erro nos testes: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal de teste"""
    
    print("🚀 Teste das Regras Inteligentes Expandidas para Trinks")
    print("=" * 60)
    
    # Testar regras
    rules_success = test_trinks_rules()
    
    # Testar ferramentas
    tools_success = test_intelligent_tools()
    
    # Resumo final
    print("\n" + "=" * 60)
    print("📊 RESUMO DOS TESTES:")
    print(f"   ✅ Regras: {'PASSOU' if rules_success else 'FALHOU'}")
    print(f"   ✅ Ferramentas: {'PASSOU' if tools_success else 'FALHOU'}")
    
    if rules_success and tools_success:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        print("🚀 Sistema de regras inteligentes está funcionando perfeitamente!")
    else:
        print("\n❌ ALGUNS TESTES FALHARAM!")
        print("🔧 Verifique os erros acima e corrija os problemas.")
    
    return rules_success and tools_success

if __name__ == "__main__":
    main() 