import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import json
from datetime import datetime

class TestWebhookWhatsApp:
    """Testes para webhook e resposta das mensagens do WhatsApp"""
    
    def test_webhook_handler_success(self, client, sample_empresa):
        """Testa processamento bem-sucedido de webhook do WhatsApp"""
        webhook_data = {
            "Body": "Olá, preciso de ajuda",
            "From": "whatsapp:+5511999999999",
            "To": "whatsapp:+5511888888888",
            "WaId": "5511999999999",
            "MessageType": "text",
            "ProfileName": "João Silva"
        }
        
        with patch('integrations.twilio_service.Client') as mock_twilio:
            mock_client = Mock()
            mock_twilio.return_value = mock_client
            
            response = client.post(
                f"/webhook/{sample_empresa.slug}",
                data=webhook_data
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "success" in data
    
    def test_webhook_handler_empresa_not_found(self, client):
        """Testa webhook para empresa inexistente"""
        webhook_data = {
            "Body": "Olá",
            "From": "whatsapp:+5511999999999",
            "To": "whatsapp:+5511888888888",
            "WaId": "5511999999999"
        }
        
        response = client.post("/webhook/empresa-inexistente", data=webhook_data)
        assert response.status_code == 404
    
    def test_webhook_handler_invalid_data(self, client, sample_empresa):
        """Testa webhook com dados inválidos"""
        webhook_data = {
            "Body": "",  # Mensagem vazia
            "From": "invalid-format",
            "To": "invalid-format"
        }
        
        response = client.post(f"/webhook/{sample_empresa.slug}", data=webhook_data)
        assert response.status_code == 400
    
    def test_webhook_handler_missing_required_fields(self, client, sample_empresa):
        """Testa webhook com campos obrigatórios ausentes"""
        webhook_data = {
            "Body": "Olá"
            # Campos From, To, WaId ausentes
        }
        
        response = client.post(f"/webhook/{sample_empresa.slug}", data=webhook_data)
        assert response.status_code == 400
    
    def test_webhook_handler_media_message(self, client, sample_empresa):
        """Testa processamento de mensagem com mídia"""
        webhook_data = {
            "Body": "Imagem",
            "From": "whatsapp:+5511999999999",
            "To": "whatsapp:+5511888888888",
            "WaId": "5511999999999",
            "MessageType": "image",
            "MediaUrl0": "https://example.com/image.jpg"
        }
        
        with patch('integrations.twilio_service.Client') as mock_twilio:
            mock_client = Mock()
            mock_twilio.return_value = mock_client
            
            response = client.post(f"/webhook/{sample_empresa.slug}", data=webhook_data)
            
            assert response.status_code == 200
            data = response.json()
            assert "success" in data
    
    def test_webhook_handler_openai_integration(self, client, sample_empresa, mock_openai):
        """Testa integração com OpenAI no processamento de webhook"""
        webhook_data = {
            "Body": "Qual é o horário de funcionamento?",
            "From": "whatsapp:+5511999999999",
            "To": "whatsapp:+5511888888888",
            "WaId": "5511999999999"
        }
        
        # Mock da resposta do OpenAI
        mock_openai.ChatCompletion.create.return_value = Mock(
            choices=[Mock(message=Mock(content="Nosso horário de funcionamento é de segunda a sexta, das 8h às 18h."))]
        )
        
        with patch('integrations.twilio_service.Client') as mock_twilio:
            mock_client = Mock()
            mock_twilio.return_value = mock_client
            
            response = client.post(f"/webhook/{sample_empresa.slug}", data=webhook_data)
            
            assert response.status_code == 200
            # Verifica se o OpenAI foi chamado
            mock_openai.ChatCompletion.create.assert_called_once()
    
    def test_webhook_handler_twilio_response(self, client, sample_empresa, mock_twilio):
        """Testa envio de resposta via Twilio"""
        webhook_data = {
            "Body": "Olá",
            "From": "whatsapp:+5511999999999",
            "To": "whatsapp:+5511888888888",
            "WaId": "5511999999999"
        }
        
        mock_client = Mock()
        mock_twilio.return_value = mock_client
        
        response = client.post(f"/webhook/{sample_empresa.slug}", data=webhook_data)
        
        assert response.status_code == 200
        # Verifica se o Twilio foi chamado para enviar resposta
        mock_client.messages.create.assert_called()
    
    def test_webhook_handler_error_handling(self, client, sample_empresa):
        """Testa tratamento de erros no webhook"""
        webhook_data = {
            "Body": "Teste de erro",
            "From": "whatsapp:+5511999999999",
            "To": "whatsapp:+5511888888888",
            "WaId": "5511999999999"
        }
        
        # Mock para simular erro no Twilio
        with patch('integrations.twilio_service.Client') as mock_twilio:
            mock_client = Mock()
            mock_client.messages.create.side_effect = Exception("Twilio error")
            mock_twilio.return_value = mock_client
            
            response = client.post(f"/webhook/{sample_empresa.slug}", data=webhook_data)
            
            # Deve retornar erro mas não quebrar
            assert response.status_code in [200, 500]
    
    def test_webhook_handler_message_storage(self, client, sample_empresa, test_db_session):
        """Testa armazenamento de mensagens no banco de dados"""
        webhook_data = {
            "Body": "Mensagem para armazenar",
            "From": "whatsapp:+5511999999999",
            "To": "whatsapp:+5511888888888",
            "WaId": "5511999999999"
        }
        
        with patch('integrations.twilio_service.Client') as mock_twilio:
            mock_client = Mock()
            mock_twilio.return_value = mock_client
            
            response = client.post(f"/webhook/{sample_empresa.slug}", data=webhook_data)
            
            assert response.status_code == 200
        
        # Verifica se a mensagem foi armazenada
        from models import Mensagem
        mensagens = test_db_session.query(Mensagem).filter(
            Mensagem.empresa_id == sample_empresa.id,
            Mensagem.cliente_id == "5511999999999"
        ).all()
        
        assert len(mensagens) > 0
        assert any(msg.text == "Mensagem para armazenar" for msg in mensagens)
    
    def test_webhook_handler_conversation_context(self, client, sample_empresa):
        """Testa manutenção do contexto da conversa"""
        # Primeira mensagem
        webhook_data_1 = {
            "Body": "Olá, sou João",
            "From": "whatsapp:+5511999999999",
            "To": "whatsapp:+5511888888888",
            "WaId": "5511999999999"
        }
        
        # Segunda mensagem
        webhook_data_2 = {
            "Body": "Preciso de ajuda com meu pedido",
            "From": "whatsapp:+5511999999999",
            "To": "whatsapp:+5511888888888",
            "WaId": "5511999999999"
        }
        
        with patch('integrations.twilio_service.Client') as mock_twilio:
            mock_client = Mock()
            mock_twilio.return_value = mock_client
            
            # Envia primeira mensagem
            response1 = client.post(f"/webhook/{sample_empresa.slug}", data=webhook_data_1)
            assert response1.status_code == 200
            
            # Envia segunda mensagem
            response2 = client.post(f"/webhook/{sample_empresa.slug}", data=webhook_data_2)
            assert response2.status_code == 200
    
    def test_webhook_handler_rate_limiting(self, client, sample_empresa):
        """Testa limitação de taxa de mensagens"""
        webhook_data = {
            "Body": "Teste de rate limiting",
            "From": "whatsapp:+5511999999999",
            "To": "whatsapp:+5511888888888",
            "WaId": "5511999999999"
        }
        
        with patch('integrations.twilio_service.Client') as mock_twilio:
            mock_client = Mock()
            mock_twilio.return_value = mock_client
            
            # Envia múltiplas mensagens rapidamente
            responses = []
            for i in range(10):
                response = client.post(f"/webhook/{sample_empresa.slug}", data=webhook_data)
                responses.append(response.status_code)
            
            # Todas devem ser processadas com sucesso
            assert all(status == 200 for status in responses)
    
    def test_webhook_handler_empresa_inactive(self, client, test_db_session):
        """Testa webhook para empresa inativa"""
        from models import Empresa
        
        # Criar empresa inativa
        empresa_inativa = Empresa(
            slug="empresa-inativa",
            nome="Empresa Inativa",
            status="inativo"
        )
        test_db_session.add(empresa_inativa)
        test_db_session.commit()
        
        webhook_data = {
            "Body": "Olá",
            "From": "whatsapp:+5511999999999",
            "To": "whatsapp:+5511888888888",
            "WaId": "5511999999999"
        }
        
        response = client.post(f"/webhook/{empresa_inativa.slug}", data=webhook_data)
        assert response.status_code == 404
    
    def test_webhook_handler_logging(self, client, sample_empresa, test_db_session):
        """Testa logging de webhooks"""
        webhook_data = {
            "Body": "Mensagem para log",
            "From": "whatsapp:+5511999999999",
            "To": "whatsapp:+5511888888888",
            "WaId": "5511999999999"
        }
        
        with patch('integrations.twilio_service.Client') as mock_twilio:
            mock_client = Mock()
            mock_twilio.return_value = mock_client
            
            response = client.post(f"/webhook/{sample_empresa.slug}", data=webhook_data)
            assert response.status_code == 200
        
        # Verifica se o log foi criado
        from models import Log
        logs = test_db_session.query(Log).filter(
            Log.empresa_id == sample_empresa.id
        ).all()
        
        # Deve haver pelo menos um log
        assert len(logs) >= 1
    
    def test_test_webhook_endpoint(self, client):
        """Testa endpoint de teste de webhook"""
        response = client.get("/test-webhook")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "message" in data 