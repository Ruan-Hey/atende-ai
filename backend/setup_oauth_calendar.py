#!/usr/bin/env python3
"""
Script para configurar OAuth2 para Google Calendar
"""

import os
import sys
import json
from datetime import datetime

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def setup_oauth_calendar():
    """Configura OAuth2 para Google Calendar"""
    
    print("🔧 Configurando OAuth2 para Google Calendar...")
    
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
            # Buscar empresa TinyTeams
            empresa = session.query(Empresa).filter(Empresa.slug == 'tinyteams').first()
            if not empresa:
                print("❌ Empresa TinyTeams não encontrada")
                return
            
            print(f"✅ Empresa encontrada: {empresa.nome}")
            
            # Buscar API Google Calendar
            google_calendar_api = session.query(API).filter(API.nome == 'Google Calendar').first()
            if not google_calendar_api:
                print("❌ API Google Calendar não encontrada")
                return
            
            print("✅ API Google Calendar encontrada")
            
            # Buscar configuração atual
            empresa_api = session.query(EmpresaAPI).filter(
                EmpresaAPI.empresa_id == empresa.id,
                EmpresaAPI.api_id == google_calendar_api.id,
                EmpresaAPI.ativo == True
            ).first()
            
            if not empresa_api:
                print("❌ Configuração do Google Calendar não encontrada")
                return
            
            print("✅ Configuração atual encontrada")
            
            # Mostrar configurações atuais
            config_atual = empresa_api.config or {}
            print(f"\n📋 Configurações atuais:")
            for key, value in config_atual.items():
                if value and len(str(value)) > 20:
                    print(f"  {key}: {str(value)[:20]}...")
                else:
                    print(f"  {key}: {value}")
            
            print(f"\n🔧 Para configurar OAuth2:")
            print("1. Acesse: https://console.cloud.google.com/")
            print("2. Selecione o projeto: tinyteams-calendar-456789")
            print("3. Vá em 'APIs e serviços' > 'Credenciais'")
            print("4. Clique em 'Criar credenciais' > 'ID do cliente OAuth 2.0'")
            print("5. Configure:")
            print("   - Tipo: Aplicativo da Web")
            print("   - Nome: TinyTeams Calendar OAuth")
            print("   - URIs autorizados: http://localhost:8000")
            print("   - URIs de redirecionamento: http://localhost:8000/oauth/callback")
            print("6. Copie o Client ID e Client Secret")
            
            print(f"\n📝 Depois execute:")
            print("python setup_oauth_tokens.py")
            
            # Verificar se já tem OAuth configurado
            if config_atual.get('google_calendar_client_id') and config_atual.get('google_calendar_client_secret'):
                print(f"\n✅ OAuth já configurado!")
                print("Para obter tokens de acesso, execute:")
                print("python get_oauth_tokens.py")
            else:
                print(f"\n❌ OAuth não configurado")
                print("Configure as credenciais OAuth primeiro")
            
        finally:
            session.close()
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    setup_oauth_calendar() 