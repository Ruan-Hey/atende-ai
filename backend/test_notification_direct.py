#!/usr/bin/env python3
"""
Teste direto para disparar notificação simulando erro
"""
import sys
import os

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_notification_direct():
    """Testa notificação diretamente simulando erro"""
    
    print("🧪 TESTE DIRETO DE NOTIFICAÇÕES")
    print("=" * 50)
    
    try:
        # Importar módulos necessários
        from models import Log
        from main import save_log_to_db, SessionLocal
        
        print("✅ Módulos importados com sucesso!")
        
        # Criar sessão do banco
        session = SessionLocal()
        
        try:
            # Simular erro que deveria disparar notificação
            empresa_id = 1  # TinyTeams
            error_msg = "🧪 TESTE: Notificação disparada com sucesso!"
            error_details = {
                'tool': 'test_notification',
                'test': True,
                'message': 'Esta é uma notificação de teste!'
            }
            
            print(f"🏢 Empresa ID: {empresa_id}")
            print(f"📝 Mensagem de erro: {error_msg}")
            print(f"🔍 Detalhes: {error_details}")
            
            # Salvar erro no banco (vai disparar notificação automática)
            save_log_to_db(session, empresa_id, 'ERROR', error_msg, error_details)
            
            print("✅ Erro salvo no banco com sucesso!")
            print("🔔 Notificação deveria ter sido disparada automaticamente!")
            print("📱 Verifique se apareceu uma notificação no navegador!")
            
            # Verificar se foi salvo
            log_entry = session.query(Log).filter(
                Log.empresa_id == empresa_id,
                Log.level == 'ERROR',
                Log.message == error_msg
            ).first()
            
            if log_entry:
                print(f"✅ Log encontrado no banco: ID {log_entry.id}")
            else:
                print("❌ Log não encontrado no banco")
            
        finally:
            session.close()
            
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🎯 PRÓXIMOS PASSOS:")
    print("1. Verifique se apareceu uma notificação no navegador")
    print("2. Verifique os logs do backend")
    print("3. Verifique a tabela logs")
    print("=" * 50)

if __name__ == "__main__":
    test_notification_direct()
