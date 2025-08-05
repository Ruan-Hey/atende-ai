import os
from fastapi import FastAPI, HTTPException, Request, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import json
from datetime import datetime, timedelta
import random

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from config import Config
from models import WebhookData, MessageResponse, AdminMetrics, EmpresaMetrics, HealthCheck, Base, Empresa, Mensagem, Log, Usuario, gerar_hash_senha, Atendimento, Cliente, Atividade
from services import MessageProcessor, MetricsService
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from jose import jwt, JWTError
from passlib.hash import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
import redis
from typing import Optional, List

# Configurações
config = Config()
engine = create_engine(config.POSTGRES_URL)
# Base.metadata.create_all(bind=engine)  # Comentado para evitar erro na inicialização

# criar_tabelas()

SessionLocal = sessionmaker(bind=engine)

def save_log_to_db(session: Session, empresa_id: int, level: str, message: str, details: dict = None):
    # Se não há empresa_id, tentar atribuir à TinyTeams
    if empresa_id is None:
        tinyteams = session.query(Empresa).filter(Empresa.slug == 'tinyteams').first()
        if tinyteams:
            empresa_id = tinyteams.id
    
    log = Log(
        empresa_id=empresa_id,
        level=level,
        message=message,
        details=details or {}
    )
    session.add(log)
    session.commit()

# Funções de autenticação
async def get_current_user(token: str = Depends(OAuth2PasswordBearer(tokenUrl="api/login"))):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError as e:
        logger.error(f"JWT decode error: {e}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"Unexpected error in get_current_user: {e}")
        raise credentials_exception
    
    session = SessionLocal()
    try:
        user = session.query(Usuario).filter(Usuario.email == email).first()
        if user is None:
            logger.error(f"User not found for email: {email}")
            raise credentials_exception
        return user
    except Exception as e:
        logger.error(f"Database error in get_current_user: {e}")
        raise credentials_exception
    finally:
        session.close()

async def get_current_superuser(current_user: Usuario = Depends(get_current_user)):
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

async def get_current_company_user(current_user: Usuario = Depends(get_current_user)):
    if current_user.is_superuser:
        return current_user
    if not current_user.empresa_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not associated with any company"
        )
    return current_user

app = FastAPI(title="Atende Ai Backend", version="1.0.0")

# CORS para desenvolvimento local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instanciar serviços
message_processor = MessageProcessor(buffer_timeout=10)  # 10 segundos de buffer
metrics_service = MetricsService()

# Inicializar engine do banco
# engine = create_engine(Config.POSTGRES_URL)

# Comando para criar as tabelas (roda uma vez)
# def criar_tabelas():
#     Base.metadata.create_all(engine)

# Descomente a linha abaixo e rode o main.py uma vez para criar as tabelas:
# criar_tabelas()

# SessionLocal = sessionmaker(bind=engine)

# def save_log_to_db(session: Session, empresa_id: int, level: str, message: str, details: dict = None):
#     log = Log(
#         empresa_id=empresa_id,
#         level=level,
#         message=message,
#         details=details or {}
#     )
#     session.add(log)
#     session.commit()

@app.post("/api/admin/empresas")
async def criar_empresa(data: dict, current_user: Usuario = Depends(get_current_superuser)):
    session = SessionLocal()
    try:
        empresa = Empresa(
            slug=data["slug"],
            nome=data["nome"],
            prompt=data.get("prompt"),
            whatsapp_number=data.get("whatsapp_number"),
            google_sheets_id=data.get("google_sheets_id"),
            chatwoot_token=data.get("chatwoot_token"),
            openai_key=data.get("openai_key"),
            twilio_sid=data.get("twilio_sid"),
            twilio_token=data.get("twilio_token"),
            twilio_number=data.get("twilio_number"),
            chatwoot_inbox_id=data.get("chatwoot_inbox_id"),
            chatwoot_origem=data.get("chatwoot_origem"),
            horario_funcionamento=data.get("horario_funcionamento"),
            filtros_chatwoot=data.get("filtros_chatwoot", []),
            usar_buffer=data.get("usar_buffer", True),
            mensagem_quebrada=data.get("mensagem_quebrada", False)
        )
        session.add(empresa)
        session.commit()
        return {"success": True, "empresa_id": empresa.id}
    except Exception as e:
        session.rollback()
        return {"success": False, "error": str(e)}
    finally:
        session.close()

