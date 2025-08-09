#!/usr/bin/env python3
"""
Script para testar qual método de autenticação está sendo usado
"""

import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Empresa, EmpresaAPI, API
from config import Config
from integrations.google_calendar_service import GoogleCalendarService

def test_auth_method():
    """Testa qual método de autenticação está sendo usado"""
    try:
        # Configurar conexão com banco
        config = Config()
        engine = create_engine(config.POSTGRES_URL)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        # Buscar empresa TinyTeams
        empresa = session.query(Empresa).filter(Empresa.slug == 'tinyteams').first()
        if not empresa:
            print("❌ Empresa 'tinyteams' não encontrada")
            return
        
        print(f"✅ Empresa encontrada: {empresa.nome} (ID: {empresa.id})")
        
        # Buscar API Google Calendar
        google_calendar_api = session.query(API).filter(API.nome == 'Google Calendar').first()
        if not google_calendar_api:
            print("❌ API 'Google Calendar' não encontrada")
            return
        
        # Buscar configuração da empresa
        empresa_api = session.query(EmpresaAPI).filter(
            EmpresaAPI.empresa_id == empresa.id,
            EmpresaAPI.api_id == google_calendar_api.id
        ).first()
        
        if not empresa_api or not empresa_api.config:
            print("❌ Configuração do Google Calendar não encontrada")
            return
        
        config_data = empresa_api.config
        print("\n📋 Configuração atual:")
        print(f"   - google_calendar_enabled: {config_data.get('google_calendar_enabled')}")
        print(f"   - client_id: {config_data.get('client_id')}")
        print(f"   - client_secret: {config_data.get('client_secret')[:10] if config_data.get('client_secret') else 'N/A'}...")
        print(f"   - refresh_token: {config_data.get('refresh_token')[:20] if config_data.get('refresh_token') else 'N/A'}...")
        print(f"   - service_account: {'Presente' if config_data.get('google_calendar_service_account') else 'N/A'}")
        
        # Preparar configuração para o GoogleCalendarService
        calendar_config = {
            'google_calendar_enabled': config_data.get('google_calendar_enabled', True),
            'google_calendar_client_id': config_data.get('client_id'),
            'google_calendar_client_secret': config_data.get('client_secret'),
            'google_calendar_refresh_token': config_data.get('refresh_token'),
            'google_calendar_service_account': config_data.get('google_calendar_service_account')
        }
        
        print(f"\n🔧 Configuração para GoogleCalendarService:")
        print(f"   - google_calendar_enabled: {calendar_config['google_calendar_enabled']}")
        print(f"   - google_calendar_client_id: {calendar_config['google_calendar_client_id']}")
        print(f"   - google_calendar_client_secret: {calendar_config['google_calendar_client_secret'][:10] if calendar_config['google_calendar_client_secret'] else 'N/A'}...")
        print(f"   - google_calendar_refresh_token: {calendar_config['google_calendar_refresh_token'][:20] if calendar_config['google_calendar_refresh_token'] else 'N/A'}...")
        print(f"   - google_calendar_service_account: {'Presente' if calendar_config['google_calendar_service_account'] else 'N/A'}")
        
        # Testar autenticação
        print("\n🧪 Testando autenticação...")
        
        # Adicionar logging para ver qual método está sendo usado
        import logging
        logging.basicConfig(level=logging.INFO)
        
        calendar_service = GoogleCalendarService(calendar_config)
        
        if calendar_service.service:
            print("✅ Google Calendar autenticado com sucesso!")
            
            # Testar listar eventos
            try:
                events = calendar_service.list_events(
                    start_date="2024-01-01",
                    end_date="2024-12-31"
                )
                print(f"✅ Lista de eventos obtida: {len(events)} eventos encontrados")
                
                # Mostrar alguns eventos
                for i, event in enumerate(events[:3]):
                    print(f"   Evento {i+1}: {event.get('summary', 'Sem título')} - {event.get('start', {}).get('dateTime', event.get('start', {}).get('date', 'Sem data'))}")
                
            except Exception as e:
                print(f"❌ Erro ao listar eventos: {e}")
        else:
            print("❌ Falha na autenticação")
        
        session.close()
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        if 'session' in locals():
            session.close()

if __name__ == "__main__":
    test_auth_method() 