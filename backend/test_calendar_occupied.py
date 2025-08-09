#!/usr/bin/env python3
"""
Teste que simula horários ocupados para o dia 11 de agosto de 2025
"""

import os
import sys
from datetime import datetime, timedelta

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def simulate_occupied_slots():
    """Simula horários ocupados para o dia 11 de agosto de 2025"""
    
    print("🔍 Simulando horários ocupados para 11 de agosto de 2025...")
    
    # Data de teste
    test_date = "2025-08-11"
    print(f"📅 Data: {test_date}")
    
    # Horários padrão disponíveis (9h às 17h)
    all_hours = [
        "09:00", "10:00", "11:00", "12:00", 
        "13:00", "14:00", "15:00", "16:00", "17:00"
    ]
    
    # Simular eventos ocupados
    occupied_events = [
        {
            "start": "2025-08-11T10:00:00",
            "end": "2025-08-11T11:00:00", 
            "summary": "Reunião com Cliente A"
        },
        {
            "start": "2025-08-11T14:00:00",
            "end": "2025-08-11T15:30:00",
            "summary": "Apresentação Projeto B"
        },
        {
            "start": "2025-08-11T16:00:00",
            "end": "2025-08-11T17:00:00",
            "summary": "Call com Equipe"
        }
    ]
    
    print(f"\n📅 Eventos ocupados:")
    for i, event in enumerate(occupied_events, 1):
        start = event["start"].split("T")[1][:5]  # Extrair apenas hora
        end = event["end"].split("T")[1][:5]
        summary = event["summary"]
        print(f"  {i}. {start}-{end} - {summary}")
    
    # Calcular horários disponíveis
    occupied_hours = set()
    for event in occupied_events:
        start_hour = event["start"].split("T")[1][:5]
        end_hour = event["end"].split("T")[1][:5]
        
        # Adicionar todas as horas ocupadas
        current = datetime.strptime(start_hour, "%H:%M")
        end = datetime.strptime(end_hour, "%H:%M")
        
        while current < end:
            occupied_hours.add(current.strftime("%H:%M"))
            current += timedelta(hours=1)
    
    # Horários disponíveis
    available_hours = [hour for hour in all_hours if hour not in occupied_hours]
    
    print(f"\n🕐 Horários disponíveis:")
    for i, hour in enumerate(available_hours, 1):
        print(f"  {i}. {hour}")
    
    print(f"\n📊 Resumo:")
    print(f"  Total de horários: {len(all_hours)}")
    print(f"  Horários ocupados: {len(occupied_hours)}")
    print(f"  Horários disponíveis: {len(available_hours)}")
    
    # Simular resposta do agente
    print(f"\n🤖 Resposta do Agente:")
    if available_hours:
        slots_info = ", ".join(available_hours[:5])  # Primeiros 5 horários
        print(f"Para o dia 11 de agosto de 2025, tenho os seguintes horários disponíveis:")
        print(f"{slots_info}")
        print(f"Por favor, escolha um dos horários para agendarmos a reunião.")
    else:
        print(f"Não há horários disponíveis para 11 de agosto de 2025.")
        print(f"Por favor, escolha outra data para a reunião.")

if __name__ == "__main__":
    simulate_occupied_slots() 