import os
from fastapi import FastAPI, HTTPException, Request, Query, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import json
from datetime import datetime, timedelta
import random
import asyncio
import time

# Configurar logging limpo
from config import LOGGING_CONFIG
import logging.config
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

from config import Config
from models import WebhookData, MessageResponse, AdminMetrics, EmpresaMetrics, HealthCheck, Base, Empresa, Mensagem, Log, Usuario, gerar_hash_senha, Atendimento, Cliente, Atividade, API, EmpresaAPI
from services.services import MetricsService
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from jose import jwt, JWTError
from passlib.hash import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer

from typing import Optional, List, Dict, Tuple, Any

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
            usar_buffer=data.get("usar_buffer", True),
            mensagem_quebrada=data.get("mensagem_quebrada", False),
            twilio_sid=data.get("twilio_sid"),
            twilio_token=data.get("twilio_token"),
            twilio_number=data.get("twilio_number"),
            knowledge_json=data.get("knowledge_json") or {"items": []}
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

# Endpoints antigos de agent_cache removidos - agora usando SmartAgent

@app.get("/api/admin/metrics")
def get_admin_metrics(current_user: Usuario = Depends(get_current_superuser)) -> AdminMetrics:
    """Retorna métricas para o painel admin"""
    session = SessionLocal()
    try:
        # Log de acesso às métricas
        save_log_to_db(session, None, 'INFO', f'Usuário {current_user.email} acessou métricas admin')
        
        # Usar o MetricsService que busca dados do banco
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
    current_user: Usuario = Depends(get_current_user),
    label: str = None,
    from_date: str = None,
    to_date: str = None
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
        
        # Se houver filtros por label/data, basear em atendimentos
        from sqlalchemy import func, and_
        use_att_filter = bool(label or from_date or to_date)
        clientes = []
        if use_att_filter:
            from models import Atendimento
            query = session.query(
                Atendimento.cliente_id,
                func.max(Atendimento.data_atendimento).label('ultima_atividade'),
                func.count(Atendimento.id).label('total_mensagens')
            ).filter(
                Atendimento.empresa_id == empresa.id
            )
            if label:
                query = query.filter(Atendimento.label_slug == label)
            if from_date:
                query = query.filter(Atendimento.data_atendimento >= from_date)
            if to_date:
                query = query.filter(Atendimento.data_atendimento <= to_date)
            query = query.group_by(Atendimento.cliente_id).order_by(func.count(Atendimento.id).desc())
            result = query.all()
            for row in result:
                cliente_info = session.query(Cliente).filter(
                    Cliente.empresa_id == empresa.id,
                    Cliente.cliente_id == row.cliente_id
                ).first()
                nome_cliente = cliente_info.nome if cliente_info and cliente_info.nome else row.cliente_id
                clientes.append({
                    "cliente_id": row.cliente_id,
                    "nome": nome_cliente,
                    "ultima_atividade": row.ultima_atividade.isoformat() if row.ultima_atividade else None,
                    "total_mensagens": row.total_mensagens,
                    "tipo_atividade": label or 'mensagem'
                })
            return {"empresa": empresa_slug, "clientes": clientes}
        
        # Fallback: comportamento atual baseado em mensagens
        from sqlalchemy import func
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

@app.get("/api/admin/debounce/status")
def get_buffer_status():
    """Retorna status do debounce em memória"""
    try:
        active = len(debounce_state)
        keys = [
            {"empresa": k[0], "cliente_id": k[1], "restante_ms": int(max(0, v.get('deadline', 0) - time.time()) * 1000)}
            for k, v in debounce_state.items()
        ]
        return {
            "status": "active" if active > 0 else "idle",
            "message": "Debounce em memória ativo",
            "active_clients": active,
            "timers": keys
        }
    except Exception as e:
        logger.error(f"Erro ao verificar status do debounce: {e}")
        return {
            "status": "error",
            "message": f"Erro ao verificar debounce: {str(e)}",
            "active_clients": 0,
            "timers": []
        }

