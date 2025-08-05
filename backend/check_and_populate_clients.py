#!/usr/bin/env python3
"""
Script para verificar e popular dados de clientes de teste
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from models import Mensagem, Empresa
from config import Config

def check_and_populate_clients():
    """Verifica se há dados de clientes e popula dados de teste se necessário"""
    
    # Criar engine e session
    engine = create_engine(Config.POSTGRES_URL)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        # Buscar empresa TinyTeams
        empresa = session.query(Empresa).filter(Empresa.slug == 'tinyteams').first()
        
        if not empresa:
            print("❌ Empresa TinyTeams não encontrada. Execute init_db.py primeiro.")
            return
        
        print(f"✅ Empresa encontrada: {empresa.nome} (ID: {empresa.id})")
        
        # Verificar se há mensagens para esta empresa
        mensagens_count = session.query(Mensagem).filter(Mensagem.empresa_id == empresa.id).count()
        print(f"📊 Total de mensagens na empresa: {mensagens_count}")
        
        # Verificar clientes únicos
        clientes_unicos = session.query(func.count(func.distinct(Mensagem.cliente_id))).filter(
            Mensagem.empresa_id == empresa.id
        ).scalar()
        print(f"👥 Clientes únicos: {clientes_unicos}")
        
        if mensagens_count == 0:
            print("📝 Populando dados de teste...")
            
            # Criar mensagens de teste
            mensagens_teste = [
                # Cliente 1 - Conversa sobre desenvolvimento
                {
                    "cliente_id": "5511999999999",
                    "text": "Olá! Preciso de ajuda com desenvolvimento de software",
                    "is_bot": False,
                    "timestamp": datetime.now() - timedelta(hours=2)
                },
                {
                    "cliente_id": "5511999999999", 
                    "text": "Olá! Sou o assistente da TinyTeams. Como posso ajudar com desenvolvimento de software?",
                    "is_bot": True,
                    "timestamp": datetime.now() - timedelta(hours=2, minutes=1)
                },
                {
                    "cliente_id": "5511999999999",
                    "text": "Quero desenvolver um sistema de gestão",
                    "is_bot": False,
                    "timestamp": datetime.now() - timedelta(hours=1, minutes=30)
                },
                {
                    "cliente_id": "5511999999999",
                    "text": "Ótimo! Posso ajudar com isso. Que tipo de sistema você precisa?",
                    "is_bot": True,
                    "timestamp": datetime.now() - timedelta(hours=1, minutes=29)
                },
                
                # Cliente 2 - Conversa sobre reserva
                {
                    "cliente_id": "5511888888888",
                    "text": "Oi! Quero fazer uma reserva para reunião",
                    "is_bot": False,
                    "timestamp": datetime.now() - timedelta(hours=4)
                },
                {
                    "cliente_id": "5511888888888",
                    "text": "Olá! Posso ajudar com sua reserva. Que data você gostaria?",
                    "is_bot": True,
                    "timestamp": datetime.now() - timedelta(hours=4, minutes=1)
                },
                {
                    "cliente_id": "5511888888888",
                    "text": "Amanhã às 14h",
                    "is_bot": False,
                    "timestamp": datetime.now() - timedelta(hours=3, minutes=45)
                },
                {
                    "cliente_id": "5511888888888",
                    "text": "Perfeito! Reserva confirmada para amanhã às 14h",
                    "is_bot": True,
                    "timestamp": datetime.now() - timedelta(hours=3, minutes=44)
                },
                
                # Cliente 3 - Conversa sobre atendimento
                {
                    "cliente_id": "5511777777777",
                    "text": "Preciso de suporte técnico",
                    "is_bot": False,
                    "timestamp": datetime.now() - timedelta(hours=6)
                },
                {
                    "cliente_id": "5511777777777",
                    "text": "Olá! Estou aqui para ajudar com suporte técnico. Qual é o problema?",
                    "is_bot": True,
                    "timestamp": datetime.now() - timedelta(hours=6, minutes=1)
                },
                {
                    "cliente_id": "5511777777777",
                    "text": "Meu sistema não está funcionando",
                    "is_bot": False,
                    "timestamp": datetime.now() - timedelta(hours=5, minutes=30)
                },
                {
                    "cliente_id": "5511777777777",
                    "text": "Vou te ajudar a resolver isso. Pode me dar mais detalhes?",
                    "is_bot": True,
                    "timestamp": datetime.now() - timedelta(hours=5, minutes=29)
                }
            ]
            
            # Inserir mensagens
            for msg_data in mensagens_teste:
                mensagem = Mensagem(
                    empresa_id=empresa.id,
                    cliente_id=msg_data["cliente_id"],
                    text=msg_data["text"],
                    is_bot=msg_data["is_bot"],
                    timestamp=msg_data["timestamp"]
                )
                session.add(mensagem)
            
            session.commit()
            print(f"✅ {len(mensagens_teste)} mensagens de teste criadas!")
            
            # Verificar novamente
            mensagens_count = session.query(Mensagem).filter(Mensagem.empresa_id == empresa.id).count()
            clientes_unicos = session.query(func.count(func.distinct(Mensagem.cliente_id))).filter(
                Mensagem.empresa_id == empresa.id
            ).scalar()
            
            print(f"📊 Após população - Mensagens: {mensagens_count}, Clientes únicos: {clientes_unicos}")
        else:
            print("✅ Já existem dados de clientes no banco!")
            
            # Mostrar detalhes dos clientes existentes
            clientes = session.query(
                Mensagem.cliente_id,
                func.max(Mensagem.timestamp).label('ultima_atividade'),
                func.count(Mensagem.id).label('total_mensagens')
            ).filter(
                Mensagem.empresa_id == empresa.id
            ).group_by(
                Mensagem.cliente_id
            ).all()
            
            print("\n📋 Clientes encontrados:")
            for cliente in clientes:
                print(f"  - {cliente.cliente_id}: {cliente.total_mensagens} mensagens (última: {cliente.ultima_atividade})")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    print("🔍 Verificando dados de clientes...")
    check_and_populate_clients() 