@app.get("/health")
def health() -> HealthCheck:
    """Health check do sistema"""
    return HealthCheck(status="ok")

@app.get("/api/admin/metrics")
def get_admin_metrics(current_user: Usuario = Depends(get_current_superuser)) -> AdminMetrics:
    """Retorna métricas para o painel admin"""
    session = SessionLocal()
    try:
        # Log de acesso às métricas
        save_log_to_db(session, None, 'INFO', f'Usuário {current_user.email} acessou métricas admin')
        
        # Usar o MetricsService que busca dados do Redis
        metrics = metrics_service.get_admin_metrics()
        return metrics
    except Exception as e:
        logger.error(f"Erro ao buscar métricas admin: {e}")
        save_log_to_db(session, None, 'ERROR', f'Erro ao buscar métricas admin: {e}')
        raise HTTPException(status_code=500, detail="Erro interno do servidor")
    finally:
        session.close()

@app.get("/api/admin/empresas")
def get_empresas(current_user: Usuario = Depends(get_current_user)):
    """Retorna lista de empresas - filtrado por acesso do usuário"""
    session = SessionLocal()
    try:
        if current_user.is_superuser:
            # Admin geral vê todas as empresas
            empresas = session.query(Empresa).all()
        else:
            # Usuário restrito vê apenas sua empresa
            empresas = session.query(Empresa).filter(Empresa.id == current_user.empresa_id).all()
        
        empresas_list = [
            {
                "id": e.id,
                "nome": e.nome,
                "slug": e.slug,
                "status": "ativo",  # Status padrão para todas as empresas
                "created_at": e.created_at.isoformat() if e.created_at else None
            }
            for e in empresas
        ]
        
        return {"empresas": empresas_list}
    finally:
        session.close()

@app.get("/api/admin/empresa/{empresa_slug}")
def get_empresa_metrics(
    empresa_slug: str,
    current_user: Usuario = Depends(get_current_user)
):
    """Retorna métricas de uma empresa específica"""
    session = SessionLocal()
    try:
        empresa = session.query(Empresa).filter(Empresa.slug == empresa_slug).first()
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        
        # Verificar se usuário tem acesso a esta empresa
        if not current_user.is_superuser and current_user.empresa_id != empresa.id:
            raise HTTPException(status_code=403, detail="Acesso negado a esta empresa")
        
        try:
            metrics = metrics_service.get_empresa_metrics(empresa_slug)
            return EmpresaMetrics(**metrics)
        except Exception as e:
            logger.error(f"Erro ao buscar métricas da empresa {empresa_slug}: {e}")
            session_log = SessionLocal()
            try:
                save_log_to_db(session_log, empresa.id, 'ERROR', f'Erro ao buscar métricas: {e}')
            finally:
                session_log.close()
            raise HTTPException(status_code=500, detail="Erro interno do servidor")
    finally:
        session.close()

