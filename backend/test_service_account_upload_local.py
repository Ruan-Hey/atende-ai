import requests
import json
import os

# Dados de teste do Service Account
test_service_account = {
    "type": "service_account",
    "project_id": "test-project-123",
    "private_key_id": "test-key-id",
    "private_key": "-----BEGIN PRIVATE KEY-----\nTEST_KEY\n-----END PRIVATE KEY-----\n",
    "client_email": "test@test-project-123.iam.gserviceaccount.com",
    "client_id": "123456789",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/test%40test-project-123.iam.gserviceaccount.com"
}

def test_service_account_upload():
    """Testa upload do Service Account localmente"""
    
    # 1. Fazer login primeiro
    login_data = {
        "username": "ruan.g.hey@gmail.com",
        "password": "admin123"
    }
    
    login_response = requests.post(
        "http://localhost:8000/api/login",
        data=login_data
    )
    
    if login_response.status_code != 200:
        print(f"❌ Erro no login: {login_response.status_code} - {login_response.text}")
        return
    
    token = login_response.json().get("access_token")
    print(f"✅ Login realizado, token: {token[:20]}...")
    
    # 2. Testar upload do Service Account
    headers = {"Authorization": f"Bearer {token}"}
    
    # Criar arquivo temporário
    with open("test_service_account.json", "w") as f:
        json.dump(test_service_account, f, indent=2)
    
    try:
        with open("test_service_account.json", "rb") as f:
            files = {"file": ("service-account.json", f, "application/json")}
            
            upload_response = requests.post(
                "http://localhost:8000/api/empresas/tinyteams/google-service-account",
                headers=headers,
                files=files
            )
        
        print(f"📤 Upload response: {upload_response.status_code}")
        print(f"📤 Upload content: {upload_response.text}")
        
        if upload_response.status_code == 200:
            result = upload_response.json()
            print(f"✅ Upload bem-sucedido: {result}")
            
            # 3. Verificar se salvou no banco
            status_response = requests.get(
                "http://localhost:8000/api/test/service-account-status",
                headers=headers
            )
            
            print(f"🔍 Status check: {status_response.status_code}")
            print(f"🔍 Status content: {status_response.text}")
            
        else:
            print(f"❌ Erro no upload: {upload_response.text}")
    
    finally:
        # Limpar arquivo temporário
        if os.path.exists("test_service_account.json"):
            os.remove("test_service_account.json")

if __name__ == "__main__":
    test_service_account_upload() 