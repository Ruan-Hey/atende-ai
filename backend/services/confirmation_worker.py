from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import pytz

from services.services import DatabaseService
from services.smart_agent_bridge import SmartAgentBridge
from services.unified_config_service import get_trinks_config
from services.trinks_provider import TrinksProvider
from integrations.twilio_service import TwilioService


def _build_time_window(timezone_str: str, lead_days: int) -> (str, str, str):
    tz = pytz.timezone(timezone_str or 'America/Sao_Paulo')
    now = datetime.now(tz)
    target = (now + timedelta(days=lead_days)).replace(hour=0, minute=0, second=0, microsecond=0)
    start = target
    end = start + timedelta(days=1)
    return start.isoformat(), end.isoformat(), target.strftime('%Y-%m-%d')


def _format_time_hhmm(iso_dt: str, timezone_str: str) -> str:
    tz = pytz.timezone(timezone_str or 'America/Sao_Paulo')
    try:
        # Tratar possíveis formatos com Z
        if iso_dt.endswith('Z'):
            dt = datetime.fromisoformat(iso_dt.replace('Z', '+00:00'))
        else:
            dt = datetime.fromisoformat(iso_dt)
        local_dt = dt.astimezone(tz)
        return local_dt.strftime('%H:%M')
    except Exception:
        return ''


def _map_variables(order: List[str], name: str, time_hhmm: str, professional: str) -> Dict[str, str]:
    # Twilio ContentVariables aceita JSON com chaves; mapeamos por nome ou por posição "1","2","3"
    mapping = {}
    values = {
        'name': name or '',
        'time': time_hhmm or '',
        'professional': professional or ''
    }
    for idx, key in enumerate(order, start=1):
        val = values.get(key, '')
        # Suportar ordem posicional "1","2","3"
        mapping[str(idx)] = val
        mapping[key] = val
    # Preferência: apenas chaves posicionais, pois você mencionou ordem (1,2,3)
    return {str(i+1): values.get(order[i], '') for i in range(min(3, len(order)))}


