#!/usr/bin/env python3
"""
Script para atualizar a API Trinks com campos obrigatórios corretos
"""

import sys
import os
from pathlib import Path

# Adicionar o diretório backend ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.trinks_parser import trinks_parser
from models import API
from sqlalchemy import create_engine, text
from config import Config
import json

def update_trinks_api():
    """Atualiza a API Trinks com informações corretas"""
    
    print("🚀 Atualizando API Trinks com campos obrigatórios...")
    
    try:
        # 1. Conectar ao banco
        engine = create_engine(Config.POSTGRES_URL)
        
        with engine.connect() as conn:
            # 2. Buscar API Trinks existente
            result = conn.execute(text("""
                SELECT id, nome, schema_cache, ativo 
                FROM apis 
                WHERE nome ILIKE '%trinks%' OR nome ILIKE '%Trinks%'
                ORDER BY id DESC
                LIMIT 1
            """))
            
            api = result.fetchone()
            if not api:
                print("❌ Nenhuma API Trinks encontrada no banco")
                return
            
            api_id = api[0]
            api_nome = api[1]
            current_schema = api[2]
            is_ativo = api[3]
            
            print(f"🔍 API encontrada: {api_nome} (ID: {api_id})")
            print(f"   Status atual: {'Ativo' if is_ativo else 'Inativo'}")
            
            # 3. Parse da documentação da Trinks
            print("\n📚 Fazendo parse da documentação da Trinks...")
            trinks_info = trinks_parser.parse_trinks_docs()
            
            print(f"✅ Parse concluído: {len(trinks_info['endpoints'])} endpoints")
            
            # 4. Mostrar campos obrigatórios descobertos
            print("\n📋 Campos obrigatórios descobertos:")
            for endpoint in trinks_info['endpoints']:
                if endpoint['required_fields']:
                    print(f"  {endpoint['method']} {endpoint['path']}")
                    for field in endpoint['required_fields']:
                        print(f"    ✅ {field['name']}: {field['type']} - {field['description']}")
            
            # 5. Atualizar a API no banco
            print(f"\n💾 Atualizando API no banco...")
            
            # Converter para JSON para armazenar no banco
            schema_json = json.dumps(trinks_info, ensure_ascii=False, indent=2)
            
            # Atualizar schema_cache
            update_result = conn.execute(text("""
                UPDATE apis 
                SET schema_cache = :schema, 
                    ativo = true,
                    updated_at = NOW()
                WHERE id = :api_id
            """), {
                "schema": schema_json,
                "api_id": api_id
            })
            
            conn.commit()
            
            print(f"✅ API Trinks atualizada com sucesso!")
            print(f"   Endpoints: {len(trinks_info['endpoints'])}")
            print(f"   Campos obrigatórios: {sum(len(ep['required_fields']) for ep in trinks_info['endpoints'])}")
            
            # 6. Gerar especificação OpenAPI
            openapi_spec = trinks_parser.generate_openapi_spec(trinks_info)
            
            # Salvar especificação OpenAPI em arquivo
            openapi_file = Path("trinks_openapi_spec.json")
            with open(openapi_file, 'w', encoding='utf-8') as f:
                json.dump(openapi_spec, f, ensure_ascii=False, indent=2)
            
            print(f"📄 Especificação OpenAPI salva em: {openapi_file}")
            
            # 7. Mostrar resumo final
            print("\n🎯 Resumo da Atualização:")
            print(f"   API: {api_nome}")
            print(f"   ID: {api_id}")
            print(f"   Endpoints: {len(trinks_info['endpoints'])}")
            print(f"   Status: Ativo")
            print(f"   Schema: Atualizado com campos obrigatórios")
            
            return trinks_info
            
    except Exception as e:
        print(f"❌ Erro ao atualizar API Trinks: {e}")
        import traceback
        traceback.print_exc()
        return None

def show_trinks_endpoints():
    """Mostra todos os endpoints da Trinks com campos obrigatórios"""
    
    print("🔍 Mostrando endpoints da Trinks atualizados...")
    
    try:
        # Conectar ao banco
        engine = create_engine(Config.POSTGRES_URL)
        
        with engine.connect() as conn:
            # Buscar API Trinks
            result = conn.execute(text("""
                SELECT id, nome, schema_cache 
                FROM apis 
                WHERE nome ILIKE '%trinks%' OR nome ILIKE '%Trinks%'
                ORDER BY id DESC
                LIMIT 1
            """))
            
            api = result.fetchone()
            if not api:
                print("❌ Nenhuma API Trinks encontrada")
                return
            
            api_id = api[0]
            api_nome = api[1]
            schema_cache = api[2]
            
            print(f"📋 API: {api_nome} (ID: {api_id})")
            print("=" * 50)
            
            if schema_cache and isinstance(schema_cache, dict):
                endpoints = schema_cache.get('endpoints', [])
                
                for endpoint in endpoints:
                    print(f"\n🔗 {endpoint['method']} {endpoint['path']}")
                    print(f"   📝 {endpoint['description']}")
                    
                    if endpoint.get('required_fields'):
                        print("   ✅ Campos obrigatórios:")
                        for field in endpoint['required_fields']:
                            print(f"      • {field['name']}: {field['type']} - {field['description']}")
                    
                    if endpoint.get('optional_fields'):
                        print("   🔧 Campos opcionais:")
                        for field in endpoint['optional_fields']:
                            print(f"      • {field['name']}: {field['type']} - {field['description']}")
                    
                    if not endpoint.get('required_fields') and not endpoint.get('optional_fields'):
                        print("   ℹ️  Sem parâmetros")
                    
                    print("   " + "-" * 40)
                
                print(f"\n📊 Total: {len(endpoints)} endpoints")
                
            else:
                print("❌ Schema não encontrado ou inválido")
                
    except Exception as e:
        print(f"❌ Erro ao mostrar endpoints: {e}")

if __name__ == "__main__":
    print("🚀 Script de Atualização da API Trinks")
    print("=" * 50)
    
    # Atualizar API
    trinks_info = update_trinks_api()
    
    if trinks_info:
        print("\n" + "=" * 50)
        # Mostrar endpoints atualizados
        show_trinks_endpoints()
    
    print("\n✨ Script finalizado!") 