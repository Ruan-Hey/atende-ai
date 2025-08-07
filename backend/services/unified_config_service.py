
from models import Empresa, EmpresaAPI, API
from sqlalchemy.orm import Session

def get_empresa_api_config(session: Session, empresa_id: int, api_name: str):
    """Obtém configuração de uma API específica da empresa"""
    
    # Buscar API
    api = session.query(API).filter(API.nome == api_name).first()
    
    if not api:
        return None
    
    # Buscar conexão
    connection = session.query(EmpresaAPI).filter(
        EmpresaAPI.empresa_id == empresa_id,
        EmpresaAPI.api_id == api.id,
        EmpresaAPI.ativo == True
    ).first()
    
    if connection and connection.config:
        return connection.config
    
    return None

def get_google_calendar_config(session: Session, empresa_id: int):
    """Obtém configuração do Google Calendar"""
    return get_empresa_api_config(session, empresa_id, "Google Calendar")

def get_openai_config(session: Session, empresa_id: int):
    """Obtém configuração do OpenAI"""
    return get_empresa_api_config(session, empresa_id, "OpenAI")

def get_twilio_config(session: Session, empresa_id: int):
    """Obtém configuração do Twilio"""
    return get_empresa_api_config(session, empresa_id, "Twilio")

def get_google_sheets_config(session: Session, empresa_id: int):
    """Obtém configuração do Google Sheets"""
    return get_empresa_api_config(session, empresa_id, "Google Sheets")

def get_chatwoot_config(session: Session, empresa_id: int):
    """Obtém configuração do Chatwoot"""
    return get_empresa_api_config(session, empresa_id, "Chatwoot")

def get_all_empresa_apis(session: Session, empresa_id: int):
    """Obtém todas as APIs ativas de uma empresa"""
    connections = session.query(EmpresaAPI).filter(
        EmpresaAPI.empresa_id == empresa_id,
        EmpresaAPI.ativo == True
    ).all()
    
    apis = []
    for conn in connections:
        api = session.query(API).filter(API.id == conn.api_id).first()
        apis.append({
            "api_name": api.nome,
            "config": conn.config,
            "api_id": api.id
        })
    
    return apis
