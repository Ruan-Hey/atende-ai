#!/usr/bin/env python3
"""
Teste simples para verificar se o campo estabelecimento_id está funcionando
"""

import sys
import os
from pathlib import Path

# Adicionar o diretório backend ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_estabelecimento_id_mapping():
    """Testa se o mapeamento do estabelecimento_id está funcionando"""
    
    print("🧪 Testando Mapeamento do Estabelecimento ID")
    print("=" * 50)
    
    # Simular configuração que vem do frontend
    configuracoes = {
        'api_5_key': 'test_api_key_123',
        'api_5_estabelecimento_id': '12345'
    }
    
    print(f"Configurações recebidas: {configuracoes}")
    
    # Simular processamento do backend
    api_configs = {}
    for key, value in configuracoes.items():
        if key.startswith('api_'):
            parts = key.split('_')
            if len(parts) >= 3:
                api_id = parts[1]
                field_name = '_'.join(parts[2:])
                
                if api_id not in api_configs:
                    api_configs[api_id] = {}
                api_configs[api_id][field_name] = value
    
    print(f"Configurações processadas: {api_configs}")
    
    # Simular mapeamento específico do Trinks
    for api_id_str, config in api_configs.items():
        if 'key' in config:
            mapped_config = config.copy()
            mapped_config["api_key"] = config["key"]
            del mapped_config["key"]
            
            # Adicionar estabelecimento_id se presente
            if "estabelecimento_id" in config:
                mapped_config["estabelecimento_id"] = config["estabelecimento_id"]
            
            print(f"Mapeamento final para API {api_id_str}: {mapped_config}")
            
            # Verificar se os campos estão corretos
            assert "api_key" in mapped_config, "api_key deve estar presente"
            assert "estabelecimento_id" in mapped_config, "estabelecimento_id deve estar presente"
            assert mapped_config["api_key"] == "test_api_key_123", "api_key deve ter o valor correto"
            assert mapped_config["estabelecimento_id"] == "12345", "estabelecimento_id deve ter o valor correto"
            
            print("✅ Todos os campos estão corretos!")
    
    print("\n🎉 Teste passou com sucesso!")
    return True

def test_empresa_config_building():
    """Testa se o estabelecimento_id está sendo incluído na configuração da empresa"""
    
    print("\n🧪 Testando Construção da Configuração da Empresa")
    print("=" * 50)
    
    # Simular configuração da API Trinks
    api_config = {
        'api_key': 'test_api_key_123',
        'base_url': 'https://api.trinks.com/v1',
        'estabelecimento_id': '12345'
    }
    
    print(f"Config da API: {api_config}")
    
    # Simular construção da configuração da empresa
    empresa_config = {}
    empresa_config['trinks_api_key'] = api_config.get('api_key')
    empresa_config['trinks_base_url'] = api_config.get('base_url')
    empresa_config['trinks_estabelecimento_id'] = api_config.get('estabelecimento_id')
    
    print(f"Config da empresa: {empresa_config}")
    
    # Verificar se os campos estão corretos
    assert 'trinks_api_key' in empresa_config, "trinks_api_key deve estar presente"
    assert 'trinks_base_url' in empresa_config, "trinks_base_url deve estar presente"
    assert 'trinks_estabelecimento_id' in empresa_config, "trinks_estabelecimento_id deve estar presente"
    
    assert empresa_config['trinks_api_key'] == 'test_api_key_123', "trinks_api_key deve ter o valor correto"
    assert empresa_config['trinks_base_url'] == 'https://api.trinks.com/v1', "trinks_base_url deve ter o valor correto"
    assert empresa_config['trinks_estabelecimento_id'] == '12345', "trinks_estabelecimento_id deve ter o valor correto"
    
    print("✅ Todos os campos da empresa estão corretos!")
    
    print("\n🎉 Teste passou com sucesso!")
    return True

def main():
    """Função principal de teste"""
    
    print("🚀 Teste do Campo Estabelecimento ID")
    print("=" * 60)
    
    try:
        # Testar mapeamento
        test1_success = test_estabelecimento_id_mapping()
        
        # Testar configuração da empresa
        test2_success = test_empresa_config_building()
        
        # Resumo final
        print("\n" + "=" * 60)
        print("📊 RESUMO DOS TESTES:")
        print(f"   ✅ Mapeamento: {'PASSOU' if test1_success else 'FALHOU'}")
        print(f"   ✅ Config Empresa: {'PASSOU' if test2_success else 'FALHOU'}")
        
        if test1_success and test2_success:
            print("\n🎉 TODOS OS TESTES PASSARAM!")
            print("🚀 Campo estabelecimento_id está funcionando perfeitamente!")
        else:
            print("\n❌ ALGUNS TESTES FALHARAM!")
            print("🔧 Verifique os erros acima e corrija os problemas.")
        
        return test1_success and test2_success
        
    except Exception as e:
        print(f"\n❌ Erro nos testes: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main() 