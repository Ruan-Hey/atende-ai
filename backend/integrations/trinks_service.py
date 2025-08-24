import requests
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class TrinksService:
    """
    Serviço base para integração com Trinks API
    Contém APENAS chamadas HTTP básicas para a API
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa o serviço Trinks
        Args:
            config: Configurações da empresa (base_url, api_key, etc.)
        """
        self.config = config
        self.base_url = config.get('trinks_base_url', '')
        self.api_key = config.get('trinks_api_key', '')
        self.estabelecimento_id = config.get('trinks_estabelecimento_id', '')
        
        # Headers padrão para todas as requisições
        self.headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json',
            'estabelecimentoId': str(self.estabelecimento_id)  # ✅ Adicionar estabelecimentoId no header
        }
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Dict:
        """
        Faz requisição HTTP para Trinks API
        Args:
            method: Método HTTP (GET, POST, PUT, DELETE)
            endpoint: Endpoint da API
            data: Dados para enviar (POST/PUT)
            params: Parâmetros de query (GET)
        Returns:
            Resposta da API como dicionário
        """
        try:
            url = f"{self.base_url}{endpoint}"
            
            # Log para debug
            logger.info(f"🌐 Trinks API Request: {method.upper()} {url}")
            logger.info(f"🔑 Headers: {self.headers}")
            if params:
                logger.info(f"📝 Params: {params}")
            if data:
                logger.info(f"📦 Data: {data}")
            
            if method.upper() == 'GET':
                response = requests.get(url, headers=self.headers, params=params)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=self.headers, json=data)
            elif method.upper() == 'PUT':
                response = requests.put(url, headers=self.headers, json=data)
            elif method.upper() == 'PATCH':
                response = requests.patch(url, headers=self.headers, json=data)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=self.headers)
            else:
                raise ValueError(f"Método HTTP não suportado: {method}")
            
            # Log da resposta para debug
            logger.info(f"📡 Trinks API Response: {response.status_code} - {response.text[:200]}")
            
            response.raise_for_status()
            
            # ✅ Tratar status 204 (No Content) - não tem corpo para fazer JSON
            if response.status_code == 204:
                return {"success": True, "status": "204", "message": "Operação realizada com sucesso"}
            
            # Para outros status codes, tentar fazer JSON
            try:
                return response.json()
            except ValueError:
                # Se não conseguir fazer JSON, retornar texto
                return {"success": True, "status": str(response.status_code), "text": response.text}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição Trinks API: {e}")
            return {'error': str(e)}
        except Exception as e:
            logger.error(f"Erro inesperado na requisição Trinks: {e}")
            return {'error': str(e)}
    
    # ====================
    # PROFISSIONAIS
    # ====================
    
    def get_professionals(self) -> Dict:
        """Busca lista de profissionais"""
        # ✅ Endpoint correto da Trinks API: /v1/profissionais
        endpoint = "/profissionais"
        return self._make_request('GET', endpoint)
    
    def get_professional(self, professional_id: str) -> Dict:
        """Busca profissional específico"""
        # ✅ Endpoint correto da Trinks API: /v1/profissionais/{id}
        endpoint = f"/profissionais/{professional_id}"
        return self._make_request('GET', endpoint)
    
    def get_professional_services(self, professional_id: str) -> Dict:
        """Busca serviços de um profissional específico"""
        # ✅ Endpoint correto da Trinks API: /v1/profissionais/{id}/servicos
        endpoint = f"/profissionais/{professional_id}/servicos"
        return self._make_request('GET', endpoint)
    
    # ====================
    # SERVIÇOS
    # ====================
    
    def get_services(self) -> Dict:
        """Busca lista de serviços"""
        # ✅ Endpoint correto da Trinks API: /v1/servicos
        endpoint = "/servicos"
        return self._make_request('GET', endpoint)
    
    def get_service(self, service_id: str) -> Dict:
        """Busca serviço específico"""
        # ✅ Endpoint correto da Trinks API: /v1/servicos/{id}
        endpoint = f"/servicos/{service_id}"
        return self._make_request('GET', endpoint)
    
    # ====================
    # AGENDAMENTOS
    # ====================
    
    def get_appointments(self, client_id: str = None) -> Dict:
        """Busca agendamentos do cliente"""
        params = {}
        if client_id:
            # Converter para inteiro se possível, senão manter como string
            try:
                params['clienteId'] = int(client_id)  # Usar clienteId (com I maiúsculo) como no exemplo
                logger.info(f"🔍 Buscando agendamentos para cliente ID: {client_id} (tipo: {type(client_id)})")
            except (ValueError, TypeError):
                params['clienteId'] = str(client_id)
                logger.info(f"🔍 Buscando agendamentos para cliente ID: {client_id} (tipo: {type(client_id)})")
            
        # ✅ Endpoint correto da Trinks API: /v1/agendamentos
        endpoint = "/agendamentos"
        return self._make_request('GET', endpoint, params=params)
    
    def get_appointment(self, appointment_id: str) -> Dict:
        """Busca agendamento específico"""
        # ✅ Endpoint correto da Trinks API: /v1/agendamentos/{id}
        endpoint = f"/agendamentos/{appointment_id}"
        return self._make_request('GET', endpoint)
    
    def create_appointment(self, appointment_data: Dict) -> Dict:
        """Cria novo agendamento"""
        # ✅ Endpoint correto da Trinks API: /v1/agendamentos
        endpoint = "/agendamentos"
        return self._make_request('POST', endpoint, data=appointment_data)
    
    def update_appointment(self, appointment_id: str, appointment_data: Dict) -> Dict:
        """Atualiza agendamento existente"""
        # ✅ Endpoint correto da Trinks API: /v1/agendamentos/{id}
        endpoint = f"/agendamentos/{appointment_id}"
        return self._make_request('PUT', endpoint, data=appointment_data)
    
    def delete_appointment(self, appointment_id: str) -> Dict:
        """Remove agendamento"""
        # ✅ Endpoint correto da Trinks API: /v1/agendamentos/{id}
        endpoint = f"/agendamentos/{appointment_id}"
        return self._make_request('DELETE', endpoint)
    
    def cancel_appointment(self, appointment_id: str, quem_cancelou: int, motivo: str) -> Dict:
        """Cancela um agendamento"""
        # ✅ Endpoint correto da Trinks API: /v1/agendamentos/{agendamentoId}/status/cancelado
        endpoint = f"/agendamentos/{appointment_id}/status/cancelado"
        
        # Payload conforme documentação da API
        data = {
            "quemCancelou": quem_cancelou,
            "motivo": motivo
        }
        
        return self._make_request('PATCH', endpoint, data=data)
    
    # ====================
    # DISPONIBILIDADE
    # ====================
    
    def get_availability(self, professional_id: str, service_id: str, date: str) -> Dict:
        """Busca disponibilidade de profissional para serviço em data específica"""
        params = {
            'profissional_id': professional_id,
            'servico_id': service_id,
            'data': date
        }
        # ✅ Endpoint correto da Trinks API: /v1/disponibilidade
        endpoint = "/disponibilidade"
        return self._make_request('GET', endpoint, params=params)
    
    def get_available_slots(self, professional_id: str, service_id: str, date: str) -> Dict:
        """Busca horários disponíveis para agendamento"""
        params = {
            'profissional_id': professional_id,
            'servico_id': service_id,
            'data': date
        }
        # ✅ Endpoint correto da Trinks API: /v1/horarios-disponiveis
        endpoint = "/horarios-disponiveis"
        return self._make_request('GET', endpoint, params=params)
    
    # ====================
    # CLIENTES
    # ====================
    
    def get_clients(self, **filters) -> Dict:
        """Busca lista de clientes"""
        # ✅ Endpoint correto da Trinks API: /v1/clientes
        endpoint = "/clientes"
        return self._make_request('GET', endpoint, params=filters)
    
    def get_client(self, client_id: str) -> Dict:
        """Busca cliente específico"""
        # ✅ Endpoint correto da Trinks API: /v1/clientes/{id}
        endpoint = f"/clientes/{client_id}"
        return self._make_request('GET', endpoint)
    
    def create_client(self, client_data: Dict) -> Dict:
        """Cria novo cliente"""
        # ✅ Endpoint correto da Trinks API: /v1/clientes
        endpoint = "/clientes"
        return self._make_request('POST', endpoint, data=client_data)
    
    def update_client(self, client_id: str, client_data: Dict) -> Dict:
        """Atualiza cliente existente"""
        # ✅ Endpoint correto da Trinks API: /v1/clientes/{id}
        endpoint = f"/clientes/{client_id}"
        return self._make_request('PUT', endpoint, data=client_data)
    
    # ====================
    # ESTABELECIMENTO
    # ====================
    
    def get_establishment_info(self) -> Dict:
        """Busca informações do estabelecimento"""
        # ✅ Endpoint correto da Trinks API: /v1/estabelecimentos/{id}
        endpoint = f"/estabelecimentos/{self.estabelecimento_id}"
        return self._make_request('GET', endpoint)
    
    def get_establishment_schedule(self) -> Dict:
        """Busca horário de funcionamento do estabelecimento"""
        # ✅ Endpoint correto da Trinks API: /v1/estabelecimentos/{id}/horario-funcionamento
        endpoint = f"/estabelecimentos/{self.estabelecimento_id}/horario-funcionamento"
        return self._make_request('GET', endpoint)
