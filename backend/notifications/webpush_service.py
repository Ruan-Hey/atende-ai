"""
Serviço para Web Push Notifications
"""

import json
import logging
from typing import List, Dict, Any, Optional
from pywebpush import webpush, WebPushException
from .vapid_keys import VAPID_PRIVATE_KEY, VAPID_CLAIMS, VAPID_HEADERS
from .models import PushSubscription, NotificationRule, NotificationLog
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class WebPushService:
    """Serviço para gerenciar web push notifications"""
    
    def __init__(self):
        self.vapid_private_key = VAPID_PRIVATE_KEY
        self.vapid_claims = VAPID_CLAIMS
        self.vapid_headers = VAPID_HEADERS
    
    def send_notification(
        self, 
        subscription: PushSubscription, 
        titulo: str, 
        mensagem: str, 
        dados: Optional[Dict] = None
    ) -> bool:
        """Envia uma notificação para uma subscription específica"""
        try:
            # 🆕 AÇÕES SIMPLES E DIRETAS
            actions = [
                {
                    "action": "view_conversation",
                    "title": "Ver conversa"
                },
                {
                    "action": "close",
                    "title": "Fechar"
                }
            ]
            
            # Preparar payload da notificação simplificado
            payload = {
                "title": titulo,
                "body": mensagem,
                "icon": "/favicon.png",
                "badge": "/favicon.png",
                "data": dados or {},
                "actions": actions,
                "requireInteraction": True,
                "tag": "atende-ai-error"
            }
            
            # Enviar via pywebpush
            response = webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {
                        "p256dh": subscription.p256dh,
                        "auth": subscription.auth
                    }
                },
                data=json.dumps(payload),
                vapid_private_key=self.vapid_private_key,
                vapid_claims=self.vapid_claims,
                content_encoding="aes128gcm"
            )
            
            logger.info(f"✅ Notificação enviada para {subscription.usuario_id}: {response.status_code}")
            return True
            
        except WebPushException as e:
            logger.error(f"❌ Erro ao enviar notificação para {subscription.usuario_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Erro inesperado ao enviar notificação: {e}")
            return False
    
    def send_bulk_notifications(
        self, 
        subscriptions: List[PushSubscription], 
        titulo: str, 
        mensagem: str, 
        dados: Optional[Dict] = None
    ) -> Dict[str, int]:
        """Envia notificações para múltiplas subscriptions"""
        resultados = {
            "total": len(subscriptions),
            "enviados": 0,
            "falhas": 0
        }
        
        for subscription in subscriptions:
            if self.send_notification(subscription, titulo, mensagem, dados):
                resultados["enviados"] += 1
            else:
                resultados["falhas"] += 1
        
        return resultados
    
    def get_subscriptions_by_rule(
        self, 
        session: Session, 
        regra: NotificationRule
    ) -> List[PushSubscription]:
        """Busca subscriptions baseado na regra de notificação"""
        subscriptions = []
        
        try:
            # Filtrar por tipo de destinatário
            if "admin" in regra.destinatarios:
                # Buscar subscriptions de usuários admin (sem join, usando subquery)
                from models import Usuario
                admin_user_ids = session.query(Usuario.id).filter(Usuario.is_superuser == True).subquery()
                admin_subs = session.query(PushSubscription).filter(
                    PushSubscription.usuario_id.in_(admin_user_ids),
                    PushSubscription.ativo == True
                ).all()
                subscriptions.extend(admin_subs)
            
            if "empresa" in regra.destinatarios and regra.empresa_id:
                # Buscar subscriptions de usuários de empresa específica
                empresa_subs = session.query(PushSubscription).filter(
                    PushSubscription.empresa_id == regra.empresa_id,
                    PushSubscription.ativo == True
                ).all()
                subscriptions.extend(empresa_subs)
            
            if "todos" in regra.destinatarios:
                # Buscar todas as subscriptions ativas
                todas_subs = session.query(PushSubscription).filter(
                    PushSubscription.ativo == True
                ).all()
                subscriptions.extend(todas_subs)
            
            # Remover duplicatas (usuário pode ter múltiplas subscriptions)
            seen = set()
            unique_subscriptions = []
            for sub in subscriptions:
                if sub.usuario_id not in seen:
                    seen.add(sub.usuario_id)
                    unique_subscriptions.append(sub)
            
            return unique_subscriptions
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar subscriptions: {e}")
            return []
    
    def execute_notification_rule(
        self, 
        session: Session, 
        regra: NotificationRule, 
        titulo: str, 
        mensagem: str, 
        dados_contexto: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Executa uma regra de notificação específica"""
        try:
            # Buscar subscriptions baseado na regra
            subscriptions = self.get_subscriptions_by_rule(session, regra)
            
            if not subscriptions:
                logger.warning(f"⚠️ Nenhuma subscription encontrada para regra: {regra.nome}")
                return {"enviados": 0, "falhas": 0, "total": 0}
            
            # Enviar notificações
            resultados = self.send_bulk_notifications(subscriptions, titulo, mensagem, dados_contexto)
            
            # Log da execução
            log = NotificationLog(
                rule_id=regra.id,
                empresa_id=dados_contexto.get('empresa_id') if dados_contexto else None,
                usuario_id=None,  # Será preenchido se necessário
                titulo=titulo,
                mensagem=mensagem,
                dados=dados_contexto,
                status='enviado' if resultados["enviados"] > 0 else 'falha'
            )
            session.add(log)
            session.commit()
            
            logger.info(f"✅ Regra '{regra.nome}' executada: {resultados['enviados']}/{resultados['total']} enviados")
            return resultados
            
        except Exception as e:
            logger.error(f"❌ Erro ao executar regra '{regra.nome}': {e}")
            return {"enviados": 0, "falhas": 0, "total": 0}
