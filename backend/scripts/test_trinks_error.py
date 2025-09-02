"""
Script de teste: força um erro na API da Trinks e dispara email para o admin.

Como executar:
  1) Ative o venv:  source venv/bin/activate
  2) Rode:          python backend/scripts/test_trinks_error.py
"""
import os
import sys
import logging
from typing import Dict

# Permitir imports relativos ao backend
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.main import send_webhook_error_notification  # type: ignore
from backend.integrations.trinks_service import TrinksService  # type: ignore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_trinks_error")


def run() -> None:
    # Config inválida para forçar erro (URL inexistente e API key vazia)
    config: Dict[str, str] = {
        "trinks_base_url": "https://api.trinks.com.br/v1/nao-existe",  # endpoint inválido
        "trinks_api_key": "",
        "trinks_estabelecimento_id": "0",
    }

    service = TrinksService(config)
    logger.info("Forçando erro em chamada para Trinks...")
    result = service.get_professionals()

    if "error" in result:
        logger.info(f"Erro capturado como esperado: {result['error']}")
        error_details = {
            "error_type": "Webhook Failed",
            "message": f"Trinks API falhou: {result['error']}",
            "webhook_url": f"{config['trinks_base_url']}/profissionais",
            "status_code": "N/A",
            "attempts": 1,
            "error_id": "TEST_WEBHOOK_ERR_TRINKS"
        }
        # Dispara notificação de erro crítico para admin
        send_webhook_error_notification(error_details)
        logger.info("Notificação enviada ao admin (verifique seu email).")
    else:
        logger.warning("A chamada não falhou como esperado. Resultado: %s", result)


if __name__ == "__main__":
    run()


