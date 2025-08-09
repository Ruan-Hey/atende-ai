#!/usr/bin/env python3
"""
Script para obter tokens OAuth2 do Google Calendar
"""

import os
import sys
import json
import webbrowser
from datetime import datetime

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def get_oauth_tokens():
    """Obtém tokens OAuth2 do Google Calendar"""
    
    print("🔐 Obtendo tokens OAuth2 do Google Calendar...")
    
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
            
            # Verificar se tem OAuth configurado
            client_id = config.get('google_calendar_client_id')
            client_secret = config.get('google_calendar_client_secret')
            
            if not client_id or not client_secret:
                print("❌ OAuth não configurado")
                print("Execute primeiro: python setup_oauth_calendar.py")
                return
            
            print("✅ OAuth configurado")
            print(f"Client ID: {client_id[:20]}...")
            
            # Construir URL de autorização
            from urllib.parse import urlencode
            
            auth_params = {
                'client_id': client_id,
                'redirect_uri': 'http://localhost:8000/oauth/callback',
                'scope': 'https://www.googleapis.com/auth/calendar',
                'response_type': 'code',
                'access_type': 'offline',
                'prompt': 'consent'
            }
            
            auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(auth_params)}"
            
            print(f"\n🔗 URL de autorização:")
            print(auth_url)
            
            print(f"\n📋 Passos:")
            print("1. Abra o link acima no navegador")
            print("2. Faça login com sua conta Google")
            print("3. Autorize o acesso ao Google Calendar")
            print("4. Copie o código de autorização da URL de redirecionamento")
            print("5. Cole o código aqui quando solicitado")
            
            # Abrir navegador automaticamente
            try:
                webbrowser.open(auth_url)
                print(f"\n🌐 Navegador aberto automaticamente")
            except:
                print(f"\n📋 Copie e cole este link no navegador:")
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
            
            import requests
            
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
                
                print(f"\n✅ Tokens salvos no banco de dados!")
                print("Agora execute: python test_oauth_calendar.py")
                
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
    get_oauth_tokens() 