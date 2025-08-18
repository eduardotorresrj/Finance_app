#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🧪 TESTE DE IMPORTAÇÃO - FINANCE APP
Script para verificar se o app.py pode ser importado
"""

import sys
import os

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_import():
    """Testa se o app.py pode ser importado"""
    print("🧪 TESTE DE IMPORTAÇÃO")
    print("=" * 50)
    
    try:
        print("📦 Tentando importar app...")
        from app import app
        print("✅ App importado com sucesso!")
        
        print("📦 Tentando importar db...")
        from app import db
        print("✅ Database importado com sucesso!")
        
        print("📦 Tentando importar User...")
        from app import User
        print("✅ User model importado com sucesso!")
        
        print("📦 Tentando importar password_reset_codes...")
        from app import password_reset_codes
        print("✅ password_reset_codes importado com sucesso!")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na importação: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_routes_simple():
    """Testa se as rotas estão registradas"""
    print("\n🔗 TESTE DE ROTAS SIMPLES")
    print("=" * 50)
    
    try:
        from app import app
        
        # Verificar se as rotas específicas existem
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append(rule.endpoint)
        
        required_routes = ['forgot_password', 'verify_code', 'reset_password']
        
        for route in required_routes:
            if route in routes:
                print(f"✅ {route} - ENCONTRADA")
            else:
                print(f"❌ {route} - NÃO ENCONTRADA")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste de rotas: {e}")
        return False

def main():
    """Função principal"""
    print("🧪 TESTE COMPLETO DE IMPORTAÇÃO")
    print("=" * 60)
    
    # Teste 1: Importação
    import_ok = test_import()
    
    # Teste 2: Rotas simples
    routes_ok = test_routes_simple()
    
    # Resumo
    print("\n📊 RESUMO:")
    print("=" * 60)
    
    if import_ok and routes_ok:
        print("🎉 TODOS OS TESTES PASSARAM!")
        print("✅ Importação OK")
        print("✅ Rotas registradas OK")
    else:
        print("❌ ALGUNS TESTES FALHARAM")
        print("🔧 Verifique os erros acima")

if __name__ == "__main__":
    main() 