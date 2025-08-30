"""
Modelos para Web Push Notifications
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from ..models import Base

class PushSubscription(Base):
    """Modelo para armazenar subscriptions de web push"""
    __tablename__ = "push_subscriptions"
    __table_args__ = {"schema": "notifications"}
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("public.usuarios.id"), nullable=False)
    empresa_id = Column(Integer, ForeignKey("public.empresas.id"), nullable=True)
    endpoint = Column(Text, nullable=False)
    p256dh = Column(String(255), nullable=False)
    auth = Column(String(255), nullable=False)
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos (simples, sem back_populates para evitar dependência cruzada)
    # usuario = relationship("Usuario")
    # empresa = relationship("Empresa")

class NotificationRule(Base):
    """Modelo para regras de notificação configuráveis"""
    __tablename__ = "notification_rules"
    __table_args__ = {"schema": "notifications"}
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), nullable=False)
    tipo = Column(String(100), nullable=False)  # 'agente_error', 'monitoring', 'system_error'
    condicao = Column(JSON, nullable=False)  # Condições específicas da regra
    destinatarios = Column(JSON, nullable=False)  # Quem recebe: ['admin', 'empresa', 'todos']
    empresa_id = Column(Integer, ForeignKey("public.empresas.id"), nullable=True)  # ID da empresa específica
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamento
    # empresa = relationship("Empresa")

class NotificationLog(Base):
    """Modelo para log de notificações enviadas"""
    __tablename__ = "notification_logs"
    __table_args__ = {"schema": "notifications"}
    
    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, nullable=True)  # Sem foreign key por enquanto
    empresa_id = Column(Integer, nullable=True)  # Sem foreign key por enquanto
    usuario_id = Column(Integer, nullable=True)  # Sem foreign key por enquanto
    titulo = Column(String(255), nullable=False)
    mensagem = Column(Text, nullable=False)
    dados = Column(JSON, nullable=True)  # Dados adicionais do contexto
    status = Column(String(100), nullable=False)  # 'enviado', 'falha', 'pendente'
    created_at = Column(DateTime, default=datetime.utcnow)
