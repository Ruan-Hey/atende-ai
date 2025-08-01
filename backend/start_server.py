#!/usr/bin/env python3
import uvicorn
import sys
import os

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(__file__))

if __name__ == "__main__":
    print("🚀 Iniciando servidor...")
    try:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except Exception as e:
        print(f"❌ Erro ao iniciar servidor: {e}")
        import traceback
        traceback.print_exc() 