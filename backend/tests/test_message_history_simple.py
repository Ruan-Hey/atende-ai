import pytest
from fastapi.testclient import TestClient

class TestMessageHistorySimple:
    """Testes simplificados para histórico de mensagens"""
    
    def test_message_storage_basic(self, client, test_db_session, sample_empresa):
        """Testa armazenamento básico de mensagens"""
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
    
    def test_message_history_retrieval_basic(self, client, test_db_session, sample_empresa):
        """Testa recuperação básica do histórico"""
        from models import Mensagem
        
        # Criar múltiplas mensagens
        cliente_id = "cliente-historia-123"
        mensagens = [
            Mensagem(
                empresa_id=sample_empresa.id,
                cliente_id=cliente_id,
                text="Primeira mensagem",
                is_bot=False
            ),
            Mensagem(
                empresa_id=sample_empresa.id,
                cliente_id=cliente_id,
                text="Segunda mensagem",
                is_bot=True
            ),
            Mensagem(
                empresa_id=sample_empresa.id,
                cliente_id=cliente_id,
                text="Terceira mensagem",
                is_bot=False
            )
        ]
        
        for msg in mensagens:
            test_db_session.add(msg)
        test_db_session.commit()
        
        # Verificar se as mensagens foram armazenadas
        stored_messages = test_db_session.query(Mensagem).filter(
            Mensagem.empresa_id == sample_empresa.id,
            Mensagem.cliente_id == cliente_id
        ).all()
        
        assert len(stored_messages) == 3
        
        # Verificar conteúdo das mensagens
        texts = [msg.text for msg in stored_messages]
        assert "Primeira mensagem" in texts
        assert "Segunda mensagem" in texts
        assert "Terceira mensagem" in texts
    
    def test_message_history_bot_vs_user(self, client, test_db_session, sample_empresa):
        """Testa diferenciação entre mensagens do bot e do usuário"""
        from models import Mensagem
        
        cliente_id = "cliente-bot-test-123"
        
        # Criar mensagens do usuário e do bot
        user_message = Mensagem(
            empresa_id=sample_empresa.id,
            cliente_id=cliente_id,
            text="Olá, preciso de ajuda",
            is_bot=False
        )
        
        bot_message = Mensagem(
            empresa_id=sample_empresa.id,
            cliente_id=cliente_id,
            text="Olá! Como posso ajudar?",
            is_bot=True
        )
        
        test_db_session.add(user_message)
        test_db_session.add(bot_message)
        test_db_session.commit()
        
        # Verificar mensagens do usuário
        user_messages = test_db_session.query(Mensagem).filter(
            Mensagem.empresa_id == sample_empresa.id,
            Mensagem.cliente_id == cliente_id,
            Mensagem.is_bot == False
        ).all()
        
        assert len(user_messages) == 1
        assert user_messages[0].text == "Olá, preciso de ajuda"
        
        # Verificar mensagens do bot
        bot_messages = test_db_session.query(Mensagem).filter(
            Mensagem.empresa_id == sample_empresa.id,
            Mensagem.cliente_id == cliente_id,
            Mensagem.is_bot == True
        ).all()
        
        assert len(bot_messages) == 1
        assert bot_messages[0].text == "Olá! Como posso ajudar?"
    
    def test_message_history_timestamp_ordering(self, client, test_db_session, sample_empresa):
        """Testa ordenação por timestamp"""
        from models import Mensagem
        from datetime import datetime, timedelta
        
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
        
        # Buscar mensagens ordenadas por timestamp (mais recente primeiro)
        stored_messages = test_db_session.query(Mensagem).filter(
            Mensagem.empresa_id == sample_empresa.id,
            Mensagem.cliente_id == cliente_id
        ).order_by(Mensagem.timestamp.desc()).all()
        
        assert len(stored_messages) == 3
        
        # Verificar ordem (mais recente primeiro)
        assert stored_messages[0].text == "Terceira mensagem"
        assert stored_messages[1].text == "Segunda mensagem"
        assert stored_messages[2].text == "Primeira mensagem"
    
    def test_message_history_data_integrity(self, client, test_db_session, sample_empresa):
        """Testa integridade dos dados das mensagens"""
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
        
        # Recuperar mensagem
        stored_message = test_db_session.query(Mensagem).filter(
            Mensagem.id == mensagem.id
        ).first()
        
        assert stored_message is not None
        assert stored_message.text == original_text
        assert stored_message.cliente_id == cliente_id
        assert stored_message.empresa_id == sample_empresa.id
        assert stored_message.is_bot == False
    
    def test_message_history_empty_conversation(self, client, test_db_session, sample_empresa):
        """Testa conversa vazia"""
        from models import Mensagem
        
        cliente_id = "cliente-vazio-123"
        
        # Buscar mensagens de cliente que não existe
        stored_messages = test_db_session.query(Mensagem).filter(
            Mensagem.empresa_id == sample_empresa.id,
            Mensagem.cliente_id == cliente_id
        ).all()
        
        assert len(stored_messages) == 0
    
    def test_message_history_multiple_clients(self, client, test_db_session, sample_empresa):
        """Testa histórico de múltiplos clientes"""
        from models import Mensagem
        
        # Criar mensagens para diferentes clientes
        clientes = ["cliente-1", "cliente-2", "cliente-3"]
        
        for i, cliente_id in enumerate(clientes):
            mensagem = Mensagem(
                empresa_id=sample_empresa.id,
                cliente_id=cliente_id,
                text=f"Mensagem do cliente {i+1}",
                is_bot=False
            )
            test_db_session.add(mensagem)
        
        test_db_session.commit()
        
        # Verificar se todas as mensagens foram armazenadas
        for cliente_id in clientes:
            stored_messages = test_db_session.query(Mensagem).filter(
                Mensagem.empresa_id == sample_empresa.id,
                Mensagem.cliente_id == cliente_id
            ).all()
            
            assert len(stored_messages) == 1
            assert f"Mensagem do cliente" in stored_messages[0].text 