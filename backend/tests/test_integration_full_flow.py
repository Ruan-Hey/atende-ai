import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import json
from datetime import datetime

class TestIntegrationFullFlow:
    """Testes de integração para fluxo completo do sistema"""
    
    def test_complete_webhook_to_response_flow(self, client, sample_empresa, mock_openai, mock_twilio):
        """Testa fluxo completo: webhook -> processamento -> resposta"""
        # Mock OpenAI
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Olá! Como posso ajudar você hoje?"))]
        mock_openai.ChatCompletion.create.return_value = mock_response
        
        # Mock Twilio
        mock_client = Mock()
        mock_twilio.return_value = mock_client
        
        # Dados do webhook
        webhook_data = {
            "Body": "Olá, preciso de ajuda",
            "From": "whatsapp:+5511999999999",
            "To": "whatsapp:+5511888888888",
            "WaId": "5511999999999",
            "MessageType": "text"
        }
        
        # Enviar webhook
        response = client.post(f"/webhook/{sample_empresa.slug}", data=webhook_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        
        # Verificar se OpenAI foi chamado
        mock_openai.ChatCompletion.create.assert_called_once()
        
        # Verificar se Twilio foi chamado para enviar resposta
        mock_client.messages.create.assert_called_once()
    
    def test_complete_admin_workflow(self, client, auth_headers, sample_empresa, sample_usuario):
        """Testa fluxo completo do painel administrativo"""
        # 1. Login
        login_data = {
            "username": "admin@test.com",
            "password": "test123"
        }
        
        login_response = client.post("/api/login", data=login_data)
        assert login_response.status_code == 200
        
        # 2. Carregar métricas
        metrics_response = client.get("/api/admin/metrics", headers=auth_headers)
        assert metrics_response.status_code == 200
        
        # 3. Listar empresas
        empresas_response = client.get("/api/admin/empresas", headers=auth_headers)
        assert empresas_response.status_code == 200
        
        # 4. Ver métricas específicas da empresa
        empresa_metrics_response = client.get(
            f"/api/admin/empresa/{sample_empresa.slug}",
            headers=auth_headers
        )
        assert empresa_metrics_response.status_code == 200
        
        # 5. Ver clientes da empresa
        clientes_response = client.get(
            f"/api/admin/empresa/{sample_empresa.slug}/clientes",
            headers=auth_headers
        )
        assert clientes_response.status_code == 200
    
    def test_complete_conversation_flow(self, client, auth_headers, sample_empresa, test_db_session):
        """Testa fluxo completo de conversa"""
        from models import Mensagem
        
        cliente_id = "cliente-completo-123"
        
        # 1. Simular múltiplas mensagens na conversa
        mensagens = [
            {"text": "Olá", "is_bot": False},
            {"text": "Olá! Como posso ajudar?", "is_bot": True},
            {"text": "Quero agendar uma consulta", "is_bot": False},
            {"text": "Claro! Qual data você prefere?", "is_bot": True},
            {"text": "Amanhã às 14h", "is_bot": False},
            {"text": "Perfeito! Agendei para você.", "is_bot": True}
        ]
        
        for msg_data in mensagens:
            mensagem = Mensagem(
                empresa_id=sample_empresa.id,
                cliente_id=cliente_id,
                text=msg_data["text"],
                is_bot=msg_data["is_bot"]
            )
            test_db_session.add(mensagem)
        test_db_session.commit()
        
        # 2. Buscar histórico da conversa
        response = client.get(
            f"/api/conversation/{sample_empresa.slug}/{cliente_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 3. Verificar se todas as mensagens estão presentes
        messages = data["messages"]
        assert len(messages) == 6
        
        # 4. Verificar ordem das mensagens
        assert messages[0]["text"] == "Perfeito! Agendei para você."
        assert messages[5]["text"] == "Olá"
    
    def test_complete_error_handling_flow(self, client, sample_empresa, mock_openai, mock_twilio):
        """Testa fluxo completo de tratamento de erros"""
        # Mock para simular erro no OpenAI
        mock_openai.ChatCompletion.create.side_effect = Exception("OpenAI API Error")
        
        # Mock Twilio
        mock_client = Mock()
        mock_twilio.return_value = mock_client
        
        webhook_data = {
            "Body": "Teste de erro",
            "From": "whatsapp:+5511999999999",
            "To": "whatsapp:+5511888888888",
            "WaId": "5511999999999"
        }
        
        # Enviar webhook que deve gerar erro
        response = client.post(f"/webhook/{sample_empresa.slug}", data=webhook_data)
        
        # Deve retornar erro mas não quebrar o sistema
        assert response.status_code in [200, 500]
    
    def test_complete_performance_flow(self, client, auth_headers, sample_empresa, test_db_session):
        """Testa fluxo completo de performance"""
        import time
        from models import Mensagem
        
        # Criar muitas mensagens para testar performance
        cliente_id = "cliente-performance-123"
        for i in range(50):
            mensagem = Mensagem(
                empresa_id=sample_empresa.id,
                cliente_id=cliente_id,
                text=f"Mensagem {i}",
                is_bot=(i % 2 == 0)
            )
            test_db_session.add(mensagem)
        test_db_session.commit()
        
        # Testar performance do carregamento de histórico
        start_time = time.time()
        response = client.get(
            f"/api/conversation/{sample_empresa.slug}/{cliente_id}",
            headers=auth_headers
        )
        end_time = time.time()
        
        assert response.status_code == 200
        # Deve ser rápido (menos de 1 segundo)
        assert (end_time - start_time) < 1.0
        
        # Testar performance do carregamento de métricas
        start_time = time.time()
        metrics_response = client.get("/api/admin/metrics", headers=auth_headers)
        end_time = time.time()
        
        assert metrics_response.status_code == 200
        assert (end_time - start_time) < 2.0
    
    def test_complete_security_flow(self, client, sample_empresa):
        """Testa fluxo completo de segurança"""
        # 1. Testar acesso não autorizado
        response = client.get("/api/admin/metrics")
        assert response.status_code == 401
        
        # 2. Testar token inválido
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/admin/metrics", headers=headers)
        assert response.status_code == 401
        
        # 3. Testar acesso a empresa de outro usuário
        # (Este teste seria mais complexo e dependeria da implementação específica)
    
    def test_complete_data_integrity_flow(self, client, auth_headers, sample_empresa, test_db_session):
        """Testa fluxo completo de integridade de dados"""
        from models import Mensagem, Log
        
        cliente_id = "cliente-integridade-123"
        
        # 1. Criar mensagem
        mensagem = Mensagem(
            empresa_id=sample_empresa.id,
            cliente_id=cliente_id,
            text="Mensagem de teste para integridade",
            is_bot=False
        )
        test_db_session.add(mensagem)
        test_db_session.commit()
        
        # 2. Verificar se foi salva corretamente
        stored_message = test_db_session.query(Mensagem).filter(
            Mensagem.id == mensagem.id
        ).first()
        
        assert stored_message is not None
        assert stored_message.text == "Mensagem de teste para integridade"
        
        # 3. Buscar via API
        response = client.get(
            f"/api/conversation/{sample_empresa.slug}/{cliente_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 4. Verificar se os dados estão consistentes
        messages = data["messages"]
        assert len(messages) == 1
        assert messages[0]["text"] == "Mensagem de teste para integridade"
        assert messages[0]["cliente_id"] == cliente_id
        assert messages[0]["is_bot"] == False
    
    def test_complete_concurrent_flow(self, client, auth_headers, sample_empresa):
        """Testa fluxo completo com operações concorrentes"""
        import threading
        import time
        
        results = []
        
        def concurrent_operation(operation_type):
            if operation_type == "metrics":
                response = client.get("/api/admin/metrics", headers=auth_headers)
            elif operation_type == "empresas":
                response = client.get("/api/admin/empresas", headers=auth_headers)
            elif operation_type == "logs":
                response = client.get("/api/logs", headers=auth_headers)
            
            results.append(response.status_code)
        
        # Executar operações concorrentes
        threads = []
        operations = ["metrics", "empresas", "logs"] * 3  # 9 operações
        
        for i, op in enumerate(operations):
            thread = threading.Thread(target=concurrent_operation, args=(op,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verificar se todas as operações foram bem-sucedidas
        assert len(results) == 9
        assert all(status == 200 for status in results)
    
    def test_complete_error_recovery_flow(self, client, sample_empresa, mock_openai, mock_twilio):
        """Testa fluxo completo de recuperação de erros"""
        # 1. Primeira tentativa com erro
        mock_openai.ChatCompletion.create.side_effect = Exception("Temporary error")
        
        webhook_data = {
            "Body": "Teste de recuperação",
            "From": "whatsapp:+5511999999999",
            "To": "whatsapp:+5511888888888",
            "WaId": "5511999999999"
        }
        
        mock_client = Mock()
        mock_twilio.return_value = mock_client
        
        # Primeira tentativa deve falhar
        response1 = client.post(f"/webhook/{sample_empresa.slug}", data=webhook_data)
        
        # 2. Segunda tentativa com sucesso
        mock_openai.ChatCompletion.create.side_effect = None
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Resposta de recuperação"))]
        mock_openai.ChatCompletion.create.return_value = mock_response
        
        response2 = client.post(f"/webhook/{sample_empresa.slug}", data=webhook_data)
        
        # Segunda tentativa deve funcionar
        assert response2.status_code == 200
    
    def test_complete_monitoring_flow(self, client, auth_headers):
        """Testa fluxo completo de monitoramento"""
        # 1. Verificar health check
        health_response = client.get("/health")
        assert health_response.status_code == 200
        
        # 2. Verificar status do buffer
        buffer_response = client.get("/api/admin/buffer/status", headers=auth_headers)
        assert buffer_response.status_code == 200
        
        # 3. Verificar erros das últimas 24h
        errors_response = client.get("/api/admin/erros-24h", headers=auth_headers)
        assert errors_response.status_code == 200
        
        # 4. Verificar logs
        logs_response = client.get("/api/logs", headers=auth_headers)
        assert logs_response.status_code == 200 