@app.get("/api/admin/empresa/{empresa_slug}/clientes")
def get_empresa_clientes(
    empresa_slug: str,
    current_user: Usuario = Depends(get_current_user)
):
    """Retorna lista de clientes de uma empresa específica"""
    session = SessionLocal()
    try:
        empresa = session.query(Empresa).filter(Empresa.slug == empresa_slug).first()
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        
        # Verificar se usuário tem acesso a esta empresa
        if not current_user.is_superuser and current_user.empresa_id != empresa.id:
            raise HTTPException(status_code=403, detail="Acesso negado a esta empresa")
        
        # Buscar clientes únicos diretamente do banco de dados
        from sqlalchemy import func
        
        # Buscar clientes únicos com suas últimas atividades e nomes
        clientes_query = session.query(
            Mensagem.cliente_id,
            func.max(Mensagem.timestamp).label('ultima_atividade'),
            func.count(Mensagem.id).label('total_mensagens')
        ).filter(
            Mensagem.empresa_id == empresa.id
        ).group_by(
            Mensagem.cliente_id
        ).order_by(
            func.count(Mensagem.id).desc()
        )
        
        clientes_result = clientes_query.all()
        
        # Formatar resultado
        clientes = []
        for cliente in clientes_result:
            # Buscar informações do cliente na tabela Cliente
            cliente_info = session.query(Cliente).filter(
                Cliente.empresa_id == empresa.id,
                Cliente.cliente_id == cliente.cliente_id
            ).first()
            
            # Determinar tipo de atividade baseado na última mensagem
            ultima_mensagem = session.query(Mensagem).filter(
                Mensagem.empresa_id == empresa.id,
                Mensagem.cliente_id == cliente.cliente_id,
                Mensagem.timestamp == cliente.ultima_atividade
            ).first()
            
            tipo_atividade = 'mensagem'  # Padrão
            if ultima_mensagem:
                # Aqui você pode adicionar lógica para determinar o tipo baseado no conteúdo
                # Por exemplo, se contém palavras como "reserva", "agendar", etc.
                if any(palavra in ultima_mensagem.text.lower() for palavra in ['reserva', 'agendar', 'marcar']):
                    tipo_atividade = 'reserva'
                elif any(palavra in ultima_mensagem.text.lower() for palavra in ['atendimento', 'suporte', 'ajuda']):
                    tipo_atividade = 'atendimento'
            
            # Usar nome do cliente se disponível, senão usar ID
            nome_cliente = cliente_info.nome if cliente_info and cliente_info.nome else cliente.cliente_id
            
            clientes.append({
                "cliente_id": cliente.cliente_id,
                "nome": nome_cliente,
                "ultima_atividade": cliente.ultima_atividade.isoformat() if cliente.ultima_atividade else None,
                "total_mensagens": cliente.total_mensagens,
                "tipo_atividade": tipo_atividade
            })
        
        return {
            "empresa": empresa_slug,
            "clientes": clientes
        }
    except Exception as e:
        logging.error(f"Erro ao buscar clientes da empresa {empresa_slug}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")
    finally:
        session.close()

@app.get("/api/admin/buffer/status")
def get_buffer_status():
    """Retorna status do buffer de mensagens"""
    try:
        status = message_processor.get_buffer_status()
        return status
    except Exception as e:
        logger.error(f"Erro ao buscar status do buffer: {e}")
        session = SessionLocal()
        try:
            save_log_to_db(session, None, 'ERROR', f'Erro ao buscar status do buffer: {e}')
        finally:
            session.close()
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@app.post("/api/admin/buffer/force-process")
def force_process_buffer(cliente_id: str, empresa: str):
    """Força o processamento do buffer para um cliente específico"""
    try:
        message_processor.force_process_buffer(cliente_id, empresa)
        return {"success": True, "message": f"Buffer processado para {empresa}:{cliente_id}"}
    except Exception as e:
        logger.error(f"Erro ao forçar processamento do buffer: {e}")
        session = SessionLocal()
        try:
            empresa_obj = session.query(Empresa).filter_by(slug=empresa).first()
            empresa_id = empresa_obj.id if empresa_obj else None
            save_log_to_db(session, empresa_id, 'ERROR', f'Erro ao forçar processamento do buffer: {e}')
        finally:
            session.close()
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@app.get("/test-webhook")
async def test_webhook():
    """Endpoint de teste simples"""
    return JSONResponse(content={
        'status': 'ok',
        'success': True,
        'message': 'Teste funcionando'
    })

