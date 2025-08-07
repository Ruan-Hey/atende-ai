#!/usr/bin/env python3

import os
import sys
import json
import logging
from datetime import datetime

# Adicionar o diretório backend ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import Empresa
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config import Config

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_database_schema():
    """Verifica a estrutura da tabela empresas"""
    logger.info("🔍 Verificando estrutura da tabela empresas...")
    
    try:
        engine = create_engine(Config().POSTGRES_URL)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        # Verificar se existem colunas para Google Calendar
        result = session.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'empresas' 
            AND column_name LIKE '%google%'
        """))
        
        google_columns = result.fetchall()
        
        if google_columns:
            logger.info("✅ Colunas do Google Calendar encontradas:")
            for col in google_columns:
                logger.info(f"   - {col[0]}: {col[1]}")
        else:
            logger.warning("⚠️ Nenhuma coluna específica do Google Calendar encontrada")
        
        # Verificar se existe coluna JSON para configurações
        result = session.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'empresas' 
            AND data_type = 'json'
        """))
        
        json_columns = result.fetchall()
        
        if json_columns:
            logger.info("✅ Colunas JSON encontradas:")
            for col in json_columns:
                logger.info(f"   - {col[0]}: {col[1]}")
        else:
            logger.warning("⚠️ Nenhuma coluna JSON encontrada")
        
        session.close()
        
    except Exception as e:
        logger.error(f"❌ Erro ao verificar schema: {e}")

def check_tinyteams_credentials():
    """Verifica as credenciais da TinyTeams no banco"""
    logger.info("🔍 Verificando credenciais da TinyTeams...")
    
    try:
        engine = create_engine(Config().POSTGRES_URL)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        # Buscar TinyTeams
        tinyteams = session.query(Empresa).filter(Empresa.slug == 'tinyteams').first()
        
        if not tinyteams:
            logger.error("❌ Empresa TinyTeams não encontrada!")
            return
        
        logger.info(f"✅ TinyTeams encontrada: ID={tinyteams.id}")
        
        # Verificar campos relacionados ao Google Calendar
        google_fields = {
            'google_sheets_id': tinyteams.google_sheets_id,
            'openai_key': tinyteams.openai_key,
            'twilio_sid': tinyteams.twilio_sid,
            'twilio_token': tinyteams.twilio_token,
            'twilio_number': tinyteams.twilio_number,
            'chatwoot_token': tinyteams.chatwoot_token,
        }
        
        logger.info("📋 Campos da TinyTeams:")
        for field, value in google_fields.items():
            if value:
                logger.info(f"   ✅ {field}: {value[:20]}..." if len(str(value)) > 20 else f"   ✅ {field}: {value}")
            else:
                logger.warning(f"   ⚠️ {field}: Não configurado")
        
        # Verificar se existe campo JSON para configurações
        try:
            # Tentar acessar campo JSON se existir
            if hasattr(tinyteams, 'filtros_chatwoot') and tinyteams.filtros_chatwoot:
                logger.info(f"   ✅ filtros_chatwoot: {tinyteams.filtros_chatwoot}")
            else:
                logger.warning("   ⚠️ filtros_chatwoot: Não configurado")
        except:
            logger.warning("   ⚠️ Campo filtros_chatwoot não encontrado")
        
        session.close()
        
    except Exception as e:
        logger.error(f"❌ Erro ao verificar credenciais: {e}")

