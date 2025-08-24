"""
Tools para execução de lógica de negócio específica do Google Calendar
Contém APENAS execução, validações e processamento de dados
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from langchain.tools import tool
from langchain_core.tools import BaseTool

# Importar regras e serviços (imports absolutos)
from rules.google_calendar_rules import GoogleCalendarRules, GoogleCalendarFlowType
from integrations.google_calendar_service import GoogleCalendarService

logger = logging.getLogger(__name__)

class GoogleCalendarTools:
    """
    Tools para execução de lógica de negócio do Google Calendar
    Contém APENAS execução, validações e processamento
    """
    
    def __init__(self, empresa_config: Dict[str, Any]):
        """
        Inicializa os tools do Google Calendar
        Args:
            empresa_config: Configuração da empresa
        """
        self.empresa_config = empresa_config
        self.google_calendar_rules = GoogleCalendarRules()
        self.google_calendar_service = GoogleCalendarService(empresa_config)
    
    @tool
    def get_available_slots(self, date: str, duration_minutes: int = 60) -> Dict[str, Any]:
        """
        Busca horários disponíveis para agendamento no Google Calendar
        Args:
            date: Data para buscar (YYYY-MM-DD)
            duration_minutes: Duração do agendamento em minutos
        Returns:
            Dicionário com horários disponíveis
        """
        try:
            logger.info(f"Buscando horários disponíveis para {date} com duração de {duration_minutes} min")
            
            # Validar campos obrigatórios usando regras
            required_fields = self.google_calendar_rules.get_required_fields(GoogleCalendarFlowType.CHECK_AVAILABILITY.value)
            if not date or not duration_minutes:
                return {
                    'success': False,
                    'error': f'Campos obrigatórios faltando: {required_fields}'
                }
            
            # Validar formato da data
            try:
                datetime.strptime(date, '%Y-%m-%d')
            except ValueError:
                return {
                    'success': False,
                    'error': 'Formato de data inválido. Use YYYY-MM-DD'
                }
            
            # Validar duração
            validation_rules = self.google_calendar_rules.get_validation_rules(GoogleCalendarFlowType.CHECK_AVAILABILITY.value)
            min_duration = validation_rules.get('min_duration', 15)
            max_duration = validation_rules.get('max_duration', 480)
            
            if duration_minutes < min_duration or duration_minutes > max_duration:
                return {
                    'success': False,
                    'error': f'Duração deve estar entre {min_duration} e {max_duration} minutos'
                }
            
            # Verificar se a data é no futuro
            today = datetime.now().date()
            check_date = datetime.strptime(date, '%Y-%m-%d').date()
            if check_date <= today:
                return {
                    'success': False,
                    'error': 'Data deve ser no futuro'
                }
            
            # Buscar horários disponíveis via service
            available_slots = self.google_calendar_service.get_available_slots(
                date=date,
                days_ahead=1  # Apenas para a data específica
            )
            
            if not available_slots:
                return {
                    'success': False,
                    'error': 'Nenhum horário disponível encontrado'
                }
            
            # Filtrar horários por duração do serviço
            filtered_slots = self._filter_slots_by_duration(available_slots, duration_minutes, date)
            
            return {
                'success': True,
                'date': date,
                'duration_minutes': duration_minutes,
                'available_slots': filtered_slots,
                'total_slots': len(filtered_slots),
                'message': f'Encontrados {len(filtered_slots)} horários disponíveis para {duration_minutes} min'
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar horários disponíveis: {e}")
            return {
                'success': False,
                'error': f'Erro interno: {str(e)}'
            }
    
    @tool
    def schedule_meeting(self, date_time: str, duration_minutes: int, summary: str, 
                        email: str = None, name: str = None, company: str = None) -> Dict[str, Any]:
        """
        Agenda uma reunião no Google Calendar
        Args:
            date_time: Data e hora da reunião (ISO format)
            duration_minutes: Duração em minutos
            summary: Título da reunião
            email: Email do cliente (opcional)
            name: Nome do cliente (opcional)
            company: Nome da empresa (opcional)
        Returns:
            Dicionário com resultado do agendamento
        """
        try:
            logger.info(f"Agendando reunião: {summary} em {date_time} por {duration_minutes} min")
            
            # Validar campos obrigatórios usando regras
            required_fields = self.google_calendar_rules.get_required_fields(GoogleCalendarFlowType.SCHEDULE_MEETING.value)
            if not all([date_time, duration_minutes, summary]):
                return {
                    'success': False,
                    'error': f'Campos obrigatórios faltando: {required_fields}'
                }
            
            # Validar formato da data/hora
            try:
                meeting_time = datetime.fromisoformat(date_time.replace('Z', '+00:00'))
            except ValueError:
                return {
                    'success': False,
                    'error': 'Formato de data/hora inválido. Use ISO 8601'
                }
            
            # Validar duração
            validation_rules = self.google_calendar_rules.get_validation_rules(GoogleCalendarFlowType.SCHEDULE_MEETING.value)
            min_duration = validation_rules.get('min_duration', 15)
            max_duration = validation_rules.get('max_duration', 480)
            
            if duration_minutes < min_duration or duration_minutes > max_duration:
                return {
                    'success': False,
                    'error': f'Duração deve estar entre {min_duration} e {max_duration} minutos'
                }
            
            # Verificar se a data/hora é no futuro
            now = datetime.now()
            if meeting_time <= now:
                return {
                    'success': False,
                    'error': 'Data e hora devem ser no futuro'
                }
            
            # Validar título
            if not summary or len(summary.strip()) == 0:
                return {
                    'success': False,
                    'error': 'Título da reunião é obrigatório'
                }
            
            # Agendar reunião via service
            result = self.google_calendar_service.schedule_meeting(
                email=email or '',
                name=name or 'Cliente',
                company=company or 'Empresa',
                date_time=date_time,
                duration_minutes=duration_minutes
            )
            
            if not result.get('success'):
                return {
                    'success': False,
                    'error': f'Erro ao agendar reunião: {result.get("message", "Erro desconhecido")}'
                }
            
            return {
                'success': True,
                'event_id': result.get('event_id'),
                'link': result.get('link'),
                'message': result.get('message'),
                'details': {
                    'summary': summary,
                    'date_time': date_time,
                    'duration_minutes': duration_minutes,
                    'client_name': name,
                    'client_email': email,
                    'company': company
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao agendar reunião: {e}")
            return {
                'success': False,
                'error': f'Erro interno: {str(e)}'
            }
    
    @tool
    def get_events_for_period(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Lista eventos em um período específico
        Args:
            start_date: Data de início (YYYY-MM-DD)
            end_date: Data de fim (YYYY-MM-DD)
        Returns:
            Dicionário com lista de eventos
        """
        try:
            logger.info(f"Buscando eventos de {start_date} até {end_date}")
            
            # Validar campos obrigatórios usando regras
            required_fields = self.google_calendar_rules.get_required_fields(GoogleCalendarFlowType.GET_EVENTS.value)
            if not start_date or not end_date:
                return {
                    'success': False,
                    'error': f'Campos obrigatórios faltando: {required_fields}'
                }
            
            # Validar formato das datas
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                return {
                    'success': False,
                    'error': 'Formato de data inválido. Use YYYY-MM-DD'
                }
            
            # Validar que data de fim é após data de início
            if end_dt <= start_dt:
                return {
                    'success': False,
                    'error': 'Data de fim deve ser após data de início'
                }
            
            # Buscar eventos via service
            events = self.google_calendar_service.list_events(start_date, end_date)
            
            if not events:
                return {
                    'success': True,
                    'start_date': start_date,
                    'end_date': end_date,
                    'events': [],
                    'total_events': 0,
                    'message': 'Nenhum evento encontrado no período'
                }
            
            # Processar e formatar dados dos eventos
            processed_events = self._process_events_data(events)
            
            return {
                'success': True,
                'start_date': start_date,
                'end_date': end_date,
                'events': processed_events,
                'total_events': len(processed_events),
                'message': f'Encontrados {len(processed_events)} eventos no período'
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar eventos: {e}")
            return {
                'success': False,
                'error': f'Erro interno: {str(e)}'
            }
    
    @tool
    def create_custom_event(self, summary: str, start: str, end: str, 
                           description: str = None, location: str = None) -> Dict[str, Any]:
        """
        Cria um evento customizado no Google Calendar
        Args:
            summary: Título do evento
            start: Data/hora de início (ISO format)
            end: Data/hora de fim (ISO format)
            description: Descrição do evento (opcional)
            location: Local do evento (opcional)
        Returns:
            Dicionário com resultado da criação
        """
        try:
            logger.info(f"Criando evento customizado: {summary}")
            
            # Validar campos obrigatórios usando regras
            required_fields = self.google_calendar_rules.get_required_fields(GoogleCalendarFlowType.CREATE_EVENT.value)
            if not all([summary, start, end]):
                return {
                    'success': False,
                    'error': f'Campos obrigatórios faltando: {required_fields}'
                }
            
            # Validar formato das datas
            try:
                start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
            except ValueError:
                return {
                    'success': False,
                    'error': 'Formato de data/hora inválido. Use ISO 8601'
                }
            
            # Validar que data de fim é após data de início
            if end_dt <= start_dt:
                return {
                    'success': False,
                    'error': 'Data/hora de fim deve ser após data/hora de início'
                }
            
            # Validar título
            if not summary or len(summary.strip()) == 0:
                return {
                    'success': False,
                    'error': 'Título do evento é obrigatório'
                }
            
            # Preparar dados do evento
            event_data = {
                'summary': summary,
                'start': {
                    'dateTime': start,
                    'timeZone': self.google_calendar_rules.get_default_timezone()
                },
                'end': {
                    'dateTime': end,
                    'timeZone': self.google_calendar_rules.get_default_timezone()
                }
            }
            
            if description:
                event_data['description'] = description
            if location:
                event_data['location'] = location
            
            # Criar evento via service
            result = self.google_calendar_service.create_event(event_data)
            
            if not result.get('success'):
                return {
                    'success': False,
                    'error': f'Erro ao criar evento: {result.get("message", "Erro desconhecido")}'
                }
            
            return {
                'success': True,
                'event_id': result.get('id'),
                'link': result.get('link'),
                'message': result.get('message'),
                'details': {
                    'summary': summary,
                    'start': start,
                    'end': end,
                    'description': description,
                    'location': location
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao criar evento: {e}")
            return {
                'success': False,
                'error': f'Erro interno: {str(e)}'
            }
    
    @tool
    def delete_event(self, event_id: str) -> Dict[str, Any]:
        """
        Remove um evento do Google Calendar
        Args:
            event_id: ID do evento a ser removido
        Returns:
            Dicionário com resultado da remoção
        """
        try:
            logger.info(f"Removendo evento: {event_id}")
            
            # Validar campos obrigatórios usando regras
            required_fields = self.google_calendar_rules.get_required_fields(GoogleCalendarFlowType.DELETE_EVENT.value)
            if not event_id:
                return {
                    'success': False,
                    'error': f'Campos obrigatórios faltando: {required_fields}'
                }
            
            # Validar ID do evento
            if not event_id or len(event_id.strip()) == 0:
                return {
                    'success': False,
                    'error': 'ID do evento é obrigatório'
                }
            
            # Remover evento via service
            success = self.google_calendar_service.delete_event(event_id)
            
            if not success:
                return {
                    'success': False,
                    'error': 'Erro ao remover evento'
                }
            
            return {
                'success': True,
                'event_id': event_id,
                'message': 'Evento removido com sucesso'
            }
            
        except Exception as e:
            logger.error(f"Erro ao remover evento: {e}")
            return {
                'success': False,
                'error': f'Erro interno: {str(e)}'
            }
    
    # ====================
    # MÉTODOS AUXILIARES DE PROCESSAMENTO
    # ====================
    
    def _filter_slots_by_duration(self, available_slots: List[Dict[str, Any]], 
                                 duration_minutes: int, date: str) -> List[Dict[str, Any]]:
        """Filtra slots disponíveis por duração do serviço"""
        try:
            filtered_slots = []
            
            # Obter regras de validação
            validation_rules = self.google_calendar_rules.get_validation_rules(GoogleCalendarFlowType.CHECK_AVAILABILITY.value)
            slot_duration = validation_rules.get('min_duration', 15)  # Usar duração mínima como base
            
            # Calcular slots necessários
            required_slots = max(1, duration_minutes // slot_duration)
            
            # Filtrar slots que têm tempo suficiente
            for slot in available_slots:
                slot_time = slot.get('time', '')
                if slot_time:
                    # Verificar se há slots consecutivos suficientes
                    if self._has_consecutive_slots(available_slots, slot_time, required_slots, slot_duration):
                        filtered_slots.append({
                            'time': slot_time,
                            'date': date,
                            'duration_minutes': duration_minutes,
                            'formatted': slot.get('formatted', ''),
                            'datetime': slot.get('datetime', '')
                        })
            
            return filtered_slots
            
        except Exception as e:
            logger.error(f"Erro ao filtrar slots por duração: {e}")
            return available_slots  # Fallback: retorna todos os slots
    
    def _has_consecutive_slots(self, all_slots: List[Dict[str, Any]], start_time: str, 
                              required_slots: int, slot_duration: int) -> bool:
        """Verifica se há slots consecutivos suficientes"""
        try:
            if required_slots <= 1:
                return True
            
            # Converter horário de início para minutos
            start_minutes = self._time_to_minutes(start_time)
            
            # Verificar se há slots consecutivos
            for i in range(required_slots):
                expected_time = start_minutes + (i * slot_duration)
                expected_time_str = self._minutes_to_time(expected_time)
                
                # Verificar se o slot esperado está disponível
                slot_available = any(
                    slot.get('time') == expected_time_str 
                    for slot in all_slots
                )
                
                if not slot_available:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao verificar slots consecutivos: {e}")
            return False
    
    def _time_to_minutes(self, time_str: str) -> int:
        """Converte horário (HH:MM) para minutos"""
        try:
            hours, minutes = map(int, time_str.split(':'))
            return hours * 60 + minutes
        except Exception:
            return 0
    
    def _minutes_to_time(self, minutes: int) -> str:
        """Converte minutos para horário (HH:MM)"""
        try:
            hours = minutes // 60
            mins = minutes % 60
            return f"{hours:02d}:{mins:02d}"
        except Exception:
            return "00:00"
    
    def _process_events_data(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Processa dados dos eventos"""
        try:
            processed = []
            
            for event in events:
                # Extrair informações básicas
                event_id = event.get('id', '')
                summary = event.get('summary', 'Sem título')
                
                # Processar data/hora de início
                start_info = event.get('start', {})
                start_time = start_info.get('dateTime') or start_info.get('date', '')
                
                # Processar data/hora de fim
                end_info = event.get('end', {})
                end_time = end_info.get('dateTime') or end_info.get('date', '')
                
                # Processar participantes
                attendees = event.get('attendees', [])
                attendee_emails = [att.get('email', '') for att in attendees if att.get('email')]
                
                processed.append({
                    'id': event_id,
                    'summary': summary,
                    'start_time': start_time,
                    'end_time': end_time,
                    'attendees': attendee_emails,
                    'description': event.get('description', ''),
                    'location': event.get('location', ''),
                    'link': event.get('htmlLink', '')
                })
            
            return processed
            
        except Exception as e:
            logger.error(f"Erro ao processar dados dos eventos: {e}")
            return []
