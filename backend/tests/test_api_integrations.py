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
    
    def test_twilio_integration_success(self, mock_requests):
        """Testa integração bem-sucedida com Twilio"""
        from integrations.twilio_service import TwilioService
    
        mock_response = Mock()
        mock_response.json.return_value = {
            'sid': 'test-message-sid',
            'status': 'sent'
        }
        mock_response.raise_for_status.return_value = None
        mock_requests.post.return_value = mock_response
    
        service = TwilioService("test-sid", "test-token", "+1234567890")
        result = service.send_whatsapp_message("+5511999999999", "Teste de mensagem")
    
        assert result['success'] is True
        assert result['message_sid'] == 'test-message-sid'
        mock_requests.post.assert_called_once()
    
    def test_twilio_integration_error(self, mock_requests):
        """Testa tratamento de erro na integração com Twilio"""
        from integrations.twilio_service import TwilioService
    
        mock_requests.post.side_effect = Exception("Twilio API error")
    
        service = TwilioService("test-sid", "test-token", "+1234567890")
        result = service.send_whatsapp_message("+5511999999999", "Teste de mensagem")
    
        assert result['success'] is False
        assert 'error' in result
    
    def test_google_calendar_integration_success(self, mock_google_calendar):
        """Testa integração bem-sucedida com Google Calendar"""
        from integrations.google_calendar_service import GoogleCalendarService
    
        mock_service = Mock()
        mock_google_calendar.return_value = mock_service
    
        # Mock para listar eventos
        mock_service.events.return_value.list.return_value.execute.return_value = {
            'items': [
                {
                    'summary': 'Reunião de teste',
                    'start': {'dateTime': '2024-01-01T10:00:00Z'},
                    'end': {'dateTime': '2024-01-01T11:00:00Z'}
                }
            ]
        }
    
        service = GoogleCalendarService("test-credentials")
        events = service.list_events("2024-01-01", "2024-01-02")
    
        assert len(events) == 1
        assert events[0]['summary'] == 'Reunião de teste'
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
    
        # Mock para credenciais
        with patch('integrations.google_sheets_service.Credentials.from_service_account_file') as mock_creds:
            mock_creds.return_value = Mock()
            
            mock_sheet = Mock()
            mock_sheet.get_all_values.return_value = [
                ["Nome", "Email"],
                ["João", "joao@test.com"],
                ["Maria", "maria@test.com"]
            ]
            mock_google_sheets.open_by_key.return_value = mock_sheet
    
            service = GoogleSheetsService("test-credentials")
            data = service.read_data("test-sheet-id")
    
            assert len(data) == 2
            assert data[0]["Nome"] == "João"
            mock_google_sheets.open_by_key.assert_called_once()
    
    def test_google_sheets_integration_error(self, mock_google_sheets):
        """Testa tratamento de erro na integração com Google Sheets"""
        from integrations.google_sheets_service import GoogleSheetsService
    
        # Mock para credenciais
        with patch('integrations.google_sheets_service.Credentials.from_service_account_file') as mock_creds:
            mock_creds.return_value = Mock()
            mock_google_sheets.open_by_key.side_effect = Exception("Google Sheets API error")
    
            service = GoogleSheetsService("test-credentials")
            
            with pytest.raises(Exception):
                service.read_data("test-sheet-id")
    
    def test_google_sheets_write_data(self, mock_google_sheets):
        """Testa escrita de dados no Google Sheets"""
        from integrations.google_sheets_service import GoogleSheetsService
    
        # Mock para credenciais
        with patch('integrations.google_sheets_service.Credentials.from_service_account_file') as mock_creds:
            mock_creds.return_value = Mock()
            
            mock_sheet = Mock()
            mock_sheet.get_all_values.return_value = [["Nome", "Email"]]
            mock_google_sheets.open_by_key.return_value = mock_sheet
    
            service = GoogleSheetsService("test-credentials")
            data = [{"Nome": "João", "Email": "joao@test.com"}]
            result = service.write_data("test-sheet-id", data)
    
            assert result is True
            mock_sheet.update.assert_called_once()
    
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
    
    def test_twilio_message_formatting(self, mock_requests):
        """Testa formatação de mensagens do Twilio"""
        from integrations.twilio_service import TwilioService
    
        mock_response = Mock()
        mock_response.json.return_value = {'sid': 'test-sid', 'status': 'sent'}
        mock_response.raise_for_status.return_value = None
        mock_requests.post.return_value = mock_response
    
        service = TwilioService("test-sid", "test-token", "+1234567890")
        
        # Testa formatação de número
        result = service.send_whatsapp_message("5511999999999", "Teste")
        assert result['success'] is True
        
        # Verifica se o número foi formatado corretamente
        call_args = mock_requests.post.call_args
        data = call_args[1]['data']
        assert data['To'] == 'whatsapp:+5511999999999'
    
    def test_google_calendar_create_event(self, mock_google_calendar):
        """Testa criação de evento no Google Calendar"""
        from integrations.google_calendar_service import GoogleCalendarService
    
        mock_service = Mock()
        mock_google_calendar.return_value = mock_service
    
        # Mock para criar evento
        mock_service.events.return_value.insert.return_value.execute.return_value = {
            "id": "test-event-id",
            "summary": "Reunião de teste"
        }
    
        service = GoogleCalendarService("test-credentials")
    
        event_data = {
            "summary": "Reunião de teste",
            "start": "2024-01-01T10:00:00Z",
            "end": "2024-01-01T11:00:00Z",
            "attendees": ["test@example.com"]
        }
    
        result = service.create_event(event_data)
        assert result['id'] == "test-event-id"
        mock_service.events.return_value.insert.assert_called_once()
    
    def test_google_sheets_write_data(self, mock_google_sheets):
        """Testa escrita de dados no Google Sheets"""
        from integrations.google_sheets_service import GoogleSheetsService
    
        # Mock para credenciais
        with patch('integrations.google_sheets_service.Credentials.from_service_account_file') as mock_creds:
            mock_creds.return_value = Mock()
            
            mock_sheet = Mock()
            mock_google_sheets.open_by_key.return_value = mock_sheet
    
            service = GoogleSheetsService("test-credentials")
            data = [{"Nome": "João", "Email": "joao@test.com"}]
            service.write_data("test-sheet-id", data)
    
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
        assert "Success after retry" in response
        assert call_count == 3
    
    def test_audio_transcription_success(self, mock_openai):
        """Testa transcrição de áudio bem-sucedida"""
        from integrations.openai_service import OpenAIService
        import tempfile
        import os
    
        # Mock para transcrição de áudio
        mock_transcript = Mock()
        mock_transcript.text = "Olá, preciso de ajuda com meu pedido"
        mock_openai.audio.transcriptions.create.return_value = mock_transcript
    
        service = OpenAIService("test-key")
    
        # Criar arquivo de áudio temporário para teste
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_file.write(b"fake audio data")
            temp_file_path = temp_file.name
        
        try:
            # Mock para requests.get
            with patch('requests.get') as mock_requests:
                mock_response = Mock()
                mock_response.content = b"fake audio data"
                mock_response.raise_for_status.return_value = None
                mock_requests.return_value = mock_response
                
                # Mock para open usando MagicMock
                with patch('builtins.open', create=True) as mock_open:
                    mock_file = MagicMock()
                    mock_open.return_value = mock_file
                    
                    # Mock para os.unlink
                    with patch('os.unlink') as mock_unlink:
                        result = service.transcribe_audio(
                            "https://example.com/audio.mp3",
                            "test-sid",
                            "test-token"
                        )
                        
                        assert result == "Olá, preciso de ajuda com meu pedido"
                        mock_openai.audio.transcriptions.create.assert_called_once()
                        mock_unlink.assert_called_once()
        
        finally:
            # Limpar arquivo temporário
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    def test_audio_transcription_error(self, mock_openai):
        """Testa tratamento de erro na transcrição de áudio"""
        from integrations.openai_service import OpenAIService
    
        # Mock para simular erro
        mock_openai.audio.transcriptions.create.side_effect = Exception("Transcription error")
    
        service = OpenAIService("test-key")
    
        # Mock para requests.get
        with patch('requests.get') as mock_requests:
            mock_response = Mock()
            mock_response.content = b"fake audio data"
            mock_response.raise_for_status.return_value = None
            mock_requests.return_value = mock_response
            
            # Mock para open usando MagicMock
            with patch('builtins.open', create=True) as mock_open:
                mock_file = MagicMock()
                mock_open.return_value = mock_file
                
                # Mock para os.unlink
                with patch('os.unlink') as mock_unlink:
                    result = service.transcribe_audio(
                        "https://example.com/audio.mp3",
                        "test-sid",
                        "test-token"
                    )
                    
                    assert result == ""
                    mock_unlink.assert_called_once()
    
    def test_audio_transcription_network_error(self, mock_openai):
        """Testa erro de rede na transcrição de áudio"""
        from integrations.openai_service import OpenAIService
    
        service = OpenAIService("test-key")
    
        # Mock para simular erro de rede
        with patch('requests.get') as mock_requests:
            mock_requests.side_effect = Exception("Network error")
            
            result = service.transcribe_audio(
                "https://example.com/audio.mp3",
                "test-sid",
                "test-token"
            )
            
            assert result == ""
    
    def test_audio_transcription_invalid_url(self, mock_openai):
        """Testa transcrição com URL inválida"""
        from integrations.openai_service import OpenAIService
    
        service = OpenAIService("test-key")
    
        # Mock para simular erro de URL inválida
        with patch('requests.get') as mock_requests:
            mock_requests.side_effect = Exception("Invalid URL")
            
            result = service.transcribe_audio(
                "invalid-url",
                "test-sid",
                "test-token"
            )
            
            assert result == "" 