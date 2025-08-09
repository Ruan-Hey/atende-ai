import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import sqlalchemy
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text, func
import os
import sys
from pathlib import Path

# Adicionar o diretório backend ao path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Imports absolutos com fallback
try:
    from models import Mensagem, Cliente, Atendimento, Atividade
except ImportError:
    from ..models import Mensagem, Cliente, Atendimento, Atividade

try:
    from config import Config
except ImportError:
    from ..config import Config

logger = logging.getLogger(__name__)

class DatabaseService:
    """Serviço para gerenciar dados no banco de dados"""
    
    def __init__(self):
        self.engine = create_engine(Config.POSTGRES_URL)
        self.SessionLocal = Session(bind=self.engine)
    
    def save_message(self, empresa_id: int, cliente_id: str, text: str, is_bot: bool = False, cliente_nome: str = None):
        """Salva mensagem no banco de dados e atualiza informações do cliente"""
        session = self.SessionLocal()
        try:
            # Salvar mensagem
            mensagem = Mensagem(
                empresa_id=empresa_id,
                cliente_id=cliente_id,
                text=text,
                is_bot=is_bot
            )
            session.add(mensagem)
            
            # Atualizar ou criar registro do cliente
            from ..models import Cliente
            cliente = session.query(Cliente).filter(
                Cliente.empresa_id == empresa_id,
                Cliente.cliente_id == cliente_id
            ).first()
            
            if cliente:
                # Atualizar último atendimento
                cliente.ultimo_atendimento = datetime.now()
                if cliente_nome and not cliente.nome:
                    cliente.nome = cliente_nome
            else:
                # Criar novo cliente
                cliente = Cliente(
                    empresa_id=empresa_id,
                    cliente_id=cliente_id,
                    nome=cliente_nome
                )
                session.add(cliente)
            
            session.commit()
            session.refresh(mensagem)  # Atualiza o objeto com o ID gerado
            logger.info(f"Mensagem salva no banco: {empresa_id}:{cliente_id}")
            return mensagem
        except Exception as e:
            session.rollback()
            logger.error(f"Erro ao salvar mensagem: {e}")
            raise
        finally:
            session.close()
    
    def get_conversation_history(self, empresa_id: int, cliente_id: str, limit: int = 20) -> List[Dict]:
        """Busca histórico de conversa do banco de dados"""
        session = self.SessionLocal()
        try:
            mensagens = session.query(Mensagem).filter(
                Mensagem.empresa_id == empresa_id,
                Mensagem.cliente_id == cliente_id
            ).order_by(Mensagem.timestamp.desc()).limit(limit).all()
            
            # Converter para formato esperado pelo frontend
            history = []
            for msg in reversed(mensagens):  # Ordem cronológica
                history.append({
                    'text': msg.text,
                    'is_bot': msg.is_bot,
                    'timestamp': msg.timestamp.isoformat()
                })
            
            return history
        except Exception as e:
            logger.error(f"Erro ao buscar histórico: {e}")
            return []
        finally:
            session.close()
    
    def count_attendances(self, empresa_id: int) -> int:
        """Conta total de atendimentos de uma empresa (por dia)"""
        session = self.SessionLocal()
        try:
            # Conta atendimentos únicos por cliente e por dia
            # Cada dia diferente de interação conta como um atendimento separado
            count = session.query(func.count(func.distinct(
                func.concat(Mensagem.cliente_id, '-', func.date(Mensagem.timestamp))
            ))).filter(
                Mensagem.empresa_id == empresa_id
            ).scalar()
            return count or 0
        except Exception as e:
            logger.error(f"Erro ao contar atendimentos: {e}")
            return 0
        finally:
            session.close()
    
    def count_unique_clients(self, empresa_id: int) -> int:
        """Conta total de clientes únicos de uma empresa"""
        session = self.SessionLocal()
        try:
            count = session.query(func.count(func.distinct(Mensagem.cliente_id))).filter(
                Mensagem.empresa_id == empresa_id
            ).scalar()
            return count or 0
        except Exception as e:
            logger.error(f"Erro ao contar clientes únicos: {e}")
            return 0
        finally:
            session.close()
    
    def get_recent_activities(self, empresa_id: int, limit: int = 10) -> List[Dict]:
        """Busca atividades recentes de uma empresa"""
        session = self.SessionLocal()
        try:
            # Buscar mensagens recentes
            mensagens = session.query(Mensagem).filter(
                Mensagem.empresa_id == empresa_id
            ).order_by(Mensagem.timestamp.desc()).limit(limit).all()
            
            activities = []
            for msg in mensagens:
                activities.append({
                    'type': 'message',
                    'cliente_id': msg.cliente_id,
                    'text': msg.text[:100] + '...' if len(msg.text) > 100 else msg.text,
                    'is_bot': msg.is_bot,
                    'timestamp': msg.timestamp.isoformat()
                })
            
            return activities
        except Exception as e:
            logger.error(f"Erro ao buscar atividades: {e}")
            return []
        finally:
            session.close()

