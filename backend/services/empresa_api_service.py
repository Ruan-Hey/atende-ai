from ..models import Empresa, API, EmpresaAPI
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class EmpresaAPIService:
    """Serviço para gerenciar APIs das empresas usando empresa_apis"""
    
    @staticmethod
    def get_empresa_api_config(session: Session, empresa_id: int, api_name: str) -> Optional[Dict[str, Any]]:
        """Obtém configuração de uma API específica da empresa"""
        try:
            # Buscar API
            api = session.query(API).filter(API.nome == api_name).first()
            
            if not api:
                logger.warning(f"API '{api_name}' não encontrada")
                return None
            
            # Buscar conexão
            connection = session.query(EmpresaAPI).filter(
                EmpresaAPI.empresa_id == empresa_id,
                EmpresaAPI.api_id == api.id,
                EmpresaAPI.ativo == True
            ).first()
            
            if connection and connection.config:
                logger.info(f"Configuração encontrada para {api_name} na empresa {empresa_id}")
                return connection.config
            
            logger.warning(f"Nenhuma configuração ativa encontrada para {api_name} na empresa {empresa_id}")
            return None
            
        except Exception as e:
            logger.error(f"Erro ao buscar configuração da API {api_name}: {e}")
            return None
    
    @staticmethod
    def get_empresa_active_apis(session: Session, empresa_id: int) -> List[Dict[str, Any]]:
        """Obtém todas as APIs ativas de uma empresa"""
        try:
            connections = session.query(EmpresaAPI).filter(
                EmpresaAPI.empresa_id == empresa_id,
                EmpresaAPI.ativo == True
            ).all()
            
            logger.info(f"Empresa {empresa_id} - Conexões encontradas: {len(connections)}")
            for conn in connections:
                logger.info(f"  - API ID: {conn.api_id}, Config: {conn.config}")
            
            apis = []
            for conn in connections:
                api = session.query(API).filter(API.id == conn.api_id).first()
                if api:
                    apis.append({
                        "api_name": api.nome,
                        "api_id": api.id,
                        "config": conn.config,
                        "ativo": conn.ativo
                    })
                    logger.info(f"  - API: {api.nome} (ID: {api.id})")
            
            logger.info(f"APIs retornadas: {len(apis)}")
            return apis
            
        except Exception as e:
            logger.error(f"Erro ao buscar APIs ativas da empresa {empresa_id}: {e}")
            return []
    
    @staticmethod
    def update_empresa_api_config(session: Session, empresa_id: int, api_name: str, config: Dict[str, Any]) -> bool:
        """Atualiza configuração de uma API da empresa"""
        try:
            # Buscar API
            api = session.query(API).filter(API.nome == api_name).first()
            
            if not api:
                logger.error(f"API '{api_name}' não encontrada")
                return False
            
            # Buscar conexão existente
            connection = session.query(EmpresaAPI).filter(
                EmpresaAPI.empresa_id == empresa_id,
                EmpresaAPI.api_id == api.id
            ).first()
            
            if connection:
                # Atualizar configuração existente
                connection.config = config
                connection.ativo = True
                logger.info(f"Configuração atualizada para {api_name} na empresa {empresa_id}")
            else:
                # Criar nova conexão
                new_connection = EmpresaAPI(
                    empresa_id=empresa_id,
                    api_id=api.id,
                    config=config,
                    ativo=True
                )
                session.add(new_connection)
                logger.info(f"Nova configuração criada para {api_name} na empresa {empresa_id}")
            
            session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Erro ao atualizar configuração da API {api_name}: {e}")
            session.rollback()
            return False
    
    @staticmethod
    def deactivate_empresa_api(session: Session, empresa_id: int, api_name: str) -> bool:
        """Desativa uma API da empresa"""
        try:
            # Buscar API
            api = session.query(API).filter(API.nome == api_name).first()
            
            if not api:
                logger.error(f"API '{api_name}' não encontrada")
                return False
            
            # Buscar conexão
            connection = session.query(EmpresaAPI).filter(
                EmpresaAPI.empresa_id == empresa_id,
                EmpresaAPI.api_id == api.id
            ).first()
            
            if connection:
                connection.ativo = False
                session.commit()
                logger.info(f"API {api_name} desativada para empresa {empresa_id}")
                return True
            else:
                logger.warning(f"Nenhuma conexão encontrada para {api_name} na empresa {empresa_id}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao desativar API {api_name}: {e}")
            session.rollback()
            return False
    
    # Métodos específicos para cada API
    @staticmethod
    def get_google_calendar_config(session: Session, empresa_id: int) -> Optional[Dict[str, Any]]:
        """Obtém configuração do Google Calendar"""
        return EmpresaAPIService.get_empresa_api_config(session, empresa_id, "Google Calendar")
    
    @staticmethod
    def get_openai_config(session: Session, empresa_id: int) -> Optional[Dict[str, Any]]:
        """Obtém configuração do OpenAI"""
        return EmpresaAPIService.get_empresa_api_config(session, empresa_id, "OpenAI")
    
    @staticmethod
    def get_twilio_config(session: Session, empresa_id: int) -> Optional[Dict[str, Any]]:
        """Obtém configuração do Twilio"""
        return EmpresaAPIService.get_empresa_api_config(session, empresa_id, "Twilio")
    
    @staticmethod
    def get_google_sheets_config(session: Session, empresa_id: int) -> Optional[Dict[str, Any]]:
        """Obtém configuração do Google Sheets"""
        return EmpresaAPIService.get_empresa_api_config(session, empresa_id, "Google Sheets")
    
    @staticmethod
    def get_chatwoot_config(session: Session, empresa_id: int) -> Optional[Dict[str, Any]]:
        """Obtém configuração do Chatwoot"""
        return EmpresaAPIService.get_empresa_api_config(session, empresa_id, "Chatwoot")
    
    @staticmethod
    def get_all_empresa_configs(session: Session, empresa_id: int) -> Dict[str, Any]:
        """Obtém todas as configurações de uma empresa em formato compatível"""
        try:
            # Buscar todas as APIs ativas
            apis = EmpresaAPIService.get_empresa_active_apis(session, empresa_id)
            
            # Converter para formato compatível com o frontend
            configs = {}
            for api in apis:
                api_name = api["api_name"]
                config = api["config"]
                
                if api_name == "OpenAI":
                    configs["openai_key"] = config.get("openai_key")
                elif api_name == "Twilio":
                    configs["twilio_sid"] = config.get("twilio_sid")
                    configs["twilio_token"] = config.get("twilio_token")
                    configs["twilio_number"] = config.get("twilio_number")
                elif api_name == "Google Sheets":
                    configs["google_sheets_id"] = config.get("google_sheets_id")
                elif api_name == "Google Calendar":
                    configs["google_calendar_enabled"] = config.get("google_calendar_enabled")
                    configs["google_calendar_client_id"] = config.get("google_calendar_client_id")
                    configs["google_calendar_client_secret"] = config.get("google_calendar_client_secret")
                    configs["google_calendar_refresh_token"] = config.get("google_calendar_refresh_token")
                elif api_name == "Chatwoot":
                    configs["chatwoot_token"] = config.get("chatwoot_token")
                    configs["chatwoot_inbox_id"] = config.get("chatwoot_inbox_id")
                    configs["chatwoot_origem"] = config.get("chatwoot_origem")
            
            return configs
            
        except Exception as e:
            logger.error(f"Erro ao obter configurações da empresa {empresa_id}: {e}")
            return {} 