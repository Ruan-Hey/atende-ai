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
from models import WebhookData, MessageResponse, AdminMetrics, EmpresaMetrics, HealthCheck, Base, Empresa, Mensagem, Log, Usuario, gerar_hash_senha
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
async def criar_empresa(data: dict):
    session = SessionLocal()
    try:
        empresa = Empresa(
            slug=data["slug"],
            nome=data["nome"],
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
    try:
        # Usar o MetricsService que busca dados do Redis
        metrics = metrics_service.get_admin_metrics()
        return metrics
    except Exception as e:
        logger.error(f"Erro ao buscar métricas admin: {e}")
        session = SessionLocal()
        try:
            save_log_to_db(session, None, 'ERROR', f'Erro ao buscar métricas admin: {e}')
        finally:
            session.close()
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

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
        
        return [
            {
                "id": e.id,
                "nome": e.nome,
                "slug": e.slug,
                "status": "ativo",  # Status padrão para todas as empresas
                "created_at": e.created_at.isoformat() if e.created_at else None
            }
            for e in empresas
        ]
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
        
        # Buscar clientes únicos do Redis baseado em atividades
        clientes = []
        
        try:
            # Buscar todas as atividades da empresa
            activity_pattern = f"activity:{empresa_slug}:*"
            clientes_unicos = {}
            
            for activity_key in message_processor.redis_service.redis_client.scan_iter(match=activity_pattern):
                activity_data = message_processor.redis_service.redis_client.get(activity_key)
                if activity_data:
                    try:
                        activity = json.loads(activity_data)
                        cliente_id = activity.get('cliente', '')
                        
                        if cliente_id and cliente_id not in clientes_unicos:
                            # Buscar contexto se existir
                            context = message_processor.redis_service.get_context(cliente_id, empresa_slug)
                            
                            clientes_unicos[cliente_id] = {
                                "cliente_id": cliente_id,
                                "nome": context.get('cliente_name', cliente_id) if context else cliente_id,
                                "ultima_atividade": activity.get('timestamp'),
                                "total_mensagens": len(context.get('messages', [])) if context else 0,
                                "tipo_atividade": activity.get('type', 'mensagem')
                            }
                        elif cliente_id in clientes_unicos:
                            # Atualizar última atividade se for mais recente
                            current_timestamp = activity.get('timestamp', '')
                            existing_timestamp = clientes_unicos[cliente_id]['ultima_atividade']
                            
                            if current_timestamp > existing_timestamp:
                                clientes_unicos[cliente_id]['ultima_atividade'] = current_timestamp
                                clientes_unicos[cliente_id]['tipo_atividade'] = activity.get('type', 'mensagem')
                                
                    except Exception as e:
                        logger.error(f"Erro ao processar atividade: {e}")
                        continue
            
            # Converter para lista
            clientes = list(clientes_unicos.values())
                    
        except Exception as redis_error:
            logger.error(f"Erro ao buscar clientes no Redis: {redis_error}")
            # Retornar lista vazia se houver erro no Redis
            clientes = []
        
        # Ordenar por total de mensagens (mais mensagens primeiro)
        clientes.sort(key=lambda x: x['total_mensagens'], reverse=True)
        
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
                'usar_buffer': empresa_db.usar_buffer or True
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
def get_logs(empresa: str = None, limit: int = 100):
    """Retorna logs do sistema"""
    # Retorna logs básicos sem dados mockados
    logs = [
        {
            "level": "INFO",
            "message": "Sistema iniciado com sucesso",
            "empresa": None,
            "timestamp": datetime.now().isoformat(),
            "details": {"version": "1.0.0"}
        }
    ]
    
    # Filtrar por empresa se especificado
    if empresa:
        logs = [log for log in logs if log.get('empresa') == empresa]
    
    return {"logs": logs[:limit]}

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
        
        # Buscar contexto do Redis
        context = message_processor.redis_service.get_context(cliente_id, empresa)
        all_messages = context.get('messages', [])
        
        # Ordenar mensagens por timestamp crescente
        all_messages.sort(key=lambda x: x.get('timestamp', ''))
        
        # Filtrar por 'before' se fornecido
        if before:
            all_messages = [m for m in all_messages if m.get('timestamp', '') < before]
        
        # Pegar as últimas 'limit' mensagens
        paginated_messages = all_messages[-limit:]
        
        # Buscar atividades do cliente
        activities = []
        activity_pattern = f"activity:{empresa}:*"
        for key in message_processor.redis_service.redis_client.scan_iter(match=activity_pattern):
            activity_data = message_processor.redis_service.redis_client.get(key)
            if activity_data:
                try:
                    activity = json.loads(activity_data)
                    if activity.get('cliente') == cliente_id:
                        activities.append(activity)
                except:
                    pass
        
        activities.sort(key=lambda x: x.get('timestamp', ''))
        
        return {
            "empresa": empresa,
            "cliente_id": cliente_id,
            "context": context,
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
        return erros_por_empresa
    finally:
        session.close()

@app.post("/api/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    session = SessionLocal()
    try:
        user = session.query(Usuario).filter(Usuario.email == form_data.username).first()
        if not user or not bcrypt.verify(form_data.password, user.senha_hash):
            raise HTTPException(status_code=401, detail="Credenciais inválidas")
        
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
        
        # Retornar configurações sem expor tokens sensíveis
        return {
            "prompt": empresa.prompt or "",
            "configuracoes": {
                "mensagemQuebrada": empresa.mensagem_quebrada or False,
                "buffer": empresa.usar_buffer or False
            },
            "apis": {
                "openai": {
                    "ativo": bool(empresa.openai_key),
                    "token": "***" if empresa.openai_key else ""
                },
                "google": {
                    "ativo": bool(empresa.google_sheets_id),
                    "token": "***" if empresa.google_sheets_id else ""
                },
                "chatwoot": {
                    "ativo": bool(empresa.chatwoot_token),
                    "token": "***" if empresa.chatwoot_token else ""
                }
            }
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
        
        # Atualizar prompt
        if "prompt" in configuracoes:
            empresa.prompt = configuracoes["prompt"]
        
        # Atualizar configurações
        if "configuracoes" in configuracoes:
            config = configuracoes["configuracoes"]
            if "mensagemQuebrada" in config:
                empresa.mensagem_quebrada = config["mensagemQuebrada"]
            if "buffer" in config:
                empresa.usar_buffer = config["buffer"]
        
        # Atualizar APIs (apenas se o token não for "***")
        if "apis" in configuracoes:
            apis = configuracoes["apis"]
            
            if "openai" in apis and apis["openai"].get("token") != "***":
                empresa.openai_key = apis["openai"]["token"] if apis["openai"]["token"] else None
            
            if "google" in apis and apis["google"].get("token") != "***":
                empresa.google_sheets_id = apis["google"]["token"] if apis["google"]["token"] else None
            
            if "chatwoot" in apis and apis["chatwoot"].get("token") != "***":
                empresa.chatwoot_token = apis["chatwoot"]["token"] if apis["chatwoot"]["token"] else None
        
        session.commit()
        
        return {"message": "Configurações atualizadas com sucesso"}
    finally:
        session.close() 

@app.get("/test-services")
async def test_services():
    """Endpoint de teste para verificar se os serviços estão funcionando"""
    try:
        # Testar se o message_processor está funcionando
        buffer_status = message_processor.get_buffer_status()
        return JSONResponse(content={
            'success': True,
            'message': 'Serviços funcionando',
            'buffer_status': buffer_status
        })
    except Exception as e:
        return JSONResponse(content={
            'success': False,
            'message': f'Erro nos serviços: {str(e)}'
        }) 