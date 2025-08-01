#!/usr/bin/env python3
import os
import sys
from datetime import datetime
sys.path.append(os.path.dirname(__file__))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Empresa, Mensagem, Log
from config import Config

def check_test_status():
    """Verifica o status atual antes do teste"""
    engine = create_engine(Config.POSTGRES_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    session = SessionLocal()
    try:
        print("=== STATUS ATUAL - TINYTEAMS ===")
        print(f"📅 Hora: {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 50)
        
        # Verificar configurações da TinyTeams
        empresa = session.query(Empresa).filter(Empresa.slug == 'tinyteams').first()
        
        if empresa:
            print(f"🏢 Empresa: {empresa.nome}")
            print(f"   Status: {empresa.status}")
            print(f"   OpenAI: {'✅ Configurado' if empresa.openai_key else '❌ Não configurado'}")
            print(f"   Prompt: {'✅ Configurado' if empresa.prompt else '❌ Não configurado'}")
            print(f"   Buffer: {'✅ Ativo' if empresa.usar_buffer else '❌ Inativo'}")
            print(f"   Mensagem Quebrada: {'✅ Ativo' if empresa.mensagem_quebrada else '❌ Inativo'}")
        else:
            print("❌ Empresa TinyTeams não encontrada!")
            return
        
        # Verificar mensagens recentes
        recent_messages = session.query(Mensagem).filter(
            Mensagem.empresa == 'tinyteams'
        ).order_by(Mensagem.timestamp.desc()).limit(3).all()
        
        print(f"\n📱 Últimas mensagens ({len(recent_messages)}):")
        for msg in recent_messages:
            timestamp = msg.timestamp.strftime('%H:%M:%S') if msg.timestamp else 'N/A'
            print(f"   [{timestamp}] {msg.tipo}: {msg.conteudo[:50]}...")
        
        # Verificar logs recentes
        recent_logs = session.query(Log).filter(
            Log.message.contains('tinyteams')
        ).order_by(Log.timestamp.desc()).limit(5).all()
        
        print(f"\n📋 Logs recentes da TinyTeams ({len(recent_logs)}):")
        for log in recent_logs:
            timestamp = log.timestamp.strftime('%H:%M:%S') if log.timestamp else 'N/A'
            print(f"   [{timestamp}] {log.level}: {log.message}")
        
        print("\n" + "=" * 50)
        print("✅ Status verificado! Pode fazer o teste.")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    check_test_status() 