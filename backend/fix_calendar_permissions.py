#!/usr/bin/env python3
"""
Script para verificar e corrigir permissões do Google Calendar
"""

import os
import sys
from datetime import datetime, timedelta

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def fix_calendar_permissions():
    """Verifica e corrige permissões do Google Calendar"""
    
    print("🔧 Verificando e corrigindo permissões do Google Calendar...")
    
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
            
            # Verificar Service Account
            service_account_email = config.get('google_calendar_client_email')
            if not service_account_email:
                print("❌ Service Account email não encontrado")
                return
            
            print(f"Service Account: {service_account_email}")
            
            # Verificar se o Service Account tem acesso ao calendário pessoal
            personal_calendar = 'ruangimeneshey@gmail.com'
            
            print(f"\n🔍 Verificando acesso ao calendário: {personal_calendar}")
            
            try:
                # Tentar acessar o calendário pessoal
                events_result = calendar_service.service.events().list(
                    calendarId=personal_calendar,
                    timeMin='2025-08-11T00:00:00Z',
                    timeMax='2025-08-12T00:00:00Z',
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                events = events_result.get('items', [])
                print(f"✅ Acesso permitido! Eventos encontrados: {len(events)}")
                
                if events:
                    print("\n📅 Eventos encontrados:")
                    for i, event in enumerate(events, 1):
                        start = event.get('start', {}).get('dateTime', 'Sem horário')
                        summary = event.get('summary', 'Sem título')
                        print(f"  {i}. {start} - {summary}")
                        
            except Exception as e:
                print(f"❌ Acesso negado: {e}")
                print("\n🔧 Para corrigir isso:")
                print("1. Acesse seu Google Calendar")
                print("2. Vá em Configurações do calendário")
                print("3. Na aba 'Compartilhar com pessoas específicas'")
                print(f"4. Adicione: {service_account_email}")
                print("5. Dê permissão: 'Fazer alterações e gerenciar compartilhamento'")
                print("\nOu execute este comando no Google Cloud Console:")
                print(f"gcloud auth application-default login")
                print("E depois configure as credenciais OAuth2")
            
        finally:
            session.close()
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_calendar_permissions() 