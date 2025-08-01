#!/usr/bin/env python3
import requests
import json

def test_api():
    base_url = "http://localhost:8000"
    
    # Teste 1: Health check
    try:
        response = requests.get(f"{base_url}/health")
        print(f"✅ Health check: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return
    
    # Teste 2: Login
    try:
        login_data = {
            "username": "admin@tinyteams.com",
            "password": "admin123"
        }
        response = requests.post(f"{base_url}/api/login", data=login_data)
        print(f"\n✅ Login: {response.status_code}")
        if response.status_code == 200:
            token = response.json()["access_token"]
            print(f"Token: {token[:20]}...")
            
            # Teste 3: Configurações da empresa
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(f"{base_url}/api/empresas/tinyteams/configuracoes", headers=headers)
            print(f"\n✅ Configurações: {response.status_code}")
            if response.status_code == 200:
                config = response.json()
                print(f"Prompt: {config.get('prompt', 'N/A')[:50]}...")
                print(f"Configurações: {config.get('configuracoes', {})}")
                print(f"APIs: {config.get('apis', {})}")
            else:
                print(f"Erro: {response.text}")
        else:
            print(f"Erro no login: {response.text}")
            
    except Exception as e:
        print(f"❌ Login failed: {e}")

if __name__ == "__main__":
    test_api() 