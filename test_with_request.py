#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🧪 TESTE COM CONTEXTO DE REQUISIÇÃO - FINANCE APP
Script para testar templates com contexto de requisição
"""

import sys
import os

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_with_request_context():
    """Testa com contexto de requisição"""
    print("🧪 TESTE COM CONTEXTO DE REQUISIÇÃO")
    print("=" * 50)
    
    try:
        from app import app
        
        with app.test_request_context('/forgot_password'):
            print("📦 Testando forgot_password com contexto de requisição...")
            
            # Testar renderização do template
            rendered = app.jinja_env.get_template('forgot_password.html').render()
            print("✅ Template renderizado com sucesso!")
            
            # Testar url_for
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
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_verify_with_request_context():
    """Testa verify_code com contexto de requisição"""
    print("\n🧪 TESTE VERIFY_CODE COM CONTEXTO DE REQUISIÇÃO")
    print("=" * 50)
    
    try:
        from app import app
        
        with app.test_request_context('/verify_code'):
            print("📦 Testando verify_code com contexto de requisição...")
            
            # Testar renderização do template
            rendered = app.jinja_env.get_template('verify_code.html').render()
            print("✅ Template renderizado com sucesso!")
            
            return True
            
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_reset_with_request_context():
    """Testa reset_password com contexto de requisição"""
    print("\n🧪 TESTE RESET_PASSWORD COM CONTEXTO DE REQUISIÇÃO")
    print("=" * 50)
    
    try:
        from app import app
        
        with app.test_request_context('/reset_password'):
            print("📦 Testando reset_password com contexto de requisição...")
            
            # Testar renderização do template com email
            rendered = app.jinja_env.get_template('reset_password.html').render(email="teste@exemplo.com")
            print("✅ Template renderizado com sucesso!")
            
            return True
            
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal"""
    print("🧪 TESTE COMPLETO COM CONTEXTO DE REQUISIÇÃO")
    print("=" * 60)
    
    # Teste 1: forgot_password
    forgot_ok = test_with_request_context()
    
    # Teste 2: verify_code
    verify_ok = test_verify_with_request_context()
    
    # Teste 3: reset_password
    reset_ok = test_reset_with_request_context()
    
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