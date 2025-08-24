#!/usr/bin/env python3
"""
Teste da Nova Arquitetura com Regras de Negócio
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rules.trinks_rules import TrinksRules
from agents.smart_agent import SmartAgent

def test_new_architecture():
    """Testa a nova arquitetura com regras de negócio"""
    
    print("🧪 Testando Nova Arquitetura com Regras de Negócio")
    print("=" * 60)
    
    # Configuração de teste
    empresa_config = {
        'openai_config': {
            'openai_key': 'test-key'  # Será substituída pela real
        },
        'nome': 'Clínica Teste',
        'trinks_enabled': True
    }
    
    # 1. Testar LLM de Próximos Passos com Regras de Negócio
    print("\n1️⃣ Testando LLM de Próximos Passos...")
    try:
        rules = TrinksRules()
        
        # Contexto de teste
        context = {
            'previous_data': {},
            'extracted_data': {
                'procedimento': 'enzimas',
                'profissional': 'Dra. Maria',
                'data': 'amanhã'
            },
            'conversation_history': []
        }
        
        # Testar decisão de próximos passos
        next_steps = rules.decide_next_steps('verificar_disponibilidade', context, empresa_config)
        
        print(f"✅ Próximos passos decididos:")
        print(f"   Action: {next_steps.get('action')}")
        print(f"   Business Rules: {next_steps.get('business_rules', [])}")
        
    except Exception as e:
        print(f"❌ Erro ao testar próximos passos: {e}")
    
    # 2. Testar SmartAgent com Regras de Negócio
    print("\n2️⃣ Testando SmartAgent com Regras de Negócio...")
    try:
        # Simular contexto com regras de negócio
        context_with_rules = {
            'waid': 'test-123',
            'business_rules': [
                'se não tiver slots e vier vazio: peça outra data',
                'se tiver horários: peça para escolher um'
            ],
            'extracted_data': {
                'procedimento': 'enzimas',
                'profissional': 'Dra. Maria',
                'data': 'amanhã'
            }
        }
        
        # Simular resultados de tools
        tool_results = {
            'buscar_servico': {
                'status': 'encontrado',
                'id': 123,
                'nome': 'enzimas'
            },
            'buscar_profissional': {
                'status': 'encontrado',
                'id': 456,
                'nome': 'Dra. Maria'
            },
            'verificar_disponibilidade': {
                'status': 'sucesso',
                'horarios': []  # Vazio - deve acionar regra de negócio
            }
        }
        
        print(f"✅ Contexto com regras: {context_with_rules.get('business_rules')}")
        print(f"✅ Resultados das tools: {list(tool_results.keys())}")
        
        # Testar análise com regras de negócio
        agent = SmartAgent(empresa_config)
        analysis = agent._analyze_tool_results_with_business_rules(
            tool_results, 
            context_with_rules['business_rules'], 
            context_with_rules
        )
        
        print(f"✅ Análise com regras de negócio:")
        print(f"   Status: {analysis.get('status')}")
        print(f"   Next Action: {analysis.get('next_action')}")
        print(f"   User Message: {analysis.get('user_message')}")
        print(f"   Reasoning: {analysis.get('reasoning')}")
        
    except Exception as e:
        print(f"❌ Erro ao testar SmartAgent: {e}")
    
    print("\n🎯 Teste da Nova Arquitetura Concluído!")
    print("=" * 60)

if __name__ == "__main__":
    test_new_architecture()
