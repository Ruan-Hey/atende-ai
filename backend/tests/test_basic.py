import pytest
from fastapi.testclient import TestClient

class TestBasicFunctionality:
    """Testes básicos para validar a estrutura"""
    
    def test_health_endpoint(self, client):
        """Testa endpoint de health check"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
    
    def test_root_endpoint(self, client):
        """Testa endpoint raiz"""
        response = client.get("/")
        assert response.status_code == 200
    
    def test_test_webhook_endpoint(self, client):
        """Testa endpoint de teste de webhook"""
        response = client.get("/test-webhook")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "success" in data
        assert "message" in data
    
    def test_unauthorized_access(self, client):
        """Testa acesso não autorizado"""
        response = client.get("/api/admin/metrics")
        assert response.status_code == 401
    
    def test_login_endpoint_exists(self, client):
        """Testa se endpoint de login existe"""
        response = client.post("/api/login", data={})
        # Deve retornar 422 (validation error) não 404 (not found)
        assert response.status_code == 422
    
    def test_empresa_not_found(self, client):
        """Testa busca de empresa inexistente"""
        response = client.get("/api/admin/empresa/empresa-inexistente")
        assert response.status_code == 401  # Não autorizado, não 404
    
    def test_conversation_endpoint_unauthorized(self, client):
        """Testa endpoint de conversa sem autorização"""
        response = client.get("/api/conversation/test-empresa/test-cliente")
        assert response.status_code == 401
    
    def test_logs_endpoint_works(self, client):
        """Testa endpoint de logs (não requer autenticação)"""
        response = client.get("/api/logs")
        assert response.status_code == 200
    
    def test_webhook_empresa_not_found(self, client):
        """Testa webhook para empresa inexistente"""
        webhook_data = {
            "Body": "Teste",
            "From": "whatsapp:+5511999999999",
            "To": "whatsapp:+5511888888888",
            "WaId": "5511999999999"
        }
        response = client.post("/webhook/empresa-inexistente", data=webhook_data)
        assert response.status_code == 404
    
    def test_webhook_empresa_not_found_404(self, client):
        """Testa webhook para empresa inexistente retorna 404"""
        webhook_data = {
            "Body": "",  # Mensagem vazia
            "From": "invalid-format"
        }
        response = client.post("/webhook/test-empresa", data=webhook_data)
        # Deve retornar 404 porque a empresa não existe
        assert response.status_code == 404
    
    def test_buffer_status_works(self, client):
        """Testa status do buffer (não requer autenticação)"""
        response = client.get("/api/admin/buffer/status")
        assert response.status_code == 200
    
    def test_erros_24h_works(self, client):
        """Testa erros 24h (não requer autenticação)"""
        response = client.get("/api/admin/erros-24h")
        assert response.status_code == 200 