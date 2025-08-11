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
            k=50,  # Aumentado para 50 mensagens
            return_messages=True
        )
        # Contexto persistente que mantém informações extraídas
        self.current_context: Dict[str, Any] = {}
        # Contexto de reserva específico que persiste durante toda a conversa
        self.reservation_context: Dict[str, Any] = {
            'cliente_nome': None,
            'waid': None,  # WhatsApp ID único do cliente
            'quantidade_pessoas': None,
            'data_reserva': None,
            'horario_reserva': None,
            'observacoes': None,
            'email': None,
            'status': 'aguardando_info'  # aguardando_info, confirmando, finalizada
        }
        
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
            
            # Verificar se email é obrigatório baseado nas regras da API
            try:
                from .api_rules_engine import api_rules_engine
                if api_rules_engine.is_email_required(self.empresa_config) and not email_str:
                    return "❌ Email é obrigatório para esta API. Por favor, forneça um email válido."
            except Exception as e:
                logger.error(f"Erro ao verificar regras da API: {e}")
                # Se não conseguir verificar, aceita sem email
            
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
            def t_fazer_reserva(data: str, hora: str, nome: str, email: str = None) -> str:
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
        try:
            from .api_rules_engine import api_rules_engine
            rules = api_rules_engine.get_api_rules(self.empresa_config)
            return rules['api_type'].value != "Nenhuma"
        except Exception as e:
            logger.error(f"Erro ao verificar APIs de agenda: {e}")
            # Fallback para verificação manual
            # Verificar Google Calendar
            if (self.empresa_config.get('google_calendar_client_id') and 
                self.empresa_config.get('google_calendar_client_secret')):
                return True
            
            # Verificar Google Sheets (para reservas)
            if (self.empresa_config.get('google_sheets_id') and 
                (self.empresa_config.get('google_sheets_client_id') or 
                 self.empresa_config.get('google_sheets_service_account'))):
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
    
    def _extract_reservation_info(self, message: str, context: Dict[str, Any] = None) -> None:
        """Extrai informações de reserva da mensagem e atualiza o contexto"""
        import re
        from datetime import datetime, timedelta
        
        # Extrair WaId do contexto se disponível
        if context and context.get('cliente_id'):
            self.reservation_context['waid'] = context['cliente_id']
        
        message_lower = message.lower()
        
        # Extrair nome do cliente
        nome_patterns = [
            r'em nome de (\w+)',
            r'nome (\w+)',
            r'para (\w+)',
            r'(\w+) gimenes hey',  # Caso específico do exemplo
            r'(\w+) hey'
        ]
        
        for pattern in nome_patterns:
            match = re.search(pattern, message_lower)
            if match and not self.reservation_context['cliente_nome']:
                self.reservation_context['cliente_nome'] = match.group(1).title()
                break
        
        # Extrair quantidade de pessoas
        pessoas_patterns = [
            r'(\d+)\s*pessoas?',
            r'para\s+(\d+)\s*pessoas?',
            r'(\d+)\s*convidados?',
            r'(\d+)\s*clientes?'
        ]
        
        for pattern in pessoas_patterns:
            match = re.search(pattern, message_lower)
            if match and not self.reservation_context['quantidade_pessoas']:
                self.reservation_context['quantidade_pessoas'] = int(match.group(1))
                break
        
        # Extrair data
        data_patterns = [
            r'para\s+(amanhã|amanha)',
            r'(amanhã|amanha)',
            r'para\s+(segunda|terça|quarta|quinta|sexta|sábado|domingo)',
            r'(segunda|terça|quarta|quinta|sexta|sábado|domingo)',
            r'(\d{1,2})/(\d{1,2})',
            r'(\d{4})-(\d{1,2})-(\d{1,2})'
        ]
        
        for pattern in data_patterns:
            match = re.search(pattern, message_lower)
            if match and not self.reservation_context['data_reserva']:
                if 'amanhã' in match.group(0) or 'amanha' in match.group(0):
                    tomorrow = datetime.now() + timedelta(days=1)
                    self.reservation_context['data_reserva'] = tomorrow.strftime('%Y-%m-%d')
                elif any(dia in match.group(0) for dia in ['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo']):
                    # Calcular próxima ocorrência do dia da semana
                    dias_semana = {
                        'segunda': 0, 'terça': 1, 'quarta': 2, 'quinta': 3,
                        'sexta': 4, 'sábado': 5, 'domingo': 6
                    }
                    dia_atual = datetime.now().weekday()
                    dia_desejado = dias_semana[match.group(1)]
                    dias_para_adicionar = (dia_desejado - dia_atual) % 7
                    if dias_para_adicionar == 0:
                        dias_para_adicionar = 7
                    data_futura = datetime.now() + timedelta(days=dias_para_adicionar)
                    self.reservation_context['data_reserva'] = data_futura.strftime('%Y-%m-%d')
                break
        
        # Extrair horário
        horario_patterns = [
            r'(\d{1,2}):(\d{2})',
            r'(\d{1,2})h',
            r'(\d{1,2})\s*horas?',
            r'às\s+(\d{1,2}):(\d{2})',
            r'para\s+(\d{1,2}):(\d{2})'
        ]
        
        for pattern in horario_patterns:
            match = re.search(pattern, message_lower)
            if match and not self.reservation_context['horario_reserva']:
                if len(match.groups()) == 2:
                    hora = match.group(1).zfill(2)
                    minuto = match.group(2)
                    self.reservation_context['horario_reserva'] = f"{hora}:{minuto}"
                else:
                    hora = match.group(1).zfill(2)
                    self.reservation_context['horario_reserva'] = f"{hora}:00"
                break
        
        # Extrair observações
        if 'aniversário' in message_lower or 'aniversario' in message_lower:
            self.reservation_context['observacoes'] = 'Aniversário'
        
        # Status será determinado pelo motor de regras da API
        # Não mais hardcoded aqui
    
    def _get_reservation_summary(self) -> str:
        """Retorna um resumo do contexto de reserva atual baseado nas regras da API"""
        try:
            from .api_rules_engine import api_rules_engine
            return api_rules_engine.get_reservation_summary(self.empresa_config, self.reservation_context)
        except Exception as e:
            logger.error(f"Erro ao obter resumo da reserva: {e}")
            # Fallback simples se houver erro
            info_coletada = []
            if self.reservation_context.get('cliente_nome'):
                info_coletada.append(f"Nome: {self.reservation_context['cliente_nome']}")
            if self.reservation_context.get('quantidade_pessoas'):
                info_coletada.append(f"Pessoas: {self.reservation_context['quantidade_pessoas']}")
            if self.reservation_context.get('data_reserva'):
                info_coletada.append(f"Data: {self.reservation_context['data_reserva']}")
            if self.reservation_context.get('horario_reserva'):
                info_coletada.append(f"Horário: {self.reservation_context['horario_reserva']}")
            
            if info_coletada:
                return f"Informações coletadas: {', '.join(info_coletada)}"
            else:
                return "Nenhuma informação coletada ainda"
    
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
            
            # Extrair informações de reserva da mensagem
            self._extract_reservation_info(message, context)
            
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
        
        # Obter regras da API ativa
        try:
            from .api_rules_engine import api_rules_engine
            api_rules = api_rules_engine.get_api_rules(empresa_config)
            api_type = api_rules['api_type']
            api_name = api_rules['api_name']
            email_required = api_rules['email_required']
            waid_required = api_rules['waid_required']
        except Exception as e:
            logger.error(f"Erro ao obter regras da API: {e}")
            api_type = "Nenhuma"
            api_name = "Nenhuma"
            email_required = False
            waid_required = False
        
        # Listar APIs dinâmicas conectadas
        dynamic_api_list = []
        for key, value in empresa_config.items():
            if key.endswith('_enabled') and value is True:
                api_name_dyn = key.replace('_enabled', '').replace('_', ' ').title()
                if api_name_dyn not in ["Google Calendar", "Openai", "Google Sheets"]:
                    dynamic_api_list.append(api_name_dyn)
        dynamic_tools_info = "\n".join([f"- {api}: use a tool {api.lower().replace(' ', '_')}_api_call" for api in dynamic_api_list]) or "(nenhuma)"
        
        system_prompt = f"""Você é um assistente virtual da {empresa_nome}.

INFORMAÇÕES ATUAIS:
- Data atual: {current_date}
- Hora atual: {current_time}
- Cliente: {cliente_name} (ID: {cliente_id})
- Status do calendário: {calendar_status}

CONTEXTO DE RESERVA ATUAL:
{self._get_reservation_summary()}

INFORMAÇÕES DO CLIENTE:
{cliente_info}

FERRAMENTAS DISPONÍVEIS:
1. buscar_cliente - Busca informações do cliente
2. enviar_mensagem - Envia mensagem
3. get_business_knowledge - Consulta informações específicas da empresa (horários, regras, promoções, etc.) - Use quando o cliente perguntar sobre horários de funcionamento, regras, promoções ou outras informações da empresa

{"" if has_calendar_api else "NOTA: Ferramentas de calendário (verificar_calendario, fazer_reserva) não estão disponíveis pois nenhuma API de agenda está configurada."}
{"" if has_calendar_api else "IMPORTANTE: Quando não há APIs de agenda, siga EXATAMENTE as instruções do prompt da empresa sobre como lidar com reservas e agendamentos."}
APIs dinâmicas conectadas (tool genérica):
{dynamic_tools_info}

INSTRUÇÕES IMPORTANTES (POLÍTICA DE DECISÃO):
- **IMPORTANTE**: Quando o cliente perguntar sobre horários de funcionamento, regras, promoções ou outras informações específicas da empresa, SEMPRE use a ferramenta get_business_knowledge para consultar essas informações antes de responder.
- Evite respostas longas. Priorize executar a ferramenta e responder com o resultado real.

INSTRUÇÕES PARA AGENDAMENTO:
- **IMPORTANTE**: Use o contexto de reserva atual para evitar perguntar informações já fornecidas
- **NUNCA repita perguntas**: Se o cliente já forneceu nome, pessoas, data ou horário, use essas informações
- **Contexto inteligente**: O sistema mantém informações de reservas durante toda a conversa
- **Fluxo otimizado**: Colete apenas as informações que ainda faltam
- **Confirmação**: Quando tiver todas as informações, confirme a reserva seguindo as regras da API ativa

REGRAS ESPECÍFICAS DA API ATIVA ({api_name}):

{"" if not waid_required else "- **WaId é OBRIGATÓRIO**: Sempre use o WaId (WhatsApp ID) como identificador único do cliente"}
{"" if not waid_required else "- **Consultas por WaId**: Ao buscar reservas existentes, sempre use o WaId, não apenas o nome"}
{"" if not waid_required else "- **Consistência**: O WaId garante que não haja conflitos entre clientes com nomes iguais"}
{"" if not waid_required else "- **Formato**: WaId vem do contexto como 'cliente_id' (ex: 554195984948)"}

{"" if not email_required else "- **Email é OBRIGATÓRIO**: Sempre solicite email para confirmar reservas"}
{"" if not email_required else "- **Validação**: Verifique se o email é válido antes de confirmar"}
{"" if not email_required else "- **Formato**: Aceite emails no formato padrão (ex: usuario@dominio.com)"}

{"" if has_calendar_api else "NOTA: APIs de agenda não configuradas - siga o prompt da empresa para reservas"}
{"" if has_calendar_api else ""}
{"" if has_calendar_api else "COM APIs de agenda configuradas:"}
{"" if has_calendar_api else "- Use verificar_calendario para ver disponibilidade"}
{"" if has_calendar_api else "- Use fazer_reserva quando tiver todas as informações"}
{"" if has_calendar_api else "- Sempre que o cliente mencionar 'hoje', use {current_date}"}
{"" if has_calendar_api else "- Para dias da semana, calcule a próxima ocorrência"}

PROMPT ESPECÍFICO DA EMPRESA:
{prompt_empresa}

Lembre-se: Use as ferramentas para fornecer informações precisas e não responda conclusões sem executar as ferramentas necessárias.

**PRIORIDADE FINAL**: O prompt da empresa sempre tem precedência sobre as instruções genéricas do sistema. Siga exatamente o que a empresa instruiu."""
        
        return system_prompt 