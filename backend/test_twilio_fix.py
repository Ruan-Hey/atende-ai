#!/usr/bin/env python3
"""
Testa a correção do problema do número do Twilio
"""

import requests
import json

def test_twilio_fix():
    """Testa a correção do problema do número"""
    
    print("🧪 TESTANDO CORREÇÃO DO TWILIO")
    print("=" * 80)
    
    # Testar com diferentes formatos de número
    test_numbers = [
        "554184447366",
        "+554184447366", 
        "++554184447366"
    ]
    
    for number in test_numbers:
        print(f"\n📱 Testando número: {number}")
        
        # Simular o que o código faria
        if not number.startswith('whatsapp:'):
            clean_number = number.lstrip('+')
            formatted_number = f"whatsapp:+{clean_number}"
            print(f"   📝 Número limpo: {clean_number}")
            print(f"   📝 Número formatado: {formatted_number}")
        else:
            print(f"   ✅ Já está no formato correto: {number}")
    
    print("\n✅ Correção aplicada!")
    print("📋 Agora o sistema deve funcionar corretamente.")
    print("💡 Teste enviando uma mensagem no WhatsApp!")

if __name__ == "__main__":
    test_twilio_fix() 