"""
Sistema de regras específicas para cada API
Define se email é obrigatório baseado na API ativa
"""

import logging
from typing import Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)

class APIType(Enum):
    """Tipos de APIs disponíveis"""
    GOOGLE_SHEETS = "Google Sheets"
    GOOGLE_CALENDAR = "Google Calendar"
    TRINKS = "Trinks"
    NONE = "Nenhuma"

class APIRulesEngine:
    """Motor de regras para APIs específicas"""
    
    def __init__(self):
        # Regras específicas para cada API
        self.api_rules = {
            APIType.GOOGLE_SHEETS: {
                "email_required": False,
                "waid_required": True,
                "reservation_flow": "sheets",
                "confirmation_message": "Reserva confirmada no Google Sheets!",
                "missing_fields_message": "Faltam informações para completar a reserva no Google Sheets"
            },
            APIType.GOOGLE_CALENDAR: {
                "email_required": True,
                "waid_required": False,
                "reservation_flow": "calendar",
                "confirmation_message": "Reserva confirmada no Google Calendar!",
                "missing_fields_message": "Faltam informações para completar a reserva no Google Calendar"
            },
            APIType.TRINKS: {
                "email_required": True,
                "waid_required": False,
                "reservation_flow": "trinks",
                "confirmation_message": "Reserva confirmada no Trinks!",
                "missing_fields_message": "Faltam informações para completar a reserva no Trinks"
            },
            APIType.NONE: {
                "email_required": False,
                "waid_required": False,
                "reservation_flow": "manual",
                "confirmation_message": "Reserva anotada! Entre em contato direto para confirmar.",
                "missing_fields_message": "Faltam informações para anotar a reserva"
            }
        }
    
    def detect_active_api(self, empresa_config: Dict[str, Any]) -> APIType:
        """Detecta qual API está ativa baseado na configuração"""
        try:
            # Verificar Google Sheets
            if (empresa_config.get('google_sheets_id') and 
                (empresa_config.get('google_sheets_client_id') or 
                 empresa_config.get('google_sheets_service_account'))):
                return APIType.GOOGLE_SHEETS
            
            # Verificar Google Calendar
            if (empresa_config.get('google_calendar_client_id') or 
                empresa_config.get('google_calendar_service_account')):
                return APIType.GOOGLE_CALENDAR
            
            # Verificar Trinks
            if empresa_config.get('trinks_enabled'):
                return APIType.TRINKS
            
            # Nenhuma API configurada
            return APIType.NONE
            
        except Exception as e:
            logger.error(f"Erro ao detectar API ativa: {e}")
            return APIType.NONE
    
    def get_api_rules(self, empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """Retorna as regras da API ativa"""
        api_type = self.detect_active_api(empresa_config)
        rules = self.api_rules[api_type].copy()
        rules['api_type'] = api_type
        rules['api_name'] = api_type.value
        
        logger.info(f"Regras da API ativa ({api_type.value}): {rules}")
        return rules
    
    def is_email_required(self, empresa_config: Dict[str, Any]) -> bool:
        """Verifica se email é obrigatório para a API ativa"""
        rules = self.get_api_rules(empresa_config)
        return rules.get('email_required', False)
    
    def is_waid_required(self, empresa_config: Dict[str, Any]) -> bool:
        """Verifica se WaId é obrigatório para a API ativa"""
        rules = self.get_api_rules(empresa_config)
        return rules.get('waid_required', False)
    
    def get_confirmation_message(self, empresa_config: Dict[str, Any]) -> str:
        """Retorna mensagem de confirmação específica da API"""
        rules = self.get_api_rules(empresa_config)
        return rules.get('confirmation_message', "Reserva confirmada!")
    
    def get_missing_fields_message(self, empresa_config: Dict[str, Any]) -> str:
        """Retorna mensagem de campos faltantes específica da API"""
        rules = self.get_api_rules(empresa_config)
        return rules.get('missing_fields_message', "Faltam informações para completar a reserva")
    
    def get_reservation_status(self, empresa_config: Dict[str, Any], 
                              reservation_context: Dict[str, Any]) -> str:
        """Determina o status da reserva baseado nas regras da API"""
        rules = self.get_api_rules(empresa_config)
        api_type = rules['api_type']
        
        # Campos obrigatórios baseados na API
        required_fields = ['cliente_nome', 'quantidade_pessoas', 'data_reserva', 'horario_reserva']
        
        if api_type == APIType.GOOGLE_SHEETS:
            required_fields.append('waid')
        elif api_type in [APIType.GOOGLE_CALENDAR, APIType.TRINKS]:
            if rules['email_required']:
                required_fields.append('email')
        
        # Verificar se todos os campos obrigatórios estão preenchidos
        missing_fields = [field for field in required_fields 
                         if not reservation_context.get(field)]
        
        if not missing_fields:
            return 'pronta_para_confirmar'
        else:
            return 'aguardando_info'
    
    def get_reservation_summary(self, empresa_config: Dict[str, Any], 
                               reservation_context: Dict[str, Any]) -> str:
        """Gera resumo da reserva baseado nas regras da API"""
        rules = self.get_api_rules(empresa_config)
        api_type = rules['api_type']
        
        # Informações já coletadas
        info_coletada = []
        if reservation_context.get('waid'):
            info_coletada.append(f"WaId: {reservation_context['waid']}")
        if reservation_context.get('cliente_nome'):
            info_coletada.append(f"Nome: {reservation_context['cliente_nome']}")
        if reservation_context.get('quantidade_pessoas'):
            info_coletada.append(f"Pessoas: {reservation_context['quantidade_pessoas']}")
        if reservation_context.get('data_reserva'):
            info_coletada.append(f"Data: {reservation_context['data_reserva']}")
        if reservation_context.get('horario_reserva'):
            info_coletada.append(f"Horário: {reservation_context['horario_reserva']}")
        if reservation_context.get('observacoes'):
            info_coletada.append(f"Observações: {reservation_context['observacoes']}")
        
        # Status baseado na API
        status = self.get_reservation_status(empresa_config, reservation_context)
        
        if status == 'pronta_para_confirmar':
            if api_type == APIType.GOOGLE_SHEETS:
                return f"✅ Reserva completa para Google Sheets! Todas as informações coletadas: {', '.join(info_coletada)}"
            elif api_type in [APIType.GOOGLE_CALENDAR, APIType.TRINKS]:
                if not reservation_context.get('email'):
                    return f"📧 Reserva quase completa! Falta apenas o email para confirmar no {api_type.value}: {', '.join(info_coletada)}"
                else:
                    return f"✅ Reserva completa para {api_type.value}! Todas as informações coletadas: {', '.join(info_coletada)}"
            else:
                return f"✅ Reserva anotada! Todas as informações coletadas: {', '.join(info_coletada)}"
        
        elif status == 'aguardando_info':
            if info_coletada:
                return f"📝 Informações já coletadas: {', '.join(info_coletada)}"
            else:
                return "📝 Nenhuma informação coletada ainda"
        
        return "Status desconhecido"

# Instância global do motor de regras
api_rules_engine = APIRulesEngine() 