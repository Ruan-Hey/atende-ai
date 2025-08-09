#!/usr/bin/env python3
"""
Script que automaticamente gera Refresh Token quando Client ID e Secret são salvos
"""

import os
import sys
import webbrowser
import requests
from datetime import datetime

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def auto_oauth_setup():
    """Configuração automática de OAuth2"""
    
    print("🚀 Configuração automática de OAuth2 para Google Calendar...")
    
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
            
            # Verificar se já tem OAuth configurado
            client_id = config.get('google_calendar_client_id')
            client_secret = config.get('google_calendar_client_secret')
            refresh_token = config.get('google_calendar_refresh_token')
            
            if not client_id or not client_secret:
                print("❌ Client ID e Client Secret não configurados")
                print("Execute primeiro: python update_oauth_credentials.py")
                return
            
            print(f"✅ Client ID: {client_id[:20]}...")
            print(f"✅ Client Secret: {client_secret[:20]}...")
            
            if refresh_token:
                print(f"✅ Refresh Token já existe: {refresh_token[:20]}...")
                print("OAuth2 já está configurado!")
                return
            
            print(f"\n🔄 Gerando Refresh Token automaticamente...")
            
            # Construir URL de autorização
            from urllib.parse import urlencode
            
            auth_params = {
                'client_id': client_id,
                'redirect_uri': 'http://localhost:8000/oauth/callback',
                'scope': 'https://www.googleapis.com/auth/calendar',
                'response_type': 'code',
                'access_type': 'offline',
                'prompt': 'consent'  # Força sempre retornar refresh token
            }
            
            auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(auth_params)}"
            
            print(f"\n🔗 URL de autorização gerada:")
            print(auth_url)
            
            print(f"\n📋 Passos automáticos:")
            print("1. Navegador será aberto automaticamente")
            print("2. Faça login com sua conta Google")
            print("3. Autorize o acesso ao Google Calendar")
            print("4. Copie o código da URL de redirecionamento")
            print("5. Cole o código aqui quando solicitado")
            
            # Abrir navegador automaticamente
            try:
                webbrowser.open(auth_url)
                print(f"\n🌐 Navegador aberto automaticamente!")
            except Exception as e:
                print(f"\n📋 Erro ao abrir navegador: {e}")
                print("Copie e cole este link no navegador:")
                print(auth_url)
            
            # Aguardar código
            print(f"\n⏳ Aguardando código de autorização...")
            auth_code = input("Cole o código aqui: ").strip()
            
            if not auth_code:
                print("❌ Código não fornecido")
                return
            
            print(f"✅ Código recebido: {auth_code[:20]}...")
            
            # Trocar código por tokens
            print(f"\n🔄 Trocando código por tokens...")
            
            token_url = "https://oauth2.googleapis.com/token"
            token_data = {
                'client_id': client_id,
                'client_secret': client_secret,
                'code': auth_code,
                'grant_type': 'authorization_code',
                'redirect_uri': 'http://localhost:8000/oauth/callback'
            }
            
            response = requests.post(token_url, data=token_data)
            
            if response.status_code == 200:
                tokens = response.json()
                
                print("✅ Tokens obtidos com sucesso!")
                print(f"Access Token: {tokens.get('access_token', '')[:20]}...")
                print(f"Refresh Token: {tokens.get('refresh_token', '')[:20]}...")
                print(f"Expires In: {tokens.get('expires_in')} segundos")
                
                # Atualizar configuração no banco
                config.update({
                    'google_calendar_refresh_token': tokens.get('refresh_token'),
                    'google_calendar_access_token': tokens.get('access_token'),
                    'google_calendar_token_expires': datetime.now().timestamp() + tokens.get('expires_in', 3600)
                })
                
                empresa_api.config = config
                session.commit()
                
                print(f"\n✅ OAuth2 configurado automaticamente!")
                print("Refresh Token salvo no banco de dados")
                print("\n🎉 Agora execute: python test_oauth_calendar.py")
                
            else:
                print(f"❌ Erro ao obter tokens: {response.status_code}")
                print(f"Resposta: {response.text}")
            
        finally:
            session.close()
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    auto_oauth_setup() 