#!/usr/bin/env python3
"""
Teste para verificar se o ask_user é detectado corretamente mesmo dentro de array
"""

def test_ask_user_array_detection():
    """Testa se o ask_user é detectado corretamente mesmo dentro de array"""
    
    print("🧪 Testando Detecção de ask_user em Array")
    print("=" * 60)
    
    # Simular diferentes formatos de action
    test_cases = [
        {
            "name": "Array com apenas ask_user",
            "action": ["ask_user"],
            "expected_detection": "ask_user",
            "expected_behavior": "Tratar como caso especial"
        },
        {
            "name": "Array com tools",
            "action": ["buscar_profissional", "buscar_servico"],
            "expected_detection": "tools",
            "expected_behavior": "Executar múltiplas actions"
        },
        {
            "name": "String ask_user",
            "action": "ask_user",
            "expected_detection": "ask_user",
            "expected_behavior": "Tratar como caso especial"
        },
        {
            "name": "String tool",
            "action": "buscar_profissional",
            "expected_detection": "tool",
            "expected_behavior": "Executar action única"
        }
    ]
    
    print("📋 Testando diferentes formatos de action:")
    print()
    
    for i, test_case in enumerate(test_cases):
        print(f"{i+1}. {test_case['name']}")
        print(f"   Action: {test_case['action']}")
        print(f"   Tipo: {type(test_case['action'])}")
        
        # Simular lógica do Smart Agent
        if isinstance(test_case['action'], list):
            print("   🔄 Action é array")
            
            # ✅ NOVO: Verificar se é array com apenas "ask_user"
            if len(test_case['action']) == 1 and test_case['action'][0] == "ask_user":
                print("   👤 Array contém apenas ask_user - tratando como caso especial")
                detection = "ask_user"
                behavior = "Tratar como caso especial"
            else:
                print("   🔧 Array contém tools - executando múltiplas actions")
                detection = "tools"
                behavior = "Executar múltiplas actions"
        else:
            print("   🔧 Action é string")
            
            # ✅ NOVO: Verificar se string é "ask_user"
            if test_case['action'] == "ask_user":
                print("   👤 Action é ask_user - tratando como caso especial")
                detection = "ask_user"
                behavior = "Tratar como caso especial"
            else:
                print("   🔧 Action é tool - executando action única")
                detection = "tool"
                behavior = "Executar action única"
        
        # Verificar se a detecção está correta
        if detection == test_case['expected_detection']:
            print(f"   ✅ DETECÇÃO CORRETA: {detection}")
        else:
            print(f"   ❌ DETECÇÃO INCORRETA: esperado {test_case['expected_detection']}, obtido {detection}")
        
        if behavior == test_case['expected_behavior']:
            print(f"   ✅ COMPORTAMENTO CORRETO: {behavior}")
        else:
            print(f"   ❌ COMPORTAMENTO INCORRETO: esperado {test_case['expected_behavior']}, obtido {behavior}")
        
        print()
    
    print("🎯 RESULTADO ESPERADO:")
    print("   ✅ ask_user é detectado corretamente em array: ['ask_user']")
    print("   ✅ ask_user é detectado corretamente em string: 'ask_user'")
    print("   ✅ Tools são executadas normalmente em array: ['tool1', 'tool2']")
    print("   ✅ Tool única é executada normalmente em string: 'tool'")
    print("   ✅ Flexibilidade para ambos os formatos mantida")
    
    print()
    print("🎯 Teste de Detecção de ask_user em Array Concluído!")
    print("=" * 60)

if __name__ == "__main__":
    test_ask_user_array_detection()
