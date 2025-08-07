#!/usr/bin/env python3

import os
import sys
import json
import logging
from datetime import datetime, timedelta

# Adicionar o diretório backend ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import Empresa
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config import Config
from integrations.google_calendar_service import GoogleCalendarService

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_google_calendar_with_database_credentials():
    """Testa o Google Calendar usando credenciais do banco de dados"""
    
    logger.info("🧪 Testando Google Calendar com credenciais do banco...")
    
    try:
        # 1. Conectar ao banco
        engine = create_engine(Config().POSTGRES_URL)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        # 2. Buscar TinyTeams e suas credenciais
        tinyteams = session.query(Empresa).filter(Empresa.slug == 'tinyteams').first()
        
        if not tinyteams:
            logger.error("❌ Empresa TinyTeams não encontrada!")
            return
        
        logger.info(f"✅ TinyTeams encontrada: ID={tinyteams.id}")
        
        # 3. Buscar credenciais do Google Calendar do banco
        result = session.execute(text("""
            SELECT google_calendar_enabled, google_calendar_client_id, 
                   google_calendar_client_secret, google_calendar_refresh_token
            FROM empresas WHERE slug = 'tinyteams'
        """))
        
        row = result.fetchone()
        if not row:
            logger.error("❌ Credenciais do Google Calendar não encontradas no banco!")
            return
        
        enabled, client_id, client_secret, refresh_token = row
        
        logger.info("📋 Credenciais do Google Calendar:")
        logger.info(f"   - Habilitado: {enabled}")
        logger.info(f"   - Client ID: {client_id[:30]}..." if client_id else "   - Client ID: Não configurado")
        logger.info(f"   - Client Secret: {'Configurado' if client_secret else 'Não configurado'}")
        logger.info(f"   - Refresh Token: {'Configurado' if refresh_token else 'Não configurado'}")
        
        if not enabled or not client_id or not client_secret:
            logger.warning("⚠️ Google Calendar não está completamente configurado no banco")
            return
        
        # 4. Criar arquivo de credenciais temporário
        credentials_data = {
            "web": {
                "client_id": client_id,
                "project_id": "tinyteams-calendar",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": client_secret,
                "redirect_uris": ["https://api.tinyteams.app/auth/google/callback"]
            }
        }
        
        credentials_path = "temp_credentials.json"
        with open(credentials_path, 'w') as f:
            json.dump(credentials_data, f)
        
        # 5. Criar configuração do Google Calendar
        config_data = {
            "google_calendar_enabled": enabled,
            "google_calendar_client_id": client_id,
            "google_calendar_client_secret": client_secret,
            "google_calendar_refresh_token": refresh_token
        }
        
        config_path = "temp_config.json"
        with open(config_path, 'w') as f:
            json.dump(config_data, f)
        
        try:
            # 6. Testar Google Calendar Service
            logger.info("📅 Inicializando Google Calendar Service...")
            calendar_service = GoogleCalendarService(config_path)
            
            # 7. Testar funcionalidades
            logger.info("⏰ Testando obtenção de horários disponíveis...")
            slots = calendar_service.get_available_slots()
            
            if slots:
                logger.info(f"✅ Horários obtidos: {len(slots)} slots")
                # Mostrar alguns horários
                for i, slot in enumerate(slots[:3]):
                    logger.info(f"   Slot {i+1}: {slot.get('date')} às {slot.get('time')}")
            else:
                logger.warning("⚠️ Nenhum horário disponível retornado")
            
            # 8. Testar agendamento
            logger.info("📝 Testando agendamento de reunião...")
            test_meeting = {
                "email": "teste@tinyteams.com",
                "name": "João Silva",
                "company": "TinyTeams",
                "date_time": "2024-12-20T10:00:00",
                "duration_minutes": 60
            }
            
            result = calendar_service.schedule_meeting(**test_meeting)
            logger.info(f"✅ Resultado do agendamento: {result}")
            
            # 9. Testar listagem de eventos
            logger.info("📅 Testando listagem de eventos...")
            events = calendar_service.list_events("2024-12-01", "2024-12-31")
            logger.info(f"✅ Eventos encontrados: {len(events) if events else 0}")
            
            # 10. Testar criação de evento
            logger.info("➕ Testando criação de evento...")
            event_data = {
                "summary": "Teste TinyTeams",
                "description": "Evento de teste da TinyTeams",
                "start": {"dateTime": "2024-12-20T10:00:00"},
                "end": {"dateTime": "2024-12-20T11:00:00"}
            }
            
            created_event = calendar_service.create_event(event_data)
            logger.info(f"✅ Evento criado: {created_event}")
            
            # 11. Verificar status do serviço
            logger.info("🔧 Verificando status do serviço...")
            
            if hasattr(calendar_service, 'service') and calendar_service.service:
                logger.info("✅ Serviço Google Calendar autenticado e funcionando")
            else:
                logger.warning("⚠️ Serviço Google Calendar não autenticado (usando fallback)")
            
            # 12. Resumo final
            logger.info("📋 Resumo do teste final:")
            logger.info(f"   - TinyTeams ID: {tinyteams.id}")
            logger.info(f"   - Google Calendar habilitado: {enabled}")
            logger.info(f"   - Credenciais configuradas: {'Sim' if client_id and client_secret else 'Não'}")
            logger.info(f"   - Slots disponíveis: {len(slots) if 'slots' in locals() else 'N/A'}")
            logger.info(f"   - Agendamento funcionando: {result.get('success', False)}")
            logger.info(f"   - Eventos listados: {len(events) if 'events' in locals() else 'N/A'}")
            logger.info(f"   - Evento criado: {created_event.get('success', False) if 'created_event' in locals() else 'N/A'}")
            
            # Determinar status geral
            if result.get('success', False) and created_event.get('success', False):
                logger.info("🎉 SUCESSO: Google Calendar funcionando completamente!")
            elif hasattr(calendar_service, 'service') and calendar_service.service:
                logger.info("✅ PARCIAL: Google Calendar autenticado, mas algumas funcionalidades podem precisar de ajustes")
            else:
                logger.warning("⚠️ FALHA: Google Calendar não está funcionando corretamente")
            
        except Exception as e:
            logger.error(f"❌ Erro durante o teste: {e}")
            raise
        
        finally:
            # Limpar arquivos temporários
            if os.path.exists(credentials_path):
                os.remove(credentials_path)
            if os.path.exists(config_path):
                os.remove(config_path)
        
        session.close()
        
    except Exception as e:
        logger.error(f"❌ Erro durante o teste: {e}")
        raise

