"""
Script de teste: simula um erro do Smart Agent e envia email para todos
os usuários com notificações ativas.

Como executar:
  1) Ative o venv:  source venv/bin/activate
  2) Rode:          python backend/scripts/test_smart_agent_error.py
"""
import os
import sys
import logging
from typing import Dict

# Permitir imports relativos ao backend
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from main import send_smart_agent_error_notification  # type: ignore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_smart_agent_error")


def run() -> None:
    logger.info("Simulando erro do Smart Agent...")
    error_details: Dict[str, str] = {
        "error_type": "Tool Error",
        "message": "Erro simulado no Smart Agent ao executar tool X",
        "error_id": "TEST_SMART_AGENT_ERR"
    }

    # Exemplo: simular erro para TinyTeams (empresa_id = 1)
    empresa_id = 1  # TinyTeams
    conversation_url = "https://app.tinyteams.com/conversation/12345"  # URL de exemplo

    # Dispara notificação apenas para usuários elegíveis na empresa (ou admin)
    send_smart_agent_error_notification(error_details, empresa_id=empresa_id, conversation_url=conversation_url)
    logger.info("Notificações enviadas (verifique os emails dos usuários).")


if __name__ == "__main__":
    run()


