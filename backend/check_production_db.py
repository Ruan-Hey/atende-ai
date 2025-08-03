#!/usr/bin/env python3
"""
Script para verificar chaves da OpenAI no banco de PRODUÇÃO
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Base, Empresa

# URL do banco de produção
PRODUCTION_DB_URL = "postgresql://atendeai:2pjZBzhDlZY275Z4FubsnBFPsjvLHNRw@dpg-d24vpfngi27c73bh06n0-a.oregon-postgres.render.com/atendeai"

def check_production_db():
    """Verifica chaves da OpenAI no banco de produção"""
    
    print("🔍 Verificando chaves da OpenAI no banco de PRODUÇÃO...")
    print(f"📊 URL do banco: {PRODUCTION_DB_URL}")
    
    try:
        # Criar engine e sessão
        engine = create_engine(PRODUCTION_DB_URL)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Testar conexão
        result = session.execute(text("SELECT 1"))
        print("✅ Conexão com banco de PRODUÇÃO estabelecida!")
        
        # Buscar empresas que contenham "tinyteams" no nome ou slug
        empresas_tinyteams = session.query(Empresa).filter(
            (Empresa.nome.ilike('%tinyteams%')) |
            (Empresa.slug.ilike('%tinyteams%'))
        ).all()
        
        print(f"\n📋 Encontradas {len(empresas_tinyteams)} empresas da TinyTeams:")
        print("=" * 80)
        
        if not empresas_tinyteams:
            print("❌ Nenhuma empresa da TinyTeams encontrada no banco de PRODUÇÃO!")
            return
        
        for empresa in empresas_tinyteams:
            print(f"\n🏢 Empresa: {empresa.nome}")
            print(f"   Slug: {empresa.slug}")
            print(f"   ID: {empresa.id}")
            print(f"   Status: {empresa.status}")
            
            if empresa.openai_key:
                # Mostrar apenas os primeiros e últimos caracteres da chave por segurança
                key_preview = empresa.openai_key[:8] + "..." + empresa.openai_key[-4:]
                print(f"   ✅ OpenAI Key: {key_preview}")
                print(f"   📝 Chave completa: {empresa.openai_key}")
            else:
                print("   ❌ Nenhuma chave da OpenAI cadastrada")
            
            print(f"   📅 Criada em: {empresa.created_at}")
            print(f"   🔄 Atualizada em: {empresa.updated_at}")
            print("-" * 50)
        
        # Verificar também todas as empresas que têm chave da OpenAI
        print(f"\n🔍 Verificando todas as empresas com chave da OpenAI:")
        print("=" * 80)
        
        empresas_com_openai = session.query(Empresa).filter(
            Empresa.openai_key.isnot(None),
            Empresa.openai_key != ""
        ).all()
        
        print(f"📊 Total de empresas com chave da OpenAI: {len(empresas_com_openai)}")
        
        for empresa in empresas_com_openai:
            key_preview = empresa.openai_key[:8] + "..." + empresa.openai_key[-4:]
            print(f"   🏢 {empresa.nome} ({empresa.slug}) - Key: {key_preview}")
        
        session.close()
        
    except Exception as e:
        print(f"❌ Erro ao conectar ao banco de PRODUÇÃO: {e}")
        return

if __name__ == "__main__":
    check_production_db() 