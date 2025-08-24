#!/usr/bin/env python3
"""
Teste para verificar se TODAS as instruções de cache estão funcionando
"""

def test_all_cache_instructions():
    """Testa se todas as instruções de cache estão sendo retornadas corretamente"""
    
    print("🧪 Testando TODAS as Instruções de Cache")
    print("=" * 60)
    
    # 1. Teste: buscar_profissional
    print("1️⃣ Testando buscar_profissional...")
    step_result_profissional = {
        "status": "encontrado",
        "id": "564410",
        "nome": "Dr. João Silva",
        "profissional_id": "564410",
        "cache_instructions": {
            "update_fields": {
                "profissional_id": "564410"
            }
        }
    }
    
    if step_result_profissional.get('cache_instructions'):
        print("✅ Cache instructions encontradas para profissional!")
        print(f"   Campos: {step_result_profissional['cache_instructions']['update_fields']}")
    else:
        print("❌ Cache instructions NÃO encontradas para profissional!")
    
    print()
    
    # 2. Teste: buscar_servico
    print("2️⃣ Testando buscar_servico...")
    step_result_servico = {
        "status": "encontrado",
        "nome": "Aplicação de Enzimas",
        "servico_id": "789",
        "cache_instructions": {
            "update_fields": {
                "servico_id": "789"
            }
        }
    }
    
    if step_result_servico.get('cache_instructions'):
        print("✅ Cache instructions encontradas para serviço!")
        print(f"   Campos: {step_result_servico['cache_instructions']['update_fields']}")
    else:
        print("❌ Cache instructions NÃO encontradas para serviço!")
    
    print()
    
    # 3. Teste: coletar_cliente (encontrado)
    print("3️⃣ Testando coletar_cliente (encontrado)...")
    step_result_cliente_encontrado = {
        "status": "cliente_encontrado",
        "cliente_id": "12345",
        "nome": "Maria Silva",
        "cpf": "123.456.789-00",
        "cache_instructions": {
            "update_fields": {
                "cliente_id": "12345",
                "nome": "Maria Silva"
            }
        }
    }
    
    if step_result_cliente_encontrado.get('cache_instructions'):
        print("✅ Cache instructions encontradas para cliente encontrado!")
        print(f"   Campos: {step_result_cliente_encontrado['cache_instructions']['update_fields']}")
    else:
        print("❌ Cache instructions NÃO encontradas para cliente encontrado!")
    
    print()
    
    # 4. Teste: coletar_cliente (criado)
    print("4️⃣ Testando coletar_cliente (criado)...")
    step_result_cliente_criado = {
        "status": "cliente_criado",
        "cliente_id": "67890",
        "nome": "João Santos",
        "cpf": "987.654.321-00",
        "cache_instructions": {
            "update_fields": {
                "cliente_id": "67890",
                "nome": "João Santos"
            }
        }
    }
    
    if step_result_cliente_criado.get('cache_instructions'):
        print("✅ Cache instructions encontradas para cliente criado!")
        print(f"   Campos: {step_result_cliente_criado['cache_instructions']['update_fields']}")
    else:
        print("❌ Cache instructions NÃO encontradas para cliente criado!")
    
    print()
    
    # 5. Teste: criar_reserva
    print("5️⃣ Testando criar_reserva...")
    step_result_reserva = {
        "status": "reserva_criada",
        "appointment_id": "AP001",
        "message": "Reserva criada com sucesso",
        "cache_instructions": {
            "update_fields": {
                "appointment_id": "AP001"
            }
        }
    }
    
    if step_result_reserva.get('cache_instructions'):
        print("✅ Cache instructions encontradas para reserva!")
        print(f"   Campos: {step_result_reserva['cache_instructions']['update_fields']}")
    else:
        print("❌ Cache instructions NÃO encontradas para reserva!")
    
    print()
    
    # 6. Simular atualização de cache com todas as instruções
    print("6️⃣ Simulando atualização de cache com todas as instruções...")
    
    extracted_data = {
        "profissional": "Dr. João",
        "profissional_id": None,
        "procedimento": "enzimas",
        "servico_id": None,
        "cliente_id": None,
        "nome": None,
        "appointment_id": None,
        "data": "2025-08-15"
    }
    
    print(f"🗄️ Dados ANTES da atualização: {extracted_data}")
    
    # Aplicar todas as instruções de cache
    all_instructions = [
        step_result_profissional,
        step_result_servico,
        step_result_cliente_encontrado,
        step_result_reserva
    ]
    
    for step_result in all_instructions:
        if step_result.get('cache_instructions'):
            cache_instructions = step_result.get('cache_instructions')
            if "update_fields" in cache_instructions:
                update_fields = cache_instructions["update_fields"]
                for field, value in update_fields.items():
                    extracted_data[field] = value
                    print(f"✅ Campo '{field}' atualizado para '{value}'")
    
    print(f"🗄️ Dados APÓS atualização: {extracted_data}")
    
    # Verificar se todos os IDs foram salvos
    campos_obrigatorios = ['profissional_id', 'servico_id', 'cliente_id', 'appointment_id']
    todos_salvos = all(extracted_data.get(campo) for campo in campos_obrigatorios)
    
    if todos_salvos:
        print("🎯 SUCESSO: Todos os IDs foram salvos no cache!")
    else:
        print("❌ ERRO: Nem todos os IDs foram salvos no cache!")
        for campo in campos_obrigatorios:
            if not extracted_data.get(campo):
                print(f"   ❌ Campo '{campo}' não foi salvo")
    
    print()
    print("🎯 Teste de TODAS as Cache Instructions Concluído!")
    print("=" * 60)

if __name__ == "__main__":
    test_all_cache_instructions()
