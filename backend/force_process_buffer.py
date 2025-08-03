#!/usr/bin/env python3
"""
Força o processamento do buffer e verifica mensagens pendentes
"""

import requests
import json

def force_process_buffer():
    """Força o processamento do buffer"""
    
    print("🔧 FORÇANDO PROCESSAMENTO DO BUFFER")
    print("=" * 80)
    
    # 1. VERIFICAR STATUS DO BUFFER
    print("📋 1. Status atual do buffer:")
    
    try:
        response = requests.get("https://api.tinyteams.app/api/admin/buffer/status", timeout=10)
        print(f"   📊 Status Code: {response.status_code}")
        if response.status_code == 200:
            buffer_data = response.json()
            print(f"   📝 Buffer Status: {json.dumps(buffer_data, indent=2)}")
        else:
            print(f"   ⚠️ Resposta inesperada: {response.text[:100]}")
    except Exception as e:
        print(f"   ❌ Erro ao verificar buffer: {e}")
    
    # 2. FORÇAR PROCESSAMENTO DO BUFFER
    print("\n🔧 2. Forçando processamento do buffer...")
    
    # Tentar processar buffer para o cliente específico
    clientes = ["554184447366", "554195984948"]
    
    for cliente_id in clientes:
        print(f"\n   📱 Processando buffer para cliente: {cliente_id}")
        
        try:
            response = requests.post(
                "https://api.tinyteams.app/api/admin/buffer/force-process",
                params={"cliente_id": cliente_id, "empresa": "tinyteams"},
                timeout=30
            )
            print(f"   📊 Status Code: {response.status_code}")
            print(f"   📝 Response: {response.text}")
            
            if response.status_code == 200:
                print("   ✅ Processamento forçado com sucesso!")
            else:
                print("   ❌ Erro ao forçar processamento")
                
        except Exception as e:
            print(f"   ❌ Erro ao processar buffer: {e}")
    
    # 3. VERIFICAR STATUS APÓS PROCESSAMENTO
    print("\n📋 3. Status do buffer após processamento:")
    
    try:
        response = requests.get("https://api.tinyteams.app/api/admin/buffer/status", timeout=10)
        print(f"   📊 Status Code: {response.status_code}")
        if response.status_code == 200:
            buffer_data = response.json()
            print(f"   📝 Buffer Status: {json.dumps(buffer_data, indent=2)}")
        else:
            print(f"   ⚠️ Resposta inesperada: {response.text[:100]}")
    except Exception as e:
        print(f"   ❌ Erro ao verificar buffer: {e}")
    
    # 4. TESTE DE ENVIO DE MENSAGEM
    print("\n🧪 4. Teste de envio de mensagem...")
    
    test_data = {
        "Body": "Teste de processamento forçado",
        "From": "whatsapp:+554184447366",
        "To": "whatsapp:+554184447366",
        "WaId": "554184447366",
        "MessageType": "text"
    }
    
    try:
        response = requests.post(
            "https://api.tinyteams.app/webhook/tinyteams",
            data=test_data,
            timeout=10
        )
        print(f"   📊 Status Code: {response.status_code}")
        print(f"   📝 Response: {response.text}")
        
        if response.status_code == 200:
            print("   ✅ Mensagem enviada com sucesso!")
            
            # Aguardar e forçar processamento
            import time
            time.sleep(3)
            
            print("   🔧 Forçando processamento da mensagem de teste...")
            
            response = requests.post(
                "https://api.tinyteams.app/api/admin/buffer/force-process",
                params={"cliente_id": "554184447366", "empresa": "tinyteams"},
                timeout=30
            )
            print(f"   📊 Status Code: {response.status_code}")
            print(f"   📝 Response: {response.text}")
            
        else:
            print("   ❌ Erro ao enviar mensagem")
            
    except Exception as e:
        print(f"   ❌ Erro ao testar envio: {e}")

if __name__ == "__main__":
    force_process_buffer() 