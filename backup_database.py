#!/usr/bin/env python3
"""
Script para fazer backup completo do banco PostgreSQL no Render
Usa pg_dump via subprocess para gerar arquivo .sql
"""

import subprocess
import os
import sys
from datetime import datetime
from pathlib import Path

def backup_database():
    """Faz backup completo do banco PostgreSQL"""
    
    # Configurações do banco (você pode alterar aqui ou usar variáveis de ambiente)
    DB_HOST = "dpg-d24vpfngi27c73bh06n0-a.oregon-postgres.render.com"
    DB_PORT = "5432"
    DB_NAME = "atendeai"
    DB_USER = "atendeai"
    DB_PASSWORD = "2pjZBzhDlZY275Z4FubsnBFPsjvLHNRw"
    
    # Nome do arquivo de backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"backup_atendeai_{timestamp}.sql"
    
    print(f"🔍 Iniciando backup do banco PostgreSQL...")
    print(f"📊 Host: {DB_HOST}")
    print(f"🗄️  Database: {DB_NAME}")
    print(f"👤 User: {DB_USER}")
    print(f"💾 Arquivo de backup: {backup_filename}")
    
    try:
        # Construir comando pg_dump
        pg_dump_cmd = [
            "pg_dump",
            f"--host={DB_HOST}",
            f"--port={DB_PORT}",
            f"--username={DB_USER}",
            f"--dbname={DB_NAME}",
            "--verbose",  # Mostra progresso
            "--clean",    # Inclui comandos DROP
            "--create",   # Inclui comandos CREATE
            "--if-exists", # Usa IF EXISTS nos DROPs
            "--no-password", # Não pede senha interativamente
            "--file", backup_filename
        ]
        
        # Configurar variável de ambiente para senha
        env = os.environ.copy()
        env["PGPASSWORD"] = DB_PASSWORD
        
        print(f"🚀 Executando pg_dump...")
        print(f"📝 Comando: {' '.join(pg_dump_cmd[:-2])} --file {backup_filename}")
        
        # Executar pg_dump
        result = subprocess.run(
            pg_dump_cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutos de timeout
        )
        
        if result.returncode == 0:
            print(f"✅ Backup concluído com sucesso!")
            print(f"📁 Arquivo salvo: {backup_filename}")
            
            # Verificar tamanho do arquivo
            if os.path.exists(backup_filename):
                size = os.path.getsize(backup_filename)
                size_mb = size / (1024 * 1024)
                print(f"📏 Tamanho do arquivo: {size_mb:.2f} MB")
            
            return True
        else:
            print(f"❌ Erro no backup:")
            print(f"🔍 Código de retorno: {result.returncode}")
            print(f"📝 Erro: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ Timeout: O backup demorou mais de 5 minutos")
        return False
    except FileNotFoundError:
        print(f"❌ Erro: pg_dump não encontrado. Certifique-se de que está instalado.")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False

def test_connection():
    """Testa a conectividade com o banco antes do backup"""
    print(f"🔍 Testando conectividade com o banco...")
    
    try:
        # Comando simples para testar conexão
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
            print(f"📊 Versão do PostgreSQL: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Erro de conectividade:")
            print(f"📝 Erro: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao testar conectividade: {e}")
        return False

if __name__ == "__main__":
    print(f"🔄 Iniciando processo de backup do Atende AI")
    print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"=" * 50)
    
    # Testar conectividade primeiro
    if test_connection():
        print(f"=" * 50)
        # Fazer backup
        success = backup_database()
        
        if success:
            print(f"🎉 Backup finalizado com sucesso!")
            print(f"💡 Você pode usar o arquivo .sql para restaurar o banco se necessário")
        else:
            print(f"💥 Falha no backup. Verifique os erros acima.")
            sys.exit(1)
    else:
        print(f"💥 Não foi possível conectar ao banco. Verifique as configurações.")
        sys.exit(1) 