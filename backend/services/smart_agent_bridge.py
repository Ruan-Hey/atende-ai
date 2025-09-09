from typing import Dict, Any, Optional
from agents.smart_agent import SmartAgent
from services.services import DatabaseService


class SmartAgentBridge:
    """Bridge para semear contexto e histórico do SmartAgent em mensagens proativas."""

    def __init__(self, empresa_id: int, empresa_config: Dict[str, Any]):
        self.empresa_id = empresa_id
        self.empresa_config = empresa_config
        self.db = DatabaseService()
        self.agent = SmartAgent(empresa_config)

    def seed_context_and_log(self, waid: str, extracted_data: Dict[str, Any], bot_message: str, cliente_nome: Optional[str] = None) -> None:
        """Adiciona mensagem do bot ao histórico e semeia extracted_data no cache do agente."""
        # Adicionar mensagem como AI na memória do agente
        try:
            self.agent.memory.chat_memory.add_ai_message(bot_message)
        except Exception:
            pass

        # Salvar conversa + extracted_data no cache interno do agente
        try:
            self.agent._save_conversation_context(waid, extracted_data)
        except Exception:
            pass

        # Persistir no banco para o histórico do usuário
        try:
            self.db.save_bot_message(self.empresa_id, waid, bot_message, cliente_nome=cliente_nome)
        except Exception:
            pass