def add_google_calendar_columns():
    """Adiciona colunas para Google Calendar se não existirem"""
    logger.info("🔧 Verificando se precisamos adicionar colunas do Google Calendar...")
    
    try:
        engine = create_engine(Config().POSTGRES_URL)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        # Verificar se existem colunas do Google Calendar
        result = session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'empresas' 
            AND column_name IN ('google_calendar_client_id', 'google_calendar_client_secret', 'google_calendar_refresh_token')
        """))
        
        existing_columns = [row[0] for row in result.fetchall()]
        
        if len(existing_columns) < 3:
            logger.info("🔧 Adicionando colunas do Google Calendar...")
            
            # Adicionar colunas que faltam
            columns_to_add = [
                'google_calendar_client_id',
                'google_calendar_client_secret', 
                'google_calendar_refresh_token',
                'google_calendar_enabled'
            ]
            
            for column in columns_to_add:
                if column not in existing_columns:
                    try:
                        if column == 'google_calendar_enabled':
                            session.execute(text(f"ALTER TABLE empresas ADD COLUMN {column} BOOLEAN DEFAULT FALSE"))
                        else:
                            session.execute(text(f"ALTER TABLE empresas ADD COLUMN {column} VARCHAR(255)"))
                        logger.info(f"   ✅ Coluna {column} adicionada")
                    except Exception as e:
                        logger.warning(f"   ⚠️ Erro ao adicionar {column}: {e}")
            
            session.commit()
            logger.info("✅ Colunas do Google Calendar configuradas")
        else:
            logger.info("✅ Colunas do Google Calendar já existem")
        
        session.close()
        
    except Exception as e:
        logger.error(f"❌ Erro ao adicionar colunas: {e}")

def update_tinyteams_google_calendar():
    """Atualiza as credenciais do Google Calendar da TinyTeams"""
    logger.info("🔧 Atualizando credenciais do Google Calendar da TinyTeams...")
    
    try:
        engine = create_engine(Config().POSTGRES_URL)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        # Buscar TinyTeams
        tinyteams = session.query(Empresa).filter(Empresa.slug == 'tinyteams').first()
        
        if not tinyteams:
            logger.error("❌ Empresa TinyTeams não encontrada!")
            return
        
        # Verificar se as colunas existem
        result = session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'empresas' 
            AND column_name IN ('google_calendar_client_id', 'google_calendar_client_secret', 'google_calendar_refresh_token', 'google_calendar_enabled')
        """))
        
        existing_columns = [row[0] for row in result.fetchall()]
        
        if len(existing_columns) < 4:
            logger.warning("⚠️ Colunas do Google Calendar não encontradas. Execute add_google_calendar_columns() primeiro.")
            return
        
        # Atualizar credenciais (exemplo - você deve substituir pelos valores reais)
        update_data = {
            'google_calendar_enabled': True,
            'google_calendar_client_id': '1059500330674-9897p14tqvsotovp9fr1pd7dnklhjhgn.apps.googleusercontent.com',
            'google_calendar_client_secret': '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',
            'google_calendar_refresh_token': ''  # Será preenchido após autenticação
        }
        
        # Atualizar cada campo
        for field, value in update_data.items():
            try:
                session.execute(text(f"UPDATE empresas SET {field} = :value WHERE id = :id"), 
                              {'value': value, 'id': tinyteams.id})
                logger.info(f"   ✅ {field} atualizado")
            except Exception as e:
                logger.error(f"   ❌ Erro ao atualizar {field}: {e}")
        
        session.commit()
        logger.info("✅ Credenciais do Google Calendar atualizadas")
        
        session.close()
        
    except Exception as e:
        logger.error(f"❌ Erro ao atualizar credenciais: {e}")

def test_google_calendar_integration():
    """Testa a integração com Google Calendar após configuração"""
    logger.info("🧪 Testando integração com Google Calendar...")
    
    try:
        engine = create_engine(Config().POSTGRES_URL)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        # Buscar TinyTeams
        tinyteams = session.query(Empresa).filter(Empresa.slug == 'tinyteams').first()
        
        if not tinyteams:
            logger.error("❌ Empresa TinyTeams não encontrada!")
            return
        
        # Verificar se as credenciais estão configuradas
        result = session.execute(text("""
            SELECT google_calendar_enabled, google_calendar_client_id, google_calendar_client_secret
            FROM empresas WHERE slug = 'tinyteams'
        """))
        
        row = result.fetchone()
        if row:
            enabled, client_id, client_secret = row
            
            logger.info(f"📋 Status do Google Calendar:")
            logger.info(f"   - Habilitado: {enabled}")
            logger.info(f"   - Client ID: {client_id[:30]}..." if client_id else "   - Client ID: Não configurado")
            logger.info(f"   - Client Secret: {'Configurado' if client_secret else 'Não configurado'}")
            
            if enabled and client_id and client_secret:
                logger.info("✅ Google Calendar configurado corretamente!")
            else:
                logger.warning("⚠️ Google Calendar não está completamente configurado")
        
        session.close()
        
    except Exception as e:
        logger.error(f"❌ Erro ao testar integração: {e}")

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🔧 VERIFICADOR DE CREDENCIAIS GOOGLE CALENDAR")
    logger.info("=" * 60)
    
    # 1. Verificar estrutura do banco
    check_database_schema()
    
    # 2. Verificar credenciais atuais
    check_tinyteams_credentials()
    
    # 3. Adicionar colunas se necessário
    add_google_calendar_columns()
    
    # 4. Atualizar credenciais
    update_tinyteams_google_calendar()
    
    # 5. Testar integração
    test_google_calendar_integration()
    
    logger.info("=" * 60)
    logger.info("✅ VERIFICAÇÃO CONCLUÍDA")
    logger.info("=" * 60) 