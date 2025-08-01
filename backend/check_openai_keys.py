#!/usr/bin/env python3
import os
import sys
sys.path.append(os.path.dirname(__file__))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Empresa
from config import Config

def check_openai_keys():
    """Verifica as chaves da OpenAI de todas as empresas"""
    engine = create_engine(Config.POSTGRES_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    session = SessionLocal()
    try:
        print("=== CHAVES DA OPENAI ===")
        
        empresas = session.query(Empresa).all()
        
        for empresa in empresas:
            print(f"\n🏢 {empresa.nome} ({empresa.slug})")
            print(f"   ID: {empresa.id}")
            print(f"   OpenAI Key: {'✅ Configurado' if empresa.openai_key else '❌ Não configurado'}")
            if empresa.openai_key:
                print(f"      Preview: {empresa.openai_key[:10]}...{empresa.openai_key[-4:]}")
            print(f"   Status: {empresa.status}")
            
    except Exception as e:
        print(f"❌ Erro: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    check_openai_keys() 