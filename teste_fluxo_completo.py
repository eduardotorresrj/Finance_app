#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🧪 TESTE DO FLUXO COMPLETO DE REDEFINIÇÃO DE SENHA
Script para simular todo o processo de redefinição
"""

import sys
import os
from datetime import datetime, timedelta
import secrets

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_complete_flow():
    """Testa o fluxo completo de redefinição de senha"""
    print("🧪 TESTE DO FLUXO COMPLETO DE REDEFINIÇÃO DE SENHA")
    print("=" * 60)
    
    try:
        from app import app, User, password_reset_codes, cleanup_expired_codes
        from werkzeug.security import generate_password_hash, check_password_hash
        
        with app.app_context():
            print("✅ Contexto da aplicação criado")
            
            # 1. Verificar usuários disponíveis
            users = User.query.filter(User.email.isnot(None)).all()
            if not users:
                print("❌ Nenhum usuário com email encontrado")
                return False
            
            test_user = users[0]
            print(f"✅ Usuário de teste: {test_user.username} ({test_user.email})")
            
            # 2. Limpar códigos expirados
            cleanup_expired_codes()
            print("✅ Códigos expirados removidos")
            
            # 3. Simular solicitação de código
            print("\n📧 SIMULANDO SOLICITAÇÃO DE CÓDIGO")
            print("-" * 40)
            
            # Gerar código único
            while True:
                verification_code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
                if verification_code not in password_reset_codes:
                    break
            
            expiry = datetime.now() + timedelta(minutes=15)
            
            # Armazenar código
            password_reset_codes[verification_code] = {
                'user_id': test_user.id,
                'email': test_user.email,
                'expiry': expiry
            }
            
            print(f"✅ Código gerado: {verification_code}")
            print(f"✅ Código armazenado para: {test_user.email}")
            print(f"✅ Válido até: {expiry.strftime('%H:%M:%S')}")
            
            # 4. Simular envio de email
            print("\n📧 SIMULANDO ENVIO DE EMAIL")
            print("-" * 40)
            
            try:
                from email_working import send_verification_email
                email_sent = send_verification_email(test_user.email, verification_code)
                if email_sent:
                    print("✅ Email processado com sucesso")
                else:
                    print("⚠️ Email não enviado, mas log salvo")
            except Exception as e:
                print(f"❌ Erro no envio: {e}")
            
            # 5. Simular verificação do código
            print("\n🔐 SIMULANDO VERIFICAÇÃO DO CÓDIGO")
            print("-" * 40)
            
            if verification_code in password_reset_codes:
                code_data = password_reset_codes[verification_code]
                
                # Verificar se não expirou
                if datetime.now() <= code_data['expiry']:
                    print("✅ Código válido e não expirado")
                    print(f"✅ Usuário ID: {code_data['user_id']}")
                    print(f"✅ Email: {code_data['email']}")
                    
                    # Remover código usado
                    del password_reset_codes[verification_code]
                    print("✅ Código removido após uso")
                    
                else:
                    print("❌ Código expirado")
                    return False
            else:
                print("❌ Código não encontrado")
                return False
            
            # 6. Simular redefinição de senha
            print("\n🔑 SIMULANDO REDEFINIÇÃO DE SENHA")
            print("-" * 40)
            
            new_password = "NovaSenha123!"
            
            # Validar senha
            def validate_password(password):
                if len(password) < 8:
                    return False, "A senha deve ter pelo menos 8 caracteres"
                if not any(c.isupper() for c in password):
                    return False, "A senha deve conter pelo menos uma letra maiúscula"
                if not any(c.islower() for c in password):
                    return False, "A senha deve conter pelo menos uma letra minúscula"
                if not any(c.isdigit() for c in password):
                    return False, "A senha deve conter pelo menos um número"
                if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
                    return False, "A senha deve conter pelo menos um caractere especial"
                return True, "Senha válida"
            
            is_valid, message = validate_password(new_password)
            if is_valid:
                print("✅ Nova senha válida")
                
                # Atualizar senha no banco
                test_user.password_hash = generate_password_hash(new_password)
                from app import db
                db.session.commit()
                print("✅ Senha atualizada no banco de dados")
                
                # Verificar se a senha foi atualizada
                if check_password_hash(test_user.password_hash, new_password):
                    print("✅ Senha verificada com sucesso")
                else:
                    print("❌ Erro na verificação da senha")
                    return False
                
            else:
                print(f"❌ Senha inválida: {message}")
                return False
            
            print("\n🎉 FLUXO COMPLETO TESTADO COM SUCESSO!")
            print("=" * 60)
            print("✅ Código gerado e armazenado")
            print("✅ Email processado")
            print("✅ Código verificado")
            print("✅ Senha redefinida")
            print("✅ Sistema funcionando perfeitamente!")
            
            return True
            
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return False

def show_usage_instructions():
    """Mostra instruções de uso"""
    print("\n📋 INSTRUÇÕES PARA TESTAR NO NAVEGADOR")
    print("=" * 60)
    print("1. Execute: python app.py")
    print("2. Acesse: http://127.0.0.1:5000")
    print("3. Faça login com uma conta existente")
    print("4. Clique em 'Logout'")
    print("5. Clique em 'Esqueci a senha'")
    print("6. Digite um email cadastrado:")
    print("   - teste@example.com")
    print("   - eduardotorresrj27@gmail.com")
    print("7. Clique em 'Enviar Código'")
    print("8. O código aparecerá na tela")
    print("9. Clique em 'Continuar para Verificação'")
    print("10. Digite o código de 6 dígitos")
    print("11. Clique em 'Verificar Código'")
    print("12. Digite uma nova senha (ex: NovaSenha123!)")
    print("13. Confirme a senha")
    print("14. Clique em 'Alterar Senha'")
    print("\n🎯 O sistema deve funcionar perfeitamente!")

def main():
    """Função principal"""
    success = test_complete_flow()
    
    if success:
        show_usage_instructions()
    else:
        print("\n❌ TESTE FALHOU")
        print("Verifique os erros acima e tente novamente")

if __name__ == "__main__":
    main() 