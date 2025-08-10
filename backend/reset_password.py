#!/usr/bin/env python3
"""
Script para redefinir senha de usuário no banco de dados
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import gerar_hash_senha, Usuario
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import Config

def reset_user_password(email: str, new_password: str):
    """Redefine a senha de um usuário"""
    
    # Conectar ao banco
    engine = create_engine(Config.POSTGRES_URL)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        # Buscar usuário pelo email
        user = session.query(Usuario).filter(Usuario.email == email).first()
        
        if not user:
            print(f"❌ Usuário com email '{email}' não encontrado!")
            return False
        
        # Gerar novo hash da senha
        new_hash = gerar_hash_senha(new_password)
        
        # Atualizar senha
        user.senha_hash = new_hash
        session.commit()
        
        print(f"✅ Senha do usuário '{email}' atualizada com sucesso!")
        print(f"📧 Email: {email}")
        print(f"🔑 Nova senha: {new_password}")
        print(f"🔒 Hash gerado: {new_hash}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao atualizar senha: {e}")
        session.rollback()
        return False
        
    finally:
        session.close()

def list_users():
    """Lista todos os usuários do banco"""
    
    engine = create_engine(Config.POSTGRES_URL)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        users = session.query(Usuario).all()
        
        if not users:
            print("❌ Nenhum usuário encontrado no banco!")
            return
        
        print("👥 Usuários cadastrados:")
        print("-" * 50)
        
        for user in users:
            print(f"ID: {user.id}")
            print(f"Email: {user.email}")
            print(f"Superuser: {'Sim' if user.is_superuser else 'Não'}")
            print(f"Empresa ID: {user.empresa_id or 'N/A'}")
            print(f"Criado em: {user.created_at}")
            print("-" * 50)
            
    except Exception as e:
        print(f"❌ Erro ao listar usuários: {e}")
        
    finally:
        session.close()

if __name__ == "__main__":
    print("🔐 Script de Redefinição de Senha")
    print("=" * 40)
    
    if len(sys.argv) == 2 and sys.argv[1] == "--list":
        list_users()
        sys.exit(0)
    
    if len(sys.argv) < 3:
        print("❌ Uso: python reset_password.py <email> <nova_senha>")
        print("📋 Exemplo: python reset_password.py admin@exemplo.com minhasenha123")
        print()
        print("🔍 Para listar usuários: python reset_password.py --list")
        sys.exit(1)
    
    email = sys.argv[1]
    new_password = sys.argv[2]
    
    print(f"🔄 Redefinindo senha para: {email}")
    print(f"🔑 Nova senha: {new_password}")
    print()
    
    success = reset_user_password(email, new_password)
    
    if success:
        print()
        print("🎉 Senha redefinida com sucesso!")
        print("💡 Agora você pode fazer login com a nova senha.")
    else:
        print()
        print("💥 Falha ao redefinir senha!")
        sys.exit(1) 