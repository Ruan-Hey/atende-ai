#!/usr/bin/env python3
"""
Script para aplicar tracking automático nos módulos principais
"""

import sys
import os
import importlib

# Adicionar o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from code_tracker import apply_tracking_to_module

def apply_tracking_to_main_modules():
    """Aplica tracking nos módulos principais"""
    
    modules_to_track = [
        'agents.smart_agent',
        'rules.trinks_rules',
        'rules.google_calendar_rules',
        'rules.google_sheets_rules',
        'tools.trinks_intelligent_tools',
        'tools.calendar_tools',
        'tools.cliente_tools',
        'services.services',
        'integrations.twilio_service',
        'integrations.openai_service'
    ]
    
    print("🚀 Aplicando tracking automático nos módulos...")
    
    for module_name in modules_to_track:
        try:
            # Importa o módulo
            module = importlib.import_module(module_name)
            
            # Aplica tracking
            apply_tracking_to_module(module_name, module)
            
            print(f"✅ Tracking aplicado em: {module_name}")
            
        except ImportError as e:
            print(f"⚠️ Módulo não encontrado: {module_name} ({e})")
        except Exception as e:
            print(f"❌ Erro ao aplicar tracking em {module_name}: {e}")
    
    print("\n🎯 Tracking aplicado com sucesso!")
    print("📊 Agora todas as funções executadas serão rastreadas automaticamente")
    print("🌐 Acesse /api/admin/code-usage para ver o relatório")

if __name__ == "__main__":
    apply_tracking_to_main_modules()
