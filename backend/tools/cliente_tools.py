from typing import Dict, Any
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Cliente, Mensagem
from config import Config
import logging

logger = logging.getLogger(__name__)

class ClienteTools:
    """Ferramentas para operações com clientes"""
    
    def __init__(self):
        self.engine = create_engine(Config.POSTGRES_URL)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def buscar_cliente_info(self, cliente_id: str, empresa_id: int) -> str:
        """Busca informações do cliente no banco de dados"""
        try:
            session = self.SessionLocal()
            
            # Buscar cliente
            cliente = session.query(Cliente).filter(
                Cliente.empresa_id == empresa_id,
                Cliente.cliente_id == cliente_id
            ).first()
            
            if not cliente:
                return f"Cliente {cliente_id} não encontrado"
            
            # Buscar última mensagem
            ultima_mensagem = session.query(Mensagem).filter(
                Mensagem.empresa_id == empresa_id,
                Mensagem.cliente_id == cliente_id
            ).order_by(Mensagem.timestamp.desc()).first()
            
            # Contar total de mensagens
            total_mensagens = session.query(Mensagem).filter(
                Mensagem.empresa_id == empresa_id,
                Mensagem.cliente_id == cliente_id
            ).count()
            
            info = f"""
Cliente: {cliente.nome or cliente_id}
Primeira interação: {cliente.primeiro_atendimento}
Última interação: {cliente.ultimo_atendimento}
Total de mensagens: {total_mensagens}
"""
            
            if ultima_mensagem:
                info += f"Última mensagem: {ultima_mensagem.text[:100]}..."
            
            return info
            
        except Exception as e:
            logger.error(f"Erro ao buscar cliente: {e}")
            return f"Erro ao buscar informações do cliente {cliente_id}"
        finally:
            session.close()
    
    def get_conversation_history(self, cliente_id: str, empresa_id: int, limit: int = 10) -> str:
        """Busca histórico de conversa do cliente"""
        try:
            session = self.SessionLocal()
            
            mensagens = session.query(Mensagem).filter(
                Mensagem.empresa_id == empresa_id,
                Mensagem.cliente_id == cliente_id
            ).order_by(Mensagem.timestamp.desc()).limit(limit).all()
            
            if not mensagens:
                return "Nenhuma mensagem encontrada"
            
            history = "Histórico de conversa:\n"
            for msg in reversed(mensagens):  # Ordem cronológica
                role = "Bot" if msg.is_bot else "Cliente"
                history += f"{role}: {msg.text}\n"
            
            return history
            
        except Exception as e:
            logger.error(f"Erro ao buscar histórico: {e}")
            return "Erro ao buscar histórico de conversa"
        finally:
            session.close() 