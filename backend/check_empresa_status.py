#!/usr/bin/env python3
import os
import sys
sys.path.append(os.path.dirname(__file__))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Empresa, Base
from config import Config

def check_empresa_status():
    """Verifica e corrige status das empresas"""
    engine = create_engine(Config.POSTGRES_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    session = SessionLocal()
    try:
        # Listar todas as empresas
        empresas = session.query(Empresa).all()
        
        print("=== Status das Empresas ===")
        for empresa in empresas:
            print(f"ID: {empresa.id}")
            print(f"Nome: {empresa.nome}")
            print(f"Slug: {empresa.slug}")
            print(f"Status: {empresa.status}")
            print("---")
            
            # Corrigir status para 'ativo' se estiver vazio ou 'inativo'
            if not empresa.status or empresa.status == 'inativo':
                empresa.status = 'ativo'
                print(f"✅ Corrigido status de '{empresa.slug}' para 'ativo'")
        
        # Commit das mudanças
        session.commit()
        print("\n✅ Status das empresas corrigidos!")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    check_empresa_status() 