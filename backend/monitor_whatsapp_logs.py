#!/usr/bin/env python3
"""
Monitor de logs em tempo real para WhatsApp
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Base, Empresa, Mensagem, Log
import time
from datetime import datetime, timedelta

# URL do banco de produção
PRODUCTION_DB_URL = "postgresql://atendeai:2pjZBzhDlZY275Z4FubsnBFPsjvLHNRw@dpg-d24vpfngi27c73bh06n0-a.oregon-postgres.render.com/atendeai"

def monitor_whatsapp_logs():
    """Monitora logs em tempo real"""
    
    print("📊 MONITOR DE LOGS - WHATSAPP")
    print("=" * 80)
    print("🕐 Iniciando monitoramento...")
    print("📱 Envie uma mensagem no WhatsApp para +554184447366")
    print("🔍 Monitorando logs em tempo real...")
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
        
        # Contador inicial de mensagens
        mensagens_iniciais = session.query(Mensagem).filter(
            Mensagem.empresa_id == empresa.id
        ).count()
        
        # Contador inicial de logs
        logs_iniciais = session.query(Log).filter(
            Log.empresa_id == empresa.id
        ).count()
        
        print(f"📊 Mensagens iniciais: {mensagens_iniciais}")
        print(f"📊 Logs iniciais: {logs_iniciais}")
        print("=" * 80)
        
        ultima_mensagem_id = 0
        ultimo_log_id = 0
        
        while True:
            try:
                # Verificar novas mensagens
                novas_mensagens = session.query(Mensagem).filter(
                    Mensagem.empresa_id == empresa.id,
                    Mensagem.id > ultima_mensagem_id
                ).order_by(Mensagem.timestamp.desc()).all()
                
                if novas_mensagens:
                    print(f"\n💬 NOVAS MENSAGENS DETECTADAS ({len(novas_mensagens)}):")
                    for msg in reversed(novas_mensagens):
                        print(f"   🕐 {msg.timestamp}")
                        print(f"   {'🤖 Bot' if msg.is_bot else '👤 Cliente'}: {msg.text}")
                        print(f"   📊 ID: {msg.id}")
                        print("-" * 50)
                        ultima_mensagem_id = max(ultima_mensagem_id, msg.id)
                
                # Verificar novos logs
                novos_logs = session.query(Log).filter(
                    Log.empresa_id == empresa.id,
                    Log.id > ultimo_log_id
                ).order_by(Log.timestamp.desc()).all()
                
                if novos_logs:
                    print(f"\n📋 NOVOS LOGS DETECTADOS ({len(novos_logs)}):")
                    for log in reversed(novos_logs):
                        print(f"   🕐 {log.timestamp}")
                        print(f"   📊 [{log.level}]: {log.message}")
                        if log.details:
                            print(f"   🔍 Detalhes: {log.details}")
                        print("-" * 50)
                        ultimo_log_id = max(ultimo_log_id, log.id)
                
                # Verificar logs de erro específicos
                logs_erro = session.query(Log).filter(
                    Log.empresa_id == empresa.id,
                    Log.level == 'ERROR',
                    Log.timestamp >= datetime.now() - timedelta(minutes=5)
                ).all()
                
                if logs_erro:
                    print(f"\n❌ ERROS RECENTES DETECTADOS ({len(logs_erro)}):")
                    for log in logs_erro:
                        print(f"   🕐 {log.timestamp}")
                        print(f"   ❌ ERRO: {log.message}")
                        if log.details:
                            print(f"   🔍 Detalhes: {log.details}")
                        print("-" * 50)
                
                # Status a cada 10 segundos
                print(f"\r🕐 {datetime.now().strftime('%H:%M:%S')} - Monitorando... (Ctrl+C para parar)", end="", flush=True)
                
                time.sleep(10)
                
            except KeyboardInterrupt:
                print("\n\n🛑 Monitoramento interrompido pelo usuário")
                break
            except Exception as e:
                print(f"\n❌ Erro durante monitoramento: {e}")
                time.sleep(5)
        
        session.close()
        
    except Exception as e:
        print(f"❌ Erro ao conectar ao banco: {e}")
        return

if __name__ == "__main__":
    monitor_whatsapp_logs() 