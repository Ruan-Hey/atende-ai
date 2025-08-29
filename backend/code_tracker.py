#!/usr/bin/env python3
"""
Sistema de tracking automático para identificar código utilizado
"""

import types
import logging
from typing import Set, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class CodeTracker:
    """Rastreador automático de execução de código"""
    
    def __init__(self):
        self.execution_tracker = {
            'functions_called': set(),
            'total_calls': 0,
            'modules_tracked': set(),
            'start_time': datetime.now()
        }
    
    def track_function(self, func, name: str):
        """Decorator que adiciona tracking a uma função"""
        def wrapper(*args, **kwargs):
            # Adiciona tracking
            self.execution_tracker['functions_called'].add(name)
            self.execution_tracker['total_calls'] += 1
            
            # Log da execução
            logger.debug(f"🚀 EXECUTANDO: {name}")
            
            # Executa a função original
            return func(*args, **kwargs)
        return wrapper
    
    def apply_tracking_to_module(self, module_name: str, module):
        """Aplica tracking automático a todas as funções de um módulo"""
        try:
            tracked_count = 0
            for name in dir(module):
                obj = getattr(module, name)
                if callable(obj) and not name.startswith('_'):
                    # Substitui a função por versão com tracking
                    setattr(module, name, self.track_function(obj, f"{module_name}.{name}"))
                    tracked_count += 1
            
            self.execution_tracker['modules_tracked'].add(module_name)
            logger.info(f"✅ Tracking aplicado em {module_name}: {tracked_count} funções")
            
        except Exception as e:
            logger.error(f"❌ Erro ao aplicar tracking em {module_name}: {e}")
    
    def get_usage_report(self) -> Dict[str, Any]:
        """Gera relatório completo de uso de código"""
        return {
            "executed_functions": sorted(list(self.execution_tracker['functions_called'])),
            "total_executions": self.execution_tracker['total_calls'],
            "modules_tracked": sorted(list(self.execution_tracker['modules_tracked'])),
            "start_time": self.execution_tracker['start_time'].isoformat(),
            "uptime": str(datetime.now() - self.execution_tracker['start_time'])
        }
    
    def save_report_to_file(self, filename: str = "code_usage_report.txt"):
        """Salva relatório em arquivo"""
        try:
            report = self.get_usage_report()
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("RELATÓRIO DE USO DE CÓDIGO\n")
                f.write("=" * 50 + "\n")
                f.write(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
                f.write(f"Tempo de execução: {report['uptime']}\n")
                f.write(f"Total de execuções: {report['total_executions']}\n")
                f.write(f"Módulos rastreados: {len(report['modules_tracked'])}\n")
                f.write(f"Funções executadas: {len(report['executed_functions'])}\n")
                
                f.write("\n🚀 FUNÇÕES EXECUTADAS:\n")
                for func in report['executed_functions']:
                    f.write(f"  - {func}\n")
                
                f.write(f"\n📊 MÓDULOS RASTREADOS:\n")
                for module in report['modules_tracked']:
                    f.write(f"  - {module}\n")
            
            logger.info(f"📄 Relatório salvo em: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar relatório: {e}")
            return False

# Instância global do tracker
code_tracker = CodeTracker()

def apply_tracking_to_module(module_name: str, module):
    """Função helper para aplicar tracking"""
    code_tracker.apply_tracking_to_module(module_name, module)

def get_code_usage():
    """Função helper para obter relatório"""
    return code_tracker.get_usage_report()

def save_usage_report(filename: str = "code_usage_report.txt"):
    """Função helper para salvar relatório"""
    return code_tracker.save_report_to_file(filename)
