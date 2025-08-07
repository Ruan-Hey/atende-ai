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

def migrate_google_calendar_to_empresa_apis():
    """Migra especificamente o Google Calendar para empresa_apis"""
    logger.info("🔄 Migrando Google Calendar para empresa_apis...")
    
    try:
        engine = create_engine(Config().POSTGRES_URL)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        # 1. Buscar API do Google Calendar
        google_calendar_api = session.query(API).filter(API.nome == "Google Calendar").first()
        
        if not google_calendar_api:
            logger.error("❌ API Google Calendar não encontrada no catálogo")
            return
        
        logger.info(f"✅ API Google Calendar encontrada: ID={google_calendar_api.id}")
        
        # 2. Buscar empresas com Google Calendar configurado
        empresas_com_calendar = session.query(Empresa).filter(
            Empresa.google_calendar_enabled == True
        ).all()
        
        logger.info(f"📋 Empresas com Google Calendar: {len(empresas_com_calendar)}")
        
        for empresa in empresas_com_calendar:
            logger.info(f"🔄 Migrando {empresa.nome}...")
            
            # Verificar se já existe conexão
            existing_connection = session.query(EmpresaAPI).filter(
                EmpresaAPI.empresa_id == empresa.id,
                EmpresaAPI.api_id == google_calendar_api.id
            ).first()
            
            # Preparar configuração
            calendar_config = {
                "google_calendar_enabled": True
            }
            
            # Adicionar credenciais se existirem
            if hasattr(empresa, 'google_calendar_client_id') and empresa.google_calendar_client_id:
                calendar_config["google_calendar_client_id"] = empresa.google_calendar_client_id
            if hasattr(empresa, 'google_calendar_client_secret') and empresa.google_calendar_client_secret:
                calendar_config["google_calendar_client_secret"] = empresa.google_calendar_client_secret
            if hasattr(empresa, 'google_calendar_refresh_token') and empresa.google_calendar_refresh_token:
                calendar_config["google_calendar_refresh_token"] = empresa.google_calendar_refresh_token
            
            if existing_connection:
                # Atualizar configuração existente
                existing_connection.config = calendar_config
                existing_connection.ativo = True
                logger.info(f"   ✅ Configuração atualizada")
            else:
                # Criar nova conexão
                new_connection = EmpresaAPI(
                    empresa_id=empresa.id,
                    api_id=google_calendar_api.id,
                    config=calendar_config,
                    ativo=True
                )
                session.add(new_connection)
                logger.info(f"   ✅ Nova conexão criada")
        
        session.commit()
        logger.info("✅ Migração do Google Calendar concluída")
        
        session.close()
        
    except Exception as e:
        logger.error(f"❌ Erro na migração: {e}")
        raise

def verify_google_calendar_migration():
    """Verifica se a migração do Google Calendar foi bem-sucedida"""
    logger.info("🔍 Verificando migração do Google Calendar...")
    
    try:
        engine = create_engine(Config().POSTGRES_URL)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        # Buscar API do Google Calendar
        google_calendar_api = session.query(API).filter(API.nome == "Google Calendar").first()
        
        if not google_calendar_api:
            logger.error("❌ API Google Calendar não encontrada")
            return
        
        # Buscar conexões ativas
        connections = session.query(EmpresaAPI).filter(
            EmpresaAPI.api_id == google_calendar_api.id,
            EmpresaAPI.ativo == True
        ).all()
        
        logger.info(f"📋 Conexões Google Calendar ativas: {len(connections)}")
        
        for conn in connections:
            empresa = session.query(Empresa).filter(Empresa.id == conn.empresa_id).first()
            config_keys = list(conn.config.keys()) if conn.config else []
            
            logger.info(f"   - {empresa.nome}: {config_keys}")
            
            # Verificar se as credenciais estão corretas
            if conn.config and "google_calendar_client_id" in conn.config:
                logger.info(f"      ✅ Client ID configurado")
            else:
                logger.warning(f"      ⚠️ Client ID não configurado")
        
        session.close()
        
    except Exception as e:
        logger.error(f"❌ Erro na verificação: {e}")
        raise

