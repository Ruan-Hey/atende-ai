#!/usr/bin/env python3
"""
Ferramentas Inteligentes para API Trinks
Usa o motor de regras expandido para operações inteligentes
CORRIGIDO PARA PRODUÇÃO - Considera duração do serviço
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from ..agents.api_rules_engine import api_rules_engine
from .api_tools import APITools
import requests

logger = logging.getLogger(__name__)

class TrinksIntelligentTools:
    """Ferramentas inteligentes para operações com API Trinks"""
    
    def __init__(self):
        self.api_tools = APITools()
    
    def search_client_by_cpf(self, cpf: str, empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Busca cliente por CPF usando as regras da API Trinks
        
        Args:
            cpf: CPF do cliente (com ou sem formatação)
            empresa_config: Configuração da empresa
            
        Returns:
            Dict com dados do cliente ou None se não encontrado
        """
        try:
            # Verificar se é API Trinks
            if not api_rules_engine.is_trinks_api(empresa_config):
                return {"error": "API Trinks não está ativa para esta empresa"}
            
            # Obter regras de busca de cliente
            client_rules = api_rules_engine.get_client_search_rules(empresa_config)
            if not client_rules:
                return {"error": "Regras de busca de cliente não configuradas"}
            
            # Limpar CPF (remover pontos e traços)
            cpf_limpo = re.sub(r'[^\d]', '', cpf)
            
            # Preparar parâmetros da busca
            search_params = {
                "cpf": cpf_limpo,
                "estabelecimentoId": empresa_config.get('trinks_estabelecimento_id')
            }
            
            # Fazer busca na API
            endpoint = client_rules['api_endpoint']
            result = self.api_tools.call_api(
                api_name="Trinks",
                endpoint_path=endpoint,
                method="GET",
                config=empresa_config.get('trinks_config', {}),
                **search_params
            )
            
            # Processar resultado
            if isinstance(result, str):
                try:
                    import json
                    result_data = json.loads(result)
                except:
                    result_data = {"raw_result": result}
            else:
                result_data = result
            
            # Verificar se encontrou cliente
            if result_data and isinstance(result_data, dict):
                if 'data' in result_data and result_data['data']:
                    cliente = result_data['data'][0] if isinstance(result_data['data'], list) else result_data['data']
                    return {
                        "found": True,
                        "cliente": cliente,
                        "message": f"Cliente encontrado: {cliente.get('nome', 'N/A')}"
                    }
                elif 'items' in result_data and result_data['items']:
                    cliente = result_data['items'][0] if isinstance(result_data['items'], list) else result_data['items']
                    return {
                        "found": True,
                        "cliente": cliente,
                        "message": f"Cliente encontrado: {cliente.get('nome', 'N/A')}"
                    }
            
            # Cliente não encontrado
            return {
                "found": False,
                "message": "Cliente não encontrado com este CPF",
                "suggest_create": client_rules.get('create_if_not_found', False)
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar cliente por CPF: {e}")
            return {"error": f"Erro na busca: {str(e)}"}
    
    def detect_service_from_conversation(self, message: str, empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detecta serviço da conversa usando NLP e regras da API Trinks
        
        Args:
            message: Mensagem do cliente
            empresa_config: Configuração da empresa
            
        Returns:
            Dict com informações do serviço detectado
        """
        try:
            # Verificar se é API Trinks
            if not api_rules_engine.is_trinks_api(empresa_config):
                return {"error": "API Trinks não está ativa para esta empresa"}
            
            # Obter regras de detecção de serviço
            service_rules = api_rules_engine.get_service_detection_rules(empresa_config)
            if not service_rules:
                return {"error": "Regras de detecção de serviço não configuradas"}
            
            # Detecção por palavras-chave (fallback)
            message_lower = message.lower()
            detected_service = None
            
            # Mapeamento de serviços
            service_mapping = service_rules.get('service_mapping', {})
            
            for service_name, keywords in service_mapping.items():
                if any(keyword in message_lower for keyword in keywords):
                    detected_service = service_name
                    break
            
            # Se não detectou por palavras-chave, usar fallback
            if not detected_service:
                fallback_keywords = service_rules.get('fallback_keywords', [])
                for keyword in fallback_keywords:
                    if keyword in message_lower:
                        detected_service = keyword
                        break
            
            if detected_service:
                # Buscar serviço na API
                return self._search_service_in_api(detected_service, empresa_config)
            
            return {
                "detected": False,
                "message": "Não consegui identificar qual serviço você deseja",
                "suggestions": list(service_mapping.keys())
            }
            
        except Exception as e:
            logger.error(f"Erro ao detectar serviço: {e}")
            return {"error": f"Erro na detecção: {str(e)}"}
    
    def _search_service_in_api(self, service_name: str, empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """Busca serviço na API Trinks"""
        try:
            service_rules = api_rules_engine.get_service_detection_rules(empresa_config)
            endpoint = service_rules['api_endpoint']
            
            # Buscar serviços
            search_params = {
                "nome": service_name,
                "estabelecimentoId": empresa_config.get('trinks_estabelecimento_id')
            }
            
            result = self.api_tools.call_api(
                api_name="Trinks",
                endpoint_path=endpoint,
                method="GET",
                config=empresa_config.get('trinks_config', {}),
                **search_params
            )
            
            # Processar resultado
            if isinstance(result, str):
                try:
                    import json
                    result_data = json.loads(result)
                except:
                    result_data = {"raw_result": result}
            else:
                result_data = result
            
            # Extrair dados do serviço
            if result_data and isinstance(result_data, dict):
                services = result_data.get('data', []) or result_data.get('items', [])
                if services and isinstance(services, list):
                    service = services[0]  # Primeiro serviço encontrado
                    return {
                        "detected": True,
                        "service": service,
                        "service_name": service.get('nome', service_name),
                        "service_id": service.get('id'),
                        "service_duration": service.get('duracaoEmMinutos', 60),
                        "message": f"Serviço detectado: {service.get('nome', service_name)} ({service.get('duracaoEmMinutos', 60)} min)"
                    }
            
            return {
                "detected": False,
                "message": f"Serviço '{service_name}' não encontrado na API",
                "service_name": service_name
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar serviço na API: {e}")
            return {"error": f"Erro na busca do serviço: {str(e)}"}
    
    def find_professionals_for_service(self, service_id: str, empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Encontra profissionais que fazem o serviço especificado
        
        Args:
            service_id: ID do serviço
            empresa_config: Configuração da empresa
            
        Returns:
            Dict com lista de profissionais
        """
        try:
            # Verificar se é API Trinks
            if not api_rules_engine.is_trinks_api(empresa_config):
                return {"error": "API Trinks não está ativa para esta empresa"}
            
            # Obter regras de busca de profissionais
            prof_rules = api_rules_engine.get_professional_search_rules(empresa_config)
            if not prof_rules:
                return {"error": "Regras de busca de profissionais não configuradas"}
            
            # Buscar profissionais
            endpoint = prof_rules['api_endpoint']
            search_params = {
                "estabelecimentoId": empresa_config.get('trinks_estabelecimento_id')
            }
            
            # Se deve filtrar por serviço
            if prof_rules.get('filter_by_service'):
                search_params["servicold"] = service_id
            
            result = self.api_tools.call_api(
                api_name="Trinks",
                endpoint_path=endpoint,
                method="GET",
                config=empresa_config.get('trinks_config', {}),
                **search_params
            )
            
            # Processar resultado
            if isinstance(result, str):
                try:
                    import json
                    result_data = json.loads(result)
                except:
                    result_data = {"raw_result": result}
            else:
                result_data = result
            
            # Extrair profissionais
            if result_data and isinstance(result_data, dict):
                professionals = result_data.get('data', []) or result_data.get('items', [])
                if professionals and isinstance(professionals, list):
                    return {
                        "found": True,
                        "professionals": professionals,
                        "count": len(professionals),
                        "message": f"Encontrados {len(professionals)} profissionais para este serviço"
                    }
            
            return {
                "found": False,
                "message": "Nenhum profissional encontrado para este serviço"
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar profissionais: {e}")
            return {"error": f"Erro na busca de profissionais: {str(e)}"}
    
    def check_professional_availability(self, data: str, service_id: str, empresa_config: Dict[str, Any], 
                                      professional_id: str = None) -> Dict[str, Any]:
        """
        Verifica disponibilidade de profissionais para um serviço em uma data
        CORRIGIDO PARA PRODUÇÃO - Considera duração real do serviço
        
        Args:
            data: Data no formato YYYY-MM-DD
            service_id: ID do serviço
            empresa_config: Configuração da empresa
            professional_id: ID do profissional específico (opcional)
            
        Returns:
            Dict com horários disponíveis
        """
        try:
            # Verificar se é API Trinks
            if not api_rules_engine.is_trinks_api(empresa_config):
                return {"error": "API Trinks não está ativa para esta empresa"}
            
            # Obter regras de verificação de disponibilidade
            avail_rules = api_rules_engine.get_availability_check_rules(empresa_config)
            if not avail_rules:
                return {"error": "Regras de verificação de disponibilidade não configuradas"}
            
            # 1. Primeiro, buscar a duração do serviço
            service_duration = self._get_service_duration(service_id, empresa_config)
            if not service_duration:
                return {"error": "Não foi possível determinar a duração do serviço"}
            
            # 2. Buscar agendamentos existentes para a data
            existing_appointments = self._get_existing_appointments(data, empresa_config, professional_id)
            if existing_appointments.get('error'):
                return existing_appointments
            
            # 3. Calcular slots disponíveis considerando duração real
            available_slots = self._calculate_available_slots(
                data, 
                service_duration, 
                existing_appointments.get('appointments', []),
                avail_rules
            )
            
            if available_slots:
                return {
                    "available": True,
                    "date": data,
                    "service_duration": service_duration,
                    "available_slots": available_slots,
                    "count": len(available_slots),
                    "message": f"Encontrados {len(available_slots)} horários disponíveis para {data} (duração: {service_duration} min)"
                }
            else:
                return {
                    "available": False,
                    "date": data,
                    "service_duration": service_duration,
                    "message": "Nenhum horário disponível encontrado para esta data e duração de serviço"
                }
            
        except Exception as e:
            logger.error(f"Erro ao verificar disponibilidade: {e}")
            return {"error": f"Erro na verificação: {str(e)}"}
    
    def _get_service_duration(self, service_id: str, empresa_config: Dict[str, Any]) -> Optional[int]:
        """Busca a duração real do serviço na API"""
        try:
            headers = {
                'X-API-KEY': empresa_config["trinks_api_key"],
                'estabelecimentoId': empresa_config['trinks_estabelecimento_id'],
                'Content-Type': 'application/json'
            }
            
            # Buscar detalhes do serviço
            response = requests.get(
                f"{empresa_config['trinks_base_url']}/servicos/{service_id}",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                service_data = response.json()
                return service_data.get('duracaoEmMinutos', 60)
            else:
                # Fallback: buscar na lista de serviços
                response_list = requests.get(
                    f"{empresa_config['trinks_base_url']}/servicos",
                    headers=headers,
                    timeout=30
                )
                
                if response_list.status_code == 200:
                    services = response_list.json().get('data', [])
                    for service in services:
                        if service.get('id') == int(service_id):
                            return service.get('duracaoEmMinutos', 60)
            
            return 60  # Duração padrão se não conseguir buscar
            
        except Exception as e:
            logger.error(f"Erro ao buscar duração do serviço: {e}")
            return 60
    
    def _get_existing_appointments(self, data: str, empresa_config: Dict[str, Any], 
                                  professional_id: str = None) -> Dict[str, Any]:
        """Busca agendamentos existentes para uma data"""
        try:
            headers = {
                'X-API-KEY': empresa_config["trinks_api_key"],
                'estabelecimentoId': empresa_config['trinks_estabelecimento_id'],
                'Content-Type': 'application/json'
            }
            
            params = {'data': data}
            if professional_id:
                params['profissionalId'] = professional_id
            
            response = requests.get(
                f"{empresa_config['trinks_base_url']}/agendamentos",
                headers=headers,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                appointments = response.json().get('data', [])
                return {"appointments": appointments}
            else:
                return {"error": f"Erro ao buscar agendamentos: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Erro ao buscar agendamentos existentes: {e}")
            return {"error": f"Erro na busca: {str(e)}"}
    
    def _calculate_available_slots(self, data: str, service_duration: int, 
                                  existing_appointments: List[Dict], 
                                  avail_rules: Dict[str, Any]) -> List[str]:
        """Calcula slots disponíveis considerando duração real do serviço"""
        try:
            available_slots = []
            slot_calc = avail_rules.get('slot_calculation', {})
            working_hours = slot_calc.get('working_hours', {})
            buffer_time = slot_calc.get('buffer_time', 15)
            
            # Horário de funcionamento
            start_hour = int(working_hours.get('start', '08:00').split(':')[0])
            end_hour = int(working_hours.get('end', '18:00').split(':')[0])
            
            # Converter agendamentos existentes para horários ocupados
            occupied_slots = self._convert_appointments_to_occupied_slots(existing_appointments)
            
            # Gerar slots de horário considerando duração real
            current_hour = start_hour
            while current_hour < end_hour:
                slot_time = f"{current_hour:02d}:00"
                
                # Verificar se o slot está disponível para a duração do serviço
                if self._is_slot_available_for_duration(slot_time, service_duration, occupied_slots, buffer_time):
                    available_slots.append(slot_time)
                
                # Próximo slot (considerando duração + buffer)
                current_hour += (service_duration + buffer_time) // 60
                if current_hour >= end_hour:
                    break
            
            return available_slots
            
        except Exception as e:
            logger.error(f"Erro ao calcular slots disponíveis: {e}")
            return []
    
    def _convert_appointments_to_occupied_slots(self, appointments: List[Dict]) -> List[Dict]:
        """Converte agendamentos para slots ocupados com início e fim"""
        occupied_slots = []
        
        for appointment in appointments:
            inicio = appointment.get('dataHoraInicio')
            duracao = appointment.get('duracaoEmMinutos', 0)
            
            if inicio and duracao:
                try:
                    inicio_dt = datetime.fromisoformat(inicio.replace('Z', '+00:00'))
                    fim_dt = inicio_dt + timedelta(minutes=duracao)
                    
                    occupied_slots.append({
                        'inicio': inicio_dt,
                        'fim': fim_dt,
                        'duracao': duracao,
                        'servico': appointment.get('servico', {}).get('nome', 'N/A')
                    })
                except Exception as e:
                    logger.warning(f"Erro ao processar agendamento: {e}")
                    continue
        
        return occupied_slots
    
    def _is_slot_available_for_duration(self, slot_time: str, service_duration: int, 
                                       occupied_slots: List[Dict], buffer_time: int) -> bool:
        """Verifica se um slot está disponível para a duração do serviço"""
        try:
            # Converter slot_time para datetime
            slot_dt = datetime.strptime(f"2025-01-01 {slot_time}", "%Y-%m-%d %H:%M")
            slot_end_dt = slot_dt + timedelta(minutes=service_duration)
            
            # Verificar conflitos com agendamentos existentes
            for occupied in occupied_slots:
                # Verificar sobreposição
                if (slot_dt < occupied['fim'] and slot_end_dt > occupied['inicio']):
                    return False
                
                # Verificar buffer
                buffer_start = slot_dt - timedelta(minutes=buffer_time)
                buffer_end = slot_end_dt + timedelta(minutes=buffer_time)
                
                if (buffer_start < occupied['fim'] and buffer_end > occupied['inicio']):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao verificar disponibilidade do slot: {e}")
            return False
    
    def create_reservation(self, reservation_data: Dict[str, Any], empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cria uma reserva usando as regras da API Trinks
        CORRIGIDO PARA PRODUÇÃO - Valida duração e conflitos
        
        Args:
            reservation_data: Dados da reserva
            empresa_config: Configuração da empresa
            
        Returns:
            Dict com resultado da criação da reserva
        """
        try:
            # Verificar se é API Trinks
            if not api_rules_engine.is_trinks_api(empresa_config):
                return {"error": "API Trinks não está ativa para esta empresa"}
            
            # Obter regras de criação de reserva
            reservation_rules = api_rules_engine.get_reservation_creation_rules(empresa_config)
            if not reservation_rules:
                return {"error": "Regras de criação de reserva não configuradas"}
            
            # Validar campos obrigatórios
            required_fields = reservation_rules.get('required_fields', [])
            missing_fields = []
            
            for field in required_fields:
                if field not in reservation_data or not reservation_data[field]:
                    missing_fields.append(field)
            
            if missing_fields:
                return {
                    "error": "Campos obrigatórios faltando",
                    "missing_fields": missing_fields,
                    "required_fields": required_fields
                }
            
            # VALIDAÇÃO CRÍTICA: Verificar se o horário está realmente disponível
            data = reservation_data.get('dataHoraInicio', '')[:10]  # YYYY-MM-DD
            service_id = reservation_data.get('servicold')
            
            if data and service_id:
                # Verificar disponibilidade real
                availability_check = self.check_professional_availability(
                    data, service_id, empresa_config, 
                    reservation_data.get('profissionalld')
                )
                
                if not availability_check.get('available'):
                    return {
                        "error": "Horário não disponível",
                        "details": availability_check.get('message', 'Conflito de horário detectado'),
                        "suggestion": "Verifique outros horários disponíveis"
                    }
            
            # Preparar dados para API
            api_data = {
                "estabelecimentoId": empresa_config.get('trinks_estabelecimento_id')
            }
            
            # Adicionar campos da reserva
            for field, value in reservation_data.items():
                if field in required_fields or field in reservation_rules.get('optional_fields', []):
                    api_data[field] = value
            
            # Fazer chamada para API
            endpoint = reservation_rules['api_endpoint']
            result = self.api_tools.call_api(
                api_name="Trinks",
                endpoint_path=endpoint,
                method="POST",
                config=empresa_config.get('trinks_config', {}),
                **api_data
            )
            
            # Processar resultado
            if isinstance(result, str):
                try:
                    import json
                    result_data = json.loads(result)
                except:
                    result_data = {"raw_result": result}
            else:
                result_data = result
            
            # Verificar sucesso
            if result_data and isinstance(result_data, dict):
                if 'id' in result_data or 'success' in str(result_data).lower():
                    return {
                        "success": True,
                        "reservation_id": result_data.get('id'),
                        "message": "Reserva criada com sucesso!",
                        "data": result_data
                    }
            
            return {
                "success": False,
                "message": "Erro ao criar reserva",
                "data": result_data
            }
            
        except Exception as e:
            logger.error(f"Erro ao criar reserva: {e}")
            return {"error": f"Erro na criação: {str(e)}"}

# Instância global das ferramentas inteligentes
trinks_intelligent_tools = TrinksIntelligentTools() 