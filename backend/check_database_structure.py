#!/usr/bin/env python3

import os
import sys
import logging
from datetime import datetime

# Adicionar o diretório backend ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import Empresa, API, EmpresaAPI
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from config import Config

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_database_structure():
    """Verifica a estrutura atual do banco de dados"""
    logger.info("🔍 Verificando estrutura atual do banco...")
    
    try:
        engine = create_engine(Config().POSTGRES_URL)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        # 1. Verificar se as tabelas existem
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        logger.info("📋 Tabelas existentes:")
        for table in existing_tables:
            logger.info(f"   - {table}")
        
        # 2. Verificar estrutura da tabela empresas
        if 'empresas' in existing_tables:
            logger.info("🏢 Estrutura da tabela 'empresas':")
            columns = inspector.get_columns('empresas')
            for column in columns:
                logger.info(f"   - {column['name']}: {column['type']}")
        
        # 3. Verificar estrutura da tabela apis
        if 'apis' in existing_tables:
            logger.info("🔗 Estrutura da tabela 'apis':")
            columns = inspector.get_columns('apis')
            for column in columns:
                logger.info(f"   - {column['name']}: {column['type']}")
        
        # 4. Verificar estrutura da tabela empresa_apis
        if 'empresa_apis' in existing_tables:
            logger.info("🔗 Estrutura da tabela 'empresa_apis':")
            columns = inspector.get_columns('empresa_apis')
            for column in columns:
                logger.info(f"   - {column['name']}: {column['type']}")
        
        session.close()
        
    except Exception as e:
        logger.error(f"❌ Erro ao verificar estrutura: {e}")
        raise

def check_current_data():
    """Verifica os dados atuais no banco"""
    logger.info("📊 Verificando dados atuais...")
    
    try:
        engine = create_engine(Config().POSTGRES_URL)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        # 1. Verificar empresas
        empresas = session.query(Empresa).all()
        logger.info(f"🏢 Empresas encontradas: {len(empresas)}")
        
        for empresa in empresas:
            logger.info(f"   - {empresa.nome} (ID: {empresa.id}, Slug: {empresa.slug})")
            
            # Verificar configurações ativas
            configs_ativas = []
            if empresa.openai_key:
                configs_ativas.append("OpenAI")
            if empresa.twilio_sid:
                configs_ativas.append("Twilio")
            if empresa.google_sheets_id:
                configs_ativas.append("Google Sheets")
            if empresa.chatwoot_token:
                configs_ativas.append("Chatwoot")
            
            if configs_ativas:
                logger.info(f"      Configurações ativas: {configs_ativas}")
            else:
                logger.info(f"      ⚠️ Sem configurações ativas")
        
        # 2. Verificar APIs
        apis = session.query(API).all()
        logger.info(f"🔗 APIs encontradas: {len(apis)}")
        
        for api in apis:
            logger.info(f"   - {api.nome} (ID: {api.id}, Tipo: {api.tipo_auth})")
        
        # 3. Verificar conexões empresa_apis
        connections = session.query(EmpresaAPI).all()
        logger.info(f"🔗 Conexões empresa_apis: {len(connections)}")
        
        for conn in connections:
            empresa = session.query(Empresa).filter(Empresa.id == conn.empresa_id).first()
            api = session.query(API).filter(API.id == conn.api_id).first()
            logger.info(f"   - {empresa.nome} ↔ {api.nome} (Ativo: {conn.ativo})")
        
        session.close()
        
    except Exception as e:
        logger.error(f"❌ Erro ao verificar dados: {e}")
        raise

