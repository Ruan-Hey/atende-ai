import redis
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from config import Config
import asyncio

# Importar serviços de integração
from integrations.openai_service import OpenAIService
from integrations.twilio_service import TwilioService
from integrations.google_sheets_service import GoogleSheetsService
# Chatwoot removido - não mais necessário
from integrations.google_calendar_service import GoogleCalendarService
from services.message_buffer import MessageBuffer

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import redis
from config import Config
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from models import Mensagem, Empresa, Atendimento, Cliente, Atividade

logger = logging.getLogger(__name__)

class DatabaseService:
    """Serviço para gerenciar dados no banco de dados"""
    
    def __init__(self):
        self.engine = create_engine(Config.POSTGRES_URL)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def save_message(self, empresa_id: int, cliente_id: str, text: str, is_bot: bool = False):
        """Salva mensagem no banco de dados"""
        session = self.SessionLocal()
        try:
            mensagem = Mensagem(
                empresa_id=empresa_id,
                cliente_id=cliente_id,
                text=text,
                is_bot=is_bot
            )
            session.add(mensagem)
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
        """Conta total de atendimentos de uma empresa"""
        session = self.SessionLocal()
        try:
            # Conta clientes únicos que interagiram hoje
            hoje = datetime.now().date()
            count = session.query(func.count(func.distinct(Mensagem.cliente_id))).filter(
                Mensagem.empresa_id == empresa_id,
                func.date(Mensagem.timestamp) == hoje
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
        """Busca atividades recentes do banco de dados"""
        session = self.SessionLocal()
        try:
            # Buscar mensagens recentes agrupadas por cliente
            recent_messages = session.query(
                Mensagem.cliente_id,
                func.max(Mensagem.timestamp).label('ultima_mensagem'),
                func.count(Mensagem.id).label('total_mensagens')
            ).filter(
                Mensagem.empresa_id == empresa_id
            ).group_by(Mensagem.cliente_id).order_by(
                func.max(Mensagem.timestamp).desc()
            ).limit(limit).all()
            
            activities = []
            for msg in recent_messages:
                activities.append({
                    'cliente': msg.cliente_id,
                    'tipo_atividade': 'mensagem',
                    'timestamp': msg.ultima_mensagem.isoformat(),
                    'total_mensagens': msg.total_mensagens
                })
            
            return activities
        except Exception as e:
            logger.error(f"Erro ao buscar atividades: {e}")
            return []
        finally:
            session.close()

class RedisService:
    """Serviço para gerenciar contexto e cache no Redis"""
    
    def __init__(self):
        self.redis_client = redis.from_url(Config.REDIS_URL)
    
    def get_context(self, cliente_id: str, empresa: str) -> Dict[str, Any]:
        """Recupera contexto de conversa do cliente"""
        key = f"context:{empresa}:{cliente_id}"
        data = self.redis_client.get(key)
        return json.loads(data) if data else {}
    
    def set_context(self, cliente_id: str, empresa: str, context: Dict[str, Any]):
        """Salva contexto de conversa do cliente"""
        key = f"context:{empresa}:{cliente_id}"
        self.redis_client.setex(key, 3600, json.dumps(context))  # Expira em 1 hora
    
    def add_message(self, cliente_id: str, empresa: str, message: str, is_bot: bool = False):
        """Adiciona mensagem ao histórico do cliente"""
        context = self.get_context(cliente_id, empresa)
        
        if 'messages' not in context:
            context['messages'] = []
        
        context['messages'].append({
            'text': message,
            'is_bot': is_bot,
            'timestamp': datetime.now().isoformat()
        })
        
        # Manter apenas as últimas 10 mensagens
        if len(context['messages']) > 10:
            context['messages'] = context['messages'][-10:]
        
        self.set_context(cliente_id, empresa, context)
    
    def clear_context(self, cliente_id: str, empresa: str):
        """Limpa todo o contexto de um cliente"""
        key = f"context:{empresa}:{cliente_id}"
        self.redis_client.delete(key)
        logger.info(f"Contexto limpo para {empresa}:{cliente_id}")

class MessageProcessor:
    """Processador de mensagens do WhatsApp com integrações completas e buffer"""
    
    def __init__(self, buffer_timeout: int = 10):
        self.redis_service = RedisService()
        self.database_service = DatabaseService()
        self.message_buffer = MessageBuffer(buffer_timeout)
        
        # Inicializar serviços de integração (será configurado por empresa)
        self.google_calendar_service = None
        
        # Configurar callback do buffer
        self.message_buffer.set_callback(self._process_buffered_message)
    
    def add_message_to_buffer(self, webhook_data: Dict[str, Any], empresa: str):
        """Adiciona mensagem ao buffer para agrupamento"""
        self.message_buffer.add_message(
            webhook_data.get('WaId', ''),
            empresa,
            webhook_data
        )
    
    async def _process_buffered_message(self, webhook_data: Dict[str, Any], empresa: str):
        """Processa mensagem do buffer (callback)"""
        try:
            cliente_id = webhook_data.get('WaId', '')
            message_text = webhook_data.get('Body', '')
            message_type = webhook_data.get('MessageType', 'text')
            profile_name = webhook_data.get('ProfileName', 'Cliente')
            
            # Carregar configuração da empresa do banco de dados
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            from models import Empresa
            
            engine = create_engine(Config.POSTGRES_URL)
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            session = SessionLocal()
            
            try:
                empresa_db = session.query(Empresa).filter(Empresa.slug == empresa).first()
                if empresa_db:
                    empresa_config = {
                        'nome': empresa_db.nome,
                        'openai_key': empresa_db.openai_key,
                        'twilio_sid': empresa_db.twilio_sid,
                        'twilio_token': empresa_db.twilio_token,
                        'twilio_number': empresa_db.twilio_number,
                        'chatwoot_url': empresa_db.chatwoot_origem,
                        'chatwoot_token': empresa_db.chatwoot_token,
                        'chatwoot_account_id': 2,
                        'mensagem_quebrada': empresa_db.mensagem_quebrada or False,
                        'prompt': empresa_db.prompt
                    }
                else:
                    logger.error(f"Empresa não encontrada no banco: {empresa}")
                    empresa_config = {}
            except Exception as e:
                logger.warning(f"Erro ao buscar empresa {empresa} no banco: {e}")
                empresa_config = {}
            finally:
                session.close()
            
            # Salvar mensagem no banco de dados
            try:
                self.database_service.save_message(empresa_db.id, cliente_id, message_text, is_bot=False)
            except Exception as e:
                logger.error(f"Erro ao salvar mensagem no banco: {e}")
            
            # Adicionar mensagem ao contexto (apenas para processamento atual)
            self.redis_service.add_message(cliente_id, empresa, message_text, is_bot=False)
            
            # Processar baseado no tipo de mensagem
            if message_type == 'audio':
                result = await self._process_audio_message(webhook_data, empresa, empresa_config)
            else:
                result = await self._process_text_message(webhook_data, empresa, empresa_config)
            
            # Log do resultado
            if result.get('success'):
                logger.info(f"Mensagem processada com sucesso para {empresa}:{cliente_id}")
            else:
                logger.error(f"Erro ao processar mensagem para {empresa}:{cliente_id}")
            
            return result
                
        except Exception as e:
            logger.error(f"Erro ao processar mensagem do buffer: {e}")
            return {
                'success': False,
                'message': 'Erro interno do servidor',
                'empresa': empresa,
                'cliente_id': webhook_data.get('WaId', '')
            }
    
    async def _process_text_message(self, webhook_data: Dict[str, Any], empresa: str, empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """Processa mensagem de texto com OpenAI"""
        try:
            cliente_id = webhook_data.get('WaId', '')
            message_text = webhook_data.get('Body', '')
            
            # Inicializar serviços
            openai_service = OpenAIService(empresa_config.get('openai_key', ''))
            twilio_service = TwilioService(
                empresa_config.get('twilio_sid', ''),
                empresa_config.get('twilio_token', ''),
                empresa_config.get('twilio_number', '')
            )
            # Chatwoot removido - não mais necessário
            
            # Obter contexto da conversa
            context = self.redis_service.get_context(cliente_id, empresa)
            
            # Inicializar informações do cliente no contexto se não existirem
            if 'cliente_id' not in context:
                context['cliente_id'] = cliente_id
                context['empresa'] = empresa
                context['cliente_name'] = webhook_data.get('ProfileName', 'Cliente')
                context['empresa_name'] = empresa_config.get('nome', 'Empresa')
                self.redis_service.set_context(cliente_id, empresa, context)
            
            # Inicializar Google Calendar Service para esta empresa
            if self.google_calendar_service is None:
                config_path = f'../empresas/{empresa}/config.json'
                self.google_calendar_service = GoogleCalendarService(config_path)
            
            # Verificar se é uma solicitação de agendamento
            if self._is_scheduling_request(message_text, context):
                ai_response = await self._handle_scheduling_request(message_text, context, empresa_config)
            else:
                # Processar com OpenAI
                ai_response = openai_service.process_text_message(message_text, context, empresa_config)
            
            mensagem_quebrada = empresa_config.get('mensagem_quebrada', False)
            twilio_results = []
            parts = [ai_response]
            if mensagem_quebrada:
                # Quebra por dois enters ou outro critério
                parts = [p.strip() for p in ai_response.split('\n\n') if p.strip()]
            
            for part in parts:
                twilio_result = twilio_service.send_whatsapp_message(cliente_id, part)
                twilio_results.append(twilio_result)
                
                # Salvar resposta do bot no banco de dados
                try:
                    # Buscar empresa_id
                    session = self.database_service.SessionLocal()
                    empresa_db = session.query(Empresa).filter(Empresa.slug == empresa).first()
                    if empresa_db:
                        self.database_service.save_message(empresa_db.id, cliente_id, part, is_bot=True)
                    session.close()
                except Exception as e:
                    logger.error(f"Erro ao salvar resposta do bot no banco: {e}")
                
                # Adicionar resposta ao contexto (apenas para processamento atual)
                self.redis_service.add_message(cliente_id, empresa, part, is_bot=True)
                if mensagem_quebrada:
                    await asyncio.sleep(0.5)
            
            # Incrementar contador de atendimentos
            self._increment_attendance_count(empresa, cliente_id)
            logger.info(f"Atendimento processado para {empresa}:{cliente_id}")
            
            return {
                'success': True,
                'message': ai_response,
                'empresa': empresa,
                'cliente_id': cliente_id,
                'twilio_result': twilio_results
            }
        except Exception as e:
            logger.error(f"Erro ao processar mensagem de texto: {e}")
            return {
                'success': False,
                'message': 'Desculpe, tive um problema técnico. Pode tentar novamente?',
                'empresa': empresa,
                'cliente_id': webhook_data.get('WaId', '')
            }
    
    async def _process_audio_message(self, webhook_data: Dict[str, Any], empresa: str, empresa_config: Dict[str, Any]) -> Dict[str, Any]:
        """Processa mensagem de áudio com transcrição"""
        try:
            cliente_id = webhook_data.get('WaId', '')
            audio_url = webhook_data.get('MediaUrl0', '')
            
            if not audio_url:
                return {
                    'success': False,
                    'message': 'Não foi possível processar o áudio.',
                    'empresa': empresa,
                    'cliente_id': cliente_id
                }
            
            # Inicializar serviços
            openai_service = OpenAIService(empresa_config.get('openai_key', ''))
            twilio_service = TwilioService(
                empresa_config.get('twilio_sid', ''),
                empresa_config.get('twilio_token', ''),
                empresa_config.get('twilio_number', '')
            )
            
            # Transcrever áudio
            transcribed_text = openai_service.transcribe_audio(
                audio_url,
                empresa_config.get('twilio_sid', ''),
                empresa_config.get('twilio_token', '')
            )
            
            if not transcribed_text:
                return {
                    'success': False,
                    'message': 'Não foi possível transcrever o áudio. Pode enviar uma mensagem de texto?',
                    'empresa': empresa,
                    'cliente_id': cliente_id
                }
            
            # Processar texto transcrito
            context = self.redis_service.get_context(cliente_id, empresa)
            ai_response = openai_service.process_text_message(transcribed_text, context, empresa_config)
            
            # Enviar resposta
            twilio_result = twilio_service.send_whatsapp_message(cliente_id, ai_response)
            
            # Salvar mensagens no banco de dados
            try:
                session = self.database_service.SessionLocal()
                empresa_db = session.query(Empresa).filter(Empresa.slug == empresa).first()
                if empresa_db:
                    # Salvar transcrição do áudio
                    self.database_service.save_message(empresa_db.id, cliente_id, transcribed_text, is_bot=False)
                    # Salvar resposta do bot
                    self.database_service.save_message(empresa_db.id, cliente_id, ai_response, is_bot=True)
                session.close()
            except Exception as e:
                logger.error(f"Erro ao salvar mensagens de áudio no banco: {e}")
            
            # Adicionar ao contexto (apenas para processamento atual)
            self.redis_service.add_message(cliente_id, empresa, transcribed_text, is_bot=False)
            self.redis_service.add_message(cliente_id, empresa, ai_response, is_bot=True)
            
            return {
                'success': True,
                'message': ai_response,
                'empresa': empresa,
                'cliente_id': cliente_id,
                'transcribed_text': transcribed_text,
                'twilio_result': twilio_result
            }
            
        except Exception as e:
            logger.error(f"Erro ao processar áudio: {e}")
            return {
                'success': False,
                'message': 'Erro ao processar áudio. Pode tentar novamente?',
                'empresa': empresa,
                'cliente_id': webhook_data.get('WaId', '')
            }
    
    # Função _register_chatwoot_conversation removida - Chatwoot não mais necessário
    
    def get_buffer_status(self) -> Dict[str, Any]:
        """Retorna status do buffer de mensagens"""
        return self.message_buffer.get_buffer_status()
    
    def force_process_buffer(self, cliente_id: str, empresa: str):
        """Força o processamento do buffer imediatamente"""
        self.message_buffer.force_process_buffer(cliente_id, empresa)
    
    def _increment_attendance_count(self, empresa: str, cliente_id: str):
        """Função mantida para compatibilidade - atendimentos agora são contados do banco"""
        # Atendimentos são contados automaticamente do banco de dados
        # Não é mais necessário incrementar contadores no Redis
        pass
    
    def get_available_slots(self, date: str = None) -> Dict[str, Any]:
        """Retorna horários disponíveis para agendamento"""
        try:
            slots = self.google_calendar_service.get_available_slots(date)
            return {
                'success': True,
                'slots': slots,
                'message': f'Encontrados {len(slots)} horários disponíveis'
            }
        except Exception as e:
            logger.error(f"Erro ao buscar horários disponíveis: {e}")
            return {
                'success': False,
                'message': 'Erro ao verificar agenda',
                'slots': []
            }
    
    def schedule_meeting(self, email: str, name: str, company: str, date_time: str) -> Dict[str, Any]:
        """Agenda uma reunião"""
        try:
            result = self.google_calendar_service.schedule_meeting(email, name, company, date_time)
            return result
        except Exception as e:
            logger.error(f"Erro ao agendar reunião: {e}")
            return {
                'success': False,
                'message': f'Erro ao agendar reunião: {str(e)}'
            }
    
    def _is_scheduling_request(self, message: str, context: Dict[str, Any]) -> bool:
        """Verifica se a mensagem é uma solicitação de agendamento"""
        message_lower = message.lower()
        scheduling_keywords = [
            'agendar', 'marcar', 'reunião', 'encontro', 'consulta', 'horário',
            'disponível', 'agenda', 'quando', 'data', 'hora'
        ]
        
        # Verifica se há palavras-chave de agendamento
        has_keywords = any(keyword in message_lower for keyword in scheduling_keywords)
        
        # Verifica se já estamos no fluxo de agendamento
        is_in_scheduling_flow = context.get('scheduling_flow', False)
        
        return has_keywords or is_in_scheduling_flow
    
    def _find_email_in_context(self, context: Dict[str, Any]) -> str:
        """Busca email no histórico da conversa"""
        if 'messages' not in context:
            return None
        
        # Busca por email nas mensagens do cliente (não do bot)
        for message in context['messages']:
            if not message.get('is_bot', False):  # Só mensagens do cliente
                text = message.get('text', '').lower()
                # Padrão simples para detectar email
                if '@' in text and '.' in text:
                    # Extrai o email da mensagem
                    words = text.split()
                    for word in words:
                        if '@' in word and '.' in word:
                            # Remove caracteres extras
                            email = word.strip('.,!?;:')
                            if '@' in email and '.' in email:
                                return email
        
        return None
    
    async def _handle_scheduling_request(self, message: str, context: Dict[str, Any], empresa_config: Dict[str, Any]) -> str:
        """Processa solicitação de agendamento"""
        message_lower = message.lower()
        
        # Verificar se o cliente está pedindo novos horários
        if any(keyword in message_lower for keyword in ['novos', 'outros', 'mais', 'diferentes', 'desatualizados']):
            # Limpar contexto anterior e buscar novos horários
            context.pop('scheduling_flow', None)
            context.pop('available_slots', None)
            context.pop('chosen_slot', None)
            context.pop('scheduling_step', None)
            self.redis_service.set_context(context.get('cliente_id', ''), context.get('empresa', ''), context)
        
        # Se é a primeira solicitação de agendamento
        if not context.get('scheduling_flow'):
            # Buscar horários disponíveis
            slots_result = self.get_available_slots()
            
            if slots_result['success'] and slots_result['slots']:
                slots = slots_result['slots'][:5]  # Primeiros 5 horários
                slots_text = '\n'.join([f"- {slot['formatted']}" for slot in slots])
                
                # Salvar slots no contexto
                context['scheduling_flow'] = True
                context['available_slots'] = slots
                self.redis_service.set_context(context.get('cliente_id', ''), context.get('empresa', ''), context)
                
                return f"Perfeito! Vou verificar nossa agenda. Temos os seguintes horários disponíveis:\n{slots_text}\n\nQual desses horários funciona melhor para você?"
            else:
                return "Desculpe, não consegui verificar a agenda no momento. Pode tentar novamente em alguns minutos?"
        
        # Se já estamos no fluxo de agendamento
        elif context.get('scheduling_flow'):
            # Se ainda não escolheu horário
            if not context.get('scheduling_step'):
                # Verificar se o cliente escolheu um horário
                if any(str(i+1) in message_lower or slot['formatted'].lower() in message_lower 
                       for i, slot in enumerate(context.get('available_slots', []))):
                    
                    # Encontrar o slot escolhido
                    chosen_slot = None
                    for i, slot in enumerate(context.get('available_slots', [])):
                        if str(i+1) in message_lower or slot['formatted'].lower() in message_lower:
                            chosen_slot = slot
                            break
                    
                    if chosen_slot:
                        # Verificar se já temos email no contexto
                        existing_email = self._find_email_in_context(context)
                        
                        if existing_email:
                            # Se já temos email, agendar diretamente
                            result = self.schedule_meeting(
                                email=existing_email,
                                name=context.get('cliente_name', 'Cliente'),
                                company=context.get('empresa_name', 'Empresa'),
                                date_time=chosen_slot['datetime']
                            )
                            
                            if result['success']:
                                # Limpar contexto de agendamento
                                context.pop('scheduling_flow', None)
                                context.pop('available_slots', None)
                                context.pop('chosen_slot', None)
                                context.pop('scheduling_step', None)
                                self.redis_service.set_context(context.get('cliente_id', ''), context.get('empresa', ''), context)
                                
                                return f"Perfeito! Reunião agendada para {chosen_slot['formatted']}. Enviei o convite para {existing_email}. Você receberá um e-mail com o link da reunião. Até lá!"
                            else:
                                return f"Desculpe, tive um problema ao agendar a reunião: {result['message']}. Pode tentar novamente?"
                        else:
                            # Se não temos email, pedir
                            context['chosen_slot'] = chosen_slot
                            context['scheduling_step'] = 'waiting_email'
                            self.redis_service.set_context(context.get('cliente_id', ''), context.get('empresa', ''), context)
                            
                            return f"Ótimo! Você escolheu {chosen_slot['formatted']}. Agora preciso do seu e-mail para enviar o convite da reunião. Qual é o seu e-mail?"
                else:
                    return "Desculpe, não entendi. Pode escolher um dos horários que mencionei ou digite o número do horário?"
            
            # Se está esperando e-mail
            elif context.get('scheduling_step') == 'waiting_email':
                if '@' in message:
                    email = message.strip()
                    chosen_slot = context.get('chosen_slot')
                    
                    if chosen_slot and email:
                        # Agendar a reunião
                        result = self.schedule_meeting(
                            email=email,
                            name=context.get('cliente_name', 'Cliente'),
                            company=context.get('empresa_name', 'Empresa'),
                            date_time=chosen_slot['datetime']
                        )
                        
                        if result['success']:
                            # Limpar contexto de agendamento
                            context.pop('scheduling_flow', None)
                            context.pop('available_slots', None)
                            context.pop('chosen_slot', None)
                            context.pop('scheduling_step', None)
                            self.redis_service.set_context(context.get('cliente_id', ''), context.get('empresa', ''), context)
                            
                            return f"Perfeito! Reunião agendada para {chosen_slot['formatted']}. Enviei o convite para {email}. Você receberá um e-mail com o link da reunião. Até lá!"
                        else:
                            return f"Desculpe, tive um problema ao agendar a reunião: {result['message']}. Pode tentar novamente?"
                    else:
                        return "Desculpe, não consegui processar o agendamento. Pode tentar novamente?"
                else:
                    return "Por favor, me informe um e-mail válido para enviar o convite da reunião."
        
        return "Desculpe, não consegui processar sua solicitação. Pode tentar novamente?"

class MetricsService:
    """Serviço para métricas e estatísticas"""
    
    def __init__(self):
        self.redis_service = RedisService()
        self.database_service = DatabaseService()
    
    def get_admin_metrics(self) -> Dict[str, Any]:
        """Retorna métricas para o painel admin - versão otimizada"""
        try:
            # Buscar empresas do banco de dados
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            from models import Empresa
            
            engine = create_engine(Config.POSTGRES_URL)
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            session = SessionLocal()
            
            try:
                empresas_db = session.query(Empresa).all()
                empresas = [
                    {
                        'slug': empresa.slug,
                        'nome': empresa.nome,
                        'status': empresa.status
                    }
                    for empresa in empresas_db
                ]
            except Exception as e:
                logger.warning(f"Erro ao buscar empresas do banco: {e}")
                empresas = []
            finally:
                session.close()
            
            # Buscar dados do banco de dados
            total_atendimentos = 0
            total_clientes = 0
            total_reservas = 0
            
            empresas_metrics = []
            for empresa in empresas:
                try:
                    # Buscar empresa_id
                    empresa_db = session.query(Empresa).filter(Empresa.slug == empresa['slug']).first()
                    if empresa_db:
                        # Contar atendimentos (clientes únicos que interagiram hoje)
                        atendimentos = self.database_service.count_attendances(empresa_db.id)
                        # Contar clientes únicos totais
                        clientes = self.database_service.count_unique_clients(empresa_db.id)
                    else:
                        atendimentos = 0
                        clientes = 0
                        
                except Exception as e:
                    logger.warning(f"Erro ao buscar dados do banco para {empresa['slug']}: {e}")
                    atendimentos = 0
                    clientes = 0
                
                empresas_metrics.append({
                    'slug': empresa['slug'],
                    'nome': empresa['nome'],
                    'status': empresa['status'],
                    'atendimentos': atendimentos,
                    'reservas': 0,  # TODO: Implementar contador de reservas
                    'clientes': clientes
                })
                
                total_atendimentos += atendimentos
                total_clientes += clientes
            
            return {
                'total_empresas': len(empresas),
                'total_clientes': total_clientes,
                'total_reservas': total_reservas,
                'total_atendimentos': total_atendimentos,
                'empresas': empresas_metrics
            }
        except Exception as e:
            logger.error(f"Erro ao buscar métricas admin: {e}")
            # Retornar dados básicos se Redis falhar
            return {
                'total_empresas': 3,
                'total_clientes': 0,
                'total_reservas': 0,
                'total_atendimentos': 0,
                'empresas': [
                    {'slug': 'tinyteams', 'nome': 'TinyTeams', 'status': 'ativo', 'atendimentos': 0, 'reservas': 0, 'clientes': 0},
                    {'slug': 'pancia-piena', 'nome': 'Pancia Piena', 'status': 'ativo', 'atendimentos': 0, 'reservas': 0, 'clientes': 0},
                    {'slug': 'umas-e-ostras', 'nome': 'Umas e Ostras', 'status': 'ativo', 'atendimentos': 0, 'reservas': 0, 'clientes': 0}
                ]
            }
    
    def get_empresa_metrics(self, empresa_slug: str) -> Dict[str, Any]:
        """Retorna métricas específicas de uma empresa"""
        try:
            # Buscar dados da empresa no banco de dados
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            from models import Empresa
            
            engine = create_engine(Config.POSTGRES_URL)
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            session = SessionLocal()
            
            try:
                empresa_db = session.query(Empresa).filter(Empresa.slug == empresa_slug).first()
                if not empresa_db:
                    logger.error(f"Empresa não encontrada: {empresa_slug}")
                    return {
                        'nome': empresa_slug,
                        'atendimentos': 0,
                        'reservas': 0,
                        'clientes': 0,
                        'status': 'inativo',
                        'recent_activity': []
                    }
                
                status = empresa_db.status
                nome = empresa_db.nome
                logger.info(f"DEBUG: Empresa {empresa_slug} - Status do banco: {status}")
            except Exception as e:
                logger.warning(f"Erro ao buscar status da empresa {empresa_slug}: {e}")
                status = 'ativo'
                nome = empresa_slug
            finally:
                session.close()
            
            # Buscar dados do banco de dados
            atendimentos = self.database_service.count_attendances(empresa_db.id)
            clientes = self.database_service.count_unique_clients(empresa_db.id)
            recent_activity_list = self.database_service.get_recent_activities(empresa_db.id, limit=10)
            
            logger.info(f"DEBUG: Retornando status '{status}' para empresa {empresa_slug}")
            return {
                'nome': nome,
                'atendimentos': atendimentos,
                'reservas': 0,  # TODO: Implementar contador de reservas
                'clientes': clientes,
                'status': status,  # Usar status do banco de dados
                'recent_activity': recent_activity_list
            }
                
        except ValueError as e:
            logger.error(f"Empresa não encontrada: {empresa_slug}")
            return {
                'nome': empresa_slug,
                'atendimentos': 0,
                'reservas': 0,
                'clientes': 0,
                'status': 'inativo',
                'recent_activity': []
            } 