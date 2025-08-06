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
        
        # Verificar se tem OpenAI key
        openai_key = empresa_config.get('openai_key')
        if not openai_key:
            logger.error("OpenAI key não encontrada na configuração da empresa")
            raise Exception("OpenAI key não configurada")
        
        logger.info(f"Inicializando LLM com OpenAI key: {openai_key[:10]}...")
        
        self.llm = OpenAI(
            api_key=openai_key,
            temperature=0.7,
            max_tokens=500
        )
        self.memory = ConversationBufferWindowMemory(
            k=5,
            return_messages=True
        )
        self.tools = self._setup_tools()
        logger.info(f"Tools configuradas: {len(self.tools)} tools")
        
        self.agent = self._create_agent()
        logger.info("Agent inicializado com sucesso")
    
    def _setup_tools(self) -> List[Tool]:
        """Configura as ferramentas disponíveis para o agent"""
        from tools.cliente_tools import ClienteTools
        from tools.calendar_tools import CalendarTools
        from tools.message_tools import MessageTools
        
        cliente_tools = ClienteTools()
        calendar_tools = CalendarTools()
        message_tools = MessageTools()
        
        # Tools básicas
        tools = []
        
        # Tool para buscar cliente (sem parâmetros)
        def buscar_cliente_simple(*args, **kwargs):
            try:
                return cliente_tools.buscar_cliente_info("cliente_atual", 1)  # empresa_id 1 = TinyTeams
            except Exception as e:
                return f"Erro ao buscar cliente: {str(e)}"
        
        # Tool para verificar calendário (sem parâmetros)
        def verificar_calendario_simple(*args, **kwargs):
            try:
                return calendar_tools.verificar_disponibilidade("amanhã", self.empresa_config)
            except Exception as e:
                return f"Erro ao verificar calendário: {str(e)}"
        
        # Tool para fazer reserva (com parâmetros simples)
        def fazer_reserva_simple(data="amanhã", hora="14:00", cliente="Cliente", *args, **kwargs):
            try:
                return calendar_tools.fazer_reserva(data, hora, cliente, self.empresa_config)
            except Exception as e:
                return f"Erro ao fazer reserva: {str(e)}"
        
        tools = [
            Tool(
                name="buscar_cliente",
                func=buscar_cliente_simple,
                description="Busca informações do cliente atual no banco de dados."
            ),
            Tool(
                name="verificar_calendario",
                func=verificar_calendario_simple,
                description="Verifica disponibilidade no Google Calendar para amanhã."
            ),
            Tool(
                name="fazer_reserva",
                func=fazer_reserva_simple,
                description="Faz reserva no Google Calendar. Parâmetros: data (opcional), hora (opcional), cliente (opcional)."
            )
        ]
        
        # Adicionar Tools das APIs conectadas
        # tools.extend(self._get_api_tools())  # Temporariamente desabilitado
        
        return tools
    
    def _get_api_tools(self) -> List[Tool]:
        """Gera Tools automaticamente das APIs conectadas"""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from models import Empresa, EmpresaAPI, API
        from config import Config
        
        tools = []
        
        try:
            # Buscar empresa
            engine = create_engine(Config.POSTGRES_URL)
            SessionLocal = sessionmaker(bind=engine)
            session = SessionLocal()
            
            # Buscar empresa pelo slug
            empresa_slug = self.empresa_config.get('slug')
            if not empresa_slug:
                return tools
            
            empresa = session.query(Empresa).filter(Empresa.slug == empresa_slug).first()
            if not empresa:
                return tools
            
            # Buscar APIs conectadas
            empresa_apis = session.query(EmpresaAPI).filter(
                EmpresaAPI.empresa_id == empresa.id,
                EmpresaAPI.ativo == True
            ).all()
            
            for empresa_api in empresa_apis:
                api = empresa_api.api
                if api.schema_cache and api.schema_cache.get('endpoints'):
                    # Gerar Tools para cada endpoint
                    for endpoint in api.schema_cache['endpoints']:
                        tool = self._create_api_tool(api, endpoint, empresa_api.config)
                        if tool:
                            tools.append(tool)
            
            session.close()
            
        except Exception as e:
            logger.error(f"Erro ao gerar Tools das APIs: {e}")
        
        return tools
    
    def _create_api_tool(self, api: API, endpoint: dict, config: dict) -> Tool:
        """Cria uma Tool para um endpoint específico"""
        try:
            from tools.api_tools import APITools
            
            # Criar função dinâmica
            def api_call(**kwargs):
                api_tools = APITools()
                return api_tools.call_api(
                    api_name=api.nome,
                    endpoint_path=endpoint['path'],
                    method=endpoint['method'],
                    config=config,
                    **kwargs
                )
            
            # Gerar descrição
            description = endpoint.get('summary', endpoint.get('description', ''))
            if not description:
                description = f"{endpoint['method']} {endpoint['path']}"
            
            # Adicionar campos obrigatórios na descrição
            required_fields = self._extract_required_fields(endpoint)
            if required_fields:
                description += f"\nCampos obrigatórios: {', '.join(required_fields)}"
            
            return Tool(
                name=f"{api.nome.lower()}_{endpoint['operation_id']}",
                func=api_call,
                description=description
            )
            
        except Exception as e:
            logger.error(f"Erro ao criar Tool para {endpoint['path']}: {e}")
            return None
    
    def _extract_required_fields(self, endpoint: dict) -> List[str]:
        """Extrai campos obrigatórios do endpoint"""
        required_fields = []
        
        # Verificar parâmetros obrigatórios
        for param in endpoint.get('parameters', []):
            if param.get('required', False):
                required_fields.append(param['name'])
        
        # Verificar request body obrigatório
        request_body = endpoint.get('request_body', {})
        if request_body and request_body.get('required', False):
            content = request_body.get('content', {})
            for media_type, schema_info in content.items():
                if 'application/json' in media_type:
                    schema = schema_info.get('schema', {})
                    required = schema.get('required', [])
                    required_fields.extend(required)
        
        return list(set(required_fields))  # Remove duplicatas
    
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
            logger.info(f"Processando mensagem: {message}")
            
            # Construir prompt com contexto da empresa
            system_prompt = self._build_system_prompt(context)
            
            # Log do prompt para debug
            logger.info(f"System prompt: {system_prompt}")
            
            # Usar o Agent para permitir chamada de tools
            logger.info("Chamando agent.ainvoke...")
            input_text = f"{system_prompt}\n\nMensagem do cliente: {message}"
            response = await self.agent.ainvoke(
                {"input": input_text}
            )
            
            logger.info(f"Resposta do agent: {response}")
            # Extrair a resposta do objeto retornado pelo ainvoke
            if isinstance(response, dict):
                return response.get('output', str(response))
            else:
                return str(response)
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem com agent: {e}")
            logger.error(f"Traceback completo: ", exc_info=True)
            return "Desculpe, tive um problema técnico. Como posso ajudar?"
    
    def _build_system_prompt(self, context: Dict[str, Any]) -> str:
        """Constrói prompt do sistema baseado na configuração da empresa"""
        base_prompt = self.empresa_config.get('prompt', 'Você é um assistente virtual.')
        
        # Adicionar informações do cliente se disponível
        cliente_info = context.get('cliente_info', {})
        if cliente_info:
            if isinstance(cliente_info, dict):
                base_prompt += f"\n\nCliente: {cliente_info.get('nome', 'Cliente')}"
                base_prompt += f"\nÚltima interação: {cliente_info.get('ultima_atividade', 'N/A')}"
            else:
                base_prompt += f"\n\nInformações do cliente: {cliente_info}"
        
        # Adicionar instruções específicas
        if self.empresa_config.get('mensagem_quebrada'):
            base_prompt += "\n\nIMPORTANTE: Quebre respostas longas em até 3 mensagens curtas."
        
        # Adicionar instruções sobre o uso das ferramentas
        base_prompt += "\n\nVocê tem acesso às seguintes ferramentas:"
        base_prompt += "\n- buscar_cliente: Para buscar informações do cliente"
        base_prompt += "\n- verificar_calendario: Para verificar disponibilidade"
        base_prompt += "\n- fazer_reserva: Para agendar reuniões"
        
        base_prompt += "\n\nUse as ferramentas quando necessário para responder adequadamente."
        
        return base_prompt 