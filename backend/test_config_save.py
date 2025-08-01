#!/usr/bin/env python3
import os
import sys
import requests
import json
sys.path.append(os.path.dirname(__file__))

def test_config_save():
    """Testa se a API de configurações está salvando corretamente"""
    print("=== TESTE DE SALVAMENTO DE CONFIGURAÇÕES ===")
    
    # URL da API
    base_url = "http://localhost:8001"
    
    # Dados de teste
    test_config = {
        "prompt": "Você é um assistente virtual da TinyTeams, uma empresa de desenvolvimento de software. Responda de forma profissional e amigável.",
        "configuracoes": {
            "mensagemQuebrada": True,
            "buffer": True
        },
        "apis": {
            "openai": {
                "ativo": True,
                "token": "sk-test123456789"
            },
            "google": {
                "ativo": False,
                "token": ""
            },
            "chatwoot": {
                "ativo": False,
                "token": ""
            }
        }
    }
    
    try:
        # Testar salvamento
        print("📝 Testando salvamento de configurações...")
        
        # Simular uma requisição PUT
        response = requests.put(
            f"{base_url}/api/empresas/tinyteams/configuracoes",
            json=test_config,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ API de configurações está funcionando!")
        else:
            print("❌ API de configurações não está funcionando corretamente")
            
    except Exception as e:
        print(f"❌ Erro ao testar API: {e}")

if __name__ == "__main__":
    test_config_save() 