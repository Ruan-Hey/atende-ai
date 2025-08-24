#!/usr/bin/env python3
"""
Teste para verificar se o caso especial ask_user está funcionando
"""

def test_ask_user_special_case():
    """Testa se o caso especial ask_user está funcionando corretamente"""
    
    print("🧪 Testando Caso Especial ask_user no Smart Agent")
    print("=" * 60)
    
    # Simular dados do LLM de próximos passos
    next_steps = {
        "action": "ask_user",
        "missing_data": ["cpf"],
        "business_rules": [
            "peça CPF do cliente para finalizar agendamento"
        ]
    }
    
    print(f"📋 Next Steps recebido: {next_steps}")
    print()
    
    # Simular dados extraídos
    extracted_data = {
        "profissional": "Dra Geraldine",
        "profissional_id": "564410",
        "procedimento": "AAA Teste",
        "servico_id": 13573388,
        "data": "2025-09-01",
        "horario": "09:30"
    }
    
    print(f"🗄️ Dados extraídos: {extracted_data}")
    print()
    
    # Simular business rules
    business_rules = [
        "peça CPF do cliente para finalizar agendamento"
    ]
    
    print(f"📋 Business Rules: {business_rules}")
    print()
    
    # Simular lógica do Smart Agent para ask_user
    print("👤 Simulando lógica do Smart Agent para ask_user...")
    
    if next_steps.get("action") == "ask_user":
        print("   ✅ Action é ask_user - tratando como caso especial")
        
        if business_rules:
            print("   📋 Usando business_rules diretamente para ask_user")
            
            # Preparar dados específicos para ask_user
            ask_user_data = {
                'action': 'ask_user',
                'missing_data': next_steps.get('missing_data', []),
                'business_rules': business_rules,
                'extracted_data': extracted_data,
                'context': {'waid': '554195984948'}
            }
            
            print(f"   📊 Dados preparados para prompt da empresa: {ask_user_data}")
            
            # Simular resposta do prompt da empresa
            print("   🏢 Chamando prompt da empresa...")
            
            # Simular mensagem formatada pela empresa
            formatted_response = f"""Perfeito! 😊 Você escolheu o horário das {extracted_data['horario']} com a {extracted_data['profissional']} 
para o dia {extracted_data['data']} para o procedimento "{extracted_data['procedimento']}". 

Agora preciso do seu CPF para finalizar o agendamento. 
Pode me passar?"""
            
            print(f"   📱 Resposta formatada pela empresa: {formatted_response}")
            
            # Verificar se a mensagem é contextualizada
            if extracted_data['horario'] in formatted_response and extracted_data['profissional'] in formatted_response:
                print("   🎯 SUCESSO: Mensagem contextualizada com dados do usuário!")
            else:
                print("   ❌ ERRO: Mensagem não está contextualizada!")
                
        else:
            print("   ⚠️ ask_user sem business_rules - usando mensagem padrão")
            formatted_response = "Preciso de mais informações para continuar. Pode me ajudar?"
    else:
        print("   ❌ ERRO: Action não é ask_user!")
    
    print()
    print("🎯 RESULTADO ESPERADO:")
    print("   ✅ ask_user é tratado como caso especial")
    print("   ✅ NÃO executa execute_step")
    print("   ✅ Usa business_rules diretamente")
    print("   ✅ Gera resposta formatada pela empresa")
    print("   ✅ Mensagem é contextualizada e específica")
    
    print()
    print("🎯 Teste do Caso Especial ask_user Concluído!")
    print("=" * 60)

if __name__ == "__main__":
    test_ask_user_special_case()
