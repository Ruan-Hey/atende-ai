#!/usr/bin/env python3
import os
import sys
sys.path.append(os.path.dirname(__file__))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Empresa
from config import Config

def check_prompts():
    """Verifica os prompts das empresas"""
    engine = create_engine(Config.POSTGRES_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    session = SessionLocal()
    try:
        print("=== PROMPTS DAS EMPRESAS ===")
        
        empresas = session.query(Empresa).all()
        
        for empresa in empresas:
            print(f"\n🏢 {empresa.nome} ({empresa.slug})")
            print(f"   ID: {empresa.id}")
            print(f"   Prompt: {'✅ Configurado' if empresa.prompt else '❌ Não configurado'}")
            if empresa.prompt:
                print(f"   Conteúdo: {empresa.prompt}")
                print(f"   Tamanho: {len(empresa.prompt)} caracteres")
            print(f"   Mensagem Quebrada: {'✅ Ativo' if empresa.mensagem_quebrada else '❌ Inativo'}")
            print(f"   Buffer: {'✅ Ativo' if empresa.usar_buffer else '❌ Inativo'}")
            
    except Exception as e:
        print(f"❌ Erro: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    check_prompts() 