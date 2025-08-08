import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config import Config
from models import Empresa, API, EmpresaAPI

def test_database_connection():
    """Testa conexão direta com o banco"""
    
    config = Config()
    print(f"🔗 Conectando ao banco: {config.POSTGRES_URL}")
    
    engine = create_engine(config.POSTGRES_URL)
    SessionLocal = sessionmaker(bind=engine)
    
    session = SessionLocal()
    try:
        # Teste 1: Verificar se consegue conectar
        result = session.execute(text("SELECT 1"))
        print("✅ Conexão com banco OK")
        
        # Teste 2: Verificar se encontra a empresa TinyTeams
        empresa = session.query(Empresa).filter(Empresa.slug == 'tinyteams').first()
        if empresa:
            print(f"✅ Empresa TinyTeams encontrada: ID {empresa.id}")
        else:
            print("❌ Empresa TinyTeams não encontrada")
            return
        
        # Teste 3: Verificar se encontra a API Google Calendar
        api = session.query(API).filter(API.nome == 'Google Calendar').first()
        if api:
            print(f"✅ API Google Calendar encontrada: ID {api.id}")
        else:
            print("❌ API Google Calendar não encontrada")
            return
        
        # Teste 4: Verificar se já existe uma conexão empresa-API
        empresa_api = session.query(EmpresaAPI).filter(
            EmpresaAPI.empresa_id == empresa.id,
            EmpresaAPI.api_id == api.id
        ).first()
        
        if empresa_api:
            print(f"✅ Conexão empresa-API encontrada: ID {empresa_api.id}")
            print(f"📋 Config atual: {empresa_api.config}")
        else:
            print("ℹ️ Conexão empresa-API não existe (será criada)")
        
        # Teste 5: Tentar inserir/atualizar
        test_config = {
            'google_calendar_enabled': True,
            'google_calendar_service_account': {'test': 'data'},
            'google_calendar_project_id': 'test-project',
            'google_calendar_client_email': 'test@test.com'
        }
        
        if empresa_api:
            # Atualizar existente
            print("🔄 Atualizando configuração existente...")
            current_config = empresa_api.config or {}
            current_config.update(test_config)
            empresa_api.config = current_config
        else:
            # Criar nova
            print("🆕 Criando nova conexão empresa-API...")
            empresa_api = EmpresaAPI(
                empresa_id=empresa.id,
                api_id=api.id,
                config=test_config,
                ativo=True
            )
            session.add(empresa_api)
        
        print("💾 Fazendo commit...")
        session.commit()
        print("✅ Commit realizado com sucesso!")
        
        # Teste 6: Verificar se salvou
        session.refresh(empresa_api)
        print(f"📋 Config após commit: {empresa_api.config}")
        
        # Teste 7: Recarregar do banco
        empresa_api_verif = session.query(EmpresaAPI).filter(
            EmpresaAPI.empresa_id == empresa.id,
            EmpresaAPI.api_id == api.id
        ).first()
        
        if empresa_api_verif and empresa_api_verif.config:
            print("✅ Dados persistidos no banco!")
            print(f"📋 Service Account: {empresa_api_verif.config.get('google_calendar_service_account')}")
        else:
            print("❌ Dados não persistidos no banco!")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    test_database_connection() 