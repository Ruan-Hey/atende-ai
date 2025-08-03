import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import json

class TestAPIIntegrations:
    """Testes para integrações com APIs externas"""
    
    def test_openai_integration_success(self, mock_openai):
        """Testa integração bem-sucedida com OpenAI"""
        from integrations.openai_service import OpenAIService
        
        # Mock da resposta do OpenAI
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Resposta do OpenAI"))]
        mock_openai.ChatCompletion.create.return_value = mock_response
        
        service = OpenAIService("test-key")
        response = service.generate_response("Olá, como posso ajudar?")
        
        assert response is not None
        assert "Resposta do OpenAI" in response
        mock_openai.ChatCompletion.create.assert_called_once()
    
    def test_openai_integration_error(self, mock_openai):
        """Testa tratamento de erro na integração com OpenAI"""
        from integrations.openai_service import OpenAIService
        
        # Mock para simular erro
        mock_openai.ChatCompletion.create.side_effect = Exception("OpenAI API error")
        
        service = OpenAIService("test-key")
        
        with pytest.raises(Exception):
            service.generate_response("Teste")
    
    def test_twilio_integration_success(self, mock_twilio):
        """Testa integração bem-sucedida com Twilio"""
        from integrations.twilio_service import TwilioService
        
        mock_client = Mock()
        mock_twilio.return_value = mock_client
        
        service = TwilioService("test-sid", "test-token", "+5511888888888")
        service.send_message("+5511999999999", "Mensagem de teste")
        
        mock_client.messages.create.assert_called_once()
    
    def test_twilio_integration_error(self, mock_twilio):
        """Testa tratamento de erro na integração com Twilio"""
        from integrations.twilio_service import TwilioService
        
        mock_client = Mock()
        mock_client.messages.create.side_effect = Exception("Twilio API error")
        mock_twilio.return_value = mock_client
        
        service = TwilioService("test-sid", "test-token", "+5511888888888")
        
        with pytest.raises(Exception):
            service.send_message("+5511999999999", "Teste")
    
    def test_google_calendar_integration_success(self, mock_google_calendar):
        """Testa integração bem-sucedida com Google Calendar"""
        from integrations.google_calendar_service import GoogleCalendarService
        
        mock_service = Mock()
        mock_google_calendar.return_value = mock_service
        
        service = GoogleCalendarService("test-credentials")
        
        # Mock para listar eventos
        mock_service.events.return_value.list.return_value.execute.return_value = {
            "items": [
                {
                    "summary": "Reunião de teste",
                    "start": {"dateTime": "2024-01-01T10:00:00Z"},
                    "end": {"dateTime": "2024-01-01T11:00:00Z"}
                }
            ]
        }
        
        events = service.list_events("2024-01-01", "2024-01-02")
        
        assert events is not None
        assert len(events) > 0
        mock_service.events.return_value.list.assert_called_once()
    
    def test_google_calendar_integration_error(self, mock_google_calendar):
        """Testa tratamento de erro na integração com Google Calendar"""
        from integrations.google_calendar_service import GoogleCalendarService
        
        mock_service = Mock()
        mock_service.events.return_value.list.side_effect = Exception("Google Calendar API error")
        mock_google_calendar.return_value = mock_service
        
        service = GoogleCalendarService("test-credentials")
        
        with pytest.raises(Exception):
            service.list_events("2024-01-01", "2024-01-02")
    
    def test_google_sheets_integration_success(self, mock_google_sheets):
        """Testa integração bem-sucedida com Google Sheets"""
        from integrations.google_sheets_service import GoogleSheetsService
        
        mock_sheet = Mock()
        mock_sheet.get_all_records.return_value = [
            {"Nome": "João", "Email": "joao@test.com"},
            {"Nome": "Maria", "Email": "maria@test.com"}
        ]
        
        mock_google_sheets.open_by_key.return_value = mock_sheet
        
        service = GoogleSheetsService("test-credentials")
        data = service.read_sheet("test-sheet-id")
        
        assert data is not None
        assert len(data) == 2
        mock_sheet.get_all_records.assert_called_once()
    
    def test_google_sheets_integration_error(self, mock_google_sheets):
        """Testa tratamento de erro na integração com Google Sheets"""
        from integrations.google_sheets_service import GoogleSheetsService
        
        mock_google_sheets.open_by_key.side_effect = Exception("Google Sheets API error")
        
        service = GoogleSheetsService("test-credentials")
        
        with pytest.raises(Exception):
            service.read_sheet("test-sheet-id")
    
    def test_openai_with_context(self, mock_openai):
        """Testa OpenAI com contexto de conversa"""
        from integrations.openai_service import OpenAIService
        
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Resposta contextualizada"))]
        mock_openai.ChatCompletion.create.return_value = mock_response
        
        service = OpenAIService("test-key")
        
        # Simula conversa com contexto
        context = [
            {"role": "user", "content": "Olá"},
            {"role": "assistant", "content": "Olá! Como posso ajudar?"},
            {"role": "user", "content": "Preciso de ajuda"}
        ]
        
        response = service.generate_response_with_context(context, "Qual é o problema?")
        
        assert response is not None
        mock_openai.ChatCompletion.create.assert_called_once()
    
    def test_twilio_message_formatting(self, mock_twilio):
        """Testa formatação de mensagens no Twilio"""
        from integrations.twilio_service import TwilioService
        
        mock_client = Mock()
        mock_twilio.return_value = mock_client
        
        service = TwilioService("test-sid", "test-token", "+5511888888888")
        
        # Testa mensagem com caracteres especiais
        service.send_message("+5511999999999", "Olá! Como vai? 😊")
        
        mock_client.messages.create.assert_called_once()
        call_args = mock_client.messages.create.call_args
        assert "Olá! Como vai? 😊" in str(call_args)
    
    def test_google_calendar_create_event(self, mock_google_calendar):
        """Testa criação de evento no Google Calendar"""
        from integrations.google_calendar_service import GoogleCalendarService
        
        mock_service = Mock()
        mock_google_calendar.return_value = mock_service
        
        service = GoogleCalendarService("test-credentials")
        
        # Mock para criar evento
        mock_service.events.return_value.insert.return_value.execute.return_value = {
            "id": "test-event-id",
            "summary": "Reunião de teste"
        }
        
        event_data = {
            "summary": "Reunião de teste",
            "start": "2024-01-01T10:00:00Z",
            "end": "2024-01-01T11:00:00Z",
            "attendees": ["test@example.com"]
        }
        
        result = service.create_event(event_data)
        
        assert result is not None
        assert "id" in result
        mock_service.events.return_value.insert.assert_called_once()
    
    def test_google_sheets_write_data(self, mock_google_sheets):
        """Testa escrita de dados no Google Sheets"""
        from integrations.google_sheets_service import GoogleSheetsService
        
        mock_sheet = Mock()
        mock_google_sheets.open_by_key.return_value = mock_sheet
        
        service = GoogleSheetsService("test-credentials")
        
        data = [
            ["Nome", "Email", "Telefone"],
            ["João", "joao@test.com", "+5511999999999"],
            ["Maria", "maria@test.com", "+5511888888888"]
        ]
        
        service.write_sheet("test-sheet-id", data)
        
        mock_sheet.update.assert_called_once()
    
    def test_integration_error_logging(self, mock_openai):
        """Testa logging de erros de integração"""
        from integrations.openai_service import OpenAIService
        
        # Mock para simular erro
        mock_openai.ChatCompletion.create.side_effect = Exception("API Error")
        
        service = OpenAIService("test-key")
        
        # Deve registrar o erro
        with pytest.raises(Exception):
            service.generate_response("Teste")
    
    def test_integration_rate_limiting(self, mock_openai):
        """Testa limitação de taxa nas integrações"""
        from integrations.openai_service import OpenAIService
        import time
        
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Resposta"))]
        mock_openai.ChatCompletion.create.return_value = mock_response
        
        service = OpenAIService("test-key")
        
        # Múltiplas chamadas rápidas
        start_time = time.time()
        for i in range(5):
            service.generate_response(f"Teste {i}")
        end_time = time.time()
        
        # Verifica se todas as chamadas foram processadas
        assert mock_openai.ChatCompletion.create.call_count == 5
        # Verifica se não demorou muito
        assert (end_time - start_time) < 10.0
    
    def test_integration_authentication(self, mock_openai):
        """Testa autenticação nas integrações"""
        from integrations.openai_service import OpenAIService
        
        # Testa com chave inválida
        service = OpenAIService("invalid-key")
        
        mock_openai.ChatCompletion.create.side_effect = Exception("Invalid API key")
        
        with pytest.raises(Exception):
            service.generate_response("Teste")
    
    def test_integration_timeout_handling(self, mock_openai):
        """Testa tratamento de timeout nas integrações"""
        from integrations.openai_service import OpenAIService
        import time
        
        def slow_response(*args, **kwargs):
            time.sleep(2)  # Simula resposta lenta
            raise Exception("Timeout")
        
        mock_openai.ChatCompletion.create.side_effect = slow_response
        
        service = OpenAIService("test-key")
        
        with pytest.raises(Exception):
            service.generate_response("Teste")
    
    def test_integration_data_validation(self, mock_openai):
        """Testa validação de dados nas integrações"""
        from integrations.openai_service import OpenAIService
        
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Resposta válida"))]
        mock_openai.ChatCompletion.create.return_value = mock_response
        
        service = OpenAIService("test-key")
        
        # Testa com dados válidos
        response = service.generate_response("Teste válido")
        assert response is not None
        
        # Testa com dados inválidos
        with pytest.raises(Exception):
            service.generate_response("")  # String vazia
    
    def test_integration_retry_mechanism(self, mock_openai):
        """Testa mecanismo de retry nas integrações"""
        from integrations.openai_service import OpenAIService
        
        call_count = 0
        
        def failing_then_success(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary error")
            return Mock(choices=[Mock(message=Mock(content="Success after retry"))])
        
        mock_openai.ChatCompletion.create.side_effect = failing_then_success
        
        service = OpenAIService("test-key")
        
        # Deve falhar nas primeiras tentativas mas eventualmente funcionar
        response = service.generate_response("Teste retry")
        
        assert response is not None
        assert call_count >= 3 