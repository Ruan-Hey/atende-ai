#!/usr/bin/env python3
import os
import sys
sys.path.append(os.path.dirname(__file__))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Empresa, Base
from config import Config

def debug_empresas():
    """Debug e corrige empresas no banco"""
    engine = create_engine(Config.POSTGRES_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    session = SessionLocal()
    try:
        print("=== DEBUG EMPRESAS ===")
        
        # Listar todas as empresas
        empresas = session.query(Empresa).all()
        
        if not empresas:
            print("❌ Nenhuma empresa encontrada no banco!")
            return
        
        for empresa in empresas:
            print(f"ID: {empresa.id}")
            print(f"Nome: {empresa.nome}")
            print(f"Slug: {empresa.slug}")
            print(f"Status atual: {empresa.status}")
            
            # Forçar status para 'ativo'
            empresa.status = 'ativo'
            print(f"✅ Status corrigido para: {empresa.status}")
            print("---")
        
        # Commit das mudanças
        session.commit()
        print("\n✅ Todas as empresas agora têm status 'ativo'!")
        
        # Verificar novamente
        print("\n=== VERIFICAÇÃO FINAL ===")
        empresas_final = session.query(Empresa).all()
        for empresa in empresas_final:
            print(f"{empresa.slug}: {empresa.status}")
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    debug_empresas() 