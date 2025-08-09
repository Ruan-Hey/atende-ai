from typing import Dict, Any
from integrations.google_calendar_service import GoogleCalendarService
from integrations.google_sheets_service import GoogleSheetsService
from tools.api_tools import APITools
import logging

logger = logging.getLogger(__name__)

class CalendarTools:
    """Ferramentas para operações de calendário e reservas"""
    
    def __init__(self):
        self.calendar_service = None
        self.sheets_service = None
        self.api_tools = APITools()
    
    def _get_calendar_service(self, empresa_config: Dict[str, Any]) -> GoogleCalendarService:
        """Inicializa serviço do Google Calendar"""
        if not self.calendar_service:
            # Criar configuração para o Google Calendar Service
            calendar_config = {
                'google_calendar_enabled': True,
                'google_calendar_client_id': empresa_config.get('google_calendar_client_id'),
                'google_calendar_client_secret': empresa_config.get('google_calendar_client_secret'),
                'google_calendar_refresh_token': empresa_config.get('google_calendar_refresh_token'),
                'google_calendar_service_account': empresa_config.get('google_calendar_service_account'),
                'google_calendar_project_id': empresa_config.get('google_calendar_project_id'),
                'google_calendar_client_email': empresa_config.get('google_calendar_client_email'),
                'google_calendar_calendar_id': empresa_config.get('google_calendar_calendar_id', 'primary'),
                'google_sheets_id': empresa_config.get('google_sheets_id')
            }
            
            self.calendar_service = GoogleCalendarService(calendar_config)
        return self.calendar_service
    
    def _get_sheets_service(self, empresa_config: Dict[str, Any]) -> GoogleSheetsService | None:
        """Inicializa serviço do Google Sheets somente se houver ID configurado"""
        if not empresa_config.get('google_sheets_id'):
            return None
        if not self.sheets_service:
            # Criar configuração para o Google Sheets Service
            sheets_config = {
                'google_sheets_id': empresa_config.get('google_sheets_id'),
                'google_calendar_client_id': empresa_config.get('google_calendar_client_id'),
                'google_calendar_client_secret': empresa_config.get('google_calendar_client_secret'),
                'google_calendar_refresh_token': empresa_config.get('google_calendar_refresh_token')
            }
            
            try:
                self.sheets_service = GoogleSheetsService(sheets_config)
            except Exception as e:
                logger.warning(f"Sheets desabilitado ou não configurado corretamente: {e}")
                self.sheets_service = None
        return self.sheets_service
    
    def _find_calendar_api(self, empresa_config: Dict[str, Any]) -> tuple[str, dict]:
        """Encontra a primeira API de agenda disponível"""
        # Verificar Google Calendar primeiro
        if (empresa_config.get('google_calendar_client_id') and 
            empresa_config.get('google_calendar_client_secret')):
            return "Google Calendar", {
                'google_calendar_client_id': empresa_config.get('google_calendar_client_id'),
                'google_calendar_client_secret': empresa_config.get('google_calendar_client_secret'),
                'google_sheets_id': empresa_config.get('google_sheets_id')
            }
        
        # Verificar Trinks
        if empresa_config.get('trinks_enabled') and empresa_config.get('trinks_config'):
            return "Trinks", empresa_config.get('trinks_config', {})
        
        # Verificar outras APIs de agenda dinamicamente
        for key, value in empresa_config.items():
            if key.endswith('_enabled') and value is True:
                api_name = key.replace('_enabled', '').replace('_', ' ').title()
                config_key = f"{key.replace('_enabled', '')}_config"
                config = empresa_config.get(config_key, {})
                
                # Verificar se é uma API de agenda (por nome ou configuração)
                if any(word in api_name.lower() for word in ['calendar', 'agenda', 'booking', 'schedule', 'trinks']):
                    return api_name, config
        
        return None, {}
    
    def verificar_disponibilidade(self, data: str, empresa_config: Dict[str, Any]) -> str:
        """Verifica disponibilidade usando qualquer API de agenda disponível"""
        try:
            # Encontrar API de agenda disponível
            api_name, api_config = self._find_calendar_api(empresa_config)
            
            if not api_name:
                return "Nenhuma API de agenda configurada para esta empresa. Não posso verificar disponibilidade."
            
            # Validar formato da data
            try:
                from datetime import datetime
                datetime.strptime(data, '%Y-%m-%d')
            except ValueError:
                return f"Formato de data inválido: {data}. Use o formato YYYY-MM-DD (ex: 2024-01-15)"
            
            # Usar API específica ou genérica
            if api_name == "Google Calendar":
                return self._verificar_google_calendar(data, empresa_config)
            elif api_name == "Trinks":
                return self._verificar_trinks(data, api_config)
            else:
                return self._verificar_api_generica(api_name, data, api_config)
            
        except Exception as e:
            logger.error(f"Erro ao verificar disponibilidade: {e}")
            return f"Erro ao verificar disponibilidade para {data}: {str(e)}"
    
    def _verificar_google_calendar(self, data: str, empresa_config: Dict[str, Any]) -> str:
        """Verifica disponibilidade no Google Calendar"""
        try:
            calendar_service = self._get_calendar_service(empresa_config)
            slots = calendar_service.get_available_slots(data)
            
            # Logar slots para diagnóstico
            try:
                import logging
                logging.getLogger(__name__).info(f"Calendar slots for {data}: {slots}")
            except Exception:
                pass
            
            if not slots:
                return f"Não há horários disponíveis para {data}. Tente outra data."
            
            slots_info = "\n".join([f"- {slot}" for slot in slots[:10]])
            return f"Horários disponíveis no Google Calendar para {data}:\n{slots_info}"
            
        except Exception as e:
            logger.error(f"Erro ao verificar Google Calendar: {e}")
            return f"Erro ao verificar Google Calendar para {data}: {str(e)}"
    
    def _verificar_trinks(self, data: str, config: Dict[str, Any]) -> str:
        """Verifica disponibilidade na API Trinks"""
        try:
            # Chamar endpoint de disponibilidade da Trinks
            result = self.api_tools.call_api(
                api_name="Trinks",
                endpoint_path="/api/availability",
                method="GET",
                config=config,
                date=data
            )
            
            return f"Verificação Trinks para {data}: {result}"
            
        except Exception as e:
            logger.error(f"Erro ao verificar Trinks: {e}")
            return f"Erro ao verificar Trinks para {data}: {str(e)}"
    
    def _verificar_api_generica(self, api_name: str, data: str, config: Dict[str, Any]) -> str:
        """Verifica disponibilidade em API genérica"""
        try:
            # Tentar endpoints comuns de agenda
            endpoints_to_try = [
                "/availability",
                "/slots",
                "/calendar/availability",
                "/booking/available",
                "/schedule/available"
            ]
            
            for endpoint in endpoints_to_try:
                try:
                    result = self.api_tools.call_api(
                        api_name=api_name,
                        endpoint_path=endpoint,
                        method="GET",
                        config=config,
                        date=data
                    )
                    
                    if "erro" not in result.lower() and "error" not in result.lower():
                        return f"Verificação {api_name} para {data}: {result}"
                        
                except Exception:
                    continue
            
            return f"Não foi possível verificar disponibilidade na {api_name} para {data}"
            
        except Exception as e:
            logger.error(f"Erro ao verificar {api_name}: {e}")
            return f"Erro ao verificar {api_name} para {data}: {str(e)}"
    
    def fazer_reserva(self, data: str, hora: str, cliente: str, empresa_config: Dict[str, Any]) -> str:
        """Faz reserva usando qualquer API de agenda disponível"""
        try:
            # Encontrar API de agenda disponível
            api_name, api_config = self._find_calendar_api(empresa_config)
            
            if not api_name:
                return "❌ Nenhuma API de agenda configurada para esta empresa. Não posso fazer reservas."
            
            # Validar formato da data
            try:
                from datetime import datetime
                datetime.strptime(data, '%Y-%m-%d')
            except ValueError:
                return f"❌ Formato de data inválido: {data}. Use o formato YYYY-MM-DD (ex: 2024-01-15)"
            
            # Validar formato da hora
            try:
                datetime.strptime(hora, '%H:%M')
            except ValueError:
                return f"❌ Formato de hora inválido: {hora}. Use o formato HH:MM (ex: 14:30)"
            
            # Validar cliente
            if not cliente or cliente.strip() == '':
                return "❌ Nome do cliente é obrigatório para fazer a reserva."
            
            # Usar API específica ou genérica
            if api_name == "Google Calendar":
                return self._fazer_reserva_google_calendar(data, hora, cliente, empresa_config)
            elif api_name == "Trinks":
                return self._fazer_reserva_trinks(data, hora, cliente, api_config)
            else:
                return self._fazer_reserva_generica(api_name, data, hora, cliente, api_config)
            
        except Exception as e:
            logger.error(f"Erro ao fazer reserva: {e}")
            return f"❌ Erro ao fazer reserva: {str(e)}"
    
    def _fazer_reserva_google_calendar(self, data: str, hora: str, cliente: str, empresa_config: Dict[str, Any]) -> str:
        """Faz reserva no Google Calendar"""
        try:
            calendar_service = self._get_calendar_service(empresa_config)
            sheets_service = self._get_sheets_service(empresa_config)
            
            # 1. Criar evento no Google Calendar (sem enviar convite)
            date_time = f"{data}T{hora}:00"
            result = calendar_service.schedule_meeting(
                email="",  # Não enviar email
                name=cliente,
                company=empresa_config.get('nome', 'Empresa'),
                date_time=date_time,
                duration_minutes=60
            )
            
            if not result.get('success'):
                return f"❌ Erro ao criar evento no Google Calendar: {result.get('message')}"
            
            # 2. Registrar no Google Sheets (se configurado)
            try:
                if sheets_service:
                    sheets_service.add_reservation(
                        data=data,
                        hora=hora,
                        cliente=cliente,
                        empresa=empresa_config.get('nome', 'Empresa')
                    )
            except Exception as e:
                logger.warning(f"Erro ao registrar no Google Sheets: {e}")
            
            return f"✅ Evento criado no Google Calendar!\nData: {data}\nHora: {hora}\nCliente: {cliente}\nID do evento: {result.get('event_id')}"
            
        except Exception as e:
            logger.error(f"Erro ao fazer reserva no Google Calendar: {e}")
            return f"❌ Erro ao fazer reserva no Google Calendar: {str(e)}"
    
    def _fazer_reserva_trinks(self, data: str, hora: str, cliente: str, config: Dict[str, Any]) -> str:
        """Faz reserva na API Trinks"""
        try:
            # Chamar endpoint de reserva da Trinks
            result = self.api_tools.call_api(
                api_name="Trinks",
                endpoint_path="/api/bookings",
                method="POST",
                config=config,
                date=data,
                time=hora,
                customer=cliente
            )
            
            return f"✅ Reserva confirmada na Trinks!\nData: {data}\nHora: {hora}\nCliente: {cliente}\nResultado: {result}"
            
        except Exception as e:
            logger.error(f"Erro ao fazer reserva na Trinks: {e}")
            return f"❌ Erro ao fazer reserva na Trinks: {str(e)}"
    
    def _fazer_reserva_generica(self, api_name: str, data: str, hora: str, cliente: str, config: Dict[str, Any]) -> str:
        """Faz reserva em API genérica"""
        try:
            # Tentar endpoints comuns de reserva
            endpoints_to_try = [
                "/bookings",
                "/reservations",
                "/appointments",
                "/schedule",
                "/calendar/book"
            ]
            
            for endpoint in endpoints_to_try:
                try:
                    result = self.api_tools.call_api(
                        api_name=api_name,
                        endpoint_path=endpoint,
                        method="POST",
                        config=config,
                        date=data,
                        time=hora,
                        customer=cliente
                    )
                    
                    if "erro" not in result.lower() and "error" not in result.lower():
                        return f"✅ Reserva confirmada na {api_name}!\nData: {data}\nHora: {hora}\nCliente: {cliente}\nResultado: {result}"
                        
                except Exception:
                    continue
            
            return f"❌ Não foi possível fazer reserva na {api_name} para {data} {hora}"
            
        except Exception as e:
            logger.error(f"Erro ao fazer reserva na {api_name}: {e}")
            return f"❌ Erro ao fazer reserva na {api_name}: {str(e)}"
    
    def cancelar_reserva(self, event_id: str, empresa_config: Dict[str, Any]) -> str:
        """Cancela reserva usando qualquer API de agenda disponível"""
        try:
            # Encontrar API de agenda disponível
            api_name, api_config = self._find_calendar_api(empresa_config)
            
            if not api_name:
                return "❌ Nenhuma API de agenda configurada para esta empresa."
            
            if api_name == "Google Calendar":
                calendar_service = self._get_calendar_service(empresa_config)
                calendar_service.delete_event(event_id)
                return f"✅ Reserva cancelada com sucesso no Google Calendar (ID: {event_id})"
            else:
                # Tentar cancelar em API genérica
                result = self.api_tools.call_api(
                    api_name=api_name,
                    endpoint_path=f"/bookings/{event_id}",
                    method="DELETE",
                    config=api_config
                )
                return f"✅ Reserva cancelada com sucesso na {api_name} (ID: {event_id})"
            
        except Exception as e:
            logger.error(f"Erro ao cancelar reserva: {e}")
            return f"❌ Erro ao cancelar reserva: {str(e)}" 