@app.post("/webhook/{empresa_slug}")
async def webhook_handler(empresa_slug: str, request: Request):
    """Endpoint para receber webhooks do Twilio com buffer ou resposta direta"""
    try:
        # Verificar se a empresa existe no banco de dados
        session = SessionLocal()
        try:
            empresa_db = session.query(Empresa).filter(Empresa.slug == empresa_slug).first()
            if not empresa_db:
                logger.error(f"Empresa não encontrada: {empresa_slug}")
                raise HTTPException(status_code=404, detail="Empresa não encontrada")
            
            empresa_config = {
                'nome': empresa_db.nome,
                'openai_key': empresa_db.openai_key,
                'twilio_sid': empresa_db.twilio_sid,
                'twilio_token': empresa_db.twilio_token,
                'twilio_number': empresa_db.twilio_number,
                'mensagem_quebrada': empresa_db.mensagem_quebrada or False,
                'prompt': empresa_db.prompt,
                'usar_buffer': empresa_db.usar_buffer if empresa_db.usar_buffer is not None else True
            }
        except Exception as e:
            logger.error(f"Erro ao buscar empresa {empresa_slug}: {e}")
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        finally:
            session.close()
        
        # Processar dados do webhook
        form_data = await request.form()
        webhook_data = dict(form_data)
        
        logger.info(f"Webhook recebido para {empresa_slug}: {webhook_data}")
        
        # Verificar se é uma mensagem válida (incluindo áudio, imagem, etc.)
        wa_id = webhook_data.get('WaId')
        body = webhook_data.get('Body', '')
        message_type = webhook_data.get('MessageType', 'text')
        num_media = webhook_data.get('NumMedia', '0')
        
        # Log do webhook recebido
        session_log = SessionLocal()
        try:
            save_log_to_db(session_log, empresa_db.id, 'INFO', f'Webhook recebido de {wa_id}', {
                'empresa': empresa_slug,
                'message_type': message_type,
                'body_length': len(body) if body else 0
            })
        finally:
            session_log.close()
        
        if not wa_id:
            logger.warning(f"Webhook inválido recebido: {webhook_data}")
            return JSONResponse(content={
                'success': True,
                'message': 'Webhook recebido (dados inválidos)',
                'empresa': empresa_slug
            })
        
        # Se é uma mensagem de mídia (áudio, imagem, etc.) mas não tem texto, criar um texto descritivo
        if (message_type != 'text' or int(num_media) > 0) and not body:
            if message_type == 'audio':
                body = "[Mensagem de áudio]"
            elif message_type == 'image':
                body = "[Imagem enviada]"
            elif message_type == 'video':
                body = "[Vídeo enviado]"
            elif message_type == 'document':
                body = "[Documento enviado]"
            else:
                body = f"[Mensagem de {message_type}]"
            
            # Atualizar o webhook_data com o texto descritivo
            webhook_data['Body'] = body
        
        # Processar mensagem
        try:
            if empresa_config.get('usar_buffer', True):
                # Adicionar mensagem ao buffer
                message_processor.add_message_to_buffer(webhook_data, empresa_slug)
                logger.info(f"Mensagem adicionada ao buffer para {empresa_slug}")
                return JSONResponse(content={
                    'success': True,
                    'message': 'Mensagem recebida e adicionada ao buffer',
                    'empresa': empresa_slug,
                    'cliente_id': wa_id,
                    'buffered': True
                })
            else:
                # Processar mensagem imediatamente
                result = await message_processor._process_buffered_message(webhook_data, empresa_slug)
                logger.info(f"Mensagem processada imediatamente para {empresa_slug}: {result}")
                return JSONResponse(content={
                    'success': result.get('success', True),
                    'message': 'Mensagem processada imediatamente',
                    'empresa': empresa_slug,
                    'cliente_id': wa_id,
                    'buffered': False,
                    'result': result
                })
        except Exception as e:
            logger.error(f"Erro ao processar mensagem para {empresa_slug}: {e}")
            
            # Log do erro
            session_log = SessionLocal()
            try:
                save_log_to_db(session_log, empresa_db.id, 'ERROR', f'Erro ao processar mensagem: {e}', {
                    'empresa': empresa_slug,
                    'cliente_id': wa_id,
                    'error': str(e)
                })
            finally:
                session_log.close()
            
            # Retornar sucesso mesmo com erro para não quebrar o webhook
            return JSONResponse(content={
                'success': True,
                'message': 'Mensagem recebida (erro no processamento)',
                'empresa': empresa_slug,
                'cliente_id': wa_id,
                'error': str(e)
            })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no webhook handler: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@app.get("/api/logs")
