from typing import Dict, List, Any
from enum import Enum

class GoogleSheetsFlowType(Enum):
    """Tipos de fluxos disponíveis no Google Sheets"""
    READ_DATA = "read_data"
    WRITE_DATA = "write_data"
    UPDATE_DATA = "update_data"
    SEARCH_DATA = "search_data"
    GET_SHEETS = "get_sheets"
    CREATE_SHEET = "create_sheet"

class GoogleSheetsRules:
    """
    Regras estáticas para integração com Google Sheets API
    Contém APENAS configurações, regras e validações estáticas
    """
    
    def __init__(self):
        """Inicializa as regras do Google Sheets"""
        pass
    
    def get_api_rules(self) -> Dict[str, Any]:
        """
        Retorna regras gerais da API Google Sheets
        Returns:
            Dicionário com regras da API
        """
        return {
            "api_type": "GOOGLE_SHEETS",
            "api_name": "Google Sheets",
            "email_required": False,
            "waid_required": True,
            "reservation_flow": "sheets",
            "confirmation_message": "Reserva confirmada no Google Sheets!",
            "missing_fields_message": "Faltam informações para completar a reserva no Google Sheets",
            "search_by_waid": True,
            "waid_column": "Telefone",
            "base_endpoints": {
                "spreadsheets": "/spreadsheets/{spreadsheet_id}",
                "sheets": "/spreadsheets/{spreadsheet_id}/sheets",
                "values": "/spreadsheets/{spreadsheet_id}/values/{range}"
            },
            "required_config": [
                "google_sheets_id",
                "google_sheets_client_id",
                "google_sheets_client_secret"
            ],
            "supported_operations": [
                "GET", "POST", "PUT", "DELETE"
            ]
        }
    
    def get_required_fields(self, flow_type: str) -> List[str]:
        """
        Retorna campos obrigatórios para cada tipo de fluxo
        Args:
            flow_type: Tipo do fluxo (GoogleSheetsFlowType)
        Returns:
            Lista de campos obrigatórios
        """
        required_fields = {
            GoogleSheetsFlowType.READ_DATA.value: [
                "spreadsheet_id", "range"
            ],
            GoogleSheetsFlowType.WRITE_DATA.value: [
                "spreadsheet_id", "range", "values"
            ],
            GoogleSheetsFlowType.UPDATE_DATA.value: [
                "spreadsheet_id", "range", "values"
            ],
            GoogleSheetsFlowType.SEARCH_DATA.value: [
                "spreadsheet_id", "search_term"
            ],
            GoogleSheetsFlowType.GET_SHEETS.value: [
                "spreadsheet_id"
            ],
            GoogleSheetsFlowType.CREATE_SHEET.value: [
                "spreadsheet_id", "sheet_name"
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
            GoogleSheetsFlowType.READ_DATA.value: {
                "spreadsheet_id_validation": "valid_id_format",
                "range_validation": "valid_range_format",
                "permission_validation": "read_access"
            },
            GoogleSheetsFlowType.WRITE_DATA.value: {
                "spreadsheet_id_validation": "valid_id_format",
                "range_validation": "valid_range_format",
                "permission_validation": "write_access",
                "data_validation": "non_empty_values"
            },
            GoogleSheetsFlowType.UPDATE_DATA.value: {
                "spreadsheet_id_validation": "valid_id_format",
                "range_validation": "valid_range_format",
                "permission_validation": "write_access",
                "data_validation": "non_empty_values"
            },
            GoogleSheetsFlowType.SEARCH_DATA.value: {
                "spreadsheet_id_validation": "valid_id_format",
                "search_term_validation": "non_empty_string"
            }
        }
        
        return validation_rules.get(flow_type, {})
    
    def get_available_flows(self) -> List[Dict[str, Any]]:
        """
        Retorna todos os fluxos disponíveis no Google Sheets
        Returns:
            Lista de fluxos com suas configurações
        """
        return [
            {
                "flow_type": GoogleSheetsFlowType.READ_DATA.value,
                "description": "Ler dados de uma planilha",
                "required_fields": self.get_required_fields(GoogleSheetsFlowType.READ_DATA.value),
                "validation_rules": self.get_validation_rules(GoogleSheetsFlowType.READ_DATA.value)
            },
            {
                "flow_type": GoogleSheetsFlowType.WRITE_DATA.value,
                "description": "Escrever dados em uma planilha",
                "required_fields": self.get_required_fields(GoogleSheetsFlowType.WRITE_DATA.value),
                "validation_rules": self.get_validation_rules(GoogleSheetsFlowType.WRITE_DATA.value)
            },
            {
                "flow_type": GoogleSheetsFlowType.UPDATE_DATA.value,
                "description": "Atualizar dados existentes em uma planilha",
                "required_fields": self.get_required_fields(GoogleSheetsFlowType.UPDATE_DATA.value),
                "validation_rules": self.get_validation_rules(GoogleSheetsFlowType.UPDATE_DATA.value)
            },
            {
                "flow_type": GoogleSheetsFlowType.SEARCH_DATA.value,
                "description": "Buscar dados em uma planilha",
                "required_fields": self.get_required_fields(GoogleSheetsFlowType.SEARCH_DATA.value),
                "validation_rules": self.get_validation_rules(GoogleSheetsFlowType.SEARCH_DATA.value)
            },
            {
                "flow_type": GoogleSheetsFlowType.GET_SHEETS.value,
                "description": "Listar abas de uma planilha",
                "required_fields": self.get_required_fields(GoogleSheetsFlowType.GET_SHEETS.value),
                "validation_rules": self.get_validation_rules(GoogleSheetsFlowType.GET_SHEETS.value)
            },
            {
                "flow_type": GoogleSheetsFlowType.CREATE_SHEET.value,
                "description": "Criar nova aba em uma planilha",
                "required_fields": self.get_required_fields(GoogleSheetsFlowType.CREATE_SHEET.value),
                "validation_rules": self.get_validation_rules(GoogleSheetsFlowType.CREATE_SHEET.value)
            }
        ]
    
    # MÉTODOS DE COMPATIBILIDADE MIGRADOS DO api_rules_engine.py
    
    def get_client_search_rules(self) -> Dict[str, Any]:
        """Retorna regras de busca de cliente para Google Sheets"""
        return {
            "api_endpoint": "/spreadsheets/{spreadsheet_id}/values/{range}",
            "search_fields": ["Telefone", "CPF", "Nome", "Email"],
            "create_if_not_found": True,
            "validation_rules": {
                "telefone": "brazilian_phone_format",
                "cpf": "brazilian_cpf_format",
                "nome": "non_empty_string"
            },
            "waid_column": "Telefone",
            "search_by_waid": True
        }
    
    def get_service_detection_rules(self) -> Dict[str, Any]:
        """Retorna regras de detecção de serviço para Google Sheets"""
        return {
            "api_endpoint": "/spreadsheets/{spreadsheet_id}/values/{range}",
            "search_fields": ["Serviço", "Categoria", "Descrição"],
            "match_strategies": ["keyword_match", "partial_match", "category_match"],
            "default_categories": ["Estética Facial", "Estética Corporal", "Tratamentos"]
        }
    
    def get_professional_search_rules(self) -> Dict[str, Any]:
        """Retorna regras de busca de profissionais para Google Sheets"""
        return {
            "api_endpoint": "/spreadsheets/{spreadsheet_id}/values/{range}",
            "search_fields": ["Nome", "Especialidade", "Disponibilidade"],
            "match_strategies": ["name_match", "specialty_match", "availability_match"],
            "filter_by_service": True
        }
    
    def get_availability_check_rules(self) -> Dict[str, Any]:
        """Retorna regras de verificação de disponibilidade para Google Sheets"""
        return {
            "api_endpoint": "/spreadsheets/{spreadsheet_id}/values/{range}",
            "required_fields": ["data"],
            "optional_fields": ["profissional", "servico"],
            "slot_duration": 30,
            "business_hours": self.get_business_hours(),
            "advance_booking": self.get_advance_booking_hours()
        }
    
    def get_reservation_creation_rules(self) -> Dict[str, Any]:
        """Retorna regras de criação de reserva para Google Sheets"""
        return {
            "api_endpoint": "/spreadsheets/{spreadsheet_id}/values/{range}",
            "required_fields": ["data", "horario", "cliente_nome", "telefone"],
            "optional_fields": ["profissional", "servico", "observacoes"],
            "validation_rules": {
                "data": "future_date_only",
                "horario": "business_hours",
                "cliente_nome": "non_empty_string",
                "telefone": "brazilian_phone_format"
            }
        }
    
    def get_reservation_management_rules(self) -> Dict[str, Any]:
        """Retorna regras de gerenciamento de reserva para Google Sheets"""
        return {
            "api_endpoint": "/spreadsheets/{spreadsheet_id}/values/{range}",
            "operations": ["GET", "PUT", "DELETE"],
            "cancellation_policy": self.get_cancellation_policy(),
            "reschedule_rules": {
                "min_hours_before": 2,
                "max_days_ahead": 30
            }
        }
    
    def get_sheet_structure(self) -> Dict[str, Any]:
        """
        Retorna estrutura padrão das planilhas
        Returns:
            Dicionário com estrutura das planilhas
        """
        return {
            "reservas": {
                "columns": [
                    "Data", "Horário", "Cliente", "Telefone", "Profissional", 
                    "Serviço", "Status", "Observações", "Data_Criacao"
                ],
                "data_types": {
                    "Data": "date",
                    "Horário": "time",
                    "Cliente": "string",
                    "Telefone": "string",
                    "Profissional": "string",
                    "Serviço": "string",
                    "Status": "string",
                    "Observações": "string",
                    "Data_Criacao": "datetime"
                }
            },
            "clientes": {
                "columns": [
                    "Nome", "Telefone", "CPF", "Email", "Endereco", 
                    "Data_Cadastro", "Observacoes"
                ],
                "data_types": {
                    "Nome": "string",
                    "Telefone": "string",
                    "CPF": "string",
                    "Email": "string",
                    "Endereco": "string",
                    "Data_Cadastro": "datetime",
                    "Observacoes": "string"
                }
            },
            "profissionais": {
                "columns": [
                    "Nome", "Especialidade", "Telefone", "Email", 
                    "Disponibilidade", "Status"
                ],
                "data_types": {
                    "Nome": "string",
                    "Especialidade": "string",
                    "Telefone": "string",
                    "Email": "string",
                    "Disponibilidade": "string",
                    "Status": "string"
                }
            }
        }
    
    def get_business_hours(self) -> Dict[str, Any]:
        """
        Retorna horário de funcionamento padrão para Google Sheets
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
        Retorna duração padrão dos slots em minutos para Google Sheets
        Returns:
            Duração em minutos
        """
        return 30  # 30 minutos padrão para Google Sheets
    
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
        Retorna política de cancelamento para Google Sheets
        Returns:
            Dicionário com política de cancelamento
        """
        return {
            "min_hours_before": 24,  # 24 horas antes
            "cancellation_fee": 0,   # Sem taxa de cancelamento
            "refund_policy": "full_refund"
        }
    
    def get_sheet_permissions(self) -> Dict[str, Any]:
        """
        Retorna configurações de permissões das planilhas
        Returns:
            Dicionário com configurações de permissões
        """
        return {
            "default_permissions": "view",
            "admin_permissions": "edit",
            "client_permissions": "view",
            "professional_permissions": "edit"
        }
