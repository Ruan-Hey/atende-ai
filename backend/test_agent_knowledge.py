#!/usr/bin/env python3
"""
Teste para verificar se o agente está conseguindo consumir o conhecimento da empresa TinyTeams
"""
import asyncio
import logging
import sys
import os

# Adicionar o diretório atual ao path para imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Empresa, Base
from agents.base_agent import BaseAgent
import json

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_session():
    """Cria uma sessão do banco de dados"""
    try:
        # Usar variáveis de ambiente ou configuração padrão
        database_url = "postgresql://postgres:postgres@localhost:5432/atende_ai"
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
                        logger.info(f"   📝 Item {i+1}: {title} (key: {key})")
            else:
                logger.warning("⚠️  Campo 'items' não é uma lista")
        else:
            logger.warning("⚠️  Estrutura de knowledge inválida")
        
        return tinyteams
        
    except Exception as e:
        logger.error(f"❌ Erro ao verificar conhecimento: {e}")
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

async def test_agent_knowledge_consumption():
    """Testa se o agente consegue consumir o conhecimento da TinyTeams"""
    logger.info("🧪 Testando consumo de conhecimento pelo agente...")
    
    # Primeiro, garantir que existe conhecimento
    if not create_test_knowledge():
        logger.error("❌ Não foi possível criar conhecimento de teste")
        return
    
    # Verificar conhecimento
    tinyteams = check_tinyteams_knowledge()
    if not tinyteams:
        logger.error("❌ Não foi possível verificar conhecimento da TinyTeams")
        return
    
    # Configuração do agente (simulada)
    empresa_config = {
        'empresa_id': tinyteams.id,
        'slug': tinyteams.slug,
        'nome': tinyteams.nome,
        'openai_key': 'test-key',  # Chave de teste
        'knowledge_json': tinyteams.knowledge_json
    }
    
    try:
        # Criar agente
        logger.info("🤖 Criando agente...")
        agent = BaseAgent(empresa_config)
        logger.info("✅ Agente criado com sucesso")
        
        # Testar acesso ao conhecimento
        logger.info("🔍 Testando acesso ao conhecimento...")
        
        # Testar diferentes chaves
        test_keys = ['horario', 'servicos', 'cancelamento', 'pagamento']
        
        for key in test_keys:
            try:
                # Usar o wrapper diretamente
                knowledge_wrapper = agent._wrappers.get('get_business_knowledge')
                if knowledge_wrapper:
                    result = knowledge_wrapper(key)
                    if result:
                        logger.info(f"✅ Conhecimento encontrado para '{key}': {result[:100]}...")
                    else:
                        logger.warning(f"⚠️  Nenhum conhecimento encontrado para '{key}'")
                else:
                    logger.error(f"❌ Wrapper de conhecimento não encontrado")
                    break
                    
            except Exception as e:
                logger.error(f"❌ Erro ao buscar conhecimento para '{key}': {e}")
        
        # Testar com aliases
        logger.info("🔍 Testando com aliases...")
        alias_tests = ['funcionamento', 'o que fazemos', 'cancelar', 'pagar']
        
        for alias in alias_tests:
            try:
                knowledge_wrapper = agent._wrappers.get('get_business_knowledge')
                if knowledge_wrapper:
                    result = knowledge_wrapper(alias)
                    if result:
                        logger.info(f"✅ Conhecimento encontrado para alias '{alias}': {result[:100]}...")
                    else:
                        logger.warning(f"⚠️  Nenhum conhecimento encontrado para alias '{alias}'")
                        
            except Exception as e:
                logger.error(f"❌ Erro ao buscar conhecimento para alias '{alias}': {e}")
        
        # Testar com chave inexistente
        logger.info("🔍 Testando com chave inexistente...")
        try:
            knowledge_wrapper = agent._wrappers.get('get_business_knowledge')
            if knowledge_wrapper:
                result = knowledge_wrapper('chave_inexistente')
                if not result:
                    logger.info("✅ Comportamento correto: nenhum conhecimento para chave inexistente")
                else:
                    logger.warning(f"⚠️  Conhecimento inesperado encontrado: {result}")
        except Exception as e:
            logger.error(f"❌ Erro ao testar chave inexistente: {e}")
        
        logger.info("✅ Teste de consumo de conhecimento concluído!")
        
    except Exception as e:
        logger.error(f"❌ Erro ao testar agente: {e}")

async def test_agent_with_real_message():
    """Testa o agente com uma mensagem real que deveria usar conhecimento"""
    logger.info("🧪 Testando agente com mensagem real...")
    
    # Verificar conhecimento
    tinyteams = check_tinyteams_knowledge()
    if not tinyteams:
        logger.error("❌ Não foi possível verificar conhecimento da TinyTeams")
        return
    
    # Configuração do agente
    empresa_config = {
        'empresa_id': tinyteams.id,
        'slug': tinyteams.slug,
        'nome': tinyteams.nome,
        'openai_key': 'test-key',
        'knowledge_json': tinyteams.knowledge_json
    }
    
    try:
        # Criar agente
        agent = BaseAgent(empresa_config)
        
        # Mensagens de teste que deveriam usar conhecimento
        test_messages = [
            "Qual é o horário de funcionamento da empresa?",
            "Quais serviços vocês oferecem?",
            "Como funciona a política de cancelamento?",
            "Quais são as formas de pagamento aceitas?",
            "Posso cancelar um agendamento?",
            "Vocês aceitam cartão de crédito?"
        ]
        
        for message in test_messages:
            logger.info(f"📝 Testando mensagem: '{message}'")
            
            try:
                # Simular contexto
                context = {
                    'cliente_id': 'teste_123',
                    'empresa': 'tinyteams'
                }
                
                # Processar mensagem
                response = await agent.process_message(message, context)
                
                if response:
                    logger.info(f"✅ Resposta do agente: {response[:200]}...")
                    
                    # Verificar se a resposta contém informações do conhecimento
                    knowledge_items = ['8h às 18h', 'desenvolvimento', '24h antes', 'PIX', 'cartão']
                    found_knowledge = any(item in response for item in knowledge_items)
                    
                    if found_knowledge:
                        logger.info("✅ Resposta contém conhecimento da empresa!")
                    else:
                        logger.warning("⚠️  Resposta não parece conter conhecimento específico da empresa")
                        
                else:
                    logger.warning("⚠️  Agente não retornou resposta")
                    
            except Exception as e:
                logger.error(f"❌ Erro ao processar mensagem '{message}': {e}")
        
        logger.info("✅ Teste com mensagens reais concluído!")
        
    except Exception as e:
        logger.error(f"❌ Erro ao testar agente com mensagens reais: {e}")

async def main():
    """Função principal"""
    logger.info("🚀 Iniciando testes de conhecimento do agente...")
    
    # Teste 1: Verificar conhecimento
    logger.info("\n" + "="*50)
    logger.info("TESTE 1: Verificação de Conhecimento")
    logger.info("="*50)
    check_tinyteams_knowledge()
    
    # Teste 2: Consumo de conhecimento pelo agente
    logger.info("\n" + "="*50)
    logger.info("TESTE 2: Consumo de Conhecimento pelo Agente")
    logger.info("="*50)
    await test_agent_knowledge_consumption()
    
    # Teste 3: Agente com mensagens reais
    logger.info("\n" + "="*50)
    logger.info("TESTE 3: Agente com Mensagens Reais")
    logger.info("="*50)
    await test_agent_with_real_message()
    
    logger.info("\n🎉 Todos os testes concluídos!")

if __name__ == "__main__":
    asyncio.run(main()) 