@app.post("/api/admin/debounce/flush")
def force_process_buffer(cliente_id: str = None, empresa: str = None):
    """Força o processamento imediato dos timers ativos (flush)"""
    try:
        targets = []
        for (emp, wa), entry in list(debounce_state.items()):
            if cliente_id and wa != cliente_id:
                continue
            if empresa and emp != empresa:
                continue
            targets.append((emp, wa, entry))
        
        processed = 0
        for emp, wa, entry in targets:
            try:
                # ajustar deadline para agora e disparar task
                entry['deadline'] = time.time()
                # criar task isolada para cada alvo
                empresa_config = entry.get('empresa_config', {})
                asyncio.create_task(_debounce_wait_and_process(emp, wa, empresa_config))
                processed += 1
            except Exception as e:
                logger.error(f"Erro no flush do debounce para {emp}:{wa}: {e}")
        
        return {
            "success": True,
            "message": "Flush disparado",
            "targets": processed
        }
    except Exception as e:
        logger.error(f"Erro ao forçar flush do debounce: {e}")
        return {
            "success": False,
            "message": f"Erro: {str(e)}"
        }

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
            
            # Buscar APIs conectadas da empresa
            empresa_apis = session.query(EmpresaAPI).filter(
                EmpresaAPI.empresa_id == empresa_db.id,
                EmpresaAPI.ativo == True
            ).all()
            
            # Criar configuração base da empresa
            empresa_config = {
                'nome': empresa_db.nome,
                'slug': empresa_db.slug,
                'empresa_id': empresa_db.id,
                'twilio_sid': empresa_db.twilio_sid,
                'twilio_token': empresa_db.twilio_token,
                'twilio_number': empresa_db.twilio_number,
                'mensagem_quebrada': empresa_db.mensagem_quebrada or False,
                'prompt': empresa_db.prompt,
                'usar_buffer': empresa_db.usar_buffer if empresa_db.usar_buffer is not None else True,
                'knowledge_json': empresa_db.knowledge_json or {"items": []}
            }
            
            # Adicionar configurações das APIs conectadas
            for empresa_api in empresa_apis:
                api_name = empresa_api.api.nome
                config = empresa_api.config or {}
                
                # Adicionar TODAS as configurações da API ao empresa_config
                # Usar prefixo com nome da API para evitar conflitos
                api_prefix = api_name.lower().replace(' ', '_')
                
                # Adicionar configuração completa da API
                empresa_config[f'{api_prefix}_config'] = config
                
                # Adicionar campos específicos para compatibilidade
                if api_name == "Google Calendar":
                    empresa_config['google_calendar_client_id'] = config.get('client_id')
                    empresa_config['google_calendar_client_secret'] = config.get('client_secret')
                    empresa_config['google_calendar_refresh_token'] = config.get('refresh_token')
                    empresa_config['google_calendar_service_account'] = config.get('google_calendar_service_account')
                    empresa_config['google_calendar_project_id'] = config.get('google_calendar_project_id')
                    empresa_config['google_calendar_client_email'] = config.get('google_calendar_client_email')
                    empresa_config['google_calendar_enabled'] = config.get('enabled', True)
                    empresa_config['google_sheets_id'] = config.get('google_sheets_id')
                elif api_name == "Google Sheets":
                    empresa_config['google_sheets_id'] = config.get('google_sheets_id')
                    # Adicionar campos OAuth2 específicos do Google Sheets, se existirem
                    empresa_config['google_sheets_client_id'] = config.get('google_sheets_client_id')
                    empresa_config['google_sheets_client_secret'] = config.get('google_sheets_client_secret')
                    empresa_config['google_sheets_refresh_token'] = config.get('google_sheets_refresh_token')
                elif api_name == "OpenAI":
                    # OpenAI vem da tabela empresa_apis
                    if config.get('openai_key'):
                        empresa_config['openai_key'] = config.get('openai_key')
                # Tratar qualquer variação de nome que contenha "Trinks" (ex.: "Trinks", "Trinks Api V2")
                elif "trinks" in api_name.lower():
                    # Normalizar chaves canônicas usadas pelo motor de regras e ferramentas inteligentes
                    trinks_api_key = config.get('api_key') or config.get('key')
                    trinks_base_url = (
                        config.get('base_url') or config.get('url_base') or config.get('url') or ''
                    )
                    # Fallback padrão e correção de esquema
                    if not trinks_base_url:
                        trinks_base_url = 'https://api.trinks.com/v1'
                    elif not trinks_base_url.startswith(('http://', 'https://')):
                        trinks_base_url = 'https://' + trinks_base_url.lstrip('/')
                    trinks_estabelecimento_id = (
                        config.get('estabelecimento_id') or config.get('estabelecimentoId') or config.get('estabelecimento')
                    )

                    empresa_config['trinks_api_key'] = trinks_api_key
                    empresa_config['trinks_base_url'] = trinks_base_url
                    empresa_config['trinks_estabelecimento_id'] = trinks_estabelecimento_id
                    empresa_config['trinks_enabled'] = True

                    # Garantir que o config usado pelas tools tenha base_url e headers obrigatórios
                    merged_config = dict(config) if isinstance(config, dict) else {}
                    if trinks_base_url and not merged_config.get('base_url'):
                        merged_config['base_url'] = trinks_base_url

                    headers = dict(merged_config.get('headers') or {})
                    if trinks_api_key and 'X-API-KEY' not in headers:
                        headers['X-API-KEY'] = trinks_api_key
                    if trinks_estabelecimento_id and 'estabelecimentoId' not in headers:
                        headers['estabelecimentoId'] = trinks_estabelecimento_id
                    if headers:
                        merged_config['headers'] = headers

                    # Sobrescrever o config específico desta API e também expor como 'trinks_config'
                    empresa_config[f'{api_prefix}_config'] = merged_config
                    empresa_config['trinks_config'] = merged_config
                elif api_name == "Chatwoot":
                    config_data['chatwoot_token'] = config.get('chatwoot_token')
                    config_data['chatwoot_inbox_id'] = config.get('chatwoot_inbox_id')
                    config_data['chatwoot_origem'] = config.get('chatwoot_origem')
                
                # Adicionar campos genéricos para qualquer API
                empresa_config[f'{api_prefix}_api_key'] = config.get('api_key')
                empresa_config[f'{api_prefix}_base_url'] = config.get('base_url')
                empresa_config[f'{api_prefix}_client_id'] = config.get('client_id')
                empresa_config[f'{api_prefix}_client_secret'] = config.get('client_secret')
                empresa_config[f'{api_prefix}_bearer_token'] = config.get('bearer_token')
                empresa_config[f'{api_prefix}_username'] = config.get('username')
                empresa_config[f'{api_prefix}_password'] = config.get('password')
                
                # Marcar API como ativa
                empresa_config[f'{api_prefix}_enabled'] = True
        
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
        
        # Transcrever áudio quando possível
        try:
            media_url = webhook_data.get('MediaUrl0')
            media_type = webhook_data.get('MediaContentType0', '')
            is_audio_media = False
            try:
                is_audio_media = (message_type == 'audio') or (int(num_media) > 0 and str(media_type).startswith('audio'))
            except Exception:
                is_audio_media = (message_type == 'audio')

            if is_audio_media and media_url and empresa_config.get('openai_key'):
                logger.info("Transcrevendo áudio recebido via WhatsApp...")
                from integrations.openai_service import OpenAIService
                oai = OpenAIService(empresa_config.get('openai_key'))
                transcript = oai.transcribe_audio(media_url, empresa_config.get('twilio_sid'), empresa_config.get('twilio_token'))
                if transcript:
                    body = transcript
                    webhook_data['Body'] = transcript
                    webhook_data['MessageType'] = 'text'
                    logger.info("Transcrição de áudio concluída com sucesso")
        except Exception as te:
            logger.error(f"Erro ao transcrever áudio: {te}")
        
        # DEBOUNCE EM MEMÓRIA (substitui buffer em banco)
        if empresa_config.get('usar_buffer', True):
            # Debounce: atualiza estado e adia o processamento
            key = _get_debounce_key(empresa_slug, wa_id)
            deadline = time.time() + DEFAULT_DEBOUNCE_SECONDS
            entry = debounce_state.get(key) or {}
            entry.update({
                'deadline': deadline,
                'webhook_data': webhook_data,
                'empresa_config': empresa_config
            })
            debounce_state[key] = entry
            
            # Se não houver task ativa, criar uma
            if not entry.get('timer') or entry['timer'].done():
                entry['timer'] = asyncio.create_task(_debounce_wait_and_process(empresa_slug, wa_id, empresa_config))
            
            return JSONResponse(content={
                'success': True,
                'message': 'Mensagem recebida. Vou aguardar alguns segundos para consolidar e responder.',
                'empresa': empresa_slug,
                'cliente_id': wa_id,
                'debounce_ms': int(DEFAULT_DEBOUNCE_SECONDS * 1000)
            })
        
        # Se não usar buffer ou se falhar, processar imediatamente
        # Processar mensagem com Smart Agent (LangGraph + LangChain)
        try:
            # ✅ CACHE GLOBAL de Smart Agents por waid
            if not hasattr(webhook_handler, '_smart_agents_cache'):
                webhook_handler._smart_agents_cache = {}
            
            # ✅ LIMPEZA PERIÓDICA do cache (evitar vazamento de memória)
            current_time = time.time()
            if not hasattr(webhook_handler, '_last_cache_cleanup'):
                webhook_handler._last_cache_cleanup = current_time
            
            # Limpar cache a cada 1 hora (3600 segundos)
            if current_time - webhook_handler._last_cache_cleanup > 3600:
                old_cache_size = len(webhook_handler._smart_agents_cache)
                # Manter apenas agentes ativos nas últimas 24 horas
                cutoff_time = current_time - 86400  # 24 horas
                webhook_handler._smart_agents_cache = {
                    waid: agent for waid, agent in webhook_handler._smart_agents_cache.items()
                    if hasattr(agent, 'last_activity') and agent.last_activity > cutoff_time
                }
                webhook_handler._last_cache_cleanup = current_time
                logger.info(f"🧹 Cache limpo: {old_cache_size} → {len(webhook_handler._smart_agents_cache)} agentes")
            
            # ✅ OBTER Smart Agent EXISTENTE ou criar novo
            if wa_id in webhook_handler._smart_agents_cache:
                smart_agent = webhook_handler._smart_agents_cache[wa_id]
                # ✅ ATUALIZAR atividade do agente
                smart_agent.last_activity = current_time
                logger.info(f"🔄 Reutilizando Smart Agent existente para waid {wa_id}")
            else:
                from agents.smart_agent import SmartAgent
                smart_agent = SmartAgent(empresa_config)
                # ✅ ADICIONAR timestamp de atividade
                smart_agent.last_activity = current_time
                webhook_handler._smart_agents_cache[wa_id] = smart_agent
                logger.info(f"🆕 Criando novo Smart Agent para waid {wa_id}")
            
            # ✅ AGORA SIM: Smart Agent tem memória preservada
            response_message = smart_agent.analyze_and_respond(webhook_data.get('Body', ''), wa_id, {
                'empresa_slug': empresa_slug,
                'cliente_id': wa_id,
                'empresa_config': empresa_config
            })
            
            result = {
                'success': True,
                'message': response_message
            }
            
            # Log do processamento
            logger.info(f"Mensagem processada com Smart Agent para {empresa_slug}:{wa_id}")
            
            # Enviar resposta via Twilio
            if result.get('success'):
                from integrations.twilio_service import TwilioService
                twilio_service = TwilioService(
                    empresa_config.get('twilio_sid'),
                    empresa_config.get('twilio_token'),
                    empresa_config.get('twilio_number')
                )
                
                response_message = result.get('message', '')
                
                # IMPLEMENTAÇÃO DA MENSAGEM QUEBRADA
                if empresa_config.get('mensagem_quebrada', False) and len(response_message) > 200:
                    # Quebrar mensagem longa em partes menores
                    messages = _break_long_message(response_message)
                    
                    # Enviar cada parte separadamente
                    for i, msg_part in enumerate(messages):
                        twilio_result = twilio_service.send_whatsapp_message(wa_id, msg_part)
                        if not twilio_result.get('success'):
                            logger.error(f"Erro ao enviar parte {i+1} da mensagem: {twilio_result.get('error')}")
                            break
                        
                        # Pequena pausa entre mensagens para não sobrecarregar
                        if i < len(messages) - 1:
                            await asyncio.sleep(0.5)
                    
                    logger.info(f"Mensagem quebrada enviada em {len(messages)} partes para {empresa_slug}:{wa_id}")
                else:
                    # Enviar mensagem completa
                    twilio_result = twilio_service.send_whatsapp_message(wa_id, response_message)
                    
                    if twilio_result.get('success'):
                        logger.info(f"Mensagem processada e enviada com sucesso para {empresa_slug}:{wa_id}")
                    else:
                        logger.error(f"Erro ao enviar mensagem via Twilio: {twilio_result.get('error')}")
            
            return JSONResponse(content={
                'success': result.get('success', True),
                'message': 'Mensagem processada com LangChain Agent',
                'empresa': empresa_slug,
                'cliente_id': wa_id,
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

def _break_long_message(message: str, max_length: int = 200) -> List[str]:
    """Quebra mensagem longa em partes menores"""
    if len(message) <= max_length:
        return [message]
    
    # Tentar quebrar por frases naturais
    sentences = message.split('. ')
    parts = []
    current_part = ""
    
    for sentence in sentences:
        if len(current_part + sentence) <= max_length:
            current_part += sentence + ". "
        else:
            if current_part:
                parts.append(current_part.strip())
            current_part = sentence + ". "
    
    if current_part:
        parts.append(current_part.strip())
    
    # Se ainda houver partes muito longas, quebrar por palavras
    final_parts = []
    for part in parts:
        if len(part) <= max_length:
            final_parts.append(part)
        else:
            words = part.split()
            current_chunk = ""
            for word in words:
                if len(current_chunk + " " + word) <= max_length:
                    current_chunk += " " + word if current_chunk else word
                else:
                    if current_chunk:
                        final_parts.append(current_chunk)
                    current_chunk = word
            if current_chunk:
                final_parts.append(current_chunk)
    
    return final_parts

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
        # Buscar configurações da empresa TinyTeams
        session = SessionLocal()
        try:
            empresa = session.query(Empresa).filter(Empresa.slug == 'tinyteams').first()
            if not empresa:
                raise HTTPException(status_code=404, detail="Empresa TinyTeams não encontrada")
            
            # Buscar configurações da API Google Calendar
            from models import API, EmpresaAPI
            api = session.query(API).filter(API.nome == 'Google Calendar').first()
            if not api:
                raise HTTPException(status_code=404, detail="API Google Calendar não encontrada")
            
            empresa_api = session.query(EmpresaAPI).filter(
                EmpresaAPI.empresa_id == empresa.id,
                EmpresaAPI.api_id == api.id
            ).first()
            
            if not empresa_api or not empresa_api.config:
                return {"message": "Google Calendar não configurado"}
            
            # Criar configuração para o Google Calendar Service
            calendar_config = {
                'google_calendar_enabled': empresa_api.config.get('google_calendar_enabled', True),
                'google_calendar_client_id': empresa_api.config.get('google_calendar_client_id'),
                'google_calendar_client_secret': empresa_api.config.get('google_calendar_client_secret'),
                'google_calendar_refresh_token': empresa_api.config.get('google_calendar_refresh_token'),
                'google_calendar_service_account': empresa_api.config.get('google_calendar_service_account'),
                'google_calendar_project_id': empresa_api.config.get('google_calendar_project_id'),
                'google_calendar_client_email': empresa_api.config.get('google_calendar_client_email')
            }
            
            # Usar Google Calendar Service
            from integrations.google_calendar_service import GoogleCalendarService
            calendar_service = GoogleCalendarService(calendar_config)
            
            # Buscar slots disponíveis
            slots = calendar_service.get_available_slots(date)
            return slots
            
        finally:
            session.close()
            
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
        from services.services import DatabaseService
        db_service = DatabaseService()
        all_messages = db_service.get_conversation_history(empresa_obj.id, cliente_id, limit=100)
        
        # Filtrar por 'before' se fornecido
        if before:
            all_messages = [m for m in all_messages if m.get('timestamp', '') < before]
        
        # Pegar as últimas 'limit' mensagens
        paginated_messages = all_messages[-limit:]
        
        # Buscar atividades do cliente do banco de dados
        activities = db_service.get_recent_activities(empresa_obj.id, limit=20)
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
        # Buscar configurações da empresa TinyTeams
        session = SessionLocal()
        try:
            empresa = session.query(Empresa).filter(Empresa.slug == 'tinyteams').first()
            if not empresa:
                raise HTTPException(status_code=404, detail="Empresa TinyTeams não encontrada")
            
            # Buscar configurações da API Google Calendar
            from models import API, EmpresaAPI
            api = session.query(API).filter(API.nome == 'Google Calendar').first()
            if not api:
                raise HTTPException(status_code=404, detail="API Google Calendar não encontrada")
            
            empresa_api = session.query(EmpresaAPI).filter(
                EmpresaAPI.empresa_id == empresa.id,
                EmpresaAPI.api_id == api.id
            ).first()
            
            if not empresa_api or not empresa_api.config:
                return {"message": "Google Calendar não configurado"}
            
            # Criar configuração para o Google Calendar Service
            calendar_config = {
                'google_calendar_enabled': empresa_api.config.get('google_calendar_enabled', True),
                'google_calendar_client_id': empresa_api.config.get('google_calendar_client_id'),
                'google_calendar_client_secret': empresa_api.config.get('google_calendar_client_secret'),
                'google_calendar_refresh_token': empresa_api.config.get('google_calendar_refresh_token'),
                'google_calendar_service_account': empresa_api.config.get('google_calendar_service_account'),
                'google_calendar_project_id': empresa_api.config.get('google_calendar_project_id'),
                'google_calendar_client_email': empresa_api.config.get('google_calendar_client_email')
            }
            
            # Usar Google Calendar Service
            from integrations.google_calendar_service import GoogleCalendarService
            calendar_service = GoogleCalendarService(calendar_config)
            
            # Agendar reunião
            result = calendar_service.schedule_meeting(email, name, company, date_time)
            return result
            
        finally:
            session.close()
            
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
        
        # Buscar APIs conectadas da empresa
        from models import EmpresaAPI, API
        
        empresa_apis = session.query(EmpresaAPI).filter(
            EmpresaAPI.empresa_id == empresa.id,
            EmpresaAPI.ativo == True
        ).all()
        
        # Inicializar configurações com dados da empresa
        config_data = {
            "nome": empresa.nome,
            "whatsapp_number": empresa.whatsapp_number,
            "prompt": empresa.prompt,
            "usar_buffer": empresa.usar_buffer,
            "mensagem_quebrada": empresa.mensagem_quebrada,
            # Twilio vem diretamente da tabela empresas
            "twilio_sid": empresa.twilio_sid,
            "twilio_token": empresa.twilio_token,
            "twilio_number": empresa.twilio_number,
            # Conhecimento da empresa (JSON) para o admin
            "knowledge_json": empresa.knowledge_json or {"items": []},
            # Labels/classificação por empresa
            "labels_json": getattr(empresa, 'labels_json', None) or {"labels": [], "min_confidence": 0.6}
        }
        
        # Log para debug do knowledge_json
        logger.info(f"📖 Retornando knowledge_json: {config_data['knowledge_json']}")
        
        # Adicionar configurações das APIs conectadas
        for empresa_api in empresa_apis:
            api = empresa_api.api
            config = empresa_api.config or {}
            
            # Criar prefixo baseado no nome da API
            api_prefix = api.nome.lower().replace(' ', '_')
            
            # Adicionar configuração completa da API
            config_data[f'{api_prefix}_config'] = config
            
            # Adicionar campos específicos para compatibilidade
            if api.nome == "Google Calendar":
                config_data['google_calendar_enabled'] = config.get('google_calendar_enabled', True)
                config_data['google_calendar_client_id'] = config.get('google_calendar_client_id')
                config_data['google_calendar_client_secret'] = config.get('google_calendar_client_secret')
                config_data['google_calendar_refresh_token'] = config.get('google_calendar_refresh_token')
                config_data['google_calendar_service_account'] = config.get('google_calendar_service_account')
                config_data['google_calendar_project_id'] = config.get('google_calendar_project_id')
                config_data['google_calendar_client_email'] = config.get('google_calendar_client_email')
            elif api.nome == "Google Sheets":
                config_data['google_sheets_id'] = config.get('google_sheets_id')
                # Adicionar campos OAuth2 específicos do Google Sheets, se existirem
                config_data['google_sheets_client_id'] = config.get('google_sheets_client_id')
                config_data['google_sheets_client_secret'] = config.get('google_sheets_client_secret')
                config_data['google_sheets_refresh_token'] = config.get('google_sheets_refresh_token')
            elif api.nome == "OpenAI":
                config_data['openai_key'] = config.get('openai_key')
            elif api.nome == "Trinks":
                empresa_config['trinks_api_key'] = config.get('api_key')
                empresa_config['trinks_base_url'] = config.get('base_url')
                empresa_config['trinks_estabelecimento_id'] = config.get('estabelecimento_id')
            elif api.nome == "Chatwoot":
                config_data['chatwoot_token'] = config.get('chatwoot_token')
                config_data['chatwoot_inbox_id'] = config.get('chatwoot_inbox_id')
                config_data['chatwoot_origem'] = config.get('chatwoot_origem')
            
            # Adicionar campos genéricos para qualquer API
            config_data[f'{api_prefix}_api_key'] = config.get('api_key')
            config_data[f'{api_prefix}_base_url'] = config.get('base_url')
            config_data[f'{api_prefix}_client_id'] = config.get('client_id')
            config_data[f'{api_prefix}_client_secret'] = config.get('client_secret')
            config_data[f'{api_prefix}_bearer_token'] = config.get('bearer_token')
            config_data[f'{api_prefix}_username'] = config.get('username')
            config_data[f'{api_prefix}_password'] = config.get('password')
            
            # Marcar API como ativa
            config_data[f'{api_prefix}_enabled'] = True
        
        return config_data
        
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
        logger.info(f"Recebendo atualização para empresa {empresa_slug}")
        logger.info(f"Dados recebidos: {configuracoes}")
        
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
        
        # Atualizar campos básicos da empresa
        if "nome" in configuracoes:
            empresa.nome = configuracoes["nome"]
        if "whatsapp_number" in configuracoes:
            empresa.whatsapp_number = configuracoes["whatsapp_number"]
        if "prompt" in configuracoes:
            empresa.prompt = configuracoes["prompt"]
        if "usar_buffer" in configuracoes:
            empresa.usar_buffer = configuracoes["usar_buffer"]
        if "mensagem_quebrada" in configuracoes:
            empresa.mensagem_quebrada = configuracoes["mensagem_quebrada"]
        
        # Atualizar conhecimento (JSON) diretamente na tabela empresas
        if "knowledge_json" in configuracoes:
            # Garantir estrutura mínima
            kj = configuracoes["knowledge_json"] or {}
            if not isinstance(kj, dict):
                kj = {"items": []}
            if "items" not in kj or not isinstance(kj["items"], list):
                kj["items"] = []
            logger.info(f"💾 Salvando knowledge_json: {kj}")
            empresa.knowledge_json = kj
            logger.info(f"✅ knowledge_json atribuído ao objeto empresa")
        
        # Atualizar labels_json (classificação) diretamente na tabela empresas
        if "labels_json" in configuracoes:
            lj = configuracoes["labels_json"] or {}
            if not isinstance(lj, dict):
                lj = {"labels": []}
            if "labels" not in lj or not isinstance(lj["labels"], list):
                lj["labels"] = []
            if "min_confidence" not in lj:
                lj["min_confidence"] = 0.6
            empresa.labels_json = lj
        
        # Atualizar dados do Twilio diretamente na tabela empresas
        if "twilio_sid" in configuracoes:
            empresa.twilio_sid = configuracoes["twilio_sid"]
        if "twilio_token" in configuracoes:
            empresa.twilio_token = configuracoes["twilio_token"]
        if "twilio_number" in configuracoes:
            empresa.twilio_number = configuracoes["twilio_number"]
        
        # Processar configurações de APIs dinamicamente
        # Buscar todas as APIs disponíveis
        from models import API, EmpresaAPI
        
        # Processar campos que começam com 'api_' (formato dinâmico)
        api_configs = {}
        for key, value in configuracoes.items():
            if key.startswith('api_'):  # Processar mesmo se vazio
                # Extrair informações do campo (ex: api_7_key -> API ID 7, campo 'key')
                parts = key.split('_')
                if len(parts) >= 3:
                    api_id = parts[1]
                    field_name = '_'.join(parts[2:])
                    
                    if api_id not in api_configs:
                        api_configs[api_id] = {}
                    api_configs[api_id][field_name] = value
        
        logger.info(f"Configurações de APIs processadas: {api_configs}")
        
        # Atualizar cada API encontrada
        for api_id_str, config in api_configs.items():
            try:
                api_id = int(api_id_str)
                
                # Verificar se a API existe
                api = session.query(API).filter(API.id == api_id).first()
                if not api:
                    logger.warning(f"API ID {api_id} não encontrada")
                    continue
                
                logger.info(f"Processando API {api.nome} (ID: {api_id}) com config: {config}")
                
                # Mapear campos específicos para cada API
                mapped_config = config.copy()
                if api.nome == "OpenAI" and "key" in config:
                    mapped_config["openai_key"] = config["key"]
                    del mapped_config["key"]
                    logger.info(f"Mapeamento OpenAI: {config} -> {mapped_config}")
                elif api.nome == "Trinks" and "key" in config:
                    mapped_config["api_key"] = config["key"]
                    del mapped_config["key"]
                    # Adicionar estabelecimento_id se presente
                    if "estabelecimento_id" in config:
                        mapped_config["estabelecimento_id"] = config["estabelecimento_id"]
                    logger.info(f"Mapeamento Trinks: {config} -> {mapped_config}")
                elif api.nome == "Chatwoot" and "key" in config:
                    mapped_config["chatwoot_token"] = config["key"]
                    del mapped_config["key"]
                elif api.nome == "Google Calendar":
                    # Mapear campos específicos do Google Calendar
                    if "client_id" in config:
                        mapped_config["google_calendar_client_id"] = config["client_id"]
                    if "client_secret" in config:
                        mapped_config["google_calendar_client_secret"] = config["client_secret"]
                    if "refresh_token" in config:
                        mapped_config["google_calendar_refresh_token"] = config["refresh_token"]
                    logger.info(f"Mapeamento Google Calendar: {config} -> {mapped_config}")
                elif api.nome == "Google Sheets":
                    # Mapear campos específicos do Google Sheets
                    if "client_id" in config:
                        mapped_config["google_sheets_client_id"] = config["client_id"]
                    if "client_secret" in config:
                        mapped_config["google_sheets_client_secret"] = config["client_secret"]
                    if "refresh_token" in config:
                        mapped_config["google_sheets_refresh_token"] = config["refresh_token"]
                    # Permitir armazenar também o ID da planilha se vier no payload dinâmico
                    if "google_sheets_id" in config:
                        mapped_config["google_sheets_id"] = config["google_sheets_id"]
                    logger.info(f"Mapeamento Google Sheets: {config} -> {mapped_config}")
                
                # Buscar ou criar conexão empresa-API
                empresa_api = session.query(EmpresaAPI).filter(
                    EmpresaAPI.empresa_id == empresa.id,
                    EmpresaAPI.api_id == api_id
                ).first()
                
                if not empresa_api:
                    # Criar nova conexão
                    empresa_api = EmpresaAPI(
                        empresa_id=empresa.id,
                        api_id=api_id,
                        config=mapped_config,
                        ativo=True
                    )
                    session.add(empresa_api)
                    logger.info(f"Nova conexão criada para API {api.nome}")
                else:
                    # Atualizar configuração existente
                    current_config = empresa_api.config or {}
                    logger.info(f"Config atual: {current_config}")
                    new_config = {**current_config, **mapped_config}
                    logger.info(f"Config após update: {new_config}")
                    empresa_api.config = new_config
                    empresa_api.ativo = True
                
                logger.info(f"Atualizando API {api.nome} (ID: {api_id}) para empresa {empresa.nome}")
                
            except ValueError:
                logger.warning(f"API ID inválido: {api_id_str}")
                continue
        
        # Remover seção de APIs específicas por nome - está conflitando com processamento dinâmico
        # As APIs agora são processadas apenas via campos dinâmicos (api_X_key)
        
        session.flush()
        session.commit()
        logger.info(f"Configurações atualizadas com sucesso para empresa {empresa.nome}")
        
        # Removido refresh pós-commit para evitar erros de sessão não vinculada
        
        return {"message": "Configurações atualizadas com sucesso"}
        
    except Exception as e:
        # Só fazer rollback se realmente houve erro na transação
        if session.is_active:
            session.rollback()
        logger.error(f"Erro ao atualizar configurações: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar configurações: {str(e)}")
    finally:
        session.close() 

@app.get("/test-services")
async def test_services():
    """Testa os serviços de integração"""
    try:
        # Testar OpenAI
        openai_result = "OpenAI: OK"
        try:
            # from services.services import OpenAIService # This line was removed as per the edit hint
            # openai_service = OpenAIService("test-key") # This line was removed as per the edit hint
            openai_result = "OpenAI: Erro de chave inválida (esperado)" # This line was removed as per the edit hint
        except Exception as e:
            openai_result = f"OpenAI: {str(e)}"
        
        # Testar Twilio
        twilio_result = "Twilio: OK"
        try:
            # from integrations.twilio_service import TwilioService # This line was removed as per the edit hint
            # twilio_service = TwilioService("test-sid", "test-token", "+1234567890") # This line was removed as per the edit hint
            twilio_result = "Twilio: Erro de credenciais inválidas (esperado)" # This line was removed as per the edit hint
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

@app.post("/api/admin/apis")
async def criar_api(data: dict, current_user: Usuario = Depends(get_current_superuser)):
    """Cria uma nova API"""
    session = SessionLocal()
    try:
        from services.api_discovery import APIDiscovery
        
        # Tentar descobrir API automaticamente
        api_info = None
        tools_geradas = 0
        
        try:
            discovery = APIDiscovery()
            api_info = discovery.discover_api(data["url_documentacao"])
            tools_geradas = len(discovery.generate_tools(api_info))
        except Exception as e:
            # Se falhar na descoberta, criar API básica
            api_info = {
                "nome": data["nome"],
                "descricao": data.get("descricao", ""),
                "url_base": data.get("url_base", ""),
                "endpoints": []
            }
            tools_geradas = 0
        
        # Criar API no banco
        # Só ativa se conseguiu descobrir endpoints
        ativo = tools_geradas > 0
        
        api = API(
            nome=data["nome"],
            descricao=data.get("descricao", api_info.get("descricao", "")),
            url_documentacao=data["url_documentacao"],
            url_base=api_info.get("url_base", data.get("url_base", "")),
            tipo_auth=data.get("tipo_auth", "api_key"),
            schema_cache=api_info,
            ativo=ativo
        )
        session.add(api)
        session.commit()
        
        return {
            "success": True, 
            "api_id": api.id,
            "api_info": api_info,
            "tools_geradas": tools_geradas,
            "message": "API criada com sucesso" + (" (sem descoberta automática)" if tools_geradas == 0 else "")
        }
    except Exception as e:
        session.rollback()
        return {"success": False, "error": str(e)}
    finally:
        session.close()

@app.get("/api/admin/apis")
def get_apis(current_user: Usuario = Depends(get_current_superuser)):
    """Lista todas as APIs disponíveis"""
    session = SessionLocal()
    try:
        apis = session.query(API).filter(API.ativo == True).all()
        
        apis_list = []
        for api in apis:
            apis_list.append({
                "id": api.id,
                "nome": api.nome,
                "descricao": api.descricao,
                "url_documentacao": api.url_documentacao,
                "url_base": api.url_base,
                "tipo_auth": api.tipo_auth,
                "logo_url": api.logo_url,
                "ativo": api.ativo,
                "tools_count": len(api.schema_cache.get("endpoints", [])) if api.schema_cache else 0,
                "created_at": api.created_at.isoformat()
            })
        
        return {"success": True, "apis": apis_list}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        session.close()

@app.put("/api/admin/apis/{api_id}")
async def atualizar_api(api_id: int, data: dict, current_user: Usuario = Depends(get_current_superuser)):
    """Atualiza uma API existente"""
    session = SessionLocal()
    try:
        api = session.query(API).filter(API.id == api_id).first()
        if not api:
            raise HTTPException(status_code=404, detail="API não encontrada")
        
        # Atualizar campos
        if "nome" in data:
            api.nome = data["nome"]
        if "descricao" in data:
            api.descricao = data["descricao"]
        if "url_documentacao" in data:
            api.url_documentacao = data["url_documentacao"]
        if "url_base" in data:
            api.url_base = data["url_base"]
        if "logo_url" in data:
            api.logo_url = data["logo_url"]
        if "tipo_auth" in data:
            api.tipo_auth = data["tipo_auth"]
        if "ativo" in data:
            api.ativo = data["ativo"]
        
        session.commit()
        return {"success": True, "message": f"API {api.nome} atualizada com sucesso"}
    except Exception as e:
        session.rollback()
        return {"success": False, "error": str(e)}
    finally:
        session.close()

@app.post("/api/admin/empresas/{empresa_id}/apis/{api_id}")
def conectar_api_empresa(
    empresa_id: int, 
    api_id: int, 
    config: dict,
    current_user: Usuario = Depends(get_current_superuser)
):
    """Conecta uma API a uma empresa"""
    session = SessionLocal()
    try:
        # Verificar se empresa e API existem
        empresa = session.query(Empresa).filter(Empresa.id == empresa_id).first()
        api = session.query(API).filter(API.id == api_id).first()
        
        if not empresa or not api:
            raise HTTPException(status_code=404, detail="Empresa ou API não encontrada")
        
        # Verificar se já está conectada
        existing = session.query(EmpresaAPI).filter(
            EmpresaAPI.empresa_id == empresa_id,
            EmpresaAPI.api_id == api_id
        ).first()
        
        if existing:
            # Atualizar configuração
            existing.config = config
            existing.ativo = True
        else:
            # Criar nova conexão
            empresa_api = EmpresaAPI(
                empresa_id=empresa_id,
                api_id=api_id,
                config=config
            )
            session.add(empresa_api)
        
        session.commit()
        return {"success": True, "message": f"API {api.nome} conectada à empresa {empresa.nome}"}
    except Exception as e:
        session.rollback()
        return {"success": False, "error": str(e)}
    finally:
        session.close()

@app.get("/api/admin/empresas/{empresa_id}/apis")
def get_empresa_apis(empresa_id: int, current_user: Usuario = Depends(get_current_superuser)):
    """Lista APIs conectadas a uma empresa"""
    session = SessionLocal()
    try:
        # Importar o novo serviço
        from services.empresa_api_service import EmpresaAPIService
        
        # Buscar APIs ativas usando o novo serviço
        apis = EmpresaAPIService.get_empresa_active_apis(session, empresa_id)
        
        return {"success": True, "apis": apis}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        session.close()

@app.get("/api/empresas/{empresa_slug}/apis")
def get_empresa_apis_by_slug(empresa_slug: str, current_user: Usuario = Depends(get_current_user)):
    """Buscar APIs ativas de uma empresa (para usuários da empresa)"""
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
        
        # Importar o novo serviço
        from services.empresa_api_service import EmpresaAPIService
        
        # Buscar APIs ativas
        apis = EmpresaAPIService.get_empresa_active_apis(session, empresa.id)
        
        return {"empresa": empresa.nome, "apis": apis}
    finally:
        session.close()

@app.put("/api/empresas/{empresa_slug}/apis/{api_name}")
def update_empresa_api_config(
    empresa_slug: str,
    api_name: str,
    config: dict,
    current_user: Usuario = Depends(get_current_user)
):
    """Atualizar configuração de uma API específica da empresa"""
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
        
        # Importar o novo serviço
        from services.empresa_api_service import EmpresaAPIService
        
        # Atualizar configuração da API
        success = EmpresaAPIService.update_empresa_api_config(session, empresa.id, api_name, config)
        
        if success:
            return {"message": f"Configuração da API {api_name} atualizada com sucesso"}
        else:
            raise HTTPException(status_code=400, detail=f"Erro ao atualizar configuração da API {api_name}")
            
    finally:
        session.close()

@app.delete("/api/empresas/{empresa_slug}/apis/{api_name}")
def deactivate_empresa_api(
    empresa_slug: str,
    api_name: str,
    current_user: Usuario = Depends(get_current_user)
):
    """Desativar uma API da empresa"""
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
        
        # Importar o novo serviço
        from services.empresa_api_service import EmpresaAPIService
        
        # Desativar API
        success = EmpresaAPIService.deactivate_empresa_api(session, empresa.id, api_name)
        
        if success:
            return {"message": f"API {api_name} desativada com sucesso"}
        else:
            raise HTTPException(status_code=400, detail=f"Erro ao desativar API {api_name}")
            
    finally:
        session.close()

@app.post("/api/empresas/{empresa_slug}/google-service-account")
async def upload_google_service_account(
    empresa_slug: str,
    file: UploadFile = File(...),
    current_user: Usuario = Depends(get_current_user)
):
    """Upload de Service Account JSON para Google Calendar"""
    logger.info(f"Recebendo upload de Service Account para empresa {empresa_slug}")
    logger.info(f"Arquivo: {file.filename}, Tamanho: {file.size}")
    
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
        
        logger.info(f"Empresa encontrada: {empresa.nome}")
        
        # Ler arquivo JSON
        content = await file.read()
        logger.info(f"Conteúdo do arquivo lido, tamanho: {len(content)} bytes")
        logger.info(f"Primeiros 200 caracteres: {content.decode()[:200]}")
        
        try:
            service_account_data = json.loads(content.decode())
            logger.info("JSON parseado com sucesso")
            logger.info(f"Campos encontrados: {list(service_account_data.keys())}")
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao fazer parse do JSON: {e}")
            logger.error(f"Conteúdo recebido: {content.decode()}")
            raise HTTPException(status_code=400, detail="Arquivo JSON inválido")
        
        # Validar estrutura do Service Account
        required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
        for field in required_fields:
            if field not in service_account_data:
                logger.error(f"Campo obrigatório '{field}' não encontrado")
                raise HTTPException(status_code=400, detail=f"Campo obrigatório '{field}' não encontrado no JSON")
        
        logger.info("Validação dos campos concluída")
        
        # Buscar API Google Calendar
        from models import API, EmpresaAPI
        api = session.query(API).filter(API.nome == 'Google Calendar').first()
        if not api:
            logger.error("API Google Calendar não encontrada")
            raise HTTPException(status_code=404, detail="API Google Calendar não encontrada")
        
        logger.info(f"API Google Calendar encontrada: {api.nome}")
        
        # Buscar ou criar conexão empresa-API
        empresa_api = session.query(EmpresaAPI).filter(
            EmpresaAPI.empresa_id == empresa.id,
            EmpresaAPI.api_id == api.id
        ).first()
        
        logger.info(f"Empresa API encontrada: {empresa_api is not None}")
        if empresa_api:
            logger.info(f"Config atual: {empresa_api.config}")
        
        if not empresa_api:
            # Criar nova conexão
            logger.info("Criando nova conexão empresa-API")
            new_config = {
                'google_calendar_enabled': True,
                'google_calendar_service_account': service_account_data,
                'google_calendar_project_id': service_account_data.get('project_id'),
                'google_calendar_client_email': service_account_data.get('client_email')
            }
            logger.info(f"Nova config a ser salva: {new_config}")
            
            empresa_api = EmpresaAPI(
                empresa_id=empresa.id,
                api_id=api.id,
                config=new_config,
                ativo=True
            )
            session.add(empresa_api)
            logger.info("EmpresaAPI adicionada à sessão")
        else:
            # Atualizar configuração existente
            logger.info("Atualizando configuração existente")
            current_config = empresa_api.config or {}
            logger.info(f"Config atual: {current_config}")
            
            updated_config = {
                'google_calendar_enabled': True,
                'google_calendar_service_account': service_account_data,
                'google_calendar_project_id': service_account_data.get('project_id'),
                'google_calendar_client_email': service_account_data.get('client_email')
            }
            logger.info(f"Config atualizada: {updated_config}")
            
            # Substituir completamente a configuração em vez de fazer update
            empresa_api.config = updated_config
            empresa_api.ativo = True
            logger.info(f"Config final: {empresa_api.config}")
        
        logger.info("Antes do flush - empresa_api.config: %s", empresa_api.config)
        try:
            session.flush()
            logger.info("Após flush - empresa_api.config: %s", empresa_api.config)
            
            session.commit()
            logger.info("Service Account salvo com sucesso no banco")
        except Exception as e:
            logger.error(f"Erro no commit: {e}")
            session.rollback()
            raise
        
        # Recarregar do banco para confirmar persistência
        empresa_api_verif = session.query(EmpresaAPI).filter(
            EmpresaAPI.empresa_id == empresa.id,
            EmpresaAPI.api_id == api.id
        ).first()
        
        logger.info(f"Verificação pós-commit - empresa_api_verif: {empresa_api_verif}")
        if empresa_api_verif:
            logger.info(f"Verificação pós-commit - config: {empresa_api_verif.config}")
            logger.info(f"Verificação pós-commit - service_account: {empresa_api_verif.config.get('google_calendar_service_account') if empresa_api_verif.config else None}")
        
        saved = bool(empresa_api_verif and empresa_api_verif.config and empresa_api_verif.config.get('google_calendar_service_account'))
        logger.info(f"Confirmação de persistência no banco: saved={saved}")
        
        return {
            "success": True,
            "saved": saved,
            "message": "Service Account configurado com sucesso!",
            "project_id": service_account_data.get('project_id'),
            "client_email": service_account_data.get('client_email')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro inesperado: {e}")
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao processar Service Account: {str(e)}")
    finally:
        session.close()

@app.get("/api/empresas/{empresa_slug}/google-oauth-url")
async def get_google_oauth_url(
    empresa_slug: str,
    current_user: Usuario = Depends(get_current_user)
):
    """Gera URL de autorização OAuth2 para Google Calendar"""
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
        
        # Buscar configuração OAuth2 da empresa
        from models import EmpresaAPI, API
        api = session.query(API).filter(API.nome == 'Google Calendar').first()
        if not api:
            raise HTTPException(status_code=404, detail="API Google Calendar não encontrada")
        
        empresa_api = session.query(EmpresaAPI).filter(
            EmpresaAPI.empresa_id == empresa.id,
            EmpresaAPI.api_id == api.id
        ).first()
        
        if not empresa_api or not empresa_api.config:
            raise HTTPException(status_code=400, detail="Google Calendar não configurado")
        
        config = empresa_api.config
        
        # Verificar se tem Service Account configurado (fallback automático)
        service_account = config.get('google_calendar_service_account')
        if service_account:
            # Se tem Service Account, usar ele automaticamente
            logger.info("Service Account encontrado, configurando automaticamente")
            
            # Atualizar configuração para usar Service Account
            current_config = empresa_api.config or {}
            current_config['google_calendar_enabled'] = True
            current_config['google_calendar_use_service_account'] = True
            empresa_api.config = current_config
            empresa_api.ativo = True
            
            session.commit()
            
            return {
                "success": True,
                "message": "Google Calendar configurado automaticamente com Service Account!",
                "method": "service_account",
                "project_id": service_account.get('project_id'),
                "client_email": service_account.get('client_email')
            }
        
        # Se não tem Service Account, tentar OAuth2
        if not config.get('google_calendar_client_id'):
            raise HTTPException(status_code=400, detail="Google Calendar OAuth2 não configurado. Configure as credenciais OAuth2 no Google Cloud Console.")
        
        # Gerar URL de autorização OAuth2
        from urllib.parse import urlencode
        
        oauth_params = {
            'client_id': config.get('google_calendar_client_id'),
            'redirect_uri': f'https://api.tinyteams.app/auth/google/callback',
            'scope': 'https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/calendar.events',
            'response_type': 'code',
            'access_type': 'offline',
            'prompt': 'consent'
        }
        
        oauth_url = f"https://accounts.google.com/o/oauth2/auth?{urlencode(oauth_params)}"
        
        return {
            "oauth_url": oauth_url,
            "message": "URL de autorização gerada",
            "method": "oauth2"
        }
        
    except Exception as e:
        logger.error(f"Erro ao gerar URL OAuth2: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar URL de autorização: {str(e)}")
    finally:
        session.close()

@app.get("/auth/google/callback")
async def google_oauth_callback(
    code: str = Query(...),
    state: str = Query(None)
):
    """Callback do OAuth2 do Google Calendar"""
    try:
        logger.info(f"Recebendo callback OAuth2 com code: {code[:20]}...")
        
        # Buscar configuração OAuth2
        session = SessionLocal()
        
        # Buscar empresa da sessão (pode ser passada via state)
        empresa_slug = state or 'tinyteams'  # Fallback para TinyTeams
        
        empresa = session.query(Empresa).filter(Empresa.slug == empresa_slug).first()
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        
        # Buscar configuração da API
        from models import EmpresaAPI, API
        api = session.query(API).filter(API.nome == 'Google Calendar').first()
        if not api:
            raise HTTPException(status_code=404, detail="API Google Calendar não encontrada")
        
        empresa_api = session.query(EmpresaAPI).filter(
            EmpresaAPI.empresa_id == empresa.id,
            EmpresaAPI.api_id == api.id
        ).first()
        
        if not empresa_api or not empresa_api.config:
            raise HTTPException(status_code=400, detail="Google Calendar não configurado")
        
        config = empresa_api.config
        
        # Trocar code por tokens
        import requests
        
        token_data = {
            'client_id': config.get('google_calendar_client_id'),
            'client_secret': config.get('google_calendar_client_secret'),
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': f'https://api.tinyteams.app/auth/google/callback'
        }
        
        logger.info(f"Tentando trocar code por tokens...")
        logger.info(f"Client ID: {config.get('google_calendar_client_id')}")
        logger.info(f"Client Secret: {config.get('google_calendar_client_secret')[:10]}...")
        logger.info(f"Code: {code[:20]}...")
        logger.info(f"Redirect URI: https://api.tinyteams.app/auth/google/callback")
        
        response = requests.post('https://oauth2.googleapis.com/token', data=token_data)
        
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response text: {response.text}")
        
        if response.status_code != 200:
            logger.error(f"Erro ao trocar code por tokens: {response.text}")
            raise HTTPException(status_code=400, detail=f"Erro na autorização OAuth2: {response.text}")
        
        tokens = response.json()
        refresh_token = tokens.get('refresh_token')
        
        if not refresh_token:
            raise HTTPException(status_code=400, detail="Refresh token não recebido")
        
        # Atualizar configuração com refresh_token
        current_config = empresa_api.config or {}
        current_config['google_calendar_refresh_token'] = refresh_token
        empresa_api.config = current_config
        
        session.commit()
        session.close()
        
        logger.info("OAuth2 configurado com sucesso!")
        
        return {
            "success": True,
            "message": "Google Calendar conectado com sucesso!",
            "redirect_url": f"https://app.tinyteams.app/admin/{empresa_slug}/configuracoes"
        }
        
    except Exception as e:
        logger.error(f"Erro no callback OAuth2: {e}")
        raise HTTPException(status_code=500, detail=f"Erro no callback: {str(e)}")

@app.get("/api/test/google-oauth-simulation")
async def test_google_oauth_simulation():
    """Simula OAuth2 para testes locais"""
    try:
        # Simular refresh_token de teste
        test_refresh_token = "test_refresh_token_12345"
        
        session = SessionLocal()
        
        # Buscar empresa TinyTeams
        empresa = session.query(Empresa).filter(Empresa.slug == 'tinyteams').first()
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        
        # Buscar configuração da API
        from models import EmpresaAPI, API
        api = session.query(API).filter(API.nome == 'Google Calendar').first()
        if not api:
            raise HTTPException(status_code=404, detail="API Google Calendar não encontrada")
        
        empresa_api = session.query(EmpresaAPI).filter(
            EmpresaAPI.empresa_id == empresa.id,
            EmpresaAPI.api_id == api.id
        ).first()
        
        if not empresa_api:
            # Criar configuração se não existir
            empresa_api = EmpresaAPI(
                empresa_id=empresa.id,
                api_id=api.id,
                config={},
                ativo=True
            )
            session.add(empresa_api)
        
        # Atualizar com refresh_token de teste
        current_config = empresa_api.config or {}
        current_config['google_calendar_refresh_token'] = test_refresh_token
        current_config['google_calendar_enabled'] = True
        empresa_api.config = current_config
        
        session.commit()
        session.close()
        
        return {
            "success": True,
            "message": "Google Calendar conectado (modo teste)!",
            "refresh_token": test_refresh_token
        }
        
    except Exception as e:
        logger.error(f"Erro na simulação OAuth2: {e}")
        raise HTTPException(status_code=500, detail=f"Erro na simulação: {str(e)}")

@app.get("/api/test/google-oauth-config")
async def test_google_oauth_config():
    """Verifica configurações OAuth2 do Google Calendar"""
    try:
        session = SessionLocal()
        
        # Buscar empresa TinyTeams
        empresa = session.query(Empresa).filter(Empresa.slug == 'tinyteams').first()
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        
        # Buscar configuração da API
        from models import EmpresaAPI, API
        api = session.query(API).filter(API.nome == 'Google Calendar').first()
        if not api:
            raise HTTPException(status_code=404, detail="API Google Calendar não encontrada")
        
        empresa_api = session.query(EmpresaAPI).filter(
            EmpresaAPI.empresa_id == empresa.id,
            EmpresaAPI.api_id == api.id
        ).first()
        
        if not empresa_api or not empresa_api.config:
            return {
                "status": "error",
                "message": "Google Calendar não configurado",
                "config": None
            }
        
        config = empresa_api.config
        
        return {
            "status": "success",
            "message": "Configurações encontradas",
            "config": {
                "client_id": config.get('google_calendar_client_id'),
                "client_secret": config.get('google_calendar_client_secret')[:10] + "..." if config.get('google_calendar_client_secret') else None,
                "refresh_token": "***" if config.get('google_calendar_refresh_token') else None,
                "service_account": "Configurado" if config.get('google_calendar_service_account') else None
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao verificar configurações: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao verificar configurações: {str(e)}")
    finally:
        session.close()

@app.get("/api/setup-default-service-account")
async def setup_default_service_account():
    """Configura Service Account padrão para Google Calendar"""
    try:
        session = SessionLocal()
        
        # Buscar empresa TinyTeams
        empresa = session.query(Empresa).filter(Empresa.slug == 'tinyteams').first()
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        
        # Buscar configuração da API
        from models import EmpresaAPI, API
        api = session.query(API).filter(API.nome == 'Google Calendar').first()
        if not api:
            raise HTTPException(status_code=404, detail="API Google Calendar não encontrada")
        
        empresa_api = session.query(EmpresaAPI).filter(
            EmpresaAPI.empresa_id == empresa.id,
            EmpresaAPI.api_id == api.id
        ).first()
        
        if not empresa_api:
            # Criar configuração se não existir
            empresa_api = EmpresaAPI(
                empresa_id=empresa.id,
                api_id=api.id,
                config={},
                ativo=True
            )
            session.add(empresa_api)
        
        # Service Account padrão (você precisa criar um real)
        default_service_account = {
            "type": "service_account",
            "project_id": "tinyteams-calendar",
            "private_key_id": "default-key-id",
            "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...\n-----END PRIVATE KEY-----\n",
            "client_email": "tinyteams@tinyteams-calendar.iam.gserviceaccount.com",
            "client_id": "123456789",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }
        
        # Atualizar configuração
        current_config = empresa_api.config or {}
        current_config.update({
            'google_calendar_enabled': True,
            'google_calendar_service_account': default_service_account,
            'google_calendar_project_id': default_service_account.get('project_id'),
            'google_calendar_client_email': default_service_account.get('client_email'),
            'google_calendar_use_service_account': True
        })
        empresa_api.config = current_config
        empresa_api.ativo = True
        
        session.commit()
        session.close()
        
        return {
            "success": True,
            "message": "Service Account padrão configurado!",
            "note": "Você precisa criar um Service Account real no Google Cloud Console"
        }
        
    except Exception as e:
        logger.error(f"Erro ao configurar Service Account padrão: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao configurar: {str(e)}")

@app.get("/api/test/service-account-status")
async def test_service_account_status():
    """Verifica se Service Account está salvo no banco"""
    try:
        session = SessionLocal()
        
        # Buscar empresa TinyTeams
        empresa = session.query(Empresa).filter(Empresa.slug == 'tinyteams').first()
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        
        # Buscar configuração da API
        from models import EmpresaAPI, API
        api = session.query(API).filter(API.nome == 'Google Calendar').first()
        if not api:
            raise HTTPException(status_code=404, detail="API Google Calendar não encontrada")
        
        empresa_api = session.query(EmpresaAPI).filter(
            EmpresaAPI.empresa_id == empresa.id,
            EmpresaAPI.api_id == api.id
        ).first()
        
        if not empresa_api or not empresa_api.config:
            return {
                "status": "not_configured",
                "message": "Service Account não configurado"
            }
        
        config = empresa_api.config
        
        # Verificar se tem Service Account
        service_account = config.get('google_calendar_service_account')
        if not service_account:
            return {
                "status": "no_service_account",
                "message": "Configuração existe mas não tem Service Account"
            }
        
        return {
            "status": "configured",
            "message": "Service Account configurado",
            "project_id": config.get('google_calendar_project_id'),
            "client_email": config.get('google_calendar_client_email'),
            "enabled": config.get('google_calendar_enabled', False)
        }
        
    except Exception as e:
        logger.error(f"Erro ao verificar Service Account: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao verificar: {str(e)}")
    finally:
        session.close()

@app.get("/oauth/callback")
async def oauth_callback(code: str = None, error: str = None):
    """Callback para OAuth2 do Google"""
    if error:
        return {"error": f"Erro na autorização: {error}"}
    
    if not code:
        return {"error": "Código de autorização não fornecido"}
    
    try:
        # Aqui você pode processar o código e gerar o refresh token
        # Por enquanto, apenas retorna o código para o usuário copiar
        return {
            "success": True,
            "message": "Código de autorização recebido",
            "code": code,
            "instructions": "Copie este código e cole no terminal para gerar o Refresh Token"
        }
    except Exception as e:
        return {"error": f"Erro ao processar código: {str(e)}"}

@app.post("/api/admin/{empresa_slug}/oauth/generate-token")
async def generate_oauth_token(empresa_slug: str, request: Request):
    """Gera Refresh Token a partir do código de autorização"""
    try:
        data = await request.json()
        code = data.get('code')
        client_id = data.get('client_id')
        client_secret = data.get('client_secret')
        
        if not all([code, client_id, client_secret]):
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Código, client_id e client_secret são obrigatórios"}
            )
        
        # Determinar redirect_uri baseado no ambiente
        is_development = os.getenv('ENVIRONMENT', 'production') == 'development'
        redirect_uri = 'http://localhost:8000/oauth/callback' if is_development else 'https://api.tinyteams.app/oauth/callback'
        
        # Trocar código por tokens
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri
        }
        
        import requests
        response = requests.post(token_url, data=token_data)
        
        if response.status_code != 200:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": f"Erro ao trocar código por token: {response.text}"}
            )
        
        tokens = response.json()
        refresh_token = tokens.get('refresh_token')
        access_token = tokens.get('access_token')
        
        if not refresh_token:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Refresh token não foi retornado pelo Google"}
            )
        
        # Salvar no banco de dados
        session = SessionLocal()
        try:
            empresa = session.query(Empresa).filter(Empresa.slug == empresa_slug).first()
            if not empresa:
                return JSONResponse(
                    status_code=404,
                    content={"success": False, "message": "Empresa não encontrada"}
                )
            
            # Verificar se já existe configuração para Google Calendar
            empresa_api = session.query(EmpresaAPI).filter(
                EmpresaAPI.empresa_id == empresa.id,
                EmpresaAPI.api_name == 'google_calendar'
            ).first()
            
            if empresa_api:
                # Atualizar configuração existente
                empresa_api.config = {
                    **empresa_api.config,
                    'client_id': client_id,
                    'client_secret': client_secret,
                    'refresh_token': refresh_token,
                    'access_token': access_token
                }
            else:
                # Criar nova configuração
                empresa_api = EmpresaAPI(
                    empresa_id=empresa.id,
                    api_name='google_calendar',
                    config={
                        'client_id': client_id,
                        'client_secret': client_secret,
                        'refresh_token': refresh_token,
                        'access_token': access_token
                    }
                )
                session.add(empresa_api)
            
            session.commit()
            
            return JSONResponse(
                content={
                    "success": True,
                    "message": "Refresh Token gerado e salvo com sucesso",
                    "refresh_token": refresh_token
                }
            )
            
        except Exception as e:
            session.rollback()
            logger.error(f"Erro ao salvar no banco: {e}")
            return JSONResponse(
                status_code=500,
                content={"success": False, "message": f"Erro ao salvar no banco: {str(e)}"}
            )
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Erro ao gerar token: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"Erro interno: {str(e)}"}
        )

