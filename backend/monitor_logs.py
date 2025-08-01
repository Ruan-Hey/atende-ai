#!/usr/bin/env python3
import os
import sys
import time
from datetime import datetime
sys.path.append(os.path.dirname(__file__))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Log, Mensagem
from config import Config

def monitor_logs():
    """Monitora logs em tempo real"""
    engine = create_engine(Config.POSTGRES_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    session = SessionLocal()
    try:
        print("=== MONITOR DE LOGS EM TEMPO REAL ===")
        print("Pressione Ctrl+C para parar")
        print("=" * 50)
        
        # Pegar o último log ID para começar a monitorar
        last_log = session.query(Log).order_by(Log.id.desc()).first()
        last_id = last_log.id if last_log else 0
        
        print(f"🕐 Iniciando monitoramento a partir do log ID: {last_id}")
        print(f"📅 Hora atual: {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 50)
        
        while True:
            # Buscar novos logs
            new_logs = session.query(Log).filter(Log.id > last_id).order_by(Log.id.asc()).all()
            
            for log in new_logs:
                timestamp = log.timestamp.strftime('%H:%M:%S') if log.timestamp else 'N/A'
                print(f"[{timestamp}] {log.level}: {log.message}")
                
                # Se for um erro, destacar
                if log.level == 'ERROR':
                    print(f"    🔴 ERRO DETECTADO: {log.message}")
                
                # Se for relacionado ao webhook, destacar
                if 'webhook' in log.message.lower() or 'tinyteams' in log.message.lower():
                    print(f"    🔵 WEBHOOK: {log.message}")
                
                last_id = log.id
            
            # Verificar mensagens recentes
            recent_messages = session.query(Mensagem).filter(
                Mensagem.empresa == 'tinyteams'
            ).order_by(Mensagem.timestamp.desc()).limit(5).all()
            
            if recent_messages:
                print(f"\n📱 Últimas mensagens da TinyTeams:")
                for msg in recent_messages:
                    timestamp = msg.timestamp.strftime('%H:%M:%S') if msg.timestamp else 'N/A'
                    print(f"    [{timestamp}] {msg.tipo}: {msg.conteudo[:50]}...")
            
            time.sleep(2)  # Verificar a cada 2 segundos
            
    except KeyboardInterrupt:
        print("\n🛑 Monitoramento interrompido pelo usuário")
    except Exception as e:
        print(f"❌ Erro no monitoramento: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    monitor_logs() 