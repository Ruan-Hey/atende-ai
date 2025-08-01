#!/usr/bin/env python3
import os
import sys
sys.path.append(os.path.dirname(__file__))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Empresa
from config import Config

def config_openai_tinyteams():
    """Configura a chave da OpenAI para a TinyTeams"""
    engine = create_engine(Config.POSTGRES_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    session = SessionLocal()
    try:
        print("=== CONFIGURANDO OPENAI PARA TINYTEAMS ===")
        
        # Buscar a TinyTeams
        empresa = session.query(Empresa).filter(Empresa.slug == 'tinyteams').first()
        
        if not empresa:
            print("❌ Empresa TinyTeams não encontrada!")
            return
        
        print(f"🏢 Empresa: {empresa.nome} ({empresa.slug})")
        print(f"   OpenAI Key atual: {'✅ Configurado' if empresa.openai_key else '❌ Não configurado'}")
        
        # Solicitar a chave da OpenAI
        print("\n🔑 Digite a chave da OpenAI para a TinyTeams:")
        openai_key = input("Chave: ").strip()
        
        if not openai_key:
            print("❌ Chave não fornecida!")
            return
        
        # Atualizar a chave
        empresa.openai_key = openai_key
        session.commit()
        
        print(f"   ✅ OpenAI Key configurada!")
        print(f"   Preview: {openai_key[:10]}...{openai_key[-4:]}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    config_openai_tinyteams() 