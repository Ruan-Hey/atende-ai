
from models import Empresa, EmpresaAPI, API
from sqlalchemy.orm import Session
from sqlalchemy import text

def get_google_calendar_config(session: Session, empresa_id: int):
    """Obtém configuração do Google Calendar usando ambas as arquiteturas"""
    
    # 1. Tentar obter da tabela empresa_apis (arquitetura correta)
    google_calendar_api = session.query(API).filter(API.nome == "Google Calendar").first()
    
    if google_calendar_api:
        connection = session.query(EmpresaAPI).filter(
            EmpresaAPI.empresa_id == empresa_id,
            EmpresaAPI.api_id == google_calendar_api.id,
            EmpresaAPI.ativo == True
        ).first()
        
        if connection and connection.config:
            return connection.config
    
    # 2. Fallback para tabela empresas (arquitetura antiga) usando SQL
    result = session.execute(text("""
        SELECT google_calendar_enabled, google_calendar_client_id, 
               google_calendar_client_secret, google_calendar_refresh_token
        FROM empresas WHERE id = :empresa_id
    """), {"empresa_id": empresa_id})
    
    row = result.fetchone()
    if row and row[0]:  # google_calendar_enabled
        config = {
            "google_calendar_enabled": True
        }
        
        if row[1]:  # google_calendar_client_id
            config["google_calendar_client_id"] = row[1]
        if row[2]:  # google_calendar_client_secret
            config["google_calendar_client_secret"] = row[2]
        if row[3]:  # google_calendar_refresh_token
            config["google_calendar_refresh_token"] = row[3]
        
        return config
    
    return None
