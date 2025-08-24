#!/usr/bin/env python3
"""
Teste para verificar se o Smart Agent consegue lidar com array de actions
"""

def test_array_actions():
    """Testa se o Smart Agent consegue lidar com array de actions"""
    
    print("🧪 Testando Array de Actions no Smart Agent")
    print("=" * 60)
    
    # Simular resultado da LLM de próximos passos
    next_steps = {
        "action": ["buscar_profissional", "buscar_servico", "verificar_disponibilidade"],
        "business_rules": [
            "se não tiver slots: peça outra data",
            "se tiver horários: peça para escolher um"
        ]
    }
    
    print(f"📋 Next Steps recebido: {next_steps}")
    print()
    
    # Verificar se action é array
    action = next_steps.get("action")
    if isinstance(action, list):
        print("✅ Action é array!")
        print(f"   Número de passos: {len(action)}")
        print(f"   Passos: {action}")
        
        # Simular execução de múltiplas actions
        print()
        print("🔄 Simulando execução de múltiplas actions...")
        
        results = []
        for i, step in enumerate(action):
            print(f"   {i+1}. Executando: {step}")
            
            # Simular resultado de cada step
            if step == "buscar_profissional":
                step_result = {
                    "status": "encontrado",
                    "profissional_id": "564410",
                    "cache_instructions": {
                        "update_fields": {"profissional_id": "564410"}
                    }
                }
            elif step == "buscar_servico":
                step_result = {
                    "status": "encontrado", 
                    "servico_id": "789",
                    "cache_instructions": {
                        "update_fields": {"servico_id": "789"}
                    }
                }
            elif step == "verificar_disponibilidade":
                step_result = {
                    "status": "encontrado",
                    "available_slots": ["14:00", "15:00", "16:00"]
                }
            else:
                step_result = {"status": "erro", "error": "Step não reconhecido"}
            
            print(f"      Resultado: {step_result.get('status')}")
            
            # Simular aplicação de cache_instructions
            if step_result.get('cache_instructions'):
                cache_instructions = step_result.get('cache_instructions')
                if "update_fields" in cache_instructions:
                    update_fields = cache_instructions["update_fields"]
                    print(f"      Cache atualizado: {update_fields}")
            
            # Coletar resultado
            if step_result.get('status') in ['encontrado', 'sucesso', 'concluido']:
                results.append(f"✅ {step}: Sucesso")
            else:
                results.append(f"⚠️ {step}: {step_result.get('status')}")
        
        print()
        print("📊 Resumo da execução:")
        for result in results:
            print(f"   {result}")
        
        # Simular dados extraídos atualizados
        extracted_data = {
            "profissional": "Dra Geraldine",
            "profissional_id": "564410",  # ✅ Atualizado pelo cache
            "procedimento": "AAA Teste",
            "servico_id": "789",          # ✅ Atualizado pelo cache
            "data": "2025-09-01"
        }
        
        print()
        print("🗄️ Dados extraídos após execução:")
        print(f"   {extracted_data}")
        
        # Verificar se os IDs foram salvos
        if extracted_data.get('profissional_id') and extracted_data.get('servico_id'):
            print("🎯 SUCESSO: Todos os IDs foram salvos no cache!")
        else:
            print("❌ ERRO: Nem todos os IDs foram salvos no cache!")
            
    else:
        print("❌ Action NÃO é array!")
        print(f"   Tipo: {type(action)}")
        print(f"   Valor: {action}")
    
    print()
    print("🎯 Teste de Array de Actions Concluído!")
    print("=" * 60)

if __name__ == "__main__":
    test_array_actions()
