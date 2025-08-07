#!/usr/bin/env python3

import os
import sys
import json
import logging
from datetime import datetime

# Adicionar o diretório backend ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import Empresa, API, EmpresaAPI
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config import Config

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_apis_catalog():
    """Configura o catálogo de APIs disponíveis"""
    logger.info("🔧 Configurando catálogo de APIs...")
    
    try:
        engine = create_engine(Config().POSTGRES_URL)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        # Lista de APIs que o sistema suporta
        apis_to_create = [
            {
                "nome": "google_calendar",
                "descricao": "Google Calendar API para agendamento de reuniões",
                "url_documentacao": "https://developers.google.com/calendar",
                "url_base": "https://www.googleapis.com/calendar/v3",
                "tipo_auth": "oauth2",
                "logo_url": "https://developers.google.com/static/images/calendar-logo.png"
            },
            {
                "nome": "google_sheets",
                "descricao": "Google Sheets API para integração com planilhas",
                "url_documentacao": "https://developers.google.com/sheets",
                "url_base": "https://sheets.googleapis.com/v4",
                "tipo_auth": "oauth2",
                "logo_url": "https://developers.google.com/static/images/sheets-logo.png"
            },
            {
                "nome": "openai",
                "descricao": "OpenAI API para processamento de linguagem natural",
                "url_documentacao": "https://platform.openai.com/docs",
                "url_base": "https://api.openai.com/v1",
                "tipo_auth": "api_key",
                "logo_url": "https://openai.com/favicon.ico"
            },
            {
                "nome": "twilio",
                "descricao": "Twilio API para WhatsApp e SMS",
                "url_documentacao": "https://www.twilio.com/docs",
                "url_base": "https://api.twilio.com/2010-04-01",
                "tipo_auth": "api_key",
                "logo_url": "https://www.twilio.com/favicon.ico"
            },
            {
                "nome": "chatwoot",
                "descricao": "Chatwoot API para atendimento ao cliente",
                "url_documentacao": "https://www.chatwoot.com/developers/api",
                "url_base": "https://app.chatwoot.com/api/v1",
                "tipo_auth": "api_key",
                "logo_url": "https://www.chatwoot.com/favicon.ico"
            }
        ]
        
        # Criar ou atualizar APIs
        for api_data in apis_to_create:
            existing_api = session.query(API).filter(API.nome == api_data["nome"]).first()
            
            if existing_api:
                logger.info(f"✅ API {api_data['nome']} já existe")
            else:
                new_api = API(**api_data)
                session.add(new_api)
                logger.info(f"✅ API {api_data['nome']} criada")
        
        session.commit()
        logger.info("✅ Catálogo de APIs configurado")
        
        session.close()
        
    except Exception as e:
        logger.error(f"❌ Erro ao configurar APIs: {e}")
        raise

def migrate_empresa_configurations():
    """Migra as configurações da tabela empresas para empresa_apis"""
    logger.info("🔄 Migrando configurações para empresa_apis...")
    
    try:
        engine = create_engine(Config().POSTGRES_URL)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        # Buscar todas as empresas
        empresas = session.query(Empresa).all()
        
        # Buscar APIs
        apis = {api.nome: api for api in session.query(API).all()}
        
        for empresa in empresas:
            logger.info(f"📋 Migrando configurações da empresa: {empresa.nome}")
            
            # Configurações para migrar
            configs_to_migrate = {
                "google_calendar": {
                    "google_calendar_enabled": True,
                    "google_calendar_client_id": getattr(empresa, 'google_calendar_client_id', None),
                    "google_calendar_client_secret": getattr(empresa, 'google_calendar_client_secret', None),
                    "google_calendar_refresh_token": getattr(empresa, 'google_calendar_refresh_token', None)
                },
                "google_sheets": {
                    "google_sheets_id": getattr(empresa, 'google_sheets_id', None)
                },
                "openai": {
                    "openai_key": getattr(empresa, 'openai_key', None)
                },
                "twilio": {
                    "twilio_sid": getattr(empresa, 'twilio_sid', None),
                    "twilio_token": getattr(empresa, 'twilio_token', None),
                    "twilio_number": getattr(empresa, 'twilio_number', None)
                },
                "chatwoot": {
                    "chatwoot_token": getattr(empresa, 'chatwoot_token', None),
                    "chatwoot_inbox_id": getattr(empresa, 'chatwoot_inbox_id', None),
                    "chatwoot_origem": getattr(empresa, 'chatwoot_origem', None)
                }
            }
            
            # Migrar cada configuração
            for api_name, config in configs_to_migrate.items():
                if api_name not in apis:
                    logger.warning(f"⚠️ API {api_name} não encontrada no catálogo")
                    continue
                
                api = apis[api_name]
                
                # Verificar se já existe conexão
                existing_connection = session.query(EmpresaAPI).filter(
                    EmpresaAPI.empresa_id == empresa.id,
                    EmpresaAPI.api_id == api.id
                ).first()
                
                # Filtrar configurações que têm valores
                active_config = {k: v for k, v in config.items() if v is not None and v != ''}
                
                if active_config:  # Só criar se há configurações ativas
                    if existing_connection:
                        # Atualizar configuração existente
                        existing_connection.config = active_config
                        existing_connection.ativo = True
                        logger.info(f"   ✅ {api_name}: Configuração atualizada")
                    else:
                        # Criar nova conexão
                        new_connection = EmpresaAPI(
                            empresa_id=empresa.id,
                            api_id=api.id,
                            config=active_config,
                            ativo=True
                        )
                        session.add(new_connection)
                        logger.info(f"   ✅ {api_name}: Nova conexão criada")
                else:
                    logger.info(f"   ⚠️ {api_name}: Sem configurações ativas")
        
        session.commit()
        logger.info("✅ Migração concluída")
        
        session.close()
        
    except Exception as e:
        logger.error(f"❌ Erro na migração: {e}")
        raise

