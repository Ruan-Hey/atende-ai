import requests
import json

def test_calendar_invite():
    """Testa se consegue enviar convite para o Google Calendar"""
    
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
    
    # 2. Testar webhook com mensagem sobre agendar reunião
    headers = {"Authorization": f"Bearer {token}"}
    
    webhook_data = {
        "Body": "Agendar uma reunião amanhã às 14h com João Silva",
        "From": "+5511999999999",
        "To": "+554184447366",
        "WaId": "test_user_123",
        "MessageType": "text"
    }
    
    print("🤖 Enviando mensagem para agendar reunião...")
    webhook_response = requests.post(
        "http://localhost:8000/webhook/tinyteams",
        headers=headers,
        json=webhook_data
    )
    
    print(f"📤 Webhook response: {webhook_response.status_code}")
    if webhook_response.status_code == 200:
        result = webhook_response.json()
        print(f"✅ Resposta do agente: {result.get('message', 'Sem mensagem')}")
        
        # Verificar se menciona agendamento ou convite
        message = result.get('message', '').lower()
        if any(word in message for word in ['agendado', 'agendamento', 'convite', 'reunião', 'evento', 'calendar']):
            print("🎉 AGENTE CONSEGUIU AGENDAR REUNIÃO!")
        else:
            print("⚠️ Agente respondeu, mas não mencionou agendamento")
    else:
        print(f"❌ Erro no webhook: {webhook_response.text}")
    
    # 3. Testar endpoint direto de agendamento
    print("\n📅 Testando endpoint de agendamento...")
    
    schedule_response = requests.post(
        "http://localhost:8000/api/calendar/schedule",
        headers=headers,
        params={
            "email": "joao.silva@exemplo.com",
            "name": "João Silva", 
            "company": "Empresa ABC",
            "date_time": "2025-08-12T14:00:00"
        }
    )
    
    print(f"📤 Schedule response: {schedule_response.status_code}")
    if schedule_response.status_code == 200:
        result = schedule_response.json()
        print(f"✅ Resultado do agendamento: {result}")
    else:
        print(f"❌ Erro no agendamento: {schedule_response.text}")

if __name__ == "__main__":
    test_calendar_invite() 