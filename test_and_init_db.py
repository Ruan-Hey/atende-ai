#!/usr/bin/env python3
"""
Script para testar conectividade e inicializar banco após restart no Render
"""

import subprocess
import os
import sys
import time
from datetime import datetime

def test_connection():
    """Testa se o banco está online"""
    try:
        test_cmd = [
            "psql",
            f"--host=dpg-d24vpfngi27c73bh06n0-a.oregon-postgres.render.com",
            f"--port=5432",
            f"--username=atendeai",
            f"--dbname=atendeai",
            "--command=SELECT 1;",
            "--no-password"
        ]
        
        env = os.environ.copy()
        env["PGPASSWORD"] = "2pjZBzhDlZY275Z4FubsnBFPsjvLHNRw"
        
        result = subprocess.run(
            test_cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        return result.returncode == 0
    except:
        return False

def wait_for_database():
    """Aguarda o banco ficar online"""
    print(f"⏳ Aguardando banco ficar online...")
    
    max_attempts = 30  # 5 minutos
    attempt = 0
    
    while attempt < max_attempts:
        if test_connection():
            print(f"✅ Banco online!")
            return True
        
        attempt += 1
        print(f"⏳ Tentativa {attempt}/{max_attempts} - Aguardando...")
        time.sleep(10)  # 10 segundos entre tentativas
    
    print(f"❌ Banco não ficou online após {max_attempts} tentativas")
    return False

def init_database():
    """Inicializa o banco com dados padrão"""
    print(f"🏗️  Inicializando banco...")
    
    try:
        # Ativar ambiente virtual e executar init_db.py
        init_cmd = [
            "bash", "-c", 
            "source venv/bin/activate && cd backend && python init_db.py"
        ]
        
        result = subprocess.run(
            init_cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            print(f"✅ Banco inicializado com sucesso!")
            print(f"📝 Log: {result.stdout}")
            return True
        else:
            print(f"❌ Erro ao inicializar banco:")
            print(f"📝 Erro: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False

def verify_tables():
    """Verifica se as tabelas foram criadas"""
    print(f"🔍 Verificando tabelas...")
    
    try:
        verify_cmd = [
            "psql",
            f"--host=dpg-d24vpfngi27c73bh06n0-a.oregon-postgres.render.com",
            f"--port=5432",
            f"--username=atendeai",
            f"--dbname=atendeai",
            "--command=SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';",
            "--no-password"
        ]
        
        env = os.environ.copy()
        env["PGPASSWORD"] = "2pjZBzhDlZY275Z4FubsnBFPsjvLHNRw"
        
        result = subprocess.run(
            verify_cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print(f"✅ Tabelas encontradas:")
            tables = result.stdout.strip().split('\n')[2:]  # Pular cabeçalho
            for table in tables:
                if table.strip():
                    print(f"  - {table.strip()}")
            return True
        else:
            print(f"❌ Erro ao verificar tabelas: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao verificar tabelas: {e}")
        return False

if __name__ == "__main__":
    print(f"🔄 Aguardando restart do banco no Render")
    print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"=" * 50)
    
    # Aguardar banco ficar online
    if wait_for_database():
        print(f"=" * 50)
        
        # Inicializar banco
        if init_database():
            print(f"=" * 50)
            # Verificar tabelas
            verify_tables()
            print(f"🎉 Banco pronto para uso!")
        else:
            print(f"💥 Falha ao inicializar banco")
            sys.exit(1)
    else:
        print(f"💥 Banco não ficou online")
        sys.exit(1) 