import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import redis
from unittest.mock import Mock, patch
import os
import sys
import uuid

# Adicionar o diretório raiz ao path para importar os módulos
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from models import Base, Usuario, Empresa, Mensagem, Log
from config import Config

# Configuração para testes
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def test_db_engine():
    """Cria um engine de banco de dados para testes usando SQLite em memória"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def test_db_session(test_db_engine):
    """Cria uma sessão de banco de dados para testes"""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def client(test_db_session):
    """Cria um cliente de teste para a aplicação FastAPI"""
    # Mock da sessão de banco para que a aplicação use a mesma sessão dos testes
    with patch('main.SessionLocal') as mock_session:
        mock_session.return_value = test_db_session
        
        with TestClient(app) as test_client:
            yield test_client

@pytest.fixture
def mock_redis():
    """Mock do Redis para testes"""
    with patch('redis.Redis') as mock_redis:
        mock_redis_instance = Mock()
        mock_redis.return_value = mock_redis_instance
        yield mock_redis_instance

@pytest.fixture
def mock_openai():
    """Mock do OpenAI para testes"""
    with patch('integrations.openai_service.openai') as mock_openai:
        yield mock_openai

@pytest.fixture
def mock_twilio():
    """Mock do Twilio para testes"""
    with patch('integrations.twilio_service.Client') as mock_twilio:
        yield mock_twilio

@pytest.fixture
def mock_google_calendar():
    """Mock do Google Calendar para testes"""
    with patch('integrations.google_calendar_service.build') as mock_calendar:
        yield mock_calendar

@pytest.fixture
def mock_google_sheets():
    """Mock do Google Sheets para testes"""
    with patch('integrations.google_sheets_service.gspread') as mock_sheets:
        yield mock_sheets

@pytest.fixture
def sample_empresa(test_db_session):
    """Cria uma empresa de exemplo para testes"""
    # Gerar slug único para evitar conflitos
    unique_slug = f"test-empresa-{uuid.uuid4().hex[:8]}"
    
    empresa = Empresa(
        slug=unique_slug,
        nome="Empresa Teste",
        prompt="Olá! Como posso ajudar?",
        webhook_url="https://webhook.test.com",
        status="ativo",
        whatsapp_number="+5511999999999",
        openai_key="test-openai-key",
        twilio_sid="test-twilio-sid",
        twilio_token="test-twilio-token",
        twilio_number="+5511888888888"
    )
    test_db_session.add(empresa)
    test_db_session.commit()
    test_db_session.refresh(empresa)
    return empresa

@pytest.fixture
def sample_usuario(test_db_session, sample_empresa):
    """Cria um usuário de exemplo para testes"""
    from passlib.hash import bcrypt
    
    usuario = Usuario(
        email="admin@test.com",
        senha_hash=bcrypt.hash("test123"),
        is_superuser=True,
        empresa_id=sample_empresa.id
    )
    test_db_session.add(usuario)
    test_db_session.commit()
    test_db_session.refresh(usuario)
    return usuario

@pytest.fixture
def sample_mensagem(test_db_session, sample_empresa):
    """Cria uma mensagem de exemplo para testes"""
    mensagem = Mensagem(
        empresa_id=sample_empresa.id,
        cliente_id="test-cliente-123",
        text="Olá, preciso de ajuda",
        is_bot=False
    )
    test_db_session.add(mensagem)
    test_db_session.commit()
    test_db_session.refresh(mensagem)
    return mensagem

@pytest.fixture
def auth_headers(sample_usuario):
    """Cria headers de autenticação para testes"""
    from jose import jwt
    from config import Config
    
    config = Config()
    token = jwt.encode(
        {"sub": sample_usuario.email, "exp": 9999999999},
        config.SECRET_KEY,
        algorithm=config.ALGORITHM
    )
    return {"Authorization": f"Bearer {token}"} 