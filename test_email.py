#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🔧 TESTE DE CONFIGURAÇÃO DE EMAIL - FINANCE APP
Este script testa se o email está configurado corretamente.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def test_email_configuration():
    """Testa a configuração de email"""
    
    print("🔧 TESTE DE CONFIGURAÇÃO DE EMAIL - FINANCE APP")
    print("=" * 60)
    
    try:
        # Importar configurações
        from email_config import (
            SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, 
            SENDER_PASSWORD, EMAIL_FROM_NAME, is_email_configured
        )
        
        print(f"📧 Servidor SMTP: {SMTP_SERVER}:{SMTP_PORT}")
        print(f"📧 Email remetente: {SENDER_EMAIL}")
        print(f"📧 Nome remetente: {EMAIL_FROM_NAME}")
        print(f"🔑 Senha: {'*' * len(SENDER_PASSWORD)}")
        
        # Verificar se está configurado
        if not is_email_configured():
            print("\n❌ EMAIL NÃO CONFIGURADO!")
            print("\n📋 Para configurar:")
            print("1. Ative autenticação de 2 fatores no Gmail")
            print("2. Gere uma senha de app em: https://myaccount.google.com/apppasswords")
            print("3. Edite o arquivo email_config.py")
            print("4. Execute este teste novamente")
            return False
        
        print("\n✅ Configuração básica OK!")
        
        # Testar conexão SMTP
        print("\n🔗 Testando conexão SMTP...")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        
        print("🔐 Testando autenticação...")
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        
        print("✅ Autenticação OK!")
        
        # Testar envio de email
        print("\n📤 Testando envio de email...")
        
        msg = MIMEMultipart()
        msg['From'] = f"{EMAIL_FROM_NAME} <{SENDER_EMAIL}>"
        msg['To'] = SENDER_EMAIL  # Enviar para o próprio email
        msg['Subject'] = "🧪 Teste de Configuração - Finance App"
        
        body = """
        Olá! 👋
        
        Este é um email de teste para verificar se a configuração do Finance App está funcionando.
        
        ✅ Se você recebeu este email, a configuração está correta!
        
        Atenciosamente,
        Equipe Finance App 💰
        """
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        text = msg.as_string()
        server.sendmail(SENDER_EMAIL, SENDER_EMAIL, text)
        server.quit()
        
        print("✅ Email de teste enviado com sucesso!")
        print(f"📧 Verifique sua caixa de entrada: {SENDER_EMAIL}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Erro ao importar configuração: {e}")
        print("💡 Verifique se o arquivo email_config.py existe")
        return False
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ Erro de autenticação: {e}")
        print("💡 Verifique se a senha de app está correta")
        return False
        
    except smtplib.SMTPException as e:
        print(f"❌ Erro SMTP: {e}")
        return False
        
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False

if __name__ == "__main__":
    success = test_email_configuration()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 CONFIGURAÇÃO DE EMAIL FUNCIONANDO PERFEITAMENTE!")
        print("✅ Você pode usar a funcionalidade 'Esqueci a senha'")
    else:
        print("❌ CONFIGURAÇÃO DE EMAIL COM PROBLEMAS")
        print("🔧 Siga as instruções acima para corrigir")
    
    print("=" * 60) 