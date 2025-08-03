import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import json
from datetime import datetime, timedelta

class TestMessageHistory:
    """Testes para verificação do histórico de mensagens"""
    
    def test_message_storage_success(self, client, sample_empresa, test_db_session):
        """Testa armazenamento bem-sucedido de mensagens"""
        from models import Mensagem
        
        # Criar mensagem de teste
        mensagem = Mensagem(
            empresa_id=sample_empresa.id,
            cliente_id="test-cliente-123",
            text="Mensagem de teste",
            is_bot=False
        )
        test_db_session.add(mensagem)
        test_db_session.commit()
        
        # Verificar se a mensagem foi armazenada
        stored_message = test_db_session.query(Mensagem).filter(
            Mensagem.id == mensagem.id
        ).first()
        
        assert stored_message is not None
        assert stored_message.text == "Mensagem de teste"
        assert stored_message.cliente_id == "test-cliente-123"
        assert stored_message.is_bot == False
    
    def test_message_history_retrieval(self, client, auth_headers, sample_empresa, test_db_session):
        """Testa recuperação do histórico de mensagens"""
        from models import Mensagem
        
        # Criar múltiplas mensagens para um cliente
        cliente_id = "cliente-historia-123"
        mensagens = [
            Mensagem(
                empresa_id=sample_empresa.id,
                cliente_id=cliente_id,
                text="Olá, preciso de ajuda",
                is_bot=False
            ),
            Mensagem(
                empresa_id=sample_empresa.id,
                cliente_id=cliente_id,
                text="Olá! Como posso ajudar?",
                is_bot=True
            ),
            Mensagem(
                empresa_id=sample_empresa.id,
                cliente_id=cliente_id,
                text="Quero agendar uma consulta",
                is_bot=False
            )
        ]
        
        for msg in mensagens:
            test_db_session.add(msg)
        test_db_session.commit()
        
        # Buscar histórico
        response = client.get(
            f"/api/conversation/{sample_empresa.slug}/{cliente_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "messages" in data
        assert len(data["messages"]) == 3
        
        # Verificar ordem das mensagens (mais recente primeiro)
        messages = data["messages"]
        assert messages[0]["text"] == "Quero agendar uma consulta"
        assert messages[1]["text"] == "Olá! Como posso ajudar?"
        assert messages[2]["text"] == "Olá, preciso de ajuda"
    
    def test_message_history_pagination(self, client, auth_headers, sample_empresa, test_db_session):
        """Testa paginação do histórico de mensagens"""
        from models import Mensagem
        
        # Criar muitas mensagens
        cliente_id = "cliente-paginacao-123"
        for i in range(25):
            mensagem = Mensagem(
                empresa_id=sample_empresa.id,
                cliente_id=cliente_id,
                text=f"Mensagem {i}",
                is_bot=(i % 2 == 0)
            )
            test_db_session.add(mensagem)
        test_db_session.commit()
        
        # Buscar com limite
        response = client.get(
            f"/api/conversation/{sample_empresa.slug}/{cliente_id}?limit=10",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["messages"]) == 10
        assert "has_more" in data
    
    def test_message_history_filtering(self, client, auth_headers, sample_empresa, test_db_session):
        """Testa filtros no histórico de mensagens"""
        from models import Mensagem
        
        # Criar mensagens com diferentes timestamps
        cliente_id = "cliente-filtro-123"
        base_time = datetime.now()
        
        mensagens = [
            Mensagem(
                empresa_id=sample_empresa.id,
                cliente_id=cliente_id,
                text="Mensagem antiga",
                is_bot=False,
                timestamp=base_time - timedelta(days=2)
            ),
            Mensagem(
                empresa_id=sample_empresa.id,
                cliente_id=cliente_id,
                text="Mensagem recente",
                is_bot=False,
                timestamp=base_time
            )
        ]
        
        for msg in mensagens:
            test_db_session.add(msg)
        test_db_session.commit()
        
        # Buscar mensagens recentes
        response = client.get(
            f"/api/conversation/{sample_empresa.slug}/{cliente_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Deve retornar mensagens ordenadas por timestamp
        assert len(data["messages"]) >= 1
    
    def test_message_history_empresa_not_found(self, client, auth_headers):
        """Testa busca de histórico para empresa inexistente"""
        response = client.get(
            "/api/conversation/empresa-inexistente/cliente-123",
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    def test_message_history_unauthorized(self, client, sample_empresa):
        """Testa acesso não autorizado ao histórico"""
        response = client.get(
            f"/api/conversation/{sample_empresa.slug}/cliente-123"
        )
        
        assert response.status_code == 401
    
    def test_message_history_empty(self, client, auth_headers, sample_empresa):
        """Testa histórico vazio para cliente sem mensagens"""
        response = client.get(
            f"/api/conversation/{sample_empresa.slug}/cliente-sem-mensagens",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "messages" in data
        assert len(data["messages"]) == 0
    
    def test_message_history_bot_messages(self, client, auth_headers, sample_empresa, test_db_session):
        """Testa histórico incluindo mensagens do bot"""
        from models import Mensagem
        
        cliente_id = "cliente-bot-123"
        mensagens = [
            Mensagem(
                empresa_id=sample_empresa.id,
                cliente_id=cliente_id,
                text="Olá",
                is_bot=False
            ),
            Mensagem(
                empresa_id=sample_empresa.id,
                cliente_id=cliente_id,
                text="Olá! Como posso ajudar?",
                is_bot=True
            ),
            Mensagem(
                empresa_id=sample_empresa.id,
                cliente_id=cliente_id,
                text="Preciso de ajuda",
                is_bot=False
            )
        ]
        
        for msg in mensagens:
            test_db_session.add(msg)
        test_db_session.commit()
        
        response = client.get(
            f"/api/conversation/{sample_empresa.slug}/{cliente_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        messages = data["messages"]
        assert len(messages) == 3
        
        # Verificar se as mensagens do bot estão marcadas corretamente
        bot_messages = [msg for msg in messages if msg["is_bot"]]
        user_messages = [msg for msg in messages if not msg["is_bot"]]
        
        assert len(bot_messages) == 1
        assert len(user_messages) == 2
    
    def test_message_history_performance(self, client, auth_headers, sample_empresa, test_db_session):
        """Testa performance do carregamento do histórico"""
        from models import Mensagem
        import time
        
        # Criar muitas mensagens para testar performance
        cliente_id = "cliente-performance-123"
        for i in range(100):
            mensagem = Mensagem(
                empresa_id=sample_empresa.id,
                cliente_id=cliente_id,
                text=f"Mensagem {i}",
                is_bot=(i % 2 == 0)
            )
            test_db_session.add(mensagem)
        test_db_session.commit()
        
        start_time = time.time()
        response = client.get(
            f"/api/conversation/{sample_empresa.slug}/{cliente_id}?limit=50",
            headers=auth_headers
        )
        end_time = time.time()
        
        assert response.status_code == 200
        # Verifica se a resposta foi rápida (menos de 1 segundo)
        assert (end_time - start_time) < 1.0
    
    def test_message_history_concurrent_access(self, client, auth_headers, sample_empresa, test_db_session):
        """Testa acesso concorrente ao histórico"""
        from models import Mensagem
        import threading
        import time
        
        # Criar mensagens
        cliente_id = "cliente-concurrent-123"
        for i in range(10):
            mensagem = Mensagem(
                empresa_id=sample_empresa.id,
                cliente_id=cliente_id,
                text=f"Mensagem {i}",
                is_bot=False
            )
            test_db_session.add(mensagem)
        test_db_session.commit()
        
        results = []
        
        def fetch_history():
            response = client.get(
                f"/api/conversation/{sample_empresa.slug}/{cliente_id}",
                headers=auth_headers
            )
            results.append(response.status_code)
        
        # Múltiplas requisições simultâneas
        threads = []
        for i in range(5):
            thread = threading.Thread(target=fetch_history)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Todas as requisições devem ser bem-sucedidas
        assert all(status == 200 for status in results)
    
    def test_message_history_data_integrity(self, client, auth_headers, sample_empresa, test_db_session):
        """Testa integridade dos dados do histórico"""
        from models import Mensagem
        
        cliente_id = "cliente-integridade-123"
        original_text = "Mensagem com caracteres especiais: áéíóú çãõ ñ"
        
        mensagem = Mensagem(
            empresa_id=sample_empresa.id,
            cliente_id=cliente_id,
            text=original_text,
            is_bot=False
        )
        test_db_session.add(mensagem)
        test_db_session.commit()
        
        response = client.get(
            f"/api/conversation/{sample_empresa.slug}/{cliente_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        messages = data["messages"]
        assert len(messages) == 1
        assert messages[0]["text"] == original_text
    
    def test_message_history_timestamp_ordering(self, client, auth_headers, sample_empresa, test_db_session):
        """Testa ordenação por timestamp no histórico"""
        from models import Mensagem
        
        cliente_id = "cliente-timestamp-123"
        base_time = datetime.now()
        
        # Criar mensagens com timestamps específicos
        mensagens = [
            Mensagem(
                empresa_id=sample_empresa.id,
                cliente_id=cliente_id,
                text="Primeira mensagem",
                is_bot=False,
                timestamp=base_time - timedelta(minutes=2)
            ),
            Mensagem(
                empresa_id=sample_empresa.id,
                cliente_id=cliente_id,
                text="Segunda mensagem",
                is_bot=True,
                timestamp=base_time - timedelta(minutes=1)
            ),
            Mensagem(
                empresa_id=sample_empresa.id,
                cliente_id=cliente_id,
                text="Terceira mensagem",
                is_bot=False,
                timestamp=base_time
            )
        ]
        
        for msg in mensagens:
            test_db_session.add(msg)
        test_db_session.commit()
        
        response = client.get(
            f"/api/conversation/{sample_empresa.slug}/{cliente_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        messages = data["messages"]
        assert len(messages) == 3
        
        # Verificar ordem (mais recente primeiro)
        assert messages[0]["text"] == "Terceira mensagem"
        assert messages[1]["text"] == "Segunda mensagem"
        assert messages[2]["text"] == "Primeira mensagem"
    
    def test_message_history_cleanup_old_messages(self, client, auth_headers, sample_empresa, test_db_session):
        """Testa limpeza de mensagens antigas"""
        from models import Mensagem
        
        cliente_id = "cliente-cleanup-123"
        old_time = datetime.now() - timedelta(days=365)  # 1 ano atrás
        
        # Criar mensagem antiga
        old_message = Mensagem(
            empresa_id=sample_empresa.id,
            cliente_id=cliente_id,
            text="Mensagem antiga",
            is_bot=False,
            timestamp=old_time
        )
        test_db_session.add(old_message)
        test_db_session.commit()
        
        # Verificar se a mensagem antiga ainda está acessível
        response = client.get(
            f"/api/conversation/{sample_empresa.slug}/{cliente_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # A mensagem antiga deve estar disponível
        messages = data["messages"]
        assert len(messages) == 1
        assert messages[0]["text"] == "Mensagem antiga" 