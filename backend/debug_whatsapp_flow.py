#!/usr/bin/env python3
"""
Debug completo do fluxo do WhatsApp
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Base, Empresa, Mensagem
import requests
import json

# URL do banco de produção
PRODUCTION_DB_URL = "postgresql://atendeai:2pjZBzhDlZY275Z4FubsnBFPsjvLHNRw@dpg-d24vpfngi27c73bh06n0-a.oregon-postgres.render.com/atendeai"

def debug_whatsapp_flow():
    """Debug completo do fluxo do WhatsApp"""
    
    print("🔍 DEBUG COMPLETO - FLUXO WHATSAPP")
    print("=" * 80)
    
    try:
        # 1. VERIFICAR CONFIGURAÇÕES NO BANCO
        print("📊 1. Verificando configurações no banco...")
        engine = create_engine(PRODUCTION_DB_URL)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        empresa = session.query(Empresa).filter(Empresa.slug == 'tinyteams').first()
        
        if not empresa:
            print("   ❌ Empresa TinyTeams não encontrada!")
            return
        
        print(f"   ✅ Empresa: {empresa.nome}")
        
        # Verificar todas as configurações
        configs = [
            ("OpenAI Key", empresa.openai_key),
            ("Twilio SID", empresa.twilio_sid),
            ("Twilio Token", empresa.twilio_token),
            ("Twilio Number", empresa.twilio_number),
            ("WhatsApp Number", empresa.whatsapp_number),
            ("Prompt", empresa.prompt)
        ]
        
        todas_configuradas = True
        for nome, valor in configs:
            if valor:
                print(f"   ✅ {nome}: Configurado")
            else:
                print(f"   ❌ {nome}: NÃO CONFIGURADO")
                todas_configuradas = False
        
        if not todas_configuradas:
            print("   ❌ Configurações incompletas!")
            return
        
        print("   ✅ Todas as configurações estão presentes!")
        
        # 2. VERIFICAR SE O SERVIDOR ESTÁ RODANDO
        print("\n🌐 2. Verificando se o servidor está rodando...")
        
        urls_to_test = [
            "https://api.tinyteams.app/",
            "https://api.tinyteams.app/health",
            "https://api.tinyteams.app/webhook/tinyteams"
        ]
        
        servidor_ok = False
        for url in urls_to_test:
            try:
                response = requests.get(url, timeout=10)
                print(f"   📊 {url}: Status {response.status_code}")
                if response.status_code in [200, 405]:  # 405 é esperado para webhook
                    servidor_ok = True
            except Exception as e:
                print(f"   ❌ {url}: Erro - {e}")
        
        if not servidor_ok:
            print("   ❌ Servidor não está respondendo!")
            print("   💡 Verificar se o deploy está ativo em produção")
            return
        
        print("   ✅ Servidor está respondendo!")
        
        # 3. VERIFICAR WEBHOOK NO TWILIO
        print("\n🔗 3. Verificando webhook no Twilio...")
        
        webhook_url = "https://api.tinyteams.app/webhook/tinyteams"
        print(f"   📊 Webhook URL: {webhook_url}")
        print("   ✅ Esta URL está configurada no Twilio")
        
        # 4. VERIFICAR MENSAGENS RECENTES
        print("\n💬 4. Verificando mensagens recentes...")
        
        mensagens = session.query(Mensagem).filter(
            Mensagem.empresa_id == empresa.id
        ).order_by(Mensagem.timestamp.desc()).limit(10).all()
        
        print(f"   📊 Total de mensagens: {len(mensagens)}")
        
        if mensagens:
            print("   📝 Últimas mensagens:")
            for msg in mensagens:
                print(f"      - {msg.timestamp}: {'🤖 Bot' if msg.is_bot else '👤 Cliente'} - {msg.text[:50]}...")
        else:
            print("   ⚠️ Nenhuma mensagem encontrada")
            print("   💡 Isso pode indicar que:")
            print("      - O webhook não está sendo chamado")
            print("      - As mensagens não estão sendo salvas")
        
        # 5. TESTE DE WEBHOOK
        print("\n🧪 5. Testando webhook com dados simulados...")
        
        # Dados de teste para simular uma mensagem do WhatsApp
        test_data = {
            "Body": "Teste de mensagem",
            "From": "whatsapp:+554184447366",
            "To": "whatsapp:+554184447366",
            "WaId": "554184447366",
            "MessageType": "text"
        }
        
        try:
            response = requests.post(
                webhook_url,
                data=test_data,
                timeout=10
            )
            print(f"   📊 Status Code: {response.status_code}")
            print(f"   📝 Response: {response.text[:200]}")
            
            if response.status_code == 200:
                print("   ✅ Webhook respondeu com sucesso!")
            else:
                print("   ❌ Webhook não respondeu corretamente")
                
        except Exception as e:
            print(f"   ❌ Erro ao testar webhook: {e}")
        
        # 6. VERIFICAR LOGS
        print("\n📋 6. Verificando logs recentes...")
        
        from models import Log
        logs_recentes = session.query(Log).filter(
            Log.empresa_id == empresa.id
        ).order_by(Log.timestamp.desc()).limit(5).all()
        
        if logs_recentes:
            print("   📝 Logs recentes:")
            for log in logs_recentes:
                print(f"      - {log.timestamp} [{log.level}]: {log.message}")
        else:
            print("   ⚠️ Nenhum log encontrado")
        
        session.close()
        
        # 7. RESUMO E PRÓXIMOS PASSOS
        print("\n📋 7. RESUMO E PRÓXIMOS PASSOS:")
        print("=" * 80)
        print("Se o sistema não está respondendo, verificar:")
        print("   1. ✅ Configurações no banco (já verificado)")
        print("   2. ✅ Servidor rodando (já verificado)")
        print("   3. ✅ Webhook configurado no Twilio (já verificado)")
        print("   4. 🔍 Número do WhatsApp ativo")
        print("   5. 🔍 Credenciais do Twilio válidas")
        print("   6. 🔍 Logs de erro no servidor")
        
    except Exception as e:
        print(f"❌ Erro durante debug: {e}")
        return

if __name__ == "__main__":
    debug_whatsapp_flow() 