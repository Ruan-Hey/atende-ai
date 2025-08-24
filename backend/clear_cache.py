#!/usr/bin/env python3
"""
Script para limpar o cache do SmartAgent
"""

import sys
import os

# Adicionar o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from agents.smart_agent import SmartAgent
    
    # Verificar se o cache existe
    if hasattr(SmartAgent, '_conversation_cache'):
        cache_size = len(SmartAgent._conversation_cache)
        SmartAgent._conversation_cache.clear()
        print(f"✅ Cache limpo com sucesso!")
        print(f"📊 {cache_size} conversas foram removidas")
    else:
        print("ℹ️ Cache não existe ainda (nenhuma conversa foi iniciada)")
    
except Exception as e:
    print(f"❌ Erro ao limpar cache: {e}")
    print("💡 Certifique-se de que o backend não está rodando")
