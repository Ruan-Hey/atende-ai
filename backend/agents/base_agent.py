from langchain.agents import initialize_agent, AgentType
from langchain_openai import OpenAI, ChatOpenAI
from langchain.memory import ConversationBufferWindowMemory
from langchain.tools import Tool
from langchain_core.tools import tool as lc_tool
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage
from typing import Dict, Any, List
import logging
from models import API

logger = logging.getLogger(__name__)

class BaseAgent:
    """Agent base para processamento de mensagens"""
    
    def __init__(self, empresa_config: Dict[str, Any]):
        self.empresa_config = empresa_config
        self.llm = OpenAI(
            api_key=empresa_config.get('openai_key'),
            temperature=0.1,
            max_tokens=500
        )
        # Chat model para tool-calling (mais determinístico)
        self.chat_llm = ChatOpenAI(
            api_key=empresa_config.get('openai_key'),
            temperature=0.0,
            model="gpt-4o"
        )
        self.memory = ConversationBufferWindowMemory(
            k=20,
            return_messages=True
        )
        self.current_context: Dict[str, Any] = {}
        self.tools = self._setup_tools()
        
        # Guardar referências para wrappers ANTES de criar structured_tools
        self._wrappers = {
            "buscar_cliente": self._get_buscar_cliente_wrapper(),
            "verificar_calendario": self._get_verificar_calendario_wrapper(),
            "fazer_reserva": self._get_fazer_reserva_wrapper(),
            "enviar_mensagem": self._get_enviar_mensagem_wrapper(),
        }
        
        # Cache simples em memória por execução
        self._knowledge_cache: Dict[str, str] = {}
        
        # Adicionar wrapper de conhecimento de negócios
        def _get_business_knowledge_wrapper():
            def wrapper(key: str) -> str:
                try:
                    if not key:
                        return "Parâmetros ausentes: forneça key"
                    cache_key = f"{self.empresa_config.get('empresa_id')}::knowledge::{key}"
                    if cache_key in self._knowledge_cache:
                        return self._knowledge_cache[cache_key]
                    knowledge = self.empresa_config.get('knowledge_json') or {}
                    items = knowledge.get('items') if isinstance(knowledge, dict) else []
                    if not isinstance(items, list):
                        items = []
                    # Matching por key exata; fallback por title case-insensitive
                    found = None
                    for it in items:
                        if isinstance(it, dict) and it.get('key') == key:
                            found = it
                            break
                    if not found:
                        for it in items:
                            if isinstance(it, dict) and it.get('title', '').strip().lower() == key.strip().lower():
                                found = it
                                break
                    if not found and isinstance(key, str):
                        # aliases opcionais
                        for it in items:
                            aliases = it.get('aliases', []) if isinstance(it, dict) else []
                            if isinstance(aliases, list) and any(a.strip().lower() == key.strip().lower() for a in aliases if isinstance(a, str)):
                                found = it
                                break
                    if not found:
                        return ""
                    desc = found.get('description') or ""
                    self._knowledge_cache[cache_key] = desc
                    return desc
                except Exception:
                    return ""
            return wrapper
        self._wrappers["get_business_knowledge"] = _get_business_knowledge_wrapper()
        
        # Tools estruturadas para tool-calling nativo
        self.structured_tools = self._setup_structured_tools()
        self.agent = self._create_agent()
    
    def _setup_tools(self) -> List[Tool]:
        """Configura as ferramentas disponíveis para o agent"""
        from tools.cliente_tools import ClienteTools
        from tools.calendar_tools import CalendarTools
        from tools.message_tools import MessageTools
        import json
        
        cliente_tools = ClienteTools()
        calendar_tools = CalendarTools()
        message_tools = MessageTools()
        
        # Wrappers que aceitam string (JSON) e usam contexto/empresa_config
        def _parse_json(tool_input: str) -> Dict[str, Any]:
            try:
                return json.loads(tool_input) if isinstance(tool_input, str) else (tool_input or {})
            except Exception:
                return {}
        
        def buscar_cliente_wrapper(tool_input: str = None, **kwargs) -> str:
            # Aceitar tanto tool_input quanto kwargs
            if tool_input:
                data = _parse_json(tool_input)
            else:
                data = kwargs
            
            cliente_id = data.get('cliente_id') or self.current_context.get('cliente_id')
            empresa_id = self.empresa_config.get('empresa_id')
            if not cliente_id or not empresa_id:
                return "Parâmetros ausentes: forneça {'cliente_id': '...'}; empresa_id vem do contexto."
            return cliente_tools.buscar_cliente_info(cliente_id, int(empresa_id))
        
        def verificar_calendario_wrapper(tool_input: str = None, **kwargs) -> str:
            # Aceitar tanto tool_input quanto kwargs
            if tool_input:
                data = _parse_json(tool_input)
            else:
                data = kwargs
            
            data_str = data.get('data') or data.get('date')
            if not data_str:
                return "Parâmetros ausentes: forneça {'data': 'YYYY-MM-DD'}"
            return calendar_tools.verificar_disponibilidade(data_str, self.empresa_config)
        
        def fazer_reserva_wrapper(tool_input: str = None, **kwargs) -> str:
            # Aceitar tanto tool_input quanto kwargs
            if tool_input:
                data = _parse_json(tool_input)
            else:
                data = kwargs
            
            data_str = data.get('data') or data.get('date')
            hora = data.get('hora') or data.get('time')
            email = data.get('email') or data.get('cliente_email')
            cliente = data.get('cliente') or data.get('customer') or self.current_context.get('cliente_name') or 'Cliente'
            if not data_str or not hora:
                return "Parâmetros ausentes: forneça {'data': 'YYYY-MM-DD', 'hora': 'HH:MM', 'cliente': 'Nome', 'email': 'email@cliente'}"
            return calendar_tools.fazer_reserva(data_str, hora, cliente, self.empresa_config, email=email)
        
        def enviar_mensagem_wrapper(tool_input: str = None, **kwargs) -> str:
            # Aceitar tanto tool_input quanto kwargs
            if tool_input:
                data = _parse_json(tool_input)
            else:
                data = kwargs
            
            mensagem = data.get('mensagem') or data.get('message') or (tool_input if isinstance(tool_input, str) else None)
            cliente_id = data.get('cliente_id') or self.current_context.get('cliente_id')
            if not mensagem or not cliente_id:
                return "Parâmetros ausentes: forneça {'mensagem': '...', 'cliente_id': '...'}"
            return message_tools.enviar_resposta(mensagem, cliente_id, self.empresa_config, canal=self.current_context.get('channel', 'whatsapp'))
        
        def get_business_knowledge_wrapper(tool_input: str = None, **kwargs) -> str:
            # Aceitar tanto tool_input quanto kwargs
            data = _parse_json(tool_input) if tool_input else kwargs
            key = data.get('key') or data.get('titulo') or data.get('title')
            return self._wrappers["get_business_knowledge"](key)
        
        # Tools básicas (modo compatibilidade com AgentExecutor)
        tools = [
            Tool(
                name="buscar_cliente",
                func=buscar_cliente_wrapper,
                description="Busca informações do cliente no banco de dados. Use quando precisar de dados do cliente. Entrada: JSON {'cliente_id': '...'}"
            ),
            Tool(
                name="verificar_calendario",
                func=verificar_calendario_wrapper,
                description="Verifica disponibilidade real no Google Calendar/Trinks/outros. Entrada: JSON {'data': 'YYYY-MM-DD'}"
            ),
            Tool(
                name="fazer_reserva",
                func=fazer_reserva_wrapper,
                description="Faz reserva real na agenda disponível e envia convite se 'email' for informado. Entrada: JSON {'data': 'YYYY-MM-DD', 'hora': 'HH:MM', 'cliente': 'Nome', 'email': 'email@cliente'}"
            ),
            Tool(
                name="enviar_mensagem",
                func=enviar_mensagem_wrapper,
                description="Envia mensagem pelo canal apropriado. Entrada: JSON {'mensagem': '...', 'cliente_id': '...'}"
            ),
            Tool(
                name="get_business_knowledge",
                func=get_business_knowledge_wrapper,
                description="Retorna um texto curto a partir do conhecimento da empresa. Entrada: JSON {'key': 'slug ou título'}"
            )
        ]
        
        # Adicionar Tools das APIs conectadas
        tools.extend(self._get_api_tools())
        
        return tools
    
    def _get_buscar_cliente_wrapper(self):
        """Retorna wrapper para buscar_cliente"""
        from tools.cliente_tools import ClienteTools
        cliente_tools = ClienteTools()
        
        def wrapper(cliente_id: str = None, **kwargs) -> str:
            cliente_id = cliente_id or self.current_context.get('cliente_id')
            empresa_id = self.empresa_config.get('empresa_id')
            if not cliente_id or not empresa_id:
                return "Parâmetros ausentes: forneça cliente_id; empresa_id vem do contexto."
            return cliente_tools.buscar_cliente_info(cliente_id, int(empresa_id))
        return wrapper
    
    def _get_verificar_calendario_wrapper(self):
        """Retorna wrapper para verificar_calendario"""
        from tools.calendar_tools import CalendarTools
        calendar_tools = CalendarTools()
        
        def wrapper(data: str = None, **kwargs) -> str:
            data_str = data or kwargs.get('data') or kwargs.get('date')
            if not data_str:
                return "Parâmetros ausentes: forneça data no formato YYYY-MM-DD"
            return calendar_tools.verificar_disponibilidade(data_str, self.empresa_config)
        return wrapper
    
    def _get_fazer_reserva_wrapper(self):
        """Retorna wrapper para fazer_reserva"""
        from tools.calendar_tools import CalendarTools
        calendar_tools = CalendarTools()
        
        def wrapper(data: str = None, hora: str = None, cliente: str = None, email: str = None, **kwargs) -> str:
            data_str = data or kwargs.get('data') or kwargs.get('date')
            hora_str = hora or kwargs.get('hora') or kwargs.get('time')
            email_str = email or kwargs.get('email') or kwargs.get('cliente_email')
            cliente_str = cliente or kwargs.get('cliente') or kwargs.get('customer') or self.current_context.get('cliente_name') or 'Cliente'
            if not data_str or not hora_str:
                return "Parâmetros ausentes: forneça data (YYYY-MM-DD) e hora (HH:MM)"
            return calendar_tools.fazer_reserva(data_str, hora_str, cliente_str, self.empresa_config, email=email_str)
        return wrapper
    
    def _get_enviar_mensagem_wrapper(self):
        """Retorna wrapper para enviar_mensagem"""
        from tools.message_tools import MessageTools
        message_tools = MessageTools()
        
        def wrapper(mensagem: str = None, cliente_id: str = None, **kwargs) -> str:
            mensagem_str = mensagem or kwargs.get('mensagem') or kwargs.get('message')
            cliente_id_str = cliente_id or kwargs.get('cliente_id') or self.current_context.get('cliente_id')
            if not mensagem_str or not cliente_id_str:
                return "Parâmetros ausentes: forneça mensagem e cliente_id"
            return message_tools.enviar_resposta(mensagem_str, cliente_id_str, self.empresa_config, canal=self.current_context.get('channel', 'whatsapp'))
        return wrapper
    
    def _setup_structured_tools(self):
        """Cria StructuredTools com assinaturas tipadas para tool-calling nativo"""
        from typing import Optional
        import json
        structured = []
        
        @lc_tool("buscar_cliente")
        def t_buscar_cliente(cliente_id: str) -> str:
            """Busca informações do cliente no banco de dados usando o ID fornecido."""
            return self._wrappers["buscar_cliente"](cliente_id=cliente_id)
        structured.append(t_buscar_cliente)
        
        @lc_tool("verificar_calendario")
        def t_verificar_calendario(data: str) -> str:
            """Verifica disponibilidade no calendário para a data especificada (formato YYYY-MM-DD)."""
            return self._wrappers["verificar_calendario"](data=data)
        structured.append(t_verificar_calendario)
        
        @lc_tool("fazer_reserva")
        def t_fazer_reserva(data: str, hora: str, cliente: str, email: str = "") -> str:
            """Faz uma reserva no calendário (envia convite se email for informado)."""
            return self._wrappers["fazer_reserva"](data=data, hora=hora, cliente=cliente, email=email)
        structured.append(t_fazer_reserva)
        
        @lc_tool("enviar_mensagem")
        def t_enviar_mensagem(mensagem: str, cliente_id: str) -> str:
            """Envia uma mensagem para o cliente especificado."""
            return self._wrappers["enviar_mensagem"](mensagem=mensagem, cliente_id=cliente_id)
        structured.append(t_enviar_mensagem)
        
        @lc_tool("get_business_knowledge")
        def t_get_business_knowledge(key: str) -> str:
            """Retorna texto curto de conhecimento da empresa para a chave informada (slug ou título)."""
            return self._wrappers["get_business_knowledge"](key)
        structured.append(t_get_business_knowledge)
        
        # Adicionar StructuredTools dinâmicos para APIs conectadas
        from tools.api_tools import APITools
        for key, value in self.empresa_config.items():
            if key.endswith('_enabled') and value is True:
                api_name = key.replace('_enabled', '').replace('_', ' ').title()
                config_key = f"{key.replace('_enabled', '')}_config"
                api_config = self.empresa_config.get(config_key, {})
                if not api_config:
                    continue
                tool_name = f"{api_name.lower().replace(' ', '_')}_api_call"
                
                # Criar wrapper e registrar em _wrappers para o loop de execução
                def _make_dyn_wrapper(api_name_local: str, api_config_local: dict):
                    def wrapper(endpoint_path: str, method: str = "GET", params_json: str = "") -> str:
                        try:
                            api_tools = APITools()
                            extra = {}
                            if params_json:
                                try:
                                    extra = json.loads(params_json)
                                except Exception:
                                    # Se não foi um JSON válido, ignore e não quebre a execução
                                    extra = {}
                            return api_tools.call_api(
                                api_name=api_name_local,
                                endpoint_path=endpoint_path,
                                method=method,
                                config=api_config_local,
                                **extra
                            )
                        except Exception as e:
                            return f"Erro ao chamar API {api_name_local}: {str(e)}"
                    return wrapper
                self._wrappers[tool_name] = _make_dyn_wrapper(api_name, api_config)
                
                @lc_tool(tool_name)
                def t_dynamic_api_call(endpoint_path: str, method: str = "GET", params_json: str = "") -> str:  # type: ignore
                    """Chama dinamicamente um endpoint da API conectada à empresa."""
                    return self._wrappers[tool_name](endpoint_path=endpoint_path, method=method, params_json=params_json)
                structured.append(t_dynamic_api_call)
        
        return structured
    
    def _get_api_tools(self) -> List[Tool]:
        """Gera Tools automaticamente das APIs conectadas usando empresa_config"""
        from tools.api_tools import APITools
        
        tools = []
        
        try:
            # Buscar todas as APIs ativas no empresa_config
            for key, value in self.empresa_config.items():
                if key.endswith('_enabled') and value is True:
                    # Extrair nome da API do prefixo
                    api_name = key.replace('_enabled', '').replace('_', ' ').title()
                    
                    # Buscar configuração da API
                    config_key = f"{key.replace('_enabled', '')}_config"
                    api_config = self.empresa_config.get(config_key, {})
                    
                    if api_config:
                        # Criar Tool genérica para a API
                        tool = self._create_generic_api_tool(api_name, api_config)
                        if tool:
                            tools.append(tool)
        
        except Exception as e:
            logger.error(f"Erro ao gerar Tools das APIs: {e}")
        
        return tools
    
    def _create_generic_api_tool(self, api_name: str, config: dict) -> Tool:
        """Cria uma Tool genérica para uma API"""
        try:
            from tools.api_tools import APITools
            
            # Criar função dinâmica
            def api_call(endpoint_path: str, method: str = "GET", **kwargs):
                api_tools = APITools()
                return api_tools.call_api(
                    api_name=api_name,
                    endpoint_path=endpoint_path,
                    method=method,
                    config=config,
                    **kwargs
                )
            
            # Gerar descrição
            description = f"Chama endpoints da API {api_name}. Use endpoint_path para especificar o caminho e method para o método HTTP (GET, POST, PUT, DELETE)."
            
            return Tool(
                name=f"{api_name.lower().replace(' ', '_')}_api_call",
                func=api_call,
                description=description
            )
            
        except Exception as e:
            logger.error(f"Erro ao criar Tool genérica para {api_name}: {e}")
            return None
    
    def _create_agent(self):
        """Cria o agent com as ferramentas configuradas (modo legado). Protegido por try/except."""
        try:
            return initialize_agent(
                tools=self.tools,
                llm=self.llm,
                agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                memory=self.memory,
                verbose=True,
                handle_parsing_errors=True
            )
        except Exception as e:
            logger.warning(f"Falha ao criar agent legado (seguindo apenas com tool-calling nativo): {e}")
            return None
    
    async def process_message(self, message: str, context: Dict[str, Any]) -> str:
        """Processa uma mensagem usando tool-calling: executa tools antes de responder"""
        try:
            # Adicionar data atual ao contexto
            from datetime import datetime, timedelta
            current_date = datetime.now().strftime('%Y-%m-%d')
            current_time = datetime.now().strftime('%H:%M')
            
            # Atualizar contexto com informações de data/hora
            context.update({
                'current_date': current_date,
                'current_time': current_time,
                'current_datetime': datetime.now().isoformat()
            })
            
            # Atualizar contexto atual
            self.current_context = context
            
            # Construir prompt do sistema (reforça usar tools antes de responder)
            system_prompt = self._build_system_prompt(context)
            
            # Mensagens iniciais
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=message)
            ]
            
            # Adicionar histórico de conversa da memória
            if hasattr(self.memory, 'chat_memory') and self.memory.chat_memory.messages:
                # Inserir mensagens do histórico entre SystemMessage e HumanMessage atual
                # Pegar as últimas 10 mensagens para manter contexto sem sobrecarregar
                history_messages = self.memory.chat_memory.messages[-10:]
                messages[1:1] = history_messages
            
            # Chat com ferramentas (tool calling nativo)
            llm_with_tools = self.chat_llm.bind_tools(self.structured_tools)
            
            # Loop de execução de tools até chegar na resposta final
            safety_counter = 0
            ai_response: AIMessage = await llm_with_tools.ainvoke(messages)
            
            while isinstance(ai_response, AIMessage) and getattr(ai_response, 'tool_calls', None):
                safety_counter += 1
                if safety_counter > 6:
                    logger.warning("Limite de tool-calls atingido; encerrando com última resposta do modelo")
                    break
                
                # Acrescenta a própria mensagem do modelo que solicitou ferramentas
                messages.append(ai_response)
                
                # Executa cada tool solicitada e anexa ToolMessage com o resultado
                for tool_call in ai_response.tool_calls:
                    tool_name = tool_call.get('name')
                    tool_args = tool_call.get('args', {}) or {}
                    tool_call_id = tool_call.get('id')
                    try:
                        logger.info(f"Tool requested: {tool_name} args={tool_args}")
                        if tool_name in self._wrappers:
                            tool_result = self._wrappers[tool_name](**tool_args)
                        else:
                            tool_result = f"Tool {tool_name} não encontrada"
                        # Logar resultado (limitado)
                        result_preview = str(tool_result)
                        if len(result_preview) > 800:
                            result_preview = result_preview[:800] + "... [truncated]"
                        logger.info(f"Tool result ({tool_name}): {result_preview}")
                    except Exception as e:
                        tool_result = f"Erro ao executar tool {tool_name}: {str(e)}"
                        logger.error(tool_result)
                    messages.append(ToolMessage(content=str(tool_result), tool_call_id=tool_call_id))
                
                # Após fornecer resultados das tools, o modelo deve formular a resposta final
                ai_response = await llm_with_tools.ainvoke(messages)
            
            final_text = ai_response.content if isinstance(ai_response, AIMessage) else str(ai_response)
            logger.info(f"Final response: {final_text}")
            
            # Salvar na memória
            self.memory.save_context(
                {"input": message},
                {"output": final_text}
            )
            
            return final_text
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}")
            return f"Desculpe, tive um problema técnico: {str(e)}"
    
    def _build_system_prompt(self, context: Dict[str, Any]) -> str:
        """Constrói o prompt do sistema com contexto da empresa"""
        empresa_config = self.empresa_config
        
        # Informações da empresa
        empresa_nome = empresa_config.get('nome', 'Empresa')
        empresa_slug = empresa_config.get('slug', 'empresa')
        prompt_empresa = empresa_config.get('prompt', '')
        
        # Informações do cliente
        cliente_id = context.get('cliente_id', 'Cliente')
        cliente_name = context.get('cliente_name', 'Cliente')
        cliente_info = context.get('cliente_info', {}).get('info', '')
        
        # Informações de data/hora
        current_date = context.get('current_date', 'Data atual não disponível')
        current_time = context.get('current_time', 'Hora atual não disponível')
        
        # Verificar se Google Calendar está configurado
        google_calendar_enabled = empresa_config.get('google_calendar_enabled', False)
        google_calendar_client_id = empresa_config.get('google_calendar_client_id')
        google_calendar_refresh_token = empresa_config.get('google_calendar_refresh_token')
        
        calendar_status = "✅ Google Calendar configurado e funcionando" if (google_calendar_enabled and google_calendar_client_id and google_calendar_refresh_token) else "❌ Google Calendar não configurado"
        
        # Listar APIs dinâmicas conectadas
        dynamic_api_list = []
        for key, value in empresa_config.items():
            if key.endswith('_enabled') and value is True:
                api_name = key.replace('_enabled', '').replace('_', ' ').title()
                if api_name not in ["Google Calendar", "Openai", "Google Sheets"]:
                    dynamic_api_list.append(api_name)
        dynamic_tools_info = "\n".join([f"- {api}: use a tool {api.lower().replace(' ', '_')}_api_call" for api in dynamic_api_list]) or "(nenhuma)"
        
        system_prompt = f"""Você é um assistente virtual da {empresa_nome}.

INFORMAÇÕES ATUAIS:
- Data atual: {current_date}
- Hora atual: {current_time}
- Cliente: {cliente_name} (ID: {cliente_id})
- Status do calendário: {calendar_status}

INFORMAÇÕES DO CLIENTE:
{cliente_info}

FERRAMENTAS DISPONÍVEIS:
1. buscar_cliente - Busca informações do cliente
2. verificar_calendario - Verifica disponibilidade real no Google Calendar
3. fazer_reserva - Faz reserva real na agenda (e envia convite ao cliente)
4. enviar_mensagem - Envia mensagem
5. get_business_knowledge - Consulta informações específicas da empresa (horários, regras, promoções, etc.) - Use quando o cliente perguntar sobre horários de funcionamento, regras, promoções ou outras informações da empresa
APIs dinâmicas conectadas (tool genérica):
{dynamic_tools_info}

INSTRUÇÕES IMPORTANTES (POLÍTICA DE DECISÃO):
- Quando o cliente pedir para agendar/confirmar um horário, extraia data e hora do contexto recente e chame a ferramenta apropriada.
- Se JÁ tivermos data e hora e o cliente confirmar (ex.: "pode agendar às 17h"), peça o email do cliente se ainda não tiver e então chame DIRETAMENTE a ferramenta fazer_reserva com data, hora, nome e email.
- Se faltar apenas UM dado (data, hora ou email), pergunte somente o que falta. Não repita perguntas já respondidas.
- Sempre que o cliente mencionar "hoje", use {current_date}. Para dias da semana (ex.: segunda-feira), calcule a próxima ocorrência a partir da data atual.
- Para verificar disponibilidade, use verificar_calendario (YYYY-MM-DD). Depois que o cliente escolher um horário dessa lista e fornecer o email, chame fazer_reserva.
- **IMPORTANTE**: Quando o cliente perguntar sobre horários de funcionamento, regras, promoções ou outras informações específicas da empresa, SEMPRE use a ferramenta get_business_knowledge para consultar essas informações antes de responder.
- Evite respostas longas. Priorize executar a ferramenta e responder com o resultado real.

PROMPT ESPECÍFICO DA EMPRESA:
{prompt_empresa}

Lembre-se: Use as ferramentas para fornecer informações precisas e não responda conclusões sem executar as ferramentas necessárias."""
        
        return system_prompt 