#!/usr/bin/env python3
import os
import sys
sys.path.append(os.path.dirname(__file__))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Empresa
from config import Config

def check_tinyteams_config():
    """Verifica todas as configurações da TinyTeams"""
    engine = create_engine(Config.POSTGRES_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    session = SessionLocal()
    try:
        print("=== CONFIGURAÇÕES DA TINYTEAMS ===")
        
        # Buscar a TinyTeams
        empresa = session.query(Empresa).filter(Empresa.slug == 'tinyteams').first()
        
        if not empresa:
            print("❌ Empresa TinyTeams não encontrada!")
            return
        
        print(f"🏢 Empresa: {empresa.nome} ({empresa.slug})")
        print(f"   ID: {empresa.id}")
        print(f"   Status: {empresa.status}")
        print(f"   WhatsApp: {'✅ Configurado' if empresa.whatsapp_number else '❌ Não configurado'}")
        if empresa.whatsapp_number:
            print(f"      Número: {empresa.whatsapp_number}")
        
        print(f"   Prompt: {'✅ Configurado' if empresa.prompt else '❌ Não configurado'}")
        if empresa.prompt:
            print(f"      Conteúdo: {empresa.prompt}")
        
        print(f"   Mensagem Quebrada: {'✅ Ativo' if empresa.mensagem_quebrada else '❌ Inativo'}")
        print(f"   Buffer: {'✅ Ativo' if empresa.usar_buffer else '❌ Inativo'}")
        
        print(f"   OpenAI: {'✅ Configurado' if empresa.openai_key else '❌ Não configurado'}")
        print(f"   Google Sheets: {'✅ Configurado' if empresa.google_sheets_id else '❌ Não configurado'}")
        print(f"   Chatwoot: {'✅ Configurado' if empresa.chatwoot_token else '❌ Não configurado'}")
        print(f"   Webhook URL: {'✅ Configurado' if empresa.webhook_url else '❌ Não configurado'}")
        if empresa.webhook_url:
            print(f"      URL: {empresa.webhook_url}")
        
        # Verificar se há mensagens no buffer
        from models import Mensagem
        mensagens = session.query(Mensagem).filter(Mensagem.empresa == 'tinyteams').count()
        print(f"   Mensagens no banco: {mensagens}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    check_tinyteams_config() 