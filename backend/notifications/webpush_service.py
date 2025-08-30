"""
Serviço para Web Push Notifications
"""

import json
import logging
from typing import List, Dict, Optional
from pywebpush import WebPushException, webpush
from .vapid_keys import VAPID_PRIVATE_KEY, VAPID_CLAIMS

logger = logging.getLogger(__name__)

class WebPushService:
    """Serviço para enviar push notifications"""
    
    def __init__(self):
        self.vapid_private_key = VAPID_PRIVATE_KEY
        self.vapid_claims = VAPID_CLAIMS
    
    def send_notification(
        self,
        subscription_info: Dict,
        title: str,
        message: str,
        data: Optional[Dict] = None
    ) -> bool:
        """
        Envia uma push notification
        
        Args:
            subscription_info: Informações da subscription
            title: Título da notificação
            message: Mensagem da notificação
            data: Dados adicionais
        
        Returns:
            bool: True se enviado com sucesso
        """
        try:
            # Preparar payload da notificação
            payload = {
                "title": title,
                "message": message,
                "data": data or {}
            }
            
            # Converter para JSON
            payload_json = json.dumps(payload)
            
            # Enviar notificação
            response = webpush(
                subscription_info=subscription_info,
                data=payload_json,
                vapid_private_key=self.vapid_private_key,
                vapid_claims=self.vapid_claims
            )
            
            logger.info(f"✅ Notificação enviada com sucesso: {title}")
            return True
            
        except WebPushException as e:
            logger.error(f"❌ Erro ao enviar notificação: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Erro inesperado ao enviar notificação: {e}")
            return False
    
    def send_bulk_notifications(
        self,
        subscriptions: List[Dict],
        title: str,
        message: str,
        data: Optional[Dict] = None
    ) -> Dict[str, int]:
        """
        Envia notificações para múltiplas subscriptions
        
        Args:
            subscriptions: Lista de subscriptions
            title: Título da notificação
            message: Mensagem da notificação
            data: Dados adicionais
        
        Returns:
            Dict com contagem de sucessos e falhas
        """
        success_count = 0
        failure_count = 0
        
        for subscription in subscriptions:
            if self.send_notification(subscription, title, message, data):
                success_count += 1
            else:
                failure_count += 1
        
        result = {
            "success": success_count,
            "failure": failure_count,
            "total": len(subscriptions)
        }
        
        logger.info(f"📊 Notificações em lote: {result}")
        return result
    
    def send_agent_error_notification(
        self,
        subscriptions: List[Dict],
        empresa_nome: str,
        error_message: str,
        error_details: Dict
    ) -> Dict[str, int]:
        """
        Envia notificação específica para erro de agente
        
        Args:
            subscriptions: Lista de subscriptions
            empresa_nome: Nome da empresa
            error_message: Mensagem de erro
            error_details: Detalhes do erro
        
        Returns:
            Dict com contagem de sucessos e falhas
        """
        title = f"🚨 Erro no Agente - {empresa_nome}"
        message = error_message
        
        data = {
            "type": "agent_error",
            "empresa": empresa_nome,
            "error_details": error_details,
            "timestamp": error_details.get("timestamp")
        }
        
        return self.send_bulk_notifications(subscriptions, title, message, data)

# Instância global do serviço
webpush_service = WebPushService()
