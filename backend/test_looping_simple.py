#!/usr/bin/env python3
"""
Teste simples da lógica de looping de disponibilidade
Testa apenas a lógica de cálculo de datas pulando sábados e domingos.
"""

from datetime import datetime, timedelta

def test_date_looping_logic():
    """Testa a lógica de looping de datas pulando sábados e domingos"""
    
    print("🧪 Testando lógica de looping de datas...")
    
    # Data inicial: 01/09/2024 (domingo)
    data_inicial = datetime(2024, 9, 1)
    max_tentativas = 7
    
    print(f"📅 Data inicial: {data_inicial.strftime('%Y-%m-%d')} ({data_inicial.strftime('%A')})")
    print(f"🔄 Máximo de tentativas: {max_tentativas}")
    print()
    
    # Simular o looping
    current_date = data_inicial
    attempts = 0
    found_slots = False
    next_available_date = None
    next_available_slots = []
    
    while attempts < max_tentativas and not found_slots:
        current_date_str = current_date.strftime('%Y-%m-%d')
        weekday = current_date.weekday()  # 0=Segunda, 6=Domingo
        dia_semana = current_date.strftime('%A')
        
        # Pular sábados (5) e domingos (6)
        if weekday in [5, 6]:
            print(f"⏭️ Tentativa {attempts + 1:2d}: {current_date_str} - {dia_semana} PULADO (fim de semana)")
            current_date += timedelta(days=1)
            attempts += 1
            continue
        
        print(f"🔍 Tentativa {attempts + 1:2d}: {current_date_str} - {dia_semana} VERIFICANDO...")
        
        # Simular verificação de disponibilidade
        # Para o teste, vamos simular que dia 05/09 tem horários disponíveis
        if current_date_str == "2024-09-05":
            # Encontrou slots disponíveis
            found_slots = True
            next_available_date = current_date_str
            next_available_slots = ["10:30", "11:30", "12:00"]
            print(f"✅ ENCONTRADO! {len(next_available_slots)} slots disponíveis para {next_available_date}")
            break
        else:
            print(f"❌ Nenhum slot disponível para {current_date_str}")
            current_date += timedelta(days=1)
            attempts += 1
    
    # Preparar resultado
    if found_slots:
        resultado = {
            "success": True,
            "original_date": data_inicial.strftime('%Y-%m-%d'),
            "next_available_date": next_available_date,
            "attempts_made": attempts,
            "available_slots": next_available_slots,
            "looping_info": {
                "total_attempts": attempts,
                "message": f"Não há disponibilidade para {data_inicial.strftime('%Y-%m-%d')}. Próxima data com horários: {next_available_date} [{', '.join(next_available_slots)}]"
            }
        }
    else:
        resultado = {
            "success": False,
            "original_date": data_inicial.strftime('%Y-%m-%d'),
            "attempts_made": attempts,
            "available_slots": [],
            "looping_info": {
                "total_attempts": attempts,
                "message": f"Não foi possível encontrar horários disponíveis em {attempts} tentativas. Tente uma data mais distante."
            }
        }
    
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
    
    return resultado

def test_weekend_skipping():
    """Testa especificamente o pulo de sábados e domingos"""
    
    print("\n🧮 Testando pulo de sábados e domingos...")
    
    # Testar várias datas iniciais
    datas_teste = [
        "2024-09-01",  # Domingo
        "2024-09-07",  # Sábado
        "2024-09-02",  # Segunda
        "2024-09-14",  # Sábado
        "2024-09-15",  # Domingo
    ]
    
    for data_teste in datas_teste:
        print(f"\n📅 Testando data inicial: {data_teste}")
        
        data_inicial = datetime.strptime(data_teste, '%Y-%m-%d')
        current_date = data_inicial
        attempts = 0
        max_tentativas = 5
        
        while attempts < max_tentativas:
            current_date_str = current_date.strftime('%Y-%m-%d')
            weekday = current_date.weekday()
            dia_semana = current_date.strftime('%A')
            
            if weekday in [5, 6]:
                print(f"   ⏭️ {current_date_str} - {dia_semana} PULADO")
            else:
                print(f"   ✅ {current_date_str} - {dia_semana} VERIFICADO")
            
            current_date += timedelta(days=1)
            attempts += 1
    
    print("✅ Teste de pulo de fins de semana concluído!")

if __name__ == "__main__":
    print("🚀 Iniciando testes simples de looping de disponibilidade...")
    
    # Testar lógica principal
    resultado = test_date_looping_logic()
    
    # Testar pulo de fins de semana
    test_weekend_skipping()
    
    if resultado.get('success'):
        print("\n🎉 Teste principal passou!")
    else:
        print("\n💥 Teste principal falhou!")
    
    print("\n✅ Todos os testes concluídos!")
