#!/usr/bin/env python3
"""
Script para atualizar credenciais OAuth2 no banco de dados e gerar Refresh Token automaticamente
"""

import os
import sys

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def update_oauth_credentials():
    """Atualiza credenciais OAuth2 no banco de dados e gera Refresh Token automaticamente"""
    
    print("🔧 Atualizando credenciais OAuth2 no banco de dados...")
    
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from models import Empresa, EmpresaAPI, API
        from config import Config
        
        # Conectar ao banco
        engine = create_engine(Config.POSTGRES_URL)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        try:
            # Buscar configurações
            empresa = session.query(Empresa).filter(Empresa.slug == 'tinyteams').first()
            google_calendar_api = session.query(API).filter(API.nome == 'Google Calendar').first()
            empresa_api = session.query(EmpresaAPI).filter(
                EmpresaAPI.empresa_id == empresa.id,
                EmpresaAPI.api_id == google_calendar_api.id,
                EmpresaAPI.ativo == True
            ).first()
            
            config = empresa_api.config or {}
            
            print("✅ Configuração encontrada")
            print(f"\n📋 Configurações atuais:")
            for key, value in config.items():
                if value and len(str(value)) > 20:
                    print(f"  {key}: {str(value)[:20]}...")
                else:
                    print(f"  {key}: {value}")
            
            print(f"\n🔧 Digite as credenciais OAuth2:")
            client_id = input("Client ID: ").strip()
            client_secret = input("Client Secret: ").strip()
            
            if not client_id or not client_secret:
                print("❌ Credenciais não fornecidas")
                return
            
            # Atualizar configuração
            config.update({
                'google_calendar_client_id': client_id,
                'google_calendar_client_secret': client_secret
            })
            
            empresa_api.config = config
            session.commit()
            
            print(f"\n✅ Credenciais OAuth2 salvas!")
            
            # Perguntar se quer gerar Refresh Token automaticamente
            print(f"\n🔄 Deseja gerar o Refresh Token automaticamente agora?")
            print("1. Sim - Gerar Refresh Token agora")
            print("2. Não - Fazer depois")
            
            choice = input("Escolha (1 ou 2): ").strip()
            
            if choice == "1":
                print(f"\n🚀 Iniciando geração automática do Refresh Token...")
                
                # Importar e executar o processo automático
                from auto_oauth_setup import auto_oauth_setup
                auto_oauth_setup()
            else:
                print(f"\n✅ Credenciais salvas!")
                print("Para gerar o Refresh Token depois, execute:")
                print("python auto_oauth_setup.py")
            
        finally:
            session.close()
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    update_oauth_credentials() 