class MetricsService:
    """Serviço para métricas e analytics"""
    
    def __init__(self):
        self.db_service = DatabaseService()
    
    def get_admin_metrics(self) -> Dict[str, Any]:
        """Retorna métricas para o painel admin"""
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            
            try:
                from models import Empresa
                from config import Config
            except ImportError:
                from ..models import Empresa
                from ..config import Config
            
            engine = create_engine(Config.POSTGRES_URL)
            SessionLocal = sessionmaker(bind=engine)
            session = SessionLocal()
            
            try:
                empresas = session.query(Empresa).all()
                
                total_empresas = len(empresas)
                total_atendimentos = 0
                total_clientes = 0
                
                for empresa in empresas:
                    atendimentos = self.db_service.count_attendances(empresa.id)
                    clientes = self.db_service.count_unique_clients(empresa.id)
                    total_atendimentos += atendimentos
                    total_clientes += clientes
                
                # Preparar lista de empresas para o frontend
                empresas_list = []
                for empresa in empresas:
                    atendimentos = self.db_service.count_attendances(empresa.id)
                    clientes = self.db_service.count_unique_clients(empresa.id)
                    empresas_list.append({
                        'id': empresa.id,
                        'nome': empresa.nome,
                        'slug': empresa.slug,
                        'atendimentos': atendimentos,
                        'clientes': clientes,
                        'status': 'ativo'
                    })
                
                return {
                    'total_empresas': total_empresas,
                    'total_clientes': total_clientes,
                    'total_reservas': 0,  # Não implementado ainda
                    'total_atendimentos': total_atendimentos,
                    'empresas': empresas_list
                }
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Erro ao buscar métricas admin: {e}")
            return {
                'total_empresas': 0,
                'total_atendimentos_hoje': 0,
                'total_clientes': 0,
                'empresas_ativas': 0,
                'status': 'error',
                'error': str(e)
            }
    
    def get_empresa_metrics(self, empresa_slug: str) -> Dict[str, Any]:
        """Retorna métricas para uma empresa específica"""
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            from ..models import Empresa
            from .config import Config
            
            engine = create_engine(Config.POSTGRES_URL)
            SessionLocal = sessionmaker(bind=engine)
            session = SessionLocal()
            
            try:
                empresa = session.query(Empresa).filter(Empresa.slug == empresa_slug).first()
                if not empresa:
                    return {
                        'status': 'error',
                        'error': 'Empresa não encontrada'
                    }
                
                atendimentos = self.db_service.count_attendances(empresa.id)
                clientes = self.db_service.count_unique_clients(empresa.id)
                recent_activity = self.db_service.get_recent_activities(empresa.id, 5)
                
                return {
                    'nome': empresa.nome,
                    'atendimentos': atendimentos,
                    'reservas': 0,  # Não implementado ainda
                    'clientes': clientes,
                    'status': empresa.status or 'ativo',
                    'recent_activity': recent_activity
                }
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Erro ao buscar métricas da empresa {empresa_slug}: {e}")
            return {
                'nome': 'Erro',
                'atendimentos': 0,
                'reservas': 0,
                'clientes': 0,
                'status': 'erro',
                'recent_activity': []
            } 