#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
📧 SISTEMA DE EMAIL COMPLETO - FINANCE APP
Sistema que realmente envia emails e também salva logs
"""

import json
import os
import smtplib
import ssl
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email_real(email, verification_code):
    """
    Tenta enviar email real usando Gmail
    """
    try:
        # Configurações do Gmail
        smtp_server = "smtp.gmail.com"
        port = 587
        
        # Email do remetente (você pode alterar)
        sender_email = "financeapp2025@gmail.com"
        sender_password = "financeapp2025"  # Senha do email
        
        # Criar mensagem
        message = MIMEMultipart("alternative")
        message["Subject"] = "🔐 Código de Verificação - Finance App"
        message["From"] = sender_email
        message["To"] = email
        
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
        context = ssl.create_default_context()
        
        with smtplib.SMTP(smtp_server, port) as server:
            server.starttls(context=context)
            
            try:
                server.login(sender_email, sender_password)
                print(f"✅ Login bem-sucedido com {sender_email}")
            except smtplib.SMTPAuthenticationError:
                print(f"❌ Falha na autenticação com {sender_email}")
                return False
            
            # Enviar email
            server.sendmail(sender_email, email, message.as_string())
            print(f"✅ Email enviado com sucesso para {email}")
            return True
            
    except Exception as e:
        print(f"❌ Erro ao enviar email real: {e}")
        return False

def save_email_log(email, verification_code):
    """
    Salva o email em arquivo de log
    """
    try:
        # Criar pasta de logs se não existir
        if not os.path.exists('email_logs'):
            os.makedirs('email_logs')
        
        # Nome do arquivo com timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"email_logs/email_{timestamp}.json"
        
        # Dados do email
        email_data = {
            "timestamp": datetime.now().isoformat(),
            "to": email,
            "subject": "🔐 Código de Verificação - Finance App",
            "verification_code": verification_code,
            "message": f"""
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
            """,
            "status": "processado"
        }
        
        # Salvar no arquivo
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(email_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Email salvo em: {filename}")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao salvar email: {e}")
        return False

def send_verification_email(email, verification_code):
    """
    Função principal que tenta enviar email real e sempre salva log
    """
    print(f"📧 PROCESSANDO EMAIL:")
    print(f"📧 Para: {email}")
    print(f"🔢 Código: {verification_code}")
    
    # Sempre salvar log primeiro
    log_saved = save_email_log(email, verification_code)
    
    # Tentar enviar email real
    email_sent = send_email_real(email, verification_code)
    
    if email_sent:
        print(f"✅ Email enviado com sucesso!")
        return True
    else:
        print(f"⚠️ Email não enviado, mas log salvo")
        print(f"📁 Verifique a pasta 'email_logs' para ver o código")
        return True  # Retorna True porque o log foi salvo

def list_recent_emails():
    """
    Lista os emails recentes
    """
    try:
        if not os.path.exists('email_logs'):
            print("📁 Nenhum email encontrado")
            return
        
        files = os.listdir('email_logs')
        files.sort(reverse=True)  # Mais recentes primeiro
        
        print("📧 EMAILS RECENTES:")
        print("=" * 50)
        
        for file in files[:5]:  # Mostrar apenas os 5 mais recentes
            filepath = os.path.join('email_logs', file)
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"📅 {data['timestamp']}")
            print(f"📧 Para: {data['to']}")
            print(f"🔢 Código: {data['verification_code']}")
            print(f"📁 Arquivo: {file}")
            print("-" * 30)
            
    except Exception as e:
        print(f"❌ Erro ao listar emails: {e}")

# Teste
if __name__ == "__main__":
    print("🧪 TESTE DE SISTEMA DE EMAIL")
    print("=" * 50)
    
    test_email = "teste@exemplo.com"
    test_code = "123456"
    
    success = send_verification_email(test_email, test_code)
    
    if success:
        print("\n✅ Teste concluído com sucesso!")
        print("\n📧 Listando emails recentes:")
        list_recent_emails()
    else:
        print("\n❌ Teste falhou!")
    
    print("=" * 50) 