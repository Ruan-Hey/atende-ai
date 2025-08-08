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
            return self._wrappers["buscar_cliente"](cliente_id=cliente_id)
        structured.append(t_buscar_cliente)
        
        @lc_tool("verificar_calendario")
        def t_verificar_calendario(data: str) -> str:
            return self._wrappers["verificar_calendario"](data=data)
        structured.append(t_verificar_calendario)
        
        @lc_tool("fazer_reserva")
        def t_fazer_reserva(data: str, hora: str, cliente: str) -> str:
            return self._wrappers["fazer_reserva"](data=data, hora=hora, cliente=cliente)
        structured.append(t_fazer_reserva)
        
        @lc_tool("enviar_mensagem")
        def t_enviar_mensagem(mensagem: str, cliente_id: str) -> str:
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
        """Processa mensagem usando tool-calling nativo (fallback para legado em erro)"""
        try:
            # Guardar contexto atual para wrappers
            self.current_context = context or {}
            
            # Construir prompt com contexto da empresa
            system_prompt = self._build_system_prompt(context)
            logger.info(f"System prompt: {system_prompt}")
            
            # Montar conversa para tool-calling
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=message)
            ]
            
            llm_with_tools = self.chat_llm.bind_tools(self.structured_tools)
            
            # Loop de execução de tools (até 3 chamadas)
            for _ in range(3):
                ai_msg: AIMessage = await llm_with_tools.ainvoke(messages)
                messages.append(ai_msg)
                
                if not ai_msg.tool_calls:
                    # Sem tool calls → resposta final
                    return (ai_msg.content or "").strip() or "Tudo certo! Como posso ajudar?"
                
                # Executar cada tool call
                for call in ai_msg.tool_calls:
                    name = call["name"] if isinstance(call, dict) else call.name
                    args = call["args"] if isinstance(call, dict) else call.args
                    try:
                        tool_map = {t.name: t for t in self.structured_tools}
                        if name in tool_map:
                            result = tool_map[name].invoke(args)
                        else:
                            result = f"Tool desconhecida: {name}"
                    except Exception as e:
                        result = f"Erro na tool {name}: {e}"
                    messages.append(ToolMessage(content=str(result), tool_call_id=(call.get("id") if isinstance(call, dict) else call.id)))
            
            # Se exceder chamadas, retornar última resposta do modelo
            return "Para continuar, preciso de mais detalhes (data/hora/cliente)."
        
        except Exception as e:
            logger.error(f"Erro no tool-calling, usando modo legado: {e}")
            # Fallback: modo legado
            try:
                agent_input = (
                    f"{system_prompt}\n\nMensagem do cliente: {message}\n\n"
                    "Quando decidir usar uma ferramenta, SEMPRE forneça Action Input como um JSON válido."
                )
                response = await self.agent.ainvoke({"input": agent_input})
                return response["output"].strip()
            except Exception:
                return "Desculpe, tive um problema técnico. Como posso ajudar?"
    
    def _build_system_prompt(self, context: Dict[str, Any]) -> str:
        """Constrói prompt do sistema baseado na configuração da empresa"""
        base_prompt = self.empresa_config.get('prompt', 'Você é um assistente virtual.')
        
        # Adicionar informações do cliente se disponível
        cliente_info = context.get('cliente_info', {})
        if cliente_info:
            base_prompt += f"\n\nCliente: {cliente_info.get('nome', 'Cliente')}"
            base_prompt += f"\nÚltima interação: {cliente_info.get('ultima_atividade', 'N/A')}"
        
        # Adicionar instruções específicas sobre ferramentas
        base_prompt += """
        
IMPORTANTE - REGRAS DE USO:
1. SEMPRE use as ferramentas disponíveis para verificar informações reais
2. NUNCA invente horários, datas ou informações de calendário
3. Para agendamentos, use a ferramenta 'verificar_calendario' primeiro
4. Para fazer reservas, use a ferramenta 'fazer_reserva' com dados reais
5. Se não tiver acesso às ferramentas, diga que não pode fazer a operação
6. Seja honesto sobre limitações - não invente funcionalidades
7. Sempre confirme informações antes de agendar
8. Ao chamar uma ferramenta, o Action Input deve ser JSON válido com os campos esperados.

FORMATOS DE ACTION INPUT:
- buscar_cliente: {"cliente_id": "..."}
- verificar_calendario: {"data": "YYYY-MM-DD"}
- fazer_reserva: {"data": "YYYY-MM-DD", "hora": "HH:MM", "cliente": "Nome"}
- enviar_mensagem: {"mensagem": "...", "cliente_id": "..."}
"""
        
        # Adicionar instruções específicas
        if self.empresa_config.get('mensagem_quebrada'):
            base_prompt += "\n\nIMPORTANTE: Quebre respostas longas em até 3 mensagens curtas."
        
        return base_prompt 