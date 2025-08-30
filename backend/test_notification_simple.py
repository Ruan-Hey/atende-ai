#!/usr/bin/env python3
"""
Teste simples para disparar notificação
"""
import requests
import json

def test_notification():
    """Testa o endpoint de notificação"""
    
    # URL do backend
    base_url = "http://localhost:8000"
    
    # Dados para ativar notificação
    data = {
        "empresa_id": 1,  # TinyTeams
        "action": "enable"
    }
    
    try:
        print("🔔 Testando ativação de notificações...")
        
        # Fazer POST para ativar notificações
        response = requests.post(
            f"{base_url}/api/notifications/toggle",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"✅ Status: {response.status_code}")
        print(f"✅ Resposta: {response.json()}")
        
        if response.status_code == 200:
            print("🎉 Notificações ativadas com sucesso!")
            print("📱 Agora você deve ver uma notificação no navegador!")
        else:
            print("❌ Erro ao ativar notificações")
            
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    test_notification()
