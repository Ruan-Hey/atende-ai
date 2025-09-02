"""
Serviço de Email para Notificações
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        # Configuração do Gmail
        self.sender_email = "tinyteams.app@gmail.com"
        self.sender_password = "vins jvxh rrjn ysgn"
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
    
    def send_email(self, to_email: str, subject: str, body: str) -> bool:
        """
        Envia um email para um destinatário
        
        Args:
            to_email: Email do destinatário
            subject: Assunto do email
            body: Corpo do email
            
        Returns:
            bool: True se enviado com sucesso, False caso contrário
        """
        try:
            # Criar mensagem
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Enviar email
            logger.info(f"📧 Enviando email para: {to_email}")
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            
            text = msg.as_string()
            server.sendmail(self.sender_email, to_email, text)
            server.quit()
            
            logger.info(f"✅ Email enviado com sucesso para: {to_email}")
            return True
            
        except smtplib.SMTPAuthenticationError:
            logger.error("❌ Erro de autenticação Gmail")
            return False
        except Exception as e:
            logger.error(f"❌ Erro ao enviar email: {e}")
            return False
    
    def send_smart_agent_error_notification(self, user_email: str, error_details: dict) -> bool:
        """
        Envia notificação de erro do Smart Agent para usuário
        
        Args:
            user_email: Email do usuário
            error_details: Detalhes do erro
            
        Returns:
            bool: True se enviado com sucesso
        """
        subject = "🚨 Erro no Smart Agent - TinyTeams"
        
        # URL da conversa (se disponível)
        conversation_url = error_details.get('conversation_url', 'N/A')
        empresa_nome = error_details.get('empresa_nome', 'TinyTeams')
        
        body = f"""
Olá!

Ocorreu um erro no Smart Agent do {empresa_nome}.

📅 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
🔍 Tipo de Erro: {error_details.get('error_type', 'Erro desconhecido')}
📝 Detalhes: {error_details.get('message', 'Sem detalhes disponíveis')}
🆔 ID do Erro: {error_details.get('error_id', 'N/A')}
💬 Conversa: {conversation_url}

Nossa equipe foi notificada e está trabalhando para resolver o problema.

Atenciosamente,
Equipe TinyTeams
        """
        
        return self.send_email(user_email, subject, body)
    
    def send_webhook_error_notification(self, admin_email: str, error_details: dict) -> bool:
        """
        Envia notificação de erro crítico do Webhook para admin
        
        Args:
            admin_email: Email do administrador
            error_details: Detalhes do erro crítico
            
        Returns:
            bool: True se enviado com sucesso
        """
        subject = "🚨 ERRO CRÍTICO - Webhook Falhou - Atende AI"
        
        body = f"""
🚨 ALERTA CRÍTICO - WEBHOOK FALHOU

📅 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
🔍 Tipo de Erro: {error_details.get('error_type', 'Erro crítico')}
📝 Mensagem: {error_details.get('message', 'Sem detalhes disponíveis')}
🆔 ID do Erro: {error_details.get('error_id', 'N/A')}
🌐 URL do Webhook: {error_details.get('webhook_url', 'N/A')}
📊 Status Code: {error_details.get('status_code', 'N/A')}
⏱️ Tentativas: {error_details.get('attempts', 'N/A')}

AÇÃO NECESSÁRIA:
- Verificar logs do sistema
- Investigar falha no webhook
- Possível impacto nos clientes

Equipe Atende AI
        """
        
        return self.send_email(admin_email, subject, body)

# Instância global do serviço
email_service = EmailService()
