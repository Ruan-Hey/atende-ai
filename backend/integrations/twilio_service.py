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
            
            # Adicionar parâmetros se fornecidos (ContentVariables é um JSON ÚNICO)
            if parameters:
                data['ContentVariables'] = json.dumps(parameters)
            
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

    def fetch_template_text(self, template_sid: str) -> Dict[str, Any]:
        """Busca o conteúdo do template (ContentSid) na Twilio Content API e retorna o corpo de WhatsApp.
        Retorna {success, text}.
        """
        try:
            # Twilio Content API (v1)
            url = f"https://content.twilio.com/v1/Content/{template_sid}"
            resp = requests.get(url, auth=(self.account_sid, self.auth_token))
            if resp.status_code != 200:
                return {'success': False, 'error': f'status {resp.status_code}'}
            data = resp.json() if resp.content else {}
            # Extração robusta: procurar primeiro campo de texto em qualquer nível
            def _find_text(node):
                if isinstance(node, dict):
                    # campos típicos
                    for key in ('text', 'body'):
                        val = node.get(key)
                        if isinstance(val, str) and val.strip():
                            return val
                    for v in node.values():
                        found = _find_text(v)
                        if found:
                            return found
                elif isinstance(node, list):
                    for item in node:
                        found = _find_text(item)
                        if found:
                            return found
                return None

            types_obj = data.get('types') if isinstance(data, dict) else None
            text = _find_text(types_obj if types_obj is not None else data)
            return {'success': True, 'text': text or ''}
        except Exception as e:
            logger.warning(f"Falha ao buscar template text: {e}")
            return {'success': False, 'error': str(e)}