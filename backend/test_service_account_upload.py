#!/usr/bin/env python3
"""
Teste para upload de Service Account
"""

import json
import requests
from config import Config

def test_service_account_upload():
    """Testa o upload de Service Account"""
    
    # Primeiro fazer login
    login_data = {
        'username': 'ruan.g.hey@gmail.com',
        'password': 'admin123'
    }
    
    try:
        # Login
        login_response = requests.post('http://localhost:8000/api/login', data=login_data)
        if login_response.status_code != 200:
            print(f"Erro no login: {login_response.status_code} - {login_response.text}")
            return
        
        token_data = login_response.json()
        token = token_data['access_token']
        print(f"Login realizado com sucesso. Token: {token[:20]}...")
        
        # Dados de teste (Service Account fake)
        service_account_data = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "test-key-id",
            "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...\n-----END PRIVATE KEY-----\n",
            "client_email": "test@test-project.iam.gserviceaccount.com",
            "client_id": "123456789",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }
        
        # Criar arquivo temporário
        with open('test_service_account.json', 'w') as f:
            json.dump(service_account_data, f)
        
        # Simular upload com autenticação
        url = "http://localhost:8000/api/empresas/tinyteams/google-service-account"
        
        with open('test_service_account.json', 'rb') as f:
            files = {'file': ('service_account.json', f, 'application/json')}
            headers = {'Authorization': f'Bearer {token}'}
            
            response = requests.post(url, files=files, headers=headers)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    test_service_account_upload() 