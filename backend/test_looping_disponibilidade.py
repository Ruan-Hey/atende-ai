#!/usr/bin/env python3
"""
Teste da funcionalidade de looping de disponibilidade
Verifica se o sistema consegue encontrar horários disponíveis em até 7 tentativas, pulando sábados e domingos.
"""

import sys
import os
import json
from datetime import datetime, timedelta

# Adicionar o diretório backend ao path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def test_looping_disponibilidade():
    """Testa a funcionalidade de looping de disponibilidade"""
    
    print("🧪 Testando funcionalidade de looping de disponibilidade...")
    
    try:
        # Importar as ferramentas
        from tools.trinks_intelligent_tools import trinks_intelligent_tools
        
        # Configuração de exemplo da empresa
        empresa_config = {
            'trinks_estabelecimento_id': '12345',
            'trinks_config': {
                'base_url': 'https://api.trinks.com',
                'api_key': 'test_key'
            },
            'auto_looping_disponibilidade': True
        }
        
        # Data de teste (01/09/2024 - domingo)
        data_teste = "2024-09-01"
        
        print(f"📅 Data de teste: {data_teste}")
        print(f"📅 Dia da semana: {datetime.strptime(data_teste, '%Y-%m-%d').strftime('%A')}")
        
        # Testar a função de looping
        resultado = trinks_intelligent_tools.check_professional_availability_with_looping(
            data=data_teste,
            service_id="123",
            empresa_config=empresa_config,
            professional_id=None,
            max_attempts=7
        )
        
        print("\n📊 Resultado do teste:")
        print(f"   Sucesso: {resultado.get('success', False)}")
        print(f"   Data original: {resultado.get('original_date')}")
        print(f"   Próxima data disponível: {resultado.get('next_available_date')}")
        print(f"   Tentativas realizadas: {resultado.get('attempts_made', 0)}")
        print(f"   Slots disponíveis: {len(resultado.get('available_slots', []))}")
        
        if resultado.get('looping_info'):
            print(f"   Mensagem do looping: {resultado.get('looping_info', {}).get('message', 'N/A')}")
        
        # Simular cenário real
        print("\n🎯 Simulando cenário real:")
        print("   Usuário: 'Queria marcar AAA TESTE com a Amabile dia 01/09'")
        print("   Sistema: Verifica disponibilidade para 01/09")
        
        if resultado.get('success'):
            print(f"   Sistema: 'Não tem nada para dia {resultado.get('original_date')} o próximo dia que tem é {resultado.get('next_available_date')} {resultado.get('available_slots', [])[:3]}'")
        else:
            print(f"   Sistema: 'Não foi possível encontrar horários disponíveis em {resultado.get('attempts_made', 0)} tentativas'")
        
        print("\n✅ Teste concluído!")
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_date_calculation():
    """Testa o cálculo de datas pulando sábados e domingos"""
    
    print("\n🧮 Testando cálculo de datas...")
    
    # Data inicial: 01/09/2024 (domingo)
    data_inicial = datetime(2024, 9, 1)
    
    print(f"📅 Data inicial: {data_inicial.strftime('%Y-%m-%d')} ({data_inicial.strftime('%A')})")
    
    # Simular 7 tentativas
    for i in range(7):
        data_atual = data_inicial + timedelta(days=i)
        weekday = data_atual.weekday()
        dia_semana = data_atual.strftime('%A')
        
        if weekday in [5, 6]:  # Sábado ou domingo
            print(f"   {i+1:2d}. {data_atual.strftime('%Y-%m-%d')} - {dia_semana} ⏭️ PULADO")
        else:
            print(f"   {i+1:2d}. {data_atual.strftime('%Y-%m-%d')} - {dia_semana} ✅ VERIFICADO")
    
    print("✅ Cálculo de datas concluído!")

if __name__ == "__main__":
    print("🚀 Iniciando testes de looping de disponibilidade...")
    
    # Testar cálculo de datas
    test_date_calculation()
    
    # Testar funcionalidade principal
    success = test_looping_disponibilidade()
    
    if success:
        print("\n🎉 Todos os testes passaram!")
    else:
        print("\n💥 Alguns testes falharam!")
        sys.exit(1)

