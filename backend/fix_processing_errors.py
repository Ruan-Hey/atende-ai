#!/usr/bin/env python3
"""
Script para corrigir erros de processamento identificados
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Base, Empresa, Mensagem, Log
import requests
import json
import asyncio

# URL do banco de produção
PRODUCTION_DB_URL = "postgresql://atendeai:2pjZBzhDlZY275Z4FubsnBFPsjvLHNRw@dpg-d24vpfngi27c73bh06n0-a.oregon-postgres.render.com/atendeai"

def test_openai_integration():
    """Testa a integração com OpenAI diretamente"""
    
    print("🧪 TESTANDO INTEGRAÇÃO COM OPENAI")
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
        print(f"🔑 OpenAI Key: {empresa.openai_key[:10]}...{empresa.openai_key[-4:]}")
        print(f"📝 Prompt: {empresa.prompt[:50]}..." if empresa.prompt else "❌ Prompt não configurado")
        
        # Testar OpenAI diretamente
        print("\n🧪 Testando OpenAI...")
        
        try:
            import openai
            client = openai.OpenAI(api_key=empresa.openai_key)
            
            # Teste simples
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Você é um assistente útil."},
                    {"role": "user", "content": "Olá, como você está?"}
                ],
                max_tokens=50,
                temperature=0.7
            )
            
            result = response.choices[0].message.content
            print(f"   ✅ OpenAI funcionando!")
            print(f"   📝 Resposta: {result}")
            
        except Exception as e:
            print(f"   ❌ Erro na OpenAI: {e}")
            return
        
        # Testar Twilio
        print("\n🧪 Testando Twilio...")
        
        try:
            import base64
            credentials = f"{empresa.twilio_sid}:{empresa.twilio_token}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            headers = {
                'Authorization': f'Basic {encoded_credentials}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            # Testar envio de mensagem
            data = {
                'To': f'whatsapp:+{empresa.whatsapp_number}',
                'From': f'whatsapp:+{empresa.twilio_number}',
                'Body': 'Teste de integração'
            }
            
            response = requests.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{empresa.twilio_sid}/Messages.json",
                headers=headers,
                data=data,
                timeout=10
            )
            
            print(f"   📊 Status Code: {response.status_code}")
            
            if response.status_code == 201:
                print("   ✅ Twilio funcionando!")
                result = response.json()
                print(f"   📝 Message SID: {result.get('sid', 'N/A')}")
            else:
                print(f"   ❌ Erro no Twilio: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Erro no Twilio: {e}")
        
        session.close()
        
    except Exception as e:
        print(f"❌ Erro durante teste: {e}")
        return

def test_message_processing():
    """Testa o processamento de mensagens com dados seguros"""
    
    print("\n🧪 TESTANDO PROCESSAMENTO DE MENSAGENS")
    print("=" * 80)
    
    # Dados de teste seguros
    test_data = {
        "Body": "Teste de processamento seguro",
        "From": "whatsapp:+554184447366",
        "To": "whatsapp:+554184447366",
        "WaId": "554184447366",
        "MessageType": "text",
        "ProfileName": "Teste"
    }
    
    try:
        response = requests.post(
            "https://api.tinyteams.app/webhook/tinyteams",
            data=test_data,
            timeout=10
        )
        print(f"📊 Status Code: {response.status_code}")
        print(f"📝 Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Webhook respondeu com sucesso!")
            
            # Aguardar processamento
            import time
            time.sleep(5)
            
            # Verificar se foi processado
            response = requests.get("https://api.tinyteams.app/api/admin/buffer/status", timeout=10)
            if response.status_code == 200:
                buffer_data = response.json()
                print(f"📊 Buffer Status: {json.dumps(buffer_data, indent=2)}")
            
        else:
            print("❌ Erro no webhook")
            
    except Exception as e:
        print(f"❌ Erro ao testar processamento: {e}")

def check_configuration_issues():
    """Verifica possíveis problemas de configuração"""
    
    print("\n🔍 VERIFICANDO PROBLEMAS DE CONFIGURAÇÃO")
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
        
        print("📋 Verificando configurações:")
        
        # Verificar se o prompt está vazio ou None
        if not empresa.prompt or empresa.prompt.strip() == "":
            print("   ❌ PROMPT ESTÁ VAZIO!")
            print("   💡 Isso pode causar o erro 'NoneType' object has no attribute 'rstrip'")
        else:
            print(f"   ✅ Prompt configurado ({len(empresa.prompt)} caracteres)")
        
        # Verificar se a chave da OpenAI está válida
        if not empresa.openai_key or empresa.openai_key.strip() == "":
            print("   ❌ CHAVE DA OPENAI ESTÁ VAZIA!")
        else:
            print(f"   ✅ OpenAI Key configurada ({len(empresa.openai_key)} caracteres)")
        
        # Verificar configurações do Twilio
        if not empresa.twilio_sid or empresa.twilio_sid.strip() == "":
            print("   ❌ TWILIO SID ESTÁ VAZIO!")
        else:
            print(f"   ✅ Twilio SID configurado")
        
        if not empresa.twilio_token or empresa.twilio_token.strip() == "":
            print("   ❌ TWILIO TOKEN ESTÁ VAZIO!")
        else:
            print(f"   ✅ Twilio Token configurado")
        
        if not empresa.twilio_number or empresa.twilio_number.strip() == "":
            print("   ❌ TWILIO NUMBER ESTÁ VAZIO!")
        else:
            print(f"   ✅ Twilio Number configurado")
        
        session.close()
        
    except Exception as e:
        print(f"❌ Erro durante verificação: {e}")
        return

if __name__ == "__main__":
    test_openai_integration()
    test_message_processing()
    check_configuration_issues() 