#!/usr/bin/env python3
"""
Script para verificar a estrutura atual da tabela empresas
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Adicionar o diretório atual ao path para importar config
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config

def verificar_estrutura_empresas():
    """Verifica a estrutura atual da tabela empresas"""
    try:
        # Criar engine usando POSTGRES_URL
        engine = create_engine(Config.POSTGRES_URL)
        
        # Criar sessão
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Query para verificar estrutura da tabela empresas
        query = text("""
            SELECT 
                column_name, 
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns 
            WHERE table_name = 'empresas' 
            ORDER BY ordinal_position
        """)
        
        result = session.execute(query)
        columns = result.fetchall()
        
        print("=== ESTRUTURA ATUAL DA TABELA EMPRESAS ===")
        print(f"{'Coluna':<25} {'Tipo':<15} {'Nullable':<10} {'Default'}")
        print("-" * 70)
        
        for col in columns:
            print(f"{col[0]:<25} {col[1]:<15} {col[2]:<10} {col[3] or 'NULL'}")
        
        print(f"\nTotal de colunas: {len(columns)}")
        
        # Verificar se as colunas que queremos remover ainda existem
        colunas_para_remover = [
            'openai_key',
            'google_sheets_id', 
            'chatwoot_token',
            'chatwoot_inbox_id',
            'chatwoot_origem',
            'horario_funcionamento',
            'google_calendar_client_id',
            'google_calendar_client_secret', 
            'google_calendar_refresh_token',
            'webhook_url'
        ]
        
        print("\n=== VERIFICAÇÃO DE COLUNAS PARA REMOVER ===")
        colunas_existentes = [col[0] for col in columns]
        
        for coluna in colunas_para_remover:
            if coluna in colunas_existentes:
                print(f"❌ {coluna} - AINDA EXISTE")
            else:
                print(f"✅ {coluna} - JÁ FOI REMOVIDA")
        
        session.close()
        
    except Exception as e:
        print(f"Erro ao conectar ao banco: {e}")

if __name__ == "__main__":
    verificar_estrutura_empresas() 