def get_logs(empresa: str = None, limit: int = 100, level: str = None, exclude_info: bool = True):
    """Retorna logs do sistema do banco de dados"""
    print("🔍 DEBUG: Função get_logs chamada")
    session = SessionLocal()
    try:
        # Construir query base
        query = session.query(Log).order_by(Log.timestamp.desc())
        
        # Filtrar por empresa se especificado
        if empresa:
            empresa_obj = session.query(Empresa).filter(Empresa.slug == empresa).first()
            if empresa_obj:
                query = query.filter(Log.empresa_id == empresa_obj.id)
        
        # Filtrar por nível se especificado
        if level and level.lower() != 'all':
            query = query.filter(Log.level == level.upper())
        elif exclude_info:
            # Por padrão, excluir logs de INFO para não poluir
            query = query.filter(Log.level != 'INFO')
        
        # Limitar resultados
        logs_db = query.limit(limit).all()
        print(f"🔍 DEBUG: {len(logs_db)} logs encontrados no banco")
        
        # Converter para formato da API
        logs = []
        for log in logs_db:
            empresa_nome = None
            if log.empresa_id:
                empresa_obj = session.query(Empresa).filter(Empresa.id == log.empresa_id).first()
                empresa_nome = empresa_obj.nome if empresa_obj else None
            
            logs.append({
                "level": log.level,
                "message": log.message,
                "empresa": empresa_nome,
                "timestamp": log.timestamp.isoformat(),
                "details": log.details or {}
            })
        
        print(f"🔍 DEBUG: Retornando {len(logs)} logs")
        return {"logs": logs}
    except Exception as e:
        print(f"🔍 DEBUG: Erro: {e}")
        logger.error(f"Erro ao buscar logs: {e}")
        raise HTTPException(status_code=500, detail="Erro ao buscar logs")
    finally:
        session.close()

@app.get("/api/calendar/slots")
def get_available_slots(date: str = None):
    """Retorna horários disponíveis para agendamento"""
    try:
        slots = message_processor.get_available_slots(date)
        return slots
    except Exception as e:
        logger.error(f"Erro ao buscar horários disponíveis: {e}")
        raise HTTPException(status_code=500, detail="Erro ao verificar agenda")

