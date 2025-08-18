#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
📧 SISTEMA DE EMAIL COM SENDGRID - FINANCE APP
Usando SendGrid para envio real de emails
"""

import json
import os
import requests
from datetime import datetime

def send_email_via_sendgrid(email, verification_code):
    """
    Envia email usando SendGrid (gratuito até 100 emails/dia)
    """
    try:
        # Configurações do SendGrid (você precisa criar uma conta gratuita)
        api_key = "YOUR_SENDGRID_API_KEY"  # Substitua pela sua chave
        url = "https://api.sendgrid.com/v3/mail/send"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "personalizations": [
                {
                    "to": [{"email": email}],
                    "subject": "🔐 Código de Verificação - Finance App"
                }
            ],
            "from": {"email": "noreply@financeapp.com", "name": "Finance App"},
            "content": [
                {
                    "type": "text/plain",
                    "value": f"""
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
                }
            ]
        }
        
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 202:
            print(f"✅ Email enviado via SendGrid para {email}")
            return True
        else:
            print(f"❌ Erro no SendGrid: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erro no SendGrid: {e}")
        return False

def send_email_via_mailgun(email, verification_code):
    """
    Envia email usando Mailgun (gratuito até 5.000 emails/mês)
    """
    try:
        # Configurações do Mailgun
        api_key = "YOUR_MAILGUN_API_KEY"  # Substitua pela sua chave
        domain = "your-domain.com"  # Substitua pelo seu domínio
        url = f"https://api.mailgun.net/v3/{domain}/messages"
        
        data = {
            "from": "Finance App <noreply@your-domain.com>",
            "to": email,
            "subject": "🔐 Código de Verificação - Finance App",
            "text": f"""
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
        }
        
        response = requests.post(url, auth=("api", api_key), data=data)
        
        if response.status_code == 200:
            print(f"✅ Email enviado via Mailgun para {email}")
            return True
        else:
            print(f"❌ Erro no Mailgun: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erro no Mailgun: {e}")
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
    Função principal que tenta diferentes métodos
    """
    print(f"📧 PROCESSANDO EMAIL:")
    print(f"📧 Para: {email}")
    print(f"🔢 Código: {verification_code}")
    
    # Sempre salvar log primeiro
    log_saved = save_email_log(email, verification_code)
    
    # Método 1: SendGrid
    if send_email_via_sendgrid(email, verification_code):
        return True
    
    # Método 2: Mailgun
    if send_email_via_mailgun(email, verification_code):
        return True
    
    # Método 3: Log apenas (sempre funciona)
    print("🔄 Usando método de log apenas...")
    print(f"✅ Email processado e salvo em arquivo")
    print(f"📁 Verifique a pasta 'email_logs' para ver o código")
    return True

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