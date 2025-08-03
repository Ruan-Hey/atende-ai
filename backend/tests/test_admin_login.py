import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import json
from passlib.hash import bcrypt

class TestAdminLogin:
    """Testes para login no painel administrativo"""
    
    def test_login_success(self, client, sample_usuario):
        """Testa login bem-sucedido"""
        login_data = {
            "username": "admin@test.com",
            "password": "test123"
        }
        
        response = client.post("/api/login", data=login_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0
    
    def test_login_invalid_credentials(self, client):
        """Testa login com credenciais inválidas"""
        login_data = {
            "username": "admin@test.com",
            "password": "wrong_password"
        }
        
        response = client.post("/api/login", data=login_data)
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
    
    def test_login_user_not_found(self, client):
        """Testa login com usuário inexistente"""
        login_data = {
            "username": "nonexistent@test.com",
            "password": "test123"
        }
        
        response = client.post("/api/login", data=login_data)
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
    
    def test_login_missing_credentials(self, client):
        """Testa login sem credenciais"""
        response = client.post("/api/login", data={})
        
        assert response.status_code == 422  # Validation error
    
    def test_login_missing_username(self, client):
        """Testa login sem username"""
        login_data = {
            "password": "test123"
        }
        
        response = client.post("/api/login", data=login_data)
        
        assert response.status_code == 422
    
    def test_login_missing_password(self, client):
        """Testa login sem password"""
        login_data = {
            "username": "admin@test.com"
        }
        
        response = client.post("/api/login", data=login_data)
        
        assert response.status_code == 422
    
    def test_login_empty_credentials(self, client):
        """Testa login com credenciais vazias"""
        login_data = {
            "username": "",
            "password": ""
        }
        
        response = client.post("/api/login", data=login_data)
        
        assert response.status_code == 401
    
    def test_login_with_superuser(self, client, test_db_session):
        """Testa login com usuário superuser"""
        from models import Usuario, Empresa
        
        # Criar empresa
        empresa = Empresa(
            slug="test-superuser-empresa",
            nome="Empresa Superuser",
            status="ativo"
        )
        test_db_session.add(empresa)
        test_db_session.commit()
        
        # Criar usuário superuser
        usuario = Usuario(
            email="superuser@test.com",
            senha_hash=bcrypt.hash("superuser123"),
            is_superuser=True,
            empresa_id=empresa.id
        )
        test_db_session.add(usuario)
        test_db_session.commit()
        
        login_data = {
            "username": "superuser@test.com",
            "password": "superuser123"
        }
        
        response = client.post("/api/login", data=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
    
    def test_login_with_regular_user(self, client, test_db_session, sample_empresa):
        """Testa login com usuário regular"""
        from models import Usuario
        
        # Criar usuário regular
        usuario = Usuario(
            email="regular@test.com",
            senha_hash=bcrypt.hash("regular123"),
            is_superuser=False,
            empresa_id=sample_empresa.id
        )
        test_db_session.add(usuario)
        test_db_session.commit()
        
        login_data = {
            "username": "regular@test.com",
            "password": "regular123"
        }
        
        response = client.post("/api/login", data=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
    
    def test_token_validation_success(self, client, auth_headers):
        """Testa validação de token válido"""
        response = client.get("/api/admin/metrics", headers=auth_headers)
        assert response.status_code == 200
    
    def test_token_validation_invalid_token(self, client):
        """Testa validação de token inválido"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/admin/metrics", headers=headers)
        assert response.status_code == 401
    
    def test_token_validation_missing_token(self, client):
        """Testa validação sem token"""
        response = client.get("/api/admin/metrics")
        assert response.status_code == 401
    
    def test_token_validation_expired_token(self, client, test_db_session, sample_usuario):
        """Testa validação de token expirado"""
        from jose import jwt
        from config import Config
        
        config = Config()
        # Token expirado (exp no passado)
        expired_token = jwt.encode(
            {"sub": sample_usuario.email, "exp": 0},
            config.SECRET_KEY,
            algorithm=config.ALGORITHM
        )
        
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/api/admin/metrics", headers=headers)
        assert response.status_code == 401
    
    def test_superuser_access_control(self, client, test_db_session, sample_empresa):
        """Testa controle de acesso para superuser"""
        from models import Usuario
        
        # Criar usuário não superuser
        usuario = Usuario(
            email="nonsuper@test.com",
            senha_hash=bcrypt.hash("nonsuper123"),
            is_superuser=False,
            empresa_id=sample_empresa.id
        )
        test_db_session.add(usuario)
        test_db_session.commit()
        
        # Gerar token para usuário não superuser
        from jose import jwt
        from config import Config
        
        config = Config()
        token = jwt.encode(
            {"sub": usuario.email, "exp": 9999999999},
            config.SECRET_KEY,
            algorithm=config.ALGORITHM
        )
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Tentar acessar endpoint que requer superuser
        response = client.get("/api/admin/usuarios", headers=headers)
        assert response.status_code == 403
    
    def test_login_performance(self, client, sample_usuario):
        """Testa performance do login"""
        import time
        
        login_data = {
            "username": "admin@test.com",
            "password": "test123"
        }
        
        start_time = time.time()
        response = client.post("/api/login", data=login_data)
        end_time = time.time()
        
        assert response.status_code == 200
        # Verifica se o login foi rápido (menos de 1 segundo)
        assert (end_time - start_time) < 1.0
    
    def test_concurrent_logins(self, client, test_db_session):
        """Testa múltiplos logins simultâneos"""
        from models import Usuario, Empresa
        
        # Criar múltiplos usuários
        empresa = Empresa(slug="test-concurrent", nome="Empresa Concurrent", status="ativo")
        test_db_session.add(empresa)
        test_db_session.commit()
        
        usuarios = []
        for i in range(5):
            usuario = Usuario(
                email=f"user{i}@test.com",
                senha_hash=bcrypt.hash(f"password{i}"),
                is_superuser=False,
                empresa_id=empresa.id
            )
            test_db_session.add(usuario)
            usuarios.append(usuario)
        
        test_db_session.commit()
        
        # Simular logins simultâneos
        import threading
        import time
        
        results = []
        
        def login_user(email, password):
            login_data = {"username": email, "password": password}
            response = client.post("/api/login", data=login_data)
            results.append(response.status_code)
        
        threads = []
        for i in range(5):
            thread = threading.Thread(
                target=login_user,
                args=(f"user{i}@test.com", f"password{i}")
            )
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verifica se todos os logins foram bem-sucedidos
        assert all(status == 200 for status in results) 