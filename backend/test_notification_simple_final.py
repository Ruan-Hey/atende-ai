#!/usr/bin/env python3
"""
Teste FINAL SIMPLES de notificações - versão simplificada
"""

import sys
import os

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_simple_notification():
    """Testa notificação simplificada"""
    
    print("🧪 TESTE FINAL SIMPLES - NOTIFICAÇÕES SIMPLIFICADAS")
    print("=" * 60)
    
    try:
        # Importar módulos necessários
        from models import Log
        from agents.smart_agent import SmartAgent
        from main import SessionLocal
        
        print("✅ Módulos importados com sucesso!")
        
        # Criar sessão do banco
        session = SessionLocal()
        
        try:
            # 🆕 TESTE SIMPLES - SÓ O ESSENCIAL
            empresa_id = 4  # ginestetica
            waid = "554195984948"  # WhatsApp ID real da URL
            
            print(f"🏢 Empresa ID: {empresa_id}")
            print(f"📱 WhatsApp ID: {waid}")
            print(f"🔗 Rota esperada: /conversation/ginestetica/{waid}")
            
            # 🆕 CRIAR INSTÂNCIA DO SMARTAGENT
            empresa_config = {
                'empresa_id': empresa_id,
                'nome': 'ginestetica',
                'slug': 'ginestetica'
            }
            
            agent = SmartAgent(empresa_config)
            print("✅ SmartAgent criado com sucesso!")
            
            # 🆕 SIMULAR ERRO SIMPLES COM WAID
            error_msg = "Erro simples: Falha no fluxo Trinks"
            error_details = {
                'tool': 'trinks_booking',
                'waid': waid,  # 🆕 SÓ ISSO PARA CONTEXTO
                'test': True
            }
            
            print(f"📝 Mensagem de erro: {error_msg}")
            print(f"🔍 Detalhes: {error_details}")
            
            # 🆕 USAR O SMARTAGENT PARA SALVAR (vai disparar notificação automática)
            agent._save_log_to_db('ERROR', error_msg, error_details)
            
            print("✅ Erro salvo via SmartAgent com sucesso!")
            print("🔔 Notificação simplificada deveria ter sido disparada!")
            
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
            
        finally:
            session.close()
            
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🎯 RESULTADO ESPERADO:")
    print("1. ✅ Notificação simples enviada")
    print("2. ✅ Com rota direta para conversa")
    print("3. ✅ Sem consultas complexas no banco")
    print("4. ✅ Código limpo e simples")
    print("=" * 60)

if __name__ == "__main__":
    test_simple_notification()
