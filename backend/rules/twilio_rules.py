from typing import Dict, List, Any
from enum import Enum

class TwilioFlowType(Enum):
    """Tipos de fluxos disponíveis no Twilio"""
    SEND_MESSAGE = "send_message"
    RECEIVE_MESSAGE = "receive_message"
    GET_MESSAGES = "get_messages"
    CREATE_WEBHOOK = "create_webhook"
    VALIDATE_PHONE = "validate_phone"

class TwilioRules:
    """
    Regras estáticas para integração com Twilio API
    Contém APENAS configurações, regras e validações estáticas
    """
    
    def __init__(self):
        """Inicializa as regras do Twilio"""
        pass
    
    def get_api_rules(self) -> Dict[str, Any]:
        """
        Retorna regras gerais da API Twilio
        Returns:
            Dicionário com regras da API
        """
        return {
            "api_type": "TWILIO",
            "api_name": "Twilio",
            "email_required": False,
            "waid_required": True,
            "reservation_flow": "twilio",
            "confirmation_message": "Mensagem enviada via Twilio!",
            "missing_fields_message": "Faltam informações para enviar a mensagem via Twilio",
            "base_endpoints": {
                "messages": "/2010-04-01/Accounts/{account_sid}/Messages.json",
                "webhooks": "/2010-04-01/Accounts/{account_sid}/IncomingPhoneNumbers/{phone_number_sid}/SmsUrl.json"
            },
            "required_config": [
                "twilio_account_sid",
                "twilio_auth_token",
                "twilio_phone_number"
            ],
            "supported_operations": [
                "GET", "POST"
            ]
        }
    
    def get_required_fields(self, flow_type: str) -> List[str]:
        """
        Retorna campos obrigatórios para cada tipo de fluxo
        Args:
            flow_type: Tipo do fluxo (TwilioFlowType)
        Returns:
            Lista de campos obrigatórios
        """
        required_fields = {
            TwilioFlowType.SEND_MESSAGE.value: [
                "to", "from_", "body"
            ],
            TwilioFlowType.RECEIVE_MESSAGE.value: [
                "from", "body", "message_sid"
            ],
            TwilioFlowType.GET_MESSAGES.value: [
                "account_sid"
            ],
            TwilioFlowType.CREATE_WEBHOOK.value: [
                "phone_number_sid", "webhook_url"
            ],
            TwilioFlowType.VALIDATE_PHONE.value: [
                "phone_number"
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
            TwilioFlowType.SEND_MESSAGE.value: {
                "to_validation": "valid_phone_number",
                "from_validation": "valid_twilio_number",
                "body_validation": "non_empty_string",
                "body_length_validation": "max_1600_characters"
            },
            TwilioFlowType.RECEIVE_MESSAGE.value: {
                "from_validation": "valid_phone_number",
                "body_validation": "non_empty_string",
                "message_sid_validation": "valid_sid_format"
            },
            TwilioFlowType.GET_MESSAGES.value: {
                "account_sid_validation": "valid_sid_format"
            },
            TwilioFlowType.CREATE_WEBHOOK.value: {
                "phone_number_sid_validation": "valid_sid_format",
                "webhook_url_validation": "valid_url_format"
            },
            TwilioFlowType.VALIDATE_PHONE.value: {
                "phone_number_validation": "valid_phone_format"
            }
        }
        
        return validation_rules.get(flow_type, {})
    
    def get_available_flows(self) -> List[Dict[str, Any]]:
        """
        Retorna todos os fluxos disponíveis no Twilio
        Returns:
            Lista de fluxos com suas configurações
        """
        return [
            {
                "flow_type": TwilioFlowType.SEND_MESSAGE.value,
                "description": "Enviar mensagem SMS via Twilio",
                "required_fields": self.get_required_fields(TwilioFlowType.SEND_MESSAGE.value),
                "validation_rules": self.get_validation_rules(TwilioFlowType.SEND_MESSAGE.value)
            },
            {
                "flow_type": TwilioFlowType.RECEIVE_MESSAGE.value,
                "description": "Receber mensagem SMS via Twilio",
                "required_fields": self.get_required_fields(TwilioFlowType.RECEIVE_MESSAGE.value),
                "validation_rules": self.get_validation_rules(TwilioFlowType.RECEIVE_MESSAGE.value)
            },
            {
                "flow_type": TwilioFlowType.GET_MESSAGES.value,
                "description": "Listar mensagens enviadas/recebidas",
                "required_fields": self.get_required_fields(TwilioFlowType.GET_MESSAGES.value),
                "validation_rules": self.get_validation_rules(TwilioFlowType.GET_MESSAGES.value)
            },
            {
                "flow_type": TwilioFlowType.CREATE_WEBHOOK.value,
                "description": "Configurar webhook para receber mensagens",
                "required_fields": self.get_required_fields(TwilioFlowType.CREATE_WEBHOOK.value),
                "validation_rules": self.get_validation_rules(TwilioFlowType.CREATE_WEBHOOK.value)
            },
            {
                "flow_type": TwilioFlowType.VALIDATE_PHONE.value,
                "description": "Validar formato de número de telefone",
                "required_fields": self.get_required_fields(TwilioFlowType.VALIDATE_PHONE.value),
                "validation_rules": self.get_validation_rules(TwilioFlowType.VALIDATE_PHONE.value)
            }
        ]
    
    # MÉTODOS DE COMPATIBILIDADE MIGRADOS DO api_rules_engine.py
    
    def get_message_formatting_rules(self) -> Dict[str, Any]:
        """Retorna regras de formatação de mensagens para Twilio"""
        return {
            "max_length": 1600,
            "encoding": "UTF-8",
            "allowed_characters": "all_unicode",
            "media_support": True,
            "media_types": ["image/jpeg", "image/png", "image/gif", "audio/mp3", "video/mp4"]
        }
    
    def get_phone_validation_rules(self) -> Dict[str, Any]:
        """Retorna regras de validação de telefone para Twilio"""
        return {
            "supported_countries": ["BR", "US", "CA", "MX", "AR", "CL", "CO", "PE"],
            "format_patterns": {
                "BR": r"^\+55\s?\d{2}\s?\d{4,5}\s?\d{4}$",
                "US": r"^\+1\s?\d{3}\s?\d{3}\s?\d{4}$",
                "CA": r"^\+1\s?\d{3}\s?\d{3}\s?\d{4}$"
            },
            "default_country": "BR"
        }
    
    def get_rate_limiting_rules(self) -> Dict[str, Any]:
        """Retorna regras de limitação de taxa para Twilio"""
        return {
            "requests_per_second": 10,
            "requests_per_minute": 600,
            "requests_per_hour": 36000,
            "concurrent_requests": 100
        }
    
    def get_error_handling_rules(self) -> Dict[str, Any]:
        """Retorna regras de tratamento de erro para Twilio"""
        return {
            "retry_attempts": 3,
            "retry_delay": 1000,  # milissegundos
            "backoff_multiplier": 2,
            "max_retry_delay": 10000,  # milissegundos
            "fatal_errors": ["21211", "21214", "21608"]  # Códigos de erro fatais
        }
    
    def get_webhook_configuration_rules(self) -> Dict[str, Any]:
        """Retorna regras de configuração de webhook para Twilio"""
        return {
            "supported_methods": ["GET", "POST"],
            "required_headers": ["X-Twilio-Signature"],
            "signature_validation": True,
            "timeout": 30,  # segundos
            "retry_on_failure": True
        }
    
    def get_message_templates(self) -> Dict[str, Any]:
        """Retorna templates de mensagem para Twilio"""
        return {
            "confirmation": "✅ Sua reserva foi confirmada para {data} às {horario}",
            "reminder": "⏰ Lembrete: Sua consulta é hoje às {horario}",
            "cancellation": "❌ Sua reserva para {data} foi cancelada",
            "reschedule": "🔄 Sua consulta foi reagendada para {nova_data} às {novo_horario}",
            "welcome": "👋 Olá! Como posso ajudar você hoje?",
            "error": "❌ Desculpe, ocorreu um erro. Tente novamente."
        }
    
    def get_media_handling_rules(self) -> Dict[str, Any]:
        """Retorna regras de manipulação de mídia para Twilio"""
        return {
            "max_file_size": 16 * 1024 * 1024,  # 16MB
            "supported_formats": {
                "images": ["jpeg", "jpg", "png", "gif"],
                "audio": ["mp3", "wav", "ogg"],
                "video": ["mp4", "avi", "mov"]
            },
            "compression": True,
            "quality_settings": {
                "images": "high",
                "audio": "medium",
                "video": "low"
            }
        }
    
    def get_delivery_status_rules(self) -> Dict[str, Any]:
        """Retorna regras de status de entrega para Twilio"""
        return {
            "status_codes": {
                "queued": "Mensagem na fila para envio",
                "failed": "Falha no envio",
                "sent": "Mensagem enviada com sucesso",
                "delivered": "Mensagem entregue",
                "undelivered": "Mensagem não entregue"
            },
            "webhook_events": ["sent", "delivered", "failed", "undelivered"],
            "status_update_webhook": True
        }
    
    def get_phone_number_rules(self) -> Dict[str, Any]:
        """Retorna regras de números de telefone para Twilio"""
        return {
            "number_types": ["local", "toll-free", "mobile"],
            "capabilities": {
                "SMS": True,
                "MMS": True,
                "Voice": False,
                "Fax": False
            },
            "geographic_restrictions": {
                "BR": ["São Paulo", "Rio de Janeiro", "Minas Gerais"],
                "US": ["California", "New York", "Texas"]
            }
        }
    
    def get_compliance_rules(self) -> Dict[str, Any]:
        """Retorna regras de conformidade para Twilio"""
        return {
            "gdpr_compliance": True,
            "data_retention": 30,  # dias
            "opt_out_handling": True,
            "spam_prevention": True,
            "content_filtering": True,
            "reporting_requirements": {
                "monthly_reports": True,
                "compliance_audits": True
            }
        }
