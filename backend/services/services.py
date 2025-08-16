import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from config import Config
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from models import Mensagem, Cliente, Atendimento, Atividade, Empresa

logger = logging.getLogger(__name__)

class DatabaseService:
    """Serviço para gerenciar dados no banco de dados"""
    
    def __init__(self):
        self.engine = create_engine(Config.POSTGRES_URL)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
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

            # Classificação LLM opcional: apenas para mensagens do cliente
            try:
                if not is_bot:
                    # Carregar labels_json e openai_key
                    from sqlalchemy.orm import Session as SASession
                    from services.unified_config_service import get_openai_config
                    s2: SASession = self.SessionLocal()
                    try:
                        empresa = s2.query(Empresa).filter(Empresa.id == empresa_id).first()
                        labels_json = getattr(empresa, 'labels_json', None) if empresa else None
                        if labels_json and isinstance(labels_json, dict) and labels_json.get('labels'):
                            openai_cfg = get_openai_config(s2, empresa_id) or {}
                            api_key = openai_cfg.get('openai_key')
                            if api_key:
                                from integrations.openai_service import OpenAIService
                                oai = OpenAIService(api_key)
                                result = oai.classify_message(text, labels_json)
                                min_conf = labels_json.get('min_confidence', 0.6)
                                if result.get('label') and float(result.get('confidence', 0.0)) >= float(min_conf):
                                    atend = Atendimento(
                                        empresa_id=empresa_id,
                                        cliente_id=cliente_id,
                                        data_atendimento=mensagem.timestamp,
                                        label_slug=result['label'],
                                        source_message_id=mensagem.id,
                                        observacoes=result.get('observacoes'),
                                        confidence=int(round(float(result.get('confidence', 0.0)) * 100))
                                    )
                                    s2.add(atend)
                                    try:
                                        s2.commit()
                                    except Exception as ce:
                                        s2.rollback()
                                        logger.warning(f"Não foi possível salvar atendimento classificado (provável duplicado): {ce}")
                    finally:
                        s2.close()
            except Exception as ce:
                logger.error(f"Erro na classificação opcional: {ce}")

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
            # Buscar todas as empresas
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            from models import Empresa
            from config import Config
            
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
            from models import Empresa
            from config import Config
            
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