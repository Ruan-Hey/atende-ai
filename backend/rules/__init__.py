"""
Módulo de regras para integração com APIs externas
Contém APENAS configurações, regras e validações estáticas
"""

from .trinks_rules import TrinksRules, TrinksFlowType
from .google_calendar_rules import GoogleCalendarRules, GoogleCalendarFlowType
from .google_sheets_rules import GoogleSheetsRules, GoogleSheetsFlowType
from .twilio_rules import TwilioRules, TwilioFlowType

# Mapeamento de tipos de API para suas respectivas regras
API_RULES_MAPPING = {
    "TRINKS": TrinksRules,
    "GOOGLE_CALENDAR": GoogleCalendarRules,
    "GOOGLE_SHEETS": GoogleSheetsRules,
    "TWILIO": TwilioRules
}

# Mapeamento de tipos de fluxo para suas respectivas regras
FLOW_TYPE_MAPPING = {
    "TRINKS": TrinksFlowType,
    "GOOGLE_CALENDAR": GoogleCalendarFlowType,
    "GOOGLE_SHEETS": GoogleSheetsFlowType,
    "TWILIO": TwilioFlowType
}

def get_rules_class(api_type: str):
    """
    Retorna a classe de regras para um tipo de API específico
    Args:
        api_type: Tipo da API (TRINKS, GOOGLE_CALENDAR, etc.)
    Returns:
        Classe de regras correspondente
    """
    return API_RULES_MAPPING.get(api_type.upper())

def get_flow_type_class(api_type: str):
    """
    Retorna a classe de tipos de fluxo para um tipo de API específico
    Args:
        api_type: Tipo da API (TRINKS, GOOGLE_CALENDAR, etc.)
    Returns:
        Classe de tipos de fluxo correspondente
    """
    return FLOW_TYPE_MAPPING.get(api_type.upper())

def get_available_apis() -> list:
    """
    Retorna lista de APIs disponíveis
    Returns:
        Lista com nomes das APIs disponíveis
    """
    return list(API_RULES_MAPPING.keys())

def validate_api_type(api_type: str) -> bool:
    """
    Valida se um tipo de API é suportado
    Args:
        api_type: Tipo da API para validar
    Returns:
        True se suportado, False caso contrário
    """
    return api_type.upper() in API_RULES_MAPPING

__all__ = [
    "TrinksRules",
    "TrinksFlowType", 
    "GoogleCalendarRules",
    "GoogleCalendarFlowType",
    "GoogleSheetsRules",
    "GoogleSheetsFlowType",
    "TwilioRules",
    "TwilioFlowType",
    "API_RULES_MAPPING",
    "FLOW_TYPE_MAPPING",
    "get_rules_class",
    "get_flow_type_class",
    "get_available_apis",
    "validate_api_type"
]
