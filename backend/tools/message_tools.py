from typing import Dict, Any
from integrations.twilio_service import TwilioService
import logging

logger = logging.getLogger(__name__)

class MessageTools:
    """Ferramentas para envio de mensagens"""
    
    def __init__(self):
        self.twilio_service = None
    
    def _get_twilio_service(self, empresa_config: Dict[str, Any]) -> TwilioService:
        """Inicializa serviço do Twilio"""
        if not self.twilio_service:
            self.twilio_service = TwilioService(
                empresa_config.get('twilio_sid'),
                empresa_config.get('twilio_token'),
                empresa_config.get('twilio_number')
            )
        return self.twilio_service
    
    def enviar_resposta(self, mensagem: str, cliente_id: str, empresa_config: Dict[str, Any], canal: str = "whatsapp") -> str:
        """Envia resposta pelo canal apropriado"""
        try:
            if canal == "whatsapp":
                # Verificar se Twilio está configurado
                if not empresa_config.get('twilio_sid') or not empresa_config.get('twilio_token'):
                    return f"❌ Twilio não configurado para esta empresa"
                
                twilio_service = self._get_twilio_service(empresa_config)
                result = twilio_service.send_whatsapp_message(cliente_id, mensagem)
                
                if result.get('success'):
                    return f"✅ Mensagem enviada com sucesso para {cliente_id}"
                else:
                    return f"❌ Erro ao enviar mensagem: {result.get('error', 'Erro desconhecido')}"
            
            elif canal == "instagram":
                # TODO: Implementar integração com Instagram
                return f"📱 Instagram não implementado ainda. Mensagem: {mensagem[:50]}..."
            
            else:
                return f"❌ Canal {canal} não suportado"
                
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}")
            return f"❌ Erro ao enviar mensagem: {str(e)}"
    
    def enviar_mensagem_quebrada(self, mensagem: str, cliente_id: str, empresa_config: Dict[str, Any], canal: str = "whatsapp") -> str:
        """Envia mensagem quebrada em partes menores"""
        try:
            # Quebrar mensagem em partes de até 500 caracteres
            partes = self._quebrar_mensagem(mensagem, 500)
            
            twilio_service = self._get_twilio_service(empresa_config)
            
            for i, parte in enumerate(partes, 1):
                result = twilio_service.send_whatsapp_message(cliente_id, parte)
                
                if not result.get('success'):
                    return f"❌ Erro ao enviar parte {i}: {result.get('error', 'Erro desconhecido')}"
            
            return f"✅ Mensagem enviada em {len(partes)} partes"
            
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem quebrada: {e}")
            return f"❌ Erro ao enviar mensagem quebrada: {str(e)}"
    
    def _quebrar_mensagem(self, mensagem: str, max_length: int = 500) -> list:
        """Quebra mensagem em partes menores"""
        if len(mensagem) <= max_length:
            return [mensagem]
        
        partes = []
        palavras = mensagem.split()
        parte_atual = ""
        
        for palavra in palavras:
            if len(parte_atual + " " + palavra) <= max_length:
                parte_atual += " " + palavra if parte_atual else palavra
            else:
                if parte_atual:
                    partes.append(parte_atual)
                parte_atual = palavra
        
        if parte_atual:
            partes.append(parte_atual)
        
        return partes 