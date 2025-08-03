#!/usr/bin/env python3
"""
Script para testar o salvamento da chave da OpenAI na empresa TinyTeams
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Base, Empresa
from config import Config

def test_openai_save():
    """Testa o salvamento da chave da OpenAI"""
    
    print("🧪 Testando salvamento da chave da OpenAI...")
    print(f"📊 Conectando ao banco: {Config.POSTGRES_URL}")
    
    try:
        # Criar engine e sessão
        engine = create_engine(Config.POSTGRES_URL)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Buscar empresa TinyTeams
        empresa = session.query(Empresa).filter(Empresa.slug == 'tinyteams').first()
        
        if not empresa:
            print("❌ Empresa TinyTeams não encontrada!")
            return
        
        print(f"\n🏢 Empresa encontrada: {empresa.nome} (ID: {empresa.id})")
        print(f"   Chave atual: {'✅ Configurada' if empresa.openai_key else '❌ Não configurada'}")
        
        if empresa.openai_key:
            print(f"   Preview: {empresa.openai_key[:8]}...{empresa.openai_key[-4:]}")
        
        # Simular salvamento de uma chave de teste
        chave_teste = "sk-test123456789abcdef"
        
        print(f"\n🔧 Testando salvamento de chave de teste...")
        print(f"   Chave de teste: {chave_teste[:8]}...{chave_teste[-4:]}")
        
        # Salvar chave de teste
        empresa.openai_key = chave_teste
        session.commit()
        
        print("   ✅ Chave salva com sucesso!")
        
        # Verificar se foi salva
        session.refresh(empresa)
        print(f"   📝 Chave após salvamento: {'✅ Configurada' if empresa.openai_key else '❌ Não configurada'}")
        
        if empresa.openai_key:
            print(f"   Preview: {empresa.openai_key[:8]}...{empresa.openai_key[-4:]}")
        
        # Limpar chave de teste
        print(f"\n🧹 Limpando chave de teste...")
        empresa.openai_key = None
        session.commit()
        
        print("   ✅ Chave de teste removida!")
        
        session.close()
        
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")
        return

if __name__ == "__main__":
    test_openai_save() 