#!/usr/bin/env python3
"""
Script para debugar o problema do conhecimento da empresa
"""

import asyncio
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Empresa
from agents.base_agent import BaseAgent

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuração do banco
DATABASE_URL = "postgresql://atendeai:atendeai@localhost:5432/atendeai"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def test_knowledge_loading():
    """Testa se o conhecimento está sendo carregado corretamente"""
    session = SessionLocal()
    try:
        # Buscar empresa Pancia Piena
        empresa = session.query(Empresa).filter(Empresa.slug == "pancia-piena").first()
        
        if not empresa:
            logger.error("❌ Empresa 'pancia-piena' não encontrada")
            return
        
        logger.info(f"✅ Empresa encontrada: {empresa.nome}")
        logger.info(f"📊 ID: {empresa.id}")
        
        # Verificar knowledge_json
        knowledge = empresa.knowledge_json
        logger.info(f"📖 Knowledge JSON: {knowledge}")
        
        if not knowledge:
            logger.warning("⚠️ Knowledge JSON está vazio")
            return
        
        if not isinstance(knowledge, dict):
            logger.error(f"❌ Knowledge JSON não é um dicionário: {type(knowledge)}")
            return
        
        items = knowledge.get('items', [])
        logger.info(f"📝 Número de itens: {len(items)}")
        
        for i, item in enumerate(items):
            logger.info(f"  Item {i+1}:")
            logger.info(f"    Título: {item.get('title', 'N/A')}")
            logger.info(f"    Key: {item.get('key', 'N/A')}")
            logger.info(f"    Descrição: {item.get('description', 'N/A')[:100]}...")
            logger.info(f"    Ativo: {item.get('active', 'N/A')}")
        
        # Testar agente
        empresa_config = {
            'nome': empresa.nome,
            'slug': empresa.slug,
            'empresa_id': empresa.id,
            'knowledge_json': empresa.knowledge_json or {"items": []}
        }
        
        logger.info("🧪 Testando agente...")
        agent = BaseAgent(empresa_config)
        
        # Testar busca por diferentes chaves
        test_keys = [
            "valor do rodizio",
            "rodizio",
            "valores",
            "preco",
            "preços",
            "horario de atendimento",
            "horario",
            "funcionamento"
        ]
        
        for key in test_keys:
            result = agent._wrappers["get_business_knowledge"](key)
            if result:
                logger.info(f"✅ Key '{key}': {result[:100]}...")
            else:
                logger.warning(f"❌ Key '{key}': Nada encontrado")
        
    except Exception as e:
        logger.error(f"❌ Erro durante teste: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    test_knowledge_loading() 