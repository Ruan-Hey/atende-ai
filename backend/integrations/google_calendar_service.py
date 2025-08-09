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
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

class GoogleCalendarService:
    def __init__(self, config: Dict[str, any] = None):
        """
        Inicializa o serviço do Google Calendar
        Args:
            config: Dicionário com configurações (client_id, client_secret, refresh_token, etc.)
        """
        self.config = config or {}
        self.SCOPES = ['https://www.googleapis.com/auth/calendar']  # Escopo único e válido
        self.creds = None
        self.service = None
        self._calendar_id: Optional[str] = None
        
        # Timezone padrão Brasil; pode ser sobrescrito por config
        tz_name = self.config.get('google_calendar_timezone', 'America/Sao_Paulo')
        try:
            self.tz = ZoneInfo(tz_name)
        except Exception:
            self.tz = ZoneInfo('America/Sao_Paulo')
        
        # Verifica se o Google Calendar está habilitado
        if not self.config.get('google_calendar_enabled', False):
            logger.warning("Google Calendar não está habilitado na configuração")
            return
        
        self._authenticate()
    
    def _authenticate(self):
        """Autentica com Google Calendar API"""
        try:
            # PRIORIDADE 1: Verificar se temos configuração OAuth2 completa
            client_id = self.config.get('google_calendar_client_id')
            client_secret = self.config.get('google_calendar_client_secret')
            refresh_token = self.config.get('google_calendar_refresh_token')
            
            if client_id and client_secret and refresh_token:
                logger.info("Usando OAuth2 para autenticação (prioridade)")
                self._authenticate_with_oauth2()
                return
            
            # PRIORIDADE 2: Verificar se temos Service Account (fallback)
            service_account = self.config.get('google_calendar_service_account')
            if service_account:
                logger.info("Usando Service Account para autenticação (fallback)")
                self._authenticate_with_service_account(service_account)
                return
            
            # PRIORIDADE 3: Fallback para arquivo de credenciais
            logger.info("Usando arquivo de credenciais (fallback)")
            self._authenticate_with_file()
            
        except Exception as e:
            logger.warning(f"Google Calendar não configurado ou erro na autenticação: {e}")
            # Não falhar, apenas continuar sem autenticação
            self.service = None
    
    def _authenticate_with_oauth2(self):
        """Autentica usando OAuth2 (client_id, client_secret, refresh_token)"""
        try:
            client_id = self.config.get('google_calendar_client_id')
            client_secret = self.config.get('google_calendar_client_secret')
            refresh_token = self.config.get('google_calendar_refresh_token')
            
            if not all([client_id, client_secret, refresh_token]):
                logger.warning("Credenciais OAuth2 incompletas")
                return
            
            # Criar credenciais OAuth2
            self.creds = Credentials(
                None,  # No access token initially
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret,
                scopes=self.SCOPES
            )
            
            # Refresh das credenciais
            self.creds.refresh(Request())
            logger.info("Autenticado com OAuth2 (refresh token)")
            
            self.service = build('calendar', 'v3', credentials=self.creds)
            logger.info("Google Calendar autenticado com sucesso via OAuth2")
            
        except Exception as e:
            logger.error(f"Erro na autenticação OAuth2: {e}")
            raise
    
    def _authenticate_with_service_account(self, service_account_data):
        """Autentica usando Service Account"""
        try:
            from google.oauth2 import service_account
            
            # Criar credenciais do Service Account
            self.creds = service_account.Credentials.from_service_account_info(
                service_account_data,
                scopes=self.SCOPES
            )
            
            self.service = build('calendar', 'v3', credentials=self.creds)
            logger.info("Google Calendar autenticado com Service Account")
            
        except Exception as e:
            logger.error(f"Erro na autenticação com Service Account: {e}")
            self.service = None
    
    def _authenticate_with_file(self):
        """Autentica usando arquivo de credenciais (fallback)"""
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
                        logger.warning("Arquivo 'credentials.json' não encontrado. Google Calendar não configurado.")
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
            logger.warning(f"Google Calendar não configurado ou erro na autenticação: {e}")
            # Não falhar, apenas continuar sem autenticação
            self.service = None

    # -------------------------------
    # Seleção automática de calendário
    # -------------------------------
    def _resolve_calendar_id(self) -> str:
        """Retorna o calendarId configurado ou detecta automaticamente o primeiro acessível.
        Preferência: primary > owner > writer > primeiro da lista.
        """
        if self._calendar_id:
            return self._calendar_id
        configured = self.config.get('google_calendar_calendar_id')
        if configured:
            self._calendar_id = configured
            return self._calendar_id
        # Sem id configurado: tentar descobrir
        try:
            if not self.service:
                return 'primary'
            calendars_resp = self.service.calendarList().list().execute()
            items = calendars_resp.get('items', [])
            # primary
            primary = next((c.get('id') for c in items if c.get('primary')), None)
            if primary:
                self._calendar_id = primary
                return self._calendar_id
            # owner
            owner = next((c.get('id') for c in items if c.get('accessRole') == 'owner'), None)
            if owner:
                self._calendar_id = owner
                return self._calendar_id
            # writer ou primeiro
            writer = next((c.get('id') for c in items if c.get('accessRole') in ['owner', 'writer']), None)
            if writer:
                self._calendar_id = writer
                return self._calendar_id
            if items:
                self._calendar_id = items[0].get('id', 'primary')
                return self._calendar_id
        except Exception as e:
            logger.warning(f"Falha ao detectar calendarId automaticamente: {e}")
        # Fallback final
        self._calendar_id = 'primary'
        return self._calendar_id
    
    def get_available_slots(self, date: Optional[str] = None, days_ahead: int = 7) -> List[Dict[str, str]]:
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
            # Define período de busca com timezone consistente (Brasil por padrão)
            now = datetime.now(self.tz)
            
            if date:
                start_date = datetime.strptime(date, '%Y-%m-%d').replace(tzinfo=self.tz)
            else:
                # Usa a data atual na timezone definida
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            end_date = start_date + timedelta(days=days_ahead)
            
            # Calendar a consultar
            calendar_id = self._resolve_calendar_id()
            
            # Busca eventos no calendário (informando timezone)
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=start_date.isoformat(),
                timeMax=end_date.isoformat(),
                singleEvents=True,
                orderBy='startTime',
                timeZone=str(self.tz)
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
                                event_start = event_start.astimezone(self.tz)
                            else:  # Só data
                                event_start = datetime.strptime(event_start_str, '%Y-%m-%d').replace(tzinfo=self.tz)
                            
                            if 'T' in event_end_str:  # Tem time
                                event_end = datetime.fromisoformat(event_end_str.replace('Z', '+00:00'))
                                event_end = event_end.astimezone(self.tz)
                            else:  # Só data
                                event_end = datetime.strptime(event_end_str, '%Y-%m-%d').replace(tzinfo=self.tz)
                            
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
            calendar_id = self._resolve_calendar_id()
            # Converte string para datetime
            meeting_time = datetime.fromisoformat(date_time.replace('Z', '+00:00'))
            end_time = meeting_time + timedelta(minutes=duration_minutes)
            
            event = {
                'summary': f'Reunião TinyTeams - {company}',
                'description': f'Reunião com {name} ({email}) da empresa {company}',
                'start': {
                    'dateTime': meeting_time.isoformat(),
                    'timeZone': 'America/Sao_Paulo',
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'America/Sao_Paulo',
                },
                # Removido 'attendees' para funcionar com Service Account
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 30},
                    ],
                },
            }
            
            event = self.service.events().insert(calendarId=calendar_id, body=event).execute()
            
            logger.info(f'Reunião agendada: {event.get("htmlLink")}')
            return {
                'success': True,
                'event_id': event.get('id'),
                'link': event.get('htmlLink'),
                'message': f'Reunião agendada para {meeting_time.strftime("%d/%m às %Hh")}'}
        
        except Exception as e:
            logger.error(f"Erro ao agendar reunião: {e}")
            return {'success': False, 'message': f'Erro ao agendar: {str(e)}'}
    
    def list_events(self, start_date: str, end_date: str) -> List[Dict]:
        """
        Lista eventos em um período específico
        Args:
            start_date: Data de início (YYYY-MM-DD)
            end_date: Data de fim (YYYY-MM-DD)
        """
        if not self.service:
            logger.warning("Google Calendar não autenticado")
            return []
        
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            calendar_id = self._resolve_calendar_id()
            
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=start_dt.isoformat() + 'Z',
                timeMax=end_dt.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            return events_result.get('items', [])
            
        except Exception as e:
            logger.error(f"Erro ao listar eventos: {e}")
            return []
    
    def create_event(self, event_data: Dict) -> Dict:
        """
        Cria um evento no Google Calendar
        Args:
            event_data: Dados do evento (summary, start, end, attendees, etc.)
        """
        if not self.service:
            logger.warning("Google Calendar não autenticado")
            return {'success': False, 'message': 'Calendário não configurado'}
        
        try:
            calendar_id = self._resolve_calendar_id()
            event = self.service.events().insert(calendarId=calendar_id, body=event_data).execute()
            
            logger.info(f'Evento criado: {event.get("id")}')
            return {
                'success': True,
                'id': event.get('id'),
                'summary': event.get('summary'),
                'link': event.get('htmlLink')
            }
            
        except Exception as e:
            logger.error(f"Erro ao criar evento: {e}")
            return {'success': False, 'message': f'Erro ao criar evento: {str(e)}'}
    
    def delete_event(self, event_id: str) -> bool:
        """Remove um evento pelo ID no calendário configurado."""
        if not self.service:
            logger.warning("Google Calendar não autenticado")
            return False
        try:
            calendar_id = self._resolve_calendar_id()
            self.service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
            logger.info(f"Evento removido: {event_id}")
            return True
        except Exception as e:
            logger.error(f"Erro ao remover evento: {e}")
            return False 