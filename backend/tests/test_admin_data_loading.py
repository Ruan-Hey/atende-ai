import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import json

class TestAdminDataLoading:
    """Testes para carregamento de dados no painel administrativo"""
    
    def test_get_admin_metrics_success(self, client, auth_headers, sample_empresa, sample_usuario):
        """Testa carregamento bem-sucedido das métricas do admin"""
        response = client.get("/api/admin/metrics", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verifica se as métricas estão presentes
        assert "total_empresas" in data
        assert "total_clientes" in data
        assert "total_reservas" in data
        assert "total_atendimentos" in data
        assert "empresas" in data
        assert isinstance(data["empresas"], list)
    
    def test_get_admin_metrics_unauthorized(self, client):
        """Testa acesso não autorizado às métricas do admin"""
        response = client.get("/api/admin/metrics")
        assert response.status_code == 401
    
    def test_get_empresas_success(self, client, auth_headers, sample_empresa):
        """Testa carregamento bem-sucedido da lista de empresas"""
        response = client.get("/api/admin/empresas", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        if len(data) > 0:
            empresa = data[0]
            assert "id" in empresa
            assert "nome" in empresa
            assert "slug" in empresa
            assert "status" in empresa
    
    def test_get_empresa_metrics_success(self, client, auth_headers, sample_empresa):
        """Testa carregamento de métricas específicas de uma empresa"""
        response = client.get(f"/api/admin/empresa/{sample_empresa.slug}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "nome" in data
        assert "atendimentos" in data
        assert "reservas" in data
        assert "clientes" in data
        assert "status" in data
        assert "recent_activity" in data
    
    def test_get_empresa_metrics_not_found(self, client, auth_headers):
        """Testa busca de empresa inexistente"""
        response = client.get("/api/admin/empresa/empresa-inexistente", headers=auth_headers)
        assert response.status_code == 404
    
    def test_get_empresa_clientes_success(self, client, auth_headers, sample_empresa, sample_mensagem):
        """Testa carregamento de clientes de uma empresa"""
        response = client.get(f"/api/admin/empresa/{sample_empresa.slug}/clientes", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        if len(data) > 0:
            cliente = data[0]
            assert "cliente_id" in cliente
            assert "ultima_mensagem" in cliente
            assert "total_mensagens" in cliente
    
    def test_get_usuarios_success(self, client, auth_headers, sample_usuario):
        """Testa carregamento da lista de usuários"""
        response = client.get("/api/admin/usuarios", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        if len(data) > 0:
            usuario = data[0]
            assert "id" in usuario
            assert "email" in usuario
            assert "is_superuser" in usuario
            assert "empresa_id" in usuario
    
    def test_get_usuarios_forbidden(self, client, auth_headers, sample_usuario):
        """Testa acesso negado para usuário não superuser"""
        # Criar usuário não superuser
        from models import Usuario
        from passlib.hash import bcrypt
        
        # Mock para simular usuário não superuser
        with patch('main.get_current_superuser') as mock_superuser:
            mock_superuser.side_effect = Exception("Not enough permissions")
            
            response = client.get("/api/admin/usuarios", headers=auth_headers)
            assert response.status_code == 403
    
    def test_get_logs_success(self, client, auth_headers):
        """Testa carregamento de logs"""
        response = client.get("/api/logs", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
    
    def test_get_logs_with_empresa_filter(self, client, auth_headers, sample_empresa):
        """Testa carregamento de logs filtrados por empresa"""
        response = client.get(f"/api/logs?empresa={sample_empresa.slug}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
    
    def test_get_erros_24h_success(self, client, auth_headers):
        """Testa carregamento de erros das últimas 24h"""
        response = client.get("/api/admin/erros-24h", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
    
    def test_get_buffer_status_success(self, client, auth_headers):
        """Testa carregamento do status do buffer"""
        response = client.get("/api/admin/buffer/status", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "pending_messages" in data
        assert "processed_messages" in data
    
    def test_admin_data_loading_performance(self, client, auth_headers, sample_empresa):
        """Testa performance do carregamento de dados"""
        import time
        
        start_time = time.time()
        response = client.get("/api/admin/metrics", headers=auth_headers)
        end_time = time.time()
        
        assert response.status_code == 200
        # Verifica se a resposta foi rápida (menos de 2 segundos)
        assert (end_time - start_time) < 2.0
    
    def test_admin_data_loading_with_multiple_empresas(self, client, auth_headers, test_db_session):
        """Testa carregamento com múltiplas empresas"""
        from models import Empresa
        
        # Criar múltiplas empresas
        empresas = []
        for i in range(5):
            empresa = Empresa(
                slug=f"empresa-{i}",
                nome=f"Empresa {i}",
                status="ativo"
            )
            test_db_session.add(empresa)
            empresas.append(empresa)
        
        test_db_session.commit()
        
        response = client.get("/api/admin/empresas", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verifica se todas as empresas foram carregadas
        assert len(data) >= 5 