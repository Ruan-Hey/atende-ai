#!/usr/bin/env python3
import os
import sys
sys.path.append(os.path.dirname(__file__))

from models import Usuario, gerar_hash_senha
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import Config

def reset_password():
    """Reseta a senha de todos os usuários"""
    engine = create_engine(Config.POSTGRES_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        # Gerar hash da senha
        senha_hash = gerar_hash_senha('123456')
        print(f"Hash da senha '123456': {senha_hash}")
        
        # Buscar todos os usuários
        users = session.query(Usuario).all()
        
        for user in users:
            # Atualizar senha
            user.senha_hash = senha_hash
            print(f"✅ Senha atualizada para: {user.email} (Superuser: {user.is_superuser})")
        
        session.commit()
        print(f"✅ {len(users)} usuários atualizados!")
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    reset_password() 