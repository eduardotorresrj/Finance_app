#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🧪 TESTE DE TEMPLATE - FINANCE APP
Script para testar especificamente o template forgot_password.html
"""

import sys
import os

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_template():
    """Testa se o template pode ser renderizado"""
    print("🧪 TESTE DE TEMPLATE")
    print("=" * 50)
    
    try:
        from app import app
        
        with app.app_context():
            print("📦 Tentando renderizar forgot_password.html...")
            
            # Testar renderização do template
            rendered = app.jinja_env.get_template('forgot_password.html').render()
            print("✅ Template renderizado com sucesso!")
            
            # Verificar se há algum problema com url_for
            print("📦 Testando url_for...")
            
            from flask import url_for
            
            try:
                forgot_url = url_for('forgot_password')
                print(f"✅ forgot_password URL: {forgot_url}")
            except Exception as e:
                print(f"❌ forgot_password URL: {e}")
            
            try:
                verify_url = url_for('verify_code')
                print(f"✅ verify_code URL: {verify_url}")
            except Exception as e:
                print(f"❌ verify_code URL: {e}")
            
            try:
                login_url = url_for('login')
                print(f"✅ login URL: {login_url}")
            except Exception as e:
                print(f"❌ login URL: {e}")
            
            return True
            
    except Exception as e:
        print(f"❌ Erro no teste de template: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_verify_template():
    """Testa se o template verify_code.html pode ser renderizado"""
    print("\n🧪 TESTE DE TEMPLATE VERIFY_CODE")
    print("=" * 50)
    
    try:
        from app import app
        
        with app.app_context():
            print("📦 Tentando renderizar verify_code.html...")
            
            # Testar renderização do template
            rendered = app.jinja_env.get_template('verify_code.html').render()
            print("✅ Template renderizado com sucesso!")
            
            return True
            
    except Exception as e:
        print(f"❌ Erro no teste de template: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_reset_template():
    """Testa se o template reset_password.html pode ser renderizado"""
    print("\n🧪 TESTE DE TEMPLATE RESET_PASSWORD")
    print("=" * 50)
    
    try:
        from app import app
        
        with app.app_context():
            print("📦 Tentando renderizar reset_password.html...")
            
            # Testar renderização do template com email
            rendered = app.jinja_env.get_template('reset_password.html').render(email="teste@exemplo.com")
            print("✅ Template renderizado com sucesso!")
            
            return True
            
    except Exception as e:
        print(f"❌ Erro no teste de template: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal"""
    print("🧪 TESTE COMPLETO DE TEMPLATES")
    print("=" * 60)
    
    # Teste 1: Template forgot_password
    forgot_ok = test_template()
    
    # Teste 2: Template verify_code
    verify_ok = test_verify_template()
    
    # Teste 3: Template reset_password
    reset_ok = test_reset_template()
    
    # Resumo
    print("\n📊 RESUMO:")
    print("=" * 60)
    
    if forgot_ok and verify_ok and reset_ok:
        print("🎉 TODOS OS TESTES PASSARAM!")
        print("✅ forgot_password.html OK")
        print("✅ verify_code.html OK")
        print("✅ reset_password.html OK")
        print("\n💡 O problema pode ser:")
        print("   - Cache do navegador")
        print("   - Servidor não reiniciado")
        print("   - Erro específico no contexto da requisição")
    else:
        print("❌ ALGUNS TESTES FALHARAM")
        print("🔧 Verifique os erros acima")

if __name__ == "__main__":
    main() 