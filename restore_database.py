#!/usr/bin/env python3
"""
Script para restaurar backup do banco PostgreSQL no Render
Usa psql via subprocess para restaurar arquivo .sql
"""

import subprocess
import os
import sys
from datetime import datetime
from pathlib import Path

def restore_database(backup_file):
    """Restaura backup do banco PostgreSQL"""
    
    # Configurações do banco
    DB_HOST = "dpg-d24vpfngi27c73bh06n0-a.oregon-postgres.render.com"
    DB_PORT = "5432"
    DB_NAME = "atendeai"
    DB_USER = "atendeai"
    DB_PASSWORD = "2pjZBzhDlZY275Z4FubsnBFPsjvLHNRw"
    
    print(f"🔍 Iniciando restauração do banco PostgreSQL...")
    print(f"📊 Host: {DB_HOST}")
    print(f"🗄️  Database: {DB_NAME}")
    print(f"👤 User: {DB_USER}")
    print(f"📁 Arquivo de backup: {backup_file}")
    
    # Verificar se o arquivo existe
    if not os.path.exists(backup_file):
        print(f"❌ Erro: Arquivo {backup_file} não encontrado!")
        return False
    
    try:
        # Construir comando psql para restaurar
        psql_cmd = [
            "psql",
            f"--host={DB_HOST}",
            f"--port={DB_PORT}",
            f"--username={DB_USER}",
            f"--dbname={DB_NAME}",
            "--verbose",  # Mostra progresso
            "--no-password", # Não pede senha interativamente
            "--file", backup_file
        ]
        
        # Configurar variável de ambiente para senha
        env = os.environ.copy()
        env["PGPASSWORD"] = DB_PASSWORD
        
        print(f"🚀 Executando restauração...")
        print(f"⚠️  ATENÇÃO: Isso vai sobrescrever o banco atual!")
        
        # Perguntar confirmação
        confirm = input("🤔 Tem certeza que quer continuar? (sim/não): ").lower()
        if confirm not in ['sim', 's', 'yes', 'y']:
            print(f"❌ Restauração cancelada pelo usuário")
            return False
        
        # Executar psql
        result = subprocess.run(
            psql_cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=600  # 10 minutos de timeout
        )
        
        if result.returncode == 0:
            print(f"✅ Restauração concluída com sucesso!")
            print(f"📝 Log: {result.stdout}")
            return True
        else:
            print(f"❌ Erro na restauração:")
            print(f"🔍 Código de retorno: {result.returncode}")
            print(f"📝 Erro: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ Timeout: A restauração demorou mais de 10 minutos")
        return False
    except FileNotFoundError:
        print(f"❌ Erro: psql não encontrado. Certifique-se de que está instalado.")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False

def list_backup_files():
    """Lista arquivos de backup disponíveis"""
    backup_files = []
    for file in os.listdir('.'):
        if file.startswith('backup_atendeai_') and file.endswith('.sql'):
            backup_files.append(file)
    
    if backup_files:
        print(f"📁 Arquivos de backup encontrados:")
        for i, file in enumerate(sorted(backup_files, reverse=True), 1):
            size = os.path.getsize(file) / (1024 * 1024)
            print(f"  {i}. {file} ({size:.2f} MB)")
        return backup_files
    else:
        print(f"❌ Nenhum arquivo de backup encontrado no diretório atual")
        return []

def test_connection():
    """Testa a conectividade com o banco antes da restauração"""
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
            return True
        else:
            print(f"❌ Erro de conectividade:")
            print(f"📝 Erro: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao testar conectividade: {e}")
        return False

if __name__ == "__main__":
    print(f"🔄 Iniciando processo de restauração do Atende AI")
    print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"=" * 50)
    
    # Testar conectividade primeiro
    if not test_connection():
        print(f"💥 Não foi possível conectar ao banco. Verifique as configurações.")
        sys.exit(1)
    
    # Listar arquivos de backup
    backup_files = list_backup_files()
    
    if not backup_files:
        print(f"💥 Nenhum arquivo de backup encontrado!")
        sys.exit(1)
    
    # Perguntar qual arquivo usar
    if len(backup_files) == 1:
        backup_file = backup_files[0]
        print(f"📁 Usando arquivo: {backup_file}")
    else:
        print(f"🤔 Qual arquivo de backup você quer restaurar?")
        try:
            choice = int(input(f"Digite o número (1-{len(backup_files)}): ")) - 1
            if 0 <= choice < len(backup_files):
                backup_file = backup_files[choice]
            else:
                print(f"❌ Escolha inválida!")
                sys.exit(1)
        except ValueError:
            print(f"❌ Entrada inválida!")
            sys.exit(1)
    
    print(f"=" * 50)
    
    # Fazer restauração
    success = restore_database(backup_file)
    
    if success:
        print(f"🎉 Restauração finalizada com sucesso!")
        print(f"💡 O banco foi restaurado para o estado do backup")
    else:
        print(f"💥 Falha na restauração. Verifique os erros acima.")
        sys.exit(1) 