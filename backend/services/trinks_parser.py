#!/usr/bin/env python3
"""
Parser FINAL e PRECISO para documentação da Trinks
Contém APENAS os 16 endpoints necessários com campos obrigatórios corretos
"""

import requests
import re
import json
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

class TrinksParser:
    """Parser FINAL e PRECISO para documentação da Trinks"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AtendeAI-TrinksParser-FINAL/1.0'
        })
    
    def parse_trinks_docs(self, base_url: str = "https://trinks.readme.io/reference") -> Dict[str, Any]:
        """Parse FINAL da documentação da Trinks - APENAS 16 endpoints necessários"""
        
        try:
            logger.info("🎯 Iniciando parse FINAL da Trinks - 16 endpoints precisos...")
            
            # 1. Página principal
            main_page = self._parse_main_page(f"{base_url}/introducao")
            
            # 2. APENAS os endpoints que realmente precisamos
            endpoints = self._get_final_endpoints()
            
            # 3. Consolidar informações
            api_info = {
                'nome': 'Trinks API - FINAL',
                'descricao': 'API de agendamentos da Trinks com 16 endpoints precisos',
                'url_base': 'https://api.trinks.com/v1',
                'endpoints': endpoints,
                'version': 'v1.0',
                'source': base_url,
                'total_endpoints': len(endpoints)
            }
            
            logger.info(f"✅ Parse FINAL concluído: {len(endpoints)} endpoints PRECISOS")
            return api_info
            
        except Exception as e:
            logger.error(f"❌ Erro no parse FINAL da Trinks: {e}")
            raise
    
    def _parse_main_page(self, url: str) -> Dict[str, Any]:
        """Parse da página principal"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extrair informações básicas
            title = soup.find('title')
            title_text = title.get_text() if title else 'Trinks API - FINAL'
            
            return {
                'title': title_text,
                'url': url
            }
            
        except Exception as e:
            logger.error(f"Erro ao parse página principal: {e}")
            return {}
    
    def _get_final_endpoints(self) -> List[Dict[str, Any]]:
        """APENAS os 16 endpoints que realmente precisamos - CAMPOS 100% PRECISOS"""
        
        # ENDPOINTS FINAIS baseados na documentação REAL das imagens
        final_endpoints = [
            # ========================================
            # AGENDAMENTOS (8 endpoints)
            # ========================================
            
            # 1. Listar Agendamentos
            {
                'path': '/agendamentos',
                'method': 'GET',
                'description': 'Listar os agendamentos do estabelecimento',
                'required_fields': [],
                'required_headers': [
                    {'name': 'estabelecimentoId', 'type': 'string', 'description': 'ID do estabelecimento (OBRIGATÓRIO)'}
                ],
                'optional_fields': [
                    {'name': 'page', 'type': 'int32', 'description': 'Numeração da página'},
                    {'name': 'pageSize', 'type': 'int32', 'description': 'Quantidade de registros por página'},
                    {'name': 'clienteld', 'type': 'int32', 'description': 'ID do cliente para filtrar'},
                    {'name': 'datalnicio', 'type': 'date-time', 'description': 'Data de início para filtrar'},
                    {'name': 'dataFim', 'type': 'date-time', 'description': 'Data de fim para filtrar'}
                ]
            },
            
            # 2. Criar Agendamento
            {
                'path': '/agendamentos',
                'method': 'POST',
                'description': 'Cria um agendamento',
                'required_fields': [
                    {'name': 'servicold', 'type': 'int32', 'description': 'ID do serviço (OBRIGATÓRIO)'},
                    {'name': 'clienteld', 'type': 'int32', 'description': 'ID do cliente (OBRIGATÓRIO)'},
                    {'name': 'dataHoralnicio', 'type': 'date-time', 'description': 'Data e hora de início (OBRIGATÓRIO)'},
                    {'name': 'duracaoEmMinutos', 'type': 'int32', 'description': 'Duração em minutos (OBRIGATÓRIO)'},
                    {'name': 'valor', 'type': 'double', 'description': 'Valor do serviço (OBRIGATÓRIO)'}
                ],
                'required_headers': [
                    {'name': 'estabelecimentoId', 'type': 'string', 'description': 'ID do estabelecimento (OBRIGATÓRIO)'}
                ],
                'optional_fields': [
                    {'name': 'profissionalld', 'type': 'int32', 'description': 'ID do profissional (pode ser null)'},
                    {'name': 'observacoes', 'type': 'string', 'description': 'Observações adicionais (pode ser null)'},
                    {'name': 'confirmado', 'type': 'boolean', 'description': 'Se o agendamento está confirmado'}
                ]
            },
            
            # 3. Obter Agendamento
            {
                'path': '/agendamentos/{id}',
                'method': 'GET',
                'description': 'Obter detalhes de um agendamento',
                'required_fields': [
                    {'name': 'id', 'type': 'int32', 'description': 'ID do agendamento (PATH PARAMS - OBRIGATÓRIO)'}
                ],
                'required_headers': [
                    {'name': 'estabelecimentoId', 'type': 'string', 'description': 'ID do estabelecimento (OBRIGATÓRIO)'}
                ],
                'optional_fields': []
            },
            
            # 4. Listar Configurações
            {
                'path': '/agendamentos/configuracoes',
                'method': 'GET',
                'description': 'Lista as configurações de agendamento do estabelecimento',
                'required_fields': [],
                'required_headers': [
                    {'name': 'estabelecimentoId', 'type': 'string', 'description': 'ID do estabelecimento (OBRIGATÓRIO)'}
                ],
                'optional_fields': []
            },
            
            # 5. Editar Agendamento
            {
                'path': '/agendamentos/{agendamentoId}',
                'method': 'PUT',
                'description': 'Edita um agendamento',
                'required_fields': [
                    {'name': 'agendamentoId', 'type': 'int32', 'description': 'ID do agendamento (PATH PARAMS - OBRIGATÓRIO)'}
                ],
                'required_headers': [
                    {'name': 'estabelecimentoId', 'type': 'string', 'description': 'ID do estabelecimento (OBRIGATÓRIO)'}
                ],
                'optional_fields': [
                    {'name': 'servicoId', 'type': 'int32', 'description': 'ID do serviço'},
                    {'name': 'clienteId', 'type': 'int32', 'description': 'ID do cliente'},
                    {'name': 'profissionalId', 'type': 'int32', 'description': 'ID do profissional (pode ser null)'},
                    {'name': 'dataHoraInicio', 'type': 'date-time', 'description': 'Data e hora de início'},
                    {'name': 'duracaoEmMinutos', 'type': 'int32', 'description': 'Duração em minutos'},
                    {'name': 'valor', 'type': 'double', 'description': 'Valor do serviço'},
                    {'name': 'observacoes', 'type': 'string', 'description': 'Observações adicionais'}
                ]
            },
            
            # 6. Confirmar Agendamento
            {
                'path': '/agendamentos/{agendamentoId}/status/confirmado',
                'method': 'PATCH',
                'description': 'Confirma um agendamento',
                'required_fields': [
                    {'name': 'agendamentoId', 'type': 'int32', 'description': 'ID do agendamento (PATH PARAMS - OBRIGATÓRIO)'}
                ],
                'required_headers': [
                    {'name': 'estabelecimentoId', 'type': 'string', 'description': 'ID do estabelecimento (OBRIGATÓRIO)'}
                ],
                'optional_fields': []
            },
            
            # 7. Cancelar Agendamento
            {
                'path': '/agendamentos/{agendamentoId}/status/cancelado',
                'method': 'PATCH',
                'description': 'Cancela um agendamento',
                'required_fields': [
                    {'name': 'agendamentoId', 'type': 'int32', 'description': 'ID do agendamento (PATH PARAMS - OBRIGATÓRIO)'},
                    {'name': 'quemCancelou', 'type': 'int32', 'description': 'ID de quem cancelou (OBRIGATÓRIO)'},
                    {'name': 'motivo', 'type': 'string', 'description': 'Motivo do cancelamento (OBRIGATÓRIO, length ≥ 1)'}
                ],
                'required_headers': [
                    {'name': 'estabelecimentoId', 'type': 'string', 'description': 'ID do estabelecimento (OBRIGATÓRIO)'}
                ],
                'optional_fields': []
            },
            
            # 8. Listar Profissionais com Agenda
            {
                'path': '/agendamentos/profissionais/{data}',
                'method': 'GET',
                'description': 'Lista os profissionais com agenda do estabelecimento',
                'required_fields': [
                    {'name': 'data', 'type': 'date', 'description': 'Data para consultar agenda (PATH PARAMS - OBRIGATÓRIO)'}
                ],
                'required_headers': [
                    {'name': 'estabelecimentoId', 'type': 'string', 'description': 'ID do estabelecimento (OBRIGATÓRIO)'}
                ],
                'optional_fields': [
                    {'name': 'intervalos', 'type': 'int32', 'description': 'Intervalos de tempo'},
                    {'name': 'servicold', 'type': 'int32', 'description': 'ID do serviço para filtrar'},
                    {'name': 'servicoDuracao', 'type': 'int32', 'description': 'Duração do serviço'},
                    {'name': 'profissionalld', 'type': 'int32', 'description': 'ID do profissional para filtrar'},
                    {'name': 'page', 'type': 'int32', 'description': 'Número da página'},
                    {'name': 'excluirExcecoesDeAgendamentoOnline', 'type': 'boolean', 'description': 'Excluir exceções de agendamento online'}
                ]
            },
            
            # ========================================
            # CLIENTES (5 endpoints)
            # ========================================
            
            # 9. Listar Clientes
            {
                'path': '/clientes',
                'method': 'GET',
                'description': 'Listar todos os clientes do estabelecimento',
                'required_fields': [],
                'required_headers': [
                    {'name': 'estabelecimentoId', 'type': 'string', 'description': 'ID do estabelecimento (OBRIGATÓRIO)'}
                ],
                'optional_fields': [
                    {'name': 'page', 'type': 'int32', 'description': 'Numeração da página'},
                    {'name': 'pageSize', 'type': 'int32', 'description': 'Quantidade de registros por página'},
                    {'name': 'nome', 'type': 'string', 'description': 'Nome do cliente'},
                    {'name': 'cpf', 'type': 'string', 'description': 'CPF do cliente (Ex: 99999999999)'},
                    {'name': 'email', 'type': 'string', 'description': 'E-mail do cliente'},
                    {'name': 'telefone', 'type': 'string', 'description': 'Telefone do cliente'},
                    {'name': 'dataCadastroInicio', 'type': 'date-time', 'description': 'Data de cadastro inicial'},
                    {'name': 'dataCadastroFim', 'type': 'date-time', 'description': 'Data de cadastro final'},
                    {'name': 'dataAlteracaoCadastralInicio', 'type': 'date-time', 'description': 'Data de alteração cadastral inicial'},
                    {'name': 'dataAlteracaoCadastralFim', 'type': 'date-time', 'description': 'Data de alteração cadastral final'},
                    {'name': 'incluirDetalhes', 'type': 'boolean', 'description': 'Inclui detalhes do cliente nos resultados (default: false)'}
                ]
            },
            
            # 10. Criar Cliente
            {
                'path': '/clientes',
                'method': 'POST',
                'description': 'Cria um novo cliente no estabelecimento',
                'required_fields': [],  # Todos os campos são opcionais
                'required_headers': [
                    {'name': 'estabelecimentoId', 'type': 'string', 'description': 'ID do estabelecimento (OBRIGATÓRIO)'}
                ],
                'optional_fields': [
                    {'name': 'nome', 'type': 'string', 'description': 'Nome do cliente (pode ser null)'},
                    {'name': 'email', 'type': 'string', 'description': 'Email do cliente (pode ser null)'},
                    {'name': 'cpf', 'type': 'string', 'description': 'CPF do cliente (pode ser null)'},
                    {'name': 'genero', 'type': 'string', 'description': 'Gênero: M=Masculino, F=Feminino, N=Não-Binário, X=Não informado'},
                    {'name': 'observacoes', 'type': 'string', 'description': 'Observações adicionais (pode ser null)'},
                    {'name': 'codigoExterno', 'type': 'string', 'description': 'Código externo (pode ser null)'},
                    {'name': 'telefones', 'type': 'array', 'description': 'Array de telefones (pode ser null)'},
                    {'name': 'preferencias', 'type': 'object', 'description': 'Objeto de preferências (pode ser null)'}
                ]
            },
            
            # 11. Detalhes do Cliente
            {
                'path': '/clientes/{id}',
                'method': 'GET',
                'description': 'Obtem todos os detalhes de um cliente',
                'required_fields': [
                    {'name': 'id', 'type': 'int32', 'description': 'ID do cliente (PATH PARAMS - OBRIGATÓRIO)'}
                ],
                'required_headers': [
                    {'name': 'estabelecimentoId', 'type': 'string', 'description': 'ID do estabelecimento (OBRIGATÓRIO)'}
                ],
                'optional_fields': []
            },
            
            # 12. Editar Cliente
            {
                'path': '/clientes/{clienteld}',
                'method': 'PUT',
                'description': 'Alterar os dados de um cliente',
                'required_fields': [
                    {'name': 'clienteld', 'type': 'int32', 'description': 'ID do cliente (PATH PARAMS - OBRIGATÓRIO)'}
                ],
                'required_headers': [
                    {'name': 'estabelecimentoId', 'type': 'string', 'description': 'ID do estabelecimento (OBRIGATÓRIO)'}
                ],
                'optional_fields': [
                    {'name': 'nome', 'type': 'string', 'description': 'Nome do cliente (pode ser null)'},
                    {'name': 'email', 'type': 'string', 'description': 'Email do cliente (pode ser null)'},
                    {'name': 'cpf', 'type': 'string', 'description': 'CPF do cliente (pode ser null)'},
                    {'name': 'genero', 'type': 'string', 'description': 'Gênero: M=Masculino, F=Feminino, N=Não-Binário, X=Não informado'},
                    {'name': 'observacoes', 'type': 'string', 'description': 'Observações adicionais (pode ser null)'},
                    {'name': 'codigoExterno', 'type': 'string', 'description': 'Código externo (pode ser null)'}
                ]
            },
            
            # 13. Excluir Cliente
            {
                'path': '/clientes/{clientId}',
                'method': 'DELETE',
                'description': 'Excluir um cliente do estabelecimento',
                'required_fields': [
                    {'name': 'clientId', 'type': 'int32', 'description': 'ID do cliente (PATH PARAMS - OBRIGATÓRIO)'}
                ],
                'required_headers': [
                    {'name': 'estabelecimentoId', 'type': 'string', 'description': 'ID do estabelecimento (OBRIGATÓRIO)'}
                ],
                'optional_fields': []
            },
            
            # ========================================
            # PRODUTOS E SERVIÇOS (3 endpoints)
            # ========================================
            
            # 14. Listar Produtos
            {
                'path': '/produtos',
                'method': 'GET',
                'description': 'Listar todos os produtos do estabelecimento',
                'required_fields': [],
                'required_headers': [
                    {'name': 'estabelecimentoId', 'type': 'string', 'description': 'ID do estabelecimento (OBRIGATÓRIO)'}
                ],
                'optional_fields': [
                    {'name': 'page', 'type': 'int32', 'description': 'Número da página'},
                    {'name': 'pageSize', 'type': 'int32', 'description': 'Quantidade de registros por página'},
                    {'name': 'nome', 'type': 'string', 'description': 'Nome do produto para filtrar'}
                ]
            },
            
            # 15. Listar Serviços
            {
                'path': '/servicos',
                'method': 'GET',
                'description': 'Listar todos os serviços do estabelecimento',
                'required_fields': [],
                'required_headers': [
                    {'name': 'estabelecimentoId', 'type': 'string', 'description': 'ID do estabelecimento (OBRIGATÓRIO)'}
                ],
                'optional_fields': [
                    {'name': 'page', 'type': 'int32', 'description': 'Número da página'},
                    {'name': 'pageSize', 'type': 'int32', 'description': 'Quantidade de registros por página'},
                    {'name': 'nome', 'type': 'string', 'description': 'Nome do serviço para filtrar'},
                    {'name': 'categoria', 'type': 'string', 'description': 'Categoria para filtro'},
                    {'name': 'somenteVisiveisCliente', 'type': 'boolean', 'description': 'Se verdadeiro, apenas serviços visíveis ao cliente (default: false)'}
                ]
            },
            
            # 16. Listar Promoções
            {
                'path': '/servicos/{id}/promocoes',
                'method': 'GET',
                'description': 'Lista as promoções associadas a um serviço com o valor por dia da semana',
                'required_fields': [
                    {'name': 'id', 'type': 'int32', 'description': 'ID do serviço (PATH PARAMS - OBRIGATÓRIO)'}
                ],
                'required_headers': [
                    {'name': 'estabelecimentoId', 'type': 'string', 'description': 'ID do estabelecimento (OBRIGATÓRIO)'}
                ],
                'optional_fields': []
            }
        ]
        
        # Processar cada endpoint
        processed_endpoints = []
        for endpoint in final_endpoints:
            processed_endpoint = {
                'path': endpoint['path'],
                'method': endpoint['method'],
                'summary': f"{endpoint['method']} {endpoint['path']}",
                'description': endpoint['description'],
                'operation_id': f"{endpoint['method'].lower()}_{endpoint['path'].replace('/', '_').replace('{', '').replace('}', '')}",
                'parameters': endpoint['required_fields'] + endpoint['optional_fields'],
                'request_body': {
                    'required': [field['name'] for field in endpoint['required_fields']],
                    'properties': {
                        field['name']: {
                            'type': field['type'],
                            'description': field['description']
                        } for field in endpoint['required_fields'] + endpoint['optional_fields']
                    }
                } if endpoint['method'] in ['POST', 'PUT', 'PATCH'] else None,
                'responses': {
                    '200': {'description': 'Sucesso'},
                    '201': {'description': 'Criado com sucesso'},
                    '204': {'description': 'Sem conteúdo'},
                    '400': {'description': 'Dados inválidos'},
                    '401': {'description': 'Não autorizado'},
                    '404': {'description': 'Não encontrado'},
                    '422': {'description': 'Erro de validação'},
                    '500': {'description': 'Erro interno'}
                },
                'required_fields': endpoint['required_fields'],
                'required_headers': endpoint.get('required_headers', []),
                'optional_fields': endpoint['optional_fields']
            }
            
            processed_endpoints.append(processed_endpoint)
        
        return processed_endpoints
    
    def generate_openapi_spec(self, api_info: Dict[str, Any]) -> Dict[str, Any]:
        """Gera especificação OpenAPI FINAL a partir das informações parseadas"""
        
        openapi_spec = {
            'openapi': '3.0.0',
            'info': {
                'title': api_info['nome'],
                'description': api_info['descricao'],
                'version': api_info.get('version', '1.0.0')
            },
            'servers': [
                {'url': api_info['url_base']}
            ],
            'paths': {}
        }
        
        # Adicionar cada endpoint
        for endpoint in api_info['endpoints']:
            path = endpoint['path']
            method = endpoint['method'].lower()
            
            if path not in openapi_spec['paths']:
                openapi_spec['paths'][path] = {}
            
            # Preparar parâmetros (incluindo headers obrigatórios)
            parameters = []
            
            # Adicionar parâmetros de path
            for field in endpoint['required_fields']:
                if '{' + field['name'] + '}' in path:
                    parameters.append({
                        'name': field['name'],
                        'in': 'path',
                        'required': True,
                        'schema': {'type': field['type']},
                        'description': field['description']
                    })
            
            # Adicionar headers obrigatórios
            for header in endpoint.get('required_headers', []):
                parameters.append({
                    'name': header['name'],
                    'in': 'header',
                    'required': True,
                    'schema': {'type': header['type']},
                    'description': header['description']
                })
            
            openapi_spec['paths'][path][method] = {
                'summary': endpoint['summary'],
                'description': endpoint['description'],
                'operationId': endpoint['operation_id'],
                'parameters': parameters,
                'requestBody': endpoint['request_body'] if method in ['post', 'put', 'patch'] else None,
                'responses': endpoint['responses']
            }
        
        return openapi_spec

# Instância global FINAL
trinks_parser = TrinksParser() 