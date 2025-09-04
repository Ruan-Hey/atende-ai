from typing import Dict, Any, List
try:
    from langchain_openai import ChatOpenAI
except ImportError:
    from langchain.chat_models import ChatOpenAI
try:
    from langchain.memory import ConversationBufferWindowMemory
except ImportError:
    from langchain_community.memory import ConversationBufferWindowMemory
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import tool as lc_tool
import logging
import json
import requests
from datetime import datetime

# Importar TrinksRules diretamente
from rules.trinks_rules import TrinksRules

logger = logging.getLogger(__name__)

class SmartAgent:
    """Agente inteligente que usa LLM para identificar intenções e TrinksRules para executar fluxos"""
    
    def __init__(self, empresa_config: Dict[str, Any]):
        self.empresa_config = empresa_config
        
        # TrinksRules para operações específicas da API Trinks
        self.trinks_rules = TrinksRules()
        
        # LLM para identificação inteligente de intenções
        self.llm = ChatOpenAI(
            api_key=empresa_config.get('openai_key'),
            temperature=0.1,
            model="gpt-4o"
        )
        
        # Memory para contexto da conversa
        self.memory = ConversationBufferWindowMemory(
            k=20,
            return_messages=True
        )
        
        # Tools estruturadas
        self.tools = self._setup_tools()
        
        # Contexto da conversa atual
        self.current_conversation_state = None
        
        # Cache global de contextos por waid (WhatsApp ID)
        if not hasattr(SmartAgent, '_conversation_cache'):
            SmartAgent._conversation_cache = {}
    
    def _save_log_to_db(self, level: str, message: str, details: dict = None):
        """Salva log no banco de dados com empresa_id"""
        try:
            from main import save_log_to_db
            from database import SessionLocal
            
            empresa_id = self.empresa_config.get('empresa_id')
            if empresa_id:
                session = SessionLocal()
                try:
                    save_log_to_db(session, empresa_id, level, message, details)
                    
                    # 🔔 NOTIFICAÇÃO AUTOMÁTICA para erros críticos
                    if level == 'ERROR':
                        self._send_error_notification(session, message, details, empresa_id)
                        
                finally:
                    session.close()
        except Exception as e:
            # Fallback para logging normal se falhar
            logger.error(f"Erro ao salvar log no banco: {e}")
            logger.error(message)
    
    def _send_error_notification(self, session, message: str, details: dict, empresa_id: int):
        """Envia notificação push para erros do agente - VERSÃO SIMPLIFICADA"""
        try:
            from notifications.webpush_service import WebPushService
            from notifications.models import NotificationRule
            
            # Buscar regra de notificação para erros do agente
            regra = session.query(NotificationRule).filter(
                NotificationRule.tipo == 'agente_error',
                NotificationRule.ativo == True
            ).first()
            
            if regra:
                # 🆕 DADOS BÁSICOS - SEM CONSULTAS COMPLEXAS
                waid = details.get('waid')
                empresa_slug = self.empresa_config.get('slug', '')
                
                # 🆕 ROTA SIMPLES - SÓ EMPRESA + WAID
                rota_conversa = f"/conversation/{empresa_slug}/{waid}" if waid else ""
                
                # Notificação básica
                titulo = f"🚨 Erro no Agente - {self.empresa_config.get('nome', 'Empresa')}"
                mensagem = f"Erro: {message[:100]}..."
                
                # Dados contexto simplificados
                dados_contexto = {
                    'empresa_id': empresa_id,
                    'empresa_slug': empresa_slug,
                    'rota_conversa': rota_conversa,
                    'waid': waid,
                    'tipo_erro': 'agente_error'
                }
                
                # Executar regra de notificação
                webpush_service = WebPushService()
                webpush_service.execute_notification_rule(
                    session, regra, titulo, mensagem, dados_contexto
                )
                
                logger.info(f"🔔 Notificação de erro enviada para regra: {regra.nome}")
            else:
                logger.info("ℹ️ Nenhuma regra de notificação configurada para erros do agente")
                
        except Exception as e:
            logger.error(f"❌ Erro ao enviar notificação: {e}")
    
    async def _force_trinks_error(self):
        """Força erro no fluxo Trinks para teste"""
        try:
            # Simular erro no fluxo de agendamento sem service_id
            error_msg = "Erro no fluxo Trinks: service_id não fornecido para agendamento"
            error_details = {
                'tool': 'trinks_booking',
                'error_type': 'missing_service_id',
                'user_message': 'Quero agendar um horário para amanhã às 14h'
            }
            
            # Salvar erro no banco (vai disparar notificação)
            from main import save_log_to_db
            from database import SessionLocal
            
            session = SessionLocal()
            try:
                save_log_to_db(session, self.empresa_config.get('empresa_id'), 'ERROR', error_msg, error_details)
                logger.info("🔔 Erro Trinks forçado - notificação deveria ter sido enviada!")
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"❌ Erro ao forçar erro Trinks: {e}")
    
    async def _force_agent_error(self):
        """Força erro geral no agente para teste"""
        try:
            # Simular erro geral do agente
            error_msg = "Erro geral no agente: falha na execução da ferramenta"
            error_details = {
                'tool': 'general_execution',
                'error_type': 'tool_execution_failure',
                'context': 'test_forced_error'
            }
            
            # Salvar erro no banco (vai disparar notificação)
            from main import save_log_to_db
            from database import SessionLocal
            
            session = SessionLocal()
            try:
                save_log_to_db(session, self.empresa_config.get('empresa_id'), 'ERROR', error_msg, error_details)
                logger.info("🔔 Erro do agente forçado - notificação deveria ter sido enviada!")
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"❌ Erro ao forçar erro do agente: {e}")

    def _setup_tools(self) -> List:
        """Configura as tools disponíveis usando as TrinksRules para executar operações"""
        tools = []
        
        @lc_tool("get_business_knowledge")
        def get_business_knowledge(key: str) -> str:
            """Consulta informações específicas da empresa (horários, regras, promoções, etc.)"""
            try:
                knowledge = self.empresa_config.get('knowledge_json', {})
                items = knowledge.get('items', [])
                
                key_lower = key.lower().strip()
                for item in items:
                    if isinstance(item, dict):
                        item_key = item.get('key', '').lower().strip()
                        if item_key == key_lower:
                            return item.get('content', 'Informação não encontrada')
                
                return f"Informação sobre '{key}' não encontrada. Tente: horários, regras, promoções, endereço, telefone."
            except Exception as e:
                error_msg = f"Erro ao buscar conhecimento: {e}"
                logger.error(error_msg)
                self._save_log_to_db('ERROR', error_msg, {'tool': 'get_business_knowledge', 'key': key})
                return "Erro ao buscar informações da empresa"
        
        @lc_tool("get_api_rules")
        def get_api_rules() -> str:
            """Retorna as regras da API Trinks para a empresa"""
            try:
                # Usar TrinksRules diretamente
                rules = self.trinks_rules.get_api_rules()
                return f"Regras da API Trinks: Email obrigatório: {rules.get('email_required', False)}, WaId obrigatório: {rules.get('waid_required', True)}"
            except Exception as e:
                error_msg = f"Erro ao buscar regras da API: {e}"
                logger.error(error_msg)
                self._save_log_to_db('ERROR', error_msg, {'tool': 'get_api_rules'})
                return "Erro ao buscar regras da API"
        
        @lc_tool("get_available_flows")
        def get_available_flows() -> str:
            """Retorna os fluxos disponíveis para a API Trinks"""
            try:
                # Usar TrinksRules diretamente
                rules = self.trinks_rules.get_api_rules()
                flows = rules.get('fluxos_por_intencao', {})
                
                if flows:
                    flow_list = []
                    for intent, flow in flows.items():
                        flow_list.append(f"- {intent}: {flow['descricao']}")
                    
                    return f"Fluxos disponíveis para Trinks:\n" + "\n".join(flow_list)
                else:
                    return f"Nenhum fluxo configurado para Trinks"
            except Exception as e:
                error_msg = f"Erro ao buscar fluxos: {e}"
                logger.error(error_msg)
                self._save_log_to_db('ERROR', error_msg, {'tool': 'get_available_flows'})
                return "Erro ao buscar fluxos disponíveis"
        
        @lc_tool("search_client")
        def search_client(identifier: str, identifier_type: str = "cpf") -> str:
            """Busca cliente por CPF, telefone ou nome usando as rules da API"""
            try:
                # Obter regras da API Trinks
                rules_instance = self.trinks_rules
                if not rules_instance:
                    return "API não configurada para esta empresa"
                
                # Executar busca usando as rules (que chamam as tools)
                if hasattr(rules_instance, 'execute_client_search'):
                    result = rules_instance.execute_client_search(identifier, identifier_type)
                    
                    if result.get('success'):
                        return result.get('message', 'Cliente encontrado')
                    else:
                        return f"Erro: {result.get('error', 'Busca falhou')}"
                else:
                    return "API não suporta busca de clientes"
                    
            except Exception as e:
                logger.error(f"Erro ao buscar cliente: {e}")
                return f"Erro ao buscar cliente: {str(e)}"
        
        @lc_tool("check_availability")
        def check_availability(professional: str = None, service: str = None, date: str = None) -> str:
            """Verifica disponibilidade usando as rules da API"""
            try:
                # Obter regras da API Trinks
                rules_instance = self.trinks_rules
                if not rules_instance:
                    return "API não configurada para esta empresa"
                
                # Executar verificação usando as rules (que chamam as tools)
                if hasattr(rules_instance, 'execute_availability_check'):
                    result = rules_instance.execute_availability_check(professional, service, date)
                    
                    if result.get('success'):
                        return result.get('message', 'Verificação concluída')
                    else:
                        return f"Erro: {result.get('error', 'Verificação falhou')}"
                else:
                    return "API não suporta verificação de disponibilidade"
                    
            except Exception as e:
                logger.error(f"Erro ao verificar disponibilidade: {e}")
                return f"Erro ao verificar disponibilidade: {str(e)}"
        
        @lc_tool("book_appointment")
        def book_appointment(professional: str, service: str, date: str, time: str, client_name: str) -> str:
            """Agenda uma consulta usando as rules da API"""
            try:
                # Obter regras da API Trinks
                rules_instance = self.trinks_rules
                if not rules_instance:
                    return "API não configurada para esta empresa"
                
                # Executar agendamento usando as rules (que chamam as tools)
                if hasattr(rules_instance, 'execute_reservation_creation'):
                    result = rules_instance.execute_reservation_creation(professional, service, date, time, client_name)
                    
                    if result.get('success'):
                        return result.get('message', 'Agendamento realizado')
                    else:
                        return f"Erro: {result.get('error', 'Agendamento falhou')}"
                else:
                    return "API não suporta agendamento"
                    
            except Exception as e:
                logger.error(f"Erro ao agendar consulta: {e}")
                return f"Erro ao agendar consulta: {str(e)}"
        
        @lc_tool("execute_flow")
        def execute_flow(intent: str, **kwargs) -> str:
            """Executa um fluxo específico baseado na intenção usando as rules"""
            try:
                # Obter regras da API Trinks
                rules = self.trinks_rules.get_api_rules()
                flows = rules.get('fluxos_por_intencao', {})
                
                if intent not in flows:
                    return f"Intenção '{intent}' não suportada. Fluxos disponíveis: {list(flows.keys())}"
                
                flow = flows[intent]
                required_fields = flow.get('campos_obrigatorios', [])
                
                # Verificar campos obrigatórios
                missing_fields = []
                for field in required_fields:
                    if field not in kwargs:
                        missing_fields.append(field)
                
                if missing_fields:
                    return f"Campos obrigatórios faltando para '{intent}': {missing_fields}"
                
                # Executar fluxo usando as rules apropriadas
                rules_instance = self.trinks_rules
                if rules_instance:
                    # Mapear intenção para método da rule
                    if intent == "verificar_disponibilidade":
                        if hasattr(rules_instance, 'execute_availability_check'):
                            result = rules_instance.execute_availability_check(**kwargs)
                            return result.get('message', 'Fluxo executado')
                    elif intent == "agendar_consulta":
                        if hasattr(rules_instance, 'execute_reservation_creation'):
                            result = rules_instance.execute_reservation_creation(**kwargs)
                            return result.get('message', 'Fluxo executado')
                
                # Fallback: simular execução do fluxo
                steps = flow.get('passos', [])
                result = f"Executando fluxo '{intent}':\n"
                
                for step in steps:
                    result += f"✅ {step}\n"
                
                result += f"\nDados recebidos: {kwargs}"
                return result
                
            except Exception as e:
                logger.error(f"Erro ao executar fluxo: {e}")
                return f"Erro ao executar fluxo '{intent}': {str(e)}"
        
        tools = [
            get_business_knowledge,
            get_api_rules,
            get_available_flows,
            search_client,
            check_availability,
            book_appointment,
            execute_flow
        ]
        
        return tools
    
    def process_message(self, message: str, waid: str, context: Dict[str, Any] = None) -> str:
        """Processa uma mensagem recebida e retorna a resposta apropriada"""
        try:
            logger.info(f"Processando mensagem para waid {waid}")
            
            # ✅ CARREGAR contexto do cache por waid
            self._load_conversation_context(waid)
            
            # ✅ ARQUITETURA: Preparar contexto com histórico para as Rules
            if context is None:
                context = {}
            
            # ✅ OBTER HISTÓRICO da memória LangChain (últimas 10 mensagens)
            conversation_history = []
            if self.memory.chat_memory.messages:
                conversation_history = self.memory.chat_memory.messages[-10:]
                logger.info(f"📚 Histórico da conversa: {len(conversation_history)} mensagens")
            
            # ✅ ADICIONAR ao contexto para as Rules
            context['conversation_history'] = conversation_history
            context['waid'] = waid
            
            # ✅ NOVO: PASSAR CACHE TEMPORÁRIO como contexto
            if waid in SmartAgent._conversation_cache:
                cached_data = SmartAgent._conversation_cache[waid]
                if 'extracted_data' in cached_data:
                    extracted_data = cached_data['extracted_data']
                    
                    # ✅ PASSAR cache temporário como contexto
                    if 'temp_professional_cache' in extracted_data:
                        context['temp_professional_cache'] = extracted_data['temp_professional_cache']
                        context['temp_cache_expiry'] = extracted_data['temp_cache_expiry']
                        logger.info(f"🔄 Cache temporário passado para TrinksRules: {len(extracted_data['temp_professional_cache'])} profissionais")
            
            # ✅ ARQUITETURA UNIFICADA: Detectar intenção e extrair dados em uma única chamada LLM
            parsed_result = self.trinks_rules.detect_intent_and_extract(message, context, self.empresa_config)
            intent = parsed_result.get("intent", "general")
            extracted_data = parsed_result.get("extracted", {})
            cache_instructions = parsed_result.get("cache_instructions", {})
            logger.info(f"Resultado do parsing unificado via Rules - Intent: {intent}, Dados: {extracted_data}")
            logger.info(f"📋 Cache instructions recebidas: {cache_instructions}")

            # ✅ EXECUTAR CACHE_INSTRUCTIONS ANTES de salvar no contexto
            if cache_instructions:
                logger.info(f"🧹 Executando cache_instructions antes de salvar no cache...")
                self._execute_cache_instructions(cache_instructions, waid)
            else:
                logger.info(f"📋 Nenhuma cache_instruction para executar")

            # ✅ EXECUTAR MESCLAGEM INTELIGENTE para preservar contexto
            logger.info(f"🔄 Executando mesclagem inteligente para preservar contexto...")
            merged_data = self._merge_extracted_with_cache(extracted_data, waid)
            logger.info(f"✅ Dados mesclados com contexto: {merged_data}")

            # ✅ Disponibilizar no contexto para próximos passos/execução
            context['extracted_data'] = merged_data
            context['intent'] = intent

            # ✅ ARQUITETURA: 3) LLM de PRÓXIMOS PASSOS (Rules orquestra, Tools operam)
            try:
                next_steps = self.trinks_rules.decide_next_steps(intent, context, self.empresa_config)
            except Exception as _e:
                logger.warning(f"Falha ao decidir próximos passos: {_e}")
                next_steps = {"action": "ask_user", "agent_response": "Poderia detalhar, por favor?"}

            # ✅ NOVA ARQUITETURA: Extrair regras de negócio dos próximos passos
            business_rules = next_steps.get('business_rules', [])
            
            logger.info(f"📋 Regras de negócio recebidas: {business_rules}")
            
            # ✅ Disponibilizar regras de negócio no contexto para uso futuro
            context['business_rules'] = business_rules
            
            # ✅ DEBUG: Log da action recebida
            action = next_steps.get("action")
            logger.info(f"🎯 Action recebida: {action}")
            
            # ✅ DEBUG: Verificar se precisa executar action
            if action:
                logger.info(f"🔧 Executando action: {action}")
                
                # ✅ NOVO: Verificar se action é array ou string
                if isinstance(action, list):
                    logger.info(f"🔄 Action é array com {len(action)} passos: {action}")
                    
                    # ✅ NOVO: Verificar se é array com apenas "ask_user"
                    if len(action) == 1 and action[0] == "ask_user":
                        logger.info("👤 Array contém apenas ask_user - tratando como caso especial")
                        # ✅ ask_user vai DIRETO para o prompt da empresa
                        result = self._handle_ask_user_direct(business_rules, merged_data, next_steps, context, intent)
                    else:
                        logger.info("🔧 Array contém tools - executando múltiplas actions")
                        result = self._execute_multiple_actions(action, merged_data, next_steps, context)
                else:
                    logger.info(f"🔧 Action é string única: {action}")
                    
                    # ✅ NOVO: Verificar se string é "ask_user"
                    if action == "ask_user":
                        logger.info("👤 Action é ask_user - tratando como caso especial")
                        # ✅ ask_user vai DIRETO para o prompt da empresa
                        result = self._handle_ask_user_direct(business_rules, merged_data, next_steps, context, intent)
                    else:
                        logger.info("🔧 Action é tool - executando action única")
                        result = self._execute_single_action(action, merged_data, context)
                
                # ✅ NOVO: Analisar resultados e gerar resposta formatada
                # ✅ Verificar se é ask_user para evitar análise desnecessária
                if isinstance(action, list) and len(action) == 1 and action[0] == "ask_user":
                    logger.info("👤 ask_user detectado - pulando análise desnecessária")
                    # ✅ ask_user já retorna resposta formatada pronta (string)
                    # result já é a string formatada, não precisa de .get()
                elif isinstance(action, str) and action == "ask_user":
                    logger.info("👤 ask_user detectado - pulando análise desnecessária")
                    # ✅ ask_user já retorna resposta formatada pronta (string)
                    # result já é a string formatada, não precisa de .get()
                elif isinstance(result, dict) and result.get('status') != 'erro':
                    # ✅ Verificar se é resultado de múltiplas actions
                    if result.get('status') == 'actions_executadas':
                        logger.info("🔧 Múltiplas actions executadas - analisando resultados completos...")
                        
                        # ✅ Usar TODOS os resultados das actions
                        analysis_data = {
                            'results': result.get('results', {}),
                            'extracted_data': merged_data,
                            'business_rules': business_rules,
                            'context': context
                        }
                        
                        # ✅ Chamar direto a LLM principal (sem análise intermediária)
                        logger.info("✅ Chamando direto a LLM principal com prompt da empresa...")
                        formatted_response = self._analyze_with_company_llm(
                            f"Processar intent: {intent}",
                            analysis_data
                        )
                        logger.info(f"✅ Resposta formatada pela empresa: {formatted_response}")
                        result = formatted_response
                    else:
                        logger.info("🔧 Action única executada - analisando resultado...")
                        
                        # ✅ Para action única, chamar direto a LLM principal
                        analysis_data = {
                            'results': {'single_action': result},
                            'extracted_data': merged_data,
                            'business_rules': business_rules,
                            'context': context
                        }
                        
                        # ✅ Chamar direto a LLM principal (sem análise intermediária)
                        logger.info("✅ Chamando direto a LLM principal com prompt da empresa...")
                        formatted_response = self._analyze_with_company_llm(
                            f"Processar intent: {intent}",
                            analysis_data
                        )
                        logger.info(f"✅ Resposta formatada pela empresa: {formatted_response}")
                        result = formatted_response
                else:
                    # ✅ FALLBACK: Se não houver regras de negócio, usar resultado bruto
                    logger.info("🔄 Usando resultado bruto (sem regras de negócio)")
                    if isinstance(result, dict):
                        result = f"✅ Actions executadas com sucesso. Status: {result.get('status')}"
                    else:
                        result = str(result)
            else:
                # Para manter simplicidade: usar a mensagem pronta da LLM de próximos passos
                result = next_steps.get("agent_response") or "Certo, me diga por favor o próximo detalhe (data/horário/CPF)."
            
            # ✅ ADICIONAR mensagem atual à memória LangChain
            self.memory.chat_memory.add_user_message(message)
            
            # ✅ ADICIONAR resposta do bot à memória LangChain
            self.memory.chat_memory.add_ai_message(result)
            
            # ✅ SALVAR contexto no cache por waid (INCLUINDO MENSAGENS + DADOS EXTRAÍDOS)
            try:
                # Preferir enriched_data consolidado com ids quando disponível
                enriched = getattr(self, '_last_enriched_extracted_data', None)
                data_to_cache = enriched if isinstance(enriched, dict) and enriched else extracted_data
            except Exception:
                data_to_cache = extracted_data
            self._save_conversation_context(waid, data_to_cache)
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}")
            return self._generate_response_with_company_prompt(
                "erro_geral",
                {'error': f"Erro ao processar mensagem: {str(e)}", 'context': context},
                context
            )
    
    
    

    
    # ✅ MÉTODO REMOVIDO: _execute_intent_flow nunca foi usado
    # Todo o fluxo principal usa process_message() que funciona perfeitamente
    
    def _generate_general_response(self, message: str, context: Dict[str, Any] = None) -> str:
        """Gera resposta para mensagens gerais usando prompt da empresa"""
        try:
            # Usar prompt da empresa para resposta geral
            return self._generate_response_with_company_prompt(
                "resposta_geral",
                {'message': message, 'context': context},
                context
            )
            
        except Exception as e:
            logger.error(f"Erro ao gerar resposta geral: {e}")
            return self._generate_response_with_company_prompt(
                "erro_geral",
                {'error': f"Erro ao gerar resposta geral: {str(e)}", 'context': context},
                context
            )
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Retorna um resumo do estado atual da conversa"""
        return {
            "status": "active",
            "memory_size": len(self.memory.chat_memory.messages),
            "tools_available": len(self.tools),
            "empresa": self.empresa_config.get('nome', 'N/A')
        }
    
    def _load_conversation_context(self, waid: str) -> None:
        """Carrega contexto de conversa do cache global"""
        if waid in SmartAgent._conversation_cache:
            cached_data = SmartAgent._conversation_cache[waid]
            logger.info(f"Carregando contexto para waid {waid}: {len(cached_data.get('messages', []))} mensagens")
            
            # ✅ CORREÇÃO: Acessar a estrutura correta do cache
            if isinstance(cached_data, dict) and 'messages' in cached_data:
                cached_messages = cached_data['messages']
                # Log resumido do extracted_data salvo no cache
                try:
                    ed = cached_data.get('extracted_data', {}) or {}
                    ed_summary = {
                        'profissional': ed.get('profissional'),
                        'profissional_id': ed.get('profissional_id'),
                        'procedimento': ed.get('procedimento'),
                        'servico_id': ed.get('servico_id'),
                        'data': ed.get('data'),
                        'horario': ed.get('horario')
                    }
                    logger.info(f"🗄️ extracted_data do cache (load) para {waid}: {ed_summary}")
                except Exception as _e:
                    logger.warning(f"Falha ao logar extracted_data do cache: {_e}")
                # Restaurar mensagens na memória
                for msg in cached_messages:
                    if msg.get('type') == 'human':
                        self.memory.chat_memory.add_user_message(msg['content'])
                    elif msg.get('type') == 'ai':
                        self.memory.chat_memory.add_ai_message(msg['content'])
            else:
                # ✅ COMPATIBILIDADE: Fallback para formato antigo
                logger.warning(f"Formato de cache inesperado para waid {waid}, tentando fallback")
                if isinstance(cached_data, list):
                    # Formato antigo: lista direta de mensagens
                    for msg in cached_data:
                        if msg.get('type') == 'human':
                            self.memory.chat_memory.add_user_message(msg['content'])
                        elif msg.get('type') == 'ai':
                            self.memory.chat_memory.add_ai_message(msg['content'])
                else:
                    logger.error(f"Formato de cache inválido para waid {waid}: {type(cached_data)}")
        else:
            logger.info(f"Primeira mensagem para waid {waid}, criando novo contexto")
    
    def _save_conversation_context(self, waid: str, extracted_data: Dict[str, Any] = None) -> None:
        """Salva contexto de conversa no cache global"""
        messages = []
        for msg in self.memory.chat_memory.messages:
            if hasattr(msg, 'type') and msg.type == 'human':
                messages.append({'type': 'human', 'content': msg.content})
            elif hasattr(msg, 'type') and msg.type == 'ai':
                messages.append({'type': 'ai', 'content': msg.content})
            else:
                # Fallback para diferentes tipos de mensagem
                messages.append({'type': 'unknown', 'content': str(msg.content)})
        
        # ✅ Salvar mensagens + dados extraídos
        cache_data = {
            'messages': messages,
            'extracted_data': extracted_data or {}
        }
        
        SmartAgent._conversation_cache[waid] = cache_data
        logger.info(f"🗄️ Contexto + dados extraídos salvos para waid {waid}: {len(messages)} mensagens + {len(extracted_data) if extracted_data else 0} campos")
        try:
            ed = extracted_data or {}
            ed_summary = {
                'profissional': ed.get('profissional'),
                'profissional_id': ed.get('profissional_id'),
                'procedimento': ed.get('procedimento'),
                'servico_id': ed.get('servico_id'),
                'data': ed.get('data'),
                'horario': ed.get('horario')
            }
            logger.info(f"🗄️ extracted_data salvo (save) para {waid}: {ed_summary}")
        except Exception as _e:
            logger.warning(f"Falha ao logar extracted_data salvo: {_e}")
    
    def _update_cache_from_instructions(self, cache_instructions: Dict[str, Any], extracted_data: Dict[str, Any]) -> None:
        """✅ NOVA FUNÇÃO: Atualiza cache seguindo instruções das Rules"""
        try:
            if "update_fields" in cache_instructions:
                update_fields = cache_instructions["update_fields"]
                logger.info(f"📋 Atualizando cache com instruções: {update_fields}")
                
                # ✅ GARANTIR que _last_enriched_extracted_data seja inicializado
                if not hasattr(self, '_last_enriched_extracted_data') or self._last_enriched_extracted_data is None:
                    self._last_enriched_extracted_data = extracted_data.copy()
                    logger.info(f"✅ _last_enriched_extracted_data inicializado com: {extracted_data}")
                
                for field, value in update_fields.items():
                    extracted_data[field] = value
                    logger.info(f"✅ Campo '{field}' atualizado para '{value}' no cache")
                
                # Atualizar também o atributo interno para manter sincronizado
                for field, value in update_fields.items():
                    self._last_enriched_extracted_data[field] = value
                    logger.info(f"✅ Campo '{field}' atualizado para '{value}' no enriched_data")
                        
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar cache com instruções: {e}")
    
    def _execute_cache_instructions(self, cache_instructions: Dict[str, Any], waid: str) -> None:
        """✅ NOVA FUNÇÃO: Executa instruções de cache (clear_fields) antes de salvar"""
        try:
            if not cache_instructions or not isinstance(cache_instructions, dict):
                logger.info("📋 Nenhuma instrução de cache para executar")
                return
            
            clear_fields = cache_instructions.get("clear_fields", [])
            if not clear_fields:
                logger.info("📋 Nenhum campo para limpar do cache")
                return
            
            logger.info(f"🧹 Executando cache_instructions: clear_fields = {clear_fields}")
            
            # ✅ Verificar se existe cache para este waid
            if waid not in SmartAgent._conversation_cache:
                logger.info(f"📋 Cache não encontrado para waid {waid}, nada para limpar")
                return
            
            cached_data = SmartAgent._conversation_cache[waid]
            if not isinstance(cached_data, dict) or 'extracted_data' not in cached_data:
                logger.info(f"📋 Estrutura de cache inválida para waid {waid}")
                return
            
            extracted_data = cached_data['extracted_data']
            if not isinstance(extracted_data, dict):
                logger.info(f"📋 extracted_data inválido para waid {waid}")
                return
            
            # ✅ Limpar campos especificados
            cleared_count = 0
            for field in clear_fields:
                if field in extracted_data:
                    old_value = extracted_data[field]
                    extracted_data[field] = None
                    cleared_count += 1
                    logger.info(f"🧹 Campo '{field}' limpo do cache (era: {old_value})")
                else:
                    logger.info(f"📋 Campo '{field}' não encontrado no cache, nada para limpar")
            
            # ✅ Atualizar cache global
            SmartAgent._conversation_cache[waid]['extracted_data'] = extracted_data
            
            # ✅ Atualizar também o atributo interno se existir
            if hasattr(self, '_last_enriched_extracted_data') and self._last_enriched_extracted_data:
                for field in clear_fields:
                    if field in self._last_enriched_extracted_data:
                        old_value = self._last_enriched_extracted_data[field]
                        self._last_enriched_extracted_data[field] = None
                        logger.info(f"🧹 Campo '{field}' limpo do _last_enriched_extracted_data (era: {old_value})")
            
            logger.info(f"✅ Cache limpo com sucesso: {cleared_count} campos limpos")
            
        except Exception as e:
            logger.error(f"❌ Erro ao executar cache_instructions: {e}")
            logger.error(f"cache_instructions: {cache_instructions}, waid: {waid}")
    
    def _merge_extracted_with_cache(self, extracted_data: Dict[str, Any], waid: str) -> Dict[str, Any]:
        """✅ NOVA FUNÇÃO: Mescla dados extraídos com cache atual de forma inteligente"""
        try:
            logger.info(f"🔄 Executando mesclagem inteligente para waid {waid}")
            
            # ✅ Verificar se existe cache para este waid
            if waid not in SmartAgent._conversation_cache:
                logger.info(f"📋 Cache não encontrado para waid {waid}, retornando dados extraídos")
                return extracted_data
            
            cached_data = SmartAgent._conversation_cache[waid]
            if not isinstance(cached_data, dict) or 'extracted_data' not in cached_data:
                logger.info(f"📋 Estrutura de cache inválida para waid {waid}, retornando dados extraídos")
                return extracted_data
            
            current_cache = cached_data['extracted_data']
            if not isinstance(current_cache, dict):
                logger.info(f"📋 extracted_data inválido para waid {waid}, retornando dados extraídos")
                return extracted_data
            
            # ✅ MESCLAGEM INTELIGENTE: Atualiza apenas o que mudou, mantém o resto
            merged_cache = current_cache.copy()
            updated_count = 0
            
            for field, new_value in extracted_data.items():
                if new_value is not None and new_value != "" and new_value != "null":
                    old_value = merged_cache.get(field)
                    if old_value != new_value:
                        merged_cache[field] = new_value
                        updated_count += 1
                        logger.info(f"🔄 Campo '{field}' atualizado: '{old_value}' → '{new_value}'")
                    else:
                        logger.info(f"📋 Campo '{field}' mantido: '{old_value}' (sem mudança)")
                else:
                    logger.info(f"📋 Campo '{field}' ignorado: valor inválido")
            
            # ✅ Atualizar cache global
            SmartAgent._conversation_cache[waid]['extracted_data'] = merged_cache
            
            # ✅ Atualizar também o atributo interno se existir
            if hasattr(self, '_last_enriched_extracted_data') and self._last_enriched_extracted_data:
                for field, value in extracted_data.items():
                    if value is not None and value != "" and value != "null":
                        self._last_enriched_extracted_data[field] = value
            
            # ✅ REGRA DE EXPIRAÇÃO AUTOMÁTICA: Cache temporário expira após 2 mensagens
            if 'temp_cache_expiry' in merged_cache:
                # ✅ PROTEÇÃO: Verificar se o valor é numérico antes de fazer operação matemática
                expiry_value = merged_cache['temp_cache_expiry']
                if isinstance(expiry_value, (int, float)):
                    merged_cache['temp_cache_expiry'] = expiry_value - 1
                    if merged_cache['temp_cache_expiry'] <= 0:
                        # Cache expirou → limpar automaticamente
                        if 'temp_professional_cache' in merged_cache:
                            del merged_cache['temp_professional_cache']
                        del merged_cache['temp_cache_expiry']
                        logger.info("🧹 Cache temporário expirado e limpo automaticamente")
                    else:
                        logger.info(f"⏰ Cache temporário expira em {merged_cache['temp_cache_expiry']} mensagens")
                else:
                    # Se não for numérico, converter para número ou usar valor padrão
                    logger.warning(f"⚠️ temp_cache_expiry não é numérico: {expiry_value} (tipo: {type(expiry_value)})")
                    merged_cache['temp_cache_expiry'] = 1  # Reset para 1 mensagem
                    logger.info("⏰ Cache temporário resetado para 1 mensagem")
            
            logger.info(f"✅ Mesclagem inteligente concluída: {updated_count} campos atualizados")
            logger.info(f"🎯 Cache final: {merged_cache}")
            
            return merged_cache
            
        except Exception as e:
            logger.error(f"❌ Erro ao executar mesclagem inteligente: {e}")
            logger.error(f"extracted_data: {extracted_data}, waid: {waid}")
            # Fallback: retornar dados extraídos sem mesclar
            return extracted_data
    
    def _execute_availability_check(self, extracted_data: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Executa verificação de disponibilidade com suporte a busca por profissional OU procedimento"""
        try:
            # Obter regras expandidas da API
            api_rules = self.trinks_rules.get_availability_check_rules_expanded()
            if not api_rules:
                return "Erro: Regras de disponibilidade não configuradas"
            
            # Validar requisição
            validation = self.trinks_rules.validate_availability_request(extracted_data)
            if not validation.get('valid'):
                # NÃO retornar erro direto - usar prompt principal do admin
                logger.info(f"Validação falhou: {validation.get('error')} - usando prompt principal do admin")
                return self._generate_response_with_company_prompt(
                    "verificar_disponibilidade",
                    {
                        'error': validation.get('error'),
                        'extracted_data': extracted_data,
                        'missing_fields': validation.get('missing_fields', []),
                        'context': context
                    },
                    context
                )
            
            search_type = validation.get('search_type')
            logger.info(f"Executando fluxo verificar_disponibilidade com tipo: {search_type}")
            
            # ⚙️ Previous data do cache (ids já resolvidos, etc.)
            previous_data = {}
            try:
                waid = context.get('waid') if context else None
                if waid and hasattr(SmartAgent, '_conversation_cache') and waid in SmartAgent._conversation_cache:
                    cached = SmartAgent._conversation_cache.get(waid, {})
                    if isinstance(cached, dict):
                        previous_data = cached.get('extracted_data', {}) or {}
            except Exception as _e:
                logger.warning(f"Não foi possível obter previous_data do cache: {_e}")

            # Executar fluxo expandido único
            return self._execute_expanded_availability_check(extracted_data, context, api_rules, previous_data)
                
        except Exception as e:
            logger.error(f"Erro ao executar verificação de disponibilidade: {e}")
            # NÃO retornar erro direto - usar prompt principal do admin
            return self._generate_response_with_company_prompt(
                "verificar_disponibilidade",
                {
                    'error': f"Erro ao verificar disponibilidade: {str(e)}",
                    'context': context
                },
                context
            )
    
    def _execute_expanded_availability_check(self, data: Dict[str, Any], context: Dict[str, Any], api_rules: Dict[str, Any], previous_data: Dict[str, Any] = None) -> str:
        """Executa verificação de disponibilidade usando arquitetura Rules → Tools → Integrations"""
        try:
            logger.info("Executando fluxo expandido de verificação de disponibilidade")
            
            # 1. OBTER REGRAS E PASSOS
            rules_instance = self.trinks_rules
            if not rules_instance:
                return "Erro: Não foi possível obter as regras da API"
            
            # Obter passos configurados via Rules (arquitetura correta)
            passos = rules_instance.get_availability_flow_steps(data, self.empresa_config, previous_data or {})
            logger.info(f"📋 Fluxo configurado via Rules: {passos}")
            
            # 2. EXECUTAR CADA PASSO VIA RULES (que chamam Tools)
            resultado = {}
            
            for i, passo in enumerate(passos, 1):
                logger.info(f"PASSO {i}: Executando {passo} via Rules...")
                
                try:
                    if passo == "extrair_dados":
                        # Dados já extraídos pelo Smart Agent
                        resultado[passo] = {"status": "concluido", "dados": data}
                        logger.info(f"PASSO {i}: {passo} ✓")
                        
                    elif passo == "validar_campos":
                        # Validar usando regras
                        validation = rules_instance.validate_availability_request(data)
                        resultado[passo] = validation
                        if not validation.get('valid'):
                            return self._generate_response_with_company_prompt(
                                "verificar_disponibilidade",
                                {'error': validation.get('error'), 'context': context},
                                context
                            )
                        logger.info(f"PASSO {i}: {passo} ✓")
                        
                    elif passo == "buscar_profissional":
                        # Executar via Rules (que chama Tools)
                        step_result = rules_instance.execute_step(passo, data, self.empresa_config)
                        resultado[passo] = step_result
                        
                        if step_result.get('status') == 'erro':
                            return self._generate_response_with_company_prompt(
                                "verificar_disponibilidade",
                                {'error': step_result.get('error'), 'context': context},
                                context
                            )
                        logger.info(f"PASSO {i}: {passo} ✓ - {step_result.get('status')}")
                        
                    elif passo == "fazer_match_profissional":
                        # Match já feito no passo anterior
                        resultado[passo] = {"status": "concluido"}
                        logger.info(f"PASSO {i}: {passo} ✓")
                        
                    elif passo == "buscar_servico":
                        # Executar via Rules (que chama Tools)
                        step_result = rules_instance.execute_step(passo, data, self.empresa_config)
                        resultado[passo] = step_result
                        
                        if step_result.get('status') == 'erro':
                            return self._generate_response_with_company_prompt(
                                "verificar_disponibilidade",
                                {'error': step_result.get('error'), 'context': context},
                                context
                            )
                        
                        # Log mais detalhado para buscar_servico
                        if step_result.get('id'):
                            logger.info(f"PASSO {i}: {passo} ✓ - Serviço encontrado: {step_result.get('nome')} (ID: {step_result.get('id')})")
                        else:
                            logger.info(f"PASSO {i}: {passo} ✓ - {step_result.get('status', 'Resultado')}")
                        
                    elif passo == "fazer_match_servico":
                        # Match já feito no passo anterior
                        resultado[passo] = {"status": "concluido"}
                        logger.info(f"PASSO {i}: {passo} ✓")
                        
                    elif passo == "verificar_disponibilidade":
                        # Preparar dados para verificação
                        servico_info = resultado.get('buscar_servico', {})
                        profissional_info = resultado.get('buscar_profissional', {})
                        
                        # Extrair IDs
                        servico_id = None
                        profissional_id = None
                        
                        if servico_info.get('id'):
                            servico_id = servico_info['id']
                        elif servico_info.get('result', {}).get('id'):
                            servico_id = servico_info['result']['id']
                        
                        if profissional_info.get('id'):
                            profissional_id = profissional_info['id']
                        elif profissional_info.get('result', {}).get('id'):
                            profissional_id = profissional_info['result']['id']

                        # Fallback: usar IDs do previous_data se não foram obtidos neste fluxo
                        if not servico_id and isinstance(previous_data, dict):
                            servico_id = previous_data.get('servico_id') or servico_id
                        if not profissional_id and isinstance(previous_data, dict):
                            profissional_id = previous_data.get('profissional_id') or profissional_id
                        logger.info(f"🗄️ IDs usados para verificação: servico_id={servico_id} | profissional_id={profissional_id}")
                        
                        # Dados para execução
                        execution_data = {
                            'servico_id': servico_id,
                            'data': data.get('data'),
                            'profissional_id': profissional_id
                        }
                        logger.info(f"🗄️ execution_data enviado para verificar_disponibilidade: {execution_data}")
                        # Preparar enriched_data parcial com ids resolvidos até aqui
                        try:
                            enriched_data = dict(data)
                            if servico_id:
                                enriched_data['servico_id'] = servico_id
                            if profissional_id:
                                enriched_data['profissional_id'] = profissional_id
                            # Manter data informada
                            if data.get('data'):
                                enriched_data['data'] = data.get('data')
                            # Disponibilizar para quem salvar mais tarde
                            self._last_enriched_extracted_data = enriched_data
                        except Exception as _e:
                            logger.warning(f"Falha ao montar enriched_data parcial: {_e}")

                        # Executar via Rules (que chama Tools)
                        step_result = rules_instance.execute_step(passo, execution_data, self.empresa_config)
                        resultado[passo] = step_result
                        
                        if step_result.get('status') == 'erro':
                            return self._generate_response_with_company_prompt(
                                "verificar_disponibilidade",
                                {'error': step_result.get('error'), 'context': context},
                                context
                            )
                        logger.info(f"PASSO {i}: {passo} ✓ - Disponibilidade verificada")
                        
                    elif passo == "validar_slots":
                        # Preparar dados para validação
                        disponibilidade = resultado.get('verificar_disponibilidade', {})
                        servico_info = resultado.get('buscar_servico', {})
                        
                        # Dados para execução
                        execution_data = {
                            'disponibilidade': disponibilidade,
                            'servico_info': servico_info
                        }
                        
                        # Executar via Rules (que chama Tools)
                        step_result = rules_instance.execute_step(passo, execution_data, self.empresa_config)
                        resultado[passo] = step_result
                        
                        if step_result.get('status') == 'erro':
                            logger.warning(f"PASSO {i}: {passo} ⚠️ - Erro na validação: {step_result.get('error')}")
                        else:
                            logger.info(f"PASSO {i}: {passo} ✓ - Slots validados")
                        
                    elif passo == "gerar_resposta":
                        # Gerar resposta final
                        resultado[passo] = {"status": "concluido"}
                        logger.info(f"PASSO {i}: {passo} ✓")
                        
                    else:
                        logger.warning(f"PASSO {i}: {passo} ⚠️ - Passo não implementado")
                        resultado[passo] = {"status": "nao_implementado"}
                        
                except Exception as e:
                    logger.error(f"Erro no PASSO {i} ({passo}): {e}")
                    resultado[passo] = {"status": "erro", "error": str(e)}
                    return self._generate_response_with_company_prompt(
                        "verificar_disponibilidade",
                        {'error': f"Erro no passo {passo}: {str(e)}", 'context': context},
                        context
                    )
            
            # 3. ✅ NOVA ARQUITETURA: Analisar resultados com regras de negócio
            logger.info("🎯 Todos os passos executados com sucesso via Rules → Tools → Integrations!")
            
            # ✅ Obter regras de negócio do contexto
            business_rules = context.get('business_rules', []) if context else []
            logger.info(f"📋 Regras de negócio para análise: {business_rules}")
            
            # ✅ Atualizar enriched_data final com contexto de disponibilidade (ids, etc.)
            try:
                enriched_data = getattr(self, '_last_enriched_extracted_data', dict(data))
                # Se no resultado houver ids, manter
                bs = resultado.get('buscar_servico', {}) or {}
                bp = resultado.get('buscar_profissional', {}) or {}
                if isinstance(bs, dict):
                    sid = bs.get('servico_id') or bs.get('id') or (bs.get('result', {}) or {}).get('id')
                    if sid:
                        enriched_data['servico_id'] = sid
                if isinstance(bp, dict):
                    pid = bp.get('profissional_id') or bp.get('id') or (bp.get('result', {}) or {}).get('id')
                    if pid:
                        enriched_data['profissional_id'] = pid
                # Garantir data
                if data.get('data'):
                    enriched_data['data'] = data.get('data')
                self._last_enriched_extracted_data = enriched_data
            except Exception as _e:
                logger.warning(f"Falha ao consolidar enriched_data final: {_e}")

            # ✅ NOVA ARQUITETURA: Chamar direto a LLM principal
            if business_rules:
                logger.info("🔍 Chamando direto a LLM principal com prompt da empresa...")
                return self._generate_response_with_company_prompt(
                    "verificar_disponibilidade",
                    {
                        'results': resultado,
                        'business_rules': business_rules,
                        'context': context
                    },
                    context
                )
            
            # ✅ FALLBACK: Lógica original se não houver regras de negócio
            logger.info("🔄 Usando lógica padrão (fallback)")
            
            # Verificar se temos disponibilidade
            disponibilidade = resultado.get('verificar_disponibilidade', {})
            
            if disponibilidade and disponibilidade.get('available_slots'):
                horarios = disponibilidade.get('available_slots', [])
                servico = resultado.get('buscar_servico', {})
                profissional = resultado.get('buscar_profissional', {})
                
                dados_para_llm = {
                    'horarios_disponiveis': horarios,
                    'servico': servico,
                    'profissional': profissional,
                    'data': data.get('data'),
                    'context': context
                }
                
                return self._generate_response_with_company_prompt(
                    "verificar_disponibilidade",
                    dados_para_llm,
                    context
                )
            else:
                return self._generate_response_with_company_prompt(
                    "verificar_disponibilidade",
                    {
                        'error': "Não há horários disponíveis para o serviço solicitado",
                        'context': context
                    },
                    context
                )
                
        except Exception as e:
            logger.error(f"Erro ao executar fluxo expandido: {e}")
            return self._generate_response_with_company_prompt(
                "verificar_disponibilidade",
                {
                    'error': f"Erro ao verificar disponibilidade: {str(e)}",
                    'context': context
                },
                context
            )
    
    def _call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Chama uma tool específica via LangChain"""
        try:
            if tool_name in self.tools:
                logger.info(f"🔧 Chamando tool: {tool_name}")
                result = self.tools[tool_name].invoke(params)
                return {"success": True, "result": result}
            else:
                logger.warning(f"Tool {tool_name} não encontrada")
                return {"success": False, "error": f"Tool {tool_name} não encontrada"}
        except Exception as e:
            logger.error(f"Erro ao chamar tool {tool_name}: {e}")
            return {"success": False, "error": str(e)}
    
    def _execute_reservation_creation(self, data: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Executa criação de reserva - DELEGA para Rules"""
        try:
            logger.info(f"📅 Delegando agendar_consulta para Rules com dados: {data}")
            
            # Verificar se tem dados básicos (já validados em verificar_disponibilidade)
            dados_basicos = ['profissional_id', 'servico_id', 'data', 'horario']
            dados_faltantes = [campo for campo in dados_basicos if not data.get(campo)]
            
            if dados_faltantes:
                return f"Para agendar, preciso das seguintes informações: {', '.join(dados_faltantes)}"
            
            # DELEGAR para Rules (que executam o fluxo completo)
            rules_instance = self.trinks_rules
            if not rules_instance:
                return "Erro: Não foi possível obter as regras da API"
            
            resultado = rules_instance.execute_flow("agendar_consulta", data, self.empresa_config, context)
            
            # Se precisa perguntar algo ao usuário, retornar a pergunta
            if resultado.get('status') in ['perguntar_cpf', 'perguntar_nome']:
                return self._generate_response_with_company_prompt(
                    "perguntar_dados",
                    {'message': resultado.get('message', 'Preciso de mais informações para continuar'), 'context': context},
                    context
                )
            
            # Se houve erro, retornar mensagem de erro
            if resultado.get('status') == 'erro':
                return self._generate_response_with_company_prompt(
                    "agendar_consulta",
                    {'error': resultado.get('error'), 'context': context},
                    context
                )
            
            # Se dados incompletos, retornar mensagem
            if resultado.get('status') == 'dados_incompletos':
                return f"Para agendar, preciso das seguintes informações: {', '.join(resultado.get('campos_faltantes', []))}"
            
            # Sucesso! Retornar resultado formatado
            if resultado.get('status') == 'sucesso':
                # Atualizar cache com dados do cliente e agendamento
                if resultado.get('cliente_id'):
                    data['cliente_id'] = resultado.get('cliente_id')
                if resultado.get('appointment_id'):
                    data['appointment_id'] = resultado.get('appointment_id')
                
                return self._generate_response_with_company_prompt(
                    "agendar_consulta",
                    resultado,
                    context
                )
            
            # Fallback
            return "Agendamento processado. Aguarde confirmação."
            
        except Exception as e:
            logger.error(f"Erro ao executar criação de reserva: {e}")
            return self._generate_response_with_company_prompt(
                "agendar_consulta",
                {'error': f"Erro ao criar reserva: {str(e)}", 'context': context},
                context
            )
    
    def _execute_reservation_cancellation(self, data: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Executa cancelamento de reserva"""
        try:
            if not data.get('data'):
                return self._generate_response_with_company_prompt(
                    "cancelar_consulta",
                    {'error': "Dados insuficientes para cancelamento", 'missing_fields': ['data'], 'context': context},
                    context
                )
            
            # Usar prompt da empresa para formatar resposta
            return self._generate_response_with_company_prompt(
                "cancelar_consulta",
                data,
                context
            )
            
        except Exception as e:
            logger.error(f"Erro ao cancelar reserva: {e}")
            return self._generate_response_with_company_prompt(
                "cancelar_consulta",
                {'error': f"Erro ao cancelar reserva: {str(e)}", 'context': context},
                context
            )
    
    def _execute_reservation_reschedule(self, data: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Executa reagendamento de reserva"""
        try:
            if not data.get('data_atual') or not data.get('nova_data'):
                return self._generate_response_with_company_prompt(
                    "reagendar_consulta",
                    {'error': "Dados insuficientes para reagendamento", 'missing_fields': ['data_atual', 'nova_data'], 'context': context},
                    context
                )
            
            # Usar prompt da empresa para formatar resposta
            return self._generate_response_with_company_prompt(
                "reagendar_consulta",
                data,
                context
            )
            
        except Exception as e:
            logger.error(f"Erro ao reagendar reserva: {e}")
            return self._generate_response_with_company_prompt(
                "reagendar_consulta",
                {'error': f"Erro ao reagendar reserva: {str(e)}", 'context': context},
                context
            )
    
    def _call_trinks_api(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Chama API Trinks real"""
        
        try:
            # Configuração da API
            base_url = self.empresa_config.get('trinks_base_url')
            api_key = self.empresa_config.get('trinks_api_key')
            estabelecimento_id = self.empresa_config.get('trinks_estabelecimento_id')
            
            if not all([base_url, api_key, estabelecimento_id]):
                logger.error("Configuração Trinks incompleta")
                return {"error": "Configuração Trinks incompleta"}
            
            # Headers
            headers = {
                'X-API-KEY': api_key,
                'estabelecimentoId': estabelecimento_id,
                'Content-Type': 'application/json'
            }
            
            # Fazer requisição
            import requests
            response = requests.get(
                f"{base_url}{endpoint}",
                params=params,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Erro na API Trinks: {response.status_code}")
                return {"error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Erro ao chamar API Trinks: {e}")
            return {"error": str(e)}
    
    def _find_professional_match(self, nome_procurado: str, profissionais: List[Dict], estrategias: List[str]) -> Dict[str, Any]:
        """Usa LLM para fazer match inteligente entre nome procurado e lista de profissionais"""
        try:
            logger.info(f"🤖 LLM fazendo match inteligente para '{nome_procurado}' entre {len(profissionais)} profissionais")
            
            # Preparar prompt para o LLM
            system_prompt = f"""Você é um assistente especializado em identificar profissionais de saúde.

TAREFA: Identificar qual profissional da lista corresponde ao nome mencionado pelo usuário.

NOME PROCURADO: "{nome_procurado}"

LISTA DE PROFISSIONAIS:
{json.dumps(profissionais, indent=2, ensure_ascii=False)}

INSTRUÇÕES:
1. Analise o nome procurado e compare com a lista de profissionais
2. Considere variações de nomes, apelidos e títulos
3. Retorne o profissional com maior confiança de match
4. Se houver ambiguidade, escolha o mais provável

FORMATO DE RESPOSTA (JSON):
{{
    "id": "ID do profissional",
    "nome": "Nome completo do profissional",
    "confianca": "ALTA|MEDIA|BAIXA",
    "razao": "Explicação do match"
}}

RESPONDA APENAS em JSON válido."""
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Identifique o profissional '{nome_procurado}' na lista fornecida.")
            ]
            
            response = self.llm.invoke(messages)
            logger.info(f"Resposta do LLM para match: {response.content}")
            
            # Limpar e parsear resposta
            content = response.content.strip()
            if content.startswith('```json'):
                content = content[7:-3]  # Remove ```json e ```
            elif content.startswith('```'):
                content = content[3:-3]  # Remove ``` genérico
            
            content = content.strip()
            logger.info(f"Conteúdo limpo para parse: {content}")
            
            try:
                match_result = json.loads(content)
                
                # Buscar o profissional completo na lista original
                profissional_id = match_result.get('id')
                for prof in profissionais:
                    if str(prof.get('id')) == str(profissional_id):
                        logger.info(f"LLM encontrou profissional: {prof['nome']} (confiança: {match_result.get('confianca', 'N/A')})")
                        logger.info(f"Razão do match: {match_result.get('razao', 'N/A')}")
                        return prof
                
                logger.error(f"ID retornado pelo LLM não encontrado na lista: {profissional_id}")
                return None
                
            except json.JSONDecodeError as e:
                logger.error(f"Erro ao parsear resposta do LLM: {e}")
                logger.error(f"Resposta recebida: {response.content}")
                return None
            
        except Exception as e:
            logger.error(f"Erro no match inteligente com LLM: {e}")
            return None
    
    # NOVOS MÉTODOS PARA FLUXO DE PROCEDIMENTO
    
    def _get_professionals_list(self) -> List[Dict[str, Any]]:
        """Busca lista de profissionais via API Trinks"""
        try:
            result = self._call_trinks_api("/profissionais", {})
            if result and not result.get('error'):
                return result.get('data', [])
            return []
        except Exception as e:
            logger.error(f"Erro ao buscar profissionais: {e}")
            return []
    
    def _get_services_list(self) -> List[Dict[str, Any]]:
        """Busca lista de serviços via API Trinks com filtro de visibilidade"""
        try:
            logger.info("🔍 Buscando TODOS os serviços da API Trinks (pageSize=300 + filtro cliente)...")
            
            # Parâmetros simples: uma chamada com pageSize grande
            params = {
                'page': 1,
                'pageSize': 300,  # Buscar 300 serviços de uma vez
                'somenteVisiveisCliente': True  # Apenas serviços visíveis para cliente
            }
            
            result = self._call_trinks_api("/servicos", params)
            
            if result and not result.get('error'):
                servicos = result.get('data', [])
                logger.info(f"✅ API Trinks retornou {len(servicos)} serviços")
                
                # Log resumido dos serviços
                if servicos:
                    categorias = set(serv.get('categoria', 'Sem categoria') for serv in servicos)
                    logger.info(f"📋 API retornou {len(servicos)} serviços em {len(categorias)} categorias")
                    logger.debug(f"Categorias: {sorted(list(categorias))}")
                    logger.debug(f"Lista completa: {[s.get('nome', 'N/A') for s in servicos]}")
                
                return servicos
            else:
                logger.error(f"❌ Erro na API Trinks: {result}")
            return []
                
        except Exception as e:
            logger.error(f"❌ Erro ao buscar serviços: {e}")
            return []
    
    def _get_professional_availability(self, profissional_id: str, data: str) -> Dict[str, Any]:
        """Busca disponibilidade de um profissional em uma data específica"""
        try:
            logger.info(f"Buscando disponibilidade para profissional ID {profissional_id} na data {data}")
            
            result = self._call_trinks_api(
                f"/agendamentos/profissionais/{data}",
                {'profissionalId': profissional_id}
            )
            
            if result and not result.get('error'):
                # Retornar dados do profissional específico
                for prof in result.get('data', []):
                    if str(prof.get('id')) == str(profissional_id):
                        return prof
            return {}
            
        except Exception as e:
            logger.error(f"Erro ao buscar disponibilidade: {e}")
            return {}
    
    def _get_service_availability(self, servico_id: str, data: str, profissional_id: str = None) -> Dict[str, Any]:
        """Busca disponibilidade de um serviço em uma data específica, com filtro opcional de profissional"""
        try:
            logger.info(f"Buscando disponibilidade para serviço ID {servico_id} na data {data}" + (f" com filtro de profissional {profissional_id}" if profissional_id else ""))
            
            # Construir endpoint CORRETO conforme documentação Trinks
            endpoint = f"/agendamentos/profissionais/{data}"
            params = {}
            
            # Adicionar parâmetros conforme documentação
            if servico_id:
                params['servicold'] = servico_id  # ID do serviço
            
            if profissional_id:
                params['profissionalld'] = profissional_id  # ID do profissional
            
            logger.debug(f"Endpoint={endpoint}, Params={params}")
            result = self._call_trinks_api(endpoint, params)
            
            if result and not result.get('error'):
                # Processar dados da API para extrair disponibilidade
                logger.debug(f"Dados brutos da API: {result}")
                
                # Extrair dados do profissional específico se filtrado
                if profissional_id:
                    for prof in result.get('data', []):
                        if str(prof.get('id')) == str(profissional_id):
                            logger.debug(f"Profissional encontrado: {prof}")
                            return {
                                'horariosVagos': prof.get('horariosVagos', []),
                                'intervalosVagos': prof.get('intervalosVagos', []),
                                'profissional': prof
                            }
                
                # Se não filtrado por profissional, retornar todos
                logger.debug(f"Retornando dados para todos os profissionais")
                return {
                    'horariosVagos': result.get('data', []),
                    'intervalosVagos': [],
                    'profissionais': result.get('data', [])
                }
            
            logger.warning(f"API retornou erro ou dados vazios: {result}")
            return {}
            
        except Exception as e:
            logger.error(f"Erro ao buscar disponibilidade do serviço: {e}")
            return {}
    
    def _find_service_match(self, nome_procurado: str, servicos: List[Dict], estrategias: List[str]) -> Dict[str, Any]:
        """Usa LLM para fazer match inteligente entre nome procurado e lista de serviços"""
        try:
            logger.info(f"🤖 LLM fazendo match inteligente de serviço para '{nome_procurado}' entre {len(servicos)} serviços")
            logger.debug(f"Serviços para análise: {[s.get('nome', 'N/A') for s in servicos]}")
            
            # Preparar prompt para o LLM
            system_prompt = f"""Você é um assistente especializado em identificar serviços de saúde.

TAREFA: Identificar qual serviço da lista corresponde ao nome mencionado pelo usuário.

NOME PROCURADO: "{nome_procurado}"

LISTA DE SERVIÇOS:
{json.dumps(servicos, indent=2, ensure_ascii=False)}

ESTRATÉGIA DE MATCH:
1. **Busca por Palavras-Chave**: Procure por serviços que contenham as palavras principais do nome procurado
2. **Correspondência Parcial**: Não exija match exato - procure por correspondências parciais
3. **Sinônimos**: Considere variações e sinônimos
4. **Categorias**: Procure por serviços da mesma categoria

EXEMPLOS:
- "limpeza de pele" → Procure por serviços que contenham "limpeza" E "pele"
- "massagem relaxante" → Procure por serviços que contenham "massagem" OU "relaxante"
- "aplicação de enzimas" → Procure por serviços que contenham "enzimas" OU "aplicação"

INSTRUÇÕES:
1. Analise o nome procurado e identifique palavras-chave principais
2. Procure na lista por serviços que contenham essas palavras-chave
3. Considere correspondências parciais - não exija match exato
4. Se encontrar múltiplos matches, escolha o mais relevante
5. SEMPRE tente encontrar um match - nunca retorne null

FORMATO DE RESPOSTA (JSON):
{{
    "id": "ID do serviço",
    "nome": "Nome completo do serviço",
    "confianca": "ALTA|MEDIA|BAIXA",
    "razao": "Explicação do match e palavras-chave encontradas"
}}

IMPORTANTE: 
- SEMPRE tente encontrar um match, mesmo que não seja perfeito
- Use correspondência parcial - não exija match exato
- Se não encontrar match exato, escolha o mais próximo
- NUNCA retorne id ou nome como null

RESPONDA APENAS em JSON válido."""
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Identifique o serviço '{nome_procurado}' na lista fornecida.")
            ]
            
            response = self.llm.invoke(messages)
            logger.info(f"Resposta do LLM para match de serviço: {response.content}")
            
            # Limpar e parsear resposta
            content = response.content.strip()
            if content.startswith('```json'):
                content = content[7:-3]  # Remove ```json e ```
            elif content.startswith('```'):
                content = content[3:-3]  # Remove ``` genérico
            
            content = content.strip()
            logger.info(f"Conteúdo limpo para parse: {content}")
            
            match_result = json.loads(content)
            
            # Buscar o serviço completo na lista original
            servico_id = match_result.get('id')
            for serv in servicos:
                if str(serv.get('id')) == str(servico_id):
                    logger.info(f"LLM encontrou serviço: {serv['nome']} (confiança: {match_result.get('confianca', 'N/A')})")
                    logger.info(f"Razão do match: {match_result.get('razao', 'N/A')}")
                    return serv
            
            logger.error(f"ID retornado pelo LLM não encontrado na lista: {servico_id}")
            return None
            
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao parsear resposta do LLM: {e}")
            logger.error(f"Resposta recebida: {response.content}")
            return None
        
        except Exception as e:
            logger.error(f"Erro no match inteligente de serviço: {e}")
            return None
    
    def _get_professionals_by_service(self, servico_id: str) -> List[Dict[str, Any]]:
        """Busca profissionais que fazem um serviço específico"""
        try:
            # Por enquanto, retornar todos os profissionais (implementar filtro depois)
            # TODO: Implementar filtro por serviço quando a API Trinks suportar
            return self._get_professionals_list()
        except Exception as e:
            logger.error(f"Erro ao buscar profissionais por serviço: {e}")
            return []
    
    def _generate_professional_preference_question(self, servico: Dict[str, Any], profissionais: List[Dict[str, Any]], data: str, context: Dict[str, Any]) -> str:
        """Gera pergunta para o usuário escolher profissional preferido"""
        try:
            # Usar prompt da empresa para formatar a pergunta
            return self._generate_response_with_company_prompt(
                "perguntar_preferencia_profissional",
                {
                    'servico': servico['nome'],
                    'data': data,
                    'profissionais_disponiveis': len(profissionais),
                    'nomes_profissionais': [p.get('nome', 'N/A') for p in profissionais[:3]]  # Mostrar primeiros 3
                },
                context
            )
            
        except Exception as e:
            logger.error(f"Erro ao gerar pergunta de preferência: {e}")
            # Fallback para resposta padrão
            return f"Perfeito! Encontrei o serviço '{servico['nome']}' e {len(profissionais)} profissionais disponíveis para {data}. Tem algum profissional específico em mente, ou posso mostrar a disponibilidade de todos?" 
    
    def _generate_response_with_company_prompt(self, action_type: str, data: Dict[str, Any], context: Dict[str, Any] = None) -> str:
        """Wrapper que redireciona para _analyze_with_company_llm mantendo compatibilidade"""
        
        # ✅ Adicionar action_type e data ao contexto para a LLM principal
        if context is None:
            context = {}
        
        # ✅ Enriquecer contexto com dados da action
        enriched_context = context.copy()
        enriched_context['action_type'] = action_type
        enriched_context['action_data'] = data
        
        # ✅ Redirecionar para LLM principal que decide tudo
        return self._analyze_with_company_llm(
            f"Processar ação: {action_type}",
            enriched_context
        )
    
    # ✅ MÉTODO REMOVIDO: _generate_fallback_response
    # Agora todos os erros são enviados para o LLM da empresa através do fluxo normal
    # O prompt da empresa deve ser configurado para responder adequadamente a erros 
    
    # ✅ MÉTODO REMOVIDO: _get_conversation_state nunca foi usado
    
    def _update_conversation_state(self, waid: str, new_data: Dict[str, Any]):
        """Atualiza o estado da conversa com novas informações extraídas"""
        state = self._get_conversation_state(waid)
        
        # ✅ PRESERVAR CONTEXTO: Só atualizar campos que foram realmente mencionados
        for key, value in new_data.items():
            if value is not None and value != "" and value != "null":
                # ✅ Atualiza apenas se o valor for válido
                state[key] = value
                logger.info(f"Campo '{key}' atualizado para: {value}")
            else:
                # ✅ Preserva o valor anterior se o campo não foi mencionado
                logger.info(f"Campo '{key}' preservado com valor anterior: {state.get(key, 'N/A')}")
        
        state['last_update'] = datetime.now()
        logger.info(f"Estado da conversa atualizado para waid {waid}: {state}")
    
    def _merge_extracted_with_state(self, waid: str, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Combina dados extraídos com o estado persistente da conversa de forma inteligente"""
        state = self._get_conversation_state(waid)
        merged_data = state.copy()
        
        # ✅ MESCLAGEM INTELIGENTE: Preservar contexto anterior, atualizar apenas o que mudou
        for key, value in extracted_data.items():
            if value is not None and value != "" and value != "null":
                # ✅ Campo foi mencionado na nova mensagem - atualizar
                old_value = merged_data.get(key, 'N/A')
                merged_data[key] = value
                logger.info(f"✅ Campo '{key}' atualizado: '{old_value}' → '{value}'")
            else:
                # ✅ Campo não foi mencionado - preservar valor anterior
                preserved_value = merged_data.get(key, 'N/A')
                logger.info(f"🔄 Campo '{key}' preservado: '{preserved_value}'")
        
        # Remover campos internos do estado
        merged_data.pop('last_update', None)
        
        logger.info(f"🎯 Dados mesclados para waid {waid}: {merged_data}")
        
        # ✅ VALIDAÇÃO FINAL: Garantir que campos críticos não sejam perdidos
        critical_fields = ['procedimento', 'data', 'profissional']
        for field in critical_fields:
            if field in merged_data and merged_data[field] and field not in extracted_data:
                logger.info(f"🛡️ Campo crítico '{field}' preservado: '{merged_data[field]}'")
            elif field not in merged_data or not merged_data[field]:
                logger.warning(f"⚠️ Campo crítico '{field}' não encontrado no estado final")
        
        return merged_data
    
    def _detectar_preferencia_profissional(self, mensagem: str) -> Dict[str, Any]:
        """Detecta se o usuário tem preferência por profissional ou é indiferente"""
        try:
            prompt = f"""
            Analise a seguinte mensagem do usuário e determine se ele está indicando que NÃO tem preferência por profissional específico.

            Mensagem: "{mensagem}"

            Responda apenas com um JSON válido:
            {{
                "tem_preferencia": true/false,
                "profissional_especifico": "nome_do_profissional" ou null,
                "razao": "explicacao_curta"
            }}

            Exemplos de "SEM preferência":
            - "tanto faz", "qualquer um", "não tenho preferência"
            - "pode ser qualquer um", "indiferente", "não importa"
            - "o que tiver disponível", "o melhor horário"

            Exemplos de "COM preferência":
            - "com a Dr. Maria", "quero o João", "prefiro a Ana"
            - "gostaria da Dra. Silva", "pode ser o Dr. Carlos"
            """
            
            messages = [
                SystemMessage(content=prompt),
                HumanMessage(content=mensagem)
            ]
            
            response = self.llm.invoke(messages)
            content = response.content.strip()
            
            # Limpar resposta do LLM
            if content.startswith('```json'):
                content = content[7:-3]
            elif content.startswith('```'):
                content = content[3:-3]
            
            content = content.strip()
            logger.info(f"Resposta do LLM para preferência: {content}")
            
            # Parsear JSON
            try:
                result = json.loads(content)
                logger.info(f"Preferência detectada: {result}")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"Erro ao parsear JSON da preferência: {e}")
                return {"tem_preferencia": True, "profissional_especifico": None, "razao": "Erro no parse"}
                
        except Exception as e:
            logger.error(f"Erro ao detectar preferência de profissional: {e}")
            return {"tem_preferencia": True, "profissional_especifico": None, "razao": "Erro na detecção"} 

    def _check_availability_for_all_professionals(self, servico: Dict[str, Any], data: str, context: Dict[str, Any]) -> str:
        """Verifica disponibilidade de TODOS os profissionais para um serviço e data - ABORDAGEM HÍBRIDA"""
        try:
            logger.info(f"🔍 ABORDAGEM HÍBRIDA: Verificando disponibilidade de TODOS os profissionais para {servico['nome']} em {data}")
            
            # Buscar disponibilidade de todos os profissionais
            disponibilidade_total = []
            profissionais_com_horarios = []
            
            # Buscar lista de profissionais que fazem o serviço
            profissionais = self._get_professionals_list()
            logger.info(f"📋 Analisando {len(profissionais)} profissionais para o serviço")
            
            for prof in profissionais:
                # Buscar disponibilidade específica para este profissional + serviço + data
                disponibilidade = self._get_service_availability(servico['id'], data, prof['id'])
                
                if disponibilidade and disponibilidade.get('available_slots'):
                    # Obter duração do procedimento para validação
                    procedure_duration = self.trinks_rules.get_procedure_duration(
                        servico['nome'], 
                        servico
                    )
                    
                    # Validar slots por duração
                    available_slots = disponibilidade.get('available_slots', [])
                    if available_slots:
                        slots_data = [{'horario': slot, 'disponivel': True} for slot in available_slots]
                        valid_slots = self.trinks_rules.filter_available_slots_by_duration(
                            slots_data, 
                            procedure_duration
                        )
                        
                        if valid_slots:
                            valid_horarios = [slot['horario_inicio'] for slot in valid_slots]
                            profissionais_com_horarios.append({
                                'profissional': prof,
                                'horarios': valid_horarios,
                                'quantidade_horarios': len(valid_horarios),
                                'disponibilidade_bruta': disponibilidade
                            })
                            logger.info(f"✅ {prof['nome']}: {len(valid_horarios)} horários válidos")
                        else:
                            logger.info(f"❌ {prof['nome']}: horários não atendem duração do procedimento")
                    else:
                        logger.info(f"❌ {prof['nome']}: sem horários disponíveis")
                else:
                    logger.info(f"❌ {prof['nome']}: sem disponibilidade para este serviço/data")
            
            if not profissionais_com_horarios:
                return self._generate_response_with_company_prompt(
                    "verificar_disponibilidade",
                    {
                        'error': f"Não há horários disponíveis para {servico['nome']} em {data}",
                        'suggestion': "Gostaria de verificar outra data?",
                        'context': context
                    },
                    context
                )
            
            # ✅ PRIORIZAR por quantidade de horários (mais horários primeiro)
            profissionais_com_horarios.sort(key=lambda x: x['quantidade_horarios'], reverse=True)
            
            logger.info(f"🎯 Profissionais ordenados por prioridade (mais horários primeiro):")
            for i, prof in enumerate(profissionais_com_horarios):
                logger.info(f"   {i+1}. {prof['profissional']['nome']}: {prof['quantidade_horarios']} horários")
            
            # Retornar disponibilidade priorizada de todos os profissionais
            return self._generate_response_with_company_prompt(
                "verificar_disponibilidade",
                {
                    'servico': servico,
                    'data': data,
                    'disponibilidade': profissionais_com_horarios,
                    'tipo': 'todos_profissionais_priorizados',
                    'context': context
                },
                context
            )
            
        except Exception as e:
            logger.error(f"Erro ao verificar disponibilidade de todos os profissionais: {e}")
            return self._generate_response_with_company_prompt(
                "verificar_disponibilidade",
                {
                    'error': f"Erro ao verificar disponibilidade: {str(e)}",
                    'context': context
                },
                context
            )
    
    def _check_availability_for_specific_professional(self, servico: Dict[str, Any], profissional_nome: str, data: str, context: Dict[str, Any]) -> str:
        """Verifica disponibilidade de um profissional específico para um serviço e data"""
        try:
            logger.info(f"Verificando disponibilidade de {profissional_nome} para {servico['nome']} em {data}")
            
            # Buscar lista de profissionais para fazer match
            profissionais = self._get_professionals_list()
            profissional = self._find_professional_match(profissional_nome, profissionais, [])
            
            if not profissional:
                return self._generate_response_with_company_prompt(
                    "verificar_disponibilidade",
                    {
                        'error': f"Não consegui identificar o profissional '{profissional_nome}'",
                        'suggestion': "Pode ser mais específico?",
                        'context': context
                    },
                    context
                )
            
            # Verificar disponibilidade do profissional específico
            disponibilidade = self._get_professional_availability(profissional['id'], data)
            
            if not disponibilidade or not disponibilidade.get('horarios_disponiveis'):
                return self._generate_response_with_company_prompt(
                    "verificar_disponibilidade",
                    {
                        'error': f"{profissional['nome']} não tem horários disponíveis para {servico['nome']} em {data}",
                        'suggestion': "Gostaria de verificar outra data ou outro profissional?",
                        'context': context
                    },
                    context
                )
            
            # Retornar disponibilidade do profissional específico
            return self._generate_response_with_company_prompt(
                "verificar_disponibilidade",
                {
                    'servico': servico,
                    'profissional': profissional,
                    'data': data,
                    'disponibilidade': disponibilidade.get('horarios_disponiveis', []),
                    'tipo': 'profissional_especifico',
                    'context': context
                },
                context
            )
            
        except Exception as e:
            logger.error(f"Erro ao verificar disponibilidade de profissional específico: {e}")
            return self._generate_response_with_company_prompt(
                "verificar_disponibilidade",
                {
                    'error': f"Erro ao verificar disponibilidade: {str(e)}",
                    'context': context
                },
                context
            )
    
    def _generate_generic_preference_question(self, servico: Dict[str, Any], data: str, context: Dict[str, Any]) -> str:
        """Gera pergunta genérica sobre preferência de profissional SEM sugerir nomes"""
        try:
            return self._generate_response_with_company_prompt(
                "verificar_disponibilidade",
                {
                    'servico': servico,
                    'data': data,
                    'pergunta': 'preferencia_generica',
                    'context': context
                },
                context
            )
        except Exception as e:
            logger.error(f"Erro ao gerar pergunta de preferência genérica: {e}")
            return "Gostaria de verificar a disponibilidade de todos os profissionais ou tem alguma preferência específica?" 
    
    def _execute_single_action(self, action: str, extracted_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """✅ NOVA FUNÇÃO: Executa uma action individual e retorna resultado estruturado"""
        try:
            # Executar a action via Rules
            step_result = self.trinks_rules.execute_step(action, extracted_data, self.empresa_config, context)
            logger.info(f"🔧 Resultado da execução: {step_result}")
            
            # ✅ NOVO: Seguir instruções de cache das Rules
            if step_result.get('cache_instructions'):
                logger.info(f"📋 Seguindo instruções de cache: {step_result.get('cache_instructions')}")
                self._update_cache_from_instructions(step_result.get('cache_instructions'), extracted_data)
            
            # Retornar resultado estruturado para análise posterior
            return {
                "status": "action_executada",
                "action": action,
                "result": step_result
            }
                
        except Exception as e:
            logger.error(f"❌ Erro ao executar {action}: {e}")
            return {
                "status": "erro",
                "action": action,
                "error": str(e)
            }
    
    def _execute_multiple_actions(self, actions: list, extracted_data: Dict[str, Any], next_steps: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """✅ NOVA FUNÇÃO: Executa múltiplas actions em sequência e retorna resultados estruturados"""
        try:
            logger.info(f"🔄 Executando {len(actions)} actions em sequência: {actions}")
            
            results = {}
            for i, action in enumerate(actions):
                logger.info(f"🔄 Executando action {i+1}/{len(actions)}: {action}")
                
                # Executar action individual
                step_result = self.trinks_rules.execute_step(action, extracted_data, self.empresa_config, context)
                logger.info(f"🔧 Resultado da execução {action}: {step_result}")
                
                # ✅ NOVO: Seguir instruções de cache das Rules
                if step_result.get('cache_instructions'):
                    logger.info(f"📋 Seguindo instruções de cache para {action}: {step_result.get('cache_instructions')}")
                    self._update_cache_from_instructions(step_result.get('cache_instructions'), extracted_data)
                
                # Armazenar resultado estruturado
                results[action] = step_result
                
                # Se falhou, parar execução
                if step_result.get('status') == 'erro':
                    logger.error(f"❌ Action {action} falhou, parando execução")
                    break
            
            # Retornar resultados estruturados para análise posterior
            return {
                "status": "actions_executadas",
                "results": results,
                "actions_executadas": actions
            }
                
        except Exception as e:
            logger.error(f"❌ Erro ao executar múltiplas actions: {e}")
            return {
                "status": "erro",
                "error": str(e),
                "results": {}
            }

    def _handle_ask_user_direct(self, business_rules: list, extracted_data: Dict[str, Any], next_steps: Dict[str, Any], context: Dict[str, Any], intent: str) -> str:
        """✅ NOVA FUNÇÃO: ask_user vai DIRETO para o prompt da empresa (sem LLM intermediária)"""
        logger.info("👤 ask_user - indo DIRETO para o prompt da empresa")
        
        # ✅ Preparar dados para o prompt da empresa
        ask_user_data = {
            'action': 'ask_user',
            'missing_data': next_steps.get('missing_data', []),
            'business_rules': business_rules,
            'extracted_data': extracted_data,
            'context': context
        }
        
        # ✅ Gerar resposta formatada DIRETAMENTE pelo prompt da empresa
        formatted_response = self._generate_response_with_company_prompt(
            intent,
            ask_user_data,
            context
        )
        logger.info(f"👤 Resposta formatada DIRETA pela empresa: {formatted_response}")
        
        # ✅ Retornar string pronta para o usuário
        return formatted_response

    def _format_company_knowledge(self) -> str:
        """Formata as knowledge da empresa para uso no prompt"""
        try:
            knowledge = self.empresa_config.get('knowledge_json', {})
            items = knowledge.get('items', [])
            
            if not items:
                return "Nenhuma informação específica configurada."
            
            formatted = []
            for item in items:
                if isinstance(item, dict):
                    key = item.get('key', '')
                    description = item.get('description', '')
                    if key and description:
                        formatted.append(f"• {key}: {description}")
            
            return "\n".join(formatted) if formatted else "Nenhuma informação específica configurada."
        except Exception as e:
            logger.error(f"Erro ao formatar knowledge: {e}")
            return "Erro ao carregar informações da empresa"

    def _format_conversation_history(self, messages: List) -> str:
        """Formata histórico da conversa para o prompt"""
        if not messages:
            return "Nenhum histórico disponível"
        
        formatted = []
        for msg in messages:
            if hasattr(msg, 'content'):
                role = "Cliente" if hasattr(msg, '__class__') and 'Human' in msg.__class__.__name__ else "Assistente"
                formatted.append(f"• {role}: {msg.content}")
        
        return "\n".join(formatted)

    def _analyze_with_company_llm(self, message: str, context: Dict) -> str:
        """LLM da empresa analisa TUDO e decide o caminho"""
        
        # ✅ OBTER histórico da memória LangChain
        conversation_history = []
        if self.memory.chat_memory.messages:
            conversation_history = self.memory.chat_memory.messages[-6:]
        
        # ✅ OBTER regras de negócio do contexto
        business_rules = context.get('business_rules', [])
        
        # ✅ OBTER dados extraídos do contexto
        extracted_data = context.get('extracted_data', {})
        
        # ✅ OBTER action_type e dados das tools (unificando results e action_data)
        action_type = context.get('action_type', 'análise_geral')
        results = context.get('results', {})
        action_data = context.get('action_data', {})
        
        # ✅ COMBINAR para contemplar ambos os casos de uso
        tools_data = results if results else action_data
        
        system_prompt = f"""Você é um assistente virtual da {self.empresa_config.get('nome', 'Empresa')}.

PROMPT DA EMPRESA:
{self.empresa_config.get('prompt', '')}

KNOWLEDGE DA EMPRESA:
{self._format_company_knowledge()}

HISTÓRICO DA CONVERSA (últimas 6 mensagens):
{self._format_conversation_history(conversation_history)}

REGRAS DE NEGÓCIO:
{business_rules if business_rules else 'Nenhuma regra específica definida'}

DADOS EXTRAÍDOS:
{json.dumps(extracted_data, indent=2, ensure_ascii=False, default=str) if extracted_data else 'Nenhum dado extraído'}

TIPO DE AÇÃO:
{action_type}

DADOS DA AÇÃO:
{json.dumps(tools_data, indent=2, ensure_ascii=False, default=str) if tools_data else 'Nenhum dado de ação'}

INSTRUÇÕES:
Analise a mensagem do usuário e responda de acordo com o prompt da empresa, considerando o contexto da conversa e as regras de negócio.

IMPORTANTE - MÚLTIPLAS MENSAGENS:
Se você receber múltiplas mensagens (como agora), NÃO responda cada uma separadamente.
Analise tudo junto e dê UMA resposta inteligente que aborde o contexto completo.

EXEMPLO: Se o usuário disser 'Oi' + 'Tudo bem?', responda 'Oi! Tudo bem sim, obrigado! 😊 Como posso te ajudar hoje?'"""

        # ✅ UMA CHAMADA LLM que decide tudo
        response = self.llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=message)
        ])
        
        return response.content.strip()

    def _call_complete_flow(self, message: str, waid: str, context: Dict) -> str:
        """Chama o fluxo completo baseado na API ativa da empresa"""
        
        # ✅ DETECTAR qual API está ativa e chamar fluxo apropriado
        active_apis = []
        
        if self.empresa_config.get('trinks_enabled'):
            active_apis.append('trinks')
        
        if self.empresa_config.get('google_calendar_enabled'):
            active_apis.append('google_calendar')
        
        if self.empresa_config.get('google_sheets_enabled'):
            active_apis.append('google_sheets')
        
        logger.info(f"🔄 APIs ativas detectadas: {active_apis}")
        
        # ✅ DECIDIR qual fluxo usar baseado na API ativa
        if 'trinks' in active_apis:
            logger.info("🔄 Usando fluxo Trinks")
            return self._call_trinks_flow(message, waid, context)
        
        elif 'google_calendar' in active_apis:
            logger.info("🔄 Usando fluxo Google Calendar")
            return self._call_google_calendar_flow(message, waid, context)
        
        elif 'google_sheets' in active_apis:
            logger.info("🔄 Usando fluxo Google Sheets")
            return self._call_google_sheets_flow(message, waid, context)
        
        else:
            logger.warning("⚠️ Nenhuma API ativa detectada")
            return self._generate_response_with_company_prompt(
                "erro_sistema",
                {'error': "Nenhuma API ativa detectada", 'context': context},
                context
            )

    def analyze_and_respond(self, message: str, waid: str, context: Dict[str, Any] = None) -> str:
        """Método principal que analisa e decide o caminho"""
        try:
            logger.info(f"Analisando mensagem para waid {waid}")
            
            # ✅ CARREGAR contexto do cache por waid
            self._load_conversation_context(waid)
            
            # ✅ PRIMEIRO: Análise inteligente com LLM da empresa
            response = self._analyze_with_company_llm(message, context)
            
            # ✅ SEGUNDO: Se LLM disse que vai processar → chama fluxo completo
            if "vou processar" in response.lower() or "processar" in response.lower():
                logger.info("🔄 LLM decidiu usar fluxo completo - chamando TrinksRules")
                return self._call_complete_flow(message, waid, context)
            
            # ✅ TERCEIRO: Resposta direta da empresa
            logger.info("✅ Resposta direta da empresa")
            
            # ✅ CRÍTICO: SALVAR mensagem e resposta na memória ANTES de retornar
            self.memory.chat_memory.add_user_message(message)
            self.memory.chat_memory.add_ai_message(response)
            
            # ✅ SALVAR contexto no cache para manter histórico
            self._save_conversation_context(waid, {})
            
            return response
            
        except Exception as e:
            logger.error(f"Erro na análise: {e}")
            return "Ocorreu um erro. Tente novamente."

    def _call_trinks_flow(self, message: str, waid: str, context: Dict) -> str:
        """Chama fluxo Trinks (process_message atual)"""
        return self.process_message(message, waid, context)

    def _call_google_calendar_flow(self, message: str, waid: str, context: Dict) -> str:
        """Chama fluxo Google Calendar (quando implementado)"""
        # TODO: Implementar fluxo Google Calendar
        return "Funcionalidade Google Calendar em desenvolvimento"

    def _call_google_sheets_flow(self, message: str, waid: str, context: Dict) -> str:
        """Chama fluxo Google Sheets (quando implementado)"""
        # TODO: Implementar fluxo Google Sheets
        return "Funcionalidade Google Sheets em desenvolvimento"