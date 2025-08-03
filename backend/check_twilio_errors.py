#!/usr/bin/env python3
"""
Verifica erros específicos relacionados ao Twilio e envio de mensagens
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Base, Empresa, Mensagem, Log
import requests
import json

# URL do banco de produção
PRODUCTION_DB_URL = "postgresql://atendeai:2pjZBzhDlZY275Z4FubsnBFPsjvLHNRw@dpg-d24vpfngi27c73bh06n0-a.oregon-postgres.render.com/atendeai"

def check_twilio_errors():
    """Verifica erros específicos do Twilio"""
    
    print("🔍 VERIFICANDO ERROS DO TWILIO")
    print("=" * 80)
    
    try:
        # Conectar ao banco
        engine = create_engine(PRODUCTION_DB_URL)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Buscar empresa
        empresa = session.query(Empresa).filter(Empresa.slug == 'tinyteams').first()
        if not empresa:
            print("❌ Empresa TinyTeams não encontrada!")
            return
        
        print(f"🏢 Empresa: {empresa.nome}")
        
        # 1. VERIFICAR LOGS DE ERRO RECENTES
        print("\n📋 1. Logs de erro recentes (últimas 24h):")
        
        from datetime import datetime, timedelta
        ontem = datetime.now() - timedelta(hours=24)
        
        logs_erro = session.query(Log).filter(
            Log.empresa_id == empresa.id,
            Log.level == 'ERROR',
            Log.timestamp >= ontem
        ).order_by(Log.timestamp.desc()).all()
        
        if logs_erro:
            print(f"   📊 Total de erros: {len(logs_erro)}")
            for log in logs_erro:
                print(f"   🕐 {log.timestamp}")
                print(f"   ❌ {log.message}")
                if log.details:
                    print(f"   🔍 Detalhes: {log.details}")
                print("-" * 50)
        else:
            print("   ✅ Nenhum erro encontrado nas últimas 24h")
        
        # 2. VERIFICAR LOGS RELACIONADOS AO TWILIO
        print("\n📋 2. Logs relacionados ao Twilio:")
        
        logs_twilio = session.query(Log).filter(
            Log.empresa_id == empresa.id,
            Log.message.ilike('%twilio%')
        ).order_by(Log.timestamp.desc()).limit(10).all()
        
        if logs_twilio:
            print(f"   📊 Total de logs Twilio: {len(logs_twilio)}")
            for log in logs_twilio:
                print(f"   🕐 {log.timestamp} [{log.level}]")
                print(f"   📝 {log.message}")
                if log.details:
                    print(f"   🔍 Detalhes: {log.details}")
                print("-" * 50)
        else:
            print("   ⚠️ Nenhum log relacionado ao Twilio encontrado")
        
        # 3. VERIFICAR LOGS DE ENVIO DE MENSAGENS
        print("\n📋 3. Logs de envio de mensagens:")
        
        logs_envio = session.query(Log).filter(
            Log.empresa_id == empresa.id,
            Log.message.ilike('%enviar%') | 
            Log.message.ilike('%send%') |
            Log.message.ilike('%message%')
        ).order_by(Log.timestamp.desc()).limit(10).all()
        
        if logs_envio:
            print(f"   📊 Total de logs de envio: {len(logs_envio)}")
            for log in logs_envio:
                print(f"   🕐 {log.timestamp} [{log.level}]")
                print(f"   📝 {log.message}")
                if log.details:
                    print(f"   🔍 Detalhes: {log.details}")
                print("-" * 50)
        else:
            print("   ⚠️ Nenhum log de envio encontrado")
        
        # 4. VERIFICAR MENSAGENS RECENTES
        print("\n📋 4. Mensagens recentes:")
        
        mensagens = session.query(Mensagem).filter(
            Mensagem.empresa_id == empresa.id
        ).order_by(Mensagem.timestamp.desc()).limit(5).all()
        
        if mensagens:
            print(f"   📊 Total de mensagens: {len(mensagens)}")
            for msg in mensagens:
                print(f"   🕐 {msg.timestamp}")
                print(f"   {'🤖 Bot' if msg.is_bot else '👤 Cliente'}: {msg.text[:100]}...")
                print("-" * 50)
        else:
            print("   ⚠️ Nenhuma mensagem encontrada")
        
        # 5. TESTE DE CREDENCIAIS DO TWILIO
        print("\n🧪 5. Testando credenciais do Twilio...")
        
        try:
            # Testar se as credenciais são válidas fazendo uma requisição para a API do Twilio
            import base64
            credentials = f"{empresa.twilio_sid}:{empresa.twilio_token}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            headers = {
                'Authorization': f'Basic {encoded_credentials}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            # Tentar buscar informações da conta (endpoint seguro)
            response = requests.get(
                f"https://api.twilio.com/2010-04-01/Accounts/{empresa.twilio_sid}.json",
                headers=headers,
                timeout=10
            )
            
            print(f"   📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                print("   ✅ Credenciais do Twilio são válidas!")
                data = response.json()
                print(f"   📊 Status da conta: {data.get('status', 'N/A')}")
            elif response.status_code == 401:
                print("   ❌ Credenciais do Twilio inválidas!")
            else:
                print(f"   ⚠️ Resposta inesperada: {response.text[:100]}")
                
        except Exception as e:
            print(f"   ❌ Erro ao testar credenciais: {e}")
        
        session.close()
        
    except Exception as e:
        print(f"❌ Erro durante verificação: {e}")
        return

if __name__ == "__main__":
    check_twilio_errors() 