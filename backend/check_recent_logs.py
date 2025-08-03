#!/usr/bin/env python3
"""
Script para verificar logs recentes relacionados a configurações e erros
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Base, Log, Empresa
from config import Config
from datetime import datetime, timedelta

def check_recent_logs():
    """Verifica logs recentes relacionados a configurações"""
    
    print("🔍 Verificando logs recentes...")
    print(f"📊 Conectando ao banco: {Config.POSTGRES_URL}")
    
    try:
        # Criar engine e sessão
        engine = create_engine(Config.POSTGRES_URL)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Buscar logs das últimas 24 horas
        ontem = datetime.now() - timedelta(hours=24)
        
        logs_recentes = session.query(Log).filter(
            Log.timestamp >= ontem
        ).order_by(Log.timestamp.desc()).limit(50).all()
        
        print(f"\n📋 Encontrados {len(logs_recentes)} logs recentes:")
        print("=" * 80)
        
        if not logs_recentes:
            print("❌ Nenhum log encontrado nas últimas 24 horas!")
            return
        
        for log in logs_recentes:
            empresa_nome = "Sistema" if not log.empresa else log.empresa.nome
            print(f"\n🕐 {log.timestamp}")
            print(f"   📊 Nível: {log.level}")
            print(f"   🏢 Empresa: {empresa_nome}")
            print(f"   📝 Mensagem: {log.message}")
            if log.details:
                print(f"   🔍 Detalhes: {log.details}")
            print("-" * 50)
        
        # Buscar logs específicos de configuração
        print(f"\n🔍 Logs relacionados a configurações:")
        print("=" * 80)
        
        logs_config = session.query(Log).filter(
            Log.message.ilike('%config%') |
            Log.message.ilike('%openai%') |
            Log.message.ilike('%empresa%') |
            Log.message.ilike('%salvar%') |
            Log.message.ilike('%atualizar%')
        ).order_by(Log.timestamp.desc()).limit(20).all()
        
        print(f"📊 Total de logs de configuração: {len(logs_config)}")
        
        for log in logs_config:
            empresa_nome = "Sistema" if not log.empresa else log.empresa.nome
            print(f"   🕐 {log.timestamp} - {log.level} - {empresa_nome}: {log.message}")
        
        # Verificar logs de erro
        print(f"\n❌ Logs de erro recentes:")
        print("=" * 80)
        
        logs_erro = session.query(Log).filter(
            Log.level == 'ERROR'
        ).order_by(Log.timestamp.desc()).limit(10).all()
        
        print(f"📊 Total de logs de erro: {len(logs_erro)}")
        
        for log in logs_erro:
            empresa_nome = "Sistema" if not log.empresa else log.empresa.nome
            print(f"   🕐 {log.timestamp} - {empresa_nome}: {log.message}")
        
        session.close()
        
    except Exception as e:
        print(f"❌ Erro ao conectar ao banco: {e}")
        return

if __name__ == "__main__":
    check_recent_logs() 