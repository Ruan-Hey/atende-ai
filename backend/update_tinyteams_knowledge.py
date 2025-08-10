#!/usr/bin/env python3
"""
Script para atualizar o conhecimento da empresa TinyTeams
"""
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

def update_tinyteams_knowledge():
    """Atualiza o conhecimento da TinyTeams com informações mais completas"""
    session = get_database_session()
    if not session:
        return False
    
    try:
        # Buscar TinyTeams
        tinyteams = session.query(Empresa).filter(Empresa.slug == 'tinyteams').first()
        if not tinyteams:
            logger.error("❌ TinyTeams não encontrada")
            return False
        
        logger.info(f"✅ TinyTeams encontrada: ID={tinyteams.id}")
        logger.info(f"📖 Nome atual: {tinyteams.nome}")
        
        # Conhecimento atualizado e mais completo
        updated_knowledge = {
            "items": [
                {
                    "title": "Horário de Funcionamento",
                    "key": "horario",
                    "description": "A TinyTeams funciona de segunda a sexta, das 8h às 18h, e aos sábados das 9h às 13h. Em feriados não funcionamos.",
                    "aliases": ["funcionamento", "horários", "expediente", "quando funcionam", "dias úteis"],
                    "active": True
                },
                {
                    "title": "Serviços Oferecidos",
                    "key": "servicos",
                    "description": "Oferecemos desenvolvimento de software personalizado, consultoria em TI, suporte técnico especializado, treinamentos em equipe e integração de sistemas. Trabalhamos com as principais tecnologias do mercado.",
                    "aliases": ["o que fazemos", "produtos", "soluções", "tecnologias", "desenvolvimento", "consultoria"],
                    "active": True
                },
                {
                    "title": "Política de Cancelamento",
                    "key": "cancelamento",
                    "description": "Cancelamentos podem ser feitos até 24h antes do agendamento sem custos adicionais. Cancelamentos com menos de 24h de antecedência podem ter taxa de 50% do valor do serviço.",
                    "aliases": ["cancelar", "desmarcar", "política", "taxa cancelamento", "antecedência"],
                    "active": True
                },
                {
                    "title": "Formas de Pagamento",
                    "key": "pagamento",
                    "description": "Aceitamos PIX, cartão de crédito/débito (até 12x), boleto bancário e transferência bancária. Para projetos maiores, oferecemos parcelamento personalizado.",
                    "aliases": ["pagar", "meios de pagamento", "cartão", "pix", "boleto", "parcelamento", "transferência"],
                    "active": True
                },
                {
                    "title": "Tecnologias Utilizadas",
                    "key": "tecnologias",
                    "description": "Trabalhamos com React, Node.js, Python, Java, .NET, AWS, Azure, Docker, Kubernetes, e muitas outras tecnologias modernas. Sempre escolhemos a melhor stack para cada projeto.",
                    "aliases": ["tech stack", "linguagens", "frameworks", "cloud", "ferramentas", "stack tecnológico"],
                    "active": True
                },
                {
                    "title": "Processo de Desenvolvimento",
                    "key": "processo",
                    "description": "Seguimos metodologia ágil com sprints de 2 semanas, reuniões diárias, e entregas incrementais. Mantemos comunicação constante com o cliente durante todo o processo.",
                    "aliases": ["metodologia", "ágil", "sprints", "entregas", "comunicação", "desenvolvimento ágil"],
                    "active": True
                },
                {
                    "title": "Suporte Técnico",
                    "key": "suporte",
                    "description": "Oferecemos suporte técnico 24/7 para clientes premium, e suporte em horário comercial para demais clientes. Temos SLA de resposta de até 2 horas para casos críticos.",
                    "aliases": ["suporte 24h", "SLA", "resposta", "crítico", "premium", "horário comercial"],
                    "active": True
                },
                {
                    "title": "Preços e Orçamentos",
                    "key": "precos",
                    "description": "Nossos preços variam conforme a complexidade do projeto e tecnologias utilizadas. Oferecemos orçamento gratuito e sem compromisso. Entre em contato para uma avaliação personalizada.",
                    "aliases": ["orçamento", "preço", "custo", "avaliação", "gratuito", "sem compromisso"],
                    "active": True
                }
            ]
        }
        
        # Atualizar conhecimento
        tinyteams.knowledge_json = updated_knowledge
        session.commit()
        
        logger.info("✅ Conhecimento da TinyTeams atualizado com sucesso!")
        logger.info(f"📚 {len(updated_knowledge['items'])} itens de conhecimento")
        
        # Mostrar resumo
        for item in updated_knowledge['items']:
            logger.info(f"   📝 {item['title']} (key: {item['key']})")
            if item.get('aliases'):
                logger.info(f"      🏷️  Aliases: {', '.join(item['aliases'])}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao atualizar conhecimento: {e}")
        session.rollback()
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()

def main():
    """Função principal"""
    logger.info("🚀 Atualizando conhecimento da TinyTeams...")
    
    if update_tinyteams_knowledge():
        logger.info("🎉 Conhecimento atualizado com sucesso!")
    else:
        logger.error("❌ Falha ao atualizar conhecimento")

if __name__ == "__main__":
    main() 