from langchain.agents import initialize_agent, AgentType
from langchain_openai import OpenAI, ChatOpenAI
from langchain.memory import ConversationBufferWindowMemory
from langchain.tools import Tool
from langchain_core.tools import tool as lc_tool
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage
from typing import Dict, Any, List
import logging
import re
import unicodedata
from ..models import API

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
            def _normalize(text: str) -> str:
                if not isinstance(text, str):
                    return ""
                # remove acentos, baixa caixa e trim
                text_nfkd = unicodedata.normalize('NFKD', text)
                text_ascii = ''.join(c for c in text_nfkd if not unicodedata.combining(c))
                return re.sub(r"\s+", " ", text_ascii).strip().lower()

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

                    key_norm = _normalize(key)

                    # 1) match por key exata (normalizada)
                    found = None
                    for it in items:
                        if not isinstance(it, dict):
                            continue
                        if _normalize(it.get('key', '')) == key_norm:
                            found = it
                            break

                    # 2) match por título exato (normalizado)
                    if not found:
                        for it in items:
                            if not isinstance(it, dict):
                                continue
                            if _normalize(it.get('title', '')) == key_norm:
                                found = it
                                break

                    # 3) match por alias exato (normalizado)
                    if not found:
                        for it in items:
                            if not isinstance(it, dict):
                                continue
                            aliases = it.get('aliases', []) if isinstance(it, dict) else []
                            aliases_norm = [_normalize(a) for a in aliases if isinstance(a, str)]
                            if key_norm in aliases_norm:
                                found = it
                                break

                    # 4) match parcial: se a key contiver palavras de 'horario de funcionamento', etc.
                    if not found:
                        # termos comuns para horário
                        horario_norms = {_normalize(t) for t in [
                            'horario de atendimento', 'horario de funcionamento', 'funcionamento', 'horarios', 'expediente',
                            'horario', 'horário de atendimento', 'horário de funcionamento'
                        ]}
                        if any(term in key_norm for term in horario_norms):
                            # preferir item cuja key/title/aliases contenham 'horario'
                            for it in items:
                                if not isinstance(it, dict):
                                    continue
                                blob = ' '.join([
                                    _normalize(it.get('key', '')),
                                    _normalize(it.get('title', '')),
                                    ' '.join([_normalize(a) for a in (it.get('aliases') or []) if isinstance(a, str)])
                                ])
                                if 'horario' in blob or 'funcionamento' in blob:
                                    found = it
                                    break

                    if not found:
                        return ""

                    desc = (found.get('description') or "").strip()
                    self._knowledge_cache[cache_key] = desc
                    return desc
                except Exception:
                    return ""
            return wrapper
        self._wrappers["get_business_knowledge"] = _get_business_knowledge_wrapper()
        
        # Tools estruturadas para tool-calling nativo
        self.structured_tools = self._setup_structured_tools()
    
    def _get_buscar_cliente_wrapper(self):
        """Retorna wrapper para buscar_cliente"""
        from ..tools.cliente_tools import ClienteTools
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
        from ..tools.calendar_tools import CalendarTools
        calendar_tools = CalendarTools()
        
        def wrapper(data: str = None, **kwargs) -> str:
            data_str = data or kwargs.get('data') or kwargs.get('date')
            if not data_str:
                return "Parâmetros ausentes: forneça data no formato YYYY-MM-DD"
            return calendar_tools.verificar_disponibilidade(data_str, self.empresa_config)
        return wrapper
    
    def _get_fazer_reserva_wrapper(self):
        """Retorna wrapper para fazer_reserva"""
        from ..tools.calendar_tools import CalendarTools
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
        from ..tools.message_tools import MessageTools
        message_tools = MessageTools()
        
        def wrapper(mensagem: str = None, cliente_id: str = None, **kwargs) -> str:
            mensagem_str = mensagem or kwargs.get('mensagem') or kwargs.get('message')
            cliente_id_str = cliente_id or kwargs.get('cliente_id') or self.current_context.get('cliente_id')
            if not mensagem_str or not cliente_id_str:
                return "Parâmetros ausentes: forneça mensagem e cliente_id"
            return message_tools.enviar_resposta(mensagem_str, cliente_id_str, self.empresa_config, canal=self.current_context.get('channel', 'whatsapp'))
        return wrapper
    
    def _setup_structured_tools(self) -> List:
        structured = []
        
        @lc_tool("buscar_cliente")
        def t_buscar_cliente(cliente_id: str) -> str:
            """Busca histórico e informações do cliente pelo ID."""
            return self._wrappers["buscar_cliente"](cliente_id=cliente_id)
        structured.append(t_buscar_cliente)
        
        # Verificar se há APIs de agenda configuradas antes de disponibilizar ferramentas de calendário
        has_calendar_api = self._has_calendar_api()
        
        if has_calendar_api:
            @lc_tool("verificar_calendario")
            def t_verificar_calendario(data: str) -> str:
                """Lista horários disponíveis reais para uma data específica no formato YYYY-MM-DD."""
                return self._wrappers["verificar_calendario"](data=data)
            structured.append(t_verificar_calendario)
            
            @lc_tool("fazer_reserva")
            def t_fazer_reserva(data: str, hora: str, nome: str, email: str) -> str:
                """Faz reserva real na agenda para uma data, hora, nome e email específicos."""
                return self._wrappers["fazer_reserva"](data=data, hora=hora, cliente=nome, email=email)
            structured.append(t_fazer_reserva)
        
        @lc_tool("enviar_mensagem")
        def t_enviar_mensagem(mensagem: str, cliente_id: str) -> str:
            """Envia uma mensagem para o cliente especificado no canal atual (ex.: WhatsApp)."""
            return self._wrappers["enviar_mensagem"](mensagem=mensagem, cliente_id=cliente_id)
        structured.append(t_enviar_mensagem)
        
        @lc_tool("get_business_knowledge")
        def t_get_business_knowledge(key: str) -> str:
            """Retorna texto curto de conhecimento da empresa para a chave informada (slug ou título)."""
            return self._wrappers["get_business_knowledge"](key)
        structured.append(t_get_business_knowledge)
        
        # Adicionar StructuredTools dinâmicos para APIs conectadas (com docstrings)
        from ..tools.api_tools import APITools
        import json
        api_tools = APITools()
        for key, value in self.empresa_config.items():
            if key.endswith('_enabled') and value is True:
                api_name = key.replace('_enabled', '').replace('_', ' ').title()
                if api_name in ["Google Calendar", "Openai", "Google Sheets"]:
                    continue
                config_key = f"{key.replace('_enabled', '')}_config"
                api_config = self.empresa_config.get(config_key, {})
                if not api_config:
                    continue
                tool_name = f"{api_name.lower().replace(' ', '_')}_api_call"

                def _make_dyn_wrapper(api_name_local: str, api_config_local: dict):
                    def wrapper(endpoint_path: str, method: str = "GET", params_json: str = "") -> str:
                        try:
                            extra = {}
                            if params_json:
                                try:
                                    extra = json.loads(params_json)
                                except Exception:
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
                    """Chama dinamicamente um endpoint da API conectada à empresa.
                    - endpoint_path: caminho do endpoint (ex.: /v1/clientes)
                    - method: método HTTP (GET, POST, PUT, DELETE)
                    - params_json: JSON com parâmetros adicionais
                    """
                    return self._wrappers[tool_name](endpoint_path=endpoint_path, method=method, params_json=params_json)
                structured.append(t_dynamic_api_call)
        
        return structured
    
    def _has_calendar_api(self) -> bool:
        """Verifica se há alguma API de agenda configurada e ativa"""
        # Verificar Google Calendar
        if (self.empresa_config.get('google_calendar_client_id') and 
            self.empresa_config.get('google_calendar_client_secret')):
            return True
        
        # Verificar Trinks
        if self.empresa_config.get('trinks_enabled') and self.empresa_config.get('trinks_config'):
            return True
        
        # Verificar outras APIs de agenda dinamicamente
        for key, value in self.empresa_config.items():
            if key.endswith('_enabled') and value is True:
                api_name = key.replace('_enabled', '').replace('_', ' ').title()
                config_key = f"{key.replace('_enabled', '')}_config"
                config = self.empresa_config.get(config_key, {})
                
                # Verificar se é uma API de agenda (por nome ou configuração)
                if any(word in api_name.lower() for word in ['calendar', 'agenda', 'booking', 'schedule', 'trinks']):
                    if config:  # Só considerar se tiver configuração
                        return True
        
        return False
    
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
                history_messages = self.memory.chat_memory.messages[-10:]
                messages[1:1] = history_messages
            
            # Heurística: se o usuário perguntar sobre horário/funcionamento, injeta conhecimento curto
            try:
                lower_msg = (message or "").lower()
                horario_terms = ["horario", "horário", "funciona", "abre", "fech", "atende", "abrem", "fecham"]
                if any(term in lower_msg for term in horario_terms):
                    desc = self._wrappers["get_business_knowledge"]("horário de funcionamento")
                    if not desc:
                        # fallback por slug comum
                        desc = self._wrappers["get_business_knowledge"]("horario-de-funcionamento")
                    if desc:
                        messages.insert(1, SystemMessage(content=f"Conhecimento da empresa (horário de funcionamento): {desc}. Responda conforme essas regras."))
            except Exception as _:
                pass
            
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
        
        # Verificar se há APIs de agenda configuradas
        has_calendar_api = self._has_calendar_api()
        calendar_status = "✅ APIs de agenda configuradas e funcionando" if has_calendar_api else "❌ Nenhuma API de agenda configurada"
        
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
2. enviar_mensagem - Envia mensagem
3. get_business_knowledge - Consulta informações específicas da empresa (horários, regras, promoções, etc.) - Use quando o cliente perguntar sobre horários de funcionamento, regras, promoções ou outras informações da empresa

