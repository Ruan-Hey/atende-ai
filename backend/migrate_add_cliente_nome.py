#!/usr/bin/env python3
"""
Script para adicionar campo nome na tabela Cliente
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from config import Config

def migrate_add_cliente_nome():
    """Adiciona campo nome na tabela Cliente"""
    
    # Criar engine
    engine = create_engine(Config.POSTGRES_URL)
    
    try:
        with engine.connect() as conn:
            # Verificar se o campo já existe
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'clientes' 
                AND column_name = 'nome'
            """))
            
            if result.fetchone():
                print("✅ Campo 'nome' já existe na tabela 'clientes'")
                return
            
            # Adicionar campo nome
            print("🔧 Adicionando campo 'nome' na tabela 'clientes'...")
            conn.execute(text("""
                ALTER TABLE clientes 
                ADD COLUMN nome VARCHAR(255)
            """))
            conn.commit()
            print("✅ Campo 'nome' adicionado com sucesso!")
            
    except Exception as e:
        print(f"❌ Erro ao adicionar campo: {e}")
        return

if __name__ == "__main__":
    print("🚀 Migrando tabela Cliente...")
    migrate_add_cliente_nome() 