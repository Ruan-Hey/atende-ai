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
        # Chat model para tool-calling
        self.chat_llm = ChatOpenAI(
            api_key=empresa_config.get('openai_key'),
            temperature=0.1
        )
        self.memory = ConversationBufferWindowMemory(
            k=20,
            return_messages=True
        )
        self.current_context: Dict[str, Any] = {}
        self.tools = self._setup_tools()
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
            cliente = data.get('cliente') or data.get('customer') or self.current_context.get('cliente_name') or 'Cliente'
            if not data_str or not hora:
                return "Parâmetros ausentes: forneça {'data': 'YYYY-MM-DD', 'hora': 'HH:MM', 'cliente': 'Nome'}"
            return calendar_tools.fazer_reserva(data_str, hora, cliente, self.empresa_config)
        
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
                description="Faz reserva real na agenda disponível. Entrada: JSON {'data': 'YYYY-MM-DD', 'hora': 'HH:MM', 'cliente': 'Nome'}"
            ),
            Tool(
                name="enviar_mensagem",
                func=enviar_mensagem_wrapper,
                description="Envia mensagem pelo canal apropriado. Entrada: JSON {'mensagem': '...', 'cliente_id': '...'}"
            )
        ]
        
        # Adicionar Tools das APIs conectadas
        tools.extend(self._get_api_tools())
        
        # Guardar referências para wrappers no structured setup
        self._wrappers = {
            "buscar_cliente": buscar_cliente_wrapper,
            "verificar_calendario": verificar_calendario_wrapper,
            "fazer_reserva": fazer_reserva_wrapper,
            "enviar_mensagem": enviar_mensagem_wrapper,
        }
        
        return tools
    
    def _setup_structured_tools(self):
        """Cria StructuredTools com assinaturas tipadas para tool-calling nativo"""
        from typing import Optional
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
        def t_fazer_reserva(data: str, hora: str, cliente: str) -> str:
            """Faz uma reserva no calendário para a data, hora e cliente especificados."""
            return self._wrappers["fazer_reserva"](data=data, hora=hora, cliente=cliente)
        structured.append(t_fazer_reserva)
        
        @lc_tool("enviar_mensagem")
        def t_enviar_mensagem(mensagem: str, cliente_id: str) -> str:
            """Envia uma mensagem para o cliente especificado."""
            return self._wrappers["enviar_mensagem"](mensagem=mensagem, cliente_id=cliente_id)
        structured.append(t_enviar_mensagem)
        
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
        """Cria o agent com as ferramentas configuradas (modo legado)"""
        return initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True
        )
    
    async def process_message(self, message: str, context: Dict[str, Any]) -> str:
        """Processa uma mensagem usando o agent"""
        try:
            # Adicionar data atual ao contexto
            from datetime import datetime
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
            
            # Construir prompt do sistema
            system_prompt = self._build_system_prompt(context)
            
            # Criar mensagens para o chat
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=message)
            ]
            
            # Adicionar histórico de conversa
            if hasattr(self.memory, 'chat_memory') and self.memory.chat_memory.messages:
                # Adicionar mensagens do histórico (exceto a última que é a atual)
                messages[1:1] = self.memory.chat_memory.messages[:-1]
            
            # Processar com o LLM
            response = await self.chat_llm.ainvoke(messages)
            
            # Salvar na memória
            self.memory.save_context(
                {"input": message},
                {"output": response.content}
            )
            
            return response.content
            
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
3. fazer_reserva - Faz reserva real na agenda
4. enviar_mensagem - Envia mensagem

INSTRUÇÕES IMPORTANTES:
- SEMPRE use a data atual ({current_date}) como referência quando o cliente não especificar data
- Para verificar disponibilidade, use a ferramenta verificar_calendario com a data no formato YYYY-MM-DD
- Para fazer reservas, use a ferramenta fazer_reserva com data, hora e nome do cliente
- Quando o cliente perguntar sobre horários disponíveis, SEMPRE verifique o calendário real primeiro
- Se o cliente mencionar "hoje", use {current_date}
- Se o cliente mencionar "amanhã", calcule a data de amanhã

PROMPT ESPECÍFICO DA EMPRESA:
{prompt_empresa}

Lembre-se: Sempre seja útil, profissional e use as ferramentas disponíveis para fornecer informações precisas sobre disponibilidade e fazer reservas."""
        
        return system_prompt 