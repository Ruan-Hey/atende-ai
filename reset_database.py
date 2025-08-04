#!/usr/bin/env python3
"""
Script para resetar completamente o banco PostgreSQL no Render
Recria todas as tabelas e dados iniciais
"""

import subprocess
import os
import sys
from datetime import datetime

def reset_database():
    """Reseta completamente o banco de dados"""
    
    # Configurações do banco
    DB_HOST = "dpg-d24vpfngi27c73bh06n0-a.oregon-postgres.render.com"
    DB_PORT = "5432"
    DB_NAME = "atendeai"
    DB_USER = "atendeai"
    DB_PASSWORD = "2pjZBzhDlZY275Z4FubsnBFPsjvLHNRw"
    
    print(f"🔄 Iniciando reset completo do banco PostgreSQL...")
    print(f"📊 Host: {DB_HOST}")
    print(f"🗄️  Database: {DB_NAME}")
    print(f"👤 User: {DB_USER}")
    print(f"⚠️  ATENÇÃO: Isso vai APAGAR todos os dados!")
    
    # Perguntar confirmação
    confirm = input("🤔 Tem certeza que quer APAGAR todos os dados? (sim/não): ").lower()
    if confirm not in ['sim', 's', 'yes', 'y']:
        print(f"❌ Reset cancelado pelo usuário")
        return False
    
    try:
        # 1. Conectar e dropar todas as tabelas
        print(f"🗑️  Removendo todas as tabelas...")
        
        drop_cmd = [
            "psql",
            f"--host={DB_HOST}",
            f"--port={DB_PORT}",
            f"--username={DB_USER}",
            f"--dbname={DB_NAME}",
            "--no-password",
            "--command=DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
        ]
        
        env = os.environ.copy()
        env["PGPASSWORD"] = DB_PASSWORD
        
        result = subprocess.run(
            drop_cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            print(f"❌ Erro ao limpar banco: {result.stderr}")
            return False
        
        print(f"✅ Banco limpo com sucesso!")
        
        # 2. Recriar tabelas usando o script de inicialização
        print(f"🏗️  Recriando tabelas...")
        
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
            print(f"✅ Tabelas recriadas com sucesso!")
            print(f"📝 Log: {result.stdout}")
            return True
        else:
            print(f"❌ Erro ao recriar tabelas:")
            print(f"📝 Erro: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ Timeout: O reset demorou muito")
        return False
    except FileNotFoundError:
        print(f"❌ Erro: psql não encontrado. Certifique-se de que está instalado.")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False

def test_connection():
    """Testa a conectividade com o banco"""
    print(f"🔍 Testando conectividade com o banco...")
    
    try:
        test_cmd = [
            "psql",
            f"--host=dpg-d24vpfngi27c73bh06n0-a.oregon-postgres.render.com",
            f"--port=5432",
            f"--username=atendeai",
            f"--dbname=atendeai",
            "--command=SELECT version();",
            "--no-password"
        ]
        
        env = os.environ.copy()
        env["PGPASSWORD"] = "2pjZBzhDlZY275Z4FubsnBFPsjvLHNRw"
        
        result = subprocess.run(
            test_cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print(f"✅ Conectividade OK")
            return True
        else:
            print(f"❌ Erro de conectividade:")
            print(f"📝 Erro: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao testar conectividade: {e}")
        return False

def verify_tables():
    """Verifica se as tabelas foram criadas corretamente"""
    print(f"🔍 Verificando tabelas criadas...")
    
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
    print(f"🔄 Iniciando reset completo do banco Atende AI")
    print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"=" * 50)
    
    # Testar conectividade primeiro
    if not test_connection():
        print(f"💥 Não foi possível conectar ao banco. Verifique as configurações.")
        sys.exit(1)
    
    print(f"=" * 50)
    
    # Fazer reset
    success = reset_database()
    
    if success:
        print(f"=" * 50)
        # Verificar tabelas
        verify_tables()
        print(f"🎉 Reset finalizado com sucesso!")
        print(f"💡 O banco foi recriado do zero com dados iniciais")
    else:
        print(f"💥 Falha no reset. Verifique os erros acima.")
        sys.exit(1) 