def verify_migration():
    """Verifica se a migração foi bem-sucedida"""
    logger.info("🔍 Verificando migração...")
    
    try:
        engine = create_engine(Config().POSTGRES_URL)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        # Buscar todas as empresas
        empresas = session.query(Empresa).all()
        
        for empresa in empresas:
            logger.info(f"📋 Verificando empresa: {empresa.nome}")
            
            # Buscar APIs conectadas
            connections = session.query(EmpresaAPI).filter(
                EmpresaAPI.empresa_id == empresa.id,
                EmpresaAPI.ativo == True
            ).all()
            
            if connections:
                logger.info(f"   ✅ {len(connections)} APIs conectadas:")
                for conn in connections:
                    api = session.query(API).filter(API.id == conn.api_id).first()
                    config_keys = list(conn.config.keys()) if conn.config else []
                    logger.info(f"      - {api.nome}: {config_keys}")
            else:
                logger.warning(f"   ⚠️ Nenhuma API conectada")
        
        session.close()
        
    except Exception as e:
        logger.error(f"❌ Erro na verificação: {e}")
        raise

def create_migration_summary():
    """Cria um resumo da migração"""
    logger.info("📊 Criando resumo da migração...")
    
    try:
        engine = create_engine(Config().POSTGRES_URL)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        # Estatísticas
        total_empresas = session.query(Empresa).count()
        total_apis = session.query(API).count()
        total_connections = session.query(EmpresaAPI).count()
        active_connections = session.query(EmpresaAPI).filter(EmpresaAPI.ativo == True).count()
        
        logger.info("📈 Resumo da Migração:")
        logger.info(f"   - Total de empresas: {total_empresas}")
        logger.info(f"   - Total de APIs: {total_apis}")
        logger.info(f"   - Total de conexões: {total_connections}")
        logger.info(f"   - Conexões ativas: {active_connections}")
        
        # Detalhes por empresa
        empresas = session.query(Empresa).all()
        for empresa in empresas:
            connections = session.query(EmpresaAPI).filter(
                EmpresaAPI.empresa_id == empresa.id,
                EmpresaAPI.ativo == True
            ).all()
            
            api_names = []
            for conn in connections:
                api = session.query(API).filter(API.id == conn.api_id).first()
                api_names.append(api.nome)
            
            logger.info(f"   - {empresa.nome}: {api_names}")
        
        session.close()
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar resumo: {e}")
        raise

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🔄 MIGRAÇÃO PARA EMPRESA_APIS")
    logger.info("=" * 60)
    
    try:
        # 1. Configurar catálogo de APIs
        setup_apis_catalog()
        
        # 2. Migrar configurações
        migrate_empresa_configurations()
        
        # 3. Verificar migração
        verify_migration()
        
        # 4. Criar resumo
        create_migration_summary()
        
        logger.info("=" * 60)
        logger.info("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Erro durante a migração: {e}")
        raise 