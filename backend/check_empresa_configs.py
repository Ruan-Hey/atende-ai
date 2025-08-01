#!/usr/bin/env python3
import os
import sys
sys.path.append(os.path.dirname(__file__))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Empresa, Base
from config import Config

def check_empresa_configs():
    """Verifica as configurações das empresas"""
    engine = create_engine(Config.POSTGRES_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    session = SessionLocal()
    try:
        print("=== CONFIGURAÇÕES DAS EMPRESAS ===")
        
        empresas = session.query(Empresa).all()
        
        for empresa in empresas:
            print(f"\n🏢 {empresa.nome} ({empresa.slug})")
            print(f"   ID: {empresa.id}")
            print(f"   Status: {empresa.status}")
            
            # Prompt
            print(f"   📝 Prompt: {'✅ Configurado' if empresa.prompt else '❌ Não configurado'}")
            if empresa.prompt:
                print(f"      Preview: {empresa.prompt[:100]}...")
            
            # Configurações
            print(f"   ⚙️  Mensagem Quebrada: {'✅ Ativo' if empresa.mensagem_quebrada else '❌ Inativo'}")
            print(f"   ⚙️  Buffer: {'✅ Ativo' if empresa.usar_buffer else '❌ Inativo'}")
            
            # APIs
            print(f"   🔑 OpenAI: {'✅ Configurado' if empresa.openai_key else '❌ Não configurado'}")
            print(f"   🔑 Google Sheets: {'✅ Configurado' if empresa.google_sheets_id else '❌ Não configurado'}")
            print(f"   🔑 Chatwoot: {'✅ Configurado' if empresa.chatwoot_token else '❌ Não configurado'}")
            
            # Outras configurações
            print(f"   📞 WhatsApp: {'✅ Configurado' if empresa.whatsapp_number else '❌ Não configurado'}")
            print(f"   🔗 Webhook: {'✅ Configurado' if empresa.webhook_url else '❌ Não configurado'}")
            
            print("   " + "-" * 50)
            
    except Exception as e:
        print(f"❌ Erro: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    check_empresa_configs() 