def check_google_calendar_columns():
    """Verifica especificamente as colunas do Google Calendar"""
    logger.info("📅 Verificando colunas do Google Calendar...")
    
    try:
        engine = create_engine(Config().POSTGRES_URL)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        # Verificar se existem colunas do Google Calendar na tabela empresas
        inspector = inspect(engine)
        columns = inspector.get_columns('empresas')
        
        google_columns = [col for col in columns if 'google_calendar' in col['name']]
        
        if google_columns:
            logger.info("✅ Colunas do Google Calendar encontradas na tabela empresas:")
            for col in google_columns:
                logger.info(f"   - {col['name']}: {col['type']}")
        else:
            logger.info("⚠️ Nenhuma coluna do Google Calendar encontrada na tabela empresas")
        
        # Verificar dados do Google Calendar
        result = session.execute(text("""
            SELECT 
                nome,
                google_calendar_enabled,
                google_calendar_client_id,
                google_calendar_client_secret,
                google_calendar_refresh_token
            FROM empresas 
            WHERE google_calendar_enabled = true 
               OR google_calendar_client_id IS NOT NULL
        """))
        
        rows = result.fetchall()
        if rows:
            logger.info("📋 Dados do Google Calendar encontrados:")
            for row in rows:
                logger.info(f"   - {row[0]}: Habilitado={row[1]}, Client ID={'Sim' if row[2] else 'Não'}")
        else:
            logger.info("⚠️ Nenhum dado do Google Calendar encontrado")
        
        session.close()
        
    except Exception as e:
        logger.error(f"❌ Erro ao verificar Google Calendar: {e}")
        raise

def create_safe_migration_plan():
    """Cria um plano seguro de migração"""
    logger.info("📋 Criando plano de migração seguro...")
    
    try:
        engine = create_engine(Config().POSTGRES_URL)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        # Verificar o que precisa ser migrado
        empresas = session.query(Empresa).all()
        
        migration_plan = {
            "empresas_para_migrar": [],
            "apis_para_criar": [],
            "conexoes_para_criar": []
        }
        
        for empresa in empresas:
            empresa_plan = {
                "empresa": empresa.nome,
                "id": empresa.id,
                "configuracoes": {}
            }
            
            # Verificar configurações ativas
            if empresa.openai_key:
                empresa_plan["configuracoes"]["openai"] = {"openai_key": "***"}
            if empresa.twilio_sid:
                empresa_plan["configuracoes"]["twilio"] = {
                    "twilio_sid": "***",
                    "twilio_token": "***" if empresa.twilio_token else None,
                    "twilio_number": empresa.twilio_number
                }
            if empresa.google_sheets_id:
                empresa_plan["configuracoes"]["google_sheets"] = {"google_sheets_id": "***"}
            if empresa.chatwoot_token:
                empresa_plan["configuracoes"]["chatwoot"] = {
                    "chatwoot_token": "***",
                    "chatwoot_inbox_id": empresa.chatwoot_inbox_id,
                    "chatwoot_origem": empresa.chatwoot_origem
                }
            
            # Verificar Google Calendar
            if hasattr(empresa, 'google_calendar_enabled') and empresa.google_calendar_enabled:
                empresa_plan["configuracoes"]["google_calendar"] = {
                    "google_calendar_enabled": True,
                    "google_calendar_client_id": "***" if hasattr(empresa, 'google_calendar_client_id') and empresa.google_calendar_client_id else None,
                    "google_calendar_client_secret": "***" if hasattr(empresa, 'google_calendar_client_secret') and empresa.google_calendar_client_secret else None
                }
            
            if empresa_plan["configuracoes"]:
                migration_plan["empresas_para_migrar"].append(empresa_plan)
        
        # Mostrar plano
        logger.info("📋 Plano de Migração:")
        logger.info(f"   - Empresas para migrar: {len(migration_plan['empresas_para_migrar'])}")
        
        for empresa_plan in migration_plan["empresas_para_migrar"]:
            logger.info(f"   - {empresa_plan['empresa']}: {list(empresa_plan['configuracoes'].keys())}")
        
        session.close()
        
        return migration_plan
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar plano: {e}")
        raise

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🔍 VERIFICAÇÃO SEGURA DO BANCO")
    logger.info("=" * 60)
    
    try:
        # 1. Verificar estrutura
        check_database_structure()
        
        # 2. Verificar dados
        check_current_data()
        
        # 3. Verificar Google Calendar
        check_google_calendar_columns()
        
        # 4. Criar plano de migração
        migration_plan = create_safe_migration_plan()
        
        logger.info("=" * 60)
        logger.info("✅ VERIFICAÇÃO CONCLUÍDA")
        logger.info("=" * 60)
        
        # Resumo final
        logger.info("📊 RESUMO:")
        logger.info("   - Este script apenas VERIFICA, não modifica nada")
        logger.info("   - Execute a migração apenas após revisar os dados")
        logger.info("   - Faça backup antes de qualquer migração")
        
    except Exception as e:
        logger.error(f"❌ Erro durante a verificação: {e}")
        raise 