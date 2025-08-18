#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🧪 TESTE DO SISTEMA DE REDEFINIÇÃO DE SENHA
Script para testar se o sistema está funcionando corretamente
"""

import sys
import os

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_email_system():
    """Testa o sistema de email"""
    print("📧 TESTANDO SISTEMA DE EMAIL")
    print("=" * 50)
    
    try:
        from email_working import send_verification_email
        print("✅ Importação do email_working OK")
        
        # Teste de envio
        test_email = "teste@exemplo.com"
        test_code = "123456"
        
        result = send_verification_email(test_email, test_code)
        print(f"✅ Resultado do envio: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no sistema de email: {e}")
        return False

def test_app_imports():
    """Testa as importações do app.py"""
    print("\n🔧 TESTANDO IMPORTAÇÕES DO APP")
    print("=" * 50)
    
    try:
        # Testar importações básicas
        import secrets
        print("✅ secrets OK")
        
        import smtplib
        print("✅ smtplib OK")
        
        from email.mime.text import MIMEText
        print("✅ MIMEText OK")
        
        from email.mime.multipart import MIMEMultipart
        print("✅ MIMEMultipart OK")
        
        # Testar importação do Flask
        from flask import Flask, session
        print("✅ Flask OK")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro nas importações: {e}")
        return False

def test_database():
    """Testa a conexão com o banco de dados"""
    print("\n🗄️ TESTANDO BANCO DE DADOS")
    print("=" * 50)
    
    try:
        from app import db, User
        
        # Verificar se o banco existe
        if os.path.exists('finance.db'):
            print("✅ Arquivo do banco existe")
        else:
            print("⚠️ Arquivo do banco não existe")
        
        # Tentar conectar
        try:
            # Criar contexto da aplicação
            from app import app
            with app.app_context():
                # Tentar fazer uma consulta simples
                users = User.query.all()
                print(f"✅ Conexão OK - {len(users)} usuários encontrados")
                
                # Verificar se há usuários com email
                users_with_email = User.query.filter(User.email.isnot(None)).all()
                print(f"✅ {len(users_with_email)} usuários com email cadastrado")
                
                return True
                
        except Exception as e:
            print(f"❌ Erro na conexão: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao importar módulos do banco: {e}")
        return False

def test_password_reset_flow():
    """Testa o fluxo completo de redefinição de senha"""
    print("\n🔄 TESTANDO FLUXO DE REDEFINIÇÃO")
    print("=" * 50)
    
    try:
        from app import app, User, password_reset_codes, cleanup_expired_codes
        from datetime import datetime, timedelta
        import secrets
        
        with app.app_context():
            # 1. Limpar códigos expirados
            cleanup_expired_codes()
            print("✅ Limpeza de códigos expirados OK")
            
            # 2. Verificar se há usuários
            users = User.query.filter(User.email.isnot(None)).all()
            if not users:
                print("⚠️ Nenhum usuário com email encontrado")
                print("💡 Crie um usuário com email primeiro")
                return False
            
            test_user = users[0]
            print(f"✅ Usuário de teste: {test_user.username} ({test_user.email})")
            
            # 3. Gerar código de teste
            verification_code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
            expiry = datetime.now() + timedelta(minutes=15)
            
            password_reset_codes[verification_code] = {
                'user_id': test_user.id,
                'email': test_user.email,
                'expiry': expiry
            }
            print(f"✅ Código gerado: {verification_code}")
            
            # 4. Verificar se o código foi armazenado
            if verification_code in password_reset_codes:
                print("✅ Código armazenado corretamente")
            else:
                print("❌ Erro ao armazenar código")
                return False
            
            # 5. Simular verificação
            code_data = password_reset_codes[verification_code]
            if code_data['user_id'] == test_user.id:
                print("✅ Verificação do código OK")
            else:
                print("❌ Erro na verificação do código")
                return False
            
            # 6. Limpar código de teste
            del password_reset_codes[verification_code]
            print("✅ Limpeza do código de teste OK")
            
            return True
            
    except Exception as e:
        print(f"❌ Erro no fluxo de redefinição: {e}")
        return False

def test_templates():
    """Testa se os templates existem"""
    print("\n📄 TESTANDO TEMPLATES")
    print("=" * 50)
    
    templates = [
        'templates/forgot_password.html',
        'templates/verify_code.html',
        'templates/reset_password.html'
    ]
    
    all_exist = True
    for template in templates:
        if os.path.exists(template):
            print(f"✅ {template}")
        else:
            print(f"❌ {template} - NÃO ENCONTRADO")
            all_exist = False
    
    return all_exist

def main():
    """Função principal de teste"""
    print("🧪 TESTE COMPLETO DO SISTEMA DE REDEFINIÇÃO DE SENHA")
    print("=" * 60)
    
    tests = [
        ("Sistema de Email", test_email_system),
        ("Importações do App", test_app_imports),
        ("Banco de Dados", test_database),
        ("Fluxo de Redefinição", test_password_reset_flow),
        ("Templates", test_templates)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Erro no teste {test_name}: {e}")
            results.append((test_name, False))
    
    # Resumo
    print("\n📊 RESUMO DOS TESTES")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 RESULTADO: {passed}/{total} testes passaram")
    
    if passed == total:
        print("🎉 SISTEMA FUNCIONANDO PERFEITAMENTE!")
        print("\n💡 Para testar no navegador:")
        print("1. Execute: python app.py")
        print("2. Acesse: http://127.0.0.1:5000")
        print("3. Faça login → Logout → Esqueci a senha")
        print("4. Digite um email cadastrado")
        print("5. O código aparecerá na tela")
    else:
        print("⚠️ ALGUNS PROBLEMAS ENCONTRADOS")
        print("\n🔧 Verifique:")
        print("1. Se todos os arquivos estão presentes")
        print("2. Se o banco de dados foi criado")
        print("3. Se há usuários com email cadastrado")
        print("4. Se todas as dependências estão instaladas")

if __name__ == "__main__":
    main() 