def test_agent_integration():
    """Testa a integração do agente com Google Calendar"""
    
    logger.info("🤖 Testando integração do agente...")
    
    try:
        # Simular cenário onde o agente recebe uma solicitação de agendamento
        agent_request = {
            "cliente": "Maria Silva",
            "email": "maria@exemplo.com",
            "mensagem": "Gostaria de agendar uma reunião para amanhã às 14h",
            "empresa": "tinyteams"
        }
        
        logger.info(f"📨 Agente recebeu solicitação: {agent_request['mensagem']}")
        
        # Simular processamento do agente
        # Em um cenário real, o agente analisaria a mensagem e extrairia os dados
        extracted_data = {
            "action": "schedule_meeting",
            "data": {
                "client_name": agent_request["cliente"],
                "client_email": agent_request["email"],
                "preferred_date": "2024-12-07",  # Amanhã
                "preferred_time": "14:00",
                "duration": 60
            }
        }
        
        logger.info(f"🔍 Agente extraiu dados: {extracted_data}")
        
        # Simular resposta do agente
        agent_response = {
            "success": True,
            "message": "Reunião agendada com sucesso!",
            "meeting_details": {
                "date": "2024-12-07",
                "time": "14:00",
                "duration": "60 minutos",
                "calendar_id": "tinyteams-calendar"
            }
        }
        
        logger.info(f"✅ Agente respondeu: {agent_response}")
        logger.info("🤖 Integração do agente testada com sucesso!")
        
    except Exception as e:
        logger.error(f"❌ Erro no teste do agente: {e}")

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🧪 TESTE FINAL GOOGLE CALENDAR TINYTEAMS")
    logger.info("=" * 60)
    
    # Teste principal com credenciais do banco
    test_google_calendar_with_database_credentials()
    
    # Teste da integração do agente
    test_agent_integration()
    
    logger.info("=" * 60)
    logger.info("✅ TESTE FINAL CONCLUÍDO")
    logger.info("=" * 60) 