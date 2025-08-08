#!/usr/bin/env python3
"""
Script para limpar a tabela empresas removendo colunas que agora estão em empresa_apis
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Base

# Configuração do banco de dados
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/atende_ai")

def cleanup_empresas_table():
    """Remove colunas desnecessárias da tabela empresas"""
    
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("🔄 Iniciando limpeza da tabela empresas...")
        
        # Lista de colunas para remover
        columns_to_remove = [
            'openai_key',
            'google_sheets_id', 
            'chatwoot_token',
            'chatwoot_inbox_id',
            'chatwoot_origem',
            'horario_funcionamento'
        ]
        
        # Verificar se as colunas existem antes de tentar removê-las
        for column in columns_to_remove:
            try:
                # Verificar se a coluna existe
                result = session.execute(text(f"""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'empresas' 
                    AND column_name = '{column}'
                """))
                
                if result.fetchone():
                    print(f"🗑️  Removendo coluna: {column}")
                    session.execute(text(f"ALTER TABLE empresas DROP COLUMN {column}"))
                else:
                    print(f"ℹ️  Coluna {column} não existe, pulando...")
                    
            except Exception as e:
                print(f"⚠️  Erro ao remover coluna {column}: {e}")
        
        # Commit das alterações
        session.commit()
        print("✅ Limpeza concluída com sucesso!")
        
        # Mostrar estrutura atual da tabela
        print("\n📋 Estrutura atual da tabela empresas:")
        result = session.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'empresas' 
            ORDER BY ordinal_position
        """))
        
        for row in result:
            print(f"  - {row[0]}: {row[1]}")
            
    except Exception as e:
        print(f"❌ Erro durante a limpeza: {e}")
        session.rollback()
    finally:
        session.close()

def verify_apis_in_empresa_apis():
    """Verifica se as APIs estão corretamente configuradas em empresa_apis"""
    
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("\n🔍 Verificando APIs em empresa_apis...")
        
        # Verificar APIs existentes
        result = session.execute(text("""
            SELECT ea.empresa_id, e.nome as empresa_nome, a.nome as api_nome, ea.config
            FROM empresa_apis ea
            JOIN empresas e ON ea.empresa_id = e.id
            JOIN apis a ON ea.api_id = a.id
            WHERE ea.ativo = true
            ORDER BY e.nome, a.nome
        """))
        
        empresas_apis = {}
        for row in result:
            empresa_id = row[0]
            if empresa_id not in empresas_apis:
                empresas_apis[empresa_id] = []
            empresas_apis[empresa_id].append({
                'api': row[2],
                'config': row[3]
            })
        
        if empresas_apis:
            print("✅ APIs encontradas em empresa_apis:")
            for empresa_id, apis in empresas_apis.items():
                print(f"\n🏢 Empresa ID {empresa_id}:")
                for api in apis:
                    print(f"  - {api['api']}: {len(api['config'] or {})} configurações")
        else:
            print("⚠️  Nenhuma API encontrada em empresa_apis")
            
    except Exception as e:
        print(f"❌ Erro ao verificar APIs: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    print("🧹 Script de limpeza da tabela empresas")
    print("=" * 50)
    
    # Executar limpeza
    cleanup_empresas_table()
    
    # Verificar APIs
    verify_apis_in_empresa_apis()
    
    print("\n🎉 Processo concluído!")
    print("\n📝 Próximos passos:")
    print("1. Atualizar o modelo Empresa em models.py")
    print("2. Testar se o sistema ainda funciona corretamente")
    print("3. Fazer commit das alterações") 