#!/usr/bin/env python3
"""
Script de teste para verificar horários ocupados no Google Calendar
"""

import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from integrations.google_calendar_service import GoogleCalendarService
from config import Config

def test_calendar_slots():
    """Testa a verificação de horários ocupados no Google Calendar"""
    
    print("🔍 Testando horários ocupados no Google Calendar...")
    
    # Configuração da empresa TinyTeams
    empresa_config = {
        'google_calendar_enabled': True,
        'google_calendar_client_id': os.getenv('GOOGLE_CALENDAR_CLIENT_ID'),
        'google_calendar_client_secret': os.getenv('GOOGLE_CALENDAR_CLIENT_SECRET'),
        'google_calendar_refresh_token': os.getenv('GOOGLE_CALENDAR_REFRESH_TOKEN'),
        'google_calendar_service_account': os.getenv('GOOGLE_CALENDAR_SERVICE_ACCOUNT'),
        'google_calendar_project_id': os.getenv('GOOGLE_CALENDAR_PROJECT_ID'),
        'google_calendar_client_email': os.getenv('GOOGLE_CALENDAR_CLIENT_EMAIL'),
        'google_sheets_id': os.getenv('GOOGLE_SHEETS_ID')
    }
    
    # Data de teste: 11 de agosto de 2025
    test_date = "2025-08-11"
    
    try:
        # Criar serviço do Google Calendar
        calendar_service = GoogleCalendarService(empresa_config)
        
        if not calendar_service.service:
            print("❌ Google Calendar não está autenticado")
            return
        
        print(f"✅ Google Calendar autenticado com sucesso")
        print(f"📅 Verificando horários para: {test_date}")
        
        # Verificar horários disponíveis
        available_slots = calendar_service.get_available_slots(test_date)
        
        print(f"\n📊 Resultados para {test_date}:")
        print(f"Total de horários disponíveis: {len(available_slots)}")
        
        if available_slots:
            print("\n🕐 Horários disponíveis:")
            for i, slot in enumerate(available_slots[:10], 1):  # Mostrar apenas os primeiros 10
                print(f"  {i}. {slot}")
        else:
            print("❌ Nenhum horário disponível encontrado")
        
        # Verificar eventos existentes
        print(f"\n📋 Verificando eventos existentes...")
        
        # Converter data para datetime
        start_date = datetime.strptime(test_date, '%Y-%m-%d')
        end_date = start_date + timedelta(days=1)
        
        events = calendar_service.list_events(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        print(f"Total de eventos encontrados: {len(events)}")
        
        if events:
            print("\n📅 Eventos existentes:")
            for i, event in enumerate(events, 1):
                start = event.get('start', {}).get('dateTime', 'Sem horário')
                summary = event.get('summary', 'Sem título')
                print(f"  {i}. {start} - {summary}")
        else:
            print("✅ Nenhum evento encontrado para esta data")
            
    except Exception as e:
        print(f"❌ Erro ao testar Google Calendar: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_calendar_slots() 