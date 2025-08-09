#!/usr/bin/env python3
"""
Teste rápido para verificar se OAuth2 está funcionando
"""

import os
import sys
from datetime import datetime, timedelta

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def quick_oauth_test():
    """Teste rápido do OAuth2"""
    
    print("⚡ Teste rápido do OAuth2...")
    
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
            refresh_token = config.get('google_calendar_refresh_token')
            
            print("📋 Status das configurações:")
            print(f"  Client ID: {'✅' if client_id else '❌'}")
            print(f"  Client Secret: {'✅' if client_secret else '❌'}")
            print(f"  Refresh Token: {'✅' if refresh_token else '❌'}")
            
            if not client_id or not client_secret:
                print("\n❌ OAuth não configurado")
                print("Execute: python update_oauth_credentials.py")
                return
            
            if not refresh_token:
                print("\n❌ Refresh Token não gerado")
                print("Execute: python auto_oauth_setup.py")
                return
            
            print("\n✅ OAuth2 configurado!")
            
            # Testar acesso ao calendário
            print("\n🔍 Testando acesso ao calendário...")
            
            import requests
            
            # Verificar se o token expirou
            token_expires = config.get('google_calendar_token_expires', 0)
            current_time = datetime.now().timestamp()
            
            if current_time > token_expires:
                print("🔄 Token expirado, renovando...")
                
                # Renovar token
                token_url = "https://oauth2.googleapis.com/token"
                token_data = {
                    'client_id': client_id,
                    'client_secret': client_secret,
                    'refresh_token': refresh_token,
                    'grant_type': 'refresh_token'
                }
                
                response = requests.post(token_url, data=token_data)
                
                if response.status_code == 200:
                    tokens = response.json()
                    access_token = tokens.get('access_token')
                    
                    # Atualizar no banco
                    config.update({
                        'google_calendar_access_token': access_token,
                        'google_calendar_token_expires': datetime.now().timestamp() + tokens.get('expires_in', 3600)
                    })
                    
                    empresa_api.config = config
                    session.commit()
                    
                    print("✅ Token renovado")
                else:
                    print(f"❌ Erro ao renovar token: {response.status_code}")
                    return
            else:
                access_token = config.get('google_calendar_access_token')
                print("✅ Token válido")
            
            # Testar acesso ao calendário
            test_date = "2025-08-11"
            start_date = datetime.strptime(test_date, '%Y-%m-%d')
            end_date = start_date + timedelta(days=1)
            
            calendar_url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            params = {
                'timeMin': start_date.isoformat() + 'Z',
                'timeMax': end_date.isoformat() + 'Z',
                'singleEvents': 'true',
                'orderBy': 'startTime'
            }
            
            response = requests.get(calendar_url, headers=headers, params=params)
            
            if response.status_code == 200:
                events_data = response.json()
                events = events_data.get('items', [])
                
                print(f"\n🎉 SUCESSO! OAuth2 funcionando!")
                print(f"Eventos encontrados: {len(events)}")
                
                if events:
                    print("\n📅 Eventos encontrados:")
                    for i, event in enumerate(events, 1):
                        start = event.get('start', {}).get('dateTime', 'Sem horário')
                        summary = event.get('summary', 'Sem título')
                        print(f"  {i}. {start} - {summary}")
                        
                        # Verificar se é o evento "teste"
                        if summary == "teste":
                            print(f"    ✅ Evento 'teste' encontrado!")
                else:
                    print("✅ Nenhum evento encontrado (calendário vazio)")
                    
            else:
                print(f"❌ Erro ao acessar calendário: {response.status_code}")
                print(f"Resposta: {response.text}")
            
        finally:
            session.close()
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    quick_oauth_test() 