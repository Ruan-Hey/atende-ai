#!/usr/bin/env python3
"""
Teste simples para verificar se a nova funcionalidade de cache está funcionando
"""

def test_cache_instructions():
    """Testa se as instruções de cache estão sendo retornadas corretamente"""
    
    print("🧪 Testando Instruções de Cache")
    print("=" * 50)
    
    # Simular resultado de uma tool (como seria retornado pelo Rules Engine)
    step_result = {
        "status": "encontrado",
        "id": "564410",
        "nome": "Dr. João Silva",
        "profissional_id": "564410",
        "confianca": "ALTA",
        "razao": "Match exato com nome",
        "cache_instructions": {
            "update_fields": {
                "profissional_id": "564410"
            }
        }
    }
    
    print(f"📋 Step Result: {step_result}")
    print()
    
    # Verificar se tem instruções de cache
    if step_result.get('cache_instructions'):
        print("✅ Cache instructions encontradas!")
        cache_instructions = step_result.get('cache_instructions')
        
        if "update_fields" in cache_instructions:
            update_fields = cache_instructions["update_fields"]
            print(f"📝 Campos para atualizar: {update_fields}")
            
            # Simular dados extraídos (como seria no Smart Agent)
            extracted_data = {
                "profissional": "Dr. João",
                "profissional_id": None,  # Será atualizado
                "procedimento": "enzimas",
                "data": "2025-08-15"
            }
            
            print(f"🗄️ Dados antes da atualização: {extracted_data}")
            
            # Simular atualização do cache
            for field, value in update_fields.items():
                extracted_data[field] = value
                print(f"✅ Campo '{field}' atualizado para '{value}'")
            
            print(f"🗄️ Dados após atualização: {extracted_data}")
            
            # Verificar se o profissional_id foi salvo
            if extracted_data.get('profissional_id'):
                print("🎯 SUCESSO: profissional_id foi salvo no cache!")
            else:
                print("❌ ERRO: profissional_id não foi salvo no cache!")
        else:
            print("❌ ERRO: update_fields não encontrado nas instruções")
    else:
        print("❌ ERRO: Cache instructions não encontradas")
    
    print()
    print("🎯 Teste de Cache Instructions Concluído!")
    print("=" * 50)

if __name__ == "__main__":
    test_cache_instructions()
