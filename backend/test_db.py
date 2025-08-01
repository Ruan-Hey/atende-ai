#!/usr/bin/env python3
import os
import sys
sys.path.append(os.path.dirname(__file__))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Empresa, Base
from config import Config

def test_db():
    """Testa a conexão com o banco de dados"""
    try:
        print("=== TESTE DE CONEXÃO COM BANCO ===")
        
        config = Config()
        print(f"URL do banco: {config.POSTGRES_URL}")
        
        engine = create_engine(config.POSTGRES_URL)
        print("✅ Engine criado com sucesso")
        
        # Testar conexão
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Conexão com banco OK")
        
        # Testar modelo
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        
        try:
            empresas = session.query(Empresa).all()
            print(f"✅ Query executada: {len(empresas)} empresas encontradas")
            
            for empresa in empresas:
                print(f"  - {empresa.nome} ({empresa.slug})")
                print(f"    Prompt: {'✅' if empresa.prompt else '❌'}")
                print(f"    Mensagem Quebrada: {'✅' if empresa.mensagem_quebrada else '❌'}")
                print(f"    Buffer: {'✅' if empresa.usar_buffer else '❌'}")
                
        except Exception as e:
            print(f"❌ Erro na query: {e}")
        finally:
            session.close()
            
    except Exception as e:
        print(f"❌ Erro geral: {e}")

if __name__ == "__main__":
    test_db() 