{"" if has_calendar_api else "NOTA: Ferramentas de calendário (verificar_calendario, fazer_reserva) não estão disponíveis pois nenhuma API de agenda está configurada."}
{"" if has_calendar_api else "Quando clientes perguntarem sobre agendamento, informe que o sistema de reservas não está configurado e sugira que entrem em contato diretamente."}
APIs dinâmicas conectadas (tool genérica):
{dynamic_tools_info}

INSTRUÇÕES IMPORTANTES (POLÍTICA DE DECISÃO):
- **IMPORTANTE**: Quando o cliente perguntar sobre horários de funcionamento, regras, promoções ou outras informações específicas da empresa, SEMPRE use a ferramenta get_business_knowledge para consultar essas informações antes de responder.
- Evite respostas longas. Priorize executar a ferramenta e responder com o resultado real.
{"" if has_calendar_api else ""}
{"" if has_calendar_api else "INSTRUÇÕES PARA AGENDAMENTO (quando não há APIs de agenda):"}
{"" if has_calendar_api else "- Quando clientes perguntarem sobre agendamento ou reservas, informe educadamente que o sistema de reservas online não está configurado no momento."}
{"" if has_calendar_api else "- Sugira que entrem em contato diretamente com a empresa por telefone ou WhatsApp para fazer reservas."}
{"" if has_calendar_api else "- Use get_business_knowledge para informar horários de funcionamento quando disponíveis."}
{"" if has_calendar_api else ""}
{"" if has_calendar_api else "INSTRUÇÕES PARA AGENDAMENTO (quando há APIs de agenda):"}
{"" if has_calendar_api else "- Quando o cliente pedir para agendar/confirmar um horário, extraia data e hora do contexto recente e chame a ferramenta apropriada."}
{"" if has_calendar_api else "- Se JÁ tivermos data e hora e o cliente confirmar (ex.: 'pode agendar às 17h'), peça o email do cliente se ainda não tiver e então chame DIRETAMENTE a ferramenta fazer_reserva com data, hora, nome e email."}
{"" if has_calendar_api else "- Se faltar apenas UM dado (data, hora ou email), pergunte somente o que falta. Não repita perguntas já respondidas."}
{"" if has_calendar_api else "- Sempre que o cliente mencionar 'hoje', use {current_date}. Para dias da semana (ex.: segunda-feira), calcule a próxima ocorrência a partir da data atual."}
{"" if has_calendar_api else "- Para verificar disponibilidade, use verificar_calendario (YYYY-MM-DD). Depois que o cliente escolher um horário dessa lista e fornecer o email, chame fazer_reserva."}

PROMPT ESPECÍFICO DA EMPRESA:
{prompt_empresa}

Lembre-se: Use as ferramentas para fornecer informações precisas e não responda conclusões sem executar as ferramentas necessárias."""
        
        return system_prompt 