#!/usr/bin/env python3
"""
Script para gerar refresh token do Google OAuth2
"""

import requests
import json

def generate_refresh_token(authorization_code, client_id, client_secret):
    """
    Gera refresh token a partir do código de autorização
    """
    token_url = "https://oauth2.googleapis.com/token"
    
    data = {
        'code': authorization_code,
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': 'http://localhost:8000/oauth/callback',
        'grant_type': 'authorization_code'
    }
    
    try:
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        
        print("✅ Refresh Token gerado com sucesso!")
        print(f"🔑 Refresh Token: {token_data.get('refresh_token')}")
        print(f"⏰ Access Token: {token_data.get('access_token')}")
        print(f"📅 Expira em: {token_data.get('expires_in')} segundos")
        
        return token_data.get('refresh_token')
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro ao gerar refresh token: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Resposta do servidor: {e.response.text}")
        return None

if __name__ == "__main__":
    # Código de autorização fornecido pelo usuário
    authorization_code = "4/0AVMBsJjxeR_73nhxLXI9frVXDTeXciQi4JO7N2shLRUW-PaB4c1GToNgmOIa-bC7ibJwMg"
    
    print("🚀 Gerando Refresh Token para Google Sheets...")
    print(f"📝 Código de autorização: {authorization_code}")
    print()
    
    # Você precisa fornecer o Client ID e Client Secret do Google
    print("⚠️  IMPORTANTE: Você precisa fornecer o Client ID e Client Secret do Google")
    print("   Estes são obtidos no Google Cloud Console > APIs & Services > Credentials")
    print()
    
    client_id = input("🔑 Client ID: ").strip()
    client_secret = input("🔐 Client Secret: ").strip()
    
    if not client_id or not client_secret:
        print("❌ Client ID e Client Secret são obrigatórios!")
        exit(1)
    
    print()
    refresh_token = generate_refresh_token(authorization_code, client_id, client_secret)
    
    if refresh_token:
        print()
        print("🎉 Sucesso! Agora você pode:")
        print("1. Copiar o refresh token acima")
        print("2. Colar no campo 'Refresh Token' da configuração do Google Sheets")
        print("3. Salvar as configurações")
        print()
        print("💡 Dica: O refresh token não expira, mas o access token sim")
    else:
        print("❌ Falha ao gerar refresh token. Verifique as credenciais e tente novamente.") 