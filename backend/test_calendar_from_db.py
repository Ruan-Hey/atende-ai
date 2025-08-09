#!/usr/bin/env python3
"""
Teste que busca configurações do Google Calendar do banco de dados
"""

import os
import sys
from datetime import datetime, timedelta

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_calendar_from_db():
    """Testa acesso ao Google Calendar usando configurações do banco"""
    
    print("🔍 Testando Google Calendar com configurações do banco de dados...")
    
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
            # Buscar empresa TinyTeams
            empresa = session.query(Empresa).filter(Empresa.slug == 'tinyteams').first()
            if not empresa:
                print("❌ Empresa TinyTeams não encontrada no banco")
                return
            
            print(f"✅ Empresa encontrada: {empresa.nome}")
            
            # Buscar API do Google Calendar
            google_calendar_api = session.query(API).filter(API.nome == 'Google Calendar').first()
            if not google_calendar_api:
                print("❌ API Google Calendar não encontrada no banco")
                return
            
            print(f"✅ API Google Calendar encontrada")
            
            # Buscar configuração da empresa para Google Calendar
            empresa_api = session.query(EmpresaAPI).filter(
                EmpresaAPI.empresa_id == empresa.id,
                EmpresaAPI.api_id == google_calendar_api.id,
                EmpresaAPI.ativo == True
            ).first()
            
            if not empresa_api:
                print("❌ Configuração do Google Calendar não encontrada para TinyTeams")
                return
            
            print(f"✅ Configuração do Google Calendar encontrada")
            
            # Extrair configurações
            config = empresa_api.config or {}
            print(f"\n📋 Configurações encontradas:")
            for key, value in config.items():
                if value and len(str(value)) > 20:
                    print(f"  {key}: {str(value)[:20]}...")
                else:
                    print(f"  {key}: {value}")
            
            # Criar configuração para o serviço
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
            
            # Verificar se temos credenciais
            has_credentials = any([
                empresa_config.get('google_calendar_client_id'),
                empresa_config.get('google_calendar_service_account')
            ])
            
            if not has_credentials:
                print("❌ Credenciais do Google Calendar não configuradas no banco")
                return
            
            print(f"\n🔐 Tentando autenticar com Google Calendar...")
            calendar_service = GoogleCalendarService(empresa_config)
            
            if not calendar_service.service:
                print("❌ Falha na autenticação com Google Calendar")
                print("Verifique as credenciais no banco de dados")
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
            else:
                print("❌ Nenhum horário disponível encontrado")
            
        finally:
            session.close()
            
    except Exception as e:
        print(f"❌ Erro ao acessar Google Calendar: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_calendar_from_db() 