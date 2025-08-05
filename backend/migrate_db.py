#!/usr/bin/env python3
"""
Script para migrar o banco de dados
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Base, Empresa, Mensagem, Log, Usuario, Atendimento, Cliente, Atividade
from config import Config

def create_tables():
    """Cria todas as tabelas no banco de dados"""
    try:
        engine = create_engine(Config.POSTGRES_URL)
        
        # Criar todas as tabelas
        Base.metadata.create_all(engine)
        
        print("✅ Tabelas criadas com sucesso!")
        
        # Verificar se as tabelas foram criadas
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            
            tables = [row[0] for row in result]
            print(f"📋 Tabelas encontradas: {', '.join(tables)}")
            
    except Exception as e:
        print(f"❌ Erro ao criar tabelas: {e}")
        sys.exit(1)

def create_admin_user():
    """Cria usuário admin padrão"""
    try:
        engine = create_engine(Config.POSTGRES_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        
        # Verificar se já existe um usuário admin
        admin_user = session.query(Usuario).filter(Usuario.email == "admin@atende.ai").first()
        
        if not admin_user:
            from passlib.hash import bcrypt
            
            admin_user = Usuario(
                email="admin@atende.ai",
                senha_hash=bcrypt.hash("admin123"),
                is_superuser=True
            )
            
            session.add(admin_user)
            session.commit()
            print("✅ Usuário admin criado: admin@atende.ai / admin123")
        else:
            print("ℹ️  Usuário admin já existe")
            
        session.close()
        
    except Exception as e:
        print(f"❌ Erro ao criar usuário admin: {e}")

def create_sample_empresas():
    """Cria empresas de exemplo"""
    try:
        engine = create_engine(Config.POSTGRES_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        
        # Verificar se já existem empresas
        existing_empresas = session.query(Empresa).count()
        
        if existing_empresas == 0:
            empresas = [
                {
                    'slug': 'tinyteams',
                    'nome': 'TinyTeams',
                    'status': 'ativo',
                    'prompt': 'Você é um assistente virtual da TinyTeams, uma empresa de tecnologia especializada em soluções de produtividade e colaboração.',
                    'whatsapp_number': '+554184447366',
                    'usar_buffer': True,
                    'mensagem_quebrada': False
                },
                {
                    'slug': 'pancia-piena',
                    'nome': 'Pancia Piena',
                    'status': 'ativo',
                    'prompt': 'Você é um assistente virtual da Pancia Piena, um restaurante italiano autêntico.',
                    'whatsapp_number': '+554184447366',
                    'usar_buffer': True,
                    'mensagem_quebrada': False
                },
                {
                    'slug': 'umas-e-ostras',
                    'nome': 'Umas e Ostras',
                    'status': 'ativo',
                    'prompt': 'Você é um assistente virtual da Umas e Ostras, um restaurante especializado em frutos do mar.',
                    'whatsapp_number': '+554184447366',
                    'usar_buffer': True,
                    'mensagem_quebrada': False
                }
            ]
            
            for empresa_data in empresas:
                empresa = Empresa(**empresa_data)
                session.add(empresa)
            
            session.commit()
            print("✅ Empresas de exemplo criadas")
        else:
            print(f"ℹ️  Já existem {existing_empresas} empresas no banco")
            
        session.close()
        
    except Exception as e:
        print(f"❌ Erro ao criar empresas de exemplo: {e}")

def migrate_logs_to_tinyteams():
    """Migra logs existentes sem empresa_id para a TinyTeams"""
    try:
        engine = create_engine(Config.POSTGRES_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        
        # Buscar a empresa TinyTeams
        tinyteams = session.query(Empresa).filter(Empresa.slug == 'tinyteams').first()
        
        if not tinyteams:
            print("❌ Empresa TinyTeams não encontrada. Execute create_sample_empresas() primeiro.")
            return
        
        # Contar logs sem empresa_id
        logs_sem_empresa = session.query(Log).filter(Log.empresa_id == None).count()
        
        if logs_sem_empresa > 0:
            # Atualizar logs sem empresa_id para TinyTeams
            session.query(Log).filter(Log.empresa_id == None).update({
                Log.empresa_id: tinyteams.id
            })
            session.commit()
            print(f"✅ {logs_sem_empresa} logs migrados para TinyTeams")
        else:
            print("ℹ️  Nenhum log sem empresa_id encontrado")
            
        session.close()
        
    except Exception as e:
        print(f"❌ Erro ao migrar logs: {e}")

if __name__ == "__main__":
    print("🚀 Iniciando migração do banco de dados...")
    
    create_tables()
    create_admin_user()
    create_sample_empresas()
    migrate_logs_to_tinyteams()
    
    print("✅ Migração concluída com sucesso!") 