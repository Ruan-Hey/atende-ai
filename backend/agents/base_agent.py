from langchain.agents import initialize_agent, AgentType
from langchain_openai import OpenAI
from langchain.memory import ConversationBufferWindowMemory
from langchain.tools import Tool
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
        self.memory = ConversationBufferWindowMemory(
            k=20,
            return_messages=True
        )
        self.tools = self._setup_tools()
        self.agent = self._create_agent()
    
    def _setup_tools(self) -> List[Tool]:
        """Configura as ferramentas disponíveis para o agent"""
        from tools.cliente_tools import ClienteTools
        from tools.calendar_tools import CalendarTools
        from tools.message_tools import MessageTools
        
        cliente_tools = ClienteTools()
        calendar_tools = CalendarTools()
        message_tools = MessageTools()
        
        # Tools básicas
        tools = [
            Tool(
                name="buscar_cliente",
                func=cliente_tools.buscar_cliente_info,
                description="Busca informações do cliente no banco de dados. Use quando precisar de dados do cliente."
            ),
            Tool(
                name="verificar_calendario",
                func=calendar_tools.verificar_disponibilidade,
                description="Verifica disponibilidade real no Google Calendar. Use SEMPRE antes de sugerir horários. Parâmetro: data (formato YYYY-MM-DD)"
            ),
            Tool(
                name="fazer_reserva",
                func=calendar_tools.fazer_reserva,
                description="Faz reserva real no Google Calendar e registra no Google Sheets. Use apenas após confirmar disponibilidade. Parâmetros: data, hora, cliente, empresa_config"
            ),
            Tool(
                name="enviar_mensagem",
                func=message_tools.enviar_resposta,
                description="Envia mensagem pelo canal apropriado. Use para enviar respostas confirmadas."
            )
        ]
        
        # Adicionar Tools das APIs conectadas
        tools.extend(self._get_api_tools())
        
        return tools
    
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
        """Cria o agent com as ferramentas configuradas"""
        return initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True
        )
    
    async def process_message(self, message: str, context: Dict[str, Any]) -> str:
        """Processa mensagem usando o agent"""
        try:
            # Construir prompt com contexto da empresa
            system_prompt = self._build_system_prompt(context)
            
            # Log do prompt para debug
            logger.info(f"System prompt: {system_prompt}")
            
            # Usar o agent com as tools configuradas
            # Preparar input para o agent
            agent_input = f"{system_prompt}\n\nMensagem do cliente: {message}\n\nResponda usando as ferramentas disponíveis quando necessário."
            
            # Executar o agent
            response = await self.agent.ainvoke({"input": agent_input})
            
            return response["output"].strip()
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem com agent: {e}")
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
7. Sempre confirme informações antes de agendar"""
        
        # Adicionar instruções específicas
        if self.empresa_config.get('mensagem_quebrada'):
            base_prompt += "\n\nIMPORTANTE: Quebre respostas longas em até 3 mensagens curtas."
        
        return base_prompt 