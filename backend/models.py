from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, Text, TIMESTAMP, ForeignKey, JSON, create_engine, func, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from passlib.hash import bcrypt

Base = declarative_base()

class Empresa(Base):
    __tablename__ = 'empresas'
    id = Column(Integer, primary_key=True)
    slug = Column(String(100), unique=True, nullable=False)
    nome = Column(String(255), nullable=False)
    prompt = Column(Text)
    status = Column(String(20), default="ativo")
    whatsapp_number = Column(String(30))
    twilio_sid = Column(String(255))
    twilio_token = Column(String(255))
    twilio_number = Column(String(30))
    usar_buffer = Column(Boolean)
    mensagem_quebrada = Column(Boolean)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    mensagens = relationship('Mensagem', back_populates='empresa')
    # New optional JSON field to store company knowledge (title/description items)
    knowledge_json = Column(JSON, nullable=True)
    # New optional JSON field to store label classification config per empresa
    labels_json = Column(JSON, nullable=True)

class Mensagem(Base):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey('empresas.id'))
    cliente_id = Column(String(100), nullable=False)
    text = Column(Text, nullable=False)
    is_bot = Column(Boolean, nullable=False)
    timestamp = Column(TIMESTAMP, server_default=func.now())
    empresa = relationship('Empresa', back_populates='mensagens')

class Atendimento(Base):
    __tablename__ = 'atendimentos'
    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey('empresas.id'))
    cliente_id = Column(String(100), nullable=False)
    data_atendimento = Column(TIMESTAMP, server_default=func.now())
    empresa = relationship('Empresa')
    # Classification fields (nullable for backward compatibility)
    label_slug = Column(String(100), nullable=True)
    source_message_id = Column(Integer, nullable=True)
    observacoes = Column(JSON, nullable=True)
    confidence = Column(Integer, nullable=True)  # stored as int percentage or can be float; keeping int for safety

class Cliente(Base):
    __tablename__ = 'clientes'
    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey('empresas.id'))
    cliente_id = Column(String(100), nullable=False)
    nome = Column(String(255), nullable=True)  # Nome do cliente do WhatsApp
    primeiro_atendimento = Column(TIMESTAMP, server_default=func.now())
    ultimo_atendimento = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    empresa = relationship('Empresa')
    __table_args__ = (UniqueConstraint('empresa_id', 'cliente_id', name='_cliente_empresa_uc'),)

class Atividade(Base):
    __tablename__ = 'atividades'
    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey('empresas.id'))
    cliente_id = Column(String(100), nullable=False)
    tipo = Column(String(50), nullable=False)  # 'atendimento', 'reserva', etc.
    descricao = Column(Text, nullable=False)
    timestamp = Column(TIMESTAMP, server_default=func.now())
    empresa = relationship('Empresa')

class WebhookData(BaseModel):
    """Dados recebidos do webhook do Twilio"""
    Body: str
    From: str
    To: str
    WaId: str
    MessageType: Optional[str] = "text"
    MediaUrl0: Optional[str] = None
    ProfileName: Optional[str] = None

class MessageResponse(BaseModel):
    """Resposta de mensagem processada"""
    success: bool
    message: str
    empresa: str
    cliente_id: str
    timestamp: datetime = Field(default_factory=datetime.now)

class AdminMetrics(BaseModel):
    """Métricas para o painel admin"""
    total_empresas: int
    total_clientes: int
    total_reservas: int
    total_atendimentos: int
    empresas: List[Dict[str, Any]]

class EmpresaMetrics(BaseModel):
    """Métricas específicas de uma empresa"""
    nome: str
    atendimentos: int
    reservas: int
    clientes: int
    status: str
    recent_activity: List[Dict[str, Any]]

class LogEntry(BaseModel):
    """Entrada de log"""
    level: str
    message: str
    empresa: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    details: Optional[Dict[str, Any]] = None

class HealthCheck(BaseModel):
    """Resposta de health check"""
    status: str
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = "1.0.0"

class Log(Base):
    __tablename__ = 'logs'
    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey('empresas.id'), nullable=True)
    level = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    details = Column(JSON)
    timestamp = Column(TIMESTAMP, server_default=func.now())
    empresa = relationship('Empresa')

class Usuario(Base):
    __tablename__ = 'usuarios'
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    senha_hash = Column(String(255), nullable=False)
    is_superuser = Column(Boolean, default=False)
    empresa_id = Column(Integer, ForeignKey('empresas.id'), nullable=True)
    # Configurações de notificação
    notifications_enabled = Column(Boolean, default=False)  # Usuário ativa/desativa notificações
    smart_agent_error_notifications = Column(Boolean, default=False)  # Notificações de erro do Smart Agent
    created_at = Column(TIMESTAMP, server_default=func.now())
    empresa = relationship('Empresa')
    __table_args__ = (UniqueConstraint('email', name='_usuario_email_uc'),)

class API(Base):
    """Modelo para APIs externas"""
    __tablename__ = "apis"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, index=True)
    descricao = Column(Text)
    url_documentacao = Column(String)
    url_base = Column(String)
    tipo_auth = Column(String)  # api_key, oauth, basic, etc
    schema_cache = Column(JSON)  # Cache do schema descoberto
    logo_url = Column(String)  # URL da logo da API
    ativo = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())

class EmpresaAPI(Base):
    """Modelo para APIs conectadas às empresas"""
    __tablename__ = "empresa_apis"
    
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"))
    api_id = Column(Integer, ForeignKey("apis.id"))
    config = Column(JSON)  # Configurações específicas (api_key, etc)
    ativo = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default=func.now())
    
    # Relacionamentos
    empresa = relationship("Empresa", back_populates="apis")
    api = relationship("API", back_populates="empresas")

# Adicionar relacionamento na classe Empresa
Empresa.apis = relationship("EmpresaAPI", back_populates="empresa")
API.empresas = relationship("EmpresaAPI", back_populates="api")

# (Modelo BufferMessage removido; debounce agora é em memória)

# Remover relacionamento dinamicamente adicionado se existir
if hasattr(Empresa, 'buffer_messages'):
    delattr(Empresa, 'buffer_messages')

class EmpresaReminder(Base):
    __tablename__ = 'empresa_reminders'
    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey('empresas.id'), nullable=False, index=True)
    enabled = Column(Boolean, default=False)
    provider = Column(String(50), default='Trinks')
    timezone = Column(String(64), default='America/Sao_Paulo')
    send_time_local = Column(String(8), nullable=False)  # HH:MM
    lead_days = Column(Integer, default=1)
    twilio_template_sid = Column(String(255), nullable=False)
    twilio_variable_order = Column(JSON, nullable=True)  # ex.: ["name","time","professional"]
    dedupe_strategy = Column(String(64), default='first_slot_per_day')
    next_run_at = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    empresa = relationship('Empresa')

class Notification(Base):
    __tablename__ = 'notifications'
    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey('empresas.id'), nullable=False, index=True)
    tipo = Column(String(50), nullable=False)  # ex.: 'confirmacao'
    appointment_id = Column(String(100), nullable=False)
    execution_date = Column(String(10), nullable=False)  # YYYY-MM-DD (dia do agendamento)
    to_number = Column(String(32), nullable=False)
    variables = Column(JSON, nullable=True)
    message_sid = Column(String(64), nullable=True)
    status = Column(String(32), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    empresa = relationship('Empresa')
    __table_args__ = (UniqueConstraint('empresa_id', 'tipo', 'appointment_id', 'execution_date', name='_uniq_notification'),)

def gerar_hash_senha(senha: str) -> str:
    return bcrypt.hash(senha) 