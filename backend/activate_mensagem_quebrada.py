#!/usr/bin/env python3
import os
import sys
sys.path.append(os.path.dirname(__file__))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Empresa
from config import Config

def activate_mensagem_quebrada():
    """Ativa a mensagem quebrada na Pancia Piena"""
    engine = create_engine(Config.POSTGRES_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    session = SessionLocal()
    try:
        print("=== ATIVANDO MENSAGEM QUEBRADA ===")
        
        # Buscar a Pancia Piena
        empresa = session.query(Empresa).filter(Empresa.slug == 'pancia-piena').first()
        
        if not empresa:
            print("❌ Empresa Pancia Piena não encontrada!")
            return
        
        print(f"🏢 Empresa: {empresa.nome} ({empresa.slug})")
        print(f"   Status atual - Mensagem Quebrada: {'✅ Ativo' if empresa.mensagem_quebrada else '❌ Inativo'}")
        
        # Ativar mensagem quebrada
        empresa.mensagem_quebrada = True
        session.commit()
        
        print(f"   ✅ Mensagem quebrada ativada!")
        print(f"   Status final - Mensagem Quebrada: {'✅ Ativo' if empresa.mensagem_quebrada else '❌ Inativo'}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    activate_mensagem_quebrada() 