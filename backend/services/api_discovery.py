#!/usr/bin/env python3
"""
Sistema de descoberta automática de APIs
"""

import requests
import json
import yaml
import re
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin, urlparse
import logging

logger = logging.getLogger(__name__)

class APIDiscovery:
    """Sistema para descobrir e gerar Tools automaticamente de APIs"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AtendeAI-APIDiscovery/1.0'
        })
    
    def discover_api(self, url_documentacao: str) -> Dict[str, Any]:
        """Descobre API a partir da URL da documentação"""
        try:
            # Tentar diferentes formatos de documentação
            discovery_methods = [
                self._try_openapi_spec,
                self._try_swagger_ui,
                self._try_rest_docs,
                self._try_manual_parse,
                self._try_readme_docs
            ]
            
            for method in discovery_methods:
                try:
                    result = method(url_documentacao)
                    if result:
                        logger.info(f"API descoberta usando {method.__name__}")
                        return result
                except Exception as e:
                    logger.warning(f"Método {method.__name__} falhou: {e}")
                    continue
            
            raise Exception("Não foi possível descobrir a API")
            
        except Exception as e:
            logger.error(f"Erro ao descobrir API: {e}")
            raise
    
    def _try_openapi_spec(self, url: str) -> Optional[Dict[str, Any]]:
        """Tenta descobrir via OpenAPI/Swagger spec"""
        try:
            # Tentar diferentes endpoints comuns
            spec_urls = [
                url,
                urljoin(url, '/swagger.json'),
                urljoin(url, '/openapi.json'),
                urljoin(url, '/api-docs'),
                urljoin(url, '/swagger/v1/swagger.json'),
                urljoin(url, '/v1/swagger.json')
            ]
            
            for spec_url in spec_urls:
                try:
                    response = self.session.get(spec_url, timeout=10)
                    if response.status_code == 200:
                        spec = response.json()
                        return self._parse_openapi_spec(spec, url)
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao tentar OpenAPI spec: {e}")
            return None
    
    def _parse_openapi_spec(self, spec: Dict[str, Any], base_url: str) -> Dict[str, Any]:
        """Parse OpenAPI spec e extrai informações"""
        try:
            api_info = {
                'nome': spec.get('info', {}).get('title', 'API Desconhecida'),
                'descricao': spec.get('info', {}).get('description', ''),
                'url_base': spec.get('servers', [{}])[0].get('url', base_url),
                'endpoints': [],
                'schemas': spec.get('components', {}).get('schemas', {})
            }
            
            # Extrair endpoints
            paths = spec.get('paths', {})
            for path, methods in paths.items():
                for method, details in methods.items():
                    if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                        endpoint = {
                            'path': path,
                            'method': method.upper(),
                            'summary': details.get('summary', ''),
                            'description': details.get('description', ''),
                            'operation_id': details.get('operationId', ''),
                            'parameters': details.get('parameters', []),
                            'request_body': details.get('requestBody', {}),
                            'responses': details.get('responses', {})
                        }
                        api_info['endpoints'].append(endpoint)
            
            return api_info
            
        except Exception as e:
            logger.error(f"Erro ao parse OpenAPI spec: {e}")
            raise
    
    def _try_swagger_ui(self, url: str) -> Optional[Dict[str, Any]]:
        """Tenta descobrir via Swagger UI"""
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                # Procurar por URLs de spec no HTML
                html = response.text
                spec_urls = re.findall(r'"(https?://[^"]*swagger[^"]*\.json)"', html)
                spec_urls.extend(re.findall(r'"(https?://[^"]*openapi[^"]*\.json)"', html))
                
                for spec_url in spec_urls:
                    try:
                        spec_response = self.session.get(spec_url, timeout=10)
                        if spec_response.status_code == 200:
                            spec = spec_response.json()
                            return self._parse_openapi_spec(spec, url)
                    except:
                        continue
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao tentar Swagger UI: {e}")
            return None
    
    def _try_rest_docs(self, url: str) -> Optional[Dict[str, Any]]:
        """Tenta descobrir via documentação REST genérica"""
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                # Procurar por padrões de endpoints
                html = response.text
                endpoints = re.findall(r'([A-Z]+)\s+([/][^\s]+)', html)
                
                if endpoints:
                    api_info = {
                        'nome': 'API REST',
                        'descricao': 'API descoberta via documentação REST',
                        'url_base': url,
                        'endpoints': []
                    }
                    
                    for method, path in endpoints:
                        endpoint = {
                            'path': path,
                            'method': method,
                            'summary': f'{method} {path}',
                            'description': '',
                            'operation_id': f'{method.lower()}_{path.replace("/", "_")}',
                            'parameters': [],
                            'request_body': {},
                            'responses': {}
                        }
                        api_info['endpoints'].append(endpoint)
                    
                    return api_info
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao tentar REST docs: {e}")
            return None
    
    def _try_manual_parse(self, url: str) -> Optional[Dict[str, Any]]:
        """Parse manual de documentação"""
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                # Tentar extrair informações básicas
                content = response.text.lower()
                
                api_info = {
                    'nome': 'API Manual',
                    'descricao': 'API descoberta via parse manual',
                    'url_base': url,
                    'endpoints': []
                }
                
                # Procurar por padrões de endpoints
                patterns = [
                    r'get\s+([/][^\s]+)',
                    r'post\s+([/][^\s]+)',
                    r'put\s+([/][^\s]+)',
                    r'delete\s+([/][^\s]+)'
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        method = pattern.split()[0].upper()
                        endpoint = {
                            'path': match,
                            'method': method,
                            'summary': f'{method} {match}',
                            'description': '',
                            'operation_id': f'{method.lower()}_{match.replace("/", "_")}',
                            'parameters': [],
                            'request_body': {},
                            'responses': {}
                        }
                        api_info['endpoints'].append(endpoint)
                
                if api_info['endpoints']:
                    return api_info
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao tentar parse manual: {e}")
            return None

    def _try_readme_docs(self, url: str) -> Optional[Dict[str, Any]]:
        """Tenta descobrir via documentação Readme.io e similares"""
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                html = response.text
                
                # Extrair informações da página
                api_info = {
                    'nome': 'API Readme',
                    'descricao': 'API descoberta via documentação Readme',
                    'url_base': url,
                    'endpoints': []
                }
                
                # Procurar por seções de API na documentação
                # Padrões comuns em documentações de API
                api_sections = re.findall(r'<h[1-6][^>]*>([^<]*api[^<]*)</h[1-6]>', html, re.IGNORECASE)
                endpoint_sections = re.findall(r'<h[1-6][^>]*>([^<]*endpoint[^<]*)</h[1-6]>', html, re.IGNORECASE)
                
                # Procurar por URLs de endpoints na documentação
                endpoint_urls = re.findall(r'https?://[^\s<>"]+/(api|v\d+)/[^\s<>"]+', html)
                
                # Procurar por métodos HTTP
                http_methods = re.findall(r'\b(GET|POST|PUT|DELETE|PATCH)\b', html, re.IGNORECASE)
                
                # Se encontrou seções de API, tentar extrair endpoints
                if api_sections or endpoint_sections:
                    # Procurar por padrões de endpoints na documentação
                    endpoint_patterns = [
                        r'([A-Z]+)\s+([/][^\s<>"]+)',
                        r'([A-Z]+)\s+([^\s<>"]+\.com[^\s<>"]*)',
                        r'([A-Z]+)\s+([^\s<>"]+\.io[^\s<>"]*)'
                    ]
                    
                    for pattern in endpoint_patterns:
                        matches = re.findall(pattern, html, re.IGNORECASE)
                        for method, path in matches:
                            if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                                endpoint = {
                                    'path': path,
                                    'method': method.upper(),
                                    'summary': f'{method.upper()} {path}',
                                    'description': f'Endpoint descoberto na documentação {url}',
                                    'operation_id': f'{method.lower()}_{path.replace("/", "_").replace(".", "_")}',
                                    'parameters': [],
                                    'request_body': {},
                                    'responses': {}
                                }
                                api_info['endpoints'].append(endpoint)
                
                # Se não encontrou endpoints específicos, criar endpoints genéricos baseados na documentação
                if not api_info['endpoints']:
                    # Endpoints comuns baseados no tipo de API
                    if 'agendamento' in html.lower() or 'appointment' in html.lower():
                        common_endpoints = [
                            ('GET', '/agendamentos'),
                            ('POST', '/agendamentos'),
                            ('GET', '/agendamentos/{id}'),
                            ('PUT', '/agendamentos/{id}'),
                            ('DELETE', '/agendamentos/{id}'),
                            ('GET', '/clientes'),
                            ('POST', '/clientes'),
                            ('GET', '/clientes/{id}'),
                            ('PUT', '/clientes/{id}'),
                            ('DELETE', '/clientes/{id}'),
                            ('GET', '/profissionais'),
                            ('GET', '/servicos'),
                            ('GET', '/estabelecimentos')
                        ]
                        
                        for method, path in common_endpoints:
                            endpoint = {
                                'path': path,
                                'method': method,
                                'summary': f'{method} {path}',
                                'description': f'Endpoint sugerido para API de agendamentos',
                                'operation_id': f'{method.lower()}_{path.replace("/", "_").replace("{", "").replace("}", "")}',
                                'parameters': [],
                                'request_body': {},
                                'responses': {}
                            }
                            api_info['endpoints'].append(endpoint)
                
                if api_info['endpoints']:
                    return api_info
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao tentar Readme docs: {e}")
            return None
    
    def generate_tools(self, api_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Gera Tools do LangChain a partir das informações da API"""
        tools = []
        
        for endpoint in api_info.get('endpoints', []):
            tool = {
                'name': endpoint['operation_id'],
                'description': endpoint.get('summary', endpoint.get('description', '')),
                'method': endpoint['method'],
                'path': endpoint['path'],
                'parameters': self._extract_parameters(endpoint),
                'required_fields': self._extract_required_fields(endpoint)
            }
            tools.append(tool)
        
        return tools
    
    def _extract_parameters(self, endpoint: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extrai parâmetros do endpoint"""
        parameters = []
        
        # Parâmetros de path
        for param in endpoint.get('parameters', []):
            if param.get('in') == 'path':
                parameters.append({
                    'name': param['name'],
                    'type': param.get('schema', {}).get('type', 'string'),
                    'required': param.get('required', False),
                    'description': param.get('description', '')
                })
        
        # Parâmetros de query
        for param in endpoint.get('parameters', []):
            if param.get('in') == 'query':
                parameters.append({
                    'name': param['name'],
                    'type': param.get('schema', {}).get('type', 'string'),
                    'required': param.get('required', False),
                    'description': param.get('description', '')
                })
        
        return parameters
    
    def _extract_required_fields(self, endpoint: Dict[str, Any]) -> List[str]:
        """Extrai campos obrigatórios do endpoint"""
        required_fields = []
        
        # Verificar request body
        request_body = endpoint.get('request_body', {})
        if request_body:
            content = request_body.get('content', {})
            for media_type, schema_info in content.items():
                if 'application/json' in media_type:
                    schema = schema_info.get('schema', {})
                    required = schema.get('required', [])
                    required_fields.extend(required)
        
        # Verificar parâmetros obrigatórios
        for param in endpoint.get('parameters', []):
            if param.get('required', False):
                required_fields.append(param['name'])
        
        return list(set(required_fields))  # Remove duplicatas 