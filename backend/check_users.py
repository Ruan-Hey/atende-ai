#!/usr/bin/env python3
import os
import sys
sys.path.append(os.path.dirname(__file__))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Usuario, Empresa
from config import Config

def check_users():
    """Verifica os usuários no banco"""
    engine = create_engine(Config.POSTGRES_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    session = SessionLocal()
    try:
        print("=== USUÁRIOS NO BANCO ===")
        
        usuarios = session.query(Usuario).all()
        
        if not usuarios:
            print("❌ Nenhum usuário encontrado!")
            return
        
        for usuario in usuarios:
            print(f"\n👤 Usuário ID: {usuario.id}")
            print(f"   Email: {usuario.email}")
            print(f"   Superuser: {'✅' if usuario.is_superuser else '❌'}")
            print(f"   Empresa ID: {usuario.empresa_id}")
            
            if usuario.empresa_id:
                empresa = session.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()
                if empresa:
                    print(f"   Empresa: {empresa.nome} ({empresa.slug})")
                else:
                    print(f"   Empresa: ❌ Não encontrada")
            
    except Exception as e:
        print(f"❌ Erro: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    check_users() 