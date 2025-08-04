#!/usr/bin/env python3
"""
Script para reset completo do banco PostgreSQL
Recria apenas as tabelas essenciais sem dados problemáticos
"""

import subprocess
import os
import sys
from datetime import datetime

def complete_reset():
    """Faz reset completo do banco"""
    
    print(f"🔄 Iniciando reset COMPLETO do banco...")
    print(f"⚠️  ATENÇÃO: Isso vai APAGAR TUDO e recriar do zero!")
    
    # Perguntar confirmação
    confirm = input("🤔 Tem certeza que quer APAGAR TUDO? (sim/não): ").lower()
    if confirm not in ['sim', 's', 'yes', 'y']:
        print(f"❌ Reset cancelado pelo usuário")
        return False
    
    try:
        # 1. Dropar completamente o schema public
        print(f"🗑️  Removendo TUDO do banco...")
        
        drop_cmd = [
            "psql",
            f"--host=dpg-d24vpfngi27c73bh06n0-a.oregon-postgres.render.com",
            f"--port=5432",
            f"--username=atendeai",
            f"--dbname=atendeai",
            "--no-password",
            "--command=DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO atendeai;"
        ]
        
        env = os.environ.copy()
        env["PGPASSWORD"] = "2pjZBzhDlZY275Z4FubsnBFPsjvLHNRw"
        
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
        
        print(f"✅ Banco completamente limpo!")
        
        # 2. Recriar tabelas usando SQLAlchemy
        print(f"🏗️  Recriando tabelas essenciais...")
        
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
        print(f"❌ Erro: psql não encontrado.")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False

def verify_clean_state():
    """Verifica se o banco está limpo e funcional"""
    print(f"🔍 Verificando estado do banco...")
    
    try:
        # Testar consulta simples
        test_cmd = [
            "psql",
            f"--host=dpg-d24vpfngi27c73bh06n0-a.oregon-postgres.render.com",
            f"--port=5432",
            f"--username=atendeai",
            f"--dbname=atendeai",
            "--command=SELECT COUNT(*) FROM empresas;",
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
            print(f"✅ Banco funcionando!")
            print(f"📊 Empresas: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Banco ainda com problemas: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao verificar banco: {e}")
        return False

if __name__ == "__main__":
    print(f"🔄 RESET COMPLETO DO BANCO ATENDE AI")
    print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"=" * 50)
    
    # Fazer reset completo
    success = complete_reset()
    
    if success:
        print(f"=" * 50)
        # Verificar estado
        verify_clean_state()
        print(f"🎉 RESET COMPLETO FINALIZADO!")
        print(f"💡 Banco recriado do zero com apenas o essencial")
    else:
        print(f"💥 Falha no reset completo. Verifique os erros acima.")
        sys.exit(1) 