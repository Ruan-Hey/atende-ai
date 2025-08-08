#!/usr/bin/env python3
"""
Script para remover as colunas restantes da tabela empresas
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Adicionar o diretório atual ao path para importar config
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config

def remover_colunas_restantes():
    """Remove as colunas restantes da tabela empresas"""
    try:
        # Criar engine
        engine = create_engine(Config.POSTGRES_URL)
        
        # Criar sessão
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Colunas restantes para remover
        colunas_para_remover = [
            'google_calendar_client_secret',
            'google_calendar_refresh_token'
        ]
        
        print("=== REMOVENDO COLUNAS RESTANTES ===")
        
        for coluna in colunas_para_remover:
            try:
                # Verificar se a coluna existe
                check_query = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'empresas' 
                    AND column_name = :coluna
                """)
                
                result = session.execute(check_query, {"coluna": coluna})
                exists = result.fetchone()
                
                if exists:
                    # Remover a coluna
                    drop_query = text(f"ALTER TABLE empresas DROP COLUMN {coluna}")
                    session.execute(drop_query)
                    session.commit()
                    print(f"✅ {coluna} - REMOVIDA COM SUCESSO")
                else:
                    print(f"⚠️ {coluna} - NÃO EXISTE")
                    
            except Exception as e:
                print(f"❌ Erro ao remover {coluna}: {e}")
                session.rollback()
        
        # Verificar estrutura final
        print("\n=== ESTRUTURA FINAL DA TABELA EMPRESAS ===")
        query = text("""
            SELECT 
                column_name, 
                data_type,
                is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'empresas' 
            ORDER BY ordinal_position
        """)
        
        result = session.execute(query)
        columns = result.fetchall()
        
        print(f"{'Coluna':<25} {'Tipo':<15} {'Nullable'}")
        print("-" * 50)
        
        for col in columns:
            print(f"{col[0]:<25} {col[1]:<15} {col[2]}")
        
        print(f"\nTotal de colunas: {len(columns)}")
        
        session.close()
        
    except Exception as e:
        print(f"Erro ao conectar ao banco: {e}")

if __name__ == "__main__":
    remover_colunas_restantes() 