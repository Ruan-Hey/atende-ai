import requests
import logging
from typing import Dict, Any
from urllib.parse import quote
import json

logger = logging.getLogger(__name__)

class TwilioService:
    """Serviço para integração com Twilio"""
    
    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
        self.base_url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}"
    
    def send_whatsapp_message(self, to_number: str, message: str) -> Dict[str, Any]:
        """Envia mensagem WhatsApp via Twilio"""
        try:
            # Formatar número para WhatsApp
            if not to_number.startswith('whatsapp:'):
                # Remover + se já existir para evitar duplicação
                clean_number = to_number.lstrip('+')
                to_number = f"whatsapp:+{clean_number}"
            
            from_number = f"whatsapp:{self.from_number}"
            
            url = f"{self.base_url}/Messages.json"
            
            data = {
                'To': to_number,
                'From': from_number,
                'Body': message
            }
            
            response = requests.post(
                url,
                data=data,
                auth=(self.account_sid, self.auth_token)
            )
            
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"Mensagem enviada via Twilio: {result.get('sid')}")
            
            return {
                'success': True,
                'message_sid': result.get('sid'),
                'status': result.get('status')
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao enviar mensagem via Twilio: {e}")
            return {
                'success': False,
                'error': str(e)
            }
        except Exception as e:
            logger.error(f"Erro inesperado ao enviar mensagem: {e}")
            return {
                'success': False,
                'error': 'Erro interno do servidor'
            }
    
    def send_whatsapp_template(self, to_number: str, template_sid: str, parameters: Dict[str, str] = None) -> Dict[str, Any]:
        """Envia template WhatsApp via Twilio"""
        try:
            if not to_number.startswith('whatsapp:'):
                # Remover + se já existir para evitar duplicação
                clean_number = to_number.lstrip('+')
                to_number = f"whatsapp:+{clean_number}"
            
            from_number = f"whatsapp:{self.from_number}"
            
            url = f"{self.base_url}/Messages.json"
            
            data = {
                'To': to_number,
                'From': from_number,
                'ContentSid': template_sid
            }
            
            # Adicionar parâmetros se fornecidos
            if parameters:
                for key, value in parameters.items():
                    data[f'ContentVariables'] = json.dumps({key: value})
            
            response = requests.post(
                url,
                data=data,
                auth=(self.account_sid, self.auth_token)
            )
            
            response.raise_for_status()
            result = response.json()
            
            return {
                'success': True,
                'message_sid': result.get('sid'),
                'status': result.get('status')
            }
            
        except Exception as e:
            logger.error(f"Erro ao enviar template via Twilio: {e}")
            return {
                'success': False,
                'error': str(e)
            } 