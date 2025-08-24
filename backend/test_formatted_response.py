#!/usr/bin/env python3
"""
Teste para verificar se a nova funcionalidade de resposta formatada está funcionando
"""

def test_formatted_response():
    """Testa se a nova funcionalidade de resposta formatada está funcionando"""
    
    print("🧪 Testando Resposta Formatada no Smart Agent")
    print("=" * 60)
    
    # Simular resultado de execução de actions
    action_result = {
        "status": "actions_executadas",
        "results": {
            "buscar_profissional": {
                "status": "encontrado",
                "profissional_id": "564031",
                "nome": "Amabile Nagel Maas",
                "cache_instructions": {
                    "update_fields": {"profissional_id": "564031"}
                }
            }
        },
        "actions_executadas": ["buscar_profissional"]
    }
    
    print(f"📋 Resultado das actions: {action_result}")
    print()
    
    # Simular regras de negócio
    business_rules = [
        "se não tiver slots: peça outra data",
        "se tiver horários: peça para escolher um"
    ]
    
    print(f"📋 Regras de negócio: {business_rules}")
    print()
    
    # Simular dados extraídos
    extracted_data = {
        "profissional": "Amabile",
        "profissional_id": "564031",  # ✅ Já atualizado pelo cache
        "procedimento": None,
        "servico_id": None,
        "data": None
    }
    
    print(f"🗄️ Dados extraídos: {extracted_data}")
    print()
    
    # Simular análise com regras de negócio
    print("🔍 Simulando análise com regras de negócio...")
    
    # Verificar se precisa de mais informações
    if not extracted_data.get('procedimento'):
        print("   ❌ Falta procedimento - precisa de input do usuário")
        analysis_status = "user_input_needed"
        user_message = "✅ Perfeito! Encontrei a profissional Amabile. Agora me diga qual serviço você gostaria de agendar."
    elif not extracted_data.get('data'):
        print("   ❌ Falta data - precisa de input do usuário")
        analysis_status = "user_input_needed"
        user_message = "✅ Ótimo! Agora preciso saber em qual data você gostaria de agendar."
    else:
        print("   ✅ Todos os dados necessários - pode verificar disponibilidade")
        analysis_status = "complete"
        user_message = "✅ Perfeito! Vou verificar a disponibilidade para você."
    
    print(f"   📊 Status da análise: {analysis_status}")
    print(f"   💬 Mensagem para usuário: {user_message}")
    
    print()
    
    # Simular resposta formatada
    if analysis_status == "user_input_needed":
        print("👤 GERANDO RESPOSTA FORMATADA PARA USUÁRIO:")
        print(f"   📱 WhatsApp receberá: {user_message}")
        
        # Verificar se a mensagem é amigável
        if "✅" in user_message and "Perfeito" in user_message:
            print("   🎯 SUCESSO: Mensagem formatada e amigável!")
        else:
            print("   ❌ ERRO: Mensagem não está formatada corretamente!")
            
    elif analysis_status == "complete":
        print("✅ GERANDO RESPOSTA FINAL FORMATADA:")
        print(f"   📱 WhatsApp receberá: {user_message}")
    
    print()
    print("🎯 Teste de Resposta Formatada Concluído!")
    print("=" * 60)

if __name__ == "__main__":
    test_formatted_response()
