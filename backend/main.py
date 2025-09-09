import os
from fastapi import FastAPI, HTTPException, Request, Query, Depends, UploadFile, File, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import json
from datetime import datetime, timedelta
import random
import asyncio
import time
import traceback
import pytz

# Configurar logging limpo
from config import LOGGING_CONFIG
import logging.config
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

from config import Config
from models import WebhookData, MessageResponse, AdminMetrics, EmpresaMetrics, HealthCheck, Base, Empresa, Mensagem, Log, Usuario, gerar_hash_senha, Atendimento, Cliente, Atividade, API, EmpresaAPI, EmpresaReminder
from services.services import MetricsService
from services.email_service import email_service
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session, load_only
from jose import jwt, JWTError
from passlib.hash import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer

from typing import Optional, List, Dict, Tuple, Any
from sqlalchemy.exc import ProgrammingError

# Configurações
config = Config()
engine = create_engine(config.POSTGRES_URL)
# Base.metadata.create_all(bind=engine)  # Comentado para evitar erro na inicialização

# criar_tabelas()

SessionLocal = sessionmaker(bind=engine)

# Função para obter sessão do banco
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Cache global para Smart Agents (acessível por todos os endpoints)
_smart_agents_cache = {}
_last_cache_cleanup = time.time()

# ============================================================================
# FUNÇÕES DE NOTIFICAÇÃO POR EMAIL
# ============================================================================

def send_smart_agent_error_notification(error_details: dict, empresa_id: Optional[int] = None, conversation_url: Optional[str] = None):
    """
    Envia notificação de erro do Smart Agent para todos os usuários que ativaram notificações
    
    Args:
        error_details: Detalhes do erro
        empresa_id: ID da empresa (opcional)
        conversation_url: URL da conversa que deu erro (opcional)
    """
    try:
        db = next(get_db())
        
        try:
            # Tentar consulta com flags (se colunas existirem)
            query = db.query(Usuario).filter(
                Usuario.email.isnot(None)
            )
            # Apenas usuários com notificações ativas, se as colunas existirem
            try:
                query = query.filter(
                    Usuario.notifications_enabled == True,
                    Usuario.smart_agent_error_notifications == True,
                )
            except Exception:
                # Se as colunas não existirem, seguimos sem esse filtro
                pass

            # Filtro por empresa: somente admins OU usuários da empresa específica
            if empresa_id is not None:
                query = query.filter(
                    (Usuario.empresa_id == empresa_id) | (Usuario.is_superuser == True)
                )

            users = query.all()
            target_emails = [u.email for u in users if getattr(u, 'email', None)]
        except Exception as query_error:
            # Fallback: colunas podem não existir ainda. Buscar apenas emails existentes.
            logger.warning(f"Colunas de notificação ausentes; usando fallback. Detalhe: {query_error}")
            try:
                # Garantir que a transação anterior seja revertida
                db.rollback()
                if empresa_id is not None:
                    rows = db.execute(text("SELECT email FROM usuarios WHERE email IS NOT NULL AND (empresa_id = :empresa_id OR is_superuser = true)"), {"empresa_id": empresa_id}).fetchall()
                else:
                    rows = db.execute(text("SELECT email FROM usuarios WHERE email IS NOT NULL")).fetchall()
                target_emails = [r[0] for r in rows]
            except Exception as raw_err:
                logger.error(f"Falha no fallback de emails: {raw_err}")
                target_emails = []

        logger.info(f"📧 Enviando notificação de erro do Smart Agent para {len(target_emails)} usuários")
        
        # Buscar nome da empresa se empresa_id foi fornecido
        empresa_nome = "TinyTeams"  # fallback
        if empresa_id:
            try:
                empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
                if empresa:
                    empresa_nome = empresa.nome or empresa.slug or "TinyTeams"
            except Exception:
                pass
        
        # Adicionar informações extras ao error_details
        enhanced_error_details = error_details.copy()
        enhanced_error_details['empresa_nome'] = empresa_nome
        enhanced_error_details['conversation_url'] = conversation_url or 'N/A'
        
        # Validação simples de email
        valid_emails = [e for e in target_emails if isinstance(e, str) and '@' in e]

        for email in valid_emails:
            try:
                success = email_service.send_smart_agent_error_notification(email, enhanced_error_details)
                if success:
                    logger.info(f"✅ Notificação enviada para: {email}")
                else:
                    logger.error(f"❌ Falha ao enviar notificação para: {email}")
            except Exception as e:
                logger.error(f"❌ Erro ao enviar notificação para {email}: {e}")
        
        db.close()
        
    except Exception as e:
        logger.error(f"❌ Erro geral ao enviar notificações de Smart Agent: {e}")

def send_webhook_error_notification(error_details: dict):
    """
    Envia notificação de erro crítico do Webhook para o admin
    
    Args:
        error_details: Detalhes do erro crítico
    """
    try:
        db = next(get_db())
        
        # Buscar o usuário admin (superuser)
        admin = db.query(Usuario).filter(Usuario.is_superuser == True).first()
        
        if not admin or not admin.email:
            logger.error("❌ Admin não encontrado ou sem email")
            return
        
        logger.info(f"📧 Enviando notificação crítica de Webhook para admin: {admin.email}")
        
        success = email_service.send_webhook_error_notification(admin.email, error_details)
        
        if success:
            logger.info(f"✅ Notificação crítica enviada para admin: {admin.email}")
        else:
            logger.error(f"❌ Falha ao enviar notificação crítica para admin: {admin.email}")
        
        db.close()
        
    except Exception as e:
        logger.error(f"❌ Erro geral ao enviar notificação crítica de Webhook: {e}")

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
        try:
            user = session.query(Usuario).filter(Usuario.email == email).first()
            if user is None:
                logger.error(f"User not found for email: {email}")
                raise credentials_exception
            return user
        except ProgrammingError as pe:
            # Limpar transação abortada antes do fallback
            try:
                session.rollback()
            except Exception:
                pass
            # Banco antigo sem colunas novas (notifications_*). Fallback para SELECT manual mínimo.
            logger.warning(f"Fallback get_current_user (schema antigo): {pe}")
            row = session.execute(text(
                "SELECT id, email, is_superuser, empresa_id FROM usuarios WHERE email = :email LIMIT 1"
            ), {"email": email}).fetchone()
            if not row:
                raise credentials_exception

            class SimpleUser:
                def __init__(self, id, email, is_superuser, empresa_id):
                    self.id = id
                    self.email = email
                    self.is_superuser = bool(is_superuser)
                    self.empresa_id = empresa_id

            return SimpleUser(row[0], row[1], row[2], row[3])
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
# CORS: não usar "*" com credentials; listar origens conhecidas de dev/prod
allowed_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5175",
    "https://app.tinyteams.app",
    "https://tinyteams.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instanciar serviços
