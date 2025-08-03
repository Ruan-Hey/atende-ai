#!/usr/bin/env python3
"""
Verifica histórico do agente e logs de processamento
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

def check_agent_history():
    """Verifica histórico do agente e logs de processamento"""
    
    print("🔍 VERIFICANDO HISTÓRICO DO AGENTE")
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
        
        # 1. VERIFICAR TODOS OS LOGS DA EMPRESA
        print("\n📋 1. Todos os logs da empresa (últimos 50):")
        
        todos_logs = session.query(Log).filter(
            Log.empresa_id == empresa.id
        ).order_by(Log.timestamp.desc()).limit(50).all()
        
        if todos_logs:
            print(f"   📊 Total de logs: {len(todos_logs)}")
            for log in todos_logs:
                print(f"   🕐 {log.timestamp} [{log.level}]")
                print(f"   📝 {log.message}")
                if log.details:
                    print(f"   🔍 Detalhes: {log.details}")
                print("-" * 50)
        else:
            print("   ⚠️ Nenhum log encontrado")
        
        # 2. VERIFICAR MENSAGENS RECENTES
        print("\n📋 2. Mensagens recentes:")
        
        mensagens = session.query(Mensagem).filter(
            Mensagem.empresa_id == empresa.id
        ).order_by(Mensagem.timestamp.desc()).limit(10).all()
        
        if mensagens:
            print(f"   📊 Total de mensagens: {len(mensagens)}")
            for msg in mensagens:
                print(f"   🕐 {msg.timestamp}")
                print(f"   {'🤖 Bot' if msg.is_bot else '👤 Cliente'}: {msg.text[:100]}...")
                print(f"   📊 Cliente ID: {msg.cliente_id}")
                print("-" * 50)
        else:
            print("   ⚠️ Nenhuma mensagem encontrada")
        
        # 3. VERIFICAR LOGS DE PROCESSAMENTO
        print("\n📋 3. Logs de processamento (últimas 24h):")
        
        from datetime import datetime, timedelta
        ontem = datetime.now() - timedelta(hours=24)
        
        logs_processamento = session.query(Log).filter(
            Log.empresa_id == empresa.id,
            Log.timestamp >= ontem,
            Log.message.ilike('%process%') |
            Log.message.ilike('%openai%') |
            Log.message.ilike('%buffer%') |
            Log.message.ilike('%enviar%') |
            Log.message.ilike('%send%')
        ).order_by(Log.timestamp.desc()).all()
        
        if logs_processamento:
            print(f"   📊 Total de logs de processamento: {len(logs_processamento)}")
            for log in logs_processamento:
                print(f"   🕐 {log.timestamp} [{log.level}]")
                print(f"   📝 {log.message}")
                if log.details:
                    print(f"   🔍 Detalhes: {log.details}")
                print("-" * 50)
        else:
            print("   ⚠️ Nenhum log de processamento encontrado")
        
        # 4. VERIFICAR LOGS DE ERRO ESPECÍFICOS
        print("\n📋 4. Logs de erro específicos:")
        
        logs_erro = session.query(Log).filter(
            Log.empresa_id == empresa.id,
            Log.level == 'ERROR'
        ).order_by(Log.timestamp.desc()).limit(10).all()
        
        if logs_erro:
            print(f"   📊 Total de erros: {len(logs_erro)}")
            for log in logs_erro:
                print(f"   🕐 {log.timestamp}")
                print(f"   ❌ {log.message}")
                if log.details:
                    print(f"   🔍 Detalhes: {log.details}")
                print("-" * 50)
        else:
            print("   ✅ Nenhum erro encontrado")
        
        # 5. VERIFICAR STATUS DO BUFFER
        print("\n📋 5. Status do buffer:")
        
        try:
            response = requests.get("https://api.tinyteams.app/api/admin/buffer/status", timeout=10)
            print(f"   📊 Status Code: {response.status_code}")
            if response.status_code == 200:
                buffer_data = response.json()
                print(f"   📝 Buffer Status: {buffer_data}")
            else:
                print(f"   ⚠️ Resposta inesperada: {response.text[:100]}")
        except Exception as e:
            print(f"   ❌ Erro ao verificar buffer: {e}")
        
        # 6. TESTE DE PROCESSAMENTO MANUAL
        print("\n🧪 6. Teste de processamento manual...")
        
        # Simular uma mensagem de teste
        test_data = {
            "Body": "Teste de processamento",
            "From": "whatsapp:+554184447366",
            "To": "whatsapp:+554184447366",
            "WaId": "554184447366",
            "MessageType": "text"
        }
        
        try:
            response = requests.post(
                "https://api.tinyteams.app/webhook/tinyteams",
                data=test_data,
                timeout=10
            )
            print(f"   📊 Status Code: {response.status_code}")
            print(f"   📝 Response: {response.text}")
            
            if response.status_code == 200:
                print("   ✅ Webhook respondeu com sucesso!")
                
                # Aguardar um pouco e verificar se a mensagem foi processada
                import time
                time.sleep(5)
                
                # Verificar se a mensagem foi salva
                nova_mensagem = session.query(Mensagem).filter(
                    Mensagem.empresa_id == empresa.id,
                    Mensagem.text.like('%Teste de processamento%')
                ).first()
                
                if nova_mensagem:
                    print("   ✅ Mensagem foi salva no banco!")
                else:
                    print("   ❌ Mensagem não foi salva no banco")
                    
        except Exception as e:
            print(f"   ❌ Erro ao testar processamento: {e}")
        
        session.close()
        
    except Exception as e:
        print(f"❌ Erro durante verificação: {e}")
        return

if __name__ == "__main__":
    check_agent_history() 