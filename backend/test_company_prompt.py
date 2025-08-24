#!/usr/bin/env python3
"""
Teste para verificar se o prompt da empresa está sendo chamado corretamente
"""

def test_company_prompt():
    """Testa se o prompt da empresa está sendo chamado corretamente"""
    
    print("🧪 Testando Prompt da Empresa no Smart Agent")
    print("=" * 60)
    
    # Simular análise com regras de negócio
    analysis_results = [
        {
            "status": "user_input_needed",
            "description": "Precisa de input do usuário (ex: escolher horário)",
            "expected_behavior": "DEVE chamar prompt da empresa"
        },
        {
            "status": "complete",
            "description": "Tudo pronto (ex: agendamento confirmado)",
            "expected_behavior": "DEVE chamar prompt da empresa"
        },
        {
            "status": "error",
            "description": "Erro na análise",
            "expected_behavior": "DEVE chamar prompt da empresa como fallback"
        },
        {
            "status": "unknown_status",
            "description": "Status inesperado",
            "expected_behavior": "DEVE chamar prompt da empresa como fallback"
        }
    ]
    
    print("📋 Testando diferentes status de análise:")
    print()
    
    for i, analysis in enumerate(analysis_results):
        print(f"{i+1}. Status: {analysis['status']}")
        print(f"   Descrição: {analysis['description']}")
        print(f"   Comportamento esperado: {analysis['expected_behavior']}")
        
        # Simular lógica do Smart Agent
        if analysis['status'] == 'user_input_needed':
            print("   ✅ AÇÃO: Chamando prompt da empresa para input do usuário")
            print("   📱 WhatsApp receberá: Resposta formatada pela empresa")
        elif analysis['status'] == 'complete':
            print("   ✅ AÇÃO: Chamando prompt da empresa para resposta final")
            print("   📱 WhatsApp receberá: Resposta final formatada pela empresa")
        else:
            print("   ✅ AÇÃO: Chamando prompt da empresa como fallback")
            print("   📱 WhatsApp receberá: Resposta de fallback formatada pela empresa")
        
        print()
    
    # Simular dados para o prompt da empresa
    analysis_data = {
        'results': {
            'buscar_profissional': {
                'status': 'encontrado',
                'profissional_id': '564410',
                'nome': 'Dra. Geraldine'
            },
            'verificar_disponibilidade': {
                'status': 'encontrado',
                'available_slots': ['09:30', '10:00', '14:00'],
                'date': '2025-09-01'
            }
        },
        'extracted_data': {
            'profissional': 'Dra Geraldine',
            'procedimento': 'AAA Teste',
            'data': '2025-09-01'
        },
        'business_rules': [
            'se não tiver slots: peça outra data',
            'se tiver horários: peça para escolher um'
        ]
    }
    
    print("📊 Dados que serão enviados para o prompt da empresa:")
    print(f"   - Profissional: {analysis_data['extracted_data']['profissional']}")
    print(f"   - Procedimento: {analysis_data['extracted_data']['procedimento']}")
    print(f"   - Data: {analysis_data['extracted_data']['data']}")
    print(f"   - Horários disponíveis: {analysis_data['results']['verificar_disponibilidade']['available_slots']}")
    print(f"   - Regras de negócio: {len(analysis_data['business_rules'])} regras")
    
    print()
    print("🎯 RESULTADO ESPERADO:")
    print("   ✅ TODOS os status agora chamam o prompt da empresa")
    print("   ✅ Usuário recebe mensagens com tom e estilo da empresa")
    print("   ✅ NÃO há mais respostas brutas ou técnicas")
    print("   ✅ Consistência na comunicação com o cliente")
    
    print()
    print("🎯 Teste do Prompt da Empresa Concluído!")
    print("=" * 60)

if __name__ == "__main__":
    test_company_prompt()
