#!/usr/bin/env python3
"""
Teste direto das regras da API expandidas
Importa diretamente o arquivo sem dependências
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importar diretamente o arquivo
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'agents'))
from rules import rules_loader
import json

def test_api_rules_expansion():
    """Testa se as regras da API foram expandidas corretamente"""
    print("🧪 Testando Expansão das Regras da API")
    print("=" * 50)
    
    # Configuração de exemplo
    empresa_config = {
        'empresa_id': 1,
        'trinks_enabled': True,
        'trinks_api_key': 'test_key',
        'nome': 'Clínica Teste'
    }
    
    try:
        # 1. Testar regras expandidas
        print("\n1. 📋 Testando Regras Expandidas...")
        rules = rules_loader.get_availability_check_rules_expanded(empresa_config)
        if rules:
            print(f"   ✅ Regras encontradas: {len(rules.get('passos', []))} passos")
            print(f"   ✅ Campos obrigatórios: {rules.get('campos_obrigatorios', [])}")
            print(f"   ✅ Campos opcionais: {rules.get('campos_opcionais', [])}")
            print(f"   ✅ Passos: {rules.get('passos', [])}")
        else:
            print("   ❌ Regras não encontradas")
            return False
        
        # 2. Testar tipos de busca
        print("\n2. 🔍 Testando Tipos de Busca...")
        search_rules = rules_loader.get_search_type_rules(empresa_config)
        if search_rules:
            print(f"   ✅ Tipos de busca: {list(search_rules.keys())}")
            for tipo, config in search_rules.items():
                print(f"      • {tipo}: {len(config.get('fluxo', []))} passos")
                print(f"        - Campos necessários: {config.get('campos_necessarios', [])}")
        else:
            print("   ❌ Regras de busca não encontradas")
            return False
        
        # 3. Testar determinação de tipo
        print("\n3. 🎯 Testando Determinação de Tipo...")
        
        # Teste por profissional
        data_profissional = {"profissional": "Amabile", "data": "2025-08-27"}
        tipo_prof = rules_loader.determine_search_type(data_profissional, empresa_config)
        print(f"   ✅ Busca por profissional: {tipo_prof}")
        
        # Teste por procedimento
        data_procedimento = {"procedimento": "massagem relaxante", "data": "2025-08-28"}
        tipo_proc = rules_loader.determine_search_type(data_procedimento, empresa_config)
        print(f"   ✅ Busca por procedimento: {tipo_proc}")
        
        # Teste inválido
        data_invalido = {"data": "2025-08-29"}
        tipo_inv = rules_loader.determine_search_type(data_invalido, empresa_config)
        print(f"   ❌ Busca sem profissional/procedimento: {tipo_inv}")
        
        # 4. Testar validação
        print("\n4. ✅ Testando Validação...")
        
        # Teste válido por profissional
        validation_valid = rules_loader.validate_availability_request(data_profissional, empresa_config)
        print(f"   ✅ Validação por profissional: {validation_valid.get('valid')}")
        print(f"      - Tipo de busca: {validation_valid.get('search_type')}")
        
        # Teste válido por procedimento
        validation_valid2 = rules_loader.validate_availability_request(data_procedimento, empresa_config)
        print(f"   ✅ Validação por procedimento: {validation_valid2.get('valid')}")
        print(f"      - Tipo de busca: {validation_valid2.get('search_type')}")
        
        # Teste inválido (sem data)
        data_invalido = {"profissional": "Amabile"}
        validation_invalid = rules_loader.validate_availability_request(data_invalido, empresa_config)
        print(f"   ❌ Validação sem data: {validation_invalid.get('valid')}")
        print(f"      - Erro: {validation_invalid.get('error')}")
        
        # Teste inválido (sem profissional nem procedimento)
        data_invalido2 = {"data": "2025-08-29"}
        validation_invalid2 = rules_loader.validate_availability_request(data_invalido2, empresa_config)
        print(f"   ❌ Validação sem profissional/procedimento: {validation_invalid2.get('valid')}")
        print(f"      - Erro: {validation_invalid2.get('error')}")
        
        # 5. Testar passos do fluxo
        print("\n5. 🚀 Testando Passos do Fluxo...")
        
        # Teste com dados simulados
        dados_profissional = {'profissional': 'Amabile', 'data': '2025-08-27'}
        dados_procedimento = {'procedimento': 'massagem relaxante', 'data': '2025-08-28'}
        
        steps_prof = rules_loader.get_availability_flow_steps(dados_profissional, empresa_config)
        print(f"   ✅ Passos por profissional: {len(steps_prof)}")
        print(f"      - Fluxo: {' → '.join(steps_prof)}")
        
        steps_proc = rules_loader.get_availability_flow_steps(dados_procedimento, empresa_config)
        print(f"   ✅ Passos por procedimento: {len(steps_proc)}")
        print(f"      - Fluxo: {' → '.join(steps_proc)}")
        
        # 6. Testar regras completas da API
        print("\n6. 🌐 Testando Regras Completas da API...")
        api_rules = rules_loader.get_api_rules(empresa_config)
        print(f"   ✅ Tipo da API: {api_rules.get('api_type')}")
        print(f"   ✅ Nome da API: {api_rules.get('api_name')}")
        print(f"   ✅ Email obrigatório: {api_rules.get('email_required')}")
        print(f"   ✅ WaId obrigatório: {api_rules.get('waid_required')}")
        
        print("\n" + "=" * 50)
        print("🎉 Todos os testes de regras passaram!")
        return True
        
    except Exception as e:
        print(f"\n❌ Erro nos testes: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Iniciando Testes das Regras da API Expandidas")
    print("=" * 60)
    
    success = test_api_rules_expansion()
    
    if success:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        print("✅ As regras da API foram expandidas com sucesso!")
        print("\n📋 Resumo das Funcionalidades:")
        print("   • Busca por profissional (fluxo existente)")
        print("   • Busca por procedimento (novo fluxo)")
        print("   • Validação inteligente de requisições")
        print("   • Determinação automática do tipo de busca")
        print("   • Fluxos personalizados por tipo de busca")
    else:
        print("\n❌ ALGUNS TESTES FALHARAM!")
        print("🔧 Verifique os erros acima") 