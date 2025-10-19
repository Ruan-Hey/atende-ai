from typing import Dict, List, Any
from datetime import datetime
import json
try:
    from langchain_openai import ChatOpenAI  # novo
except Exception:
    from langchain.chat_models import ChatOpenAI  # fallback legacy
try:
    from langchain_core.messages import SystemMessage, HumanMessage
except Exception:
    try:
        from langchain.schema import SystemMessage, HumanMessage  # legacy
    except Exception:
        # Fallback mínimo se nenhuma das duas estiver disponível
        class _BaseMessage:
            def __init__(self, content: str):
                self.content = content
        class SystemMessage(_BaseMessage):
            pass
        class HumanMessage(_BaseMessage):
            pass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class TrinksFlowType(Enum):
    """Tipos de fluxos disponíveis no Trinks"""
    CHECK_AVAILABILITY = "check_availability"
    BOOK_APPOINTMENT = "book_appointment"
    GET_PROFESSIONALS = "get_professionals"
    GET_SERVICES = "get_services"
    GET_APPOINTMENTS = "get_appointments"
    CREATE_CLIENT = "create_client"

class TrinksRules:
    """
    Regras estáticas para integração com Trinks API
    Contém APENAS configurações, regras e validações estáticas
    Seguindo a arquitetura definida em agent-architecture.mdc
    """
    
    def __init__(self):
        """Inicializa as regras do Trinks"""
        pass

    # ==========================
    # Suporte interno a LLM (Rules → LLM)
    # ==========================
    def _get_llm(self, empresa_config: Dict[str, Any]):
        api_key = (empresa_config or {}).get('openai_key') or (empresa_config or {}).get('openai_api_key')
        return ChatOpenAI(api_key=api_key, temperature=0.2, model="gpt-4o")

    def _clean_llm_json(self, text: str) -> str:
        try:
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1 and end > start:
                return text[start:end+1].strip()
            return text.strip()
        except Exception:
            return text
    
    # ========================================
    # 1. REGRAS BÁSICAS DA API
    # ========================================
    
    def get_api_rules(self) -> Dict[str, Any]:
        """
        Retorna regras gerais da API Trinks
        Returns:
            Dicionário com regras da API
        """
        return {
            "api_type": "TRINKS",
            "api_name": "Trinks",
            "email_required": False,
            "waid_required": False,
            "reservation_flow": "trinks",
            "confirmation_message": "Reserva confirmada no Trinks!",
            "missing_fields_message": "Faltam informações para completar a reserva no Trinks",
            "base_endpoints": {
                "professionals": "/estabelecimentos/{estabelecimento_id}/profissionais",
                "services": "/estabelecimentos/{estabelecimento_id}/servicos",
                "appointments": "/estabelecimentos/{estabelecimento_id}/agendamentos",
                "clients": "/estabelecimentos/{estabelecimento_id}/clientes",
                "availability": "/estabelecimentos/{estabelecimento_id}/disponibilidade",
                "available_slots": "/estabelecimentos/{estabelecimento_id}/horarios-disponiveis"
            },
            "required_config": [
                "trinks_base_url",
                "trinks_api_key", 
                "trinks_estabelecimento_id"
            ],
            "supported_operations": [
                "GET", "POST", "PUT", "DELETE"
            ]
        }
    
    def get_required_fields(self, flow_type: str) -> List[str]:
        """
        Retorna campos obrigatórios para cada tipo de fluxo
        Args:
            flow_type: Tipo do fluxo (TrinksFlowType)
        Returns:
            Lista de campos obrigatórios
        """
        required_fields = {
            TrinksFlowType.CHECK_AVAILABILITY.value: [
                "professional_id", "service_id", "date"
            ],
            TrinksFlowType.BOOK_APPOINTMENT.value: [
                "professional_id", "service_id", "date", "time", "client_name"
            ],
            TrinksFlowType.GET_PROFESSIONALS.value: [],
            TrinksFlowType.GET_SERVICES.value: [],
            TrinksFlowType.GET_APPOINTMENTS.value: [],
            TrinksFlowType.CREATE_CLIENT.value: [
                "name", "phone", "email"
            ]
        }
        
        return required_fields.get(flow_type, [])
    
    def get_validation_rules(self, flow_type: str) -> Dict[str, Any]:
        """
        Retorna regras de validação para cada fluxo
        Args:
            flow_type: Tipo do fluxo
        Returns:
            Dicionário com regras de validação
        """
        validation_rules = {
            TrinksFlowType.CHECK_AVAILABILITY.value: {
                "date_format": "YYYY-MM-DD",
                "date_validation": "future_date_only",
                "professional_id_validation": "must_exist",
                "service_id_validation": "must_exist"
            },
            TrinksFlowType.BOOK_APPOINTMENT.value: {
                "date_format": "YYYY-MM-DD",
                "time_format": "HH:MM",
                "date_validation": "future_date_only",
                "time_validation": "business_hours",
                "professional_id_validation": "must_exist",
                "service_id_validation": "must_exist",
                "client_name_validation": "non_empty_string"
            },
            TrinksFlowType.CREATE_CLIENT.value: {
                "name_validation": "non_empty_string",
                "phone_validation": "brazilian_phone_format",
                "email_validation": "valid_email_format"
            }
        }
        
        return validation_rules.get(flow_type, {})
    
    def get_available_flows(self) -> List[Dict[str, Any]]:
        """
        Retorna todos os fluxos disponíveis no Trinks
        Returns:
            Lista de fluxos com suas configurações
        """
        return [
            {
                "flow_type": TrinksFlowType.CHECK_AVAILABILITY.value,
                "description": "Verificar disponibilidade de profissional para serviço",
                "required_fields": self.get_required_fields(TrinksFlowType.CHECK_AVAILABILITY.value),
                "validation_rules": self.get_validation_rules(TrinksFlowType.CHECK_AVAILABILITY.value)
            },
            {
                "flow_type": TrinksFlowType.BOOK_APPOINTMENT.value,
                "description": "Agendar horário com profissional",
                "required_fields": self.get_required_fields(TrinksFlowType.BOOK_APPOINTMENT.value),
                "validation_rules": self.get_validation_rules(TrinksFlowType.BOOK_APPOINTMENT.value)
            },
            {
                "flow_type": TrinksFlowType.GET_PROFESSIONALS.value,
                "description": "Listar profissionais disponíveis",
                "required_fields": self.get_required_fields(TrinksFlowType.GET_PROFESSIONALS.value),
                "validation_rules": self.get_validation_rules(TrinksFlowType.GET_PROFESSIONALS.value)
            },
            {
                "flow_type": TrinksFlowType.GET_SERVICES.value,
                "description": "Listar serviços disponíveis",
                "required_fields": self.get_required_fields(TrinksFlowType.GET_SERVICES.value),
                "validation_rules": self.get_validation_rules(TrinksFlowType.GET_SERVICES.value)
            },
            {
                "flow_type": TrinksFlowType.GET_APPOINTMENTS.value,
                "description": "Listar agendamentos",
                "required_fields": self.get_required_fields(TrinksFlowType.GET_APPOINTMENTS.value),
                "validation_rules": self.get_validation_rules(TrinksFlowType.GET_APPOINTMENTS.value)
            },
            {
                "flow_type": TrinksFlowType.CREATE_CLIENT.value,
                "description": "Criar novo cliente",
                "required_fields": self.get_required_fields(TrinksFlowType.CREATE_CLIENT.value),
                "validation_rules": self.get_validation_rules(TrinksFlowType.CREATE_CLIENT.value)
            }
        ]
    
    # ========================================
    # 2. REGRAS DE CONVERSA ESPECÍFICAS
    # ========================================
    
    def get_intelligent_match_rules(self) -> Dict[str, Any]:
        """
        Retorna regras específicas do Trinks para match inteligente
        Returns:
            Dicionário com regras de match
        """
        return {
            "professional_matching": {
                "strategy": "llm_enhanced_keyword",
                "priority_fields": ["nome", "apelido", "especialidade"],
                "fallback_strategy": "fuzzy_match",
                "confidence_thresholds": {
                    "alta": 0.9,
                    "media": 0.7,
                    "baixa": 0.5
                },
                "validation_rules": {
                    "must_exist_in_trinks": True,
                    "check_availability": True,
                    "check_service_compatibility": True
                }
            },
            "service_matching": {
                "strategy": "llm_enhanced_category",
                "priority_fields": ["nome", "categoria", "descricao"],
                "fallback_strategy": "category_based",
                "confidence_thresholds": {
                    "alta": 0.85,
                    "media": 0.7,
                    "baixa": 0.5
                },
                "validation_rules": {
                    "must_exist_in_trinks": True,
                    "check_professional_compatibility": True,
                    "check_duration": True
                }
            }
        }
    
    def get_data_extraction_rules(self) -> Dict[str, Any]:
        """
        Retorna regras específicas do Trinks para extração de dados
        Returns:
            Dicionário com regras de extração
        """
        return {
            "extraction_strategy": "llm_enhanced_pattern",
            "field_patterns": {
                "profissional": {
                    "patterns": [
                        r"com\s+(?:a\s+)?([a-zA-ZÀ-ÿ\s]+)",
                        r"(?:doutor|dra?\.?)\s+([a-zA-ZÀ-ÿ\s]+)",
                        r"profissional\s+([a-zA-ZÀ-ÿ\s]+)",
                        r"([a-zA-ZÀ-ÿ\s]+)\s+(?:faz|atende|disponível)"
                    ],
                    "validation": "trinks_professional_exists",
                    "max_length": 100
                },
                "procedimento": {
                    "patterns": [
                        r"procedimento\s+([a-zA-ZÀ-ÿ\s]+)",
                        r"tratamento\s+([a-zA-ZÀ-ÿ\s]+)",
                        r"consulta\s+(?:de\s+)?([a-zA-ZÀ-ÿ\s]+)",
                        r"([a-zA-ZÀ-ÿ\s]+)\s+(?:para|com)"
                    ],
                    "validation": "trinks_service_exists",
                    "max_length": 150
                },
                "data": {
                    "patterns": [
                        r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
                        r"dia\s+(\d{1,2})",
                        r"(\d{1,2})\s+(?:de\s+)?(?:janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)",
                        r"(\d{4}-\d{2}-\d{2})"
                    ],
                    "validation": "trinks_date_format",
                    "date_formats": ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"],
                    "trinks_specific": {
                        "min_advance_hours": 2,
                        "max_days_ahead": 30
                    }
                }
            },
            "validation_rules": {
                "profissional": {
                    "must_exist_in_trinks": True,
                    "check_availability": True,
                    "check_service_compatibility": True
                },
                "procedimento": {
                    "must_exist_in_trinks": True,
                    "check_professional_compatibility": True,
                    "check_duration": True
                },
                "data": {
                    "business_hours_only": True,
                    "min_advance_hours": 2,
                    "max_days_ahead": 30
                }
            }
        }
    
    def get_conversation_flow_rules(self) -> Dict[str, Any]:
        """
        Retorna regras para fluxo de conversa específicas do Trinks
        Returns:
            Dicionário com regras de fluxo
        """
        return {
            "flow_steps_by_intent": {
                "verificar_disponibilidade": [
                    "extrair_dados",
                    "validar_campos",
                    "buscar_profissional",
                    "fazer_match_profissional",
                    "buscar_servico",
                    "fazer_match_servico",
                    "verificar_disponibilidade",
                    "validar_slots",
                    "gerar_resposta"
                ],
                "agendar_consulta": [
                    "extrair_dados",
                    "coletar_cliente",
                    "confirmar_agendamento",
                    "criar_reserva",
                    "gerar_resposta"
                ]
            },
            "step_dependencies": {
                "buscar_servico": ["buscar_profissional"],
                "verificar_disponibilidade": ["buscar_profissional", "buscar_servico"],
                "validar_slots": ["verificar_disponibilidade"],
                "coletar_cliente": ["extrair_dados"],
                "confirmar_agendamento": ["coletar_cliente"],
                "criar_reserva": ["confirmar_agendamento"]
            },
            "error_handling": {
                "profissional_nao_encontrado": "perguntar_profissional",
                "servico_nao_encontrado": "perguntar_servico",
                "sem_disponibilidade": "sugerir_alternativas",
                "erro_api": "tentar_novamente"
            },
            "validation_rules": {
                "min_required_fields": 1,
                "max_context_messages": 10,
                "timeout_minutes": 30,
                "max_retries": 3,
                "agendar_consulta": {
                    "campos_obrigatorios": ["profissional_id", "servico_id", "data", "horario", "cliente_id"],
                    "campos_minimos_cliente": ["nome", "cpf"],
                    "campos_opcionais_cliente": ["email", "observacoes"]
                }
            }
        }
    
    # ========================================
    # 3. REGRAS DE NEGÓCIO ESPECÍFICAS
    # ========================================
    
    def get_business_hours(self) -> Dict[str, Any]:
        """
        Retorna horário de funcionamento padrão do Trinks
        Returns:
            Dicionário com horários de funcionamento
        """
        return {
            "monday": {"start": "09:00", "end": "18:00", "active": True},
            "tuesday": {"start": "09:00", "end": "18:00", "active": True},
            "wednesday": {"start": "09:00", "end": "18:00", "active": True},
            "thursday": {"start": "09:00", "end": "18:00", "active": True},
            "friday": {"start": "09:00", "end": "18:00", "active": True},
            "saturday": {"start": "09:00", "end": "17:00", "active": True},
            "sunday": {"start": "00:00", "end": "00:00", "active": False}
        }
    
    def get_slot_duration(self) -> int:
        """
        Retorna duração padrão dos slots em minutos
        Returns:
            Duração em minutos
        """
        return 30  # 30 minutos padrão (não 60 como estava antes)
    
    def get_advance_booking_hours(self) -> int:
        """
        Retorna quantas horas de antecedência são necessárias para agendamento
        Returns:
            Horas de antecedência
        """
        return 2  # 2 horas de antecedência
    
    def get_max_booking_days_ahead(self) -> int:
        """
        Retorna quantos dias à frente é possível agendar
        Returns:
            Dias à frente
        """
        return 30  # 30 dias à frente
    
    def get_cancellation_policy(self) -> Dict[str, Any]:
        """
        Retorna política de cancelamento
        Returns:
            Dicionário com política de cancelamento
        """
        return {
            "min_hours_before": 24,  # 24 horas antes
            "cancellation_fee": 0,   # Sem taxa de cancelamento
            "refund_policy": "full_refund"
        }
    
    # ========================================
    # 4. REGRAS DE COMPATIBILIDADE (LEGACY)
    # ========================================
    
    def get_client_search_rules(self) -> Dict[str, Any]:
        """Retorna regras de busca de cliente para Trinks"""
        return {
            "api_endpoint": "/estabelecimentos/{estabelecimento_id}/clientes",
            "search_fields": ["cpf", "nome", "telefone", "email"],
            "create_if_not_found": True,
            "validation_rules": {
                "cpf": "brazilian_cpf_format",
                "nome": "non_empty_string",
                "telefone": "brazilian_phone_format"
            }
        }
    
    def get_service_detection_rules(self) -> Dict[str, Any]:
        """Retorna regras de detecção de serviço para Trinks"""
        return {
            "api_endpoint": "/estabelecimentos/{estabelecimento_id}/servicos",
            "search_fields": ["nome", "categoria", "descricao"],
            "match_strategies": ["keyword_match", "partial_match", "category_match"],
            "default_categories": ["Estética Facial", "Estética Corporal", "Tratamentos"]
        }
    
    def get_professional_search_rules(self) -> Dict[str, Any]:
        """Retorna regras de busca de profissionais para Trinks"""
        return {
            "api_endpoint": "/estabelecimentos/{estabelecimento_id}/profissionais",
            "search_fields": ["nome", "especialidade", "disponibilidade"],
            "match_strategies": ["name_match", "specialty_match", "availability_match"],
            "filter_by_service": True
        }
    
    def get_availability_check_rules(self) -> Dict[str, Any]:
        """Retorna regras de verificação de disponibilidade para Trinks"""
        return {
            "api_endpoint": "/estabelecimentos/{estabelecimento_id}/disponibilidade",
            "required_fields": ["data", "servico_id"],
            "optional_fields": ["profissional_id"],
            "slot_duration": 30,
            "business_hours": self.get_business_hours(),
            "advance_booking": self.get_advance_booking_hours()
        }
    
    def get_reservation_creation_rules(self) -> Dict[str, Any]:
        """Retorna regras de criação de reserva para Trinks"""
        return {
            "api_endpoint": "/estabelecimentos/{estabelecimento_id}/agendamentos",
            "required_fields": ["profissional_id", "servico_id", "data", "horario", "cliente_nome"],
            "optional_fields": ["observacoes", "cliente_telefone", "cliente_email"],
            "validation_rules": {
                "data": "future_date_only",
                "horario": "business_hours",
                "cliente_nome": "non_empty_string"
            }
        }
    
    def get_reservation_management_rules(self) -> Dict[str, Any]:
        """Retorna regras de gerenciamento de reserva para Trinks"""
        return {
            "api_endpoint": "/estabelecimentos/{estabelecimento_id}/agendamentos",
            "operations": ["GET", "PUT", "DELETE"],
            "cancellation_policy": self.get_cancellation_policy(),
            "reschedule_rules": {
                "min_hours_before": 2,
                "max_days_ahead": 30
            }
        }
    
    # MÉTODOS DE COMPATIBILIDADE MIGRADOS DO api_rules_engine.py
    
    def get_specific_api_rules(self, empresa_config: Dict[str, Any]):
        """Retorna a instância das regras específicas da API ativa - COMPATIBILIDADE"""
        return self
    
    def is_email_required(self, empresa_config: Dict[str, Any]) -> bool:
        """Verifica se email é obrigatório para a API ativa - COMPATIBILIDADE"""
        rules = self.get_api_rules()
        return rules.get('email_required', False)
    
    def is_waid_required(self, empresa_config: Dict[str, Any]) -> bool:
        """Verifica se WaId é obrigatório para a API ativa - COMPATIBILIDADE"""
        rules = self.get_api_rules()
        return rules.get('waid_required', False)
    
    def get_confirmation_message(self, empresa_config: Dict[str, Any]) -> str:
        """Retorna mensagem de confirmação específica da API - COMPATIBILIDADE"""
        rules = self.get_api_rules()
        return rules.get('confirmation_message', "Reserva confirmada!")
    
    def get_missing_fields_message(self, empresa_config: Dict[str, Any]) -> str:
        """Retorna mensagem de campos faltantes específica da API - COMPATIBILIDADE"""
        rules = self.get_api_rules()
        return rules.get('missing_fields_message', "Faltam informações para completar a reserva")
    
    def is_trinks_api(self, empresa_config: Dict[str, Any]) -> bool:
        """Verifica se a API ativa é Trinks - COMPATIBILIDADE"""
        return True  # Esta classe é específica do Trinks
    
    # MÉTODOS DELEGADOS PARA AS REGRAS ESPECÍFICAS - COMPATIBILIDADE
    
    def get_client_search_rules(self, empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """Retorna regras de busca de cliente para a API ativa - COMPATIBILIDADE"""
        return self.get_client_search_rules()
    
    def get_service_detection_rules(self, empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """Retorna regras de detecção de serviço para a API ativa - COMPATIBILIDADE"""
        return self.get_service_detection_rules()
    
    def get_professional_search_rules(self, empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """Retorna regras de busca de profissionais para a API ativa - COMPATIBILIDADE"""
        return self.get_professional_search_rules()
    
    def get_availability_check_rules(self, empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """Retorna regras de verificação de disponibilidade para a API ativa - COMPATIBILIDADE"""
        return self.get_availability_check_rules_expanded()
    
    def get_reservation_creation_rules(self, empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """Retorna regras de criação de reserva para a API ativa - COMPATIBILIDADE"""
        # TODO: Implementar regras específicas de criação de reserva
        return {"status": "nao_implementado"}
    
    # MÉTODOS ESPECÍFICOS DO TRINKS
    
    def get_availability_check_rules_expanded(self) -> Dict[str, Any]:
        """Retorna regras expandidas de verificação de disponibilidade para Trinks"""
        return {
            "flow_type": "check_availability",
            "description": "Verificação expandida de disponibilidade",
            "tipos_busca": {
                "por_profissional": {
                    "fluxo": ["extrair_dados", "buscar_profissional", "buscar_servico", "verificar_disponibilidade"],
                    "campos_obrigatorios": ["profissional", "data"],
                    "campos_opcionais": ["procedimento"]
                },
                "por_procedimento": {
                    "fluxo": ["extrair_dados", "buscar_servico", "verificar_disponibilidade"],
                    "campos_obrigatorios": ["profissional", "data"],
                    "campos_opcionais": ["procedimento"]
                }
            },
            "logica_preferencia": {
                "perguntar_se_nao_especificado": True,
                "mensagem_template": "Tem alguma preferência de profissional?",
                "opcoes_padrao": ["indiferente", "qualquer_um", "o_melhor_horario"]
            },
            "validacao_slots": {
                "duracao_slot_padrao": 30,
                "validar_consecutivos": True,
                "min_slots_consecutivos": 1
            },
            # ✅ ADICIONAR: Regras de estruturação de dados para o Agent
            "agent_data_structure": {
                "cache_fields": [
                    "profissional", "profissional_id", "procedimento", "servico_id", 
                    "data", "horario", "disponibilidade", "context"
                ],
                "required_ids": ["profissional_id", "servico_id"],
                "data_mapping": {
                    "profissional_id": "buscar_profissional.id",
                    "servico_id": "buscar_servico.id",
                    "disponibilidade": "verificar_disponibilidade"
                }
            }
        }
    
    def get_search_type_rules(self) -> Dict[str, Any]:
        """Retorna regras para determinar o tipo de busca para Trinks"""
        return {
            "por_profissional": {
                "fluxo": ["extrair_dados", "buscar_profissional", "buscar_servico", "verificar_disponibilidade"],
                "prioridade": "alta"
            },
            "por_procedimento": {
                "fluxo": ["extrair_dados", "buscar_servico", "verificar_disponibilidade"],
                "prioridade": "media"
            }
        }
    
    def determine_search_type(self, extracted_data: Dict[str, Any]) -> str:
        """Determina o tipo de busca baseado nos dados extraídos para Trinks"""
        try:
            has_professional = bool(extracted_data.get('profissional'))
            has_procedure = bool(extracted_data.get('procedimento'))
            
            if has_professional and has_procedure:
                # Se tem ambos, prioriza profissional (mais específico)
                return 'por_profissional'
            elif has_professional:
                return 'por_profissional'
            elif has_procedure:
                return 'por_procedimento'
            else:
                return 'invalido'
                
        except Exception as e:
            return 'invalido'
    
    def validate_availability_request(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Valida se a requisição de disponibilidade tem os campos necessários para Trinks"""
        try:
            # Verificar campos obrigatórios
            required_fields = ['data']
            missing_fields = [field for field in required_fields if not extracted_data.get(field)]
            
            if missing_fields:
                return {
                    'valid': False,
                    'error': f'Campos obrigatórios faltando: {", ".join(missing_fields)}',
                    'missing_fields': missing_fields
                }
            
            # Verificar se tem pelo menos um campo opcional
            optional_fields = ['profissional', 'procedimento']
            has_optional = any(extracted_data.get(field) for field in optional_fields)
            
            if not has_optional:
                return {
                    'valid': False,
                    'error': 'Deve fornecer pelo menos um: profissional OU procedimento',
                    'missing_fields': optional_fields
                }
            
            # Determinar tipo de busca
            search_type = self.determine_search_type(extracted_data)
            
            # Verificar se deve perguntar preferência de profissional
            preference_check = self.should_ask_professional_preference(extracted_data)
            
            return {
                'valid': True,
                'search_type': search_type,
                'preference_check': preference_check,
                'message': 'Requisição válida'
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': f'Erro na validação: {str(e)}'
            }
    
    def get_intelligent_flow_steps(self, extracted_data: Dict[str, Any], empresa_config: Dict[str, Any], previous_data: Dict[str, Any] = None) -> List[str]:
        """[LEGACY] Mantido apenas por compatibilidade. Use decide_next_steps no lugar."""
        logger.info("get_intelligent_flow_steps é legado; utilizar decide_next_steps")
        return ["ask_user"]

    def get_availability_flow_steps(self, extracted_data: Dict[str, Any], empresa_config: Dict[str, Any], previous_data: Dict[str, Any] = None) -> List[str]:
        """
        🧠 Usa fluxo inteligente via LLM + CACHE para verificar_disponibilidade
        """
        try:
            logger.info(f"🧠 Usando fluxo inteligente via LLM + CACHE...")
            return self.get_intelligent_flow_steps(extracted_data, empresa_config, previous_data)
            
        except Exception as e:
            logger.error(f"Erro no fluxo inteligente: {e}")
            # Fallback para fluxo seguro
            fluxo_fallback = ["extrair_dados", "buscar_servico", "verificar_disponibilidade"]
            logger.info(f"🔄 Usando fluxo de fallback: {fluxo_fallback}")
            return fluxo_fallback
    
    def get_preference_rules(self) -> Dict[str, Any]:
        """Retorna as regras de preferência de profissional para Trinks"""
        try:
            flows = self.get_available_flows()
            for flow in flows:
                if flow.get('flow_type') == 'check_availability':
                    return flow.get('logica_preferencia', {})
            
            return {}
            
        except Exception as e:
            return {}
    
    def should_ask_professional_preference(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Determina se deve perguntar preferência de profissional para Trinks"""
        try:
            preference_rules = self.get_preference_rules()
            if not preference_rules:
                return {'should_ask': False, 'reason': 'Regras de preferência não configuradas'}
            
            # Verificar se já tem profissional na mensagem
            has_professional = bool(extracted_data.get('profissional'))
            
            if has_professional:
                return {
                    'should_ask': False,
                    'reason': 'Profissional já mencionado na mensagem',
                    'action': 'usar_profissional_diretamente'
                }
            else:
                return {
                    'should_ask': True,
                    'reason': 'Nenhum profissional mencionado',
                    'action': 'perguntar_preferencia_educadamente',
                    'message_template': 'Tem alguma preferência de profissional?'
                }
                
        except Exception as e:
            return {'should_ask': False, 'reason': f'Erro: {str(e)}'}
    
    def get_slot_validation_rules(self) -> Dict[str, Any]:
        """Retorna as regras de validação de slots para Trinks"""
        try:
            flows = self.get_available_flows()
            for flow in flows:
                if flow.get('flow_type') == 'check_availability':
                    return flow.get('validacao_slots', {})
            return {}
            
        except Exception as e:
            return {}
    
    def calculate_required_slots(self, procedure_duration: int, slot_duration: int = 30) -> int:
        """Calcula quantos slots são necessários para um procedimento no Trinks"""
        try:
            import math
            # Arredondar para cima para garantir tempo suficiente
            required_slots = math.ceil(procedure_duration / slot_duration)
            return required_slots
            
        except Exception as e:
            return 1  # Fallback para 1 slot
    
    def validate_consecutive_slots(self, available_slots: List[Dict[str, Any]], 
                                 required_slots: int, 
                                 slot_duration: int = 30) -> List[Dict[str, Any]]:
        """Valida se há slots consecutivos suficientes para um procedimento no Trinks"""
        try:
            if not available_slots or required_slots <= 0:
                return []
            
            valid_start_times = []
            
            # Ordenar slots por horário
            sorted_slots = sorted(available_slots, key=lambda x: x.get('horario', ''))
            
            # Verificar cada slot como possível início
            for i in range(len(sorted_slots) - required_slots + 1):
                start_slot = sorted_slots[i]
                start_time = start_slot.get('horario')
                
                if not start_time:
                    continue
                
                # Verificar se os próximos slots consecutivos estão disponíveis
                consecutive_available = True
                for j in range(required_slots):
                    if i + j >= len(sorted_slots):
                        consecutive_available = False
                        break
                    
                    current_slot = sorted_slots[i + j]
                    if not current_slot.get('disponivel', True):
                        consecutive_available = False
                        break
                    
                    # Verificar se é o slot esperado (consecutivo)
                    expected_time = self._calculate_next_slot_time(start_time, j, slot_duration)
                    if current_slot.get('horario') != expected_time:
                        consecutive_available = False
                        break
                
                if consecutive_available:
                    valid_start_times.append({
                        'horario_inicio': start_time,
                        'slots_necessarios': required_slots,
                        'duracao_total': required_slots * slot_duration,
                        'slots_consecutivos': True
                    })
            
            return valid_start_times
            
        except Exception as e:
            return []
    
    def _calculate_next_slot_time(self, start_time: str, slot_offset: int, slot_duration: int) -> str:
        """Calcula o horário do próximo slot baseado no offset para Trinks"""
        try:
            from datetime import datetime, timedelta
            
            # Converter horário para datetime
            time_format = "%H:%M"
            start_dt = datetime.strptime(start_time, time_format)
            
            # Adicionar offset de slots
            total_minutes = slot_offset * slot_duration
            next_dt = start_dt + timedelta(minutes=total_minutes)
            
            # Retornar no formato original
            return next_dt.strftime(time_format)
            
        except Exception as e:
            return start_time
    
    def filter_available_slots_by_duration(self, available_slots: List[Dict[str, Any]], 
                                         procedure_duration: int) -> List[Dict[str, Any]]:
        """Filtra slots disponíveis baseado na duração do procedimento para Trinks"""
        try:
            # Obter regras de validação
            validation_rules = self.get_slot_validation_rules()
            slot_duration = validation_rules.get('duracao_slot_padrao', 30)
            
            # Calcular slots necessários
            required_slots = self.calculate_required_slots(procedure_duration, slot_duration)
            
            # Validar slots consecutivos
            valid_slots = self.validate_consecutive_slots(available_slots, required_slots, slot_duration)
            
            if not valid_slots:
                return []
            
            return valid_slots
            
        except Exception as e:
            return available_slots  # Fallback: retorna todos os slots
    
    def get_procedure_duration(self, procedure_name: str, servico_info: Dict[str, Any] = None) -> int:
        """Obtém a duração de um procedimento específico para Trinks"""
        try:
            # PRIORIDADE 1: Usar duração da API Trinks se disponível
            if servico_info and servico_info.get('duracaoEmMinutos'):
                duracao_api = servico_info.get('duracaoEmMinutos')
                return duracao_api
            
            # PRIORIDADE 2: Mapeamento de palavras-chave
            procedure_lower = procedure_name.lower()
            
            # Mapeamento de procedimentos para durações (em minutos)
            duration_mapping = {
                'massagem': 60,
                'massagem relaxante': 90,
                'massagem profunda': 120,
                'consulta': 30,
                'consulta médica': 45,
                'limpeza': 30,
                'tratamento': 60,
                'avaliação': 45,
                'retorno': 30,
                'acompanhamento': 45,
                'teste': 30,
                'aaa': 30
            }
            
            # Buscar por palavras-chave
            for keyword, duration in duration_mapping.items():
                if keyword in procedure_lower:
                    return duration
            
            # Duração padrão se não encontrar
            default_duration = 60
            return default_duration
            
        except Exception as e:
            return 60  # Duração padrão de 60 min
    
    # ========================================
    # 5. MÉTODOS DE EXECUÇÃO (Rules → Tools)
    # ========================================
    
    def execute_step(self, step_name: str, data: Dict[str, Any], empresa_config: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Executa um passo específico chamando a Tool apropriada
        Args:
            step_name: Nome do passo a executar
            data: Dados para execução
            empresa_config: Configuração da empresa
            context: Contexto da conversa (inclui waid)
        Returns:
            Resultado da execução
        """
        try:
            # ✅ CORREÇÃO: Usar dados enriquecidos do contexto em vez dos dados originais
            enriched_data = data.copy()
            
            # Tentar obter dados enriquecidos do contexto (cache)
            if context and isinstance(context, dict):
                # Buscar dados do cache via previous_data ou extracted_data
                previous_data = context.get('previous_data', {})
                extracted_data = context.get('extracted_data', {})
                
                # Mesclar dados para ter o contexto completo
                if previous_data:
                    enriched_data.update(previous_data)
                if extracted_data:
                    enriched_data.update(extracted_data)
                
                logger.info(f"📋 Dados enriquecidos para execução do passo {step_name}: {enriched_data}")
            
            # Importar Tools dinamicamente para evitar circular imports
            from tools.trinks_intelligent_tools import TrinksIntelligentTools
            
            tools_instance = TrinksIntelligentTools(empresa_config)
            
            if step_name == "buscar_profissional":
                return self._execute_buscar_profissional(tools_instance, enriched_data, empresa_config)
            elif step_name == "buscar_servico":
                return self._execute_buscar_servico(tools_instance, enriched_data, empresa_config)
            elif step_name == "verificar_disponibilidade":
                return self._execute_verificar_disponibilidade(tools_instance, enriched_data, empresa_config)
            elif step_name == "validar_slots":
                return self._execute_validar_slots(tools_instance, enriched_data, empresa_config)
            elif step_name == "coletar_cliente":
                return self._execute_coletar_cliente(tools_instance, enriched_data, empresa_config, context)
            elif step_name == "confirmar_agendamento":
                return self._execute_confirmar_agendamento(tools_instance, enriched_data, empresa_config)
            elif step_name == "criar_reserva":
                return self._execute_criar_reserva(tools_instance, enriched_data, empresa_config)
            elif step_name == "listar_agendamentos":
                return tools_instance.listar_agendamentos_cliente(
                    enriched_data.get('cliente_id'), 
                    enriched_data.get('data'), 
                    enriched_data.get('horario'), 
                    empresa_config
                )
            elif step_name == "cancelar_agendamento":
                return tools_instance.cancelar_agendamento(
                    enriched_data.get('agendamento_id'), 
                    enriched_data.get('motivo', 'Cliente solicitou cancelamento'), 
                    empresa_config
                )
            elif step_name == "verificar_informacoes_profissional":
                return tools_instance.verificar_informacoes_profissional(
                    enriched_data.get('profissional_id'),  # ID do profissional
                    enriched_data.get('procedimento'),     # Nome do procedimento
                    empresa_config
                )
            else:
                return {"status": "passo_nao_implementado", "step": step_name}
                
        except Exception as e:
            return {"status": "erro", "error": str(e), "step": step_name}
    
    def _execute_buscar_profissional(self, tools_instance, data: Dict[str, Any], empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """Executa busca de profissionais via Tools"""
        try:
            if data.get('profissional'):
                # Buscar profissional específico
                profissionais = tools_instance.list_professionals(empresa_config)
                if profissionais.get('success'):
                    # Fazer match inteligente
                    match_result = tools_instance.intelligent_match_professional(
                        data.get('profissional'),
                        profissionais.get('result', []),
                        empresa_config
                    )
                    
                    # CORREÇÃO: Retornar formato estruturado para o agente
                    if match_result.get('error'):
                        return {"status": "erro", "error": match_result.get('error')}
                    elif match_result.get('id') and match_result.get('nome'):
                        # Enriquecer com informações de contexto
                        resultado = {
                            "status": "encontrado",
                            "id": match_result.get('id'),
                            "nome": match_result.get('nome'),
                            "profissional_id": match_result.get('id'),  # ✅ ADICIONAR: ID para o agente
                            "confianca": match_result.get('confianca', 'BAIXA'),
                            "razao": match_result.get('razao', ''),
                            "result": match_result,  # Dados completos para compatibilidade
                            "tipo_busca": "por_profissional",
                            "cache_instructions": {  # ✅ NOVO: Instruções para o Smart Agent
                                "update_fields": {
                                    "profissional_id": match_result.get('id')
                                }
                            }
                        }
                        
                        # Se tiver procedimento na mensagem, incluir para contexto
                        if data.get('procedimento'):
                            resultado['procedimento_mencioado'] = data.get('procedimento')
                            logger.info(f"💡 Procedimento mencionado na mensagem: {data.get('procedimento')}")
                        
                        # ✅ CACHE TEMPORÁRIO: Se múltiplos profissionais, salvar cache para resolução automática
                        if 'profissionais' in resultado and len(resultado['profissionais']) > 1:
                            resultado['cache_instructions'] = {
                                "update_fields": {
                                    "temp_professional_cache": {
                                        f"{prof.get('nome', 'N/A')} (ID: {prof.get('id', 'N/A')})": prof.get('horariosVagos', [])
                                        for prof in resultado['profissionais'] if prof.get('horariosVagos')
                                    },
                                    "temp_cache_expiry": 2
                                }
                            }
                            logger.info(f"🔄 Cache temporário criado para {len(resultado['profissionais'])} profissionais")
                        
                        return resultado
                    else:
                        return {
                            "status": "nao_encontrado",
                            "profissional_procurado": data.get('profissional'),
                            "razao": match_result.get('razao', 'Profissional não encontrado'),
                            "result": match_result,  # Dados completos para compatibilidade
                            "tipo_busca": "por_profissional"
                        }
                else:
                    return {"status": "erro", "error": "Falha ao buscar profissionais"}
            else:
                # Buscar todos os profissionais
                profissionais = tools_instance.list_professionals(empresa_config)
                resultado = {"status": "todos", "profissionais": profissionais.get('result', [])}
                
                # ✅ CACHE TEMPORÁRIO: Se múltiplos profissionais, salvar cache para resolução automática
                if profissionais.get('result') and len(profissionais.get('result', [])) > 1:
                    resultado['cache_instructions'] = {
                        "update_fields": {
                            "temp_professional_cache": {
                                f"{prof.get('nome', 'N/A')} (ID: {prof.get('id', 'N/A')})": []
                                for prof in profissionais.get('result', [])
                            },
                            "temp_cache_expiry": 2
                        }
                    }
                    logger.info(f"🔄 Cache temporário criado para {len(profissionais.get('result', []))} profissionais")
                
                return resultado
                
        except Exception as e:
            return {"status": "erro", "error": str(e)}
    
    def _execute_buscar_servico(self, tools_instance, data: Dict[str, Any], empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """Executa busca de serviços via Tools"""
        try:
            if data.get('procedimento'):
                servicos = tools_instance.list_services(empresa_config)
                logger.info(f"🔍 Busca de serviços retornou: {servicos}")
                
                if servicos.get('success'):
                    # Fazer match inteligente
                    match_result = tools_instance.intelligent_match_service(
                        data.get('procedimento'),
                        servicos.get('result', []),
                        empresa_config
                    )
                    logger.info(f"🎯 Match de serviço resultou: {match_result}")
                    
                    # CORREÇÃO: Retornar formato estruturado para o agente
                    if match_result.get('error'):
                        return {"status": "erro", "error": match_result.get('error')}
                    elif match_result.get('nome'):
                        return {
                            "status": "encontrado",
                            "nome": match_result.get('nome'),
                            "servico_id": match_result.get('id'),  # ✅ ADICIONAR: ID para o agente
                            "confianca": match_result.get('confianca', 'BAIXA'),
                            "razao": match_result.get('razao', ''),
                            "result": match_result,  # Dados completos para compatibilidade
                            "cache_instructions": {  # ✅ NOVO: Instruções para o Smart Agent
                                "update_fields": {
                                    "servico_id": match_result.get('id'),
                                    "duracao_em_minutos": match_result.get('duracaoEmMinutos'),  # ✅ NOVO: Duração do serviço
                                    "valor": match_result.get('preco')  # ✅ NOVO: Preço do serviço
                                }
                            }
                        }
                    else:
                        return {
                            "status": "nao_encontrado",
                            "procedimento_procurado": data.get('procedimento'),
                            "razao": match_result.get('razao', 'Serviço não encontrado'),
                            "result": match_result  # Dados completos para compatibilidade
                        }
                else:
                    logger.error(f"❌ Falha ao buscar serviços: {servicos.get('error')}")
                    return {"status": "erro", "error": f"Falha ao buscar serviços: {servicos.get('error')}"}
            else:
                logger.warning("⚠️ Nenhum procedimento especificado para busca de serviços")
                return {"status": "nao_especificado"}
                
        except Exception as e:
            return {"status": "erro", "error": str(e)}
    
    def _execute_verificar_disponibilidade(self, tools_instance, data: Dict[str, Any], empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """Executa verificação de disponibilidade via Tools"""
        try:
            servico_id = data.get('servico_id')
            data_consulta = data.get('data')
            profissional_id = data.get('profissional_id')
            
            # CORREÇÃO: Permitir verificação sem serviço específico
            if not data_consulta:
                return {"status": "erro", "error": "Data não identificada"}
            
            # Se não tiver serviço específico, usar serviço padrão ou verificar disponibilidade geral
            if not servico_id:
                # Buscar serviços disponíveis para usar como fallback
                servicos = tools_instance.list_services(empresa_config)
                if servicos.get('success') and servicos.get('result'):
                    # Usar o primeiro serviço como padrão para verificar disponibilidade
                    servico_padrao = servicos.get('result', [])[0]
                    servico_id = servico_padrao.get('id')
                                    # CORREÇÃO: Não inventar serviço padrão
                logger.warning(f"⚠️ Não devemos inventar serviço padrão")
                return {"status": "erro", "error": "Serviço não identificado - necessário para verificação de disponibilidade"}
            
            disponibilidade = tools_instance.check_professional_availability(
                data_consulta,
                servico_id,
                empresa_config,
                profissional_id
            )
            
            # Enriquecer resposta com informações do contexto
            if disponibilidade and not disponibilidade.get('error'):
                disponibilidade['contexto_busca'] = {
                    'tipo_busca': 'por_profissional' if profissional_id else 'por_servico',
                    'servico_usado': servico_id,
                    'profissional_id': profissional_id,
                    'data_consulta': data_consulta
                }
                
                # ✅ PRESERVAR campos do serviço que já foram extraídos
                if data.get('duracao_em_minutos') or data.get('valor'):
                    disponibilidade['cache_instructions'] = {
                        "update_fields": {
                            "duracao_em_minutos": data.get('duracao_em_minutos'),
                            "valor": data.get('valor')
                        }
                    }
                
                # ✅ CACHE TEMPORÁRIO: Se múltiplos profissionais, salvar cache para resolução automática
                if disponibilidade.get('by_professional') and len(disponibilidade.get('by_professional', [])) > 1:
                    # Mesclar com cache_instructions existente ou criar novo
                    if 'cache_instructions' not in disponibilidade:
                        disponibilidade['cache_instructions'] = {"update_fields": {}}
                    
                    disponibilidade['cache_instructions']['update_fields'].update({
                        "temp_professional_cache": {
                            f"{prof.get('nome', 'N/A')} (ID: {prof.get('id', 'N/A')})": prof.get('slots', [])
                            for prof in disponibilidade.get('by_professional', [])
                        },
                        "temp_cache_expiry": 2
                    })
                    logger.info(f"🔄 Cache temporário criado para {len(disponibilidade.get('by_professional', []))} profissionais")
            
            return disponibilidade
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar disponibilidade: {e}")
            return {"status": "erro", "error": str(e)}
    
    def _execute_validar_slots(self, tools_instance, data: Dict[str, Any], empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """Executa validação de slots via Tools"""
        try:
            disponibilidade = data.get('disponibilidade', {})
            servico_info = data.get('servico_info', {})
            
            if disponibilidade and disponibilidade.get('horariosVagos'):
                # Obter duração do serviço
                procedure_duration = self.get_procedure_duration(
                    servico_info.get('nome', ''),
                    servico_info
                )
                
                # Validar slots
                slots_data = [{'horario': slot, 'disponivel': True} for slot in disponibilidade['horariosVagos']]
                valid_slots = tools_instance.filter_available_slots_by_duration(
                    slots_data,
                    procedure_duration,
                    empresa_config
                )
                
                return valid_slots
            else:
                return {"status": "sem_horarios"}
                
        except Exception as e:
            return {"status": "erro", "error": str(e)}

    def _execute_coletar_cliente(self, tools_instance, data: Dict[str, Any], empresa_config: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Executa coleta de cliente via Tools"""
        try:
            waid = context.get('waid') if context else None
            if not waid:
                return {"status": "erro", "error": "Waid não encontrado no contexto"}
            
            # Se já temos cliente_id, não precisa coletar
            if data.get('cliente_id'):
                return {"status": "cliente_ja_existe", "cliente_id": data.get('cliente_id')}
            
            # Se não temos CPF, precisamos perguntar
            if not data.get('cpf'):
                return {
                    "status": "perguntar_cpf"
                    # ✅ Sem mensagem fixa - Smart Agent gera!
                }
            
            # Buscar cliente por CPF
            cpf = data.get('cpf')
            resultado_busca = tools_instance.buscar_cliente_por_cpf(cpf, empresa_config)
            
            if resultado_busca.get('found'):
                # Cliente encontrado
                return {
                    "status": "cliente_encontrado",
                    "cliente_id": resultado_busca.get('cliente_id'),
                    "nome": resultado_busca.get('nome'),
                    "cpf": resultado_busca.get('cpf'),
                    "dados_cliente": resultado_busca,
                    "cache_instructions": {  # ✅ NOVO: Instruções para o Smart Agent
                        "update_fields": {
                            "cliente_id": resultado_busca.get('cliente_id'),
                            "nome": resultado_busca.get('nome'),
                            # ✅ PRESERVAR campos do serviço que já foram extraídos
                            "duracao_em_minutos": data.get('duracao_em_minutos'),
                            "valor": data.get('valor')
                        }
                    }
                }
            else:
                # ✅ NOVO: Cliente não encontrado - CRIAR automaticamente
                logger.info(f"👤 Cliente não encontrado - criando automaticamente para CPF: {cpf}")
                
                # ✅ Extrair nome da mensagem ou usar padrão
                nome = data.get('nome', 'Cliente')
                
                # ✅ Criar cliente automaticamente usando waid
                dados_cliente = {
                    "nome": nome,
                    "cpf": cpf,
                    "email": data.get('email')  # Opcional
                }
                
                resultado_criacao = tools_instance.criar_cliente(dados_cliente, empresa_config, waid)
                
                if resultado_criacao.get('success'):
                    logger.info(f"✅ Cliente criado automaticamente: {nome} (ID: {resultado_criacao.get('cliente_id')})")
                    return {
                        "status": "cliente_criado_automatico",
                        "cliente_id": resultado_criacao.get('cliente_id'),
                        "nome": nome,
                        "cpf": cpf,
                        "dados_cliente": resultado_criacao,
                        "cache_instructions": {
                            "update_fields": {
                                "cliente_id": resultado_criacao.get('cliente_id'),
                                "nome": nome,
                                # ✅ PRESERVAR campos do serviço que já foram extraídos
                                "duracao_em_minutos": data.get('duracao_em_minutos'),
                                "valor": data.get('valor')
                            }
                        }
                    }
                else:
                    logger.error(f"❌ Falha na criação automática do cliente: {resultado_criacao.get('error')}")
                    return {
                        "status": "erro_criacao_automatica",
                        "error": resultado_criacao.get('error'),
                        "suggestion": "Cliente não encontrado e não foi possível criar automaticamente"
                    }
                    
        except Exception as e:
            return {"status": "erro", "error": str(e)}
    
    def _execute_confirmar_agendamento(self, tools_instance, data: Dict[str, Any], empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """Executa confirmação do agendamento via Tools"""
        try:
            # Preparar dados para confirmação
            dados_agendamento = {
                "profissional_id": data.get('profissional_id'),
                "servico_id": data.get('servico_id'),
                "data": data.get('data'),
                "horario": data.get('horario'),
                "cliente_id": data.get('cliente_id'),
                "profissional": data.get('profissional'),
                "servico": data.get('procedimento'),
                "cliente_nome": data.get('cliente_nome'),
                "observacoes": data.get('observacoes')
            }
            
            # Confirmar agendamento
            resultado = tools_instance.confirmar_agendamento(dados_agendamento, empresa_config)
            
            if resultado.get('success'):
                return {
                    "status": "confirmado",
                    "resumo": resultado.get('resumo'),
                    "dados_validados": resultado.get('dados_validados'),
                    "message": resultado.get('message'),
                    "cache_instructions": {  # ✅ NOVO: Instruções para o Smart Agent
                        "update_fields": {
                            # ✅ PRESERVAR campos do serviço que já foram extraídos
                            "duracao_em_minutos": data.get('duracao_em_minutos'),
                            "valor": data.get('valor')
                        }
                    }
                }
            else:
                return {
                    "status": "erro",
                    "error": resultado.get('error'),
                    "campos_faltantes": resultado.get('campos_faltantes', [])
                }
                
        except Exception as e:
            return {"status": "erro", "error": str(e)}
    
    def _execute_criar_reserva(self, tools_instance, data: Dict[str, Any], empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """Executa criação da reserva via Tools"""
        try:
            # Preparar dados para criação da reserva
            dados_agendamento = {
                "profissional_id": data.get('profissional_id'),
                "servico_id": data.get('servico_id'),
                "data": data.get('data'),
                "horario": data.get('horario'),
                "cliente_id": data.get('cliente_id'),
                # ✅ Incluir campos obrigatórios vindos do serviço
                "duracao_em_minutos": data.get('duracao_em_minutos'),
                "valor": data.get('valor'),
                "observacoes": data.get('observacoes')
            }
            
            # Criar reserva
            resultado = tools_instance.criar_reserva(dados_agendamento, empresa_config)
            
            if resultado.get('success'):
                return {
                    "status": "reserva_criada",
                    "appointment_id": resultado.get('appointment_id'),
                    "message": resultado.get('message'),
                    "dados_completos": resultado.get('dados_completos'),
                    "cache_instructions": {  # ✅ NOVO: Instruções para o Smart Agent
                        "update_fields": {
                            "appointment_id": resultado.get('appointment_id')
                        }
                    }
                }
            else:
                return {
                    "status": "erro",
                    "error": resultado.get('error')
                }
                
        except Exception as e:
            return {"status": "erro", "error": str(e)}

    def execute_flow(self, flow_type: str, data: Dict[str, Any], empresa_config: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Executa um fluxo completo (ex: agendar_consulta)
        Args:
            flow_type: Tipo do fluxo
            data: Dados para execução
            empresa_config: Configuração da empresa
            context: Contexto da conversa
        Returns:
            Resultado completo do fluxo
        """
        try:
            if flow_type == "agendar_consulta":
                return self._execute_agendar_consulta_flow(data, empresa_config, context)
            else:
                return {"status": "erro", "error": f"Fluxo '{flow_type}' não implementado"}
                
        except Exception as e:
            return {"status": "erro", "error": str(e)}
    
    def _execute_agendar_consulta_flow(self, data: Dict[str, Any], empresa_config: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Executa fluxo completo de agendar_consulta"""
        try:
            logger.info(f"🔄 Executando fluxo completo de agendar_consulta")
            
            # Obter waid do contexto
            waid = context.get('waid') if context else None
            if not waid:
                return {"status": "erro", "error": "Waid não encontrado no contexto"}
            
            # ✅ CORREÇÃO: Usar dados enriquecidos do contexto em vez dos dados originais
            enriched_data = data.copy()
            
            # Tentar obter dados enriquecidos do contexto (cache)
            if context and isinstance(context, dict):
                # Buscar dados do cache via previous_data ou extracted_data
                previous_data = context.get('previous_data', {})
                extracted_data = context.get('extracted_data', {})
                
                # Mesclar dados para ter o contexto completo
                if previous_data:
                    enriched_data.update(previous_data)
                if extracted_data:
                    enriched_data.update(extracted_data)
                
                logger.info(f"📋 Dados enriquecidos para criação da reserva: {enriched_data}")
            
            # Sem validação antecipada: a LLM de próximos passos decide o que coletar/executar
            
            # Importar Tools
            from tools.trinks_intelligent_tools import TrinksIntelligentTools
            tools_instance = TrinksIntelligentTools(empresa_config)
            
            resultado = {}
            
            # PASSO 1: Coletar cliente
            logger.info("📋 PASSO 1: Coletar cliente")
            step_result = self._execute_coletar_cliente(tools_instance, enriched_data, empresa_config, context)
            resultado['coletar_cliente'] = step_result
            
            if step_result.get('status') == 'erro':
                return step_result
            
            # Se precisa perguntar algo, retornar para o Smart Agent
            if step_result.get('status') in ['perguntar_cpf', 'perguntar_nome']:
                return step_result
            
            # PASSO 2: Confirmar agendamento
            logger.info("📋 PASSO 2: Confirmar agendamento")
            step_result = self._execute_confirmar_agendamento(tools_instance, enriched_data, empresa_config)
            resultado['confirmar_agendamento'] = step_result
            
            if step_result.get('status') == 'erro':
                return step_result
            
            # PASSO 3: Criar reserva
            logger.info("📋 PASSO 3: Criar reserva")
            step_result = self._execute_criar_reserva(tools_instance, enriched_data, empresa_config)
            resultado['criar_reserva'] = step_result
            
            if step_result.get('status') == 'erro':
                return step_result
            
            # Sucesso! Retornar resultado completo
            logger.info("✅ Fluxo de agendar_consulta executado com sucesso")
            return {
                "status": "sucesso",
                "appointment_id": step_result.get('appointment_id'),
                "profissional": enriched_data.get('profissional'),
                "servico": enriched_data.get('procedimento'),
                "data": enriched_data.get('data'),
                "horario": enriched_data.get('horario'),
                "cliente": enriched_data.get('cliente_nome'),
                "cliente_id": enriched_data.get('cliente_id'),
                "message": "Agendamento realizado com sucesso",
                "resultado_completo": resultado
            }
            
        except Exception as e:
            logger.error(f"❌ Erro no fluxo de agendar_consulta: {e}")
            return {"status": "erro", "error": str(e)}

    # ========================================
    # 6. MÉTODOS DE INTELIGÊNCIA (Rules → LLM)
    # ========================================
    
    def extract_data(self, message: str, context: Dict[str, Any], empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """Extração de dados via LLM dentro das Rules (histórico + previous_data)."""
        try:
            previous_data = (context or {}).get('previous_data', {}) if isinstance(context, dict) else {}
            history_str = ""
            try:
                hist = (context or {}).get('conversation_history', []) if isinstance(context, dict) else []
                history_str = "\n".join([getattr(m, 'content', str(m)) for m in hist[-8:]])
            except Exception:
                pass

            system_prompt = f"""Extraia campos estruturados da conversa.

CONTEXTO ATUAL: Hoje é {datetime.now().strftime('%d/%m/%Y')} (DD/MM/YYYY).

CAMPOS:
- profissional, profissional_id
- procedimento, servico_id
- data (YYYY-MM-DD)
- horario (HH:MM)
- cpf, client_id, nome, email

REGRAS:
- Use a mensagem atual como prioridade; complete com previous_data quando fizer sentido.
- Responda APENAS um JSON com as chaves pedidas.
"""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"PREVIOUS_DATA: {previous_data}"),
                HumanMessage(content=f"HISTORICO:\n{history_str}"),
                HumanMessage(content=f"MENSAGEM_ATUAL: {message}")
            ]

            llm = self._get_llm(empresa_config)
            response = llm.invoke(messages)
            raw = (getattr(response, 'content', str(response)) or '').strip()
            cleaned = self._clean_llm_json(raw)
            import json
            data = json.loads(cleaned)
            return data if isinstance(data, dict) else {}
        except Exception as e:
            logger.error(f"Erro ao extrair dados: {e}")
            return {}

    def decide_next_steps(self, intent: str, context: Dict[str, Any], empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """Definição de próximos passos via LLM (orquestração de alto nível nas Rules)."""
        try:
            previous_data = (context or {}).get('previous_data', {}) if isinstance(context, dict) else {}
            extracted_data = (context or {}).get('extracted_data', {}) if isinstance(context, dict) else {}
            history_str = ""
            try:
                hist = (context or {}).get('conversation_history', []) if isinstance(context, dict) else []
                history_str = "\n".join([getattr(m, 'content', str(m)) for m in hist[-8:]])
            except Exception:
                pass

            # Logs de entrada
            try:
                logger.info(
                    f"🧭 Decidindo próximos passos | intent={intent} | prev_keys={list(previous_data.keys())} | extracted_keys={list(extracted_data.keys())}"
                )
            except Exception:
                pass

            system_prompt = """# DECISOR DE PRÓXIMOS PASSOS - TRINKS

## SUA FUNÇÃO
Você é um DECISOR que analisa dados e decide quais próximos passos tomar.
Você NÃO executa tools - apenas decide o que deve ser feito.

## ENTRADAS
- intent: {intent}
- previous_data: dados do cache anterior
- extracted_data: dados extraídos da mensagem atual

## TOOLS DISPONÍVEIS
- buscar_servico: busca serviço por nome
- buscar_profissional: busca profissional por nome  
- verificar_disponibilidade: verifica horários disponíveis
- coletar_cliente: busca/cria cliente por CPF
- criar_reserva: cria agendamento
- listar_agendamentos: lista agendamentos do cliente
- cancelar_agendamento: cancela agendamento
- verificar_informacoes_profissional: obtém info do profissional

## FLUXOS DE DECISÃO

### agendar_consulta
**DADOS NECESSÁRIOS:** Data, profissional_id, serviço_id, horario, cliente_id

**DECISÕES SEQUENCIAIS - SIGA EXATAMENTE ESTA ORDEM:**

**PASSO 1: Resolver IDs quando possível (antes de pedir data)**
- Se existir profissional OU procedimento em extracted_data/previous_data e FALTAR data:
  - Se tiver profissional (nome) e/ou procedimento (nome) mas SEM profissional_id/serviço_id → action=["buscar_profissional" (se houver profissional), "buscar_servico" (se houver procedimento)]
  - Objetivo: resolver profissional_id e servico_id primeiro

**PASSO 2: Verificar dados básicos restantes**
- Se após o PASSO 1 ainda faltar data → action="ask_user" com missing_data=["data"]
- Se JÁ houver data e faltar horário → action="ask_user" com missing_data=["horario"].
  - Importante: quando profissional e/ou procedimento vierem por NOME, você pode buscar IDs em paralelo DEPOIS, mas NÃO avance para disponibilidade sem antes pedir o horário.

**PASSO 3: Verificar disponibilidade**
- Se tiver profissional_id + servico_id + data e existir um horário definido → action=["verificar_disponibilidade"]

**PASSO 4: Coletar dados do cliente**
- Se faltar cliente_id (CPF e Nome Completo) → action="ask_user"

**PASSO 5: Criar agendamento**
- Se tiver todos os IDs + data + horário + CPF + Nome → action=["coletar_cliente", "criar_reserva"]

### cancelar_consulta
**DADOS NECESSÁRIOS:** cliente_id, agendamento_id

**DECISÕES SEQUENCIAIS:**
1. Se faltar CPF → action="ask_user"
2. Se tiver CPF mas SEM client_id → action=["coletar_cliente", "listar_agendamentos", "cancelar_agendamento"]
3. Se tiver agendamento_id → action=["listar_agendamentos", "cancelar_agendamento"]

### verificar_informacoes
**DADOS NECESSÁRIOS:** profissional, procedimento

**DECISÕES SEQUENCIAIS:**
1. Se faltar profissional OU procedimento → action="ask_user"
2. Se tiver ambos → action=["buscar_profissional", "verificar_informacoes_profissional"]

## REGRAS DE NEGÓCIO
- Para buscar_cliente: se faltar client_id, peça apenas CPF (não precisa do nome)
- Para verificar_informacoes: se faltar profissional, peça apenas nome

## EXEMPLOS DE DECISÃO - AGENDAR_CONSULTA

**Exemplo 1: Procedimento + Data (SEM IDs)**
- Input: "quero marcar AAA Teste dia 01/09"
- Dados: procedimento="AAA Teste", data="2025-09-01", profissional_id=None, serviço_id=None
- DECISÃO: action=["buscar_servico", "verificar_disponibilidade"]
- MOTIVO: Tem procedimento + data, mas precisa resolver IDs primeiro

**Exemplo 2: Procedimento + Data + Profissional (SEM IDs e SEM horário)**
- Input: "quero marcar consulta com Dr. João dia 15"
- Dados: procedimento="consulta", data="2025-08-15", profissional="Dr. João", profissional_id=None, serviço_id=None, horario=None
- DECISÃO: action="ask_user", missing_data=["horario"] (IDs podem ser resolvidos em paralelo depois)
- MOTIVO: Com data presente e horário ausente, DEVE pedir horário antes de seguir para disponibilidade

**Exemplo 3: Todos os IDs + Data (SEM horário)**
- Input: "já tenho o serviço e profissional, só preciso do horário"
- Dados: profissional_id="123", serviço_id="456", data="2025-08-20", horario=None
- DECISÃO: action="ask_user", missing_data=["horario"]
- MOTIVO: Mesmo com IDs + data, com horário ausente deve pedir o horário para então verificar disponibilidade

**Exemplo 4: Faltam dados do cliente**
- Input: "perfeito, quero confirmar às 15h"
- Dados: profissional_id="123", serviço_id="456", data="2025-08-20", horario="15:00", cpf=None, nome=None
- DECISÃO: action="ask_user"
- MOTIVO: Tem tudo, só falta CPF e nome do cliente

## EXEMPLOS DE DECISÃO - OUTROS INTENTS

**Exemplo 5: Cancelar consulta**
- Input: "quero cancelar minha consulta"
- DECISÃO: action="ask_user", missing_data=["CPF"]
- MOTIVO: Precisa do CPF para identificar o cliente

## FORMATO DE SAÍDA OBRIGATÓRIO
```json
{
  "action": "ask_user" OU ["tool1", "tool2"],
  "missing_data": ["informacao1", "informacao2"] (apenas se action="ask_user"),
  "business_rules": ["regra específica para o caso"]
}
```

## REGRA FUNDAMENTAL
**VOCÊ DECIDE O QUE FAZER, O SISTEMA EXECUTA.**
**NUNCA execute tools diretamente - apenas decida quais devem ser executadas.**

## LEMBRE-SE
- **SEMPRE execute as tools necessárias ANTES de pedir dados do usuário, EXCETO quando intent=agendar_consulta tiver DATA presente e HORARIO ausente. Neste caso, PEÇA o horário primeiro (action="ask_user", missing_data=["horario"]).**
- **NUNCA retorne missing_data vazio quando intent=agendar_consulta tiver data e horario=None.**
- **NUNCA pule para disponibilidade sem horário quando profissional/procedimento vierem por nome; IDs podem ser resolvidos em paralelo.**
- **A ordem dos passos é CRÍTICA - siga exatamente a sequência**
"""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"intent={intent}"),
                HumanMessage(content=f"previous_data={previous_data}"),
                HumanMessage(content=f"extracted_data={extracted_data}"),
                HumanMessage(content=f"history=\n{history_str}")
            ]

            llm = self._get_llm(empresa_config)
            response = llm.invoke(messages)
            raw = (getattr(response, 'content', str(response)) or '').strip()
            cleaned = self._clean_llm_json(raw)
            import json
            data = json.loads(cleaned)
            try:
                logger.info(
                    f"🧭 Próximos passos decididos | action={data.get('action')} | missing={data.get('missing_data')}"
                )
            except Exception:
                pass
            return data if isinstance(data, dict) else {"action": "ask_user", "agent_response": "Poderia detalhar?"}
        except Exception as e:
            logger.error(f"Erro ao decidir próximos passos: {e}")
            return {"action": "ask_user", "agent_response": "Poderia repetir, por favor?", "missing_fields": []}

    def detect_intent_and_extract(self, message: str, context: Dict[str, Any], empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """Função unificada: detecta intenção e extrai informações em uma única chamada LLM"""
        try:
            # Obter contexto limitado (últimas 10 mensagens para melhor contexto)
            context_messages = []
            if context and 'conversation_history' in context:
                # Usar até 10 mensagens para melhor contexto e performance
                context_messages = context['conversation_history'][-10:]
                logger.info(f"Adicionando contexto para parsing: {len(context_messages)} mensagens anteriores")
                logger.info(f"Últimas mensagens do contexto: {[msg.content for msg in context_messages[-4:]]}")
            else:
                logger.warning("NENHUM contexto disponível para parsing!")
            
            # ✅ NOVO: Obter cache temporário do contexto para resolução automática
            temp_professional_cache = None
            temp_cache_expiry = None
            if context and 'previous_data' in context:
                previous_data = context['previous_data']
                temp_professional_cache = previous_data.get('temp_professional_cache')
                temp_cache_expiry = previous_data.get('temp_cache_expiry')
                
                if temp_professional_cache:
                    logger.info(f"🔄 Cache temporário encontrado: {len(temp_professional_cache)} profissionais")
                    logger.info(f"🔄 Cache expira em: {temp_cache_expiry} mensagens")
                else:
                    logger.info("📋 Nenhum cache temporário disponível no contexto")
            
            # Obter fluxos disponíveis para detecção de intenção
            rules = self.get_api_rules()
            flows = rules.get('fluxos_por_intencao', {})
            available_intents = list(flows.keys()) if flows else []
            
            # Construir prompt unificado
            system_prompt = f"""Você é um assistente que analisa mensagens de WhatsApp para agendamentos.

CONTEXTO ATUAL: Hoje é {datetime.now().strftime('%d/%m/%Y')} (DD/MM/YYYY).

INTENÇÕES SUPORTADAS: {', '.join(available_intents) if available_intents else 'Nenhuma intenção específica configurada'}

FUNÇÃO PRINCIPAL: Analisar a mensagem e retornar APENAS um objeto JSON com intenção, informações extraídas e instruções de cache.

🚨 REGRA CRÍTICA: Se a mensagem atual NÃO mencionar profissional/procedimento, mas a ÚLTIMA MENSAGEM DO BOT contiver esses dados → EXTRAIA DO CONTEXTO ANTERIOR automaticamente.

ESTRUTURA OBRIGATÓRIA:
{{
  "intent": "<intenção_detectada>",
  "extracted": {{
    "profissional": "nome da pessoa mencionada (se houver, OU do contexto anterior)",
    "procedimento": "tipo de serviço/procedimento (se houver, OU do contexto anterior)",
    "data": "data mencionada (converta para YYYY-MM-DD)",
    "horario": "horário mencionado (se houver)",
    "profissional_id": "ID do profissional (se resolvido via cache)",
    "servico_id": "ID do serviço (se resolvido via cache)",
    "cpf": "CPF mencionado (se houver)",
    "nome": "nome do cliente mencionado (se houver)",
    "email": "email do cliente mencionado (se houver)"
  }},
  "cache_instructions": {{
    "clear_fields": ["lista_de_campos_para_limpar_do_cache"]
  }}
}}

REGRAS DE CLASSIFICAÇÃO DE INTENÇÃO:
- agendar_consulta: Quando o cliente quiser agendar uma consulta 
- cancelar_consulta: Quando o cliente quer cancelar agendamento existente
- reagendar_consulta: Quando o cliente quer mudar data/horário de agendamento existente
- verificar_informacoes: Para mensagens que o usuário quer saber o preço ou como funciona o serviço

EXEMPLOS DE CLASSIFICAÇÃO:
- "Sim, esse horário de amanhã às 14h está perfeito!" → agendar_consulta
- "Perfeito, confirma o dia 25 às 15h" → agendar_consulta
- "Qual o preço da consulta?" → verificar_informacoes
- "Qual o valor da consulta com a Dra. Juliana?" → verificar_informacoes
- "Quanto custa a limpeza de pele?" → verificar_informacoes

CONVERSÃO DE DATAS:
- "25/08" → "2025-08-25"
- "segunda" → próxima segunda-feira em YYYY-MM-DD
- "amanhã" → data de amanhã em YYYY-MM-DD
- "hoje" → data de hoje em YYYY-MM-DD

CONVERSÃO DE CPF: 
- SEMPRE SEM ".", "-", " "
- Exemplo: "123.456.789-01", "123456789-01" → "12345678901"

REGRAS CRÍTICAS DE PRIORIDADE:
1. SEMPRE retorne APENAS JSON válido
2. A MENSAGEM ATUAL TEM PRIORIDADE sobre o contexto anterior, MAS se a mensagem atual NÃO mencionar profissional/procedimento e a ÚLTIMA MENSAGEM DO BOT contiver esses dados → EXTRAIA DO CONTEXTO ANTERIOR automaticamente
3. APENAS extraia data caso você tenha sugerido aquele horário anteriormente, nunca extraia data que não verificamos ainda
4. Se a mensagem atual mencionar nova data, use APENAS ela (ignore datas anteriores)
5. Se a mensagem atual mencionar novo horário, use APENAS ele (ignore horários anteriores)
6. Se a mensagem atual mencionar novo profissional, use APENAS ele (ignore profissionais anteriores)
7. Use o contexto anterior para informações NÃO mencionadas na mensagem atual, ESPECIALMENTE profissional e procedimento da última mensagem do bot
8. NUNCA mantenha dados antigos se novos foram explicitamente mencionados
9. REGRA ESPECIAL: Se a mensagem atual só mencionar data/horário mas NÃO mencionar profissional/procedimento, SEMPRE extraia profissional e procedimento da última mensagem do bot disponível no contexto
10. Avaliação Gratuita é um procedimento também no tinks, caso encontre no historico de mensagem pode extrarir

REGRAS DE LIMPEZA DE CACHE:
1. SEMPRE que mencionar NOVO profissional → clear_fields: ["profissional_id", "horario"]
2. SEMPRE que mencionar NOVO procedimento/serviço → clear_fields: ["servico_id", "horario"]
3. SEMPRE que mencionar NOVA data → clear_fields: ["horario"] (se horário era específico)
4. SEMPRE que mencionar NOVO horário → clear_fields: [] (não limpa nada)
5. Se NÃO mencionar mudanças → clear_fields: [] (não limpa nada)

RESOLUÇÃO AUTOMÁTICA DE PROFISSIONAL:
- Se horário específico for mencionado → use o histórico para tentar identificar qual profissional tem esse horário na última mensagem do bot!
- Example: "14:30" → verifique se na ultima mensagem do Bot era listado o nome de algum profissional com 14:30 listado
- Se encontrar → extraia também o profissional_id correspondente

CACHE TEMPORÁRIO DE PROFISSIONAIS:
- Se disponível no contexto → use para resolver automaticamente profissional por horário
- Example: Se cache contém "Amabile (ID: 564031): 14h, 15h | Geraldine (ID: 564410): 16h"
- E usuário diz "15h" → extraia automaticamente:
  - horario: "15:00"
  - profissional_id: "564031" (Amabile)
- Cache expira automaticamente após 2 mensagens

EXEMPLO de resolução automática de profissional:
Histórico: "Amabile: 14:30, 15:00 | Geraldine: 09:30, 10:00"
Mensagem: "Pode ser as 14:30"
Resposta: {{
    "horario": "14:30",
    "profissional_id": "564031"
}}

EXEMPLO OBRIGATÓRIO DE USO DO CONTEXTO ANTERIOR:
- Última mensagem do Bot: "O Laser Lavien é um tratamento incrível... com a Dra. Amabile. Gostaria de agendar?"
- Mensagem atual do Usuário: "Sim, pode ser dia 01/09"
- RESULTADO OBRIGATÓRIO: 
  - profissional: "Dra. Amabile" (extraído do contexto anterior)
  - procedimento: "Laser Lavien" (extraído do contexto anterior)
  - data: "2025-09-01" (extraído da mensagem atual)
  - cache_instructions: {{"clear_fields": ["horario"]}}

EXEMPLO de resolução automática de profissional:
Histórico: "Amabile: 14:30, 15:00 | Geraldine: 09:30, 10:00"
Mensagem: "Pode ser as 14:30"
Resposta: {{
    "horario": "14:30",
    "profissional_id": "564031"
}}

EXEMPLOS DE CACHE_INSTRUCTIONS:
- "E para a Maria?" → {{"intent": "agendar_consulta", "extracted": {{"profissional": "maria"}}, "cache_instructions": {{"clear_fields": ["profissional_id", "horario"]}}}}
- "E para aplicação de enzimas?" → {{"intent": "agendar_consulta", "extracted": {{"procedimento": "aplicação de enzimas"}}, "cache_instructions": {{"clear_fields": ["servico_id", "horario"]}}}}
- "E para dia 28/08?" → {{"intent": "agendar_consulta", "extracted": {{"data": "2025-08-28"}}, "cache_instructions": {{"clear_fields": ["horario"]}}}}
- "E para às 15h?" → {{"intent": "agendar_consulta", "extracted": {{"horario": "15:00"}}, "cache_instructions": {{"clear_fields": []}}}}
- "Oi queria marcar retorno" → {{"intent": "agendar_consulta", "extracted": {{}}, "cache_instructions": {{"clear_fields": []}}}}

EXEMPLOS DE PRIORIDADE:
- "E para dia 28/08?" → {{"intent": "agendar_consulta", "extracted": {{"data": "2025-08-28"}}}} (IGNORE data anterior)
- "E para às 15h?" → {{"intent": "agendar_consulta", "extracted": {{"horario": "15:00"}}}} (IGNORE horário anterior)
- "E para a Maria?" → {{"intent": "agendar_consulta", "extracted": {{"profissional": "maria"}}}} (IGNORE profissional anterior)

EXEMPLOS DE PROCEDIMENTOS:
- "consulta" → procedimento: "consulta"
- "retorno" → procedimento: "retorno"
- "limpeza de pele" → procedimento: "limpeza de pele"
- "toxina botulínica" → procedimento: "toxina botulínica"

EXEMPLOS DE RESPOSTA COMPLETA:
- "Oi queria marcar retorno com a amabile" → {{"intent": "agendar_consulta", "extracted": {{"profissional": "amabile", "procedimento": "retorno"}}, "cache_instructions": {{"clear_fields": ["profissional_id", "horario"]}}}}
- "Para segunda feira" → {{"intent": "agendar_consulta", "extracted": {{"data": "2025-08-18"}}, "cache_instructions": {{"clear_fields": ["horario"]}}}}
- "as 19 ela tem?" → {{"intent": "agendar_consulta", "extracted": {{"horario": "19:00", "profissional": "amabile"}}, "cache_instructions": {{"clear_fields": ["profissional_id", "horario"]}}}}
- "Sim, esse horário está perfeito!" → {{"intent": "agendar_consulta", "extracted": {{}}, "cache_instructions": {{"clear_fields": []}}}}
- "Tanto faz, qualquer um" → {{"intent": "agendar_consulta", "extracted": {{"profissional": "indiferente"}}, "cache_instructions": {{"clear_fields": ["profissional_id", "horario"]}}}}

IMPORTANTE: A mensagem atual SEMPRE tem prioridade sobre o contexto anterior. Se o usuário mencionar uma nova data, horário ou profissional, use APENAS essas informações novas.

FORMATO OBRIGATÓRIO: Retorne APENAS o JSON, sem texto adicional, sem explicações."""
            
            try:
                messages = [SystemMessage(content=system_prompt)]
                
                # ✅ NOVO: Adicionar contexto do cache temporário se disponível
                if temp_professional_cache:
                    cache_context = f"""

CACHE TEMPORÁRIO DISPONÍVEL (expira em {temp_cache_expiry} mensagens):
{json.dumps(temp_professional_cache, indent=2, ensure_ascii=False)}

REGRAS OBRIGATÓRIAS PARA CACHE:
1. SEMPRE que extrair horário → extraia também o profissional_id correspondente do cache
2. Se cache tem "Geraldine Nagel (ID: 564410): ['09:30', '10:00']" e usuário diz "09:30" → extraia: "horario": "09:30", "profissional_id": "564410"
3. NUNCA retorne horário sem profissional_id quando cache estiver disponível
4. Use o nome do profissional para fazer match exato no cache
5. EXEMPLO OBRIGATÓRIO: Se usuário diz "09:30" e cache tem "Geraldine Nagel (ID: 564410): ['09:30', '10:00']" → extraia BOTH: "horario": "09:30" E "profissional_id": "564410"
"""
                    messages.append(SystemMessage(content=cache_context))
                    logger.info(f"🔄 Contexto do cache temporário adicionado ao prompt")
                    logger.info(f"🔄 Cache enviado para LLM: {temp_professional_cache}")
                    logger.info(f"🔄 Total de mensagens para LLM: {len(messages)}")
                else:
                    logger.info("📋 Nenhum cache temporário disponível para enviar ao prompt")
                
                # Adicionar contexto da conversa (últimas 10 mensagens)
                if context_messages:
                    messages.extend(context_messages)
                
                # Adicionar a mensagem atual
                messages.append(HumanMessage(content=message))
                
                llm = self._get_llm(empresa_config)
                response = llm.invoke(messages)
                
                # LOG da resposta bruta do LLM
                logger.info(f"Resposta bruta do LLM unificado: '{response.content}'")
                logger.info(f"Tamanho da resposta: {len(response.content)}")
                
                # Verificar se a resposta está vazia
                if not response.content or response.content.strip() == "":
                    logger.error("LLM retornou resposta vazia")
                    return {"intent": "verificar_informacoes", "extracted": {}}
                
                # Limpar resposta do LLM (remover backticks se existirem)
                content = response.content.strip()
                if content.startswith('```json'):
                    content = content[7:-3]  # Remove ```json e ```
                elif content.startswith('```'):
                    content = content[3:-3]  # Remove ``` genérico
                
                content = content.strip()
                logger.info(f"Conteúdo limpo para parse: {content}")
                
                # Parsear JSON da resposta
                try:
                    parsed = json.loads(content)
                    logger.info(f"Resultado do parsing unificado: {parsed}")
                    
                    # Validar estrutura
                    if not isinstance(parsed, dict):
                        logger.error("LLM retornou estrutura inválida")
                        return {"intent": "verificar_informacoes", "extracted": {}}
                    
                    intent = parsed.get("intent", "verificar_informacoes")
                    extracted = parsed.get("extracted", {})
                    
                    # ✅ NOVO: Validar se o cache temporário foi usado corretamente
                    if temp_professional_cache and extracted.get('horario') and not extracted.get('profissional_id'):
                        logger.warning(f"⚠️ Horário extraído ({extracted.get('horario')}) mas profissional_id não foi resolvido automaticamente")
                        logger.warning(f"⚠️ Cache disponível: {temp_professional_cache}")
                    
                    # ✅ ACEITAR QUALQUER INTENÇÃO QUE A LLM RETORNE
                    # A validação de intenções é desnecessária - a LLM sabe o que está fazendo
                    
                    return {
                        "intent": intent,
                        "extracted": extracted,
                        "cache_instructions": parsed.get("cache_instructions", {})
                    }
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Erro ao parsear JSON: {e}")
                    logger.error(f"Conteúdo que falhou: '{content}'")
                    return {"intent": "verificar_informacoes", "extracted": {}}
                
            except Exception as e:
                logger.error(f"Erro ao fazer parsing unificado: {e}")
                return {"intent": "verificar_informacoes", "extracted": {}}
        except Exception as e:
            logger.error(f"Erro ao fazer parsing unificado: {e}")
            return {"intent": "verificar_informacoes", "extracted": {}}
