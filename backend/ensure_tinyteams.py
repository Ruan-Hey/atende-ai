#!/usr/bin/env python3

from .models import Empresa
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .config import Config

def ensure_tinyteams():
    """Garante que a empresa TinyTeams esteja cadastrada"""
    engine = create_engine(Config().POSTGRES_URL)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        # Verificar se TinyTeams já existe
        tinyteams = session.query(Empresa).filter(Empresa.slug == 'tinyteams').first()
        
        if tinyteams:
            print(f"✅ Empresa TinyTeams já existe (ID: {tinyteams.id})")
            return tinyteams.id
        else:
            # Criar empresa TinyTeams
            nova_empresa = Empresa(
                nome="TinyTeams",
                slug="tinyteams",
                descricao="Empresa padrão do sistema",
                ativo=True,
                config={
                    "twilio_sid": "",
                    "twilio_token": "",
                    "twilio_number": "",
                    "openai_key": "",
                    "google_sheets_id": "",
                    "google_calendar_client_id": "",
                    "google_calendar_client_secret": "",
                    "google_calendar_refresh_token": "",
                    "chatwoot_token": "",
                    "chatwoot_inbox_id": "",
                    "chatwoot_origem": "",
                    "horario_funcionamento": "Segunda a Sexta, 9h às 18h",
                    "filtros_chatwoot": "",
                    "usar_buffer": True,
                    "mensagem_quebrada": False,
                    "prompt": "Você é um assistente virtual da TinyTeams. Ajude os clientes de forma cordial e profissional."
                }
            )
            
            session.add(nova_empresa)
            session.commit()
            
            print(f"✅ Empresa TinyTeams criada com sucesso (ID: {nova_empresa.id})")
            return nova_empresa.id
            
    except Exception as e:
        print(f"❌ Erro ao criar/verificar TinyTeams: {e}")
        session.rollback()
        return None
    finally:
        session.close()

if __name__ == "__main__":
    ensure_tinyteams() 