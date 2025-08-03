#!/usr/bin/env python3
"""
Script para executar testes unitários do projeto Atende Ai
"""

import subprocess
import sys
import os
from pathlib import Path

def run_tests(test_type="all", verbose=False):
    """
    Executa os testes unitários
    
    Args:
        test_type (str): Tipo de teste a executar
            - "all": Todos os testes
            - "admin": Testes do admin
            - "webhook": Testes de webhook
            - "api": Testes de API
            - "history": Testes de histórico
            - "integration": Testes de integração
        verbose (bool): Se deve executar em modo verboso
    """
    
    # Configurar comando base
    cmd = ["python", "-m", "pytest"]
    
    if verbose:
        cmd.append("-v")
    
    # Adicionar tipo específico de teste
    if test_type == "admin":
        cmd.extend(["-m", "admin"])
    elif test_type == "webhook":
        cmd.extend(["-m", "webhook"])
    elif test_type == "api":
        cmd.extend(["-m", "api"])
    elif test_type == "history":
        cmd.extend(["-m", "history"])
    elif test_type == "integration":
        cmd.extend(["-m", "integration"])
    elif test_type == "unit":
        cmd.extend(["-m", "unit"])
    elif test_type == "fast":
        cmd.extend(["-m", "not slow"])
    else:
        # Todos os testes
        pass
    
    # Adicionar diretório de testes
    cmd.append("tests/")
    
    print(f"Executando testes: {test_type}")
    print(f"Comando: {' '.join(cmd)}")
    print("-" * 50)
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print("\n" + "=" * 50)
        print("✅ Todos os testes passaram!")
        return True
    except subprocess.CalledProcessError as e:
        print("\n" + "=" * 50)
        print("❌ Alguns testes falharam!")
        return False

def run_coverage():
    """Executa testes com cobertura de código"""
    cmd = [
        "python", "-m", "pytest",
        "--cov=.",
        "--cov-report=html",
        "--cov-report=term-missing",
        "tests/"
    ]
    
    print("Executando testes com cobertura...")
    print(f"Comando: {' '.join(cmd)}")
    print("-" * 50)
    
    try:
        subprocess.run(cmd, check=True)
        print("\n" + "=" * 50)
        print("✅ Cobertura de testes gerada!")
        print("📊 Relatório HTML gerado em htmlcov/index.html")
        return True
    except subprocess.CalledProcessError as e:
        print("\n" + "=" * 50)
        print("❌ Erro ao gerar cobertura!")
        return False

def main():
    """Função principal"""
    if len(sys.argv) < 2:
        print("Uso: python run_tests.py [tipo_teste] [--verbose] [--coverage]")
        print("\nTipos de teste disponíveis:")
        print("  all         - Todos os testes")
        print("  admin       - Testes do painel administrativo")
        print("  webhook     - Testes de webhook e WhatsApp")
        print("  api         - Testes de integração com APIs")
        print("  history     - Testes de histórico de mensagens")
        print("  integration - Testes de integração completa")
        print("  unit        - Testes unitários")
        print("  fast        - Testes rápidos (exclui testes lentos)")
        print("\nOpções:")
        print("  --verbose   - Modo verboso")
        print("  --coverage  - Gerar relatório de cobertura")
        return
    
    test_type = sys.argv[1]
    verbose = "--verbose" in sys.argv
    coverage = "--coverage" in sys.argv
    
    if coverage:
        success = run_coverage()
    else:
        success = run_tests(test_type, verbose)
    
    if success:
        print("\n🎉 Testes executados com sucesso!")
        sys.exit(0)
    else:
        print("\n💥 Alguns testes falharam!")
        sys.exit(1)

if __name__ == "__main__":
    main() 