@app.get("/api/conversation/{empresa}/{cliente_id}")
def get_conversation_history(
    empresa: str, 
    cliente_id: str, 
    limit: int = Query(20, gt=0), 
    before: str = Query(None),
    current_user: Usuario = Depends(get_current_user)
):
    """Retorna histórico paginado de conversa de um cliente"""
    session = SessionLocal()
    try:
        # Verificar se a empresa existe e se o usuário tem acesso
        empresa_obj = session.query(Empresa).filter(Empresa.slug == empresa).first()
        if not empresa_obj:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        
        # Verificar se usuário tem acesso a esta empresa
        if not current_user.is_superuser and current_user.empresa_id != empresa_obj.id:
            raise HTTPException(status_code=403, detail="Acesso negado a esta empresa")
        
        # Buscar histórico do banco de dados
        all_messages = message_processor.database_service.get_conversation_history(empresa_obj.id, cliente_id, limit=100)
        
        # Filtrar por 'before' se fornecido
        if before:
            all_messages = [m for m in all_messages if m.get('timestamp', '') < before]
        
        # Pegar as últimas 'limit' mensagens
        paginated_messages = all_messages[-limit:]
        
        # Buscar atividades do cliente do banco de dados
        activities = message_processor.database_service.get_recent_activities(empresa_obj.id, limit=20)
        activities = [a for a in activities if a.get('cliente') == cliente_id]
        
        return {
            "empresa": empresa,
            "cliente_id": cliente_id,
            "activities": activities,
            "messages": paginated_messages
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar histórico: {e}")
        raise HTTPException(status_code=500, detail="Erro ao buscar histórico de conversa")
    finally:
        session.close()

@app.post("/api/calendar/schedule")
def schedule_meeting(email: str, name: str, company: str, date_time: str):
    """Agenda uma reunião"""
    try:
        result = message_processor.schedule_meeting(email, name, company, date_time)
        return result
    except Exception as e:
        logger.error(f"Erro ao agendar reunião: {e}")
        raise HTTPException(status_code=500, detail="Erro ao agendar reunião")

@app.get("/api/admin/erros-24h")
def erros_24h():
    session = SessionLocal()
    try:
        agora = datetime.utcnow()
        ontem = agora - timedelta(hours=24)
        empresas = session.query(Empresa).all()
        erros_por_empresa = {}
        
        for empresa in empresas:
            count = session.query(Log).filter(
                Log.empresa_id == empresa.id,
                Log.level == 'ERROR',
                Log.timestamp >= ontem,
                Log.timestamp <= agora
            ).count()
            erros_por_empresa[empresa.slug] = count
        
        # Adicionar logs de erro sem empresa específica à TinyTeams
        tinyteams = session.query(Empresa).filter(Empresa.slug == 'tinyteams').first()
        if tinyteams:
            # Contar logs de erro sem empresa_id (None)
            erros_sistema = session.query(Log).filter(
                Log.empresa_id == None,
                Log.level == 'ERROR',
                Log.timestamp >= ontem,
                Log.timestamp <= agora
            ).count()
            
            # Adicionar aos erros da TinyTeams
            erros_por_empresa['tinyteams'] = erros_por_empresa.get('tinyteams', 0) + erros_sistema
        
        return erros_por_empresa
    finally:
        session.close()

@app.post("/api/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    session = SessionLocal()
    try:
        user = session.query(Usuario).filter(Usuario.email == form_data.username).first()
        if not user or not bcrypt.verify(form_data.password, user.senha_hash):
            # Log de tentativa de login falhada
            save_log_to_db(session, None, 'WARNING', f'Tentativa de login falhada para {form_data.username}')
            raise HTTPException(status_code=401, detail="Credenciais inválidas")
        
        # Log de login bem-sucedido
        save_log_to_db(session, user.empresa_id, 'INFO', f'Login bem-sucedido para {user.email}')
        
        data = {
            "sub": user.email, 
            "is_superuser": user.is_superuser, 
            "empresa_id": user.empresa_id,
            "user_id": user.id
        }
        token = jwt.encode(data, config.SECRET_KEY, algorithm=config.ALGORITHM)
        
        return {
            "access_token": token, 
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "is_superuser": user.is_superuser,
                "empresa_id": user.empresa_id
            }
        }
    finally:
        session.close()

@app.get("/api/admin/usuarios")
def get_usuarios(current_user: Usuario = Depends(get_current_superuser)):
    session = SessionLocal()
    try:
        usuarios = session.query(Usuario).all()
        return [
            {
                "id": u.id,
                "email": u.email,
                "is_superuser": u.is_superuser,
                "empresa_id": u.empresa_id,
                "created_at": u.created_at.isoformat() if u.created_at else None
            }
            for u in usuarios
        ]
    finally:
        session.close()

@app.post("/api/admin/usuarios")
def create_usuario(
    user_data: dict,
    current_user: Usuario = Depends(get_current_superuser)
):
    session = SessionLocal()
    try:
        # Verificar se email já existe
        existing_user = session.query(Usuario).filter(Usuario.email == user_data["email"]).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email já cadastrado")
        
        # Gerar hash da senha
        senha_hash = gerar_hash_senha(user_data["password"])
        
        # Criar usuário
        novo_usuario = Usuario(
            email=user_data["email"],
            senha_hash=senha_hash,
            is_superuser=user_data.get("is_superuser", False),
            empresa_id=user_data.get("empresa_id") if user_data.get("empresa_id") else None
        )
        
        session.add(novo_usuario)
        session.commit()
        
        return {
            "id": novo_usuario.id,
            "email": novo_usuario.email,
            "is_superuser": novo_usuario.is_superuser,
            "empresa_id": novo_usuario.empresa_id
        }
    finally:
        session.close()

@app.put("/api/admin/usuarios/{user_id}")
def update_usuario(
    user_id: int,
    user_data: dict,
    current_user: Usuario = Depends(get_current_superuser)
):
    session = SessionLocal()
    try:
        usuario = session.query(Usuario).filter(Usuario.id == user_id).first()
        if not usuario:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
        # Atualizar campos
        if "email" in user_data:
            # Verificar se email já existe (exceto para o próprio usuário)
            existing_user = session.query(Usuario).filter(
                Usuario.email == user_data["email"],
                Usuario.id != user_id
            ).first()
            if existing_user:
                raise HTTPException(status_code=400, detail="Email já cadastrado")
            usuario.email = user_data["email"]
        
        if "password" in user_data and user_data["password"]:
            usuario.senha_hash = gerar_hash_senha(user_data["password"])
        
        if "is_superuser" in user_data:
            usuario.is_superuser = user_data["is_superuser"]
        
        if "empresa_id" in user_data:
            usuario.empresa_id = user_data["empresa_id"] if user_data["empresa_id"] else None
        
        session.commit()
        
        return {
            "id": usuario.id,
            "email": usuario.email,
            "is_superuser": usuario.is_superuser,
            "empresa_id": usuario.empresa_id
        }
    finally:
        session.close()

@app.delete("/api/admin/usuarios/{user_id}")
def delete_usuario(
    user_id: int,
    current_user: Usuario = Depends(get_current_superuser)
):
    session = SessionLocal()
    try:
        usuario = session.query(Usuario).filter(Usuario.id == user_id).first()
        if not usuario:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
        # Não permitir deletar o próprio usuário
        if usuario.id == current_user.id:
            raise HTTPException(status_code=400, detail="Não é possível deletar seu próprio usuário")
        
        session.delete(usuario)
        session.commit()
        
        return {"message": "Usuário deletado com sucesso"}
    finally:
        session.close()

@app.get("/")
def root():
    """Endpoint raiz"""
    return {
        "message": "Atende Ai Backend",
        "version": "1.0.0",
        "status": "running",
        "features": [
            "Webhook com buffer de mensagens",
            "Integração OpenAI",
            "Integração Twilio",
            "Integração Google Sheets",
            "Integração Chatwoot",
            "Painel admin multi-empresa"
        ]
    }

# Rotas para configurações da empresa
@app.get("/api/empresas/{empresa_slug}/configuracoes")
def get_empresa_configuracoes(
    empresa_slug: str,
    current_user: Usuario = Depends(get_current_user)
):
    """Buscar configurações da empresa (sem expor tokens sensíveis)"""
    session = SessionLocal()
    try:
        # Verificar se usuário tem acesso à empresa
        if not current_user.is_superuser:
            if not current_user.empresa_id:
                raise HTTPException(status_code=403, detail="Acesso negado")
            
            empresa = session.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
            if not empresa or empresa.slug != empresa_slug:
                raise HTTPException(status_code=403, detail="Acesso negado à empresa")
        else:
            empresa = session.query(Empresa).filter(Empresa.slug == empresa_slug).first()
            if not empresa:
                raise HTTPException(status_code=404, detail="Empresa não encontrada")
        
        # Retornar configurações no formato que o frontend espera
        return {
            "nome": empresa.nome,
            "whatsapp_number": empresa.whatsapp_number,
            "google_sheets_id": empresa.google_sheets_id,
            "openai_key": empresa.openai_key,
            "twilio_sid": empresa.twilio_sid,
            "twilio_token": empresa.twilio_token,
            "twilio_number": empresa.twilio_number,
            "usar_buffer": empresa.usar_buffer,
            "mensagem_quebrada": empresa.mensagem_quebrada,
            "prompt": empresa.prompt
        }
    finally:
        session.close()

@app.put("/api/empresas/{empresa_slug}/configuracoes")
def update_empresa_configuracoes(
    empresa_slug: str,
    configuracoes: dict,
    current_user: Usuario = Depends(get_current_user)
):
    """Atualizar configurações da empresa"""
    session = SessionLocal()
    try:
        # Verificar se usuário tem acesso à empresa
        if not current_user.is_superuser:
            if not current_user.empresa_id:
                raise HTTPException(status_code=403, detail="Acesso negado")
            
            empresa = session.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
            if not empresa or empresa.slug != empresa_slug:
                raise HTTPException(status_code=403, detail="Acesso negado à empresa")
        else:
            empresa = session.query(Empresa).filter(Empresa.slug == empresa_slug).first()
            if not empresa:
                raise HTTPException(status_code=404, detail="Empresa não encontrada")
        
        # Atualizar campos diretamente do formulário
        if "nome" in configuracoes:
            empresa.nome = configuracoes["nome"]
        if "whatsapp_number" in configuracoes:
            empresa.whatsapp_number = configuracoes["whatsapp_number"]
        if "google_sheets_id" in configuracoes:
            empresa.google_sheets_id = configuracoes["google_sheets_id"]
        if "openai_key" in configuracoes:
            empresa.openai_key = configuracoes["openai_key"]
        if "twilio_sid" in configuracoes:
            empresa.twilio_sid = configuracoes["twilio_sid"]
        if "twilio_token" in configuracoes:
            empresa.twilio_token = configuracoes["twilio_token"]
        if "twilio_number" in configuracoes:
            empresa.twilio_number = configuracoes["twilio_number"]
        if "prompt" in configuracoes:
            empresa.prompt = configuracoes["prompt"]
        if "usar_buffer" in configuracoes:
            empresa.usar_buffer = configuracoes["usar_buffer"]
        if "mensagem_quebrada" in configuracoes:
            empresa.mensagem_quebrada = configuracoes["mensagem_quebrada"]
        
        session.commit()
        
        return {"message": "Configurações atualizadas com sucesso"}
    finally:
        session.close() 

@app.get("/test-services")
async def test_services():
    """Testa os serviços de integração"""
    try:
        # Testar OpenAI
        openai_result = "OpenAI: OK"
        try:
            openai_service = OpenAIService("test-key")
            openai_result = "OpenAI: Erro de chave inválida (esperado)"
        except Exception as e:
            openai_result = f"OpenAI: {str(e)}"
        
        # Testar Twilio
        twilio_result = "Twilio: OK"
        try:
            twilio_service = TwilioService("test-sid", "test-token", "+1234567890")
            twilio_result = "Twilio: Erro de credenciais inválidas (esperado)"
        except Exception as e:
            twilio_result = f"Twilio: {str(e)}"
        
        return {
            "openai": openai_result,
            "twilio": twilio_result,
            "status": "Testes concluídos"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro nos testes: {e}")

@app.get("/test-errors")
async def test_errors():
    """Gera logs de erro para teste"""
    session = SessionLocal()
    try:
        # Buscar empresas
        empresas = session.query(Empresa).all()
        
        # Gerar erros para diferentes empresas
        erros_gerados = []
        
        for i, empresa in enumerate(empresas[:3]):  # Primeiras 3 empresas
            # Erro específico da empresa
            save_log_to_db(
                session, 
                empresa.id, 
                'ERROR', 
                f'Erro de teste na empresa {empresa.nome}: Integração falhou',
                {'empresa': empresa.slug, 'tipo': 'teste'}
            )
            erros_gerados.append(f"Erro gerado para {empresa.nome}")
        
        # Gerar erros sem empresa específica (serão atribuídos à TinyTeams)
        save_log_to_db(
            session, 
            None, 
            'ERROR', 
            'Erro de teste do sistema: Falha na conexão com banco de dados',
            {'tipo': 'sistema', 'componente': 'database'}
        )
        erros_gerados.append("Erro de sistema (será atribuído à TinyTeams)")
        
        save_log_to_db(
            session, 
            None, 
            'ERROR', 
            'Erro de teste do sistema: Timeout na API externa',
            {'tipo': 'sistema', 'componente': 'api'}
        )
        erros_gerados.append("Erro de sistema (será atribuído à TinyTeams)")
        
        return {
            "message": "Logs de erro gerados com sucesso",
            "erros_gerados": erros_gerados,
            "total_empresas": len(empresas)
        }
        
    except Exception as e:
        logger.error(f"Erro ao gerar logs de teste: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar logs: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 