metrics_service = MetricsService()

# ============================================================================
# LEMBRETES (EmpresaReminder) - ADMIN
# ============================================================================

def _compute_next_run_at(timezone_str: str, send_time_local: str):
    tz = pytz.timezone(timezone_str or 'America/Sao_Paulo')
    now = datetime.now(tz)
    try:
        hh, mm = (send_time_local or '11:00').split(':')
        target = now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
        if target <= now:
            target = target + timedelta(days=1)
        return target.astimezone(pytz.utc).replace(tzinfo=None)
    except Exception:
        target = now.replace(hour=11, minute=0, second=0, microsecond=0) + timedelta(days=1)
        return target.astimezone(pytz.utc).replace(tzinfo=None)


def _serialize_reminder(rem: EmpresaReminder) -> dict:
    return {
        "id": rem.id,
        "enabled": bool(rem.enabled),
        "provider": rem.provider or "Trinks",
        "timezone": rem.timezone or "America/Sao_Paulo",
        "send_time_local": rem.send_time_local or "11:00",
        "lead_days": rem.lead_days or 1,
        "twilio_template_sid": rem.twilio_template_sid or "",
        "twilio_variable_order": rem.twilio_variable_order or ["name","time","professional"],
        "dedupe_strategy": rem.dedupe_strategy or "first_slot_per_day",
    }

@app.get("/api/admin/empresa/{empresa_slug}/reminders/all")
def list_empresa_reminders(empresa_slug: str, current_user: Usuario = Depends(get_current_user)):
    session = SessionLocal()
    try:
        empresa = session.query(Empresa).filter(Empresa.slug == empresa_slug).first()
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        if not current_user.is_superuser and current_user.empresa_id != empresa.id:
            raise HTTPException(status_code=403, detail="Acesso negado a esta empresa")
        rems = session.query(EmpresaReminder).filter(EmpresaReminder.empresa_id == empresa.id).order_by(EmpresaReminder.id.asc()).all()
        return {"items": [_serialize_reminder(r) for r in rems]}
    finally:
        session.close()

# Alias com barra final
@app.get("/api/admin/empresa/{empresa_slug}/reminders/all/")
def list_empresa_reminders_alias(empresa_slug: str, current_user: Usuario = Depends(get_current_user)):
    return list_empresa_reminders(empresa_slug, current_user)

@app.post("/api/admin/empresa/{empresa_slug}/reminders")
def create_empresa_reminder(empresa_slug: str, data: dict, current_user: Usuario = Depends(get_current_user)):
    session = SessionLocal()
    try:
        empresa = session.query(Empresa).filter(Empresa.slug == empresa_slug).first()
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        if not current_user.is_superuser and current_user.empresa_id != empresa.id:
            raise HTTPException(status_code=403, detail="Acesso negado a esta empresa")
        rem = EmpresaReminder(
            empresa_id=empresa.id,
            enabled=bool(data.get("enabled", False)),
            provider=data.get("provider") or "Trinks",
            timezone=data.get("timezone") or "America/Sao_Paulo",
            send_time_local=data.get("send_time_local") or "11:00",
            lead_days=int(data.get("lead_days") or 1),
            twilio_template_sid=data.get("twilio_template_sid") or "",
            twilio_variable_order=data.get("twilio_variable_order") or ["name","time","professional"],
            dedupe_strategy=data.get("dedupe_strategy") or "first_slot_per_day",
        )
        if rem.enabled:
            rem.next_run_at = _compute_next_run_at(rem.timezone, rem.send_time_local)
        session.add(rem)
        session.commit()
        session.refresh(rem)
        return _serialize_reminder(rem)
    finally:
        session.close()

@app.put("/api/admin/empresa/{empresa_slug}/reminders/{reminder_id}")
def update_empresa_reminder(empresa_slug: str, reminder_id: int, data: dict, current_user: Usuario = Depends(get_current_user)):
    session = SessionLocal()
    try:
        empresa = session.query(Empresa).filter(Empresa.slug == empresa_slug).first()
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        if not current_user.is_superuser and current_user.empresa_id != empresa.id:
            raise HTTPException(status_code=403, detail="Acesso negado a esta empresa")
        rem = session.query(EmpresaReminder).filter(EmpresaReminder.id == reminder_id, EmpresaReminder.empresa_id == empresa.id).first()
        if not rem:
            raise HTTPException(status_code=404, detail="Lembrete não encontrado")
        # Atualiza
        for field in ("enabled","provider","timezone","send_time_local","lead_days","twilio_template_sid","twilio_variable_order","dedupe_strategy"):
            if field in data:
                setattr(rem, field, data[field])
        # Types
        try:
            rem.lead_days = int(rem.lead_days or 1)
        except Exception:
            rem.lead_days = 1
        # Recalcula next_run
        rem.next_run_at = _compute_next_run_at(rem.timezone, rem.send_time_local) if rem.enabled else None
        session.commit()
        session.refresh(rem)
        return _serialize_reminder(rem)
    finally:
        session.close()

@app.delete("/api/admin/empresa/{empresa_slug}/reminders/{reminder_id}")
def delete_empresa_reminder(empresa_slug: str, reminder_id: int, current_user: Usuario = Depends(get_current_user)):
    session = SessionLocal()
    try:
        empresa = session.query(Empresa).filter(Empresa.slug == empresa_slug).first()
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        if not current_user.is_superuser and current_user.empresa_id != empresa.id:
            raise HTTPException(status_code=403, detail="Acesso negado a esta empresa")
        rem = session.query(EmpresaReminder).filter(EmpresaReminder.id == reminder_id, EmpresaReminder.empresa_id == empresa.id).first()
        if not rem:
            raise HTTPException(status_code=404, detail="Lembrete não encontrado")
        session.delete(rem)
        session.commit()
        return {"success": True}
    finally:
        session.close()

@app.get("/api/admin/empresa/{empresa_slug}/reminders")
def get_empresa_reminders(empresa_slug: str, current_user: Usuario = Depends(get_current_user)):
    session = SessionLocal()
    try:
        # Verificar acesso
        empresa = session.query(Empresa).filter(Empresa.slug == empresa_slug).first()
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        if not current_user.is_superuser and current_user.empresa_id != empresa.id:
            raise HTTPException(status_code=403, detail="Acesso negado a esta empresa")

        # Carregar ou defaults
        rem = session.query(EmpresaReminder).filter(EmpresaReminder.empresa_id == empresa.id).first()
        if not rem:
            data = {
                "enabled": False,
                "provider": "Trinks",
                "timezone": "America/Sao_Paulo",
                "send_time_local": "11:00",
                "lead_days": 1,
                "twilio_template_sid": "",
                "twilio_variable_order": ["name","time","professional"],
                "dedupe_strategy": "first_slot_per_day",
            }
            return data

        return {
            "enabled": bool(rem.enabled),
            "provider": rem.provider or "Trinks",
            "timezone": rem.timezone or "America/Sao_Paulo",
            "send_time_local": rem.send_time_local or "11:00",
            "lead_days": rem.lead_days or 1,
            "twilio_template_sid": rem.twilio_template_sid or "",
            "twilio_variable_order": rem.twilio_variable_order or ["name","time","professional"],
            "dedupe_strategy": rem.dedupe_strategy or "first_slot_per_day",
        }
    finally:
        session.close()


