import requests
import json

def test_agent_calendar_access():
    """Testa se o agente consegue acessar o Google Calendar"""
    
    # 1. Fazer login
    login_data = {
        "username": "ruan.g.hey@gmail.com",
        "password": "admin123"
    }
    
    login_response = requests.post(
        "http://localhost:8000/api/login",
        data=login_data
    )
    
    if login_response.status_code != 200:
        print(f"❌ Erro no login: {login_response.status_code}")
        return
    
    token = login_response.json().get("access_token")
    print(f"✅ Login realizado")
    
    # 2. Testar webhook com mensagem sobre calendário
    headers = {"Authorization": f"Bearer {token}"}
    
    webhook_data = {
        "Body": "Listar eventos de hoje no calendário",
        "From": "+5511999999999",
        "To": "+554184447366",
        "WaId": "test_user_123",
        "MessageType": "text"
    }
    
    print("🤖 Enviando mensagem para o agente...")
    webhook_response = requests.post(
        "http://localhost:8000/webhook/tinyteams",
        headers=headers,
        json=webhook_data
    )
    
    print(f"📤 Webhook response: {webhook_response.status_code}")
    if webhook_response.status_code == 200:
        result = webhook_response.json()
        print(f"✅ Resposta do agente: {result.get('message', 'Sem mensagem')}")
        
        # Verificar se menciona Google Calendar
        message = result.get('message', '').lower()
        if 'google calendar' in message or 'calendário' in message or 'eventos' in message:
            print("🎉 AGENTE CONSEGUIU ACESSAR O GOOGLE CALENDAR!")
        else:
            print("⚠️ Agente respondeu, mas não mencionou calendário")
    else:
        print(f"❌ Erro no webhook: {webhook_response.text}")
    
    # 3. Testar endpoint direto de slots
    print("\n📅 Testando endpoint de slots...")
    slots_response = requests.get(
        "http://localhost:8000/api/calendar/slots",
        headers=headers
    )
    
    print(f"📤 Slots response: {slots_response.status_code}")
    if slots_response.status_code == 200:
        slots = slots_response.json()
        print(f"✅ Slots disponíveis: {len(slots)} horários")
        print(f"📋 Slots: {slots}")
    else:
        print(f"❌ Erro nos slots: {slots_response.text}")

if __name__ == "__main__":
    test_agent_calendar_access() 