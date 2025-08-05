#!/usr/bin/env python3
"""
Script para popular o banco de dados com logs iniciais para demonstração
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Log, Empresa
from config import Config

def populate_logs():
    """Popula o banco com logs de demonstração"""
    
    # Criar engine e session
    engine = create_engine(Config.POSTGRES_URL)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        # Buscar empresas existentes
        empresas = session.query(Empresa).all()
        
        if not empresas:
            print("❌ Nenhuma empresa encontrada. Crie empresas primeiro.")
            return
        
        # Logs de demonstração
        demo_logs = [
            # Logs de sistema
            {
                "level": "INFO",
                "message": "Sistema iniciado com sucesso",
                "empresa_id": None,
                "details": {"version": "1.0.0", "timestamp": datetime.now().isoformat()}
            },
            {
                "level": "INFO",
                "message": "Banco de dados conectado",
                "empresa_id": None,
                "details": {"database": "PostgreSQL", "status": "connected"}
            },
            {
                "level": "INFO",
                "message": "Redis conectado",
                "empresa_id": None,
                "details": {"service": "Redis", "status": "connected"}
            },
            
            # Logs de webhook
            {
                "level": "INFO",
                "message": "Webhook recebido de 5511999999999",
                "empresa_id": empresas[0].id if empresas else None,
                "details": {"empresa": empresas[0].slug if empresas else "demo", "message_type": "text", "body_length": 25}
            },
            {
                "level": "INFO",
                "message": "Mensagem processada com sucesso",
                "empresa_id": empresas[0].id if empresas else None,
                "details": {"cliente_id": "5511999999999", "response_time": "1.2s"}
            },
            
            # Logs de erro
            {
                "level": "ERROR",
                "message": "Erro ao processar mensagem de áudio",
                "empresa_id": empresas[0].id if empresas else None,
                "details": {"error": "Audio format not supported", "cliente_id": "5511888888888"}
            },
            {
                "level": "WARNING",
                "message": "Tentativa de login falhada para usuario@teste.com",
                "empresa_id": None,
                "details": {"ip": "192.168.1.100", "user_agent": "Mozilla/5.0"}
            },
            
            # Logs de atividade
            {
                "level": "INFO",
                "message": "Usuário admin@tinyteams.app acessou métricas admin",
                "empresa_id": None,
                "details": {"user_id": 1, "action": "view_metrics"}
            },
            {
                "level": "INFO",
                "message": "Nova empresa criada: Empresa Demo",
                "empresa_id": None,
                "details": {"empresa_slug": "empresa-demo", "created_by": "admin@tinyteams.app"}
            },
            
            # Logs de buffer
            {
                "level": "INFO",
                "message": "Buffer processado com sucesso",
                "empresa_id": empresas[0].id if empresas else None,
                "details": {"messages_processed": 5, "processing_time": "0.8s"}
            },
            {
                "level": "WARNING",
                "message": "Buffer com alta latência detectado",
                "empresa_id": empresas[0].id if empresas else None,
                "details": {"latency": "15.2s", "queue_size": 12}
            }
        ]
        
        # Criar logs com timestamps variados (últimas 24h)
        now = datetime.now()
        for i, log_data in enumerate(demo_logs):
            # Distribuir logs nas últimas 24 horas
            hours_ago = (i * 2) % 24  # Distribuir em 24 horas
            timestamp = now - timedelta(hours=hours_ago, minutes=i*3)
            
            log = Log(
                level=log_data["level"],
                message=log_data["message"],
                empresa_id=log_data["empresa_id"],
                details=log_data["details"],
                timestamp=timestamp
            )
            session.add(log)
        
        session.commit()
        print(f"✅ {len(demo_logs)} logs de demonstração criados com sucesso!")
        print("📊 Agora você pode ver logs reais na interface de logs")
        
    except Exception as e:
        print(f"❌ Erro ao popular logs: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    print("🚀 Populando banco de dados com logs de demonstração...")
    populate_logs() 