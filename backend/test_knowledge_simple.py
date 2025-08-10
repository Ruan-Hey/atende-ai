#!/usr/bin/env python3
"""
Teste simples para verificar se a empresa TinyTeams tem conhecimento cadastrado
"""
import asyncio
import logging
import sys
import os
import json

# Adicionar o diretório atual ao path para imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Empresa, Base

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_session():
    """Cria uma sessão do banco de dados"""
    try:
        # Usar configuração de produção do Render
        database_url = "postgresql://atendeai:2pjZBzhDlZY275Z4FubsnBFPsjvLHNRw@dpg-d24vpfngi27c73bh06n0-a.oregon-postgres.render.com/atendeai"
        engine = create_engine(database_url)
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return SessionLocal()
    except Exception as e:
        logger.error(f"❌ Erro ao conectar ao banco: {e}")
        return None

def check_tinyteams_knowledge():
    """Verifica se a TinyTeams tem conhecimento cadastrado"""
    session = get_database_session()
    if not session:
        return None
    
    try:
        # Buscar TinyTeams
        tinyteams = session.query(Empresa).filter(Empresa.slug == 'tinyteams').first()
        
        if not tinyteams:
            logger.error("❌ Empresa TinyTeams não encontrada!")
            return None
        
        logger.info(f"✅ TinyTeams encontrada: ID={tinyteams.id}")
        logger.info(f"📖 Nome: {tinyteams.nome}")
        
        # Verificar conhecimento
        knowledge = tinyteams.knowledge_json
        if not knowledge:
            logger.warning("⚠️  TinyTeams não tem conhecimento cadastrado (knowledge_json está vazio)")
            return None
        
        logger.info(f"📚 Knowledge JSON encontrado: {json.dumps(knowledge, indent=2, ensure_ascii=False)}")
        
        # Verificar estrutura
        if isinstance(knowledge, dict) and 'items' in knowledge:
            items = knowledge['items']
            if isinstance(items, list):
                logger.info(f"✅ Estrutura válida: {len(items)} itens de conhecimento encontrados")
                for i, item in enumerate(items):
                    if isinstance(item, dict):
                        title = item.get('title', 'Sem título')
                        key = item.get('key', 'Sem chave')
                        description = item.get('description', 'Sem descrição')
                        aliases = item.get('aliases', [])
                        logger.info(f"   📝 Item {i+1}: {title}")
                        logger.info(f"      🔑 Key: {key}")
                        logger.info(f"      📖 Descrição: {description[:100]}...")
                        if aliases:
                            logger.info(f"      🏷️  Aliases: {', '.join(aliases)}")
            else:
                logger.warning("⚠️  Campo 'items' não é uma lista")
        else:
            logger.warning("⚠️  Estrutura de knowledge inválida")
        
        return tinyteams
        
    except Exception as e:
        logger.error(f"❌ Erro ao verificar conhecimento: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        session.close()

def create_test_knowledge():
    """Cria conhecimento de teste para a TinyTeams se não existir"""
    session = get_database_session()
    if not session:
        return False
    
    try:
        tinyteams = session.query(Empresa).filter(Empresa.slug == 'tinyteams').first()
        if not tinyteams:
            logger.error("❌ TinyTeams não encontrada")
            return False
        
        # Verificar se já tem conhecimento
        if tinyteams.knowledge_json and isinstance(tinyteams.knowledge_json, dict) and tinyteams.knowledge_json.get('items'):
            logger.info("✅ TinyTeams já tem conhecimento cadastrado")
            return True
        
        # Criar conhecimento de teste
        test_knowledge = {
            "items": [
                {
                    "title": "Horário de Funcionamento",
                    "key": "horario",
                    "description": "A TinyTeams funciona de segunda a sexta, das 8h às 18h, e aos sábados das 9h às 13h.",
                    "aliases": ["funcionamento", "horários", "expediente"]
                },
                {
                    "title": "Serviços Oferecidos",
                    "key": "servicos",
                    "description": "Oferecemos desenvolvimento de software, consultoria em TI, suporte técnico e treinamentos.",
                    "aliases": ["o que fazemos", "produtos", "soluções"]
                },
                {
                    "title": "Política de Cancelamento",
                    "key": "cancelamento",
                    "description": "Cancelamentos podem ser feitos até 24h antes do agendamento sem custos adicionais.",
                    "aliases": ["cancelar", "desmarcar", "política"]
                },
                {
                    "title": "Formas de Pagamento",
                    "key": "pagamento",
                    "description": "Aceitamos PIX, cartão de crédito/débito, boleto bancário e transferência bancária.",
                    "aliases": ["pagar", "meios de pagamento", "cartão", "pix"]
                }
            ]
        }
        
        tinyteams.knowledge_json = test_knowledge
        session.commit()
        
        logger.info("✅ Conhecimento de teste criado para TinyTeams")
        logger.info(f"📚 {len(test_knowledge['items'])} itens adicionados")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar conhecimento: {e}")
        session.rollback()
        return False
    finally:
        session.close()

def test_knowledge_search():
    """Testa a busca de conhecimento simulando o comportamento do agente"""
    logger.info("🧪 Testando busca de conhecimento...")
    
    session = get_database_session()
    if not session:
        return
    
    try:
        tinyteams = session.query(Empresa).filter(Empresa.slug == 'tinyteams').first()
        if not tinyteams:
            logger.error("❌ TinyTeams não encontrada")
            return
        
        knowledge = tinyteams.knowledge_json
        if not knowledge:
            logger.error("❌ Nenhum conhecimento encontrado")
            return
        
        # Simular a função de busca do agente
        def get_business_knowledge(key: str) -> str:
            try:
                if not key:
                    return "Parâmetros ausentes: forneça key"
                
                knowledge_items = knowledge.get('items') if isinstance(knowledge, dict) else []
                if not isinstance(knowledge_items, list):
                    return ""
                
                # Matching por key exata
                found = None
                for item in knowledge_items:
                    if isinstance(item, dict) and item.get('key') == key:
                        found = item
                        break
                
                # Fallback por title case-insensitive
                if not found:
                    for item in knowledge_items:
                        if isinstance(item, dict) and item.get('title', '').strip().lower() == key.strip().lower():
                            found = item
                            break
                
                # Fallback por aliases
                if not found and isinstance(key, str):
                    for item in knowledge_items:
                        aliases = item.get('aliases', []) if isinstance(item, dict) else []
                        if isinstance(aliases, list) and any(a.strip().lower() == key.strip().lower() for a in aliases if isinstance(a, str)):
                            found = item
                            break
                
                if not found:
                    return ""
                
                return found.get('description') or ""
                
            except Exception as e:
                logger.error(f"Erro na busca: {e}")
                return ""
        
        # Testar diferentes chaves
        test_keys = ['horario', 'servicos', 'cancelamento', 'pagamento']
        
        for key in test_keys:
            result = get_business_knowledge(key)
            if result:
                logger.info(f"✅ Conhecimento encontrado para '{key}': {result[:100]}...")
            else:
                logger.warning(f"⚠️  Nenhum conhecimento encontrado para '{key}'")
        
        # Testar com aliases
        logger.info("🔍 Testando com aliases...")
        alias_tests = ['funcionamento', 'o que fazemos', 'cancelar', 'pagar']
        
        for alias in alias_tests:
            result = get_business_knowledge(alias)
            if result:
                logger.info(f"✅ Conhecimento encontrado para alias '{alias}': {result[:100]}...")
            else:
                logger.warning(f"⚠️  Nenhum conhecimento encontrado para alias '{alias}'")
        
        # Testar com chave inexistente
        logger.info("🔍 Testando com chave inexistente...")
        result = get_business_knowledge('chave_inexistente')
        if not result:
            logger.info("✅ Comportamento correto: nenhum conhecimento para chave inexistente")
        else:
            logger.warning(f"⚠️  Conhecimento inesperado encontrado: {result}")
        
        logger.info("✅ Teste de busca de conhecimento concluído!")
        
    except Exception as e:
        logger.error(f"❌ Erro ao testar busca de conhecimento: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

def main():
    """Função principal"""
    logger.info("🚀 Iniciando testes de conhecimento da TinyTeams...")
    
    # Teste 1: Verificar conhecimento
    logger.info("\n" + "="*50)
    logger.info("TESTE 1: Verificação de Conhecimento")
    logger.info("="*50)
    check_tinyteams_knowledge()
    
    # Teste 2: Criar conhecimento se necessário
    logger.info("\n" + "="*50)
    logger.info("TESTE 2: Criação de Conhecimento")
    logger.info("="*50)
    create_test_knowledge()
    
    # Teste 3: Verificar conhecimento novamente
    logger.info("\n" + "="*50)
    logger.info("TESTE 3: Verificação Pós-Criação")
    logger.info("="*50)
    check_tinyteams_knowledge()
    
    # Teste 4: Simular busca de conhecimento
    logger.info("\n" + "="*50)
    logger.info("TESTE 4: Simulação de Busca de Conhecimento")
    logger.info("="*50)
    test_knowledge_search()
    
    logger.info("\n🎉 Todos os testes concluídos!")

if __name__ == "__main__":
    main() 