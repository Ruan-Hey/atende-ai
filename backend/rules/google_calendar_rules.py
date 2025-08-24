from typing import Dict, List, Any
from enum import Enum

class GoogleCalendarFlowType(Enum):
    """Tipos de fluxos disponíveis no Google Calendar"""
    CHECK_AVAILABILITY = "check_availability"
    BOOK_APPOINTMENT = "book_appointment"
    GET_CALENDARS = "get_calendars"
    CREATE_EVENT = "create_event"
    UPDATE_EVENT = "update_event"
    DELETE_EVENT = "delete_event"

class GoogleCalendarRules:
    """
    Regras estáticas para integração com Google Calendar API
    Contém APENAS configurações, regras e validações estáticas
    """
    
    def __init__(self):
        """Inicializa as regras do Google Calendar"""
        pass
    
    def get_api_rules(self) -> Dict[str, Any]:
        """
        Retorna regras gerais da API Google Calendar
        Returns:
            Dicionário com regras da API
        """
        return {
            "api_type": "GOOGLE_CALENDAR",
            "api_name": "Google Calendar",
            "email_required": True,
            "waid_required": False,
            "reservation_flow": "calendar",
            "confirmation_message": "Reserva confirmada no Google Calendar!",
            "missing_fields_message": "Faltam informações para completar a reserva no Google Calendar",
            "base_endpoints": {
                "calendars": "/users/me/calendarList",
                "events": "/calendars/{calendar_id}/events",
                "free_busy": "/freeBusy"
            },
            "required_config": [
                "google_calendar_client_id",
                "google_calendar_client_secret",
                "google_calendar_refresh_token"
            ],
            "supported_operations": [
                "GET", "POST", "PUT", "DELETE"
            ]
        }
    
    def get_required_fields(self, flow_type: str) -> List[str]:
        """
        Retorna campos obrigatórios para cada tipo de fluxo
        Args:
            flow_type: Tipo do fluxo (GoogleCalendarFlowType)
        Returns:
            Lista de campos obrigatórios
        """
        required_fields = {
            GoogleCalendarFlowType.CHECK_AVAILABILITY.value: [
                "calendar_id", "date", "time_min", "time_max"
            ],
            GoogleCalendarFlowType.BOOK_APPOINTMENT.value: [
                "calendar_id", "summary", "start_time", "end_time"
            ],
            GoogleCalendarFlowType.GET_CALENDARS.value: [],
            GoogleCalendarFlowType.CREATE_EVENT.value: [
                "calendar_id", "summary", "start_time", "end_time"
            ],
            GoogleCalendarFlowType.UPDATE_EVENT.value: [
                "calendar_id", "event_id", "summary", "start_time", "end_time"
            ],
            GoogleCalendarFlowType.DELETE_EVENT.value: [
                "calendar_id", "event_id"
            ]
        }
        
        return required_fields.get(flow_type, [])
    
    def get_validation_rules(self, flow_type: str) -> Dict[str, Any]:
        """
        Retorna regras de validação para cada fluxo
        Args:
            flow_type: Tipo do fluxo
        Returns:
            Dicionário com regras de validação
        """
        validation_rules = {
            GoogleCalendarFlowType.CHECK_AVAILABILITY.value: {
                "date_format": "YYYY-MM-DD",
                "time_format": "HH:MM",
                "date_validation": "future_date_only",
                "time_validation": "business_hours"
            },
            GoogleCalendarFlowType.BOOK_APPOINTMENT.value: {
                "date_format": "YYYY-MM-DD",
                "time_format": "HH:MM",
                "date_validation": "future_date_only",
                "time_validation": "business_hours",
                "duration_validation": "minimum_30_minutes"
            },
            GoogleCalendarFlowType.CREATE_EVENT.value: {
                "date_format": "YYYY-MM-DD",
                "time_format": "HH:MM",
                "date_validation": "future_date_only",
                "time_validation": "business_hours"
            }
        }
        
        return validation_rules.get(flow_type, {})
    
    def get_available_flows(self) -> List[Dict[str, Any]]:
        """
        Retorna todos os fluxos disponíveis no Google Calendar
        Returns:
            Lista de fluxos com suas configurações
        """
        return [
            {
                "flow_type": GoogleCalendarFlowType.CHECK_AVAILABILITY.value,
                "description": "Verificar disponibilidade no calendário",
                "required_fields": self.get_required_fields(GoogleCalendarFlowType.CHECK_AVAILABILITY.value),
                "validation_rules": self.get_validation_rules(GoogleCalendarFlowType.CHECK_AVAILABILITY.value)
            },
            {
                "flow_type": GoogleCalendarFlowType.BOOK_APPOINTMENT.value,
                "description": "Agendar evento no calendário",
                "required_fields": self.get_required_fields(GoogleCalendarFlowType.BOOK_APPOINTMENT.value),
                "validation_rules": self.get_validation_rules(GoogleCalendarFlowType.BOOK_APPOINTMENT.value)
            },
            {
                "flow_type": GoogleCalendarFlowType.GET_CALENDARS.value,
                "description": "Listar calendários disponíveis",
                "required_fields": self.get_required_fields(GoogleCalendarFlowType.GET_CALENDARS.value),
                "validation_rules": self.get_validation_rules(GoogleCalendarFlowType.GET_CALENDARS.value)
            },
            {
                "flow_type": GoogleCalendarFlowType.CREATE_EVENT.value,
                "description": "Criar novo evento",
                "required_fields": self.get_required_fields(GoogleCalendarFlowType.CREATE_EVENT.value),
                "validation_rules": self.get_validation_rules(GoogleCalendarFlowType.CREATE_EVENT.value)
            },
            {
                "flow_type": GoogleCalendarFlowType.UPDATE_EVENT.value,
                "description": "Atualizar evento existente",
                "required_fields": self.get_required_fields(GoogleCalendarFlowType.UPDATE_EVENT.value),
                "validation_rules": self.get_validation_rules(GoogleCalendarFlowType.UPDATE_EVENT.value)
            },
            {
                "flow_type": GoogleCalendarFlowType.DELETE_EVENT.value,
                "description": "Excluir evento",
                "required_fields": self.get_required_fields(GoogleCalendarFlowType.DELETE_EVENT.value),
                "validation_rules": self.get_validation_rules(GoogleCalendarFlowType.DELETE_EVENT.value)
            }
        ]
    
    # MÉTODOS DE COMPATIBILIDADE MIGRADOS DO api_rules_engine.py
    
    def get_availability_check_rules(self) -> Dict[str, Any]:
        """Retorna regras de verificação de disponibilidade para Google Calendar"""
        return {
            "api_endpoint": "/calendars/{calendar_id}/events",
            "required_fields": ["data"],
            "optional_fields": ["horario_inicio", "horario_fim"],
            "slot_duration": 30,
            "business_hours": self.get_business_hours(),
            "advance_booking": self.get_advance_booking_hours()
        }
    
    def get_reservation_creation_rules(self) -> Dict[str, Any]:
        """Retorna regras de criação de reserva para Google Calendar"""
        return {
            "api_endpoint": "/calendars/{calendar_id}/events",
            "required_fields": ["summary", "start_time", "end_time"],
            "optional_fields": ["description", "location", "attendees"],
            "validation_rules": {
                "data": "future_date_only",
                "horario": "business_hours",
                "duracao_minima": 30
            }
        }
    
    def get_reservation_management_rules(self) -> Dict[str, Any]:
        """Retorna regras de gerenciamento de reserva para Google Calendar"""
        return {
            "api_endpoint": "/calendars/{calendar_id}/events",
            "operations": ["GET", "PUT", "DELETE"],
            "cancellation_policy": self.get_cancellation_policy(),
            "reschedule_rules": {
                "min_hours_before": 2,
                "max_days_ahead": 30
            }
        }
    
    def get_business_hours(self) -> Dict[str, Any]:
        """
        Retorna horário de funcionamento padrão para Google Calendar
        Returns:
            Dicionário com horários de funcionamento
        """
        return {
            "monday": {"start": "09:00", "end": "18:00", "active": True},
            "tuesday": {"start": "09:00", "end": "18:00", "active": True},
            "wednesday": {"start": "09:00", "end": "18:00", "active": True},
            "thursday": {"start": "09:00", "end": "18:00", "active": True},
            "friday": {"start": "09:00", "end": "18:00", "active": True},
            "saturday": {"start": "09:00", "end": "17:00", "active": True},
            "sunday": {"start": "00:00", "end": "00:00", "active": False}
        }
    
    def get_slot_duration(self) -> int:
        """
        Retorna duração padrão dos slots em minutos para Google Calendar
        Returns:
            Duração em minutos
        """
        return 30  # 30 minutos padrão para Google Calendar
    
    def get_advance_booking_hours(self) -> int:
        """
        Retorna quantas horas de antecedência são necessárias para agendamento
        Returns:
            Horas de antecedência
        """
        return 2  # 2 horas de antecedência
    
    def get_max_booking_days_ahead(self) -> int:
        """
        Retorna quantos dias à frente é possível agendar
        Returns:
            Dias à frente
        """
        return 30  # 30 dias à frente
    
    def get_cancellation_policy(self) -> Dict[str, Any]:
        """
        Retorna política de cancelamento para Google Calendar
        Returns:
            Dicionário com política de cancelamento
        """
        return {
            "min_hours_before": 24,  # 24 horas antes
            "cancellation_fee": 0,   # Sem taxa de cancelamento
            "refund_policy": "full_refund"
        }
    
    def get_calendar_settings(self) -> Dict[str, Any]:
        """
        Retorna configurações específicas do calendário
        Returns:
            Dicionário com configurações
        """
        return {
            "default_calendar": "primary",
            "timezone": "America/Sao_Paulo",
            "working_hours": self.get_business_hours(),
            "slot_duration": self.get_slot_duration(),
            "buffer_time": 15  # 15 minutos de buffer entre eventos
        }
