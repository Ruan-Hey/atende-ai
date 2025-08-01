#!/usr/bin/env python3
import os
import sys
sys.path.append(os.path.dirname(__file__))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Empresa
from config import Config

def fix_pancia_piena():
    """Corrige a Pancia Piena - restaura prompt original e ativa mensagem quebrada"""
    engine = create_engine(Config.POSTGRES_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    session = SessionLocal()
    try:
        print("=== CORRIGINDO PANCIA PIENA ===")
        
        # Buscar a Pancia Piena
        empresa = session.query(Empresa).filter(Empresa.slug == 'pancia-piena').first()
        
        if not empresa:
            print("❌ Empresa Pancia Piena não encontrada!")
            return
        
        print(f"🏢 Empresa: {empresa.nome} ({empresa.slug})")
        print(f"   Prompt atual: {empresa.prompt}")
        print(f"   Mensagem Quebrada atual: {'✅ Ativo' if empresa.mensagem_quebrada else '❌ Inativo'}")
        
        # Restaurar prompt original
        empresa.prompt = "Você é um assistente virtual da Pancia Piena, uma pizzaria. Responda de forma amigável e ajude com pedidos."
        
        # Ativar mensagem quebrada
        empresa.mensagem_quebrada = True
        
        session.commit()
        
        print(f"   ✅ Prompt restaurado!")
        print(f"   ✅ Mensagem quebrada ativada!")
        print(f"   Novo prompt: {empresa.prompt}")
        print(f"   Status final - Mensagem Quebrada: {'✅ Ativo' if empresa.mensagem_quebrada else '❌ Inativo'}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    fix_pancia_piena() 