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

def verificar_empresa_apis():
    """Verifica a estrutura e dados da tabela empresa_apis"""
    try:
        # Criar engine usando POSTGRES_URL
        engine = create_engine(Config.POSTGRES_URL)
        
        # Criar sessão
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Verificar se a tabela existe
        query = text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'empresa_apis'
            )
        """)
        
        result = session.execute(query)
        tabela_existe = result.fetchone()[0]
        
        if not tabela_existe:
            print("❌ Tabela empresa_apis não existe!")
            return
        
        # Verificar estrutura da tabela empresa_apis
        query = text("""
            SELECT 
                column_name, 
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns 
            WHERE table_name = 'empresa_apis' 
            ORDER BY ordinal_position
        """)
        
        result = session.execute(query)
        columns = result.fetchall()
        
        print("\n=== ESTRUTURA DA TABELA EMPRESA_APIS ===")
        print(f"{'Coluna':<25} {'Tipo':<15} {'Nullable':<10} {'Default'}")
        print("-" * 70)
        
        for col in columns:
            print(f"{col[0]:<25} {col[1]:<15} {col[2]:<10} {col[3] or 'NULL'}")
        
        # Verificar dados da tabela empresa_apis
        query = text("""
            SELECT 
                ea.id,
                e.nome as empresa_nome,
                e.slug as empresa_slug,
                a.nome as api_nome,
                ea.config,
                ea.ativo
            FROM empresa_apis ea
            JOIN empresas e ON ea.empresa_id = e.id
            JOIN apis a ON ea.api_id = a.id
            ORDER BY e.nome, a.nome
        """)
        
        result = session.execute(query)
        dados = result.fetchall()
        
        print(f"\n=== DADOS DA TABELA EMPRESA_APIS ===")
        print(f"{'ID':<5} {'Empresa':<20} {'API':<15} {'Ativo':<8} {'Config'}")
        print("-" * 80)
        
        for row in dados:
            config_str = str(row[4])[:50] + "..." if row[4] and len(str(row[4])) > 50 else str(row[4])
            print(f"{row[0]:<5} {row[1]:<20} {row[2]:<15} {row[3]:<8} {config_str}")
        
        print(f"\nTotal de registros: {len(dados)}")
        
        # Verificar especificamente a API OpenAI
        query = text("""
            SELECT 
                ea.id,
                e.nome as empresa_nome,
                e.slug as empresa_slug,
                a.nome as api_nome,
                ea.config,
                ea.ativo
            FROM empresa_apis ea
            JOIN empresas e ON ea.empresa_id = e.id
            JOIN apis a ON ea.api_id = a.id
            WHERE a.nome = 'OpenAI'
            ORDER BY e.nome
        """)
        
        result = session.execute(query)
        openai_dados = result.fetchall()
        
        print(f"\n=== CONFIGURAÇÕES OPENAI ===")
        for row in openai_dados:
            config = row[4] or {}
            openai_key = config.get('openai_key', 'NÃO CONFIGURADO')
            print(f"Empresa: {row[1]} ({row[2]})")
            print(f"  API: {row[3]}")
            print(f"  Ativo: {row[5]}")
            print(f"  OpenAI Key: {openai_key[:20]}..." if len(openai_key) > 20 else f"  OpenAI Key: {openai_key}")
            print()
        
        session.close()
        
    except Exception as e:
        print(f"Erro ao verificar empresa_apis: {e}")

def verificar_apis():
    """Verifica as APIs disponíveis"""
    try:
        # Criar engine usando POSTGRES_URL
        engine = create_engine(Config.POSTGRES_URL)
        
        # Criar sessão
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Verificar APIs disponíveis
        query = text("""
            SELECT 
                id,
                nome,
                descricao,
                tipo_auth,
                ativo
            FROM apis
            ORDER BY nome
        """)
        
        result = session.execute(query)
        apis = result.fetchall()
        
        print("\n=== APIS DISPONÍVEIS ===")
        print(f"{'ID':<5} {'Nome':<20} {'Tipo Auth':<15} {'Ativo':<8}")
        print("-" * 60)
        
        for api in apis:
            print(f"{api[0]:<5} {api[1]:<20} {api[3]:<15} {api[4]}")
        
        print(f"\nTotal de APIs: {len(apis)}")
        
        session.close()
        
    except Exception as e:
        print(f"Erro ao verificar APIs: {e}")

if __name__ == "__main__":
    verificar_estrutura_empresas()
    verificar_empresa_apis()
    verificar_apis() 