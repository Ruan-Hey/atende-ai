#!/usr/bin/env python3
"""
Teste simples para verificar horários do Google Calendar
"""

import os
import sys
from datetime import datetime, timedelta

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_calendar_config():
    """Testa a configuração do Google Calendar"""
    
    print("🔍 Testando configuração do Google Calendar...")
    
    # Verificar variáveis de ambiente
    env_vars = [
        'GOOGLE_CALENDAR_CLIENT_ID',
        'GOOGLE_CALENDAR_CLIENT_SECRET', 
        'GOOGLE_CALENDAR_REFRESH_TOKEN',
        'GOOGLE_CALENDAR_SERVICE_ACCOUNT',
        'GOOGLE_CALENDAR_PROJECT_ID',
        'GOOGLE_CALENDAR_CLIENT_EMAIL'
    ]
    
    print("\n📋 Variáveis de ambiente:")
    for var in env_vars:
        value = os.getenv(var)
        status = "✅ Configurado" if value else "❌ Não configurado"
        print(f"  {var}: {status}")
        if value and len(value) > 20:
            print(f"    Valor: {value[:20]}...")
        elif value:
            print(f"    Valor: {value}")
    
    # Testar data específica
    test_date = "2025-08-11"
    print(f"\n📅 Data de teste: {test_date}")
    
    # Simular horários padrão
    print("\n🕐 Horários padrão disponíveis (simulação):")
    default_hours = [
        "09:00", "10:00", "11:00", "12:00", 
        "13:00", "14:00", "15:00", "16:00", "17:00"
    ]
    
    for i, hour in enumerate(default_hours, 1):
        print(f"  {i}. {hour}")
    
    print(f"\n📊 Total de horários padrão: {len(default_hours)}")
    
    # Verificar se há arquivo de credenciais
    cred_files = [
        'credentials.json',
        'service-account.json',
        'google-credentials.json'
    ]
    
    print("\n🔐 Arquivos de credenciais:")
    for file in cred_files:
        if os.path.exists(file):
            print(f"  ✅ {file} - Encontrado")
        else:
            print(f"  ❌ {file} - Não encontrado")
    
    print("\n💡 Para testar com dados reais:")
    print("  1. Configure as variáveis de ambiente do Google Calendar")
    print("  2. Ou adicione um arquivo credentials.json")
    print("  3. Execute: python test_calendar_slots.py")

if __name__ == "__main__":
    test_calendar_config() 