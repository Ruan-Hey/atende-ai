#!/usr/bin/env python3
"""
Script para testar o agente com configurações corretas do Google Calendar
"""

import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Empresa, EmpresaAPI, API
from config import Config
from agents.whatsapp_agent import WhatsAppAgent

def test_agent_calendar():
    """Testa o agente com configurações corretas do Google Calendar"""
    try:
        # Configurar conexão com banco
        config = Config()
        engine = create_engine(config.POSTGRES_URL)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        # Buscar empresa TinyTeams
        empresa = session.query(Empresa).filter(Empresa.slug == 'tinyteams').first()
        if not empresa:
            print("❌ Empresa 'tinyteams' não encontrada")
            return
        
        print(f"✅ Empresa encontrada: {empresa.nome} (ID: {empresa.id})")
        
        # Buscar APIs conectadas da empresa
        empresa_apis = session.query(EmpresaAPI).filter(
            EmpresaAPI.empresa_id == empresa.id,
            EmpresaAPI.ativo == True
        ).all()
        
        # Criar configuração base da empresa
        empresa_config = {
            'nome': empresa.nome,
            'slug': empresa.slug,
            'empresa_id': empresa.id,
            'twilio_sid': empresa.twilio_sid,
            'twilio_token': empresa.twilio_token,
            'twilio_number': empresa.twilio_number,
            'mensagem_quebrada': empresa.mensagem_quebrada or False,
            'prompt': empresa.prompt,
            'usar_buffer': empresa.usar_buffer if empresa.usar_buffer is not None else True
        }
        
        # Adicionar configurações das APIs conectadas
        for empresa_api in empresa_apis:
            api_name = empresa_api.api.nome
            config_data = empresa_api.config or {}
            
            # Adicionar configuração completa da API
            api_prefix = api_name.lower().replace(' ', '_')
            empresa_config[f'{api_prefix}_config'] = config_data
            
            # Adicionar campos específicos para compatibilidade
            if api_name == "Google Calendar":
                empresa_config['google_calendar_client_id'] = config_data.get('client_id')
                empresa_config['google_calendar_client_secret'] = config_data.get('client_secret')
                empresa_config['google_calendar_refresh_token'] = config_data.get('refresh_token')
                empresa_config['google_calendar_service_account'] = config_data.get('google_calendar_service_account')
                empresa_config['google_calendar_project_id'] = config_data.get('google_calendar_project_id')
                empresa_config['google_calendar_client_email'] = config_data.get('google_calendar_client_email')
                empresa_config['google_calendar_enabled'] = config_data.get('enabled', True)
                empresa_config['google_sheets_id'] = config_data.get('google_sheets_id')
            elif api_name == "Google Sheets":
                empresa_config['google_sheets_id'] = config_data.get('google_sheets_id')
            elif api_name == "OpenAI":
                if config_data.get('openai_key'):
                    empresa_config['openai_key'] = config_data.get('openai_key')
            
            # Marcar API como ativa
            empresa_config[f'{api_prefix}_enabled'] = True
        
        print("\n📋 Configuração do agente:")
        print(f"   - google_calendar_enabled: {empresa_config.get('google_calendar_enabled')}")
        print(f"   - google_calendar_client_id: {empresa_config.get('google_calendar_client_id')}")
        print(f"   - google_calendar_refresh_token: {empresa_config.get('google_calendar_refresh_token')[:20] if empresa_config.get('google_calendar_refresh_token') else 'N/A'}...")
        print(f"   - openai_key: {empresa_config.get('openai_key')[:10] if empresa_config.get('openai_key') else 'N/A'}...")
        
        # Criar agente
        print("\n🤖 Criando agente...")
        whatsapp_agent = WhatsAppAgent(empresa_config)
        
        # Simular webhook data
        webhook_data = {
            'WaId': '5511999999999',
            'Body': 'Tem horário disponível para as 14 horas do dia 11-08?',
            'ProfileName': 'Cliente Teste'
        }
        
        print(f"\n🧪 Testando agente com mensagem: '{webhook_data['Body']}'")
        
        # Processar mensagem
        import asyncio
        result = asyncio.run(whatsapp_agent.process_whatsapp_message(webhook_data, empresa_config))
        
        print(f"\n📤 Resposta do agente:")
        print(f"   - Success: {result.get('success')}")
        print(f"   - Message: {result.get('message')}")
        
        if result.get('success'):
            print("✅ Agente funcionando corretamente!")
        else:
            print(f"❌ Erro no agente: {result.get('error')}")
        
        session.close()
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        if 'session' in locals():
            session.close()

if __name__ == "__main__":
    test_agent_calendar() 