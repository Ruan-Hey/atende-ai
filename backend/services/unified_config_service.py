
from models import Empresa, EmpresaAPI, API
from sqlalchemy.orm import Session
from typing import Optional

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

def get_trinks_config(session: Session, empresa_id: int) -> Optional[dict]:
    """Obtém configuração da Trinks (se ativa)"""
    connections = session.query(EmpresaAPI).filter(
        EmpresaAPI.empresa_id == empresa_id,
        EmpresaAPI.ativo == True
    ).all()
    for conn in connections:
        api = session.query(API).filter(API.id == conn.api_id).first()
        if api and 'trinks' in (api.nome or '').lower():
            raw = conn.config or {}
            # Normalização defensiva de chaves históricas (não quebrar registros antigos)
            try:
                cfg = dict(raw) if isinstance(raw, dict) else {}
                # api_key pode ter vindo como "key"
                api_key = cfg.get('api_key') or cfg.get('key')
                # base_url pode ter variações
                base_url = cfg.get('base_url') or cfg.get('url_base') or cfg.get('url')
                if base_url and not str(base_url).startswith(('http://', 'https://')):
                    base_url = f"https://{str(base_url).lstrip('/')}"
                if not base_url:
                    base_url = 'https://api.trinks.com/v1'
                # estabelecimento_id pode ter variações
                estab = (
                    cfg.get('estabelecimento_id')
                    or cfg.get('estabelecimentoId')
                    or cfg.get('estabelecimento')
                )
                # Reatribuir chaves canônicas mantendo outras intactas
                cfg['api_key'] = api_key
                cfg['base_url'] = base_url
                if estab is not None:
                    cfg['estabelecimento_id'] = estab
                return cfg
            except Exception:
                # Em caso de qualquer erro, retorna bruto para não bloquear
                return raw
    return None
