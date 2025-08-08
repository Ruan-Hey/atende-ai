#!/usr/bin/env python3
"""
Script para configurar OAuth2 do Google Calendar e obter refresh token
"""

import os
import json
import pickle
import logging
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Empresa, EmpresaAPI, API

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Scopes necessários para Google Calendar
SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events'
]

def setup_google_calendar_oauth():
    """Configura OAuth2 do Google Calendar e obtém refresh token"""
    logger.info("🔧 Configurando OAuth2 do Google Calendar...")
    
    try:
        # Verificar se existe arquivo de credenciais
        if not os.path.exists('credentials.json'):
            logger.error("❌ Arquivo 'credentials.json' não encontrado!")
            logger.info("📋 Para obter o arquivo credentials.json:")
            logger.info("1. Acesse https://console.cloud.google.com")
            logger.info("2. Crie um projeto ou selecione um existente")
            logger.info("3. Ative a Google Calendar API")
            logger.info("4. Vá em 'Credenciais' > 'Criar credenciais' > 'ID do cliente OAuth 2.0'")
            logger.info("5. Configure a tela de consentimento OAuth")
            logger.info("6. Baixe o arquivo JSON e renomeie para 'credentials.json'")
            return None
        
        # Fazer o fluxo de autenticação
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        
        # Salvar credenciais
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
        
        logger.info("✅ Autenticação OAuth2 concluída!")
        logger.info(f"📋 Refresh Token: {creds.refresh_token}")
        logger.info(f"📋 Client ID: {creds.client_id}")
        logger.info(f"📋 Client Secret: {creds.client_secret}")
        
        return {
            'refresh_token': creds.refresh_token,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret
        }
        
    except Exception as e:
        logger.error(f"❌ Erro na configuração OAuth2: {e}")
        return None

def update_empresa_google_calendar(refresh_token, client_id, client_secret):
    """Atualiza a configuração do Google Calendar na empresa TinyTeams"""
    logger.info("🔄 Atualizando configuração do Google Calendar...")
    
    try:
        engine = create_engine(Config().POSTGRES_URL)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        # Buscar empresa TinyTeams
        empresa = session.query(Empresa).filter(Empresa.slug == 'tinyteams').first()
        if not empresa:
            logger.error("❌ Empresa TinyTeams não encontrada!")
            return False
        
        # Buscar API Google Calendar
        api = session.query(API).filter(API.nome == 'Google Calendar').first()
        if not api:
            logger.error("❌ API Google Calendar não encontrada!")
            return False
        
        # Buscar ou criar conexão empresa-API
        empresa_api = session.query(EmpresaAPI).filter(
            EmpresaAPI.empresa_id == empresa.id,
            EmpresaAPI.api_id == api.id
        ).first()
        
        if not empresa_api:
            # Criar nova conexão
            empresa_api = EmpresaAPI(
                empresa_id=empresa.id,
                api_id=api.id,
                config={
                    'google_calendar_enabled': True,
                    'google_calendar_client_id': client_id,
                    'google_calendar_client_secret': client_secret,
                    'google_calendar_refresh_token': refresh_token
                },
                ativo=True
            )
            session.add(empresa_api)
            logger.info("✅ Nova conexão Google Calendar criada")
        else:
            # Atualizar configuração existente
            current_config = empresa_api.config or {}
            current_config.update({
                'google_calendar_enabled': True,
                'google_calendar_client_id': client_id,
                'google_calendar_client_secret': client_secret,
                'google_calendar_refresh_token': refresh_token
            })
            empresa_api.config = current_config
            empresa_api.ativo = True
            logger.info("✅ Configuração Google Calendar atualizada")
        
        session.commit()
        session.close()
        
        logger.info("✅ Google Calendar configurado com sucesso!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao atualizar configuração: {e}")
        return False

def test_google_calendar_integration():
    """Testa a integração com Google Calendar"""
    logger.info("🧪 Testando integração com Google Calendar...")
    
    try:
        from integrations.google_calendar_service import GoogleCalendarService
        
        # Configuração de teste
        config = {
            'google_calendar_enabled': True,
            'google_calendar_client_id': '1059500330674-9897p14tqvsotovp9fr1pd7dnklhjhgn.apps.googleusercontent.com',
            'google_calendar_client_secret': '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',
            'google_calendar_refresh_token': '1//04dX...'  # Será obtido do banco
        }
        
        # Buscar refresh token do banco
        engine = create_engine(Config().POSTGRES_URL)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        empresa = session.query(Empresa).filter(Empresa.slug == 'tinyteams').first()
        api = session.query(API).filter(API.nome == 'Google Calendar').first()
        
        if empresa and api:
            empresa_api = session.query(EmpresaAPI).filter(
                EmpresaAPI.empresa_id == empresa.id,
                EmpresaAPI.api_id == api.id
            ).first()
            
            if empresa_api and empresa_api.config:
                config['google_calendar_refresh_token'] = empresa_api.config.get('google_calendar_refresh_token')
        
        session.close()
        
        # Testar serviço
        calendar_service = GoogleCalendarService(config)
        
        if calendar_service.service:
            logger.info("✅ Google Calendar autenticado com sucesso!")
            
            # Testar busca de eventos
            from datetime import datetime, timedelta
            start_date = datetime.now().strftime('%Y-%m-%d')
            end_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
            
            try:
                events = calendar_service.list_events(start_date, end_date)
                logger.info(f"✅ Teste de busca de eventos: {len(events)} eventos encontrados")
                return True
            except Exception as e:
                logger.warning(f"⚠️ Erro ao buscar eventos: {e}")
                return False
        else:
            logger.warning("⚠️ Google Calendar não autenticado")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro no teste: {e}")
        return False

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🔧 CONFIGURADOR GOOGLE CALENDAR OAUTH2")
    logger.info("=" * 60)
    
    # 1. Configurar OAuth2
    oauth_config = setup_google_calendar_oauth()
    
    if oauth_config:
        # 2. Atualizar banco de dados
        success = update_empresa_google_calendar(
            oauth_config['refresh_token'],
            oauth_config['client_id'],
            oauth_config['client_secret']
        )
        
        if success:
            # 3. Testar integração
            test_google_calendar_integration()
    
    logger.info("=" * 60)
    logger.info("✅ CONFIGURAÇÃO CONCLUÍDA")
    logger.info("=" * 60) 