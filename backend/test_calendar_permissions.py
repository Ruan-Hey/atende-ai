#!/usr/bin/env python3
"""
Teste para verificar permissões do Google Calendar
"""

import os
import sys
from datetime import datetime, timedelta

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_calendar_permissions():
    """Testa permissões do Google Calendar"""
    
    print("🔍 Testando permissões do Google Calendar...")
    
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from models import Empresa, EmpresaAPI, API
        from config import Config
        from integrations.google_calendar_service import GoogleCalendarService
        
        # Conectar ao banco
        engine = create_engine(Config.POSTGRES_URL)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        try:
            # Buscar configurações
            empresa = session.query(Empresa).filter(Empresa.slug == 'tinyteams').first()
            google_calendar_api = session.query(API).filter(API.nome == 'Google Calendar').first()
            empresa_api = session.query(EmpresaAPI).filter(
                EmpresaAPI.empresa_id == empresa.id,
                EmpresaAPI.api_id == google_calendar_api.id,
                EmpresaAPI.ativo == True
            ).first()
            
            config = empresa_api.config or {}
            empresa_config = {
                'google_calendar_enabled': True,
                'google_calendar_client_id': config.get('google_calendar_client_id'),
                'google_calendar_client_secret': config.get('google_calendar_client_secret'),
                'google_calendar_refresh_token': config.get('google_calendar_refresh_token'),
                'google_calendar_service_account': config.get('google_calendar_service_account'),
                'google_calendar_project_id': config.get('google_calendar_project_id'),
                'google_calendar_client_email': config.get('google_calendar_client_email'),
                'google_sheets_id': config.get('google_sheets_id')
            }
            
            print("✅ Configurações carregadas")
            
            # Criar serviço
            calendar_service = GoogleCalendarService(empresa_config)
            
            if not calendar_service.service:
                print("❌ Falha na autenticação")
                return
            
            print("✅ Google Calendar autenticado")
            
            # Testar diferentes calendários
            test_calendars = [
                'primary',  # Calendário primário
                'teinyteams-calendar@tinyteams-calendar-456789.iam.gserviceaccount.com',  # Service Account
                'ruangimeneshey@gmail.com',  # Seu email pessoal
            ]
            
            test_date = "2025-08-11"
            start_date = datetime.strptime(test_date, '%Y-%m-%d')
            end_date = start_date + timedelta(days=1)
            
            for calendar_id in test_calendars:
                print(f"\n🔍 Testando calendário: {calendar_id}")
                
                try:
                    # Tentar listar eventos do calendário específico
                    events_result = calendar_service.service.events().list(
                        calendarId=calendar_id,
                        timeMin=start_date.isoformat() + 'Z',
                        timeMax=end_date.isoformat() + 'Z',
                        singleEvents=True,
                        orderBy='startTime'
                    ).execute()
                    
                    events = events_result.get('items', [])
                    print(f"  Eventos encontrados: {len(events)}")
                    
                    if events:
                        print("  📅 Eventos:")
                        for i, event in enumerate(events, 1):
                            start = event.get('start', {}).get('dateTime', 'Sem horário')
                            summary = event.get('summary', 'Sem título')
                            print(f"    {i}. {start} - {summary}")
                    else:
                        print("  ❌ Nenhum evento encontrado")
                        
                except Exception as e:
                    print(f"  ❌ Erro ao acessar calendário {calendar_id}: {e}")
            
            # Testar permissões do Service Account
            print(f"\n🔐 Verificando permissões do Service Account...")
            try:
                service_account_email = config.get('google_calendar_client_email')
                if service_account_email:
                    print(f"Service Account: {service_account_email}")
                    
                    # Tentar acessar calendário do Service Account
                    events_result = calendar_service.service.events().list(
                        calendarId=service_account_email,
                        timeMin=start_date.isoformat() + 'Z',
                        timeMax=end_date.isoformat() + 'Z',
                        singleEvents=True,
                        orderBy='startTime'
                    ).execute()
                    
                    events = events_result.get('items', [])
                    print(f"Eventos no Service Account: {len(events)}")
                    
                    if events:
                        for i, event in enumerate(events, 1):
                            start = event.get('start', {}).get('dateTime', 'Sem horário')
                            summary = event.get('summary', 'Sem título')
                            print(f"  {i}. {start} - {summary}")
                            
            except Exception as e:
                print(f"Erro ao verificar Service Account: {e}")
            
        finally:
            session.close()
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_calendar_permissions() 