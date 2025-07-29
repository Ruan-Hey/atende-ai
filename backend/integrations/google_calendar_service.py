import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pickle

logger = logging.getLogger(__name__)

class GoogleCalendarService:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.SCOPES = ['https://www.googleapis.com/auth/calendar.readonly', 
                       'https://www.googleapis.com/auth/calendar.events']
        self.creds = None
        self.service = None
        self._load_config()
        self._authenticate()
    
    def _load_config(self):
        """Carrega configuração do Google Calendar"""
        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            
            # Verifica se o Google Calendar está habilitado
            if not self.config.get('google_calendar_enabled', False):
                logger.warning("Google Calendar não está habilitado na configuração")
                return
                
        except Exception as e:
            logger.error(f"Erro ao carregar configuração: {e}")
            self.config = {}
    
    def _authenticate(self):
        """Autentica com Google Calendar API"""
        try:
            # Verifica se já temos credenciais salvas
            if os.path.exists('token.pickle'):
                with open('token.pickle', 'rb') as token:
                    self.creds = pickle.load(token)
            
            # Se não há credenciais válidas, faz o fluxo de autenticação
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                else:
                    # Verifica se existe o arquivo de credenciais
                    if not os.path.exists('credentials.json'):
                        logger.warning("Arquivo 'credentials.json' não encontrado. Execute setup_google_calendar.py primeiro.")
                        return
                    
                    # Faz o fluxo de autenticação
                    from google_auth_oauthlib.flow import InstalledAppFlow
                    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', self.SCOPES)
                    self.creds = flow.run_local_server(port=0)
                
                # Salva as credenciais para próximo uso
                with open('token.pickle', 'wb') as token:
                    pickle.dump(self.creds, token)
            
            self.service = build('calendar', 'v3', credentials=self.creds)
            logger.info("Google Calendar autenticado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro na autenticação do Google Calendar: {e}")
    
    def get_available_slots(self, date: str = None, days_ahead: int = 7) -> List[Dict]:
        """
        Retorna horários disponíveis para agendamento
        Args:
            date: Data específica (YYYY-MM-DD) ou None para hoje
            days_ahead: Quantos dias à frente verificar
        """
        if not self.service:
            logger.warning("Google Calendar não autenticado, retornando horários padrão")
            return self._get_default_slots()
        
        try:
            # Define período de busca com timezone consistente
            now = datetime.now()
            local_timezone = now.astimezone().tzinfo
            
            # Garante que now tenha timezone
            if now.tzinfo is None:
                now = now.replace(tzinfo=local_timezone)
            
            if date:
                start_date = datetime.strptime(date, '%Y-%m-%d').replace(tzinfo=local_timezone)
            else:
                # Usa a data atual, não o ano futuro
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            end_date = start_date + timedelta(days=days_ahead)
            
            # Busca eventos no calendário
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=start_date.isoformat(),
                timeMax=end_date.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Gera horários disponíveis (9h às 18h, intervalos de 1h)
            available_slots = []
            
            for day in range(days_ahead):
                current_date = start_date + timedelta(days=day)
                
                # Pula finais de semana
                if current_date.weekday() >= 5:  # 5 = Sábado, 6 = Domingo
                    continue
                
                # Horários comerciais: 9h às 18h
                for hour in range(9, 18):
                    slot_start = current_date.replace(hour=hour, minute=0, second=0, microsecond=0)
                    slot_end = slot_start + timedelta(hours=1)
                    
                    # Verifica se o horário está livre
                    is_available = True
                    for event in events:
                        try:
                            event_start_str = event['start'].get('dateTime', event['start'].get('date'))
                            event_end_str = event['end'].get('dateTime', event['end'].get('date'))
                            
                            # Converte strings para datetime com timezone consistente
                            if 'T' in event_start_str:  # Tem time
                                event_start = datetime.fromisoformat(event_start_str.replace('Z', '+00:00'))
                                # Converte para timezone local se necessário
                                if event_start.tzinfo != local_timezone:
                                    event_start = event_start.astimezone(local_timezone)
                            else:  # Só data
                                event_start = datetime.strptime(event_start_str, '%Y-%m-%d').replace(tzinfo=local_timezone)
                            
                            if 'T' in event_end_str:  # Tem time
                                event_end = datetime.fromisoformat(event_end_str.replace('Z', '+00:00'))
                                # Converte para timezone local se necessário
                                if event_end.tzinfo != local_timezone:
                                    event_end = event_end.astimezone(local_timezone)
                            else:  # Só data
                                event_end = datetime.strptime(event_end_str, '%Y-%m-%d').replace(tzinfo=local_timezone)
                            
                            # Se há sobreposição, o horário não está disponível
                            if (slot_start < event_end and slot_end > event_start):
                                is_available = False
                                break
                        except Exception as e:
                            logger.warning(f"Erro ao processar evento: {e}")
                            continue
                    
                    # Só adiciona se for no futuro (com margem de 2 horas)
                    if is_available and slot_start > now + timedelta(hours=2):
                        available_slots.append({
                            'date': slot_start.strftime('%Y-%m-%d'),
                            'time': slot_start.strftime('%H:%M'),
                            'datetime': slot_start.isoformat(),
                            'formatted': slot_start.strftime('%d/%m às %Hh')
                        })
            
            return available_slots[:10]  # Retorna apenas os 10 primeiros horários
            
        except Exception as e:
            logger.error(f"Erro ao buscar horários disponíveis: {e}")
            return self._get_default_slots()
    
    def _get_default_slots(self) -> List[Dict]:
        """Retorna horários padrão quando não há integração com Google Calendar"""
        slots = []
        now = datetime.now()
        local_timezone = now.astimezone().tzinfo
        
        # Garante que now tenha timezone
        if now.tzinfo is None:
            now = now.replace(tzinfo=local_timezone)
        
        # Horários de trabalho personalizáveis
        work_hours = [9, 10, 11, 14, 15, 16, 17]  # 9h, 10h, 11h, 14h, 15h, 16h, 17h
        
        # Gera horários para os próximos 5 dias úteis (mais próximos)
        for day in range(5):
            current_date = now + timedelta(days=day)
            
            # Pula finais de semana
            if current_date.weekday() >= 5:
                continue
            
            # Adiciona horários de trabalho
            for hour in work_hours:
                slot_time = current_date.replace(hour=hour, minute=0, second=0, microsecond=0)
                
                # Só adiciona se for no futuro (com margem de 2 horas)
                if slot_time > now + timedelta(hours=2):
                    slots.append({
                        'date': slot_time.strftime('%Y-%m-%d'),
                        'time': slot_time.strftime('%H:%M'),
                        'datetime': slot_time.isoformat(),
                        'formatted': slot_time.strftime('%d/%m às %Hh')
                    })
        
        return slots[:8]  # Retorna apenas os 8 primeiros horários (mais próximos)
    
    def schedule_meeting(self, email: str, name: str, company: str, date_time: str, duration_minutes: int = 60) -> Dict:
        """
        Agenda uma reunião no Google Calendar
        Args:
            email: Email do cliente
            name: Nome do cliente
            company: Nome da empresa
            date_time: Data/hora da reunião (ISO format)
            duration_minutes: Duração em minutos
        """
        if not self.service:
            logger.warning("Google Calendar não autenticado, não é possível agendar")
            return {'success': False, 'message': 'Calendário não configurado'}
        
        try:
            # Converte string para datetime
            meeting_time = datetime.fromisoformat(date_time.replace('Z', '+00:00'))
            end_time = meeting_time + timedelta(minutes=duration_minutes)
            
            event = {
                'summary': f'Reunião TinyTeams - {company}',
                'description': f'Reunião com {name} da empresa {company}',
                'start': {
                    'dateTime': meeting_time.isoformat(),
                    'timeZone': 'America/Sao_Paulo',
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'America/Sao_Paulo',
                },
                'attendees': [
                    {'email': email},
                ],
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},
                        {'method': 'popup', 'minutes': 30},
                    ],
                },
            }
            
            event = self.service.events().insert(calendarId='primary', body=event).execute()
            
            logger.info(f'Reunião agendada: {event.get("htmlLink")}')
            return {
                'success': True,
                'event_id': event.get('id'),
                'link': event.get('htmlLink'),
                'message': f'Reunião agendada para {meeting_time.strftime("%d/%m às %Hh")}'
            }
            
        except Exception as e:
            logger.error(f"Erro ao agendar reunião: {e}")
            return {'success': False, 'message': f'Erro ao agendar: {str(e)}'} 