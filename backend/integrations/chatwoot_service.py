import requests
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ChatwootService:
    """Serviço para integração com Chatwoot"""
    
    def __init__(self, base_url: str, api_token: str, account_id: int, inbox_id: int = 2, origem: str = "atendeai"):
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.account_id = account_id
        self.inbox_id = inbox_id
        self.origem = origem
        self.headers = {
            'api_access_token': api_token,
            'Content-Type': 'application/json'
        }
    
    def create_contact(self, name: str, phone_number: str, identifier: str = None) -> Dict[str, Any]:
        """Cria ou atualiza um contato no Chatwoot, adicionando origem se necessário"""
        try:
            url = f"{self.base_url}/api/v1/accounts/{self.account_id}/contacts"
            # Buscar contato existente
            existing = self.find_contact_by_phone(phone_number)
            custom_attributes = {}
            if existing.get('success') and existing.get('data'):
                attrs = existing['data'].get('payload', {}).get('contact', {}).get('custom_attributes', {})
                origens = attrs.get('origem', '')
                origens_set = set([o.strip() for o in origens.split(',') if o.strip()]) if origens else set()
                if self.origem not in origens_set:
                    origens_set.add(self.origem)
                custom_attributes['origem'] = ','.join(sorted(origens_set))
            else:
                custom_attributes['origem'] = self.origem
            data = {
                'name': name,
                'phone_number': f"+{phone_number}",
                'identifier': identifier or f"whatsapp_{phone_number}",
                'custom_attributes': custom_attributes
            }
            response = requests.post(url, json=data, headers=self.headers)
            response.raise_for_status()
            result = response.json()
            logger.info(f"Contato criado/atualizado: {name}")
            return {
                'success': True,
                'contact_id': result.get('payload', {}).get('contact', {}).get('id'),
                'data': result
            }
        except Exception as e:
            logger.error(f"Erro ao criar contato: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def create_conversation(self, contact_id: int, source_id: str = None) -> Dict[str, Any]:
        """Cria uma nova conversa no Chatwoot usando inbox_id customizado"""
        try:
            url = f"{self.base_url}/api/v1/accounts/{self.account_id}/conversations"
            data = {
                'source_id': source_id or str(int(datetime.now().timestamp())),
                'inbox_id': self.inbox_id,
                'contact_id': contact_id,
                'custom_attributes': {
                    'origem': self.origem
                }
            }
            response = requests.post(url, json=data, headers=self.headers)
            response.raise_for_status()
            result = response.json()
            logger.info(f"Conversa criada: {result.get('id')}")
            return {
                'success': True,
                'conversation_id': result.get('id'),
                'data': result
            }
        except Exception as e:
            logger.error(f"Erro ao criar conversa: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_message(self, conversation_id: int, content: str, message_type: str = 'outgoing') -> Dict[str, Any]:
        """Envia uma mensagem para uma conversa"""
        try:
            url = f"{self.base_url}/api/v1/accounts/{self.account_id}/conversations/{conversation_id}/messages"
            
            data = {
                'content': content,
                'message_type': message_type
            }
            
            response = requests.post(url, json=data, headers=self.headers)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Mensagem enviada para conversa {conversation_id}")
            
            return {
                'success': True,
                'message_id': result.get('id'),
                'data': result
            }
            
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def find_contact_by_phone(self, phone_number: str) -> Dict[str, Any]:
        """Busca um contato pelo número de telefone"""
        try:
            url = f"{self.base_url}/api/v1/accounts/{self.account_id}/contacts/search"
            params = {
                'q': phone_number,
                'label': 'atendeai'
            }
            
            response = requests.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('meta', {}).get('count', 0) > 0:
                contact = result.get('payload', [])[0]
                return {
                    'success': True,
                    'contact': contact,
                    'found': True
                }
            else:
                return {
                    'success': True,
                    'found': False
                }
                
        except Exception as e:
            logger.error(f"Erro ao buscar contato: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_conversations_by_contact(self, contact_id: int) -> Dict[str, Any]:
        """Busca conversas de um contato específico"""
        try:
            url = f"{self.base_url}/api/v1/accounts/{self.account_id}/contacts/{contact_id}/conversations"
            params = {
                'status': 'all'
            }
            
            response = requests.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            
            result = response.json()
            
            return {
                'success': True,
                'conversations': result.get('payload', [])
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar conversas: {e}")
            return {
                'success': False,
                'error': str(e)
            } 