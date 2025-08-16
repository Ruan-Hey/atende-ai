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
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.api_rules_engine import api_rules_engine
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
    
    def resolve_professional_id_by_name(self, name: str, empresa_config: Dict[str, Any]) -> Optional[str]:
        """Resolve o ID do profissional pelo nome fazendo match local sobre a lista completa do estabelecimento."""
        try:
            logger.info(f"🔎 Resolvendo profissional por nome (lista completa): {name}")
            endpoint = "profissionais"
            raw_name = (name or '').strip()

            # Normalização robusta (lowercase + remover acentos + remover títulos)
            import unicodedata
            def _norm(txt: str) -> str:
                txt = (txt or '').lower().strip()
                txt = txt.replace('dra.', '').replace('dr.', '').replace('dra', '').replace('dr', '')
                txt = ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
                return ' '.join(txt.split())
            target = _norm(raw_name)

            params: Dict[str, Any] = {
                'estabelecimentoId': empresa_config.get('trinks_estabelecimento_id') or empresa_config.get('estabelecimentoId')
            }
            result = self.api_tools.call_api(
                api_name="Trinks",
                endpoint_path=endpoint,
                method="GET",
                config=empresa_config.get('trinks_config', empresa_config),
                **params
            )

            # Parse seguro do formato "Sucesso na operação ... {json}"
            import json
            if isinstance(result, str) and result.strip().startswith("Sucesso na operação"):
                brace_idx = result.find('{')
                if brace_idx != -1:
                    result = json.loads(result[brace_idx:])
            elif isinstance(result, str):
                result = json.loads(result)

            data_list = (result or {}).get('data', []) if isinstance(result, dict) else []
            if not data_list:
                logger.info("🔎 Lista de profissionais vazia para o estabelecimento")
                return None

            # Fuzzy matching local usando difflib
            from difflib import SequenceMatcher
            best_id = None
            best_score = 0.0
            for p in data_list:
                pname = _norm(p.get('nome') or '')
                if not pname:
                    continue
                score = SequenceMatcher(None, target, pname).ratio()
                if score > best_score:
                    best_score = score
                    best_id = str(p.get('id')) if p.get('id') is not None else None
            logger.info(f"🔎 Melhor match para '{raw_name}': id={best_id} score={best_score:.2f}")
            # Limite mínimo razoável
            if best_id and best_score >= float(empresa_config.get('matching_min_score', 0.65)):
                logger.info(f"🎯 Profissional resolvido: {raw_name} -> {best_id}")
                return best_id
            return None
        except Exception as e:
            logger.warning(f"Falha ao resolver profissional por nome (lista completa): {e}")
            return None

    def _get_working_windows(self, data: str, empresa_config: Dict[str, Any], professional_id: Optional[str]) -> Optional[List[Dict[str, str]]]:
        """Busca janelas reais de trabalho via /agendamentos/profissionais/{data}."""
        try:
            if not data:
                return None
            # Fallback seguro de base_url
            safe_base_url = (
                empresa_config.get('trinks_base_url')
                or (empresa_config.get('trinks_config', {}) or {}).get('base_url')
                or 'https://api.trinks.com/v1'
            )
            headers = {
                'X-API-KEY': empresa_config.get("trinks_api_key", ""),
                'estabelecimentoId': empresa_config.get('trinks_estabelecimento_id', ''),
                'Content-Type': 'application/json'
            }
            params = {}
            if professional_id:
                params['profissionalId'] = professional_id
            import requests
            resp = requests.get(f"{safe_base_url}/agendamentos/profissionais/{data}", headers=headers, params=params, timeout=30)
            if resp.status_code == 200:
                payload = resp.json()
                return payload.get('data') or payload.get('items') or []
            return None
        except Exception as e:
            logger.warning(f"Falha ao obter janelas de trabalho: {e}")
            return None

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
            
            # 1.1 Resolver professional_id pelo nome no contexto, se não informado
            if not professional_id:
                prof_name = (empresa_config.get('current_context', {}) or {}).get('profissional_nome')
                if not prof_name:
                    # tentar pegar de um campo comum no empresa_config passado pela camada superior
                    prof_name = (empresa_config.get('profissional_nome') or '').strip()
                if prof_name:
                    resolved = self.resolve_professional_id_by_name(prof_name, empresa_config)
                    if resolved:
                        professional_id = resolved

            # 2. Buscar agendamentos existentes para a data (filtrando por profissional se houver)
            existing_appointments = self._get_existing_appointments(data, empresa_config, professional_id)
            if existing_appointments.get('error'):
                return existing_appointments
            
            # 3. Calcular slots disponíveis considerando duração real
            # 3.1 Tentar obter janelas reais de trabalho e ajustar working_hours
            windows = self._get_working_windows(data, empresa_config, professional_id)
            if windows:
                # Ajustar working hours com base nas janelas (pega a primeira janela do dia para simplificar)
                try:
                    first = windows[0]
                    start = (first.get('inicio') or first.get('start') or '08:00')[-5:]
                    end = (first.get('fim') or first.get('end') or '18:00')[-5:]
                    avail_rules = dict(avail_rules)
                    sc = dict(avail_rules.get('slot_calculation', {}))
                    sc['working_hours'] = {'start': start, 'end': end}
                    avail_rules['slot_calculation'] = sc
                except Exception:
                    pass

            # Se houver nome no contexto mas não houver ID, tentar resolver para ID
            if not professional_id:
                ctx = empresa_config.get('current_context') or {}
                pn = (ctx.get('profissional_nome') or '').strip()
                if pn:
                    try:
                        resolved = self.resolve_professional_id_by_name(pn, empresa_config)
                        if resolved:
                            professional_id = str(resolved)
                            logger.info(f"🎯 profissional_nome no contexto resolvido para ID: {professional_id}")
                    except Exception:
                        pass

            detailed = self._calculate_available_slots(
                data,
                service_duration,
                existing_appointments.get('appointments', []),
                avail_rules,
                empresa_config, # Passar a configuração da empresa para o cálculo
                professional_id=professional_id,
                service_id=service_id,
            )
            available_slots = detailed.get("available_slots", []) if isinstance(detailed, dict) else detailed
            matched_professional_id = detailed.get("matched_professional_id") if isinstance(detailed, dict) else None
            by_professional = detailed.get("by_professional", []) if isinstance(detailed, dict) else []
            
            if available_slots:
                return {
                    "available": True,
                    "date": data,
                    "service_duration": service_duration,
                    "available_slots": available_slots,
                    "count": len(available_slots),
                    "matched_professional_id": matched_professional_id,
                    "by_professional": by_professional,
                    "message": (
                        f"Encontrados {len(available_slots)} horários disponíveis para {data} (duração: {service_duration} min)"
                        + (" — filtro por profissional aplicado" if (professional_id or (empresa_config.get('current_context') or {}).get('profissional_nome')) else "")
                    ),
                }
            else:
                return {
                    "available": False,
                    "date": data,
                    "service_duration": service_duration,
                    "matched_professional_id": matched_professional_id,
                    "message": "Nenhum horário disponível encontrado para esta data e duração de serviço"
                }
            
        except Exception as e:
            logger.error(f"Erro ao verificar disponibilidade: {e}")
            return {"error": f"Erro na verificação: {str(e)}"}
    
    def _get_service_duration(self, service_id: str, empresa_config: Dict[str, Any]) -> Optional[int]:
        """Busca a duração real do serviço na API"""
        try:
            # Se não houver service_id, retorna duração padrão sem chamar API
            if not service_id:
                return 60

            # Resolver base URL com fallback
            safe_base_url = (
                empresa_config.get('trinks_base_url')
                or (empresa_config.get('trinks_config', {}) or {}).get('base_url')
                or 'https://api.trinks.com/v1'
            )

            headers = {
                'X-API-KEY': empresa_config.get("trinks_api_key", ""),
                'estabelecimentoId': empresa_config.get('trinks_estabelecimento_id', ''),
                'Content-Type': 'application/json'
            }
            
            # Buscar detalhes do serviço
            response = requests.get(
                f"{safe_base_url}/servicos/{service_id}",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                service_data = response.json()
                return service_data.get('duracaoEmMinutos', 60)
            else:
                # Fallback: buscar na lista de serviços
                response_list = requests.get(
                    f"{safe_base_url}/servicos",
                    headers=headers,
                    timeout=30
                )
                
                if response_list.status_code == 200:
                    services = response_list.json().get('data', [])
                    for service in services:
                        try:
                            if service.get('id') == int(service_id):
                                return service.get('duracaoEmMinutos', 60)
                        except Exception:
                            continue
            
            return 60  # Duração padrão se não conseguir buscar
            
        except Exception as e:
            logger.error(f"Erro ao buscar duração do serviço: {e}")
            return 60
    
    def _get_existing_appointments(self, data: str, empresa_config: Dict[str, Any], 
                                  professional_id: str = None) -> Dict[str, Any]:
        """Busca agendamentos existentes para uma data"""
        try:
            # Resolver base URL com fallback
            safe_base_url = (
                empresa_config.get('trinks_base_url')
                or (empresa_config.get('trinks_config', {}) or {}).get('base_url')
                or 'https://api.trinks.com/v1'
            )

            headers = {
                'X-API-KEY': empresa_config.get("trinks_api_key", ""),
                'estabelecimentoId': empresa_config.get('trinks_estabelecimento_id', ''),
                'Content-Type': 'application/json'
            }
            
            params = {'data': data}
            if professional_id:
                params['profissionalId'] = professional_id
            
            response = requests.get(
                f"{safe_base_url}/agendamentos",
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
                                  avail_rules: Dict[str, Any],
                                  empresa_config: Dict[str, Any],
                                  professional_id: Optional[str] = None,
                                  service_id: Optional[str] = None) -> Dict[str, Any]:
        """Calcula slots disponíveis considerando duração real do serviço. Retorna {available_slots, matched_professional_id}."""
        try:
            # PRIMEIRO: Tentar obter horários reais da API Trinks
            # Precisamos da configuração da empresa, vamos tentar obtê-la do contexto
            empresa_config = empresa_config # Passar a configuração da empresa para o cálculo
            
            detailed = self._get_trinks_real_availability(data, empresa_config, professional_id=professional_id, service_id=service_id)
            if isinstance(detailed, dict) and detailed.get("available_slots"):
                logger.info(f"✅ Usando horários reais da API Trinks: {len(detailed['available_slots'])} slots")
                return detailed
            
            # FALLBACK: Lógica interna se API Trinks falhar
            logger.warning("⚠️ API Trinks não retornou dados, usando lógica interna")
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
            
            return {"available_slots": available_slots, "matched_professional_id": professional_id}
            
        except Exception as e:
            logger.error(f"Erro ao calcular slots disponíveis: {e}")
            return {"available_slots": [], "matched_professional_id": professional_id}
    
    def _get_trinks_real_availability(self, data: str, empresa_config: Dict[str, Any], professional_id: Optional[str] = None, service_id: Optional[str] = None) -> Dict[str, Any]:
        """Obtém horários reais disponíveis da API Trinks e retorna {available_slots, matched_professional_id}."""
        try:
            logger.info(f"🔍 _get_trinks_real_availability chamada para data: {data}")
            logger.info(f"🔍 Configuração da empresa: {empresa_config.keys() if empresa_config else 'None'}")
            
            # Verificar se temos configuração da empresa
            if not empresa_config:
                logger.warning("Configuração da empresa não encontrada para API Trinks")
                return {"available_slots": [], "matched_professional_id": None}
            
            # Obter regras da API
            avail_rules = api_rules_engine.get_availability_check_rules(empresa_config)
            if not avail_rules:
                logger.warning("Regras de disponibilidade não configuradas")
                return {"available_slots": [], "matched_professional_id": None}
            
            logger.info(f"🔍 Regras obtidas: {avail_rules.keys() if avail_rules else 'None'}")
            
            # Endpoint para verificar disponibilidade
            endpoint = avail_rules.get('api_endpoint', '/agendamentos/profissionais/{data}')
            endpoint = endpoint.replace('{data}', data)
            
            # Parâmetros obrigatórios
            params = {
                'estabelecimentoId': empresa_config.get('trinks_estabelecimento_id') or empresa_config.get('estabelecimentoId')
            }
            # Filtros opcionais
            if professional_id:
                params['profissionalId'] = professional_id
            if service_id:
                params['servicoId'] = service_id
            
            logger.info(f"🔍 Endpoint: {endpoint}")
            logger.info(f"🔍 Params: {params}")
            
            # Fazer chamada para API Trinks
            logger.info(f"🔍 Chamando API Trinks: {endpoint} com params: {params}")
            
            result = self.api_tools.call_api(
                api_name="Trinks",
                endpoint_path=endpoint,
                method="GET",
                config=empresa_config.get('trinks_config', empresa_config),
                **params
            )
            
            logger.info(f"📡 Resposta da API Trinks: {result[:200]}...")
            
            # Processar resposta
            if isinstance(result, str):
                try:
                    import json
                    # Alguns chamadores retornam string com prefixo
                    # "Sucesso na operação <API> <endpoint>: { ...json... }"
                    if result.strip().startswith("Sucesso na operação"):
                        brace_idx = result.find('{')
                        if brace_idx != -1:
                            result_json_str = result[brace_idx:]
                            result_data = json.loads(result_json_str)
                        else:
                            logger.error("Resposta de sucesso sem corpo JSON")
                            return {"available_slots": [], "matched_professional_id": None}
                    else:
                        result_data = json.loads(result)
                except Exception as _:
                    logger.error("Falha ao fazer parse da resposta JSON da API Trinks")
                    return {"available_slots": [], "matched_professional_id": None}
            else:
                result_data = result
            
            # Extrair horários disponíveis
            available_slots = []
            matched_professional_id: Optional[str] = None
            by_professional: List[Dict[str, Any]] = []
            if result_data and isinstance(result_data, dict):
                data_list = result_data.get('data', [])
                if isinstance(data_list, list):
                    # Montar lista por profissional (independente do filtro)
                    for profissional in data_list:
                        try:
                            pid = str(profissional.get('id')) if profissional.get('id') is not None else None
                            pname = (profissional.get('nome') or '').strip()
                            pslots = profissional.get('horariosVagos', [])
                            if isinstance(pslots, list):
                                by_professional.append({
                                    'id': pid,
                                    'nome': pname,
                                    'slots': list(pslots)
                                })
                        except Exception:
                            continue
                    # Se houver professional_id, filtrar diretamente
                    if professional_id:
                        for profissional in data_list:
                            if str(profissional.get('id')) == str(professional_id):
                                horarios_vagos = profissional.get('horariosVagos', [])
                                if isinstance(horarios_vagos, list) and horarios_vagos:
                                    available_slots = list(horarios_vagos)
                                matched_professional_id = str(profissional.get('id'))
                                break
                    else:
                        # Tentar resolver por nome no contexto
                        ctx = empresa_config.get('current_context') or {}
                        prof_name_ctx = (ctx.get('profissional_nome') or '').strip().lower()
                        if prof_name_ctx:
                            for profissional in data_list:
                                pname = (profissional.get('nome') or '').strip().lower()
                                if prof_name_ctx and prof_name_ctx in pname:
                                    horarios_vagos = profissional.get('horariosVagos', [])
                                    if isinstance(horarios_vagos, list) and horarios_vagos:
                                        available_slots = list(horarios_vagos)
                                    matched_professional_id = str(profissional.get('id'))
                                    logger.info(f"✅ Profissional identificado na disponibilidade: {prof_name_ctx} -> {matched_professional_id}")
                                    break
                        # Se ainda não filtrou por profissional, agregue geral
                        # Importante: se o usuário especificou um profissional por nome,
                        # NÃO agregamos horários de outros profissionais. Mantemos vazio
                        # para indicar que essa profissional não tem horários.
                        if not available_slots and not prof_name_ctx:
                            for profissional in data_list:
                                horarios_vagos = profissional.get('horariosVagos', [])
                                if isinstance(horarios_vagos, list) and horarios_vagos:
                                    available_slots.extend(horarios_vagos)
                                    logger.info(f"✅ Profissional {profissional.get('nome', 'N/A')}: {len(horarios_vagos)} horários")
            
            # Remover duplicatas e ordenar (se vieram)
            available_slots = sorted(list(set(available_slots)))
            
            logger.info(f"🎯 Total de horários disponíveis na API Trinks: {len(available_slots)}")
            return {"available_slots": available_slots, "matched_professional_id": matched_professional_id, "by_professional": by_professional}
            
        except Exception as e:
            logger.error(f"Erro ao obter disponibilidade real da API Trinks: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {"available_slots": [], "matched_professional_id": None}
    
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

    def list_professionals(self, empresa_config: Dict[str, Any], nome: Optional[str] = None) -> Dict[str, Any]:
        """Lista profissionais do estabelecimento (opcionalmente filtrando por nome)."""
        try:
            params: Dict[str, Any] = {
                'estabelecimentoId': empresa_config.get('trinks_estabelecimento_id') or empresa_config.get('estabelecimentoId')
            }
            if nome:
                params['nome'] = nome
            result = self.api_tools.call_api(
                api_name="Trinks",
                endpoint_path="profissionais",
                method="GET",
                config=empresa_config.get('trinks_config', empresa_config),
                **params
            )
            # Parse seguro
            data: Any
            if isinstance(result, str):
                import json
                if result.strip().startswith("Sucesso na operação"):
                    brace_idx = result.find('{')
                    data = json.loads(result[brace_idx:]) if brace_idx != -1 else {}
                else:
                    data = json.loads(result)
            else:
                data = result
            profs = data.get('data') or data.get('items') or []
            return {"success": True, "professionals": profs}
        except Exception as e:
            logger.error(f"Erro ao listar profissionais: {e}")
            return {"success": False, "error": str(e)}

    def list_services(self, empresa_config: Dict[str, Any], nome: Optional[str] = None) -> Dict[str, Any]:
        """Lista serviços do estabelecimento (opcionalmente filtrando por nome)."""
        try:
            params: Dict[str, Any] = {
                'estabelecimentoId': empresa_config.get('trinks_estabelecimento_id') or empresa_config.get('estabelecimentoId')
            }
            if nome:
                params['nome'] = nome
            result = self.api_tools.call_api(
                api_name="Trinks",
                endpoint_path="servicos",
                method="GET",
                config=empresa_config.get('trinks_config', empresa_config),
                **params
            )
            data: Any
            if isinstance(result, str):
                import json
                if result.strip().startswith("Sucesso na operação"):
                    brace_idx = result.find('{')
                    data = json.loads(result[brace_idx:]) if brace_idx != -1 else {}
                else:
                    data = json.loads(result)
            else:
                data = result
            servs = data.get('data') or data.get('items') or []
            return {"success": True, "services": servs}
        except Exception as e:
            logger.error(f"Erro ao listar serviços: {e}")
            return {"success": False, "error": str(e)}

    def get_service_prices(self, empresa_config: Dict[str, Any], servico_id: Optional[str] = None, servico_nome: Optional[str] = None) -> Dict[str, Any]:
        """Consulta preços de um serviço por id ou nome (heurística simples)."""
        try:
            # Se temos id, buscar diretamente; senão listar e filtrar por nome
            if servico_id:
                params = {
                    'estabelecimentoId': empresa_config.get('trinks_estabelecimento_id') or empresa_config.get('estabelecimentoId')
                }
                result = self.api_tools.call_api(
                    api_name="Trinks",
                    endpoint_path=f"servicos/{servico_id}",
                    method="GET",
                    config=empresa_config.get('trinks_config', empresa_config),
                    **params
                )
                import json
                if isinstance(result, str):
                    if result.strip().startswith("Sucesso na operação"):
                        brace_idx = result.find('{')
                        data = json.loads(result[brace_idx:]) if brace_idx != -1 else {}
                    else:
                        data = json.loads(result)
                else:
                    data = result
                item = data.get('data') or data
                preco = item.get('preco') or item.get('valor')
                return {"success": True, "price": preco, "currency": item.get('moeda')}
            # Por nome
            listed = self.list_services(empresa_config, nome=servico_nome)
            if not listed.get('success'):
                return listed
            servs = listed.get('services', [])
            chosen = None
            nome_norm = (servico_nome or '').strip().lower()
            for s in servs:
                if nome_norm and nome_norm in (s.get('nome', '').strip().lower()):
                    chosen = s
                    break
            if not chosen and servs:
                chosen = servs[0]
            if not chosen:
                return {"success": False, "error": "Serviço não encontrado"}
            preco = chosen.get('preco') or chosen.get('valor')
            return {"success": True, "price": preco, "currency": chosen.get('moeda'), "service": chosen}
        except Exception as e:
            logger.error(f"Erro ao consultar preços: {e}")
            return {"success": False, "error": str(e)}

# Instância global das ferramentas inteligentes
trinks_intelligent_tools = TrinksIntelligentTools() 