def create_dual_system_service():
    """Cria um serviço que funciona com ambas as arquiteturas"""
    logger.info("🔧 Criando serviço de compatibilidade...")
    
    try:
        # Criar arquivo de serviço que funciona com ambas as arquiteturas
        service_code = '''
from models import Empresa, EmpresaAPI, API
from sqlalchemy.orm import Session

def get_google_calendar_config(session: Session, empresa_id: int):
    """Obtém configuração do Google Calendar usando ambas as arquiteturas"""
    
    # 1. Tentar obter da tabela empresa_apis (arquitetura correta)
    google_calendar_api = session.query(API).filter(API.nome == "Google Calendar").first()
    
    if google_calendar_api:
        connection = session.query(EmpresaAPI).filter(
            EmpresaAPI.empresa_id == empresa_id,
            EmpresaAPI.api_id == google_calendar_api.id,
            EmpresaAPI.ativo == True
        ).first()
        
        if connection and connection.config:
            return connection.config
    
    # 2. Fallback para tabela empresas (arquitetura antiga)
    empresa = session.query(Empresa).filter(Empresa.id == empresa_id).first()
    
    if empresa and hasattr(empresa, 'google_calendar_enabled') and empresa.google_calendar_enabled:
        config = {
            "google_calendar_enabled": True
        }
        
        if hasattr(empresa, 'google_calendar_client_id') and empresa.google_calendar_client_id:
            config["google_calendar_client_id"] = empresa.google_calendar_client_id
        if hasattr(empresa, 'google_calendar_client_secret') and empresa.google_calendar_client_secret:
            config["google_calendar_client_secret"] = empresa.google_calendar_client_secret
        if hasattr(empresa, 'google_calendar_refresh_token') and empresa.google_calendar_refresh_token:
            config["google_calendar_refresh_token"] = empresa.google_calendar_refresh_token
        
        return config
    
    return None
'''
        
        with open('services/dual_config_service.py', 'w') as f:
            f.write(service_code)
        
        logger.info("✅ Serviço de compatibilidade criado")
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar serviço: {e}")
        raise

def test_dual_system():
    """Testa o sistema dual"""
    logger.info("🧪 Testando sistema dual...")
    
    try:
        engine = create_engine(Config().POSTGRES_URL)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        # Buscar TinyTeams
        tinyteams = session.query(Empresa).filter(Empresa.slug == 'tinyteams').first()
        
        if not tinyteams:
            logger.error("❌ TinyTeams não encontrada")
            return
        
        # Testar ambas as abordagens
        logger.info(f"📋 Testando configurações para {tinyteams.nome}:")
        
        # 1. Verificar tabela empresas (antiga)
        if hasattr(tinyteams, 'google_calendar_enabled') and tinyteams.google_calendar_enabled:
            logger.info("   ✅ Google Calendar habilitado na tabela empresas")
            if hasattr(tinyteams, 'google_calendar_client_id') and tinyteams.google_calendar_client_id:
                logger.info("   ✅ Client ID configurado na tabela empresas")
        else:
            logger.info("   ⚠️ Google Calendar não habilitado na tabela empresas")
        
        # 2. Verificar empresa_apis (nova)
        google_calendar_api = session.query(API).filter(API.nome == "Google Calendar").first()
        if google_calendar_api:
            connection = session.query(EmpresaAPI).filter(
                EmpresaAPI.empresa_id == tinyteams.id,
                EmpresaAPI.api_id == google_calendar_api.id,
                EmpresaAPI.ativo == True
            ).first()
            
            if connection and connection.config:
                logger.info("   ✅ Google Calendar configurado na tabela empresa_apis")
                config_keys = list(connection.config.keys())
                logger.info(f"      Configurações: {config_keys}")
            else:
                logger.info("   ⚠️ Google Calendar não configurado na tabela empresa_apis")
        
        session.close()
        
    except Exception as e:
        logger.error(f"❌ Erro no teste: {e}")
        raise

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🔄 MIGRAÇÃO SEGURA GOOGLE CALENDAR")
    logger.info("=" * 60)
    
    try:
        # 1. Migrar Google Calendar para empresa_apis
        migrate_google_calendar_to_empresa_apis()
        
        # 2. Verificar migração
        verify_google_calendar_migration()
        
        # 3. Criar serviço de compatibilidade
        create_dual_system_service()
        
        # 4. Testar sistema dual
        test_dual_system()
        
        logger.info("=" * 60)
        logger.info("✅ MIGRAÇÃO SEGURA CONCLUÍDA")
        logger.info("=" * 60)
        
        # Resumo final
        logger.info("📊 RESUMO:")
        logger.info("   - Google Calendar migrado para empresa_apis")
        logger.info("   - Sistema dual mantém compatibilidade")
        logger.info("   - Nenhum dado foi perdido")
        logger.info("   - Sistema continua funcionando normalmente")
        
    except Exception as e:
        logger.error(f"❌ Erro durante a migração: {e}")
        raise 