def run_company_confirmation(empresa_id: int, empresa_slug: str, cfg: Dict[str, Any]) -> None:
    db = DatabaseService()
    # Obter config da Trinks
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from config import Config
    engine = create_engine(Config.POSTGRES_URL)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        trinks_cfg = get_trinks_config(session, empresa_id)
    finally:
        session.close()
    if not trinks_cfg:
        return

    empresa_config = {
        'empresa_id': empresa_id,
        'empresa_slug': empresa_slug,
        'trinks_base_url': trinks_cfg.get('base_url'),
        'trinks_api_key': trinks_cfg.get('api_key'),
        'trinks_estabelecimento_id': trinks_cfg.get('estabelecimento_id'),
        'openai_config': {}
    }

    provider = TrinksProvider(empresa_config)
    start_iso, end_iso, exec_date = _build_time_window(cfg.get('timezone'), cfg.get('lead_days', 1))
    appointments = provider.list_appointments_range(start_iso, end_iso)

    # Deduplicar por cliente pegando primeiro horário
    by_client: Dict[str, Dict[str, Any]] = {}
    for ap in appointments:
        cliente_id = str((ap.get('cliente') or {}).get('id') or ap.get('clienteId') or '')
        if not cliente_id:
            continue
        inicio = ap.get('dataHoraInicio') or ''
        if cliente_id not in by_client or (inicio and inicio < by_client[cliente_id].get('dataHoraInicio', '')):
            by_client[cliente_id] = ap

    if not by_client:
        return

    # Twilio service
    from models import Empresa
    engine = create_engine(Config.POSTGRES_URL)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        empresa = session.query(Empresa).filter(Empresa.id == empresa_id).first()
        if not empresa:
            return
        twilio_sid = empresa.twilio_sid or ''
        twilio_token = empresa.twilio_token or ''
        twilio_from = (empresa.twilio_number or '').lstrip('+')
    finally:
        session.close()

    twilio = TwilioService(twilio_sid, twilio_token, twilio_from)

    # Bridge para semear SmartAgent
    bridge = SmartAgentBridge(empresa_id, empresa_config)

    # Variáveis e envio
    order = cfg.get('twilio_variable_order') or ["name","time","professional"]
    template_sid = cfg.get('twilio_template_sid')

    for cliente_id, ap in by_client.items():
        inicio = ap.get('dataHoraInicio') or ''
        time_hhmm = _format_time_hhmm(inicio, cfg.get('timezone'))
        profissional = (ap.get('profissional') or {}).get('nome') or ''
        professional_id = (ap.get('profissional') or {}).get('id') or ''
        appointment_id = str(ap.get('id') or '')

        # Buscar detalhes do cliente (telefone e nome)
        from integrations.trinks_service import TrinksService
        ts = TrinksService(empresa_config)
        cli = ts.get_client(cliente_id)
        name = (cli.get('nome') or (cli.get('data') or {}).get('nome') or '').strip()
        phone_raw = (cli.get('telefone') or (cli.get('data') or {}).get('telefone') or '')
        phone = db.normalize_phone_br(phone_raw)
        if not phone:
            continue

        variables = _map_variables(order, name, time_hhmm, profissional)

        # Idempotência
        existing = db.record_notification(
            empresa_id,
            'confirmacao',
            appointment_id,
            exec_date,
            phone,
            variables,
            None,
            None
        )
        if not existing:
            # já enviado
            continue

        # Mensagem do bot (para histórico)
        bot_message = f"Olá {name}, confirmando seu horário de amanhã às {time_hhmm} com {profissional}. Responda 1 para confirmar, 2 para cancelar, 3 para remarcar."
        extracted = {
            'appointment_id': appointment_id,
            'data': exec_date,
            'horario': time_hhmm,
            'profissional': profissional,
            'profissional_id': professional_id
        }
        waid = phone  # usamos telefone como chave de conversa
        bridge.seed_context_and_log(waid, extracted, bot_message, cliente_nome=name)

        # Enviar via Twilio template
        res = twilio.send_whatsapp_template(phone, template_sid, parameters=variables)
        # Atualizar com SID/status
        db.record_notification(
            empresa_id,
            'confirmacao',
            appointment_id,
            exec_date,
            phone,
            variables,
            res.get('message_sid') if isinstance(res, dict) else None,
            res.get('status') if isinstance(res, dict) else None
        )


def scheduler_loop_once() -> None:
    """Executa 1 iteração: encontra o próximo next_run_at e dorme até lá, então roda."""
    import time
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from config import Config
    from models import EmpresaReminder, Empresa

    engine = create_engine(Config.POSTGRES_URL)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        now_utc = datetime.utcnow()
        rem = session.query(EmpresaReminder, Empresa).join(Empresa, EmpresaReminder.empresa_id == Empresa.id).\
            filter(EmpresaReminder.enabled == True, EmpresaReminder.next_run_at != None, Empresa.status == 'ativo').\
            order_by(EmpresaReminder.next_run_at.asc()).first()
        if not rem:
            time.sleep(60)
            return
        conf, emp = rem
        sleep_sec = max(0, (conf.next_run_at - now_utc).total_seconds())
        time.sleep(sleep_sec)
        # Rodar confirmação para essa empresa
        db = DatabaseService()
        configs = db.get_active_reminders()
        match = [c for c in configs if c['empresa_id'] == conf.empresa_id]
        if match:
            cfg = match[0]
            run_company_confirmation(conf.empresa_id, emp.slug, cfg)
        # Reagendar para o próximo dia no mesmo horário local
        tz = pytz.timezone(conf.timezone or 'America/Sao_Paulo')
        local_next = tz.localize(datetime.now(tz).replace(hour=int((conf.send_time_local or '11:00')[:2]), minute=int((conf.send_time_local or '11:00')[3:5]), second=0, microsecond=0)) + timedelta(days=1)
        conf.next_run_at = local_next.astimezone(pytz.utc).replace(tzinfo=None)
        session.commit()
    finally:
        session.close()


