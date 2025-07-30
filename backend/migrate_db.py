#!/usr/bin/env python3
"""
Script para migrar o banco de dados existente
"""

import os
import sys
from sqlalchemy import create_engine, text
from config import Config

def migrate_database():
    """Migra o banco de dados para adicionar novas colunas"""
    
    # Configuração
    config = Config()
    
    # Debug: verificar a URL
    print(f"🔍 DATABASE_URL: {os.getenv('DATABASE_URL', 'NÃO DEFINIDA')}")
    print(f"🔍 POSTGRES_URL: {os.getenv('POSTGRES_URL', 'NÃO DEFINIDA')}")
    print(f"🔍 Config.POSTGRES_URL: {config.POSTGRES_URL}")
    
    engine = create_engine(config.POSTGRES_URL)
    
    try:
        with engine.connect() as conn:
            # Verificar se as colunas já existem
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'empresas' 
                AND column_name IN ('prompt', 'webhook_url', 'status')
            """))
            existing_columns = [row[0] for row in result]
            
            # Adicionar colunas se não existirem
            if 'prompt' not in existing_columns:
                print("Adicionando coluna 'prompt'...")
                conn.execute(text("ALTER TABLE empresas ADD COLUMN prompt TEXT"))
            
            if 'webhook_url' not in existing_columns:
                print("Adicionando coluna 'webhook_url'...")
                conn.execute(text("ALTER TABLE empresas ADD COLUMN webhook_url VARCHAR(500)"))
            
            if 'status' not in existing_columns:
                print("Adicionando coluna 'status'...")
                conn.execute(text("ALTER TABLE empresas ADD COLUMN status VARCHAR(20) DEFAULT 'ativo'"))
            
            conn.commit()
            print("✅ Migração concluída com sucesso!")
            
    except Exception as e:
        print(f"❌ Erro na migração: {e}")
        sys.exit(1)

if __name__ == "__main__":
    migrate_database() 