from typing import Dict, Any
from integrations.google_calendar_service import GoogleCalendarService
from integrations.google_sheets_service import GoogleSheetsService
import logging

logger = logging.getLogger(__name__)

class CalendarTools:
    """Ferramentas para operações de calendário e reservas"""
    
    def __init__(self):
        self.calendar_service = None
        self.sheets_service = None
    
    def _get_calendar_service(self, empresa_config: Dict[str, Any]) -> GoogleCalendarService:
        """Inicializa serviço do Google Calendar"""
        if not self.calendar_service:
            # Criar configuração para o Google Calendar Service
            calendar_config = {
                'google_calendar_enabled': True,
                'google_calendar_client_id': empresa_config.get('google_calendar_client_id'),
                'google_calendar_client_secret': empresa_config.get('google_calendar_client_secret'),
                'google_calendar_refresh_token': empresa_config.get('google_calendar_refresh_token'),
                'google_sheets_id': empresa_config.get('google_sheets_id')
            }
            
            self.calendar_service = GoogleCalendarService(calendar_config)
        return self.calendar_service
    
    def _get_sheets_service(self, empresa_config: Dict[str, Any]) -> GoogleSheetsService:
        """Inicializa serviço do Google Sheets"""
        if not self.sheets_service:
            # Criar configuração para o Google Sheets Service
            sheets_config = {
                'google_sheets_id': empresa_config.get('google_sheets_id'),
                'google_calendar_client_id': empresa_config.get('google_calendar_client_id'),
                'google_calendar_client_secret': empresa_config.get('google_calendar_client_secret'),
                'google_calendar_refresh_token': empresa_config.get('google_calendar_refresh_token')
            }
            
            self.sheets_service = GoogleSheetsService(sheets_config)
        return self.sheets_service
    
    def verificar_disponibilidade(self, data: str, empresa_config: Dict[str, Any]) -> str:
        """Verifica disponibilidade no Google Calendar"""
        try:
            # Usar API real do Google Calendar
            calendar_service = self._get_calendar_service(empresa_config)
            
            # Verificar se a empresa tem Google Calendar configurado
            if not empresa_config.get('google_sheets_id'):
                return f"Google Calendar não configurado para esta empresa"
            
            slots = calendar_service.get_available_slots(data)
            
            if not slots:
                return f"Não há horários disponíveis para {data}"
            
            slots_info = "\n".join([f"- {slot}" for slot in slots[:5]])  # Primeiros 5 slots
            return f"Horários disponíveis para {data}:\n{slots_info}"
            
        except Exception as e:
            logger.error(f"Erro ao verificar disponibilidade: {e}")
            return f"Erro ao verificar disponibilidade para {data}: {str(e)}"
    
    def fazer_reserva(self, data: str, hora: str, cliente: str, empresa_config: Dict[str, Any]) -> str:
        """Faz reserva no Google Calendar e registra no Google Sheets"""
        try:
            calendar_service = self._get_calendar_service(empresa_config)
            sheets_service = self._get_sheets_service(empresa_config)
            
            # 1. Criar evento no Google Calendar
            event_id = calendar_service.create_event(
                date_time=f"{data} {hora}",
                description=f"Reserva para {cliente}",
                attendees=[cliente]
            )
            
            # 2. Registrar no Google Sheets
            sheets_service.add_reservation(
                data=data,
                hora=hora,
                cliente=cliente,
                empresa=empresa_config.get('nome', 'Empresa')
            )
            
            return f"✅ Reserva confirmada!\nData: {data}\nHora: {hora}\nCliente: {cliente}\nID do evento: {event_id}"
            
        except Exception as e:
            logger.error(f"Erro ao fazer reserva: {e}")
            return f"❌ Erro ao fazer reserva: {str(e)}"
    
    def cancelar_reserva(self, event_id: str, empresa_config: Dict[str, Any]) -> str:
        """Cancela reserva no Google Calendar"""
        try:
            calendar_service = self._get_calendar_service(empresa_config)
            calendar_service.delete_event(event_id)
            
            return f"✅ Reserva cancelada com sucesso (ID: {event_id})"
            
        except Exception as e:
            logger.error(f"Erro ao cancelar reserva: {e}")
            return f"❌ Erro ao cancelar reserva: {str(e)}" 