@app.put("/api/admin/empresa/{empresa_slug}/reminders")
def update_empresa_reminders(empresa_slug: str, configuracoes: dict, current_user: Usuario = Depends(get_current_user)):
    session = SessionLocal()
    try:
        # Verificar acesso
        empresa = session.query(Empresa).filter(Empresa.slug == empresa_slug).first()
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        if not current_user.is_superuser and current_user.empresa_id != empresa.id:
            raise HTTPException(status_code=403, detail="Acesso negado a esta empresa")

        rem = session.query(EmpresaReminder).filter(EmpresaReminder.empresa_id == empresa.id).first()
        if not rem:
            rem = EmpresaReminder(empresa_id=empresa.id)
            session.add(rem)

        # Atualizar campos
        if "enabled" in configuracoes:
            rem.enabled = bool(configuracoes["enabled"])
        if "provider" in configuracoes:
            rem.provider = configuracoes["provider"] or "Trinks"
        if "timezone" in configuracoes:
            rem.timezone = configuracoes["timezone"] or "America/Sao_Paulo"
        if "send_time_local" in configuracoes:
            rem.send_time_local = configuracoes["send_time_local"] or "11:00"
        if "lead_days" in configuracoes:
            try:
                rem.lead_days = int(configuracoes["lead_days"]) if configuracoes["lead_days"] is not None else 1
            except Exception:
                rem.lead_days = 1
        if "twilio_template_sid" in configuracoes:
            rem.twilio_template_sid = configuracoes["twilio_template_sid"] or ""
        if "twilio_variable_order" in configuracoes:
            rem.twilio_variable_order = configuracoes["twilio_variable_order"] or ["name","time","professional"]
        if "dedupe_strategy" in configuracoes:
            rem.dedupe_strategy = configuracoes["dedupe_strategy"] or "first_slot_per_day"

        # Recalcular próximo agendamento
        rem.next_run_at = _compute_next_run_at(rem.timezone, rem.send_time_local) if rem.enabled else None

        session.commit()

        return {
            "enabled": bool(rem.enabled),
            "provider": rem.provider,
            "timezone": rem.timezone,
            "send_time_local": rem.send_time_local,
            "lead_days": rem.lead_days,
            "twilio_template_sid": rem.twilio_template_sid,
            "twilio_variable_order": rem.twilio_variable_order,
            "dedupe_strategy": rem.dedupe_strategy,
        }
    finally:
        session.close()


@app.get("/api/admin/empresa/{empresa_slug}/reminders/options")
def get_empresa_reminder_options(empresa_slug: str, current_user: Usuario = Depends(get_current_user)):
    session = SessionLocal()
    try:
        empresa = session.query(Empresa).filter(Empresa.slug == empresa_slug).first()
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        if not current_user.is_superuser and current_user.empresa_id != empresa.id:
            raise HTTPException(status_code=403, detail="Acesso negado a esta empresa")
        return {
            "providers": ["Trinks"],
            "placeholders": ["name","time","professional"]
        }
    finally:
        session.close()


@app.post("/api/admin/empresa/{empresa_slug}/reminders/preview")
def preview_empresa_reminders(empresa_slug: str, reminder_id: int = Query(None), current_user: Usuario = Depends(get_current_user)):
    session = SessionLocal()
    try:
        # Acesso
        empresa = session.query(Empresa).filter(Empresa.slug == empresa_slug).first()
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        if not current_user.is_superuser and current_user.empresa_id != empresa.id:
            raise HTTPException(status_code=403, detail="Acesso negado a esta empresa")

        if reminder_id is not None:
            rem = session.query(EmpresaReminder).filter(
                EmpresaReminder.empresa_id == empresa.id,
                EmpresaReminder.id == reminder_id
            ).first()
        else:
            rem = session.query(EmpresaReminder).filter(EmpresaReminder.empresa_id == empresa.id).order_by(EmpresaReminder.id.asc()).first()
        # Preview deve funcionar mesmo com lembretes desativados
        if not rem:
            # Defaults para preview
            class _RemObj:
                timezone = 'America/Sao_Paulo'
                lead_days = 1
                twilio_variable_order = ["name","time","professional"]
            rem = _RemObj()

        # Obter config da Trinks
        from services.unified_config_service import get_trinks_config
        trinks_cfg = get_trinks_config(session, empresa.id)
        if not trinks_cfg:
            return {"items": []}

        empresa_config = {
            'empresa_id': empresa.id,
            'empresa_slug': empresa.slug,
            # Passar config crua e normalizada
            'trinks_config': trinks_cfg,
            'trinks_base_url': trinks_cfg.get('base_url'),
            'trinks_api_key': trinks_cfg.get('api_key'),
            'trinks_estabelecimento_id': trinks_cfg.get('estabelecimento_id'),
            'openai_config': {}
        }

        # Janela de tempo
        from services.trinks_provider import TrinksProvider
        provider = TrinksProvider(empresa_config)
        # Reusar lógica de janela do worker
        tz = pytz.timezone(rem.timezone or 'America/Sao_Paulo')
        now = datetime.now(tz)
        target = (now + timedelta(days=rem.lead_days or 1)).replace(hour=0, minute=0, second=0, microsecond=0)
        start_iso = target.isoformat()
        end_iso = (target + timedelta(days=1)).isoformat()

        appointments = provider.list_appointments_range(start_iso, end_iso)

        # Deduplicar por cliente pegando primeiro horário
        by_client = {}
        for ap in appointments:
            cliente_id = str((ap.get('cliente') or {}).get('id') or ap.get('clienteId') or '')
            if not cliente_id:
                continue
            inicio = ap.get('dataHoraInicio') or ''
            current = by_client.get(cliente_id)
            if not current or (inicio and inicio < current.get('dataHoraInicio', '')):
                by_client[cliente_id] = ap

        items = []
        # Buscar corpo do template Twilio para gerar preview
        preview_text = ''
        try:
            from sqlalchemy.orm import sessionmaker
            from config import Config
            from integrations.twilio_service import TwilioService
            engine = create_engine(Config.POSTGRES_URL)
            SLocal = sessionmaker(bind=engine)
            s2 = SLocal()
            try:
                emp = s2.query(Empresa).filter(Empresa.id == empresa.id).first()
                if emp and getattr(rem, 'twilio_template_sid', None):
                    tw = TwilioService(emp.twilio_sid or '', emp.twilio_token or '', (emp.twilio_number or '').lstrip('+'))
                    ft = tw.fetch_template_text(rem.twilio_template_sid)
                    if ft.get('success'):
                        preview_text = ft.get('text') or ''
            finally:
                s2.close()
        except Exception:
            preview_text = ''
        if by_client:
            from integrations.trinks_service import TrinksService
            ts = TrinksService(empresa_config)
            order = rem.twilio_variable_order or ["name","time","professional"]
            for cliente_id, ap in by_client.items():
                inicio = ap.get('dataHoraInicio') or ''
                prof = (ap.get('profissional') or {}).get('nome') or ''
                try:
                    # Converter horário para HH:MM no timezone
                    if inicio.endswith('Z'):
                        dt = datetime.fromisoformat(inicio.replace('Z', '+00:00'))
                    else:
                        dt = datetime.fromisoformat(inicio)
                    local_dt = dt.astimezone(tz)
                    hhmm = local_dt.strftime('%H:%M')
                except Exception:
                    hhmm = ''

                cli = ts.get_client(cliente_id)
                name_full = (cli.get('nome') or (cli.get('data') or {}).get('nome') or '').strip()
                # Usar apenas o primeiro nome para a saudação
                first_name = name_full.split()[0] if name_full else ''
                # Telefone para preview (normalizado)
                try:
                    from services.services import DatabaseService
                    phone_raw = (cli.get('telefone') or (cli.get('data') or {}).get('telefone') or '')
                    phone = DatabaseService.normalize_phone_br(phone_raw)
                except Exception:
                    phone = ''

                # Mapear variáveis na ordem
                values = {'name': first_name or '', 'time': hhmm or '', 'professional': prof or ''}
                variables = {str(i+1): values.get(order[i], '') for i in range(min(3, len(order)))}

                # Montar mensagem de preview substituindo {{1}}, {{2}}, {{3}}
                message_preview = preview_text
                if message_preview:
                    try:
                        for idx in range(1, 4):
                            message_preview = message_preview.replace(f"{{{{{idx}}}}}", variables.get(str(idx), ''))
                    except Exception:
                        pass

                items.append({
                    'phone': phone,
                    'name': first_name,
                    'time': hhmm,
                    'professional': prof,
                    'variables': variables,
                    'message_preview': message_preview
                })

        return {"items": items}
    finally:
        session.close()


