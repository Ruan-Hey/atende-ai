#!/usr/bin/env python3
"""
Teste para verificar acesso real ao Google Calendar
"""

import os
import sys
from datetime import datetime, timedelta

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_real_calendar_access():
    """Testa acesso real ao Google Calendar"""
    
    print("🔍 Testando acesso real ao Google Calendar...")
    
    # Verificar se temos as credenciais necessárias
    required_vars = [
        'GOOGLE_CALENDAR_CLIENT_ID',
        'GOOGLE_CALENDAR_CLIENT_SECRET',
        'GOOGLE_CALENDAR_REFRESH_TOKEN'
    ]
    
    print("\n📋 Verificando credenciais:")
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"  ✅ {var}: Configurado")
        else:
            print(f"  ❌ {var}: Não configurado")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n⚠️ Credenciais faltando: {', '.join(missing_vars)}")
        print("Para acessar sua agenda real, você precisa:")
        print("1. Configurar as variáveis de ambiente do Google Calendar")
        print("2. Ou adicionar um arquivo credentials.json")
        print("3. Ou configurar via Service Account")
        return
    
    # Tentar acessar o Google Calendar real
    try:
        from integrations.google_calendar_service import GoogleCalendarService
        
        # Configuração da empresa
        empresa_config = {
            'google_calendar_enabled': True,
            'google_calendar_client_id': os.getenv('GOOGLE_CALENDAR_CLIENT_ID'),
            'google_calendar_client_secret': os.getenv('GOOGLE_CALENDAR_CLIENT_SECRET'),
            'google_calendar_refresh_token': os.getenv('GOOGLE_CALENDAR_REFRESH_TOKEN'),
            'google_calendar_service_account': os.getenv('GOOGLE_CALENDAR_SERVICE_ACCOUNT'),
            'google_calendar_project_id': os.getenv('GOOGLE_CALENDAR_PROJECT_ID'),
            'google_calendar_client_email': os.getenv('GOOGLE_CALENDAR_CLIENT_EMAIL'),
        }
        
        print("\n🔐 Tentando autenticar com Google Calendar...")
        calendar_service = GoogleCalendarService(empresa_config)
        
        if not calendar_service.service:
            print("❌ Falha na autenticação com Google Calendar")
            print("Verifique suas credenciais e tente novamente")
            return
        
        print("✅ Google Calendar autenticado com sucesso!")
        
        # Testar com data real
        test_date = "2025-08-11"
        print(f"\n📅 Verificando eventos reais para: {test_date}")
        
        # Listar eventos reais
        start_date = datetime.strptime(test_date, '%Y-%m-%d')
        end_date = start_date + timedelta(days=1)
        
        events = calendar_service.list_events(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        print(f"\n📊 Eventos reais encontrados: {len(events)}")
        
        if events:
            print("\n📅 Seus eventos reais:")
            for i, event in enumerate(events, 1):
                start = event.get('start', {}).get('dateTime', 'Sem horário')
                summary = event.get('summary', 'Sem título')
                print(f"  {i}. {start} - {summary}")
        else:
            print("✅ Nenhum evento encontrado para esta data")
        
        # Verificar horários disponíveis
        print(f"\n🕐 Verificando horários disponíveis...")
        available_slots = calendar_service.get_available_slots(test_date)
        
        print(f"Horários disponíveis: {len(available_slots)}")
        if available_slots:
            for i, slot in enumerate(available_slots[:10], 1):
                print(f"  {i}. {slot}")
        
    except Exception as e:
        print(f"❌ Erro ao acessar Google Calendar: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_real_calendar_access() 