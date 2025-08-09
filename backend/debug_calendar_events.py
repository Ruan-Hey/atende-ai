#!/usr/bin/env python3
"""
Debug para investigar por que os eventos não estão sendo encontrados
"""

import os
import sys
from datetime import datetime, timedelta

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def debug_calendar_events():
    """Debug para investigar eventos do Google Calendar"""
    
    print("🔍 Debug: Investigando eventos do Google Calendar...")
    
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
            
            print("✅ Configurações carregadas do banco")
            
            # Criar serviço
            calendar_service = GoogleCalendarService(empresa_config)
            
            if not calendar_service.service:
                print("❌ Falha na autenticação")
                return
            
            print("✅ Google Calendar autenticado")
            
            # Testar diferentes períodos
            test_date = "2025-08-11"
            start_date = datetime.strptime(test_date, '%Y-%m-%d')
            end_date = start_date + timedelta(days=1)
            
            print(f"\n📅 Testando período: {start_date} até {end_date}")
            
            # Testar list_events
            print("\n🔍 Testando list_events...")
            events = calendar_service.list_events(
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )
            
            print(f"Eventos encontrados: {len(events)}")
            
            if events:
                print("\n📅 Eventos encontrados:")
                for i, event in enumerate(events, 1):
                    start = event.get('start', {})
                    end = event.get('end', {})
                    summary = event.get('summary', 'Sem título')
                    
                    print(f"  {i}. {summary}")
                    print(f"     Início: {start}")
                    print(f"     Fim: {end}")
                    print(f"     ID: {event.get('id')}")
            else:
                print("❌ Nenhum evento encontrado")
                
                # Testar com período maior
                print(f"\n🔍 Testando período maior (7 dias)...")
                end_date_extended = start_date + timedelta(days=7)
                events_extended = calendar_service.list_events(
                    start_date.strftime('%Y-%m-%d'),
                    end_date_extended.strftime('%Y-%m-%d')
                )
                
                print(f"Eventos em 7 dias: {len(events_extended)}")
                
                if events_extended:
                    print("\n📅 Eventos encontrados (7 dias):")
                    for i, event in enumerate(events_extended, 1):
                        start = event.get('start', {})
                        summary = event.get('summary', 'Sem título')
                        print(f"  {i}. {start} - {summary}")
                
                # Testar calendário primário
                print(f"\n🔍 Testando calendário primário...")
                try:
                    calendar_list = calendar_service.service.calendarList().list().execute()
                    print(f"Calendários disponíveis: {len(calendar_list.get('items', []))}")
                    
                    for calendar in calendar_list.get('items', []):
                        print(f"  - {calendar.get('summary')} ({calendar.get('id')})")
                        
                except Exception as e:
                    print(f"Erro ao listar calendários: {e}")
            
        finally:
            session.close()
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_calendar_events() 