from .base_agent import BaseAgent
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class WhatsAppAgent(BaseAgent):
    """Agent específico para processamento de mensagens do WhatsApp"""
    
    def __init__(self, empresa_config: Dict[str, Any]):
        super().__init__(empresa_config)
        self.channel = "whatsapp"
    
    async def process_whatsapp_message(self, webhook_data: Dict[str, Any], empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """Processa mensagem específica do WhatsApp"""
        try:
            cliente_id = webhook_data.get('WaId', '')
            message_text = webhook_data.get('Body', '')
            profile_name = webhook_data.get('ProfileName', 'Cliente')
            
            # Buscar informações do cliente
            from tools.cliente_tools import ClienteTools
            cliente_tools = ClienteTools()
            
            # Buscar empresa_id
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            from ..models import Empresa
            from ..config import Config
            
            engine = create_engine(Config.POSTGRES_URL)
            SessionLocal = sessionmaker(bind=engine)
            session = SessionLocal()
            
            try:
                empresa_db = session.query(Empresa).filter(Empresa.slug == empresa_config.get('slug')).first()
                if not empresa_db:
                    raise Exception("Empresa não encontrada")
                
                # Buscar informações do cliente
                cliente_info_str = cliente_tools.buscar_cliente_info(cliente_id, empresa_db.id)
                
                # Construir contexto
                context = {
                    'cliente_id': cliente_id,
                    'cliente_name': profile_name,
                    'empresa': empresa_config.get('slug'),
                    'cliente_info': {'info': cliente_info_str},
                    'channel': self.channel
                }
                
                # Processar com o agent
                response = await self.process_message(message_text, context)
                
                # Salvar mensagem no banco
                from .services.services import DatabaseService
                db_service = DatabaseService()
                db_service.save_message(
                    empresa_db.id, 
                    cliente_id, 
                    message_text, 
                    is_bot=False,
                    cliente_nome=profile_name
                )
                
                # Salvar resposta do bot
                db_service.save_message(
                    empresa_db.id, 
                    cliente_id, 
                    response, 
                    is_bot=True
                )
                
                return {
                    'success': True,
                    'message': response,
                    'cliente_id': cliente_id,
                    'empresa': empresa_config.get('slug'),
                    'channel': self.channel
                }
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Erro ao processar mensagem WhatsApp: {e}")
            return {
                'success': False,
                'message': 'Desculpe, tive um problema técnico. Como posso ajudar?',
                'error': str(e)
            } 