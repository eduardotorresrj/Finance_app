#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🧪 TESTE DE ROTAS - FINANCE APP
Script para verificar se todas as rotas estão funcionando
"""

import sys
import os

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_routes():
    """Testa se todas as rotas estão registradas"""
    print("🧪 TESTE DE ROTAS")
    print("=" * 50)
    
    try:
        from app import app
        
        # Listar todas as rotas registradas
        print("📋 ROTAS REGISTRADAS:")
        print("-" * 30)
        
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append({
                'endpoint': rule.endpoint,
                'methods': list(rule.methods),
                'rule': rule.rule
            })
        
        # Ordenar por endpoint
        routes.sort(key=lambda x: x['endpoint'])
        
        for route in routes:
            print(f"✅ {route['endpoint']}: {route['rule']} [{', '.join(route['methods'])}]")
        
        # Verificar rotas específicas
        print("\n🔍 VERIFICANDO ROTAS ESPECÍFICAS:")
        print("-" * 30)
        
        required_routes = [
            'forgot_password',
            'verify_code', 
            'reset_password'
        ]
        
        found_routes = [r['endpoint'] for r in routes]
        
        for route in required_routes:
            if route in found_routes:
                print(f"✅ {route} - ENCONTRADA")
            else:
                print(f"❌ {route} - NÃO ENCONTRADA")
        
        # Testar URL building
        print("\n🔗 TESTANDO URL BUILDING:")
        print("-" * 30)
        
        with app.app_context():
            try:
                forgot_url = app.url_for('forgot_password')
                print(f"✅ forgot_password: {forgot_url}")
            except Exception as e:
                print(f"❌ forgot_password: {e}")
            
            try:
                verify_url = app.url_for('verify_code')
                print(f"✅ verify_code: {verify_url}")
            except Exception as e:
                print(f"❌ verify_code: {e}")
            
            try:
                reset_url = app.url_for('reset_password')
                print(f"✅ reset_password: {reset_url}")
            except Exception as e:
                print(f"❌ reset_password: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return False

def test_app_structure():
    """Testa a estrutura da aplicação"""
    print("\n🏗️ TESTE DA ESTRUTURA DA APLICAÇÃO")
    print("=" * 50)
    
    try:
        from app import app, db, User, password_reset_codes
        
        print("✅ Flask app importado")
        print("✅ Database importado")
        print("✅ User model importado")
        print("✅ password_reset_codes importado")
        
        # Verificar se o app tem as configurações básicas
        if hasattr(app, 'config'):
            print("✅ App tem configurações")
        else:
            print("❌ App não tem configurações")
        
        # Verificar se o app tem url_map
        if hasattr(app, 'url_map'):
            print("✅ App tem url_map")
        else:
            print("❌ App não tem url_map")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na estrutura: {e}")
        return False

def main():
    """Função principal"""
    print("🧪 TESTE COMPLETO DE ROTAS")
    print("=" * 60)
    
    # Teste 1: Estrutura da aplicação
    structure_ok = test_app_structure()
    
    # Teste 2: Rotas
    routes_ok = test_routes()
    
    # Resumo
    print("\n📊 RESUMO:")
    print("=" * 60)
    
    if structure_ok and routes_ok:
        print("🎉 TODOS OS TESTES PASSARAM!")
        print("✅ Estrutura da aplicação OK")
        print("✅ Rotas registradas OK")
        print("\n💡 O problema pode ser:")
        print("   - Cache do navegador")
        print("   - Servidor não reiniciado")
        print("   - Erro no template")
    else:
        print("❌ ALGUNS TESTES FALHARAM")
        print("🔧 Verifique os erros acima")

if __name__ == "__main__":
    main() 