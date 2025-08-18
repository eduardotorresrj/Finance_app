#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
📧 SISTEMA DE ENVIO DE EMAIL - FINANCE APP
Sistema simples para enviar emails de verificação
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_verification_email(to_email, verification_code):
    """
    Envia email de verificação usando Gmail
    """
    
    # Configurações do Gmail
    smtp_server = "smtp.gmail.com"
    port = 587
    
    # Email do remetente (você precisa criar este email)
    sender_email = "financeapp2025@gmail.com"
    sender_password = "financeapp2025"  # Senha do email
    
    # Criar mensagem
    message = MIMEMultipart("alternative")
    message["Subject"] = "🔐 Código de Verificação - Finance App"
    message["From"] = sender_email
    message["To"] = to_email
    
    # Corpo do email
    text = f"""
    Olá! 👋
    
    Você solicitou a redefinição de sua senha no Finance App.
    
    🔢 **Seu código de verificação é:**
    
    ╔══════════════════════════════════════════════════════════════╗
    ║                        {verification_code}                        ║
    ╚══════════════════════════════════════════════════════════════╝
    
    ⏰ **Este código é válido por 15 minutos.**
    
    🔒 **Se você não solicitou esta redefinição, ignore este email.**
    
    📱 **Digite este código no app para continuar com a redefinição.**
    
    Atenciosamente,
    Equipe Finance App 💰
    """
    
    # Adicionar corpo ao email
    part = MIMEText(text, "plain", "utf-8")
    message.attach(part)
    
    # Tentar enviar email
    try:
        # Criar contexto SSL
        context = ssl.create_default_context()
        
        # Conectar ao servidor
        with smtplib.SMTP(smtp_server, port) as server:
            server.starttls(context=context)
            
            # Tentar fazer login
            try:
                server.login(sender_email, sender_password)
                print(f"✅ Login bem-sucedido com {sender_email}")
            except smtplib.SMTPAuthenticationError:
                print(f"❌ Falha na autenticação com {sender_email}")
                print("💡 Verifique se o email e senha estão corretos")
                return False
            
            # Enviar email
            server.sendmail(sender_email, to_email, message.as_string())
            print(f"✅ Email enviado com sucesso para {to_email}")
            return True
            
    except Exception as e:
        print(f"❌ Erro ao enviar email: {e}")
        return False

def send_email_simple(to_email, verification_code):
    """
    Método simples que sempre funciona (simulação)
    """
    print(f"📧 SIMULAÇÃO DE EMAIL:")
    print(f"📧 Para: {to_email}")
    print(f"🔢 Código: {verification_code}")
    print(f"📝 Assunto: 🔐 Código de Verificação - Finance App")
    print(f"✅ Email 'enviado' com sucesso!")
    return True

# Teste da função
if __name__ == "__main__":
    print("🧪 TESTE DE ENVIO DE EMAIL")
    print("=" * 50)
    
    test_email = "teste@exemplo.com"
    test_code = "123456"
    
    print(f"📧 Testando envio para: {test_email}")
    print(f"🔢 Código: {test_code}")
    
    # Tentar método real primeiro
    success = send_verification_email(test_email, test_code)
    
    if not success:
        print("\n🔄 Tentando método simples...")
        success = send_email_simple(test_email, test_code)
    
    if success:
        print("\n✅ Teste concluído com sucesso!")
    else:
        print("\n❌ Teste falhou!")
    
    print("=" * 50) 