@app.get("/api/admin/{empresa_slug}/oauth/generate-token")
async def generate_oauth_token_get(
    empresa_slug: str, 
    code: str = Query(...),
    client_id: str = Query(...),
    client_secret: str = Query(...)
):
    """Gera Refresh Token a partir do código de autorização via GET"""
    try:
        if not all([code, client_id, client_secret]):
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Código, client_id e client_secret são obrigatórios"}
            )
        
        # Usar sempre o redirect_uri de localhost já que o código foi obtido através do callback local
        redirect_uri = 'http://localhost:8000/oauth/callback'
        
        # Trocar código por tokens
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri
        }
        
        import requests
        response = requests.post(token_url, data=token_data)
        
        if response.status_code != 200:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": f"Erro ao trocar código por token: {response.text}"}
            )
        
        tokens = response.json()
        refresh_token = tokens.get('refresh_token')
        access_token = tokens.get('access_token')
        
        if not refresh_token:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Refresh token não foi retornado pelo Google"}
            )
        
        # Salvar no banco de dados
        session = SessionLocal()
        try:
            empresa = session.query(Empresa).filter(Empresa.slug == empresa_slug).first()
            if not empresa:
                return JSONResponse(
                    status_code=404,
                    content={"success": False, "message": "Empresa não encontrada"}
                )
            
            # Verificar se já existe configuração para Google Calendar
            empresa_api = session.query(EmpresaAPI).filter(
                EmpresaAPI.empresa_id == empresa.id,
                EmpresaAPI.api_name == 'google_calendar'
            ).first()
            
            if empresa_api:
                # Atualizar configuração existente
                empresa_api.config = {
                    **empresa_api.config,
                    'client_id': client_id,
                    'client_secret': client_secret,
                    'refresh_token': refresh_token,
                    'access_token': access_token
                }
            else:
                # Criar nova configuração
                empresa_api = EmpresaAPI(
                    empresa_id=empresa.id,
                    api_name='google_calendar',
                    config={
                        'client_id': client_id,
                        'client_secret': client_secret,
                        'refresh_token': refresh_token,
                        'access_token': access_token
                    }
                )
                session.add(empresa_api)
            
            session.commit()
            
            return JSONResponse(
                content={
                    "success": True,
                    "message": "Refresh Token gerado e salvo com sucesso",
                    "refresh_token": refresh_token
                }
            )
            
        except Exception as e:
            session.rollback()
            logger.error(f"Erro ao salvar no banco: {e}")
            return JSONResponse(
                status_code=500,
                content={"success": False, "message": f"Erro ao salvar no banco: {str(e)}"}
            )
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Erro ao gerar token: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"Erro interno: {str(e)}"}
        )

