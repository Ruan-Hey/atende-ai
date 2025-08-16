"""
Sistema de regras específicas para cada API
Define se email é obrigatório baseado na API ativa
"""

import logging
from typing import Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)

class APIType(Enum):
    """Tipos de APIs disponíveis"""
    GOOGLE_SHEETS = "Google Sheets"
    GOOGLE_CALENDAR = "Google Calendar"
    TRINKS = "Trinks"
    NONE = "Nenhuma"

class APIRulesEngine:
    """Motor de regras para APIs específicas"""
    
    def __init__(self):
        # Regras específicas para cada API
        self.api_rules = {
            APIType.GOOGLE_SHEETS: {
                "email_required": False,
                "waid_required": True,
                "reservation_flow": "sheets",
                "confirmation_message": "Reserva confirmada no Google Sheets!",
                "missing_fields_message": "Faltam informações para completar a reserva no Google Sheets",
                "search_by_waid": True,
                "waid_column": "Telefone"  # Coluna onde o WaId é armazenado
            },
            APIType.GOOGLE_CALENDAR: {
                "email_required": True,
                "waid_required": False,
                "reservation_flow": "calendar",
                "confirmation_message": "Reserva confirmada no Google Calendar!",
                "missing_fields_message": "Faltam informações para completar a reserva no Google Calendar"
            },
            APIType.TRINKS: {
                "email_required": False,
                "waid_required": False,  # WaId vem automaticamente do webhook
                "reservation_flow": "trinks",
                "confirmation_message": "Reserva confirmada no Trinks!",
                "missing_fields_message": "Faltam informações para completar a reserva no Trinks",
                
                # NOVO: Fluxos por intenção expandidos
                "fluxos_por_intencao": {
                    "verificar_disponibilidade": {
                        "passos": [
                            "extrair_dados", 
                            "determinar_tipo_busca", 
                            "buscar_entidade", 
                            "match_inteligente", 
                            "verificar_preferencia_profissional",  # Novo passo inteligente
                            "buscar_disponibilidade_por_servico", # Novo endpoint otimizado
                            "validar_slots_por_duracao",  # NOVO: Validação de slots por duração
                            "retornar_slots"
                        ],
                        "campos_obrigatorios": ["data"],
                        "campos_opcionais": ["profissional", "procedimento"],
                        "api_endpoints": [
                            "/profissionais",
                            "/servicos", 
                            "/agendamentos/servicos/{servico_id}/{data}"  # Novo endpoint por serviço+data
                        ],
                        "descricao": "Verifica horários disponíveis por serviço em uma data específica, com filtro opcional de profissional",
                        "instrucoes_llm": [
                            "1. Extraia a data da mensagem (obrigatório)",
                            "2. Extraia profissional OU procedimento (pelo menos um)",
                            "3. Determine o tipo de busca (por_profissional OU por_procedimento)",
                            "4. Use match inteligente para identificar entidade (profissional OU procedimento)",
                            "5. Se for por procedimento, busque o serviço correto",
                            "6. Verifique se já tem preferência de profissional na mensagem",
                            "7. Se não tiver preferência, pergunte educadamente",
                            "8. Busque disponibilidade por SERVIÇO + DATA (com filtro opcional de profissional)",
                            "9. Valide se há slots consecutivos suficientes para a duração do procedimento",
                            "10. Retorne apenas horários viáveis com slots consecutivos"
                        ],
                        "estrategias_match": [
                            "Compare o nome mencionado com a lista de entidades",
                            "Considere variações: 'Dr Amabile' pode ser 'Amabile Silva' ou 'Dr. Amabile'",
                            "Para procedimentos: 'massagem relaxante' pode ser 'Massagem Relaxante Profunda'",
                            "Use similaridade fonética e contextual",
                            "Priorize matches com títulos (Dr., Dra.)",
                            "Para procedimentos, considere sinônimos e variações"
                        ],
                        "fluxo_api": [
                            "GET /profissionais → Lista todos os profissionais",
                            "GET /servicos → Lista todos os serviços (se busca por procedimento)",
                            "LLM faz match inteligente → Identifica profissional OU procedimento correto",
                            "Verifica se já tem preferência de profissional na mensagem",
                            "Se não tiver preferência: pergunta educadamente",
                            "GET /agendamentos/servicos/{servico_id}/{data} → Busca disponibilidade por serviço+data",
                            "Parâmetro opcional: ?profissional_id={id} para filtrar por profissional específico",
                            "Validação automática: Filtra slots consecutivos suficientes para duração do procedimento"
                        ],
                        "tipos_busca": {
                            "por_profissional": {
                                "campos_necessarios": ["profissional", "data"],
                                "fluxo": ["buscar_profissionais", "match_inteligente", "buscar_disponibilidade_por_servico", "validar_slots_por_duracao"]
                            },
                            "por_procedimento": {
                                "campos_necessarios": ["procedimento", "data"],
                                "fluxo": ["buscar_servicos", "match_inteligente", "verificar_preferencia_profissional", "buscar_disponibilidade_por_servico", "validar_slots_por_duracao"]
                            }
                        },
                        "logica_preferencia": {
                            "se_ja_tem_profissional": "nao_perguntar_nao_mostrar_lista",
                            "se_nao_tem_profissional": "perguntar_educadamente_sem_mostrar_lista",
                            "endpoint_disponibilidade": "/agendamentos/servicos/{servico_id}/{data}",
                            "parametros_opcionais": {
                                "profissional_id": "ID do profissional para filtrar resultados (opcional)",
                                "sem_profissional": "Retorna disponibilidade de todos os profissionais que fazem o serviço"
                            }
                        },
                        "validacao_slots": {
                            "duracao_slot_padrao": 30,  # Slots padrão de 30 minutos
                            "regra_consecutivos": "Slots devem ser consecutivos para cobrir duração total",
                            "arredondamento": "Arredondar para cima para garantir tempo suficiente",
                            "exemplos": {
                                "45_min": "2 slots de 30 min (60 min total)",
                                "60_min": "2 slots de 30 min (60 min total)",
                                "90_min": "3 slots de 30 min (90 min total)",
                                "120_min": "4 slots de 30 min (120 min total)"
                            },
                            "validacao": [
                                "Calcular slots necessários: ceil(duracao_procedimento / duracao_slot)",
                                "Verificar se há slots consecutivos disponíveis",
                                "Validar que primeiro slot está livre",
                                "Confirmar que não há conflitos com outros agendamentos",
                                "Retornar apenas horários com slots consecutivos suficientes"
                            ]
                        }
                    },
                    "agendar_consulta": {
                        "passos": ["validar_dados", "criar_agendamento", "confirmar"],
                        "campos_obrigatorios": ["profissional", "servico", "data", "horario", "cliente"],
                        "api_endpoints": ["/agendamentos"],
                        "descricao": "Cria um novo agendamento com todos os dados necessários"
                    },
                    "cancelar_consulta": {
                        "passos": ["buscar_agendamento", "validar_cancelamento", "cancelar"],
                        "campos_obrigatorios": ["data", "cliente"],
                        "api_endpoints": ["/agendamentos", "/agendamentos/{id}/status/cancelado"],
                        "descricao": "Cancela uma consulta existente"
                    },
                    "reagendar_consulta": {
                        "passos": ["buscar_agendamento", "verificar_nova_disponibilidade", "atualizar"],
                        "campos_obrigatorios": ["data_atual", "nova_data", "cliente"],
                        "api_endpoints": ["/agendamentos", "/agendamentos/{id}"],
                        "descricao": "Altera a data/horário de uma consulta existente"
                    }
                }
            },
            APIType.NONE: {
                "email_required": False,
                "waid_required": False,
                "reservation_flow": "manual",
                "confirmation_message": "Reserva anotada! Entre em contato direto para confirmar.",
                "missing_fields_message": "Faltam informações para anotar a reserva"
            }
        }
    
    def detect_active_api(self, empresa_config: Dict[str, Any]) -> APIType:
        """Detecta qual API está ativa baseado na configuração"""
        try:
            # Verificar Google Sheets
            if (empresa_config.get('google_sheets_id') and 
                (empresa_config.get('google_sheets_client_id') or 
                 empresa_config.get('google_sheets_service_account'))):
                return APIType.GOOGLE_SHEETS
            
            # Verificar Google Calendar
            if (empresa_config.get('google_calendar_client_id') or 
                empresa_config.get('google_calendar_service_account')):
                return APIType.GOOGLE_CALENDAR
            
            # Verificar Trinks
            if empresa_config.get('trinks_enabled') and empresa_config.get('trinks_api_key'):
                return APIType.TRINKS
            
            # Nenhuma API configurada
            return APIType.NONE
            
        except Exception as e:
            logger.error(f"Erro ao detectar API ativa: {e}")
            return APIType.NONE
    
    def get_api_rules(self, empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """Retorna as regras da API ativa"""
        api_type = self.detect_active_api(empresa_config)
        rules = self.api_rules[api_type].copy()
        rules['api_type'] = api_type
        rules['api_name'] = api_type.value
        
        logger.info(f"Regras da API ativa ({api_type.value}): {rules}")
        return rules
    
    def is_email_required(self, empresa_config: Dict[str, Any]) -> bool:
        """Verifica se email é obrigatório para a API ativa"""
        rules = self.get_api_rules(empresa_config)
        return rules.get('email_required', False)
    
    def is_waid_required(self, empresa_config: Dict[str, Any]) -> bool:
        """Verifica se WaId é obrigatório para a API ativa"""
        rules = self.get_api_rules(empresa_config)
        return rules.get('waid_required', False)
    
    def get_confirmation_message(self, empresa_config: Dict[str, Any]) -> str:
        """Retorna mensagem de confirmação específica da API"""
        rules = self.get_api_rules(empresa_config)
        return rules.get('confirmation_message', "Reserva confirmada!")
    
    def get_missing_fields_message(self, empresa_config: Dict[str, Any]) -> str:
        """Retorna mensagem de campos faltantes específica da API"""
        rules = self.get_api_rules(empresa_config)
        return rules.get('missing_fields_message', "Faltam informações para completar a reserva")
    
    def get_reservation_status(self, empresa_config: Dict[str, Any], 
                              reservation_context: Dict[str, Any]) -> str:
        """Determina o status da reserva baseado nas regras da API"""
        rules = self.get_api_rules(empresa_config)
        api_type = rules['api_type']
        
        # Campos obrigatórios baseados na API
        required_fields = ['cliente_nome', 'quantidade_pessoas', 'data_reserva', 'horario_reserva']
        
        if api_type == APIType.GOOGLE_SHEETS:
            required_fields.append('waid')
        elif api_type in [APIType.GOOGLE_CALENDAR, APIType.TRINKS]:
            if rules['email_required']:
                required_fields.append('email')
        
        # Verificar se todos os campos obrigatórios estão preenchidos
        missing_fields = [field for field in required_fields 
                         if not reservation_context.get(field)]
        
        if not missing_fields:
            return 'pronta_para_confirmar'
        else:
            return 'aguardando_info'
    
    def get_reservation_summary(self, empresa_config: Dict[str, Any], 
                               reservation_context: Dict[str, Any]) -> str:
        """Gera resumo da reserva baseado nas regras da API"""
        rules = self.get_api_rules(empresa_config)
        api_type = rules['api_type']
        
        # Informações já coletadas
        info_coletada = []
        if reservation_context.get('waid'):
            info_coletada.append(f"WaId: {reservation_context['waid']}")
        if reservation_context.get('cliente_nome'):
            info_coletada.append(f"Nome: {reservation_context['cliente_nome']}")
        if reservation_context.get('quantidade_pessoas'):
            info_coletada.append(f"Pessoas: {reservation_context['quantidade_pessoas']}")
        if reservation_context.get('data_reserva'):
            info_coletada.append(f"Data: {reservation_context['data_reserva']}")
        if reservation_context.get('horario_reserva'):
            info_coletada.append(f"Horário: {reservation_context['horario_reserva']}")
        if reservation_context.get('observacoes'):
            info_coletada.append(f"Observações: {reservation_context['observacoes']}")
        
        # Status baseado na API
        status = self.get_reservation_status(empresa_config, reservation_context)
        
        if status == 'pronta_para_confirmar':
            if api_type == APIType.GOOGLE_SHEETS:
                return f"✅ Reserva completa para Google Sheets! Todas as informações coletadas: {', '.join(info_coletada)}"
            elif api_type in [APIType.GOOGLE_CALENDAR, APIType.TRINKS]:
                if not reservation_context.get('email'):
                    return f"📧 Reserva quase completa! Falta apenas o email para confirmar no {api_type.value}: {', '.join(info_coletada)}"
                else:
                    return f"✅ Reserva completa para {api_type.value}! Todas as informações coletadas: {', '.join(info_coletada)}"
            else:
                return f"✅ Reserva anotada! Todas as informações coletadas: {', '.join(info_coletada)}"
        
        elif status == 'aguardando_info':
            if info_coletada:
                return f"📝 Informações já coletadas: {', '.join(info_coletada)}"
            else:
                return "📝 Nenhuma informação coletada ainda"
        
        return "Status desconhecido"
    
    # NOVOS MÉTODOS PARA REGRAS EXPANDIDAS DO TRINKS
    
    def get_client_search_rules(self, empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """Retorna regras de busca de cliente para a API ativa"""
        rules = self.get_api_rules(empresa_config)
        if rules['api_type'] == APIType.TRINKS:
            return rules.get('client_search', {})
        return {}
    
    def get_service_detection_rules(self, empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """Retorna regras de detecção de serviço para a API ativa"""
        rules = self.get_api_rules(empresa_config)
        if rules['api_type'] == APIType.TRINKS:
            return rules.get('service_detection', {})
        return {}
    
    def get_professional_search_rules(self, empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """Retorna regras de busca de profissionais para a API ativa"""
        rules = self.get_api_rules(empresa_config)
        if rules['api_type'] == APIType.TRINKS:
            return rules.get('professional_search', {})
        return {}
    
    def get_availability_check_rules(self, empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """Retorna regras de verificação de disponibilidade para a API ativa"""
        rules = self.get_api_rules(empresa_config)
        if rules['api_type'] == APIType.TRINKS:
            return rules.get('availability_check', {})
        return {}
    
    def get_reservation_creation_rules(self, empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """Retorna regras de criação de reserva para a API ativa"""
        rules = self.get_api_rules(empresa_config)
        if rules['api_type'] == APIType.TRINKS:
            return rules.get('reservation_creation', {})
        return {}
    
    def get_reservation_management_rules(self, empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """Retorna regras de gerenciamento de reserva para a API ativa"""
        rules = self.get_api_rules(empresa_config)
        if rules['api_type'] == APIType.TRINKS:
            return rules.get('reservation_management', {})
        return {}
    
    def is_trinks_api(self, empresa_config: Dict[str, Any]) -> bool:
        """Verifica se a API ativa é Trinks"""
        return self.detect_active_api(empresa_config) == APIType.TRINKS

    # NOVOS MÉTODOS PARA FLUXOS EXPANDIDOS
    
    def get_availability_check_rules_expanded(self, empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """Retorna regras expandidas de verificação de disponibilidade para a API ativa"""
        rules = self.get_api_rules(empresa_config)
        if rules['api_type'] == APIType.TRINKS:
            return rules.get('fluxos_por_intencao', {}).get('verificar_disponibilidade', {})
        return {}
    
    def get_search_type_rules(self, empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """Retorna regras para determinar o tipo de busca (profissional vs procedimento)"""
        rules = self.get_api_rules(empresa_config)
        if rules['api_type'] == APIType.TRINKS:
            availability_rules = rules.get('fluxos_por_intencao', {}).get('verificar_disponibilidade', {})
            return availability_rules.get('tipos_busca', {})
        return {}
    
    def determine_search_type(self, extracted_data: Dict[str, Any]) -> str:
        """Determina o tipo de busca baseado nos dados extraídos"""
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
            logger.error(f"Erro ao determinar tipo de busca: {e}")
            return 'invalido'
    
    def validate_availability_request(self, extracted_data: Dict[str, Any], empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """Valida se a requisição de disponibilidade tem os campos necessários"""
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
            preference_check = self.should_ask_professional_preference(extracted_data, empresa_config)
            
            return {
                'valid': True,
                'search_type': search_type,
                'preference_check': preference_check,
                'message': 'Requisição válida'
            }
            
        except Exception as e:
            logger.error(f"Erro na validação: {e}")
            return {
                'valid': False,
                'error': f'Erro na validação: {str(e)}'
            }
    
    def get_availability_flow_steps(self, search_type: str, empresa_config: Dict[str, Any]) -> List[str]:
        """Retorna os passos do fluxo baseado no tipo de busca"""
        try:
            search_rules = self.get_search_type_rules(empresa_config)
            if search_type in search_rules:
                return search_rules[search_type].get('fluxo', [])
            return []
            
        except Exception as e:
            logger.error(f"Erro ao obter passos do fluxo: {e}")
            return []

    def get_preference_rules(self, empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """Retorna as regras de preferência de profissional para verificar_disponibilidade"""
        try:
            rules = self.get_api_rules(empresa_config)
            if not rules:
                return {}
            
            verificar_disponibilidade = rules.get('fluxos_por_intencao', {}).get('verificar_disponibilidade', {})
            return verificar_disponibilidade.get('logica_preferencia', {})
            
        except Exception as e:
            logger.error(f"Erro ao obter regras de preferência: {e}")
            return {}
    
    def should_ask_professional_preference(self, extracted_data: Dict[str, Any], empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """Determina se deve perguntar preferência de profissional baseado nos dados extraídos"""
        try:
            preference_rules = self.get_preference_rules(empresa_config)
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
            logger.error(f"Erro ao determinar se deve perguntar preferência: {e}")
            return {'should_ask': False, 'reason': f'Erro: {str(e)}'}

    # NOVOS MÉTODOS PARA VALIDAÇÃO DE SLOTS POR DURAÇÃO
    
    def get_slot_validation_rules(self, empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """Retorna as regras de validação de slots para a API ativa"""
        try:
            rules = self.get_api_rules(empresa_config)
            if rules['api_type'] == APIType.TRINKS:
                verificar_disponibilidade = rules.get('fluxos_por_intencao', {}).get('verificar_disponibilidade', {})
                return verificar_disponibilidade.get('validacao_slots', {})
            return {}
            
        except Exception as e:
            logger.error(f"Erro ao obter regras de validação de slots: {e}")
            return {}
    
    def calculate_required_slots(self, procedure_duration: int, slot_duration: int = 30) -> int:
        """Calcula quantos slots são necessários para um procedimento"""
        try:
            import math
            # Arredondar para cima para garantir tempo suficiente
            required_slots = math.ceil(procedure_duration / slot_duration)
            logger.info(f"Procedimento de {procedure_duration} min precisa de {required_slots} slots de {slot_duration} min")
            return required_slots
            
        except Exception as e:
            logger.error(f"Erro ao calcular slots necessários: {e}")
            return 1  # Fallback para 1 slot
    
    def validate_consecutive_slots(self, available_slots: List[Dict[str, Any]], 
                                 required_slots: int, 
                                 slot_duration: int = 30) -> List[Dict[str, Any]]:
        """Valida se há slots consecutivos suficientes para um procedimento"""
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
            
            logger.info(f"Encontrados {len(valid_start_times)} horários válidos com {required_slots} slots consecutivos")
            return valid_start_times
            
        except Exception as e:
            logger.error(f"Erro na validação de slots consecutivos: {e}")
            return []
    
    def _calculate_next_slot_time(self, start_time: str, slot_offset: int, slot_duration: int) -> str:
        """Calcula o horário do próximo slot baseado no offset"""
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
            logger.error(f"Erro ao calcular próximo slot: {e}")
            return start_time
    
    def filter_available_slots_by_duration(self, available_slots: List[Dict[str, Any]], 
                                         procedure_duration: int, 
                                         empresa_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Filtra slots disponíveis baseado na duração do procedimento"""
        try:
            # Obter regras de validação
            validation_rules = self.get_slot_validation_rules(empresa_config)
            slot_duration = validation_rules.get('duracao_slot_padrao', 30)
            
            # Calcular slots necessários
            required_slots = self.calculate_required_slots(procedure_duration, slot_duration)
            
            # Validar slots consecutivos
            valid_slots = self.validate_consecutive_slots(available_slots, required_slots, slot_duration)
            
            if not valid_slots:
                logger.warning(f"Nenhum horário válido encontrado para procedimento de {procedure_duration} min")
                return []
            
            logger.info(f"Filtrados {len(valid_slots)} horários válidos para procedimento de {procedure_duration} min")
            return valid_slots
            
        except Exception as e:
            logger.error(f"Erro ao filtrar slots por duração: {e}")
            return available_slots  # Fallback: retorna todos os slots
    
    def get_procedure_duration(self, procedure_name: str, empresa_config: Dict[str, Any], servico_info: Dict[str, Any] = None) -> int:
        """Obtém a duração de um procedimento específico"""
        try:
            # PRIORIDADE 1: Usar duração da API Trinks se disponível
            if servico_info and servico_info.get('duracaoEmMinutos'):
                duracao_api = servico_info.get('duracaoEmMinutos')
                logger.info(f"Procedimento '{procedure_name}' usando duração da API: {duracao_api} min")
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
                'teste': 30,  # Adicionado para serviços de teste
                'aaa': 30      # Adicionado para serviços AAA
            }
            
            # Buscar por palavras-chave
            for keyword, duration in duration_mapping.items():
                if keyword in procedure_lower:
                    logger.info(f"Procedimento '{procedure_name}' mapeado para {duration} min")
                    return duration
            
            # Duração padrão se não encontrar
            default_duration = 60
            logger.info(f"Procedimento '{procedure_name}' não encontrado, usando duração padrão: {default_duration} min")
            return default_duration
            
        except Exception as e:
            logger.error(f"Erro ao obter duração do procedimento: {e}")
            return 60  # Duração padrão de 60 min

# Instância global do motor de regras
api_rules_engine = APIRulesEngine() 