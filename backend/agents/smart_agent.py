from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferWindowMemory
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import tool as lc_tool
import logging
import json
import requests
from datetime import datetime

from .api_rules_engine import api_rules_engine

logger = logging.getLogger(__name__)

class SmartAgent:
    """Agente inteligente que usa LLM para identificar intenções e API Rules para executar fluxos"""
    
    def __init__(self, empresa_config: Dict[str, Any]):
        self.empresa_config = empresa_config
        
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
    
    def _setup_tools(self) -> List:
        """Configura as tools disponíveis"""
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
                logger.error(f"Erro ao buscar conhecimento: {e}")
                return "Erro ao buscar informações da empresa"
        
        @lc_tool("get_api_rules")
        def get_api_rules() -> str:
            """Retorna as regras da API ativa para a empresa"""
            try:
                rules = api_rules_engine.get_api_rules(self.empresa_config)
                return f"Regras da API {rules['api_name']}: Email obrigatório: {rules['email_required']}, WaId obrigatório: {rules['waid_required']}"
            except Exception as e:
                logger.error(f"Erro ao buscar regras da API: {e}")
                return "Erro ao buscar regras da API"
        
        @lc_tool("get_available_flows")
        def get_available_flows() -> str:
            """Retorna os fluxos disponíveis para a API ativa"""
            try:
                rules = api_rules_engine.get_api_rules(self.empresa_config)
                flows = rules.get('fluxos_por_intencao', {})
                
                if flows:
                    flow_list = []
                    for intent, flow in flows.items():
                        flow_list.append(f"- {intent}: {flow['descricao']}")
                    
                    return f"Fluxos disponíveis para {rules['api_name']}:\n" + "\n".join(flow_list)
                else:
                    return f"Nenhum fluxo configurado para {rules['api_name']}"
            except Exception as e:
                logger.error(f"Erro ao buscar fluxos: {e}")
                return "Erro ao buscar fluxos disponíveis"
        
        @lc_tool("execute_flow")
        def execute_flow(intent: str, **kwargs) -> str:
            """Executa um fluxo específico baseado na intenção"""
            try:
                rules = api_rules_engine.get_api_rules(self.empresa_config)
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
                
                # Simular execução do fluxo
                steps = flow.get('passos', [])
                result = f"Executando fluxo '{intent}':\n"
                
                for step in steps:
                    result += f"✅ {step}\n"
                
                result += f"\nDados recebidos: {kwargs}"
                return result
                
            except Exception as e:
                logger.error(f"Erro ao executar fluxo: {e}")
                return f"Erro ao executar fluxo '{intent}': {str(e)}"
        
        tools.extend([
            get_business_knowledge,
            get_api_rules,
            get_available_flows,
            execute_flow
        ])
        
        return tools
    
    def process_message(self, message: str, context: Dict[str, Any] = None) -> str:
        """Processa uma mensagem usando LLM para identificar intenção e executar fluxo"""
        try:
            # 0. Carregar contexto da conversa se disponível
            waid = context.get('waid') if context else None
            if waid:
                self._load_conversation_context(waid)
                logger.info(f"Contexto carregado para waid {waid}, mensagens na memória: {len(self.memory.chat_memory.messages)}")
            
            # 1. Usar LLM para identificar intenção
            intent = self._detect_intent_with_llm(message, context)
            logger.info(f"Intenção detectada: {intent}")
            
            # 2. Verificar se a intenção é suportada pela API
            if intent and intent != "general":
                # 3. Executar fluxo correspondente
                response = self._execute_intent_flow(intent, message, context)
            else:
                # 4. Gerar resposta geral
                response = self._generate_general_response(message, context)
            
            # 5. Salvar no memory local
            logger.info(f"Salvando contexto local: input='{message}', output='{response[:100]}...'")
            self.memory.save_context(
                {"input": message},
                {"output": response}
            )
            logger.info(f"Contexto local salvo! Total de mensagens na memória: {len(self.memory.chat_memory.messages)}")
            
            # 6. Salvar no cache global se tiver waid
            if waid:
                self._save_conversation_context(waid)
            
            return response
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}")
            return f"Desculpe, tive um problema técnico: {str(e)}"
    
    def _detect_intent_with_llm(self, message: str, context: Dict[str, Any] = None) -> str:
        """Usa LLM para identificar a intenção da mensagem com contexto da conversa"""
        try:
            # Obter fluxos disponíveis
            rules = api_rules_engine.get_api_rules(self.empresa_config)
            flows = rules.get('fluxos_por_intencao', {})
            available_intents = list(flows.keys()) if flows else []
            
            # Prompt para o LLM
            system_prompt = f"""Você é um assistente especializado em identificar intenções de clientes.

INTENÇÕES SUPORTADAS (se configuradas):
{', '.join(available_intents) if available_intents else 'Nenhuma intenção específica configurada'}

INSTRUÇÕES CRÍTICAS:
- Analise a mensagem do cliente
- SEMPRE considere o contexto da conversa anterior
- Se houver fluxos configurados, identifique a intenção
- Se não houver fluxos, responda "general"
- Responda APENAS com o nome da intenção ou "general"

REGRA DE CLASSIFICAÇÃO FUNDAMENTAL:
- agendar_consulta: SÓ quando o cliente já confirmou alguma das sugestões de horário que enviamos
- verificar_disponibilidade: Para TODAS as outras situações

EXEMPLOS DE CLASSIFICAÇÃO:
- "Queria fazer aplicação de enzimas" → verificar_disponibilidade
- "A Dra. X tem horário dia 24?" → verificar_disponibilidade  
- "Queria agendar com Dr. João amanhã" → verificar_disponibilidade
- "Sim, esse horário de amanhã às 14h está perfeito!" → agendar_consulta
- "Perfeito, confirma o dia 25 às 15h" → agendar_consulta
- "Isso mesmo, agenda para quinta às 10h" → agendar_consulta

REGRAS DE CONTEXTO:
1. Se o usuário fizer uma pergunta de follow-up (ex: "E para dia 26?"), mantenha a intenção da conversa anterior
2. Se o usuário mencionar apenas uma nova data/horário, mantenha a intenção de verificar_disponibilidade
3. Use o histórico da conversa para entender o que o usuário quer
4. SEMPRE priorize verificar_disponibilidade, a menos que seja uma confirmação explícita de horário sugerido"""

            # Mensagens para o LLM
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=message)
            ]
            
            # Adicionar contexto da conversa se disponível
            if self.memory.chat_memory.messages:
                # Usar até 10 mensagens para melhor contexto
                context_messages = self.memory.chat_memory.messages[-10:]
                logger.info(f"Adicionando contexto da conversa: {len(context_messages)} mensagens anteriores")
                logger.info(f"Últimas mensagens do contexto: {[msg.content for msg in context_messages[-4:]]}")
                messages.extend(context_messages)
            else:
                logger.warning("NENHUM contexto disponível para detecção de intenção!")
            
            # Gerar resposta
            response = self.llm.invoke(messages)
            intent = response.content.strip().lower()
            
            # Validar se a intenção é válida
            if intent in available_intents or intent == "general":
                return intent
            else:
                logger.warning(f"Intenção inválida retornada pelo LLM: {intent}")
                return "general"
                
        except Exception as e:
            logger.error(f"Erro ao detectar intenção com LLM: {e}")
            return "general"
    
    def _execute_intent_flow(self, intent: str, message: str, context: Dict[str, Any] = None) -> str:
        """Executa o fluxo correspondente à intenção"""
        try:
            # Obter waid do contexto
            waid = context.get('waid') if context else None
            if not waid:
                logger.warning("Waid não encontrado no contexto, usando estado padrão")
                waid = "default"
            
            # 1. Extrair informações da mensagem
            extracted_data = self._extract_information(message)
            logger.info(f"Dados extraídos da mensagem: {extracted_data}")
            
            # 2. Atualizar estado da conversa
            self._update_conversation_state(waid, extracted_data)
            
            # 3. Mesclar dados extraídos com estado persistente
            merged_data = self._merge_extracted_with_state(waid, extracted_data)
            logger.info(f"Dados mesclados com estado: {merged_data}")
            
            # 4. Executar fluxo baseado na intenção
            if intent == "verificar_disponibilidade":
                return self._execute_availability_check(merged_data, context)
            elif intent == "agendar_consulta":
                return self._execute_reservation_creation(merged_data, context)
            elif intent == "cancelar_consulta":
                return self._execute_reservation_cancellation(merged_data, context)
            elif intent == "reagendar_consulta":
                return self._execute_reservation_reschedule(merged_data, context)
            else:
                return f"Intenção '{intent}' não suportada"
            
        except Exception as e:
            logger.error(f"Erro ao executar fluxo: {e}")
            return f"Erro ao processar sua solicitação: {str(e)}"
    
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
            return "Olá! Como posso ajudar você hoje?"
    
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
            cached_messages = SmartAgent._conversation_cache[waid]
            logger.info(f"Carregando contexto para waid {waid}: {len(cached_messages)} mensagens")
            
            # Restaurar mensagens na memória
            for msg in cached_messages:
                if msg.get('type') == 'human':
                    self.memory.chat_memory.add_user_message(msg['content'])
                elif msg.get('type') == 'ai':
                    self.memory.chat_memory.add_ai_message(msg['content'])
        else:
            logger.info(f"Primeira mensagem para waid {waid}, criando novo contexto")
    
    def _save_conversation_context(self, waid: str) -> None:
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
        
        SmartAgent._conversation_cache[waid] = messages
        logger.info(f"Contexto salvo para waid {waid}: {len(messages)} mensagens")
    
    def _extract_information(self, message: str) -> Dict[str, Any]:
        """Extrai informações da mensagem usando LLM com contexto da conversa e estado persistente"""
        
        # Obter contexto limitado (últimas 10 mensagens para melhor contexto)
        context_messages = []
        if self.memory.chat_memory.messages:
            # Usar até 10 mensagens para melhor contexto e performance
            context_messages = self.memory.chat_memory.messages[-10:]
            logger.info(f"Adicionando contexto para extração: {len(context_messages)} mensagens anteriores")
            logger.info(f"Últimas mensagens do contexto: {[msg.content for msg in context_messages[-4:]]}")
        else:
            logger.warning("NENHUM contexto disponível para extração!")
        
        # Construir prompt com foco no formato JSON, contexto e priorização de dados novos
        system_prompt = f"""Você é um assistente que extrai informações de conversas de WhatsApp para agendamentos.

CONTEXTO ATUAL: Hoje é {datetime.now().strftime('%d/%m/%Y')} (DD/MM/YYYY).

FUNÇÃO PRINCIPAL: Analisar a conversa e retornar APENAS um objeto JSON com as informações extraídas.

CAMPOS PARA EXTRAÇÃO:
- profissional: nome da pessoa mencionada (se houver)
- procedimento: tipo de serviço/procedimento (se houver)
- data: data mencionada (converta para YYYY-MM-DD)
- horario: horário mencionado (se houver)
- servico: tipo de serviço (se houver)
- preferencia_profissional: preferência expressa (se houver)

DETECÇÃO AUTOMÁTICA DE PREFERÊNCIA:
- Se o usuário disser "tanto faz", "qualquer um", "não tenho preferência" → profissional: "indiferente"
- Se o usuário disser "pode ser qualquer um", "indiferente" → profissional: "indiferente"
- Se o usuário disser "o que tiver disponível" → profissional: "indiferente"

CONVERSÃO DE DATAS:
- "25/08" → "2025-08-25"
- "segunda" → próxima segunda-feira em YYYY-MM-DD
- "amanhã" → data de amanhã em YYYY-MM-DD
- "hoje" → data de hoje em YYYY-MM-DD

REGRAS CRÍTICAS DE PRIORIDADE:
1. SEMPRE retorne APENAS JSON válido
2. A MENSAGEM ATUAL SEMPRE TEM PRIORIDADE sobre o contexto anterior
3. Se a mensagem atual mencionar nova data, use APENAS ela (ignore datas anteriores)
4. Se a mensagem atual mencionar novo horário, use APENAS ele (ignore horários anteriores)
5. Se a mensagem atual mencionar novo profissional, use APENAS ele (ignore profissionais anteriores)
6. Use o contexto apenas para informações NÃO mencionadas na mensagem atual
7. NUNCA mantenha dados antigos se novos foram explicitamente mencionados

EXEMPLOS DE PRIORIDADE:
- "E para dia 28/08?" → {{"data": "2025-08-28"}} (IGNORE data anterior 29/08)
- "E para às 15h?" → {{"horario": "15:00"}} (IGNORE horário anterior)
- "E para amanhã?" → {{"data": "2025-08-15"}} (IGNORE data anterior)
- "E para a Maria?" → {{"profissional": "maria"}} (IGNORE profissional anterior)

EXEMPLOS DE RESPOSTA:
- "Oi queria marcar retorno com a amabile" → {{"profissional": "amabile"}}
- "Para segunda feira" → {{"data": "2025-08-18"}}
- "as 19 ela tem?" → {{"horario": "19:00", "profissional": "amabile"}}
- "E para dia 29/08?" → {{"data": "2025-08-29", "profissional": "amabile"}}
- "Tanto faz, qualquer um" → {{"profissional": "indiferente"}}
- "Pode ser qualquer um" → {{"profissional": "indiferente"}}

IMPORTANTE: A mensagem atual SEMPRE tem prioridade sobre o contexto anterior. Se o usuário mencionar uma nova data, horário ou profissional, use APENAS essas informações novas.

FORMATO OBRIGATÓRIO: Retorne APENAS o JSON, sem texto adicional, sem explicações."""
        
        try:
            messages = [SystemMessage(content=system_prompt)]
            
            # Adicionar contexto da conversa (últimas 10 mensagens)
            if context_messages:
                messages.extend(context_messages)
            
            # Adicionar a mensagem atual
            messages.append(HumanMessage(content=message))
            
            response = self.llm.invoke(messages)
            
            # LOG da resposta bruta do LLM
            logger.info(f"Resposta bruta do LLM: '{response.content}'")
            logger.info(f"Tamanho da resposta: {len(response.content)}")
            
            # Verificar se a resposta está vazia
            if not response.content or response.content.strip() == "":
                logger.error("LLM retornou resposta vazia")
                return {}
            
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
                extracted = json.loads(content)
                logger.info(f"Informações extraídas: {extracted}")
                return extracted
            except json.JSONDecodeError as e:
                logger.error(f"Erro ao parsear JSON: {e}")
                logger.error(f"Conteúdo que falhou: '{content}'")
                return {}
            
        except Exception as e:
            logger.error(f"Erro ao extrair informações: {e}")
            return {}
    
    def _execute_availability_check(self, extracted_data: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Executa verificação de disponibilidade com suporte a busca por profissional OU procedimento"""
        try:
            # Obter regras expandidas da API
            api_rules = api_rules_engine.get_availability_check_rules_expanded(self.empresa_config)
            if not api_rules:
                return "Erro: Regras de disponibilidade não configuradas"
            
            # Validar requisição
            validation = api_rules_engine.validate_availability_request(extracted_data, self.empresa_config)
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
            
            # Executar fluxo expandido único
            return self._execute_expanded_availability_check(extracted_data, context, api_rules)
                
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
    

    


    def _execute_expanded_availability_check(self, data: Dict[str, Any], context: Dict[str, Any], api_rules: Dict[str, Any]) -> str:
        """Executa verificação de disponibilidade com fluxo expandido completo"""
        try:
            logger.info("Executando fluxo expandido de verificação de disponibilidade")
            
            # Obter passos configurados
            fluxo_config = api_rules.get('fluxos_por_intencao', {}).get('verificar_disponibilidade', {})
            passos = fluxo_config.get('passos', [])
            
            logger.info(f"Passos configurados: {passos}")
            
            # PASSO 1: Extrair dados (já feito)
            logger.info("PASSO 1: Dados extraídos ✓")
            
            # PASSO 2: Determinar tipo de busca
            logger.info("PASSO 2: Determinando tipo de busca...")
            search_type = api_rules_engine.determine_search_type(data)
            logger.info(f"Tipo de busca: {search_type}")
            
            # PASSO 3: Buscar entidade (profissional ou serviço)
            logger.info("PASSO 3: Buscando entidade...")
            entidade = None
            
            if search_type == 'por_profissional':
                # Buscar profissional
                profissionais = self._get_professionals_list()
                if not profissionais:
                    return self._generate_response_with_company_prompt(
                        "verificar_disponibilidade",
                        {'error': "Não consegui buscar a lista de profissionais", 'context': context},
                        context
                    )
                
                profissional = self._find_professional_match(data.get('profissional'), profissionais, fluxo_config.get('estrategias_match', []))
                if not profissional:
                    return self._generate_response_with_company_prompt(
                        "verificar_disponibilidade",
                        {'error': f"Profissional '{data.get('profissional')}' não encontrado", 'context': context},
                        context
                    )
                
                entidade = {'tipo': 'profissional', 'dados': profissional}
                logger.info(f"Profissional encontrado: {profissional['nome']}")
                
                # IMPORTANTE: Para busca por profissional, precisamos identificar o serviço também
                if data.get('procedimento'):
                    # Usuário mencionou o procedimento, fazer match
                    servicos = self._get_services_list()
                    if servicos:
                        servico = self._find_service_match(data.get('procedimento'), servicos, fluxo_config.get('estrategias_match', []))
                        if servico:
                            entidade['servico'] = servico
                            logger.info(f"Serviço identificado para profissional: {servico['nome']}")
                        else:
                            logger.warning(f"Procedimento '{data.get('procedimento')}' não encontrado, usando serviço padrão")
                    else:
                        logger.warning("Não consegui buscar lista de serviços para identificar procedimento")
                
            elif search_type == 'por_procedimento':
                # Buscar serviço
                servicos = self._get_services_list()
                if not servicos:
                    return self._generate_response_with_company_prompt(
                        "verificar_disponibilidade",
                        {'error': "Não consegui buscar a lista de serviços", 'context': context},
                        context
                    )
                
                servico = self._find_service_match(data.get('procedimento'), servicos, fluxo_config.get('estrategias_match', []))
                if not servico:
                    return self._generate_response_with_company_prompt(
                        "verificar_disponibilidade",
                        {'error': f"Serviço '{data.get('procedimento')}' não encontrado", 'context': context},
                        context
                    )
                
                entidade = {'tipo': 'servico', 'dados': servico}
                logger.info(f"Serviço encontrado: {servico['nome']}")
                
            else:
                return self._generate_response_with_company_prompt(
                    "verificar_disponibilidade",
                    {'error': "Tipo de busca não suportado", 'context': context},
                    context
                )
    
            # PASSO 4: Match inteligente (já feito)
            logger.info("PASSO 4: Match inteligente realizado ✓")
            
            # PASSO 5: Verificar preferência de profissional - ABORDAGEM HÍBRIDA
            logger.info("PASSO 5: Verificando preferência de profissional (ABORDAGEM HÍBRIDA)...")
            
            # ✅ DETECTAR automaticamente se o usuário já indicou preferência
            if data.get('profissional') and data.get('profissional') != 'indiferente':
                logger.info(f"✅ Usuário já indicou preferência: {data.get('profissional')}")
                # Continuar com busca específica para este profissional
            else:
                # ✅ IMPLEMENTAR ABORDAGEM HÍBRIDA: Buscar para TODOS os profissionais
                logger.info("🎯 ABORDAGEM HÍBRIDA: Usuário sem preferência específica, buscando para TODOS os profissionais")
                
                if entidade['tipo'] == 'servico':
                    # Buscar disponibilidade de todos os profissionais para este serviço
                    return self._check_availability_for_all_professionals(entidade['dados'], data.get('data'), context)
                else:
                    # Se for por profissional mas sem serviço, perguntar procedimento
                    return self._generate_response_with_company_prompt(
                        "perguntar_procedimento",
                        {
                            'profissional': entidade['dados']['nome'],
                            'data': data.get('data'),
                            'context': context
                        },
                        context
                    )
            
            # PASSO 6: Buscar disponibilidade por serviço
            logger.info("PASSO 6: Buscando disponibilidade por serviço...")
            
            # IMPORTANTE: Sempre precisamos do serviço para buscar disponibilidade
            servico_id = None
            profissional_id = None
            
            if entidade['tipo'] == 'servico':
                servico_id = entidade['dados']['id']
                profissional_id = data.get('profissional_id') if data.get('profissional_id') else None
            else:  # por_profissional
                if 'servico' in entidade:
                    servico_id = entidade['servico']['id']
                    profissional_id = entidade['dados']['id']
                else:
                    # Se não temos serviço, perguntar ao usuário
                    return self._generate_response_with_company_prompt(
                        "perguntar_procedimento",
                        {
                            'profissional': entidade['dados']['nome'],
                            'data': data.get('data'),
                            'context': context
                        },
                        context
                    )
            
            # IMPORTANTE: Sempre usar o novo método _get_service_availability
            logger.info(f"Chamando _get_service_availability com servico_id={servico_id}, data={data.get('data')}, profissional_id={profissional_id}")
            disponibilidade = self._get_service_availability(servico_id, data.get('data'), profissional_id)
            
            if not disponibilidade:
                return self._generate_response_with_company_prompt(
                    "verificar_disponibilidade",
                    {
                        'error': f"Não há horários disponíveis para {entidade['dados']['nome']} em {data.get('data')}",
                        'context': context
                    },
                    context
                )
            
            # PASSO 7: Validar slots por duração (SEMPRE executar!)
            logger.info("PASSO 7: Validando slots por duração...")
            
            # Obter duração do procedimento
            procedure_duration = api_rules_engine.get_procedure_duration(
                entidade.get('servico', entidade['dados'])['nome'], 
                context.get('empresa_config', {}),
                entidade.get('servico', entidade['dados'])  # Passar informações completas do serviço
            )
            logger.info(f"Duração do procedimento '{entidade.get('servico', entidade['dados'])['nome']}': {procedure_duration} min")
            
            # Filtrar slots baseado na duração
            available_slots = disponibilidade.get('horariosVagos', [])
            if available_slots:
                # Converter horários para formato de slots
                slots_data = [{'horario': slot, 'disponivel': True} for slot in available_slots]
                
                # Aplicar validação de slots consecutivos
                valid_slots = api_rules_engine.filter_available_slots_by_duration(
                    slots_data, 
                    procedure_duration, 
                    context.get('empresa_config', {})
                )
                
                if valid_slots:
                    logger.info(f"Slots válidos encontrados: {len(valid_slots)}")
                    # Converter de volta para horários
                    valid_horarios = [slot['horario_inicio'] for slot in valid_slots]
                    disponibilidade['horariosVagos'] = valid_horarios
                else:
                    logger.warning(f"Nenhum slot válido encontrado para procedimento de {procedure_duration} min")
                    return self._generate_response_with_company_prompt(
                        "verificar_disponibilidade",
                        {
                            'error': f"Não há horários com slots consecutivos suficientes para '{entidade.get('servico', entidade['dados'])['nome']}' ({procedure_duration} min) em {data.get('data')}",
                            'context': context
                        },
                        context
                    )
            
            # PASSO 8: Retornar slots
            logger.info("PASSO 8: Formatando resposta com prompt da empresa...")
            return self._generate_response_with_company_prompt(
                "verificar_disponibilidade",
                {
                    'professional': entidade['dados']['nome'],
                    'date': data.get('data'),
                    'horarios': disponibilidade.get('horariosVagos', []),
                    'intervalos': disponibilidade.get('intervalosVagos', [])
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
    
    def _execute_reservation_creation(self, data: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Executa criação de reserva"""
        try:
            # Verificar campos obrigatórios
            required_fields = ['profissional', 'data', 'horario', 'cliente']
            missing_fields = [field for field in required_fields if not data.get(field)]
            
            if missing_fields:
                return f"Para agendar, preciso das seguintes informações: {', '.join(missing_fields)}"
            
            # Aqui implementaríamos a criação real da reserva
            # Usar prompt da empresa para formatar resposta
            return self._generate_response_with_company_prompt(
                "agendar_consulta",
                data,
                context
            )
            
        except Exception as e:
            logger.error(f"Erro ao criar reserva: {e}")
            return "Desculpe, não consegui criar a reserva no momento."
    
    def _execute_reservation_cancellation(self, data: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Executa cancelamento de reserva"""
        try:
            if not data.get('data'):
                return "Preciso saber a data da consulta para cancelar."
            
            # Usar prompt da empresa para formatar resposta
            return self._generate_response_with_company_prompt(
                "cancelar_consulta",
                data,
                context
            )
            
        except Exception as e:
            logger.error(f"Erro ao cancelar reserva: {e}")
            return "Desculpe, não consegui cancelar a reserva no momento."
    
    def _execute_reservation_reschedule(self, data: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Executa reagendamento de reserva"""
        try:
            if not data.get('data_atual') or not data.get('nova_data'):
                return "Desculpe, preciso saber a data atual e a nova data para reagendar."
            
            # Usar prompt da empresa para formatar resposta
            return self._generate_response_with_company_prompt(
                "reagendar_consulta",
                data,
                context
            )
            
        except Exception as e:
            logger.error(f"Erro ao reagendar reserva: {e}")
            return "Desculpe, não consegui reagendar a reserva no momento."
    
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
            logger.info(f"LLM fazendo match inteligente para '{nome_procurado}' entre {len(profissionais)} profissionais")
            
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
                
                # Log de TODOS os serviços para debug completo
                if servicos:
                    logger.info(f"📋 TODOS os {len(servicos)} serviços retornados pela API:")
                    for i, servico in enumerate(servicos):
                        nome = servico.get('nome', 'N/A')
                        categoria = servico.get('categoria', 'N/A')
                        duracao = servico.get('duracaoEmMinutos', 'N/A')
                        visivel = servico.get('somenteVisiveisCliente', 'N/A')
                        logger.info(f"   {i+1:3d}. {nome} | Categoria: {categoria} | Duração: {duracao}min | Visível: {visivel}")
                    
                    # Log de todas as categorias disponíveis
                    categorias = set(serv.get('categoria', 'Sem categoria') for serv in servicos)
                    logger.info(f"🏷️  Categorias disponíveis: {sorted(list(categorias))}")
                    
                    # Procurar por serviços que contenham "limpeza" ou "pele"
                    logger.info("🔍 Procurando por serviços com 'limpeza' ou 'pele'...")
                    servicos_limpeza = []
                    for serv in servicos:
                        nome = serv.get('nome', '').lower()
                        if 'limpeza' in nome or 'pele' in nome:
                            servicos_limpeza.append(serv)
                    
                    if servicos_limpeza:
                        logger.info(f"✅ Encontrados {len(servicos_limpeza)} serviços relacionados:")
                        for serv in servicos_limpeza:
                            logger.info(f"   - {serv.get('nome')} (ID: {serv.get('id')})")
                    else:
                        logger.info("❌ Nenhum serviço encontrado com 'limpeza' ou 'pele'")
                    
                    # Mostrar TODOS os serviços da categoria "Estética Facial"
                    logger.info("🔍 TODOS os serviços da categoria 'Estética Facial':")
                    servicos_facial = [s for s in servicos if s.get('categoria') == 'Estética Facial']
                    if servicos_facial:
                        for serv in servicos_facial:
                            logger.info(f"   - {serv.get('nome')} (ID: {serv.get('id')}) | Duração: {serv.get('duracaoEmMinutos', 'N/A')}min")
                    else:
                        logger.info("   Nenhum serviço encontrado na categoria 'Estética Facial'")
                
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
            
            logger.info(f"DEBUG: Endpoint={endpoint}, Params={params}")
            result = self._call_trinks_api(endpoint, params)
            
            if result and not result.get('error'):
                # Processar dados da API para extrair disponibilidade
                logger.info(f"DEBUG: Dados brutos da API: {result}")
                
                # Extrair dados do profissional específico se filtrado
                if profissional_id:
                    for prof in result.get('data', []):
                        if str(prof.get('id')) == str(profissional_id):
                            logger.info(f"DEBUG: Profissional encontrado: {prof}")
                            return {
                                'horariosVagos': prof.get('horariosVagos', []),
                                'intervalosVagos': prof.get('intervalosVagos', []),
                                'profissional': prof
                            }
                
                # Se não filtrado por profissional, retornar todos
                logger.info(f"DEBUG: Retornando dados para todos os profissionais")
                return {
                    'horariosVagos': result.get('data', []),
                    'intervalosVagos': [],
                    'profissionais': result.get('data', [])
                }
            
            logger.warning(f"DEBUG: API retornou erro ou dados vazios: {result}")
            return {}
            
        except Exception as e:
            logger.error(f"Erro ao buscar disponibilidade do serviço: {e}")
            return {}
    
    def _find_service_match(self, nome_procurado: str, servicos: List[Dict], estrategias: List[str]) -> Dict[str, Any]:
        """Usa LLM para fazer match inteligente entre nome procurado e lista de serviços"""
        try:
            logger.info(f"🤖 LLM fazendo match inteligente de serviço para '{nome_procurado}' entre {len(servicos)} serviços")
            logger.info(f"📊 Serviços que serão analisados pelo LLM:")
            for i, serv in enumerate(servicos[:5]):  # Mostrar apenas os primeiros 5 para não poluir o log
                logger.info(f"   {i+1}. {serv.get('nome', 'N/A')} | Categoria: {serv.get('categoria', 'N/A')}")
            if len(servicos) > 5:
                logger.info(f"   ... e mais {len(servicos) - 5} serviços")
            
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
        """Gera resposta personalizada usando o prompt da empresa para qualquer tipo de ação"""
        
        # Obter prompt da empresa
        company_prompt = self.empresa_config.get('prompt', '')
        company_name = self.empresa_config.get('nome', 'Empresa')
        
        # Preparar dados para o LLM
        system_prompt = f"""Você é um assistente virtual da {company_name}.

PROMPT DA EMPRESA:
{company_prompt if company_prompt else 'Responda de forma profissional e amigável.'}

INSTRUÇÕES:
- Use o tom de voz e estilo definidos no prompt da empresa
- Siga as regras sobre o que falar e o que não falar
- Mantenha a identidade da empresa
- Seja consistente com o estilo de comunicação

TIPO DE AÇÃO: {action_type}

DADOS DISPONÍVEIS:
{json.dumps(data, indent=2, ensure_ascii=False)}

RESPONDA de acordo com o prompt da empresa, formatando a resposta de forma clara e profissional."""
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Formate uma resposta para {action_type} usando os dados fornecidos e seguindo o prompt da empresa.")
            ]
            
            response = self.llm.invoke(messages)
            logger.info(f"Resposta gerada com prompt da empresa para {action_type}")
            return response.content.strip()
            
        except Exception as e:
            logger.error(f"Erro ao gerar resposta com prompt da empresa: {e}")
            # Fallback para resposta padrão
            return self._generate_fallback_response(action_type, data)
    
    def _generate_fallback_response(self, action_type: str, data: Dict[str, Any]) -> str:
        """Gera resposta de fallback quando o prompt da empresa falha"""
        
        if action_type == "verificar_disponibilidade":
            professional = data.get('professional', 'Profissional')
            date = data.get('date', 'Data')
            horarios = data.get('horarios', [])
            intervalos = data.get('intervalos', [])
            
            if horarios or intervalos:
                response = f"✅ Horários disponíveis para {professional}:\n\n"
                
                if horarios:
                    response += "🕐 Horários específicos:\n"
                    for horario in horarios:
                        response += f"• {horario}\n"
                    response += "\n"
                
                if intervalos:
                    response += "⏰ Intervalos disponíveis:\n"
                    for intervalo in intervalos:
                        response += f"• {intervalo.get('inicio', '')} - {intervalo.get('fim', '')}\n"
                
                response += f"\n📅 Data: {date}"
                return response
            else:
                return f"Infelizmente a {professional} não tem horários disponíveis para {date}."
        
        elif action_type == "perguntar_preferencia_profissional":
            servico = data.get('servico', 'serviço')
            data_str = data.get('data', 'data')
            profissionais_count = data.get('profissionais_disponiveis', 0)
            return f"Perfeito! Encontrei o serviço '{servico}' e {profissionais_count} profissionais disponíveis para {data_str}. Tem algum profissional específico em mente, ou posso mostrar a disponibilidade de todos?"
        
        elif action_type == "perguntar_procedimento":
            profissional = data.get('profissional', 'profissional')
            data_str = data.get('data', 'data')
            return f"Perfeito! Encontrei a {profissional} disponível para {data_str}. Qual procedimento você gostaria de agendar?"
        
        elif action_type == "agendar_consulta":
            return f"Perfeito! Vou agendar sua consulta com {data.get('profissional', 'profissional')} para {data.get('data', 'data')} às {data.get('horario', 'horário')}."
        
        elif action_type == "cancelar_consulta":
            return f"Vou cancelar sua consulta de {data.get('data', 'data')}. Confirma o cancelamento?"
        
        elif action_type == "reagendar_consulta":
            return f"Vou reagendar sua consulta de {data.get('data_atual', 'data atual')} para {data.get('nova_data', 'nova data')}."
        
        else:
            return f"Ação '{action_type}' processada com sucesso." 
    
    def _get_conversation_state(self, waid: str) -> Dict[str, Any]:
        """Obtém o estado atual da conversa para um waid específico"""
        if not hasattr(self, '_conversation_states'):
            self._conversation_states = {}
        
        if waid not in self._conversation_states:
            self._conversation_states[waid] = {
                'profissional': None,
                'procedimento': None,
                'data': None,
                'horario': None,
                'servico': None,
                'preferencia_profissional': None,
                'last_update': None
            }
        
        return self._conversation_states[waid]
    
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
                
                if disponibilidade and disponibilidade.get('horariosVagos'):
                    # Obter duração do procedimento para validação
                    procedure_duration = api_rules_engine.get_procedure_duration(
                        servico['nome'], 
                        context.get('empresa_config', {}),
                        servico
                    )
                    
                    # Validar slots por duração
                    available_slots = disponibilidade.get('horariosVagos', [])
                    if available_slots:
                        slots_data = [{'horario': slot, 'disponivel': True} for slot in available_slots]
                        valid_slots = api_rules_engine.filter_available_slots_by_duration(
                            slots_data, 
                            procedure_duration, 
                            context.get('empresa_config', {})
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