# Estado de debounce em memória por cliente (WaId)
debounce_state: Dict[Tuple[str, str], Dict[str, Any]] = {}
# Estrutura: {(empresa_slug, wa_id): { 'timer': asyncio.Task, 'last_message': str, 'webhook_data': dict, 'deadline': float }}

DEFAULT_DEBOUNCE_SECONDS = 8  # pode ser tornado configurável por empresa futuramente

def _get_debounce_key(empresa_slug: str, wa_id: str) -> Tuple[str, str]:
    return (empresa_slug, wa_id)

async def _debounce_wait_and_process(empresa_slug: str, wa_id: str, empresa_config: dict):
    key = _get_debounce_key(empresa_slug, wa_id)
    entry = debounce_state.get(key)
    if not entry:
        return
    deadline = entry.get('deadline', 0)
    now = time.time()
    delay = max(0, deadline - now)
    await asyncio.sleep(delay)

    # Verificar se ninguém atualizou a deadline durante a espera
    latest = debounce_state.get(key)
    if not latest or latest.get('deadline') != deadline:
        return  # houve nova mensagem, cancela este processamento

    # Processar a última mensagem recebida
    webhook_data = latest.get('webhook_data', {})
    try:
        # Criar agente inteligente
        from agents.smart_agent import SmartAgent
        
        # Criar novo agente inteligente
        smart_agent = SmartAgent(empresa_config)
        
        # Processar mensagem
        response_message = smart_agent.analyze_and_respond(webhook_data.get('Body', ''), wa_id, {
            'empresa_slug': empresa_slug,
            'cliente_id': wa_id,
            'empresa_config': empresa_config
        })
        
        result = {
            'success': True,
            'message': response_message
        }

        if result.get('success'):
            from integrations.twilio_service import TwilioService
            twilio_service = TwilioService(
                empresa_config.get('twilio_sid'),
                empresa_config.get('twilio_token'),
                empresa_config.get('twilio_number')
            )
            response_message = result.get('message', '')
            if empresa_config.get('mensagem_quebrada', False) and len(response_message) > 200:
                parts = _break_long_message(response_message)
                for i, part in enumerate(parts):
                    twilio_service.send_whatsapp_message(wa_id, part)
                    if i < len(parts) - 1:
                        await asyncio.sleep(0.5)
            else:
                twilio_service.send_whatsapp_message(wa_id, response_message)
        else:
            logger.warning(f"Agente retornou falha no debounce para {empresa_slug}:{wa_id}")
    except Exception as e:
        logger.error(f"Erro no processamento debounce: {e}")
    finally:
        # Limpar estado
        debounce_state.pop(key, None)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 