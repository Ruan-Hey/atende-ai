#!/usr/bin/env python3
"""
Script para inicializar o banco de dados com dados padrão
"""

import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Empresa
from config import Config

def init_database():
    """Inicializa o banco de dados com dados padrão"""
    
    # Configuração
    config = Config()
    engine = create_engine(config.POSTGRES_URL)
    
    # Criar tabelas
    Base.metadata.create_all(bind=engine)
    
    # Criar sessão
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Verificar se já existem empresas
        empresas_count = db.query(Empresa).count()
        if empresas_count == 0:
            print("Criando empresas padrão...")
            
            # Criar empresas
            empresas = [
                Empresa(
                    nome="TinyTeams",
                    slug="tinyteams",
                    prompt="Você é um assistente virtual da TinyTeams, uma empresa de desenvolvimento de software. Responda de forma profissional e amigável.",
                    webhook_url="",
                    status="ativo"
                ),
                Empresa(
                    nome="Pancia Piena",
                    slug="pancia-piena", 
                    prompt="Você é um assistente virtual da Pancia Piena, uma pizzaria. Responda de forma amigável e ajude com pedidos.",
                    webhook_url="",
                    status="ativo"
                ),
                Empresa(
                    nome="Umas e Ostras",
                    slug="umas-e-ostras",
                    prompt="Você é um assistente virtual da Umas e Ostras, um restaurante de frutos do mar. Responda de forma elegante e profissional.",
                    webhook_url="",
                    status="ativo"
                )
            ]
            
            for empresa in empresas:
                db.add(empresa)
            
            db.commit()
            print("✅ Empresas criadas com sucesso!")
        
        print("🎉 Banco de dados inicializado com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro ao inicializar banco: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    init_database() 