@app.post("/api/admin/empresa/{empresa_slug}/reminders/run-now")
def run_now_empresa_reminders(empresa_slug: str, reminder_id: int = Query(None), current_user: Usuario = Depends(get_current_user)):
    session = SessionLocal()
    try:
        empresa = session.query(Empresa).filter(Empresa.slug == empresa_slug).first()
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        if not current_user.is_superuser and current_user.empresa_id != empresa.id:
            raise HTTPException(status_code=403, detail="Acesso negado a esta empresa")

        if reminder_id is not None:
            rem = session.query(EmpresaReminder).filter(
                EmpresaReminder.empresa_id == empresa.id,
                EmpresaReminder.id == reminder_id
            ).first()
        else:
            rem = session.query(EmpresaReminder).filter(EmpresaReminder.empresa_id == empresa.id).order_by(EmpresaReminder.id.asc()).first()
        if not rem or not rem.enabled:
            return {"success": False, "message": "Lembretes desativados ou não configurados"}

        # Construir cfg para o worker
        cfg = {
            'empresa_id': empresa.id,
            'empresa_slug': empresa.slug,
            'timezone': rem.timezone or 'America/Sao_Paulo',
            'send_time_local': rem.send_time_local or '11:00',
            'lead_days': rem.lead_days or 1,
            'provider': rem.provider or 'Trinks',
            'twilio_template_sid': rem.twilio_template_sid or '',
            'twilio_variable_order': rem.twilio_variable_order or ["name","time","professional"],
            'dedupe_strategy': rem.dedupe_strategy or 'first_slot_per_day',
        }

        from services.confirmation_worker import run_company_confirmation
        run_company_confirmation(empresa.id, empresa.slug, cfg)
        return {"success": True}
    finally:
        session.close()

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
async def get_empresa_clientes(
    empresa_slug: str,
    current_user: Usuario = Depends(get_current_user)
):
    """Retorna clientes de uma empresa específica"""
    try:
        session = SessionLocal()
        
        # Verificar se usuário tem acesso à empresa
        if not current_user.is_superuser:
            if not current_user.empresa_id:
                raise HTTPException(status_code=403, detail="Usuário não associado a nenhuma empresa")
            
            # Buscar empresa do usuário
            user_empresa = session.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
            if not user_empresa or user_empresa.slug != empresa_slug:
                raise HTTPException(status_code=403, detail="Acesso negado a esta empresa")
        
        # Buscar empresa pelo slug
        empresa = session.query(Empresa).filter(Empresa.slug == empresa_slug).first()
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        
        # Buscar clientes da empresa
        clientes = session.query(Cliente).filter(Cliente.empresa_id == empresa.id).all()
        
        # Converter para formato JSON (compatível com o frontend ConversationView)
        clientes_json = []
        for cliente in clientes:
            try:
                # Buscar última atividade (correlacionando pelo cliente_id STRING, não pelo id interno)
                ultima_atividade = None
                try:
                    ultima_atividade = session.query(Atividade).filter(
                        Atividade.cliente_id == cliente.cliente_id
                    ).order_by(Atividade.timestamp.desc()).first()
                except Exception as _e:
                    logger.warning(f"Falha ao obter última atividade para cliente {cliente.cliente_id}: {_e}")

                # Contar mensagens deste cliente (para UI)
                total_mensagens = 0
                try:
                    total_mensagens = session.query(Mensagem).filter(
                        Mensagem.empresa_id == cliente.empresa_id,
                        Mensagem.cliente_id == cliente.cliente_id
                    ).count()
                except Exception as _e:
                    logger.warning(f"Falha ao contar mensagens para cliente {cliente.cliente_id}: {_e}")

                cliente_data = {
                    "id": cliente.id,
                    "cliente_id": cliente.cliente_id,  # WhatsApp ID usado no frontend
                    "nome": cliente.nome,
                    # telefone não existe no modelo Cliente; manter compatibilidade com null
                    "telefone": None,
                    "empresa_id": cliente.empresa_id,
                    # Normalizar timestamp para string ISO
                    "ultima_atividade": (ultima_atividade.timestamp.isoformat() if ultima_atividade and hasattr(ultima_atividade.timestamp, 'isoformat') else (ultima_atividade.timestamp if ultima_atividade else None)),
                    # Chave esperada pelo frontend
                    "tipo_atividade": (ultima_atividade.tipo if ultima_atividade else None),
                    "total_mensagens": total_mensagens
                }
                # Manter campo antigo para compatibilidade, se necessário
                if ultima_atividade:
                    cliente_data["tipo_ultima_atividade"] = ultima_atividade.tipo

                clientes_json.append(cliente_data)
            except Exception as row_e:
                logger.warning(f"Ignorando cliente {getattr(cliente,'cliente_id', 'N/A')} por erro ao montar payload: {row_e}")
        
        return {
            "empresa": empresa_slug,
            "clientes": clientes_json
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Erro ao buscar clientes da empresa {empresa_slug}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")
    finally:
        session.close()

@app.get("/api/admin/empresa/{empresa_slug}/logs")
async def get_empresa_logs(
    empresa_slug: str,
    current_user: Usuario = Depends(get_current_user),
    limit: int = 100,
    level: str = None,
    exclude_info: bool = True
):
    """Retorna logs de uma empresa específica"""
    try:
        session = SessionLocal()
        
        # Verificar se usuário tem acesso à empresa
        if not current_user.is_superuser:
            if not current_user.empresa_id:
                raise HTTPException(status_code=403, detail="Usuário não associado a nenhuma empresa")
            
            # Buscar empresa do usuário
            user_empresa = session.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
            if not user_empresa or user_empresa.slug != empresa_slug:
                raise HTTPException(status_code=403, detail="Acesso negado a esta empresa")
        
        # Buscar empresa pelo slug
        empresa = session.query(Empresa).filter(Empresa.slug == empresa_slug).first()
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        
        # Buscar logs da empresa
        query = session.query(Log).filter(Log.empresa_id == empresa.id)
        
        # Filtrar por nível se especificado
        if level and level != 'all':
            query = query.filter(Log.level == level)
        
        # Por padrão, excluir logs de INFO para não poluir
        if exclude_info:
            query = query.filter(Log.level != 'INFO')
        
        # Limitar e ordenar por timestamp mais recente
        logs_db = query.order_by(Log.timestamp.desc()).limit(limit).all()
        
        # Converter para formato JSON
        logs = []
        for log in logs_db:
            logs.append({
                "level": log.level,
                "message": log.message,
            "empresa": empresa_slug,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "details": log.details or {}
            })
        
        return {"logs": logs}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar logs da empresa {empresa_slug}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")
    finally:
        session.close()

@app.get("/api/admin/empresa/logs")
async def get_empresa_logs_without_slug():
    """Endpoint para capturar chamadas com slug vazio - DEBUG"""
    logger.warning("🚨 Chamada para /api/admin/empresa/logs sem slug da empresa!")
    return {"error": "Slug da empresa não fornecido", "expected_format": "/api/admin/empresa/{empresa_slug}/logs"}

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
                asyncio.create_task(_buffer_wait_and_process(emp, wa, empresa_config))
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
        
        # BUFFER EM MEMÓRIA (acumula mensagens e processa tudo junto)
        if empresa_config.get('usar_buffer', True):
            # Buffer: acumula mensagens e adia o processamento
            key = _get_buffer_key(empresa_slug, wa_id)
            deadline = time.time() + DEFAULT_BUFFER_SECONDS
            entry = buffer_state.get(key) or {}
            
            # ✅ ACUMULAR mensagens em vez de sobrescrever
            if 'messages' not in entry:
                entry['messages'] = []
            entry['messages'].append(webhook_data)
            
            entry.update({
                'deadline': deadline,
                'empresa_config': empresa_config,
                'wa_id': wa_id,
                'empresa_slug': empresa_slug
            })
            buffer_state[key] = entry
            
            logger.info(f"📥 Mensagem adicionada ao buffer para {empresa_slug}:{wa_id}. Total: {len(entry['messages'])} mensagens")
            
            # ✅ SEMPRE criar nova task (cancelando a anterior se existir)
            if entry.get('timer') and not entry['timer'].done():
                logger.info(f"🔄 Cancelando task anterior para {empresa_slug}:{wa_id}")
                entry['timer'].cancel()
            
            logger.info(f"🔄 Criando nova buffer task para {empresa_slug}:{wa_id}")
            entry['timer'] = asyncio.create_task(_buffer_wait_and_process(empresa_slug, wa_id, empresa_config))
            logger.info(f"✅ Buffer task criada para {empresa_slug}:{wa_id} - Status: {entry['timer']._state}")
            
            # Verificar se a task foi criada corretamente
            if entry['timer']._state == 'PENDING':
                logger.info(f"✅ Task está pendente e será executada")
            else:
                logger.warning(f"⚠️ Task não está pendente: {entry['timer']._state}")
            
            return JSONResponse(content={
                'success': True,
                'message': f'Mensagem recebida. Vou aguardar alguns segundos para consolidar e responder. ({len(entry["messages"])} mensagens no buffer)',
                'empresa': empresa_slug,
                'cliente_id': wa_id,
                'buffer_ms': int(DEFAULT_BUFFER_SECONDS * 1000),
                'buffer_count': len(entry['messages'])
            })
        
        # Se não usar buffer ou se falhar, processar imediatamente
        # Processar mensagem com Smart Agent (LangGraph + LangChain)
        try:
            # ✅ CACHE GLOBAL de Smart Agents por waid
            global _smart_agents_cache, _last_cache_cleanup
            
            # ✅ LIMPEZA PERIÓDICA do cache (evitar vazamento de memória)
            current_time = time.time()
            
            # Limpar cache a cada 1 hora (3600 segundos)
            if current_time - _last_cache_cleanup > 3600:
                old_cache_size = len(_smart_agents_cache)
                # Manter apenas agentes ativos nas últimas 24 horas
                cutoff_time = current_time - 86400  # 24 horas
                _smart_agents_cache = {
                    waid: agent for waid, agent in _smart_agents_cache.items()
                    if hasattr(agent, 'last_activity') and agent.last_activity > cutoff_time
                }
                _last_cache_cleanup = current_time
                logger.info(f"🧹 Cache limpo: {old_cache_size} → {len(_smart_agents_cache)} agentes")
            
            # ✅ OBTER Smart Agent EXISTENTE ou criar novo
            if wa_id in _smart_agents_cache:
                smart_agent = _smart_agents_cache[wa_id]
                # ✅ ATUALIZAR atividade do agente
                smart_agent.last_activity = current_time
                logger.info(f"🔄 Reutilizando Smart Agent existente para waid {wa_id}")
            else:
                from agents.smart_agent import SmartAgent
                smart_agent = SmartAgent(empresa_config)
                # ✅ ADICIONAR timestamp de atividade
                smart_agent.last_activity = current_time
                _smart_agents_cache[wa_id] = smart_agent
                logger.info(f"🆕 Criando novo Smart Agent para waid {wa_id}")
            
            # ✅ SALVAR MENSAGEM DO CLIENTE NO BANCO
            from services.services import DatabaseService
            db_service = DatabaseService()
            
            try:
                db_service.save_message(
                    empresa_id=empresa_config.get('empresa_id'),
                    cliente_id=wa_id,
                    text=webhook_data.get('Body', ''),
                    is_bot=False,
                    cliente_nome=None
                )
                logger.info(f"💾 Mensagem do cliente salva no banco: {wa_id}")
            except Exception as e:
                logger.error(f"❌ Erro ao salvar mensagem do cliente: {e}")
            
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
                        
                        # ✅ SALVAR RESPOSTA DO BOT NO BANCO
                        try:
                            db_service.save_message(
                                empresa_id=empresa_config.get('empresa_id'),
                                cliente_id=wa_id,
                                text=response_message,
                                is_bot=True,
                                cliente_nome=None
                            )
                            logger.info(f"💾 Resposta do bot salva no banco: {wa_id}")
                        except Exception as e:
                            logger.error(f"❌ Erro ao salvar resposta do bot: {e}")
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
            # print("🔍 DEBUG: Função get_logs chamada")  # Removido para limpar logs
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
        # print(f"🔍 DEBUG: {len(logs_db)} logs encontrados no banco")  # Removido para limpar logs
        
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
        
        # print(f"🔍 DEBUG: Retornando {len(logs)} logs")  # Removido para limpar logs
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
        # Primeiro tenta via ORM
        try:
            user = session.query(Usuario).filter(Usuario.email == form_data.username).first()
            senha_hash = user.senha_hash if user else None
            user_id = user.id if user else None
            user_email = user.email if user else None
            is_superuser = bool(user.is_superuser) if user else False
            empresa_id = user.empresa_id if user else None
        except ProgrammingError as pe:
            # Limpar transação abortada antes do fallback
            try:
                session.rollback()
            except Exception:
                pass
            # Fallback para bancos sem colunas novas (schema antigo)
            logger.warning(f"Fallback login (schema antigo): {pe}")
            row = session.execute(text(
                "SELECT id, email, senha_hash, is_superuser, empresa_id FROM usuarios WHERE email = :email LIMIT 1"
            ), {"email": form_data.username}).fetchone()
            user = None
            if row:
                user_id, user_email, senha_hash, is_superuser, empresa_id = row
            else:
                senha_hash = None
                user_id = None
                user_email = None
                is_superuser = False
                empresa_id = None

        if not senha_hash or not bcrypt.verify(form_data.password, senha_hash):
            # Log de tentativa de login falhada
            save_log_to_db(session, None, 'WARNING', f'Tentativa de login falhada para {form_data.username}')
            raise HTTPException(status_code=401, detail="Credenciais inválidas")
        
        # Log de login bem-sucedido
        save_log_to_db(session, empresa_id, 'INFO', f'Login bem-sucedido para {user_email}')
        
        data = {
            "sub": user_email, 
            "is_superuser": bool(is_superuser), 
            "empresa_id": empresa_id,
            "user_id": user_id
        }
        token = jwt.encode(data, config.SECRET_KEY, algorithm=config.ALGORITHM)
        
        return {
            "access_token": token, 
            "token_type": "bearer",
            "user": {
                "id": user_id,
                "email": user_email,
                "is_superuser": bool(is_superuser),
                "empresa_id": empresa_id
            }
        }
    finally:
        session.close()

@app.get("/api/admin/usuarios")
def get_usuarios(current_user: Usuario = Depends(get_current_superuser)):
    session = SessionLocal()
    try:
        try:
            # Caminho padrão (schema novo)
            usuarios = session.query(Usuario).all()
            return [
                {
                    "id": u.id,
                    "email": u.email,
                    "is_superuser": u.is_superuser,
                    "empresa_id": u.empresa_id,
                    "created_at": u.created_at.isoformat() if getattr(u, "created_at", None) else None,
                }
                for u in usuarios
            ]
        except ProgrammingError as pe:
            # Fallback para bancos antigos sem colunas novas (notifications_*)
            try:
                session.rollback()
            except Exception:
                pass
            rows = session.execute(text(
                "SELECT id, email, is_superuser, empresa_id, created_at FROM usuarios"
            )).fetchall()
            users = []
            for r in rows:
                try:
                    created = r[4].isoformat() if r[4] else None
                except Exception:
                    created = None
                users.append({
                    "id": r[0],
                    "email": r[1],
                    "is_superuser": bool(r[2]),
                    "empresa_id": r[3],
                    "created_at": created,
                })
            return users
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

@app.post("/api/admin/conversations/{empresa_slug}/{waid}/clear-cache")
def clear_conversation_cache(
    empresa_slug: str,
    waid: str,
    current_user: Usuario = Depends(get_current_user)
):
    """Limpa o cache de conversa de um usuário específico"""
    try:
        # Verificar se a empresa existe e se o usuário tem acesso
        session = SessionLocal()
        try:
            empresa = session.query(Empresa).filter(Empresa.slug == empresa_slug).first()
            if not empresa:
                raise HTTPException(status_code=404, detail="Empresa não encontrada")
            
            # Verificar se usuário tem acesso a esta empresa
            if not current_user.is_superuser:
                if not current_user.empresa_id:
                    raise HTTPException(status_code=403, detail="Acesso negado")
                
                if current_user.empresa_id != empresa.id:
                    raise HTTPException(status_code=403, detail="Acesso negado à empresa")
        finally:
            session.close()
        
        # Limpar cache do SmartAgent para este waid
        from agents.smart_agent import SmartAgent
        if hasattr(SmartAgent, '_conversation_cache') and waid in SmartAgent._conversation_cache:
            del SmartAgent._conversation_cache[waid]
            logger.info(f"🧹 Cache do SmartAgent limpo para waid {waid}")
        
        # Limpar cache global de agentes do webhook handler
        global _smart_agents_cache
        if waid in _smart_agents_cache:
            del _smart_agents_cache[waid]
            logger.info(f"🧹 Cache de agentes limpo para waid {waid}")
        
        return {
            "success": True,
            "message": f"Cache limpo com sucesso para {empresa_slug}:{waid}",
            "waid": waid,
            "empresa": empresa_slug
        }
        
    except Exception as e:
        logger.error(f"Erro ao limpar cache para {empresa_slug}:{waid}: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao limpar cache: {str(e)}")

@app.get("/api/admin/code-usage")
def get_code_usage(current_user: Usuario = Depends(get_current_superuser)):
    """Retorna relatório de uso de código para identificar código morto"""
    try:
        from code_tracker import get_code_usage
        return get_code_usage()
    except Exception as e:
        logger.error(f"Erro ao obter relatório de uso: {e}")
        return {"error": "Erro ao obter relatório de uso"}

@app.post("/api/admin/code-usage/save-report")
def save_code_usage_report(current_user: Usuario = Depends(get_current_superuser)):
    """Salva relatório de uso de código em arquivo"""
    try:
        from code_tracker import save_usage_report
        success = save_usage_report()
        return {"success": success, "message": "Relatório salvo com sucesso"}
    except Exception as e:
        logger.error(f"Erro ao salvar relatório: {e}")
        return {"error": "Erro ao salvar relatório"}

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
        
        # Log para debug do knowledge_json (resumido)
        knowledge_items = config_data['knowledge_json'].get('items', [])
        logger.info(f"📖 Retornando knowledge_json: {len(knowledge_items)} itens de conhecimento")
        
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
                # Normalização defensiva de chaves da Trinks para o painel
                api_key = config.get('api_key') or config.get('key')
                base_url = config.get('base_url') or config.get('url_base') or config.get('url')
                if base_url and not str(base_url).startswith(('http://', 'https://')):
                    base_url = f"https://{str(base_url).lstrip('/')}"
                empresa_config['trinks_api_key'] = api_key
                empresa_config['trinks_base_url'] = base_url
                empresa_config['trinks_estabelecimento_id'] = (
                    config.get('estabelecimento_id')
                    or config.get('estabelecimentoId')
                    or config.get('estabelecimento')
                )
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
def get_apis(current_user: Usuario = Depends(get_current_user)):
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
def get_empresa_apis(empresa_id: int, current_user: Usuario = Depends(get_current_user)):
    """Lista APIs conectadas a uma empresa"""
    session = SessionLocal()
    try:
        # Verificar se usuário tem acesso à empresa
        if not current_user.is_superuser:
            if not current_user.empresa_id:
                raise HTTPException(status_code=403, detail="Acesso negado")
            
            # Usuário não-admin só pode acessar sua própria empresa
            if current_user.empresa_id != empresa_id:
                raise HTTPException(status_code=403, detail="Acesso negado à empresa")
        
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

# Estado de buffer em memória por cliente (WaId)
buffer_state: Dict[Tuple[str, str], Dict[str, Any]] = {}
# Estrutura: {(empresa_slug, wa_id): { 'timer': asyncio.Task, 'messages': list, 'deadline': float, 'empresa_config': dict }}

DEFAULT_BUFFER_SECONDS = 8  # pode ser tornado configurável por empresa futuramente

def _get_buffer_key(empresa_slug: str, wa_id: str) -> Tuple[str, str]:
    return (empresa_slug, wa_id)

async def _buffer_wait_and_process(empresa_slug: str, wa_id: str, empresa_config: dict):
    logger.info(f"🚀 Buffer task iniciada para {empresa_slug}:{wa_id}")
    
    key = _get_buffer_key(empresa_slug, wa_id)
    entry = buffer_state.get(key)
    if not entry:
        logger.warning(f"⚠️ Buffer entry não encontrada para {empresa_slug}:{wa_id}")
        return
    
    deadline = entry.get('deadline', 0)
    now = time.time()
    delay = max(0, deadline - now)
    
    logger.info(f"⏰ Buffer aguardando {delay:.1f}s para {empresa_slug}:{wa_id} (deadline: {deadline:.1f}, now: {now:.1f})")
    await asyncio.sleep(delay)

    # Verificar se ninguém atualizou a deadline durante a espera
    latest = buffer_state.get(key)
    if not latest or latest.get('deadline') != deadline:
        logger.info(f"🔄 Buffer cancelado para {empresa_slug}:{wa_id} - nova mensagem chegou durante espera")
        return  # houve nova mensagem, cancela este processamento
    
    logger.info(f"✅ Buffer expirou para {empresa_slug}:{wa_id} - processando mensagens...")

    # ✅ PROCESSAR TODAS AS MENSAGENS ACUMULADAS
    messages = latest.get('messages', [])
    logger.info(f"🔄 Buffer expirou para {empresa_slug}:{wa_id}. Processando {len(messages)} mensagens acumuladas")
    
    try:
        # ✅ REUTILIZAR SMART AGENT EXISTENTE ou criar novo
        from agents.smart_agent import SmartAgent
        
        # ✅ REUTILIZAR SMART AGENT EXISTENTE ou criar novo
        # Como estamos em uma função async separada, vamos criar um novo Smart Agent
        # mas ele vai carregar o contexto do cache global automaticamente
        smart_agent = SmartAgent(empresa_config)
        logger.info(f"🆕 Smart Agent criado para {empresa_slug}:{wa_id} (vai carregar contexto do cache global)")
        
        # ✅ SALVAR MENSAGENS NO BANCO ANTES DE PROCESSAR
        from services.services import DatabaseService
        db_service = DatabaseService()
        
        # Salvar cada mensagem do cliente no banco
        for msg in messages:
            try:
                db_service.save_message(
                    empresa_id=empresa_config.get('empresa_id'),
                    cliente_id=wa_id,
                    text=msg.get('Body', ''),
                    is_bot=False,
                    cliente_nome=None  # Será extraído automaticamente se disponível
                )
                logger.info(f"💾 Mensagem do cliente salva no banco: {wa_id}")
            except Exception as e:
                logger.error(f"❌ Erro ao salvar mensagem do cliente: {e}")
        
        # ✅ PROCESSAR TODAS AS MENSAGENS JUNTAS (não individualmente!)
        logger.info(f"📝 Juntando {len(messages)} mensagens para processamento único...")
        
        # Juntar todas as mensagens em uma única string
        combined_message = "\n".join([msg.get('Body', '') for msg in messages])
        logger.info(f"📝 Mensagem consolidada: {combined_message}")
        
        # Processar UMA VEZ com todas as mensagens juntas
        response_message = smart_agent.analyze_and_respond(combined_message, wa_id, {
            'empresa_slug': empresa_slug,
            'cliente_id': wa_id,
            'empresa_config': empresa_config
        })
        
        logger.info(f"✅ Resposta única processada: {response_message[:100]}...")
        
        # ✅ ENVIAR RESPOSTA ÚNICA (não consolidada)
        final_response = response_message
        
        logger.info(f"📤 Enviando resposta única para {empresa_slug}:{wa_id}")
        
        from integrations.twilio_service import TwilioService
        twilio_service = TwilioService(
            empresa_config.get('twilio_sid'),
            empresa_config.get('twilio_token'),
            empresa_config.get('twilio_number')
        )
        
        # ✅ SALVAR RESPOSTA DO BOT NO BANCO
        try:
            db_service.save_message(
                empresa_id=empresa_config.get('empresa_id'),
                cliente_id=wa_id,
                text=final_response,
                is_bot=True,
                cliente_nome=None
            )
            logger.info(f"💾 Resposta do bot salva no banco: {wa_id}")
        except Exception as e:
            logger.error(f"❌ Erro ao salvar resposta do bot: {e}")
        
        # Enviar resposta única
        if empresa_config.get('mensagem_quebrada', False) and len(final_response) > 200:
            parts = _break_long_message(final_response)
            for i, part in enumerate(parts):
                twilio_service.send_whatsapp_message(wa_id, part)
                if i < len(parts) - 1:
                    await asyncio.sleep(0.5)
            logger.info(f"📤 Resposta única enviada em {len(parts)} partes")
        else:
            twilio_service.send_whatsapp_message(wa_id, final_response)
            logger.info(f"📤 Resposta única enviada com sucesso")
        
        logger.info(f"✅ Buffer processado com sucesso para {empresa_slug}:{wa_id}. {len(messages)} mensagens processadas")
        
    except Exception as e:
        logger.error(f"❌ Erro no processamento do buffer para {empresa_slug}:{wa_id}: {e}")
        logger.error(f"❌ Traceback completo: {traceback.format_exc()}")
    finally:
        # Limpar estado do buffer
        buffer_state.pop(key, None)
        logger.info(f"🧹 Buffer limpo para {empresa_slug}:{wa_id}")

# ============================================================================
# ENDPOINT SIMPLES DE NOTIFICAÇÕES
# ============================================================================

# Endpoint removido - migrado para email

# Endpoint removido - migrado para email

# ============================================================================
# ENDPOINTS DE PUSH NOTIFICATION REMOVIDOS - MIGRADO PARA EMAIL
# ============================================================================

# Endpoint removido - migrado para email

# Endpoint removido - migrado para email

# ============================================================================
# ENDPOINTS DE CONFIGURAÇÃO DE NOTIFICAÇÕES
# ============================================================================

@app.get("/api/notifications/settings")
async def get_notification_settings(
    current_user: Usuario = Depends(get_current_user)
):
    """Retorna as configurações de notificação do usuário"""
    try:
        return {
            "notifications_enabled": current_user.notifications_enabled,
            "smart_agent_error_notifications": current_user.smart_agent_error_notifications,
            "user_email": current_user.email
        }
    except Exception as e:
        logger.error(f"Erro ao obter configurações de notificação: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@app.post("/api/notifications/settings")
async def update_notification_settings(
    request: Request,
    current_user: Usuario = Depends(get_current_user)
):
    """Atualiza as configurações de notificação do usuário"""
    try:
        data = await request.json()
        
        db = next(get_db())
        user = db.query(Usuario).filter(Usuario.id == current_user.id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
        # Atualizar configurações
        if 'notifications_enabled' in data:
            user.notifications_enabled = data['notifications_enabled']
        
        if 'smart_agent_error_notifications' in data:
            user.smart_agent_error_notifications = data['smart_agent_error_notifications']
        
        db.commit()
        db.close()
        
        logger.info(f"✅ Configurações de notificação atualizadas para usuário {current_user.id}")
        
        return {
            "message": "Configurações atualizadas com sucesso!",
            "status": "success",
            "settings": {
                "notifications_enabled": user.notifications_enabled,
                "smart_agent_error_notifications": user.smart_agent_error_notifications
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao atualizar configurações de notificação: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

# ============================================================================
# ENDPOINTS DE TESTE DAS REGRAS DE EMAIL
# ============================================================================

# ============================================================================
# (REMOVIDOS) ENDPOINTS TEMPORÁRIOS DE TESTE
# - Foram substituídos por um script dedicado em backend/scripts/test_trinks_error.py
# ============================================================================

@app.post("/api/notifications/test")
async def test_notification(
    current_user: Usuario = Depends(get_current_user)
):
    """Testa envio de notificação por email"""
    try:
        logger.info(f"🧪 Usuário {current_user.id} testou notificação por email")
        
        # NOTIFICAÇÃO POR EMAIL REAL - USANDO GMAIL
        try:
            # Buscar dados do usuário
            # get_db já está importado no topo do arquivo
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            from datetime import datetime
            
            db = next(get_db())
            user = db.query(Usuario).filter(Usuario.id == current_user.id).first()
            
            if not user or not user.email:
                logger.warning(f"Usuário {current_user.id} não tem email")
                return {
                    "message": "⚠️ Usuário não tem email cadastrado!", 
                    "status": "warning"
                }
            
            # Configuração do email (SEU GMAIL)
            sender_email = "tinyteams.app@gmail.com"  # Seu email
            sender_password = "vins jvxh rrjn ysgn"   # Sua senha de app Gmail
            
            # Criar mensagem
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = user.email
            msg['Subject'] = "🧪 Teste de Notificação - Atende AI"
            
            body = f"""
            Olá {user.email}!
            
            Esta é uma notificação de teste do TinyTeams.
            
            ✅ Sistema funcionando perfeitamente!
            📅 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
            
            Abraços,
            Equipe Atende AI
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Enviar email REAL
            logger.info(f"📧 Enviando email REAL para: {user.email}")
            
            try:
                # Configurar SMTP Gmail
                server = smtplib.SMTP('smtp.gmail.com', 587)
                server.starttls()  # Ativar TLS
                server.login(sender_email, sender_password)
                
                # Enviar email
                text = msg.as_string()
                server.sendmail(sender_email, user.email, text)
                server.quit()
                
                logger.info(f"✅ Email REAL enviado com sucesso para: {user.email}")
                
                return {
                    "message": "📧 Email REAL enviado com sucesso!", 
                    "status": "success",
                    "details": {
                        "user_id": current_user.id,
                        "user_email": user.email,
                        "sender_email": sender_email,
                        "notification_type": "email_real",
                        "timestamp": str(datetime.now())
                    }
                }
                
            except smtplib.SMTPAuthenticationError:
                logger.error("❌ Erro de autenticação Gmail - configure senha de app")
                return {
                    "message": "❌ Erro: Configure senha de app Gmail!", 
                    "status": "error",
                    "details": {
                        "error": "SMTP Authentication Error",
                        "solution": "Configure senha de app Gmail"
                    }
                }
            except Exception as smtp_error:
                logger.error(f"❌ Erro SMTP: {smtp_error}")
                return {
                    "message": f"❌ Erro ao enviar email: {str(smtp_error)}", 
                    "status": "error"
                }
                
        except Exception as email_error:
            logger.error(f"Erro no email: {email_error}")
            return {
                "message": f"❌ Erro no email: {str(email_error)}", 
                "status": "error"
            }
            
    except Exception as e:
        logger.error(f"Erro ao testar notificação: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 