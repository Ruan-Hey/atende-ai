#!/usr/bin/env python3
"""
Ferramentas Inteligentes para API Trinks
Usa TrinksRules diretamente para operações inteligentes
CORRIGIDO PARA PRODUÇÃO - Considera duração do serviço
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rules.trinks_rules import TrinksRules
from .api_tools import APITools
import requests
from langchain.schema import SystemMessage, HumanMessage, AIMessage
import math
from difflib import SequenceMatcher

# Corrigir importação deprecated do OpenAI
try:
    from langchain_openai import OpenAI
except ImportError:
    try:
        from langchain_community.llms import OpenAI
    except ImportError:
        from langchain.llms import OpenAI

logger = logging.getLogger(__name__)

class TrinksIntelligentTools:
    """Ferramentas inteligentes para operações com API Trinks"""
    
    def __init__(self, empresa_config: Dict[str, Any] = None):
        self.api_tools = APITools()
        self.empresa_config = empresa_config
        # Inicializa as regras do Trinks diretamente
        self.trinks_rules = TrinksRules() if empresa_config else None
        # Inicializa o LLM com configuração dinâmica
        self.llm = None  # Será configurado quando necessário
    
    def _get_llm(self, empresa_config: Dict[str, Any] = None):
        """Configura e retorna o LLM com a API key da empresa"""
        if self.llm is None:
            # Usar empresa_config passado ou armazenado na instância
            config = empresa_config or self.empresa_config
            if not config:
                raise ValueError("Configuração da empresa não fornecida")
            
            # Buscar a chave OpenAI da configuração da empresa
            openai_key = config.get('openai_config', {}).get('openai_key')
            if not openai_key:
                raise ValueError("OpenAI API key não configurada para esta empresa")
            
            self.llm = OpenAI(
                api_key=openai_key,
                temperature=0.7
            )
        return self.llm
    
    def _is_trinks_api(self, empresa_config: Dict[str, Any]) -> bool:
        """Verifica se é API Trinks"""
        return empresa_config.get('trinks_enabled', False)
    
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
            if not self._is_trinks_api(empresa_config):
                return {"error": "API Trinks não está ativa para esta empresa"}
            
            # Limpar CPF (remover pontos e traços)
            cpf_limpo = re.sub(r'[^\d]', '', cpf)
            
            # Preparar parâmetros da busca
            search_params = {
                "cpf": cpf_limpo,
                "estabelecimentoId": empresa_config.get('trinks_estabelecimento_id')
            }
            
            # Fazer busca na API
            result = self.api_tools.call_api(
                api_name="Trinks",
                endpoint_path="/clients/search",
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
                "suggest_create": True
                # ✅ Sem mensagem fixa - Smart Agent gera!
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
            if not self._is_trinks_api(empresa_config):
                return {"error": "API Trinks não está ativa para esta empresa"}
            
            # Obter regras de detecção de serviço
            service_rules = self.trinks_rules.get_service_detection_rules()
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
                "suggestions": list(service_mapping.keys())
                # ✅ Sem mensagem fixa - Smart Agent gera!
            }
            
        except Exception as e:
            logger.error(f"Erro ao detectar serviço: {e}")
            return {"error": f"Erro na detecção: {str(e)}"}
    
    def _search_service_in_api(self, service_name: str, empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """Busca serviço na API Trinks"""
        try:
            service_rules = self.trinks_rules.get_service_detection_rules()
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
                "service_name": service_name
                # ✅ Sem mensagem fixa - Smart Agent gera!
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
            if not self._is_trinks_api(empresa_config):
                return {"error": "API Trinks não está ativa para esta empresa"}
            
            # Obter regras de busca de profissionais
            prof_rules = self.trinks_rules.get_professional_search_rules()
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
                        "count": len(professionals)
                        # ✅ Sem mensagem fixa - Smart Agent gera!
                    }
            
            return {
                "found": False
                # ✅ Sem mensagem fixa - Smart Agent gera!
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

    def _check_availability_with_looping_internal(self, data: str, service_id: str, empresa_config: Dict[str, Any], 
                                                 professional_id: str = None, max_attempts: int = 7) -> Dict[str, Any]:
        """
        Verifica disponibilidade com looping de até 7 tentativas, pulando sábados e domingos.
        Função interna para evitar recursão.
        
        Args:
            data: Data inicial no formato YYYY-MM-DD
            service_id: ID do serviço
            empresa_config: Configuração da empresa
            professional_id: ID do profissional específico (opcional)
            max_attempts: Número máximo de tentativas (padrão: 7)
            
        Returns:
            Dict com horários disponíveis e informações sobre o looping
        """
        try:
            logger.info(f"🔄 Iniciando verificação de disponibilidade com looping para data: {data}")
            
            # Converter data inicial para datetime
            current_date = datetime.strptime(data, '%Y-%m-%d')
            attempts = 0
            found_slots = False
            next_available_date = None
            next_available_slots = []
            
            while attempts < max_attempts and not found_slots:
                current_date_str = current_date.strftime('%Y-%m-%d')
                weekday = current_date.weekday()  # 0=Segunda, 6=Domingo
                
                # Pular sábados (5) e domingos (6)
                if weekday in [5, 6]:
                    logger.info(f"⏭️ Pulando {current_date_str} (fim de semana)")
                    current_date += timedelta(days=1)
                    attempts += 1
                    continue
                
                logger.info(f"🔍 Tentativa {attempts + 1}: Verificando disponibilidade para {current_date_str}")
                
                # Verificar disponibilidade para a data atual usando a API diretamente
                # (sem chamar check_professional_availability para evitar recursão)
                availability_result = self._get_trinks_real_availability(
                    current_date_str, 
                    empresa_config, 
                    professional_id, 
                    service_id
                )
                
                if availability_result.get('available_slots'):
                    # Encontrou slots disponíveis
                    found_slots = True
                    next_available_date = current_date_str
                    next_available_slots = availability_result.get('available_slots', [])
                    logger.info(f"✅ Encontrou {len(next_available_slots)} slots disponíveis para {next_available_date}")
                    break
                else:
                    logger.info(f"❌ Nenhum slot disponível para {current_date_str}")
                    current_date += timedelta(days=1)
                    attempts += 1
            
            # Preparar resposta
            if found_slots:
                # Sucesso: retornar dados da data com slots disponíveis
                return {
                    "success": True,
                    "original_date": data,
                    "next_available_date": next_available_date,
                    "attempts_made": attempts,
                    "available_slots": next_available_slots,
                    "matched_professional_id": availability_result.get('matched_professional_id'),
                    "by_professional": availability_result.get('by_professional', []),
                    "profissionais_disponiveis": availability_result.get('profissionais_disponiveis', []),
                    "total_profissionais": availability_result.get('total_profissionais', 0),
                    "profissionais_nomes": availability_result.get('profissionais_nomes', []),
                    "looping_info": {
                        "total_attempts": attempts,
                        "skipped_weekends": attempts - len([d for d in range(attempts) if (current_date - timedelta(days=d)).weekday() not in [5, 6]]),
                        "message": f"Não há disponibilidade para {data}. Próxima data com horários: {next_available_date} [{', '.join(next_available_slots)}]"
                    }
                }
            else:
                # Falha: não encontrou slots em nenhuma das tentativas
                return {
                    "success": False,
                    "original_date": data,
                    "attempts_made": attempts,
                    "available_slots": [],
                    "matched_professional_id": None,
                    "looping_info": {
                        "total_attempts": attempts,
                        "message": f"Não foi possível encontrar horários disponíveis em {attempts} tentativas. Tente uma data mais distante."
                    }
                }
                
        except Exception as e:
            logger.error(f"Erro ao verificar disponibilidade com looping: {e}")
            return {
                "success": False,
                "error": str(e),
                "original_date": data,
                "available_slots": []
            }

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
            if not self._is_trinks_api(empresa_config):
                return {"error": "API Trinks não está ativa para esta empresa"}
            
            # Obter regras de verificação de disponibilidade
            avail_rules = self.trinks_rules.get_availability_check_rules(self.empresa_config)
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
            
            # ✅ ESTRUTURAR DADOS para o Agent (seguindo arquitetura Rules → Tools → Integrations)
            response_data = {
                "available": bool(available_slots),
                "date": data,
                "service_duration": service_duration,
                "available_slots": available_slots,
                "matched_professional_id": matched_professional_id,
                "by_professional": by_professional
            }
            
            # Adicionar informações dos profissionais se disponível
            if by_professional:
                response_data["profissionais_disponiveis"] = by_professional
                response_data["total_profissionais"] = len(by_professional)
                response_data["profissionais_nomes"] = [
                    p.get('nome') for p in by_professional if p.get('nome')
                ]
            
            # ✅ Se não há slots disponíveis, verificar se deve usar looping automático
            if not available_slots:
                # Verificar se a empresa tem configuração para usar looping automático
                use_auto_looping = empresa_config.get('auto_looping_disponibilidade', True)
                
                if use_auto_looping:
                    logger.info(f"🔄 Nenhum slot disponível para {data}. Iniciando verificação com looping automático...")
                    
                    # Usar a nova função de looping (sem recursão)
                    looping_result = self._check_availability_with_looping_internal(
                        data, service_id, empresa_config, professional_id
                    )
                    
                    if looping_result.get('success'):
                        # Atualizar dados com informações do looping
                        response_data.update(looping_result)
                        response_data["available"] = True  # Agora temos slots disponíveis
                        response_data["looping_used"] = True
                        logger.info(f"✅ Looping automático encontrou disponibilidade: {looping_result.get('looping_info', {}).get('message', '')}")
                    else:
                        response_data["looping_used"] = True
                        response_data["looping_info"] = looping_result.get('looping_info', {})
                        logger.info(f"⚠️ Looping automático não encontrou disponibilidade após {looping_result.get('attempts_made', 0)} tentativas")
            
            return response_data
            
        except Exception as e:
            logger.error(f"Erro ao verificar disponibilidade: {e}")
            return {"error": f"Erro na verificação: {str(e)}", "available_slots": []}
    
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
            
            # ✅ API Trinks sempre retorna dados válidos
            if isinstance(detailed, dict):
                # Mapear resposta da API Trinks para formato esperado pelo agente
                mapped_response = self._map_trinks_response_to_agent_format(detailed)
                
                if detailed.get("available_slots"):
                    # ✅ Tem horários disponíveis
                    logger.info(f"✅ Usando horários reais da API Trinks: {len(detailed['available_slots'])} slots")
                    return self._return_structured_data_for_agent(detailed, {"data": data}, "com_horarios")
                else:
                    # ✅ API funcionou, mas sem horários disponíveis (comportamento normal)
                    logger.info(f"✅ API Trinks funcionou, mas sem horários disponíveis para {data} (comportamento normal)")
                    return self._return_structured_data_for_agent(detailed, {"data": data}, "sem_disponibilidade_normal")
            
            # ❌ FALLBACK: Só se API Trinks realmente falhar
            logger.warning("⚠️ API Trinks falhou ou não retornou dados válidos, usando lógica interna")
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
            
            # ✅ Retornar dados estruturados para o Agent (seguindo arquitetura Rules → Tools → Integrations)
            return self._return_structured_data_for_agent(
                {"available_slots": available_slots, "matched_professional_id": professional_id},
                {"profissional": "fallback", "data": data},
                "fallback_interno"
            )
            
        except Exception as e:
            logger.error(f"Erro ao calcular slots disponíveis: {e}")
            return {"available_slots": [], "matched_professional_id": professional_id}
    
    def _return_structured_data_for_agent(self, trinks_response: Dict[str, Any], original_data: Dict[str, Any], status: str = "success") -> Dict[str, Any]:
        """
        ✅ Retorna dados estruturados para o Agent seguindo arquitetura Rules → Tools → Integrations
        O Agent recebe dados já prontos, sem necessidade de manipulação
        """
        try:
            # ✅ DEBUG: Verificar tipos dos parâmetros
            logger.info(f"🔍 DEBUG _return_structured_data_for_agent:")
            logger.info(f"   trinks_response type: {type(trinks_response)}")
            logger.info(f"   original_data type: {type(original_data)}")
            logger.info(f"   original_data value: {original_data}")
            
            # ✅ Validar que original_data é um dicionário
            if not isinstance(original_data, dict):
                logger.error(f"❌ original_data não é um dicionário: {type(original_data)} - {original_data}")
                # Converter para dicionário se for string
                if isinstance(original_data, str):
                    original_data = {"data": original_data}
                    logger.info(f"✅ Convertido string para dicionário: {original_data}")
                else:
                    original_data = {"data": str(original_data)}
                    logger.info(f"✅ Convertido para dicionário: {original_data}")
            
            # ✅ Estruturar dados básicos
            structured_data = {
                'profissional': original_data.get('profissional'),
                'procedimento': original_data.get('procedimento'),
                'data': original_data.get('data'),
                'horario': original_data.get('horario'),
                'status': status
            }
            
            # ✅ Adicionar dados de disponibilidade da API Trinks (já estruturados pela função anterior)
            if isinstance(trinks_response, dict):
                # ✅ Os dados já vêm estruturados com 'profissionais_disponiveis', 'total_profissionais', etc.
                structured_data.update(trinks_response)
                
                # ✅ Log para confirmar que os dados estão corretos
                if trinks_response.get('profissionais_disponiveis'):
                    logger.info(f"✅ Dados dos profissionais já estruturados: {len(trinks_response['profissionais_disponiveis'])} profissionais")
                else:
                    logger.warning(f"⚠️ Dados dos profissionais não encontrados em: {list(trinks_response.keys())}")
            
            logger.info(f"✅ Dados estruturados retornados para o Agent: {list(structured_data.keys())}")
            return structured_data
            
        except Exception as e:
            logger.error(f"Erro ao estruturar dados para o Agent: {e}")
            # Retornar dados básicos se estruturação falhar
            return original_data
    
    def _map_trinks_response_to_agent_format(self, trinks_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        ✅ Mapeia resposta da API Trinks para formato esperado pelo agente
        Seguindo arquitetura Rules → Tools → Integrations
        """
        try:
            # Obter regras de mapeamento das Rules
            from rules.trinks_rules import TrinksRules
            rules = TrinksRules()
            api_rules = rules.get_availability_check_rules_expanded()
            mapping_rules = api_rules.get('api_response_mapping', {}).get('trinks_format', {})
            
            # Mapear campos conforme regras
            mapped_response = trinks_response.copy()
            
            # ✅ Mapear dados dos profissionais para formato do agente
            # Formato 1: Resposta direta da API Trinks (com 'data')
            if trinks_response.get('data'):
                profissionais_data = trinks_response.get('data', [])
                
                # Mapear conforme regras das Rules
                mapped_response['profissionais_disponiveis'] = profissionais_data
                mapped_response['total_profissionais'] = len(profissionais_data)
                mapped_response['profissionais_nomes'] = [
                    p.get('nome') for p in profissionais_data if p.get('nome')
                ]
                
                logger.info(f"✅ Resposta da API Trinks mapeada para formato do agente")
                logger.info(f"   📊 Profissionais: {len(profissionais_data)}")
                logger.info(f"   📝 Nomes: {mapped_response['profissionais_nomes']}")
            
            # ✅ Formato 2: Dados processados pela função _get_trinks_real_availability (com 'by_professional')
            elif trinks_response.get('by_professional'):
                profissionais_data = trinks_response.get('by_professional', [])
                
                # Mapear conforme regras das Rules
                mapped_response['profissionais_disponiveis'] = profissionais_data
                mapped_response['total_profissionais'] = len(profissionais_data)
                mapped_response['profissionais_nomes'] = [
                    p.get('nome') for p in profissionais_data if p.get('nome')
                ]
                
                logger.info(f"✅ Dados processados mapeados para formato do agente")
                logger.info(f"   📊 Profissionais: {len(profissionais_data)}")
                logger.info(f"   📝 Nomes: {mapped_response['profissionais_nomes']}")
            
            return mapped_response
            
        except Exception as e:
            logger.error(f"Erro ao mapear resposta da API Trinks: {e}")
            # Retornar resposta original se mapeamento falhar
            return trinks_response
    
    def _get_trinks_real_availability(self, data: str, empresa_config: Dict[str, Any], professional_id: Optional[str] = None, service_id: Optional[str] = None) -> Dict[str, Any]:
        """Obtém horários reais disponíveis da API Trinks e retorna {available_slots, matched_professional_id}."""
        try:
            logger.info(f"🔍 ===== FUNÇÃO CHAMADA =====")
            logger.info(f"🔍 _get_trinks_real_availability chamada para data: {data}")
            logger.info(f"🔍 professional_id: {professional_id}")
            logger.info(f"🔍 service_id: {service_id}")
            logger.info(f"🔍 Configuração da empresa: {empresa_config.keys() if empresa_config else 'None'}")
            logger.info(f"🔍 =========================")
            
            # Verificar se temos configuração da empresa
            if not empresa_config:
                logger.warning("Configuração da empresa não encontrada para API Trinks")
                return {"available_slots": [], "matched_professional_id": None}
            
            # Obter regras da API
            avail_rules = self.trinks_rules.get_availability_check_rules(empresa_config)
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
            
            # CORREÇÃO: Enviar apenas os parâmetros necessários
            # A API Trinks aceita apenas estabelecimentoId como obrigatório
            # Os outros são filtros opcionais
            if professional_id:
                params['profissionalId'] = professional_id
            if service_id:
                params['servicoId'] = service_id
            
            # NÃO enviar 'data' como parâmetro - ela já está na URL
            # params['data'] = data  # ← REMOVIDO
            
            # LOGS DETALHADOS PARA DEBUG
            logger.info(f"🔍 ===== DEBUG ENDPOINT =====")
            logger.info(f"🔍 Regras obtidas: {avail_rules}")
            logger.info(f"🔍 api_endpoint das regras: {avail_rules.get('api_endpoint', 'NÃO DEFINIDO')}")
            logger.info(f"🔍 Endpoint final: {endpoint}")
            logger.info(f"🔍 Base URL: {empresa_config.get('trinks_base_url') or empresa_config.get('trinks_config', {}).get('base_url', 'NÃO DEFINIDO')}")
            logger.info(f"🔍 URL completa: {(empresa_config.get('trinks_base_url') or empresa_config.get('trinks_config', {}).get('base_url', '')) + endpoint}")
            logger.info(f"🔍 Params: {params}")
            logger.info(f"🔍 =========================")
            
            # Fazer chamada para API Trinks
            logger.info(f"🔍 Chamando API Trinks: {endpoint} com params: {params}")
            logger.info(f"🔍 Tipo de chamada: GET com query parameters")
            
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
            
            # ✅ GARANTIR que AMBOS os casos sejam cobertos:
            # 1. Caso: Buscar profissionais livres (sem filtro) → usar 'data' da API
            # 2. Caso: Profissional específico → usar 'by_professional' processado
            
            response_data = {
                "available_slots": available_slots, 
                "matched_professional_id": matched_professional_id
            }
            
            # ✅ SEMPRE incluir dados dos profissionais para o Agent
            if by_professional:
                # Caso 2: Profissional específico processado
                response_data["by_professional"] = by_professional
                response_data["profissionais_disponiveis"] = by_professional
                response_data["total_profissionais"] = len(by_professional)
                response_data["profissionais_nomes"] = [
                    p.get('nome') for p in by_professional if p.get('nome')
                ]
                logger.info(f"✅ Caso 2: Profissional específico - {len(by_professional)} profissionais")
                
                # Cache temporário movido para Rules
                logger.info(f"✅ Caso 2: Profissional específico - {len(by_professional)} profissionais")
            else:
                # Caso 1: Buscar profissionais livres - usar dados originais da API
                response_data["data"] = data_list  # Dados originais da API Trinks
                response_data["profissionais_disponiveis"] = data_list
                response_data["total_profissionais"] = len(data_list)
                response_data["profissionais_nomes"] = [
                    p.get('nome') for p in data_list if p.get('nome')
                ]
                logger.info(f"✅ Caso 1: Buscar profissionais livres - {len(data_list)} profissionais")
                
                # Cache temporário movido para Rules
                logger.info(f"✅ Caso 1: Buscar profissionais livres - {len(data_list)} profissionais")
            
            return response_data
            
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
            if not self._is_trinks_api(empresa_config):
                return {"error": "API Trinks não está ativa para esta empresa"}
            
            # Obter regras de criação de reserva
            reservation_rules = self.trinks_rules.get_reservation_creation_rules()
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
            # Log dos parâmetros sendo enviados
            params: Dict[str, Any] = {
                'estabelecimentoId': empresa_config.get('trinks_estabelecimento_id') or empresa_config.get('estabelecimentoId')
            }
            if nome:
                params['nome'] = nome
            
            logger.info(f"🔍 Buscando profissionais com parâmetros: {params}")
            logger.info(f"🔗 Endpoint: profissionais")
            logger.info(f"🔑 Config Trinks: {empresa_config.get('trinks_config', {}).get('base_url', 'N/A')}")
            
            result = self.api_tools.call_api(
                api_name="Trinks",
                endpoint_path="profissionais",
                method="GET",
                config=empresa_config.get('trinks_config', empresa_config),
                **params
            )
            
            # Log do resultado bruto da API
            logger.info(f"📡 Resposta bruta da API Trinks: {type(result)} - {result}")
            
            # Parse seguro
            data: Any
            if isinstance(result, str):
                import json
                if result.strip().startswith("Sucesso na operação"):
                    brace_idx = result.find('{')
                    data = json.loads(result[brace_idx:]) if brace_idx != -1 else {}
                    logger.info(f"📝 Parse de 'Sucesso na operação': {data}")
                else:
                    data = json.loads(result)
                    logger.info(f"📝 Parse de string JSON: {data}")
            else:
                data = result
                logger.info(f"📝 Dados já parseados: {data}")
            
            # Log da estrutura dos dados
            logger.info(f"🏗️ Estrutura dos dados: {list(data.keys()) if isinstance(data, dict) else 'Não é dict'}")
            
            profs = data.get('data') or data.get('items') or []
            logger.info(f"👥 Profissionais extraídos: {len(profs)} profissionais")
            
            # Log detalhado de cada profissional
            if profs:
                logger.info(f"📋 Lista completa de profissionais:")
                for i, prof in enumerate(profs):
                    logger.info(f"   {i+1}. ID: {prof.get('id', 'N/A')} | Nome: {prof.get('nome', 'N/A')} | Especialidade: {prof.get('especialidade', 'N/A')}")
            else:
                logger.warning(f"⚠️ NENHUM profissional encontrado na API!")
                logger.warning(f"⚠️ Dados completos da resposta: {data}")
            
            # CORREÇÃO: Retornar com chave "result" para manter consistência
            return {"success": True, "result": profs, "professionals": profs}
        except Exception as e:
            logger.error(f"❌ Erro ao listar profissionais: {e}")
            logger.error(f"❌ Tipo do erro: {type(e)}")
            import traceback
            logger.error(f"❌ Stack trace: {traceback.format_exc()}")
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
            logger.info(f"🔍 Serviços encontrados na API: {len(servs)} serviços")
            if servs:
                logger.info(f"📋 Primeiros serviços: {[s.get('nome', 'Sem nome') for s in servs[:3]]}")
            return {"success": True, "result": servs}
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

    def intelligent_match_professional(self, nome_procurado: str, profissionais_list: List[Dict[str, Any]], empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Faz match inteligente de profissional usando LLM
        Args:
            nome_procurado: Nome do profissional procurado
            profissionais_list: Lista de profissionais disponíveis
            empresa_config: Configuração da empresa
        Returns:
            Dict com resultado do match
        """
        try:
            # Log detalhado dos parâmetros de entrada
            logger.info(f"🎯 INICIANDO MATCH de profissional: '{nome_procurado}'")
            logger.info(f"📊 Lista de profissionais recebida: {len(profissionais_list)} profissionais")
            logger.info(f"🔍 Tipo da lista: {type(profissionais_list)}")
            
            # Log detalhado de cada profissional na lista
            if profissionais_list:
                logger.info(f"📋 Profissionais disponíveis para match:")
                for i, prof in enumerate(profissionais_list):
                    logger.info(f"   {i+1}. {prof}")
            else:
                logger.warning(f"⚠️ LISTA DE PROFISSIONAIS VAZIA!")
            
            # Verificar se é API Trinks
            if not self._is_trinks_api(empresa_config):
                logger.error(f"❌ API Trinks não está ativa para esta empresa")
                return {"error": "API Trinks não está ativa para esta empresa"}
            
            # Obter regras de match
            match_rules = self.trinks_rules.get_intelligent_match_rules()
            if not match_rules:
                logger.error(f"❌ Regras de match não configuradas")
                return {"error": "Regras de match não configuradas"}
            
            # Prompt LLM para match de profissional
            prompt = f"""Você é um assistente especializado em identificar profissionais de saúde no sistema Trinks.

TAREFA: Identificar qual profissional da lista corresponde ao nome mencionado pelo usuário.

NOME PROCURADO: "{nome_procurado}"

LISTA DE PROFISSIONAIS DISPONÍVEIS:
{profissionais_list}

CARACTERÍSTICAS DO TRINKS:
- Profissionais podem ter apelidos ou nomes abreviados
- Especialidades são importantes para identificação
- Nomes podem ter variações de acentuação
- Sistema brasileiro com nomes em português

REGRAS CRÍTICAS:
1. NUNCA invente IDs, nomes ou dados que não existam na lista
2. SEMPRE use APENAS dados reais da lista fornecida
3. Se não encontrar match, retorne null para id e nome
4. NUNCA crie profissionais fictícios

INSTRUÇÕES:
1. Analise o nome procurado e compare com a lista
2. Considere variações, apelidos e especialidades
3. Retorne o profissional com maior confiança de match
4. Se houver ambiguidade, escolha o mais provável
5. Se não encontrar match, retorne null (não invente dados)

FORMATAÇÃO OBRIGATÓRIA:
- NUNCA use prefixos como "System:", "Resposta:", "JSON:", etc.
- NUNCA adicione texto explicativo antes ou depois do JSON
- NUNCA use aspas duplas no texto, apenas no JSON
- NUNCA invente dados - use apenas os dados reais da lista

EXEMPLO DE RESPOSTA CORRETA:
{{
    "id": "12345",
    "nome": "Dr. João Silva",
    "confianca": "ALTA",
    "razao": "Nome exato encontrado na lista"
}}

EXEMPLO DE RESPOSTA INCORRETA:
System: {{
    "id": "12345",
    "nome": "Dr. João Silva",
    "confianca": "ALTA",
    "razao": "Nome exato encontrado na lista"
}}

IMPORTANTE: 
- RESPONDA APENAS o JSON, sem "System:", sem "Resposta:", sem nenhum prefixo
- O JSON deve começar diretamente com {{ e terminar com }}
- Se usar qualquer prefixo, a resposta será inválida e causará erro
- NUNCA invente dados - use apenas os dados reais da lista

FORMATO DE RESPOSTA (JSON):
{{
    "id": "ID_REAL_DA_LISTA ou null",
    "nome": "NOME_REAL_DA_LISTA ou null",
    "confianca": "ALTA|MEDIA|BAIXA",
    "razao": "Explicação do match considerando características do Trinks"
}}

RESPONDA APENAS o JSON acima, sem nenhum texto adicional, sem aspas, sem prefixos."""

            # Log do prompt sendo enviado para o LLM
            logger.info(f"📝 PROMPT enviado para o LLM:")
            logger.info(f"   Nome procurado: '{nome_procurado}'")
            logger.info(f"   Lista de profissionais: {profissionais_list}")
            
            # Obter LLM configurado
            llm = self._get_llm(empresa_config)
            
            # Construir mensagens para o LLM
            messages = [
                SystemMessage(content=prompt),
                HumanMessage(content=f"Encontre o profissional mais adequado para: {nome_procurado}")
            ]
            
            # Log das mensagens sendo enviadas
            logger.info(f"💬 Mensagens enviadas para o LLM: {len(messages)} mensagens")
            
            # Chamar LLM
            logger.info(f"🤖 Chamando LLM para match de profissional...")
            response = llm.invoke(messages)
            
            # Log da resposta bruta do LLM
            logger.info(f"📡 Resposta bruta do LLM: {type(response)}")
            logger.info(f"📡 Conteúdo da resposta: {response}")
            
            # Processar resposta - o LLM pode retornar string diretamente ou objeto
            response_text = response.content if hasattr(response, 'content') else str(response)
            logger.info(f"📝 Texto extraído da resposta: '{response_text}'")
            
            try:
                import json
                logger.info(f"🔍 Tentando fazer parse JSON da resposta...")
                match_result = json.loads(response_text.strip())
                logger.info(f"✅ Parse JSON bem-sucedido: {match_result}")
                
                # VALIDAÇÃO: Verificar se os dados são reais
                logger.info(f"🔍 Iniciando validação do resultado...")
                match_result = self._validate_match_result(match_result, profissionais_list, "profissional")
                logger.info(f"✅ Validação concluída: {match_result}")
                
                logger.info(f"✅ Match de profissional via LLM: {match_result}")
                return match_result
            except json.JSONDecodeError as json_error:
                logger.warning(f"⚠️ Resposta do LLM não é JSON válido: {response_text}")
                logger.warning(f"⚠️ Erro JSON: {json_error}")
                # Fallback para match local
                logger.info(f"🔄 Usando fallback para match local...")
                return self._fallback_match_professional(nome_procurado, profissionais_list, match_rules)
            
        except Exception as e:
            logger.error(f"❌ Erro no match inteligente de profissional: {e}")
            logger.error(f"❌ Tipo do erro: {type(e)}")
            import traceback
            logger.error(f"❌ Stack trace: {traceback.format_exc()}")
            return {"error": f"Erro no match: {str(e)}"}
    
    def intelligent_match_service(self, nome_procurado: str, servicos_list: List[Dict[str, Any]], empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Faz match inteligente de serviço usando LLM com apenas nomes (solução simples)
        Args:
            nome_procurado: Nome do serviço procurado
            servicos_list: Lista de serviços disponíveis
            empresa_config: Configuração da empresa
        Returns:
            Dict com resultado do match
        """
        try:
            # Verificar se é API Trinks
            if not self._is_trinks_api(empresa_config):
                return {"error": "API Trinks não está ativa para esta empresa"}
            
            # SOLUÇÃO SIMPLES: Extrair apenas nomes para o LLM
            nomes_servicos = [servico.get('nome', '') for servico in servicos_list if servico.get('nome')]
            logger.info(f"🔍 Enviando {len(nomes_servicos)} nomes de serviços para o LLM")
            
            # Prompt LLM para match de serviço (apenas com nomes)
            prompt = f"""Você é um assistente especializado em identificar serviços de saúde no sistema Trinks.

TAREFA: Identificar qual serviço da lista corresponde ao nome mencionado pelo usuário.

NOME PROCURADO: "{nome_procurado}"

LISTA DE NOMES DE SERVIÇOS DISPONÍVEIS:
{nomes_servicos}

INSTRUÇÕES:
1. Analise o nome procurado e identifique palavras-chave
2. Procure por serviços que contenham essas palavras-chave
3. Considere correspondências parciais
4. SEMPRE tente encontrar um match, mesmo que não seja perfeito

REGRAS CRÍTICAS:
1. NUNCA invente nomes que não existam na lista
2. Use correspondência parcial - não exija match exato
3. Se não encontrar match, retorne null para nome
4. NUNCA crie serviços fictícios

FORMATAÇÃO OBRIGATÓRIA:
- NUNCA use prefixos como "System:", "Resposta:", "JSON:", etc.
- NUNCA adicione texto explicativo antes ou depois do JSON
- NUNCA use aspas duplas no texto, apenas no JSON
- NUNCA invente dados - use apenas os dados reais da lista

EXEMPLO DE RESPOSTA CORRETA:
{{
    "nome": "AAA TEste",
    "confianca": "ALTA",
    "razao": "Match exato encontrado na lista"
}}

EXEMPLO DE RESPOSTA INCORRETA:
System: {{
    "nome": "AAA TEste",
    "confianca": "ALTA",
    "razao": "Match exato encontrado na lista"
}}

IMPORTANTE: 
- RESPONDA APENAS o JSON, sem "System:", sem "Resposta:", sem nenhum prefixo
- O JSON deve começar diretamente com {{ e terminar com }}
- Se usar qualquer prefixo, a resposta será inválida e causará erro
- NUNCA invente dados - use apenas os dados reais da lista

FORMATO DE RESPOSTA (JSON):
{{
    "nome": "NOME_REAL_DA_LISTA ou null",
    "confianca": "ALTA|MEDIA|BAIXA",
    "razao": "Explicação do match"
}}

RESPONDA APENAS o JSON acima, sem nenhum texto adicional, sem aspas, sem prefixos."""

            # Obter LLM configurado
            llm = self._get_llm(empresa_config)
            
            # Construir mensagens para o LLM
            messages = [
                SystemMessage(content=prompt),
                HumanMessage(content=f"Encontre o serviço mais adequado para: {nome_procurado}")
            ]
            
            # Chamar LLM
            response = llm.invoke(messages)
            
            # Processar resposta
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            try:
                import json
                match_result = json.loads(response_text.strip())
                
                # BUSCAR SERVIÇO COMPLETO pelo nome retornado
                if match_result.get('nome'):
                    nome_encontrado = match_result.get('nome')
                    for servico in servicos_list:
                        if servico.get('nome') == nome_encontrado:
                            # ✅ CORRIGIDO: Retornar serviço completo com TODOS os campos
                            resultado_final = {
                                "id": servico.get('id'),
                                "nome": servico.get('nome'),
                                "confianca": match_result.get('confianca', 'ALTA'),
                                "razao": match_result.get('razao', 'Match encontrado'),
                                "match_type": "llm_with_names",
                                "duracaoEmMinutos": servico.get('duracaoEmMinutos'),  # ✅ NOVO: Duração do serviço
                                "preco": servico.get('preco'),  # ✅ NOVO: Preço do serviço
                                "categoria": servico.get('categoria'),  # ✅ NOVO: Categoria do serviço
                                "descricao": servico.get('descricao')  # ✅ NOVO: Descrição do serviço
                            }
                            logger.info(f"✅ Match de serviço via LLM: {resultado_final}")
                            return resultado_final
                
                # Se não encontrou o serviço completo
                logger.warning(f"⚠️ Nome retornado pelo LLM não encontrado na lista: {match_result.get('nome')}")
                return {"error": "Nome retornado pelo LLM não encontrado na lista"}
                
            except json.JSONDecodeError:
                logger.warning(f"⚠️ Resposta do LLM não é JSON válido: {response_text}")
                return {"error": "Resposta do LLM não é JSON válido"}
            
        except Exception as e:
            logger.error(f"Erro no match inteligente de serviço: {e}")
            return {"error": f"Erro no match: {str(e)}"}
    
    def extract_data_with_llm(self, message: str, context: Dict[str, Any], empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extrai dados da mensagem usando LLM com HISTÓRICO COMPLETO da conversa
        ARQUITETURA: Rules → Tools → Integrations
        Args:
            message: Mensagem do usuário
            context: Contexto da conversa
            empresa_config: Configuração da empresa
        Returns:
            Dict com dados extraídos
        """
        try:
            # ✅ ARQUITETURA: Verificar se é API Trinks
            if not self._is_trinks_api(empresa_config):
                return {"error": "API Trinks não está ativa para esta empresa"}
            
            # ✅ OBTER REGRAS de extração (seguindo arquitetura)
            extraction_rules = self.trinks_rules.get_data_extraction_rules()
            if not extraction_rules:
                return {"error": "Regras de extração não configuradas"}
            
            # ✅ OBTER HISTÓRICO do contexto (passado pelo Smart Agent)
            conversation_history = context.get('conversation_history', [])
            logger.info(f"📚 Histórico recebido para extração: {len(conversation_history)} mensagens")
            
            # ✅ CONSTRUIR PROMPT INTELIGENTE com histórico completo (mensagem atual PRIORITÁRIA)
            prompt = f"""Você é um assistente especializado em extrair informações de mensagens de WhatsApp para agendamento no sistema Trinks.

⚠️ REGRA CRÍTICA: Você DEVE responder APENAS com o JSON puro, sem repetir o histórico, sem explicações, sem texto adicional.

CONTEXTO ATUAL: Hoje é {datetime.now().strftime('%d/%m/%Y')} (DD/MM/YYYY)

DADOS JÁ EXTRAÍDOS ANTERIORMENTE:
{self._format_extracted_data_context(context.get('extracted_data', {}))}

HISTÓRICO COMPLETO DA CONVERSA:
{self._format_conversation_history(conversation_history)}

MENSAGEM ATUAL: "{message}"

CAMPOS PARA EXTRAIR:
- profissional: Nome do profissional mencionado (deve existir no Trinks)
- procedimento: Nome do procedimento/tratamento (deve existir no Trinks)
- data: Data mencionada (formato YYYY-MM-DD, SEMPRE futura, mínimo 2h de antecedência)
- horario: Horário mencionado (formato HH:MM, dentro do horário de funcionamento)
- servico_id: ID do serviço mencionado (deve existir no Trinks)
- profissional_id: ID do profissional mencionado (deve existir no Trinks)
- cpf: CPF do cliente mencionado
- client_id: ID do cliente mencionado (deve existir no Trinks)
- nome: Nome que o cliente informou no whatsapp
- email: Email que o cliente informou no whatsapp

REGRAS CRÍTICAS DE PRIORIDADE E CONTEXTO:
1. ✅ A MENSAGEM ATUAL TEM PRIORIDADE sobre qualquer dado do histórico/cache
2. ✅ Se a mensagem atual mencionar nova data, use ESSA nova data e mantenha os demais campos do contexto
3. ✅ Se a mensagem atual mencionar novo horário, use ESSE novo horário e mantenha os demais campos do contexto
4. ✅ Se a mensagem atual mencionar novo profissional, use ESSE novo profissional e mantenha os demais campos do contexto
5. ✅ Se a mensagem atual mencionar novo procedimento, use ESSE novo procedimento e mantenha os demais campos do contexto
6. ✅ Use o histórico apenas para preencher campos NÃO mencionados na mensagem atual

REGRAS ESPECÍFICAS PARA EXTRAÇÃO DE NOMES:
1. 🔍 Se a mensagem contém APENAS um nome (ex: "Ruan Gimenes Hey"), SEMPRE extraia como nome do cliente
2. 🔍 Se a mensagem contém frases como "meu nome é", "sou", "chamo-me", extraia o nome
3. 🔍 Nomes podem ter 1, 2, 3 ou mais palavras - preserve a formatação original
4. 🔍 Se a mensagem não contém contexto de agendamento, mas contém nomes, extraia como nome do cliente
5. 🔍 Preserve acentos, espaços e formatação original dos nomes

EXEMPLOS DE PRIORIDADE DA MENSAGEM ATUAL:
- Histórico: "procedimento: AAA TESTE, data: 29/08, servico_id: 1234567890, profissional_id: 1234567890"
- Nova mensagem: "E para dia 01/09?"
- Resultado: {{"procedimento": "AAA TESTE", "data": "2025-09-01"}} ← PROCEDIMENTO PRESERVADO!
- servico_id: 1234567890
- profissional_id: 1234567890

- Histórico: "procedimento: AAA TESTE, data: 29/08, profissional: Maria"
- Nova mensagem: "E às 15h?"
- Resultado: {{"procedimento": "AAA TESTE", "data": "2025-08-29", "profissional": "Maria", "horario": "15:00"}} ← TUDO PRESERVADO!

- Histórico: "profissional: Amabile, procedimento: AAA TESTE, data: 29/08, servico_id: 1234567890, profissional_id: 1234567890"
- Nova mensagem: "troca para a Geraldine dia 01/09"
- Resultado: {{"profissional": "Geraldine", "procedimento": "AAA TESTE", "data": "2025-09-01", "servico_id": "1234567890", "profissional_id": novo id baseado na busca}} ← NOVOS CAMPOS DA MENSAGEM ATUAL PRIORITÁRIOS!

EXEMPLOS ESPECÍFICOS DE EXTRAÇÃO DE NOMES:
- Mensagem: "Meu nome é João Silva" → {{"nome": "João Silva"}}
- Mensagem: "Sou a Maria Santos" → {{"nome": "Maria Santos"}}
- Mensagem: "Ruan Gimenes Hey" → {{"nome": "Ruan Gimenes Hey"}}
- Mensagem: "Ana Paula Costa" → {{"nome": "Ana Paula Costa"}}
- Mensagem: "Carlos Eduardo" → {{"nome": "Carlos Eduardo"}}
- Mensagem: "João" → {{"nome": "João"}}
- Mensagem: "Maria" → {{"nome": "Maria"}}

REGRAS PARA EXTRAÇÃO DE NOMES:
1. Se a mensagem contém APENAS um nome (sem contexto de agendamento), extraia como nome do cliente
2. Se a mensagem contém "meu nome é", "sou", "chamo-me", extraia como nome do cliente
3. Se a mensagem contém apenas palavras que parecem nomes próprios, extraia como nome do cliente
4. Nomes podem ter 1, 2, 3 ou mais palavras (ex: "João", "João Silva", "João Silva Santos")
5. Preserve acentos e formatação original do nome

EXEMPLOS ESPECÍFICOS DE EXTRAÇÃO DE CPF:
- Mensagem: "Meu CPF é 123.456.789-00" → {{"cpf": "12345678900"}}
- Mensagem: "CPF 987.654.321-00" → {{"cpf": "98765432100"}}
- Mensagem: "05286655963" → {{"cpf": "05286655963"}}

EXEMPLOS ESPECÍFICOS DE EXTRAÇÃO DE EMAIL:
- Mensagem: "meu email é joao@email.com" → {{"email": "joao@email.com"}}
- Mensagem: "maria.santos@gmail.com" → {{"email": "maria.santos@gmail.com"}}

INSTRUÇÕES:
1. Analise TODAS as mensagens do histórico em ordem cronológica
2. Identifique o contexto estabelecido (procedimento, profissional, etc.)
3. Preserve esse contexto APENAS onde a mensagem atual NÃO trouxe novos valores ou nao tiver conectado (Ex: Profissional ID e profissioanl | Servico ID e servico)
4. Atualize campos que foram explicitamente mencionados na mensagem atual (data/profissional/procedimento/horário)
5. Use o histórico para preencher somente campos ausentes na mensagem atual
6. NUNCA em hipotee alguma inclua algo a mais na sua saida que não seja o JSON puro assim como tem nas regras de formatação

REGRAS DE VALIDAÇÃO:
1. DATAS: SEMPRE devem ser FUTURAS em relação à data atual
2. Se a mensagem mencionar "dia 29/08", interprete como "29/08/2025" (ano atual)
3. Se a data mencionada for passada, use null
4. PROCEDIMENTOS: SEMPRE extraia o nome mencionado, mesmo com erros de digitação
5. Se mencionar "AAA TEste", extraia exatamente isso como procedimento

FORMATAÇÃO OBRIGATÓRIA:
- NUNCA use prefixos como "System:", "Resposta:", "JSON:", "Human:", etc.
- NUNCA adicione texto explicativo antes ou depois do JSON
- NUNCA use aspas duplas no texto, apenas no JSON
- SEMPRE extraia procedimentos mencionados, mesmo com erros de digitação
- NUNCA repita a mensagem do usuário
- NUNCA adicione "Human:" ou qualquer prefixo
- NUNCA inclua o histórico da conversa na resposta

EXEMPLO DE RESPOSTA CORRETA:
{{
    "profissional": "Maria",
    "procedimento": "AAA TESTE", 
    "data": "2025-09-01",
    "horario": null,
    "servico_id": "1234567890",
    "profissional_id": "1234567890"
}}

IMPORTANTE: 
- RESPONDA APENAS o JSON, sem "System:", sem "Resposta:", sem nenhum prefixo
- O JSON deve começar diretamente com {{ e terminar com }}
- SEMPRE preserve o contexto da conversa anterior
- NUNCA perca informações já estabelecidas
- NUNCA repita o histórico da conversa
- NUNCA adicione texto explicativo
- NUNCA inclua a mensagem do usuário
- APENAS o JSON puro, nada mais

FORMATO DE RESPOSTA (JSON):
{{
    "profissional": "nome ou null",
    "procedimento": "nome ou null", 
    "data": "YYYY-MM-DD ou null",
    "horario": "HH:MM ou null"
}}

RESPONDA APENAS o JSON acima, sem nenhum texto adicional, sem aspas, sem prefixos."""

            # Obter LLM configurado
            llm = self._get_llm(empresa_config)
            
            # ✅ ADICIONAR HISTÓRICO da conversa para o LLM
            conversation_history = context.get('conversation_history', [])
            logger.info(f"📚 Histórico recebido para extração: {len(conversation_history)} mensagens")
            
            # Construir mensagens para o LLM
            messages = [
                SystemMessage(content=prompt),
                HumanMessage(content=message)
            ]

            # Injetar previous_data (ids/estado atual) no contexto da extração
            try:
                previous_data = context.get('previous_data', {}) if isinstance(context, dict) else {}
            except Exception:
                previous_data = {}
            try:
                logger.info(f"🗄️ previous_data (extração): {previous_data}")
            except Exception:
                pass
            if previous_data:
                prev_summary = {
                    'profissional': previous_data.get('profissional'),
                    'profissional_id': previous_data.get('profissional_id'),
                    'procedimento': previous_data.get('procedimento'),
                    'servico_id': previous_data.get('servico_id'),
                    'data': previous_data.get('data'),
                    'horario': previous_data.get('horario'),
                    'cpf': previous_data.get('cpf'),
                    'client_id': previous_data.get('client_id'),
                    'nome': previous_data.get('nome'),
                    'email': previous_data.get('email')
                }
                messages.append(SystemMessage(content=f"ESTADO ATUAL (previous_data): {prev_summary}"))
            
            # ✅ ADICIONAR HISTÓRICO como contexto para o LLM
            if conversation_history:
                # Adicionar mensagens do histórico como contexto
                for msg in conversation_history:
                    if hasattr(msg, 'type'):
                        if msg.type == 'human':
                            messages.append(HumanMessage(content=f"Histórico - Usuário: {msg.content}"))
                        elif msg.type == 'ai':
                            messages.append(AIMessage(content=f"Histórico - Bot: {msg.content}"))
                    else:
                        # Fallback para diferentes tipos de mensagem
                        messages.append(HumanMessage(content=f"Histórico: {str(msg.content)}"))
            
            # Injetar previous_data + extracted_data para validação de campos completos
            previous_data = (context or {}).get('previous_data', {}) if isinstance(context, dict) else {}
            extracted_data = (context or {}).get('extracted_data', {}) if isinstance(context, dict) else {}
            
            # MERGIR os dados para o LLM ver o estado completo atualizado
            merged_data = {**previous_data, **extracted_data}
            
            if merged_data:
                # Mini instrução ao LLM com o estado ATUALIZADO (incluindo dados da mensagem atual)
                current_summary = {
                    'profissional_id': merged_data.get('profissional_id'),
                    'servico_id': merged_data.get('servico_id'),
                    'data': merged_data.get('data'),
                    'horario': merged_data.get('horario')  # ✅ AGORA INCLUI O NOVO HORÁRIO!
                }
                
                # Filtrar apenas campos não vazios para clareza
                non_empty_fields = {k: v for k, v in current_summary.items() if v is not None and v != ""}
                
                if non_empty_fields:
                    messages.append(SystemMessage(content=f"🗄️ ESTADO ATUAL (para decisão): {non_empty_fields}"))
                    logger.info(f"📊 Estado enviado para LLM: {non_empty_fields}")
                else:
                    messages.append(SystemMessage(content="🗄️ ESTADO ATUAL: Nenhum dado coletado ainda"))
                    logger.info("📊 Estado enviado para LLM: Nenhum dado coletado ainda")
            
            # Chamar LLM
            response = llm.invoke(messages)
            
            # Processar resposta - o LLM pode retornar string diretamente ou objeto
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # ✅ LIMPEZA AUTOMÁTICA: Remover prefixos comuns do LLM
            cleaned_response = self._clean_llm_response(response_text)
            
            try:
                import json
                extracted_data = json.loads(cleaned_response.strip())
                
                # VALIDAÇÃO PÓS-EXTRAÇÃO
                extracted_data = self._validate_extracted_data(extracted_data)
                
                logger.info(f"✅ Dados extraídos via LLM: {extracted_data}")
                return extracted_data
            except json.JSONDecodeError:
                logger.warning(f"⚠️ Resposta do LLM não é JSON válido após limpeza: {cleaned_response}")
                logger.warning(f"⚠️ Resposta original: {response_text}")
                # Fallback para extração local
                return self._fallback_extract_data(message, extraction_rules)
            
        except Exception as e:
            logger.error(f"Erro na extração de dados com LLM: {e}")
            return {"error": f"Erro na extração: {str(e)}"}
    
    def _format_conversation_history(self, conversation_history: List) -> str:
        """Formata o histórico da conversa para o prompt do LLM"""
        if not conversation_history:
            return "Nenhuma mensagem anterior na conversa."
        
        formatted_history = []
        for i, msg in enumerate(conversation_history, 1):
            if hasattr(msg, 'type'):
                if msg.type == 'human':
                    formatted_history.append(f"{i}. Usuário: \"{msg.content}\"")
                elif msg.type == 'ai':
                    formatted_history.append(f"{i}. Bot: {msg.content}")
            else:
                # Fallback para diferentes tipos de mensagem
                formatted_history.append(f"{i}. Mensagem: {msg.content}")
        
        return "\n".join(formatted_history)
    
    def detect_intent_with_llm(self, message: str, context: Dict[str, Any], empresa_config: Dict[str, Any]) -> str:
        """
        Detecta a intenção da mensagem usando LLM
        Args:
            message: Mensagem do usuário
            context: Contexto da conversa
            empresa_config: Configuração da empresa (para API key)
        Returns:
            Intenção detectada
        """
        try:
            # Construir prompt para detecção de intenção
            system_prompt = f"""Você é um assistente especializado classificar conversas de WhatsApp de uma clinica de estetica.

CONTEXTO ATUAL: Hoje é {datetime.now().strftime('%d/%m/%Y')} (DD/MM/YYYY).

FUNÇÃO: Analisar a mensagem e retornar APENAS uma das seguintes classificações:

INTENÇÕES DISPONÍVEIS:
- agendar_consulta: Usuário quer marcar um horário    
- cancelar_consulta: Usuário quer cancelar
- reagendar_consulta: Usuário quer mudar horário
- perguntar_informacoes: Usuário faz perguntas gerais
- saudacao: Usuário apenas cumprimenta

EXEMPLOS:
- "Queria ver os horários disponíveis" → agendar_consulta
- "Tem horário para dia 25?" → agendar_consulta
- "Perfeito, pode ser as 14:30" → agendar_consulta
- "Pode cancelar minha consulta?" → cancelar_consulta
- "Bom dia" → saudacao
- "Como funciona?" → perguntar_informacoes

FORMATAÇÃO OBRIGATÓRIA:
1. SEMPRE retorne APENAS uma das classificações listadas
2. NUNCA retorne texto adicional, apenas a classificação
3. NUNCA use prefixos como "System:", "Resposta:", "Intenção:", etc.
4. NUNCA use aspas ou formatação adicional



REGRAS CRÍTICAS PARA AGENDAR_CONSULTA:



RESPOSTA: Retorne APENAS a intenção, sem aspas, sem texto adicional, sem prefixos."""

            # Construir mensagens
            messages = [SystemMessage(content=system_prompt)]
            
            # Adicionar contexto se disponível (mensagens + previous_data para checagem de campos completos)
            if context and isinstance(context, dict):
                # 1) Histórico via 'messages' (compat)
                if context.get('messages'):
                    for msg in context['messages'][-5:]:  # Últimas 5 mensagens
                        if isinstance(msg, str):
                            messages.append(HumanMessage(content=msg))
                        elif hasattr(msg, 'content'):
                            messages.append(HumanMessage(content=msg.content))
                
                # 2) Histórico via 'conversation_history' (padrão atual do SmartAgent)
                conversation_history = context.get('conversation_history', [])
                if conversation_history:
                    # Usar até 10 mensagens para contexto rico
                    for ch_msg in conversation_history[-10:]:
                        if hasattr(ch_msg, 'content'):
                            # Detectar tipo aproximado
                            try:
                                if getattr(ch_msg, 'type', None) == 'human':
                                    messages.append(HumanMessage(content=ch_msg.content))
                                else:
                                    # Tratar como mensagem humana para contexto textual
                                    messages.append(HumanMessage(content=ch_msg.content))
                            except Exception:
                                messages.append(HumanMessage(content=str(ch_msg)))

            # Código removido - substituído pela implementação melhorada acima
            
            # Adicionar mensagem atual
            messages.append(HumanMessage(content=message))
            
            # Obter LLM configurado
            llm = self._get_llm(empresa_config)
            
            # Chamar LLM
            response = llm.invoke(messages)
            
            # Limpar resposta - o LLM pode retornar string diretamente ou objeto
            response_text = response.content if hasattr(response, 'content') else str(response)
            intent = response_text.strip().lower()
            
            # Validar intenção
            valid_intents = [
                'verificar_disponibilidade',
                'agendar_consulta', 
                'cancelar_consulta',
                'reagendar_consulta',
                'perguntar_informacoes',
                'saudacao'
            ]
            
            if intent in valid_intents:
                return intent
            else:
                # Fallback para intenção mais comum
                return 'verificar_disponibilidade'
                
        except Exception as e:
            logger.error(f"Erro ao detectar intenção: {e}")
            return 'verificar_disponibilidade'  # Fallback
    
    def _fallback_match_professional(self, nome_procurado: str, profissionais_list: List[Dict[str, Any]], match_rules: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback para match local de profissional"""
        try:
            # Usar estratégia de fallback das regras
            fallback_strategy = match_rules.get('professional_matching', {}).get('fallback_strategy', 'fuzzy_match')
            
            if fallback_strategy == 'fuzzy_match':
                # Implementar fuzzy matching local
                from difflib import SequenceMatcher
                
                best_match = None
                best_score = 0.0
                
                for prof in profissionais_list:
                    score = SequenceMatcher(None, nome_procurado.lower(), prof.get('nome', '').lower()).ratio()
                    if score > best_score:
                        best_score = score
                        best_match = prof
                
                if best_match and best_score >= 0.6:
                    return {
                        "id": best_match.get('id'),
                        "nome": best_match.get('nome'),
                        "confianca": "BAIXA",
                        "razao": f"Match local com score {best_score:.2f}",
                        "fallback": True
                    }
            
            return {"error": "Nenhum match encontrado"}
            
        except Exception as e:
            return {"error": f"Erro no fallback: {str(e)}"}
    
    def _fallback_match_service(self, nome_procurado: str, servicos_list: List[Dict[str, Any]], match_rules: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback para match local de serviço"""
        try:
            # Usar estratégia de fallback das regras
            fallback_strategy = match_rules.get('service_matching', {}).get('fallback_strategy', 'category_based')
            
            if fallback_strategy == 'category_based':
                # Buscar por palavras-chave nas categorias
                nome_lower = nome_procurado.lower()
                
                for servico in servicos_list:
                    categoria = servico.get('categoria', '').lower()
                    nome_servico = servico.get('nome', '').lower()
                    
                    if nome_lower in categoria or nome_lower in nome_servico:
                        return {
                            "id": servico.get('id'),
                            "nome": servico.get('nome'),
                            "confianca": "BAIXA",
                            "razao": "Match por categoria/nome",
                            "fallback": True
                        }
            
            return {"error": "Nenhum match encontrado"}
            
        except Exception as e:
            return {"error": f"Erro no fallback: {str(e)}"}
    
    def _fallback_extract_data(self, message: str, extraction_rules: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback para extração local de dados"""
        try:
            # Implementar extração local usando regex patterns das regras
            field_patterns = extraction_rules.get('field_patterns', {})
            
            extracted_data = {
                "profissional": None,
                "procedimento": None,
                "data": None,
                "horario": None
            }
            
            # Extrair profissional
            if 'profissional' in field_patterns:
                patterns = field_patterns['profissional']['patterns']
                for pattern in patterns:
                    import re
                    match = re.search(pattern, message, re.IGNORECASE)
                    if match:
                        extracted_data['profissional'] = match.group(1).strip()
                        break
            
            # Extrair procedimento
            if 'procedimento' in field_patterns:
                patterns = field_patterns['procedimento']['patterns']
                for pattern in patterns:
                    import re
                    match = re.search(pattern, message, re.IGNORECASE)
                    if match:
                        extracted_data['procedimento'] = match.group(1).strip()
                        break
            
            # TODO: Implementar extração de data e horário
            
            return extracted_data
            
        except Exception as e:
            return {"error": f"Erro no fallback: {str(e)}"}
    
    def _validate_extracted_data(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida e corrige dados extraídos pelo LLM
        """
        try:
            from datetime import datetime, timedelta
            
            # Data atual
            hoje = datetime.now()
            
            # Validar data
            if extracted_data.get('data'):
                try:
                    # Tentar parse da data
                    data_extraida = datetime.strptime(extracted_data['data'], '%Y-%m-%d')
                    
                    # Se a data for passada, invalidar
                    if data_extraida < hoje:
                        logger.warning(f"⚠️ Data passada detectada: {extracted_data['data']}, convertendo para null")
                        extracted_data['data'] = None
                    
                    # Se a data for muito futura (mais de 30 dias), invalidar
                    elif data_extraida > hoje + timedelta(days=30):
                        logger.warning(f"⚠️ Data muito futura detectada: {extracted_data['data']}, convertendo para null")
                        extracted_data['data'] = None
                        
                except ValueError:
                    logger.warning(f"⚠️ Formato de data inválido: {extracted_data['data']}, convertendo para null")
                    extracted_data['data'] = None
            
            # Validar procedimento - se foi mencionado mas retornou null, tentar extrair
            if extracted_data.get('procedimento') is None:
                # Verificar se há palavras que indicam procedimento na mensagem original
                # Esta validação será feita no prompt principal, mas aqui como backup
                pass
            
            logger.info(f"✅ Dados validados: {extracted_data}")
            return extracted_data
            
        except Exception as e:
            logger.error(f"Erro na validação de dados: {e}")
            return extracted_data
    
    def _validate_match_result(self, match_result: Dict[str, Any], original_list: List[Dict[str, Any]], tipo: str) -> Dict[str, Any]:
        """
        Valida se o resultado do match contém dados reais da lista
        """
        try:
            logger.info(f"🔍 INICIANDO VALIDAÇÃO de match para {tipo}")
            logger.info(f"📊 Resultado do LLM: {match_result}")
            logger.info(f"📋 Lista original: {len(original_list)} itens")
            logger.info(f"🔍 Tipo do resultado: {type(match_result)}")
            
            # Verificar se o ID retornado existe na lista original
            if match_result.get('id') and match_result.get('id') != 'null':
                logger.info(f"🔍 ID encontrado no resultado: {match_result.get('id')} (tipo: {type(match_result.get('id'))})")
                
                # DETECTAR TEXTO LITERAL (problema principal)
                id_value = str(match_result.get('id')).lower()
                logger.info(f"🔍 ID convertido para lowercase: '{id_value}'")
                
                texto_literal_detectado = any(texto_literal in id_value for texto_literal in ['id do', 'id da', 'id_', 'nome do', 'nome da'])
                if texto_literal_detectado:
                    logger.warning(f"⚠️ Texto literal detectado em {tipo}: '{match_result.get('id')}', convertendo para null")
                    logger.warning(f"⚠️ ID problemático: '{id_value}'")
                    match_result['id'] = None
                    match_result['nome'] = None
                    match_result['confianca'] = 'BAIXA'
                    match_result['razao'] = f'Texto literal "{match_result.get("id")}" detectado - LLM não extraiu dados reais'
                    match_result['texto_literal'] = True
                    logger.info(f"✅ Resultado após correção de texto literal: {match_result}")
                    return match_result
                
                # Buscar o item na lista original
                logger.info(f"🔍 Buscando ID '{match_result.get('id')}' na lista original...")
                item_encontrado = None
                for i, item in enumerate(original_list):
                    item_id = str(item.get('id'))
                    resultado_id = str(match_result.get('id'))
                    logger.info(f"   Comparando: '{item_id}' vs '{resultado_id}' (item {i+1})")
                    if item_id == resultado_id:
                        item_encontrado = item
                        logger.info(f"✅ ID encontrado na posição {i+1}: {item}")
                        break
                
                if not item_encontrado:
                    logger.warning(f"⚠️ ID inventado detectado em {tipo}: '{match_result.get('id')}', convertendo para null")
                    logger.warning(f"⚠️ Lista de IDs disponíveis: {[str(item.get('id', 'N/A')) for item in original_list]}")
                    match_result['id'] = None
                    match_result['nome'] = None
                    match_result['confianca'] = 'BAIXA'
                    match_result['razao'] = f'ID {match_result.get("id")} não encontrado na lista real de {tipo}'
                    match_result['inventado'] = True
                    logger.info(f"✅ Resultado após correção de ID inventado: {match_result}")
                else:
                    logger.info(f"✅ Item encontrado na lista: {item_encontrado}")
                    # Verificar se o nome também corresponde
                    nome_resultado = match_result.get('nome')
                    nome_lista = item_encontrado.get('nome')
                    if nome_resultado != nome_lista:
                        logger.warning(f"⚠️ Nome não corresponde ao ID em {tipo}: '{nome_resultado}' vs '{nome_lista}'")
                        logger.info(f"🔄 Corrigindo nome para o valor real da lista")
                        match_result['nome'] = nome_lista  # Usar nome real
                    else:
                        logger.info(f"✅ Nome corresponde ao ID: '{nome_resultado}'")
            else:
                logger.info(f"ℹ️ Nenhum ID válido encontrado no resultado: {match_result.get('id')}")
            
            logger.info(f"✅ Match de {tipo} validado: {match_result}")
            return match_result
            
        except Exception as e:
            logger.error(f"❌ Erro na validação de match de {tipo}: {e}")
            logger.error(f"❌ Tipo do erro: {type(e)}")
            import traceback
            logger.error(f"❌ Stack trace: {traceback.format_exc()}")
            return match_result
    
    def parse_phone_from_waid(self, waid: str) -> Dict[str, Any]:
        """
        Quebra o waid (WhatsApp ID) para montar o objeto telefones da API Trinks
        Args:
            waid: WhatsApp ID (ex: "5541999999999")
        Returns:
            Dicionário com estrutura { ddi, ddd, numero, tipoId } para o campo telefones
        """
        try:
            # Normalizar waid (remover caracteres especiais)
            waid_clean = ''.join(filter(str.isdigit, waid))
            
            if not waid_clean or len(waid_clean) < 10:
                raise ValueError(f"Waid inválido: {waid}")
            
            # Estrutura esperada: DDI + DDD + Número
            # Ex: 5541999999999 -> DDI: 55, DDD: 41, Número: 99999999
            
            if waid_clean.startswith('55'):  # Brasil
                ddi = "55"
                ddd = waid_clean[2:4]  # Próximos 2 dígitos
                numero = waid_clean[4:]  # Restante
            else:
                # Fallback para outros países
                ddi = waid_clean[:2] if len(waid_clean) >= 12 else "55"
                ddd = waid_clean[2:4] if len(waid_clean) >= 12 else "00"
                numero = waid_clean[4:] if len(waid_clean) >= 12 else waid_clean
            
            # Validar estrutura
            if len(ddd) != 2 or len(numero) < 8:
                raise ValueError(f"Estrutura de telefone inválida: DDI={ddi}, DDD={ddd}, Número={numero}")
            
            return {
                "ddi": ddi,
                "ddd": ddd,
                "numero": numero,
                "tipoid": 1  # 1 = Celular (padrão para WhatsApp)
            }
            
        except Exception as e:
            logger.error(f"Erro ao parsear telefone do waid {waid}: {e}")
            # Fallback seguro
            return {
                "ddi": "55",
                "ddd": "00",
                "numero": "00000000",
                "tipoid": 1
            }

    def buscar_cliente_por_cpf(self, cpf: str, empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Busca cliente por CPF na API Trinks
        Args:
            cpf: CPF do cliente
            empresa_config: Configuração da empresa
        Returns:
            Dicionário com resultado da busca
        """
        try:
            logger.info(f"🔍 Buscando cliente por CPF: {cpf}")
            
            # Importar serviço Trinks
            from integrations.trinks_service import TrinksService
            trinks_service = TrinksService(empresa_config)
            
            # ✅ CORRIGIDO: Usar filtro por CPF diretamente na API
            response = trinks_service.get_clients(cpf=cpf)
            
            if response.get('error'):
                logger.error(f"❌ Erro ao buscar clientes: {response.get('error')}")
                return {"found": False, "error": f"Erro na API: {response.get('error')}"}
            
            # ✅ API já retorna apenas clientes com o CPF específico
            clientes = response.get('data', [])
            
            if clientes and len(clientes) > 0:
                cliente_encontrado = clientes[0]  # Primeiro resultado
            
            if cliente_encontrado:
                logger.info(f"✅ Cliente encontrado: {cliente_encontrado.get('nome')} (ID: {cliente_encontrado.get('id')})")
                return {
                    "found": True,
                    "cliente_id": cliente_encontrado.get('id'),
                    "nome": cliente_encontrado.get('nome'),
                    "cpf": cliente_encontrado.get('cpf'),
                    "email": cliente_encontrado.get('email'),
                    "telefones": cliente_encontrado.get('telefones', [])
                }
            else:
                logger.info(f"❌ Cliente com CPF {cpf} não encontrado")
                return {"found": False}
                # ✅ Sem mensagem fixa - Smart Agent gera!
                
        except Exception as e:
            logger.error(f"❌ Erro ao buscar cliente por CPF: {e}")
            return {"found": False, "error": str(e)}

    def listar_agendamentos_cliente(self, cliente_id: str, data_mencoada: str = None, horario_mencoado: str = None, empresa_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Lista agendamentos de um cliente específico com match por data e/ou horário
        Args:
            cliente_id: ID do cliente
            data_mencoada: Data mencionada pelo usuário (opcional)
            horario_mencoado: Horário mencionado pelo usuário (opcional)
            empresa_config: Configuração da empresa
        Returns:
            Dicionário com resultado da busca e agendamentoId para cancelamento
        """
        try:
            logger.info(f"📅 Listando agendamentos do cliente {cliente_id}")
            
            # Importar serviço Trinks
            from integrations.trinks_service import TrinksService
            trinks_service = TrinksService(empresa_config)
            
            # Buscar agendamentos do cliente
            response = trinks_service.get_appointments(client_id=cliente_id)
            
            if response.get('error'):
                logger.error(f"❌ Erro ao buscar agendamentos: {response.get('error')}")
                return {"found": False, "error": f"Erro na API: {response.get('error')}"}
            
            agendamentos = response.get('data', [])
            
            if not agendamentos:
                logger.info(f"❌ Nenhum agendamento encontrado para cliente {cliente_id}")
                return {"found": False, "message": "Nenhum agendamento encontrado"}
            
            # ✅ FILTRO: Remover agendamentos cancelados
            agendamentos_ativos = [
                ag for ag in agendamentos 
                if ag.get('status', {}).get('nome') != 'Cancelado'
            ]
            
            logger.info(f"✅ Encontrados {len(agendamentos)} agendamentos para cliente {cliente_id}")
            logger.info(f"✅ Agendamentos ativos (não cancelados): {len(agendamentos_ativos)}")
            
            if not agendamentos_ativos:
                logger.info(f"❌ Nenhum agendamento ativo encontrado para cliente {cliente_id}")
                return {"found": False, "message": "Nenhum agendamento ativo encontrado"}
            
            # Usar apenas agendamentos ativos
            agendamentos = agendamentos_ativos
            
            # Se só tem 1 agendamento, retorna direto
            if len(agendamentos) == 1:
                agendamento = agendamentos[0]
                logger.info(f"✅ Único agendamento: {agendamento.get('dataHoraInicio')} - ID: {agendamento.get('id')}")
                return {
                    "found": True,
                    "agendamento_id": agendamento.get('id'),
                    "data_hora": agendamento.get('dataHoraInicio'),
                    "servico": agendamento.get('servico'),
                    "profissional": agendamento.get('profissional'),
                    "total_agendamentos": 1,
                    "cache_instructions": {  # ✅ NOVO: Instruções para o Smart Agent
                        "update_fields": {
                            "agendamento_id": agendamento.get('id'),
                            "data_hora": agendamento.get('dataHoraInicio'),
                            "servico": agendamento.get('servico'),
                            "profissional": agendamento.get('profissional'),
                            "cliente_id": cliente_id  # ✅ PRESERVAR cliente_id
                        }
                    }
                }
            
            # Se tem múltiplos agendamentos, fazer match por data e/ou horário
            logger.info(f"🔄 Múltiplos agendamentos - fazendo match por data: {data_mencoada}, horário: {horario_mencoado}")
            
            # Fazer match inteligente
            agendamento_match = self._fazer_match_agendamento(agendamentos, data_mencoada, horario_mencoado)
            
            if agendamento_match:
                logger.info(f"✅ Match encontrado: {agendamento_match.get('dataHoraInicio')} - ID: {agendamento_match.get('id')}")
                return {
                    "found": True,
                    "agendamento_id": agendamento_match.get('id'),
                    "data_hora": agendamento_match.get('dataHoraInicio'),
                    "servico": agendamento_match.get('servico'),
                    "profissional": agendamento_match.get('profissional'),
                    "total_agendamentos": len(agendamentos),
                    "match_used": True,
                    "cache_instructions": {  # ✅ NOVO: Instruções para o Smart Agent
                        "update_fields": {
                            "agendamento_id": agendamento_match.get('id'),
                            "data_hora": agendamento_match.get('dataHoraInicio'),
                            "servico": agendamento_match.get('servico'),
                            "profissional": agendamento_match.get('profissional'),
                            "cliente_id": cliente_id  # ✅ PRESERVAR cliente_id
                        }
                    }
                }
            else:
                logger.warning(f"⚠️ Múltiplos agendamentos mas nenhum match encontrado")
                return {
                    "found": False,
                    "total_agendamentos": len(agendamentos),
                    "agendamentos_disponiveis": [
                        {
                            "id": ag.get('id'),
                            "data_hora": ag.get('dataHoraInicio'),
                            "servico": ag.get('servico'),
                            "profissional": ag.get('profissional')
                        } for ag in agendamentos[:5]  # Máximo 5 para não sobrecarregar
                    ],
                    "message": "Múltiplos agendamentos encontrados. Preciso saber qual você quer cancelar.",
                    "cache_instructions": {  # ✅ NOVO: Instruções para o Smart Agent
                        "update_fields": {
                            "cliente_id": cliente_id  # ✅ PRESERVAR cliente_id mesmo sem match
                        }
                    }
                }
                
        except Exception as e:
            logger.error(f"❌ Erro ao listar agendamentos: {e}")
            return {"found": False, "error": str(e)}

    def _fazer_match_agendamento(self, agendamentos: List[Dict], data_mencoada: str = None, horario_mencoado: str = None) -> Dict:
        """
        Faz match inteligente entre agendamentos e dados mencionados pelo usuário
        """
        try:
            # Se não tem dados para match, retorna o primeiro
            if not data_mencoada and not horario_mencoado:
                return agendamentos[0]
            
            # Converter data mencionada para formato comparável
            data_match = None
            if data_mencoada:
                try:
                    # Tentar diferentes formatos de data
                    from datetime import datetime
                    for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%d/%m', '%d-%m']:
                        try:
                            data_match = datetime.strptime(data_mencoada, fmt)
                            break
                        except ValueError:
                            continue
                except Exception:
                    logger.warning(f"⚠️ Não conseguiu converter data: {data_mencoada}")
            
            # Converter horário mencionado para formato comparável
            horario_match = None
            if horario_mencoado:
                try:
                    from datetime import datetime
                    for fmt in ['%H:%M', '%Hh%M', '%H:%M:%S']:
                        try:
                            horario_match = datetime.strptime(horario_mencoado, fmt)
                            break
                        except ValueError:
                            continue
                except Exception:
                    logger.warning(f"⚠️ Não conseguiu converter horário: {horario_mencoado}")
            
            # Fazer match por data e/ou horário
            for agendamento in agendamentos:
                data_hora_agendamento = agendamento.get('dataHoraInicio')
                if not data_hora_agendamento:
                    continue
                
                try:
                    # Converter data/hora do agendamento
                    agendamento_dt = datetime.fromisoformat(data_hora_agendamento.replace('Z', '+00:00'))
                    
                    # Match por data
                    if data_match and agendamento_dt.date() == data_match.date():
                        logger.info(f"✅ Match por data: {data_mencoada}")
                        return agendamento
                    
                    # Match por horário (aproximado - tolerância de 30 min)
                    if horario_match:
                        hora_diff = abs((agendamento_dt.hour * 60 + agendamento_dt.minute) - 
                                      (horario_match.hour * 60 + horario_match.minute))
                        if hora_diff <= 30:  # Tolerância de 30 minutos
                            logger.info(f"✅ Match por horário: {horario_mencoado} (diferença: {hora_diff}min)")
                            return agendamento
                    
                    # Match por data E horário (mais preciso)
                    if data_match and horario_match:
                        if (agendamento_dt.date() == data_match.date() and 
                            abs((agendamento_dt.hour * 60 + agendamento_dt.minute) - 
                                (horario_match.hour * 60 + horario_match.minute)) <= 30):
                            logger.info(f"✅ Match por data E horário: {data_mencoada} {horario_mencoado}")
                            return agendamento
                            
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao processar agendamento {agendamento.get('id')}: {e}")
                    continue
            
            # Se não encontrou match, retorna None
            logger.info("❌ Nenhum match encontrado")
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro no match de agendamento: {e}")
            return None

    def cancelar_agendamento(self, agendamento_id: str, motivo: str, empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cancela um agendamento na API Trinks
        Args:
            agendamento_id: ID do agendamento a ser cancelado
            motivo: Motivo do cancelamento
            empresa_config: Configuração da empresa
        Returns:
            Dicionário com resultado do cancelamento
        """
        try:
            logger.info(f"❌ Cancelando agendamento {agendamento_id} com motivo: {motivo}")
            
            # Importar serviço Trinks
            from integrations.trinks_service import TrinksService
            trinks_service = TrinksService(empresa_config)
            
            # ✅ Usar ID padrão para "quemCancelou" (pode ser configurável)
            quem_cancelou = empresa_config.get('trinks_user_id', 1)  # ID padrão se não configurado
            
            # Chamar API de cancelamento
            response = trinks_service.cancel_appointment(agendamento_id, quem_cancelou, motivo)
            
            if response.get('error'):
                logger.error(f"❌ Erro ao cancelar agendamento: {response.get('error')}")
                return {
                    "success": False, 
                    "error": f"Erro na API: {response.get('error')}",
                    "cache_instructions": {
                        "update_fields": {
                            "agendamento_id": agendamento_id  # ✅ PRESERVAR para tentativas futuras
                        }
                    }
                }
            
            # ✅ Sucesso - limpar campos relacionados ao agendamento
            logger.info(f"✅ Agendamento {agendamento_id} cancelado com sucesso")
            return {
                "success": True,
                "message": "Agendamento cancelado com sucesso",
                "agendamento_id": agendamento_id,
                "motivo": motivo,
                "cache_instructions": {
                    "clear_fields": [  # ✅ LIMPAR campos relacionados ao agendamento cancelado
                        "agendamento_id",
                        "data_hora", 
                        "servico",
                        "profissional"
                    ],
                    "update_fields": {
                        "status": "cancelado",
                        "motivo_cancelamento": motivo
                    }
                }
            }
                
        except Exception as e:
            logger.error(f"❌ Erro ao cancelar agendamento: {e}")
            return {
                "success": False, 
                "error": str(e),
                "cache_instructions": {
                    "update_fields": {
                        "agendamento_id": agendamento_id  # ✅ PRESERVAR para tentativas futuras
                    }
                }
            }

    def criar_cliente(self, dados_cliente: Dict[str, Any], empresa_config: Dict[str, Any], waid: str) -> Dict[str, Any]:
        """
        Cria novo cliente na API Trinks usando telefone derivado do waid
        Args:
            dados_cliente: Dados do cliente {nome, cpf, email?}
            empresa_config: Configuração da empresa
            waid: WhatsApp ID para derivar telefone
        Returns:
            Dicionário com resultado da criação
        """
        try:
            logger.info(f"👤 Criando cliente: {dados_cliente.get('nome')} (CPF: {dados_cliente.get('cpf')})")
            
            # Validar campos obrigatórios
            if not dados_cliente.get('nome') or not dados_cliente.get('cpf'):
                return {"success": False, "error": "Nome e CPF são obrigatórios"}
            
            # Derivar telefone do waid
            telefone_info = self.parse_phone_from_waid(waid)
            logger.info(f"📱 Telefone derivado do waid: {telefone_info}")
            
            # Montar payload para API Trinks
            payload = {
                "nome": dados_cliente.get('nome'),
                "cpf": dados_cliente.get('cpf'),
                "email": dados_cliente.get('email'),
                "telefones": [telefone_info],
                "genero": None,  # Opcional
                "observacoes": None,  # Opcional
                "codigoExterno": None  # Opcional
            }
            
            # Remover campos None
            payload = {k: v for k, v in payload.items() if v is not None}
            
            logger.info(f"📤 Payload para criação: {payload}")
            
            # Importar serviço Trinks
            from integrations.trinks_service import TrinksService
            trinks_service = TrinksService(empresa_config)
            
            # Criar cliente
            response = trinks_service.create_client(payload)
            
            if response.get('error'):
                logger.error(f"❌ Erro ao criar cliente: {response.get('error')}")
                return {"success": False, "error": f"Erro na API: {response.get('error')}"}
            
            # Extrair dados do cliente criado
            cliente_criado = response.get('data', response)
            cliente_id = cliente_criado.get('id')
            
            if not cliente_id:
                logger.error(f"❌ Cliente criado mas sem ID: {response}")
                return {"success": False, "error": "Cliente criado mas sem ID retornado"}
            
            logger.info(f"✅ Cliente criado com sucesso: ID {cliente_id}")
            return {
                "success": True,
                "cliente_id": cliente_id,
                "nome": dados_cliente.get('nome'),
                "cpf": dados_cliente.get('cpf'),
                "email": dados_cliente.get('email'),
                "telefone": telefone_info,
                "message": "Cliente criado com sucesso"
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar cliente: {e}")
            return {"success": False, "error": str(e)}

    def confirmar_agendamento(self, dados_agendamento: Dict[str, Any], empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Confirma dados do agendamento antes de criar a reserva
        Args:
            dados_agendamento: Dados para agendamento
            empresa_config: Configuração da empresa
        Returns:
            Dicionário com confirmação e resumo
        """
        try:
            logger.info(f"✅ Confirmando agendamento: {dados_agendamento}")
            
            # Campos obrigatórios para agendamento
            campos_obrigatorios = ['profissional_id', 'servico_id', 'data', 'horario', 'cliente_id']
            campos_faltantes = [campo for campo in campos_obrigatorios if not dados_agendamento.get(campo)]
            
            if campos_faltantes:
                return {
                    "success": False,
                    "error": f"Campos obrigatórios faltando: {', '.join(campos_faltantes)}",
                    "campos_faltantes": campos_faltantes
                }
            
            # Validar formato da data
            data = dados_agendamento.get('data')
            if data and not self._validar_formato_data(data):
                return {
                    "success": False,
                    "error": f"Formato de data inválido: {data}. Use YYYY-MM-DD"
                }
            
            # Validar formato do horário
            horario = dados_agendamento.get('horario')
            if horario and not self._validar_formato_horario(horario):
                return {
                    "success": False,
                    "error": f"Formato de horário inválido: {horario}. Use HH:MM"
                }
            
            # Gerar resumo para confirmação
            resumo = {
                "profissional": dados_agendamento.get('profissional', 'Profissional'),
                "servico": dados_agendamento.get('servico', 'Serviço'),
                "data": data,
                "horario": horario,
                "cliente": dados_agendamento.get('cliente_nome', 'Cliente'),
                "observacoes": dados_agendamento.get('observacoes')
            }
            
            logger.info(f"✅ Agendamento confirmado: {resumo}")
            return {
                "success": True,
                "resumo": resumo,
                "message": "Agendamento confirmado e pronto para criação",
                "dados_validados": dados_agendamento
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao confirmar agendamento: {e}")
            return {"success": False, "error": str(e)}
    
    def _validar_formato_data(self, data: str) -> bool:
        """Valida formato de data YYYY-MM-DD"""
        try:
            from datetime import datetime
            datetime.strptime(data, '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    def _validar_formato_horario(self, horario: str) -> bool:
        """Valida formato de horário HH:MM"""
        try:
            from datetime import datetime
            datetime.strptime(horario, '%H:%M')
            return True
        except ValueError:
            return False

    def criar_reserva(self, dados_agendamento: Dict[str, Any], empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cria reserva na API Trinks
        Args:
            dados_agendamento: Dados validados para agendamento
            empresa_config: Configuração da empresa
        Returns:
            Dicionário com resultado da criação da reserva
        """
        try:
            logger.info(f"📅 Criando reserva: {dados_agendamento}")
            
            # ✅ CORRIGIDO: Montar payload para API Trinks conforme documentação
            # Formatar data+hora para o formato esperado pela API
            from datetime import datetime
            data_str = dados_agendamento.get('data')
            horario_str = dados_agendamento.get('horario')
            
            if data_str and horario_str:
                try:
                    # Combinar data + horário e formatar como ISO
                    data_hora = f"{data_str}T{horario_str}:00"
                    data_hora_inicio = datetime.fromisoformat(data_hora).isoformat()
                except Exception as e:
                    logger.error(f"❌ Erro ao formatar data+hora: {e}")
                    data_hora_inicio = f"{data_str}T{horario_str}:00"
            else:
                data_hora_inicio = None
            
            payload = {
                "servicoId": dados_agendamento.get('servico_id'),
                "clienteId": dados_agendamento.get('cliente_id'),
                "profissionalId": dados_agendamento.get('profissional_id'),
                "dataHoraInicio": data_hora_inicio,
                "duracaoEmMinutos": dados_agendamento.get('duracao_em_minutos'),
                "valor": dados_agendamento.get('valor'),
                "observacoes": dados_agendamento.get('observacoes')
            }
            
            # Remover campos None
            payload = {k: v for k, v in payload.items() if v is not None}
            
            logger.info(f"📤 Payload para criação da reserva: {payload}")
            
            # Importar serviço Trinks
            from integrations.trinks_service import TrinksService
            trinks_service = TrinksService(empresa_config)
            
            # Criar agendamento
            response = trinks_service.create_appointment(payload)
            
            if response.get('error'):
                logger.error(f"❌ Erro ao criar reserva: {response.get('error')}")
                return {"success": False, "error": f"Erro na API: {response.get('error')}"}
            
            # Extrair dados do agendamento criado
            agendamento_criado = response.get('data', response)
            appointment_id = agendamento_criado.get('id')
            
            if not appointment_id:
                logger.error(f"❌ Reserva criada mas sem ID: {response}")
                return {"success": False, "error": "Reserva criada mas sem ID retornado"}
            
            logger.info(f"✅ Reserva criada com sucesso: ID {appointment_id}")
            return {
                "success": True,
                "appointment_id": appointment_id,
                "profissional_id": dados_agendamento.get('profissional_id'),
                "servico_id": dados_agendamento.get('servico_id'),
                "data": dados_agendamento.get('data'),
                "horario": dados_agendamento.get('horario'),
                "cliente_id": dados_agendamento.get('cliente_id'),
                "message": "Reserva criada com sucesso",
                "dados_completos": agendamento_criado
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar reserva: {e}")
            return {"success": False, "error": str(e)}

    def _format_extracted_data_context(self, extracted_data: Dict[str, Any]) -> str:
        """Formata os dados extraídos para o contexto do LLM"""
        if not extracted_data:
            return "Nenhum dado extraído anteriormente."
        
        # Filtrar apenas campos relevantes e não vazios
        relevant_data = {}
        for key, value in extracted_data.items():
            if value is not None and value != "":
                relevant_data[key] = value
        
        if not relevant_data:
            return "Nenhum dado relevante extraído anteriormente."
        
        return f"DADOS JÁ EXTRAÍDOS ANTERIORMENTE: {json.dumps(relevant_data, indent=2)}"

    def _clean_llm_response(self, response_text: str) -> str:
        """Remove common prefixes and extracts only the JSON part from LLM responses"""
        try:
            # 1. Remover prefixos comuns
            prefixes_to_remove = ["System:", "Resposta:", "JSON:", "Human:", "AI:", "Assistant:"]
            for prefix in prefixes_to_remove:
                if response_text.startswith(prefix):
                    response_text = response_text[len(prefix):].strip()
            
            # 2. Procurar pelo primeiro { (início do JSON)
            json_start = response_text.find('{')
            if json_start != -1:
                response_text = response_text[json_start:]
            
            # 3. Procurar pelo último } (fim do JSON)
            json_end = response_text.rfind('}')
            if json_end != -1:
                response_text = response_text[:json_end + 1]
            
            # 4. Limpeza final
            response_text = response_text.strip()
            
            # 5. Validar se é JSON válido
            import json
            json.loads(response_text)  # Teste se é válido
            
            logger.info(f"🧹 Resposta limpa com sucesso: {response_text[:100]}...")
            return response_text
            
        except Exception as e:
            logger.warning(f"⚠️ Erro na limpeza da resposta: {e}")
            # Se falhar na limpeza, retornar original
            return response_text

    def check_professional_availability_with_looping(self, data: str, service_id: str, empresa_config: Dict[str, Any], 
                                                   professional_id: str = None, max_attempts: int = 7) -> Dict[str, Any]:
        """
        Verifica disponibilidade com looping de até 7 tentativas, pulando sábados e domingos.
        Função pública para uso externo.
        
        Args:
            data: Data inicial no formato YYYY-MM-DD
            service_id: ID do serviço
            empresa_config: Configuração da empresa
            professional_id: ID do profissional específico (opcional)
            max_attempts: Número máximo de tentativas (padrão: 7)
            
        Returns:
            Dict com horários disponíveis e informações sobre o looping
        """
        return self._check_availability_with_looping_internal(data, service_id, empresa_config, professional_id, max_attempts)

    def verificar_informacoes_profissional(self, profissional_id: str, procedimento_mencoado: str, empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verifica informações e preços de um procedimento específico de um profissional
        
        Args:
            profissional_id: ID do profissional
            procedimento_mencoado: Nome do procedimento mencionado pelo usuário
            empresa_config: Configuração da empresa
            
        Returns:
            Dict com informações do procedimento (preço, descrição, duração, etc.)
        """
        try:
            logger.info(f"💰 Verificando informações do profissional {profissional_id} para procedimento: {procedimento_mencoado}")
            
            # Importar serviço Trinks
            from integrations.trinks_service import TrinksService
            trinks_service = TrinksService(empresa_config)
            
            # Buscar serviços do profissional
            response = trinks_service.get_professional_services(profissional_id)
            
            if response.get('error'):
                logger.error(f"❌ Erro ao buscar serviços do profissional: {response.get('error')}")
                return {"success": False, "error": f"Erro na API: {response.get('error')}"}
            
            servicos = response.get('data', [])
            
            if not servicos:
                logger.warning(f"⚠️ Nenhum serviço encontrado para profissional {profissional_id}")
                return {"success": False, "message": "Profissional não possui serviços cadastrados"}
            
            logger.info(f"✅ Encontrados {len(servicos)} serviços para profissional {profissional_id}")
            
            # Fazer match inteligente com LLM
            match_result = self._fazer_match_procedimento_llm(procedimento_mencoado, servicos, empresa_config)
            
            if match_result:
                logger.info(f"✅ Match encontrado: {match_result.get('nome')} - R$ {match_result.get('preco')}")
                return {
                    "success": True,
                    "procedimento_id": match_result.get('id'),
                    "nome": match_result.get('nome'),
                    "descricao": match_result.get('descricao'),
                    "categoria": match_result.get('categoria'),
                    "duracao_em_minutos": match_result.get('duracaoEmMinutos'),
                    "preco": match_result.get('preco'),
                    "visivel_para_cliente": match_result.get('visivelParaCliente'),
                    "cache_instructions": {
                        "update_fields": {
                            "servico_id": match_result.get('id'),
                            "procedimento": match_result.get('nome'),
                            "duracao_em_minutos": match_result.get('duracaoEmMinutos'),
                            "valor": match_result.get('preco')
                        }
                    }
                }
            else:
                logger.warning(f"⚠️ Nenhum match encontrado para procedimento: {procedimento_mencoado}")
                return {
                    "success": False,
                    "procedimentos_disponiveis": [
                        {
                            "id": serv.get('id'),
                            "nome": serv.get('nome'),
                            "preco": serv.get('preco'),
                            "duracao": serv.get('duracaoEmMinutos')
                        } for serv in servicos[:5]  # Máximo 5 para não sobrecarregar
                    ],
                    "message": f"Não encontrei o procedimento '{procedimento_mencoado}'. Aqui estão os procedimentos disponíveis:",
                    "cache_instructions": {
                        "update_fields": {
                            "profissional_id": profissional_id
                        }
                    }
                }
                
        except Exception as e:
            logger.error(f"❌ Erro ao verificar informações do profissional: {e}")
            return {"success": False, "error": str(e)}

    def _fazer_match_procedimento_llm(self, procedimento_mencoado: str, servicos: List[Dict], empresa_config: Dict[str, Any]) -> Dict:
        """
        Faz match inteligente entre procedimento mencionado e serviços disponíveis usando LLM
        
        Args:
            procedimento_mencoado: Nome do procedimento mencionado pelo usuário
            servicos: Lista de serviços disponíveis
            empresa_config: Configuração da empresa (para obter OpenAI API key)
            
        Returns:
            Serviço que melhor corresponde ao procedimento mencionado
        """
        try:
            import json
            
            # Preparar contexto para o LLM
            servicos_info = []
            for serv in servicos:
                servicos_info.append({
                    "id": serv.get('id'),
                    "nome": serv.get('nome'),
                    "descricao": serv.get('descricao', ''),
                    "categoria": serv.get('categoria', ''),
                    "duracao": serv.get('duracaoEmMinutos'),
                    "preco": serv.get('preco')
                })
            
            # Prompt para o LLM
            prompt = f"""
            Você é um assistente especializado em fazer match entre procedimentos médicos mencionados e serviços cadastrados.
            
            PROCEDIMENTO MENCIONADO PELO USUÁRIO: "{procedimento_mencoado}"
            
            SERVIÇOS DISPONÍVEIS:
            {json.dumps(servicos_info, indent=2, ensure_ascii=False)}
            
            INSTRUÇÕES:
            1. Analise o procedimento mencionado pelo usuário
            2. Compare com os serviços disponíveis
            3. Identifique o serviço que melhor corresponde
            4. Considere sinônimos, variações e abreviações
            5. Retorne APENAS o JSON do serviço escolhido
            
            RESPOSTA (apenas JSON):
            """
            
            # ✅ Usar o mesmo padrão que trinks_rules.py
            from langchain_openai import ChatOpenAI
            
            # Obter API key da configuração da empresa
            api_key = (empresa_config or {}).get('openai_key') or (empresa_config or {}).get('openai_api_key')
            if not api_key:
                logger.error("❌ OpenAI API key não encontrada na configuração da empresa")
                return None
            
            # Criar instância do LLM
            llm = ChatOpenAI(api_key=api_key, temperature=0.1, model="gpt-4o")
            
            # Chamar LLM
            from langchain_core.messages import HumanMessage
            response = llm.invoke([HumanMessage(content=prompt)])
            response_text = getattr(response, 'content', str(response)) or ''
            
            # Limpar e parsear resposta
            cleaned_response = self._clean_llm_response(response_text)
            
            try:
                match_data = json.loads(cleaned_response)
                # Encontrar o serviço correspondente na lista original
                for serv in servicos:
                    if serv.get('id') == match_data.get('id'):
                        return serv
            except Exception as e:
                logger.warning(f"⚠️ Erro ao parsear resposta do LLM: {e}")
                return None
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro no match LLM: {e}")
            return None


# Instância global das ferramentas inteligentes
trinks_intelligent_tools = TrinksIntelligentTools() 