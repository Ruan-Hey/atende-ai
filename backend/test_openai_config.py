#!/usr/bin/env python3
import os
import sys
sys.path.append(os.path.dirname(__file__))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Empresa
from config import Config

def test_openai_config():
    """Testa a configuração da OpenAI diretamente no banco"""
    engine = create_engine(Config.POSTGRES_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    session = SessionLocal()
    try:
        print("=== TESTE DE CONFIGURAÇÃO OPENAI ===")
        
        # Buscar a TinyTeams
        empresa = session.query(Empresa).filter(Empresa.slug == 'tinyteams').first()
        
        if not empresa:
            print("❌ Empresa TinyTeams não encontrada!")
            return
        
        print(f"🏢 Empresa: {empresa.nome} ({empresa.slug})")
        print(f"   ID: {empresa.id}")
        print(f"   OpenAI Key atual: {'✅ Configurado' if empresa.openai_key else '❌ Não configurado'}")
        
        if empresa.openai_key:
            print(f"   Preview: {empresa.openai_key[:10]}...")
        
        # Perguntar se quer configurar
        print("\n🔧 Deseja configurar a chave da OpenAI?")
        print("1. Sim")
        print("2. Não")
        
        choice = input("Escolha (1 ou 2): ").strip()
        
        if choice == "1":
            openai_key = input("Digite a chave da OpenAI: ").strip()
            
            if openai_key:
                empresa.openai_key = openai_key
                session.commit()
                print("✅ Chave da OpenAI configurada com sucesso!")
                
                # Verificar novamente
                session.refresh(empresa)
                print(f"   Nova chave: {'✅ Configurado' if empresa.openai_key else '❌ Não configurado'}")
                if empresa.openai_key:
                    print(f"   Preview: {empresa.openai_key[:10]}...")
            else:
                print("❌ Chave não fornecida!")
        else:
            print("❌ Operação cancelada!")
            
    except Exception as e:
        print(f"❌ Erro: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    test_openai_config() 