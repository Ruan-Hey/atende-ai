#!/usr/bin/env python3
"""
Teste melhorado de notificações - simula erro em conversa real com contexto
"""

import sys
import os

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_notification_with_conversation_context():
    """Testa notificação com contexto de conversa real"""
    
    print("🧪 TESTE MELHORADO DE NOTIFICAÇÕES - COM CONTEXTO DE CONVERSA")
    print("=" * 70)
    
    try:
        # Importar módulos necessários
        from models import Log, Cliente, Mensagem
        from main import save_log_to_db, SessionLocal
        from datetime import datetime
        
        print("✅ Módulos importados com sucesso!")
        
        # Criar sessão do banco
        session = SessionLocal()
        
        try:
            # 🆕 SIMULAR CONVERSA REAL
            empresa_id = 4  # ginestetica
            waid = "5511999999999"  # WhatsApp ID simulado
            cliente_nome = "João Silva"
            
            print(f"🏢 Empresa ID: {empresa_id}")
            print(f"📱 WhatsApp ID: {waid}")
            print(f"👤 Cliente: {cliente_nome}")
            
            # 🆕 CRIAR/ATUALIZAR CLIENTE
            cliente = session.query(Cliente).filter(
                Cliente.empresa_id == empresa_id,
                Cliente.cliente_id == waid
            ).first()
            
            if not cliente:
                cliente = Cliente(
                    empresa_id=empresa_id,
                    cliente_id=waid,
                    nome=cliente_nome
                )
                session.add(cliente)
                session.commit()
                print(f"✅ Cliente criado: {cliente.id}")
            else:
                print(f"✅ Cliente encontrado: {cliente.id}")
            
            # 🆕 CRIAR MENSAGEM SIMULADA
            mensagem = Mensagem(
                empresa_id=empresa_id,
                cliente_id=waid,
                text="Quero agendar um horário para amanhã às 14h para fazer uma limpeza de pele",
                is_bot=False
            )
            session.add(mensagem)
            session.commit()
            print(f"✅ Mensagem criada: {mensagem.id}")
            
            # 🆕 SIMULAR ERRO COM CONTEXTO DA CONVERSA
            error_msg = "Erro no fluxo Trinks: service_id não fornecido para agendamento de limpeza de pele"
            error_details = {
                'tool': 'trinks_booking',
                'error_type': 'missing_service_id',
                'user_message': 'Quero agendar um horário para amanhã às 14h para fazer uma limpeza de pele',
                'waid': waid,  # 🆕 IMPORTANTE: Incluir waid para contexto
                'cliente_nome': cliente_nome,
                'test': True,
                'conversa_context': True
            }
            
            print(f"📝 Mensagem de erro: {error_msg}")
            print(f"🔍 Detalhes: {error_details}")
            
            # 🆕 SALVAR ERRO NO BANCO (vai disparar notificação enriquecida)
            save_log_to_db(session, empresa_id, 'ERROR', error_msg, error_details)
            
            print("✅ Erro salvo no banco com sucesso!")
            print("🔔 Notificação enriquecida deveria ter sido disparada!")
            
            # 🆕 VERIFICAR SE FOI SALVO
            log_entry = session.query(Log).filter(
                Log.empresa_id == empresa_id,
                Log.level == 'ERROR',
                Log.message == error_msg
            ).first()
            
            if log_entry:
                print(f"✅ Log encontrado no banco: ID {log_entry.id}")
                print(f"📊 Detalhes do log: {log_entry.details}")
            else:
                print("❌ Log não encontrado no banco")
            
            # 🆕 VERIFICAR TABELA DE NOTIFICAÇÕES
            try:
                from notifications.models import NotificationLog
                notification_logs = session.query(NotificationLog).filter(
                    NotificationLog.tipo == 'agente_error'
                ).order_by(NotificationLog.created_at.desc()).limit(5).all()
                
                if notification_logs:
                    print(f"✅ {len(notification_logs)} logs de notificação encontrados!")
                    for log in notification_logs:
                        print(f"   📋 {log.titulo} - {log.created_at}")
                        if log.dados_contexto:
                            print(f"      🔗 Rota: {log.dados_contexto.get('rota_conversa', 'N/A')}")
                            print(f"      👤 Cliente: {log.dados_contexto.get('cliente_info', {}).get('nome', 'N/A')}")
                else:
                    print("ℹ️ Nenhum log de notificação encontrado ainda")
                    
            except Exception as e:
                print(f"⚠️ Erro ao verificar logs de notificação: {e}")
            
        finally:
            session.close()
            
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🎯 PRÓXIMOS PASSOS:")
    print("1. Verifique os logs do backend para notificações enriquecidas")
    print("2. Verifique a tabela notifications.notification_logs")
    print("3. Verifique se a notificação tem contexto da conversa")
    print("4. Teste clicando na notificação para ir direto para a conversa")
    print("=" * 70)

if __name__ == "__main__":
    test_notification_with_conversation_context()
