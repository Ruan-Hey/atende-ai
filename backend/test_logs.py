#!/usr/bin/env python3
"""
Teste para verificar se a função de logs está funcionando
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import SessionLocal
from models import Log, Empresa

def test_logs_function():
    """Testa a função de logs diretamente"""
    session = SessionLocal()
    try:
        # Construir query base
        query = session.query(Log).order_by(Log.timestamp.desc())
        
        # Limitar resultados
        logs_db = query.limit(5).all()
        
        print(f"Logs encontrados no banco: {len(logs_db)}")
        
        # Converter para formato da API
        logs = []
        for log in logs_db:
            empresa_nome = None
            if log.empresa_id:
                empresa_obj = session.query(Empresa).filter(Empresa.id == log.empresa_id).first()
                empresa_nome = empresa_obj.nome if empresa_obj else None
            
            log_dict = {
                "level": log.level,
                "message": log.message,
                "empresa": empresa_nome,
                "timestamp": log.timestamp.isoformat(),
                "details": log.details or {}
            }
            logs.append(log_dict)
            print(f"Log: {log_dict}")
        
        return {"logs": logs}
    except Exception as e:
        print(f"Erro: {e}")
        return {"error": str(e)}
    finally:
        session.close()

if __name__ == "__main__":
    print("🧪 Testando função de logs...")
    result = test_logs_function()
    print(f"Resultado: {result}") 