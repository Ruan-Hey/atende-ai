#!/usr/bin/env python3
"""
Tools para chamar APIs externas automaticamente
"""

import requests
import json
import logging
from typing import Dict, Any, Optional
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class APITools:
    """Ferramentas para chamar APIs externas"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AtendeAI-APITools/1.0',
            'Content-Type': 'application/json'
        })
    
    def call_api(self, api_name: str, endpoint_path: str, method: str, config: dict, **kwargs) -> str:
        """Chama uma API externa com os parâmetros fornecidos"""
        try:
            # Configurar headers de autenticação
            self._setup_auth(config)
            
            # Construir URL
            base_url = config.get('base_url') or config.get('url_base') or config.get('url')
            # Fallbacks por API conhecida
            if (not base_url) and ('trinks' in api_name.lower() or 'trinks' in str(config).lower()):
                base_url = 'https://api.trinks.com/v1'
            # Garantir esquema
            if base_url and not base_url.startswith('http'):
                base_url = f"https://{base_url.lstrip('/')}"
            
            url = urljoin(base_url, endpoint_path)
            
            # Preparar dados da requisição
            headers = self._prepare_headers(config)
            data = self._prepare_data(kwargs, method)
            
            # Fazer a requisição
            response = self._make_request(method, url, headers, data)
            
            # Processar resposta
            return self._process_response(response, api_name, endpoint_path)
            
        except Exception as e:
            logger.error(f"Erro ao chamar API {api_name} {endpoint_path}: {e}")
            return f"Erro ao chamar API {api_name}: {str(e)}"
    
    def _setup_auth(self, config: dict):
        """Configura autenticação baseada no tipo"""
        auth_type = config.get('auth_type', 'api_key')
        
        if auth_type == 'api_key':
            api_key = config.get('api_key')
            if api_key:
                self.session.headers.update({
                    'Authorization': f'Bearer {api_key}',
                    'X-API-Key': api_key
                })
        
        elif auth_type == 'basic':
            username = config.get('username')
            password = config.get('password')
            if username and password:
                import base64
                credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
                self.session.headers.update({
                    'Authorization': f'Basic {credentials}'
                })
        
        elif auth_type == 'bearer':
            token = config.get('bearer_token')
            if token:
                self.session.headers.update({
                    'Authorization': f'Bearer {token}'
                })
    
    def _prepare_headers(self, config: dict) -> dict:
        """Prepara headers da requisição"""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Adicionar headers customizados
        custom_headers = config.get('headers', {})
        headers.update(custom_headers)
        
        return headers
    
    def _prepare_data(self, kwargs: dict, method: str) -> Optional[dict]:
        """Prepara dados da requisição"""
        if method.upper() in ['POST', 'PUT', 'PATCH']:
            # Filtrar dados válidos
            valid_data = {}
            for key, value in kwargs.items():
                if value is not None and value != '':
                    valid_data[key] = value
            
            return valid_data if valid_data else None
        
        return None
    
    def _make_request(self, method: str, url: str, headers: dict, data: Optional[dict]) -> requests.Response:
        """Faz a requisição HTTP"""
        method = method.upper()
        
        if method == 'GET':
            return self.session.get(url, headers=headers, timeout=30)
        elif method == 'POST':
            return self.session.post(url, headers=headers, json=data, timeout=30)
        elif method == 'PUT':
            return self.session.put(url, headers=headers, json=data, timeout=30)
        elif method == 'DELETE':
            return self.session.delete(url, headers=headers, timeout=30)
        elif method == 'PATCH':
            return self.session.patch(url, headers=headers, json=data, timeout=30)
        else:
            raise ValueError(f"Método HTTP não suportado: {method}")
    
    def _process_response(self, response: requests.Response, api_name: str, endpoint_path: str) -> str:
        """Processa a resposta da API"""
        try:
            if response.status_code >= 200 and response.status_code < 300:
                # Sucesso
                try:
                    data = response.json()
                    return f"Sucesso na operação {api_name} {endpoint_path}: {json.dumps(data, indent=2)}"
                except:
                    return f"Sucesso na operação {api_name} {endpoint_path}: {response.text}"
            
            elif response.status_code == 401:
                return f"Erro de autenticação na API {api_name}. Verifique as credenciais."
            
            elif response.status_code == 404:
                return f"Endpoint não encontrado na API {api_name}: {endpoint_path}"
            
            elif response.status_code >= 400 and response.status_code < 500:
                return f"Erro do cliente na API {api_name}: {response.status_code} - {response.text}"
            
            elif response.status_code >= 500:
                return f"Erro do servidor na API {api_name}: {response.status_code} - {response.text}"
            
            else:
                return f"Resposta inesperada da API {api_name}: {response.status_code} - {response.text}"
                
        except Exception as e:
            logger.error(f"Erro ao processar resposta da API {api_name}: {e}")
            return f"Erro ao processar resposta da API {api_name}: {str(e)}"
    
    def validate_required_fields(self, endpoint_info: dict, provided_fields: dict) -> tuple[bool, list]:
        """Valida se todos os campos obrigatórios foram fornecidos"""
        required_fields = []
        
        # Extrair campos obrigatórios do endpoint
        for param in endpoint_info.get('parameters', []):
            if param.get('required', False):
                required_fields.append(param['name'])
        
        # Verificar request body obrigatório
        request_body = endpoint_info.get('request_body', {})
        if request_body and request_body.get('required', False):
            content = request_body.get('content', {})
            for media_type, schema_info in content.items():
                if 'application/json' in media_type:
                    schema = schema_info.get('schema', {})
                    required = schema.get('required', [])
                    required_fields.extend(required)
        
        # Verificar campos fornecidos
        missing_fields = []
        for field in required_fields:
            if field not in provided_fields or provided_fields[field] is None:
                missing_fields.append(field)
        
        is_valid = len(missing_fields) == 0
        return is_valid, missing_fields 