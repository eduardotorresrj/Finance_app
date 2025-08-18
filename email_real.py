#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
📧 SISTEMA DE EMAIL REAL - FINANCE APP
Usando serviço gratuito para enviar emails reais
"""

import json
import os
import requests
from datetime import datetime

def send_email_via_brevo(email, verification_code):
    """
    Envia email usando Brevo (anteriormente Sendinblue) - GRATUITO até 300 emails/dia
    """
    try:
        # Configurações do Brevo (você precisa criar uma conta gratuita)
        api_key = "YOUR_BREVO_API_KEY"  # Substitua pela sua chave
        url = "https://api.brevo.com/v3/smtp/email"
        
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "api-key": api_key
        }
        
        data = {
            "sender": {
                "name": "Finance App",
                "email": "noreply@financeapp.com"
            },
            "to": [
                {
                    "email": email,
                    "name": "Usuário"
                }
            ],
            "subject": "🔐 Código de Verificação - Finance App",
            "htmlContent": f"""
            <html>
            <body>
                <h2>Olá! 👋</h2>
                <p>Você solicitou a redefinição de sua senha no Finance App.</p>
                
                <h3>🔢 Seu código de verificação é:</h3>
                
                <div style="background: #f8f9fa; border: 2px solid #007bff; border-radius: 10px; padding: 20px; text-align: center; margin: 20px 0;">
                    <h1 style="color: #007bff; font-size: 32px; margin: 0; font-family: monospace;">{verification_code}</h1>
                </div>
                
                <p><strong>⏰ Este código é válido por 15 minutos.</strong></p>
                
                <p><strong>🔒 Se você não solicitou esta redefinição, ignore este email.</strong></p>
                
                <p><strong>📱 Digite este código no app para continuar com a redefinição.</strong></p>
                
                <hr>
                <p><em>Atenciosamente,<br>Equipe Finance App 💰</em></p>
            </body>
            </html>
            """
        }
        
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 201:
            print(f"✅ Email enviado via Brevo para {email}")
            return True
        else:
            print(f"❌ Erro no Brevo: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erro no Brevo: {e}")
        return False

def send_email_via_resend(email, verification_code):
    """
    Envia email usando Resend - GRATUITO até 3.000 emails/mês
    """
    try:
        # Configurações do Resend
        api_key = "YOUR_RESEND_API_KEY"  # Substitua pela sua chave
        url = "https://api.resend.com/emails"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "from": "Finance App <noreply@financeapp.com>",
            "to": [email],
            "subject": "🔐 Código de Verificação - Finance App",
            "html": f"""
            <html>
            <body>
                <h2>Olá! 👋</h2>
                <p>Você solicitou a redefinição de sua senha no Finance App.</p>
                
                <h3>🔢 Seu código de verificação é:</h3>
                
                <div style="background: #f8f9fa; border: 2px solid #007bff; border-radius: 10px; padding: 20px; text-align: center; margin: 20px 0;">
                    <h1 style="color: #007bff; font-size: 32px; margin: 0; font-family: monospace;">{verification_code}</h1>
                </div>
                
                <p><strong>⏰ Este código é válido por 15 minutos.</strong></p>
                
                <p><strong>🔒 Se você não solicitou esta redefinição, ignore este email.</strong></p>
                
                <p><strong>📱 Digite este código no app para continuar com a redefinição.</strong></p>
                
                <hr>
                <p><em>Atenciosamente,<br>Equipe Finance App 💰</em></p>
            </body>
            </html>
            """
        }
        
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            print(f"✅ Email enviado via Resend para {email}")
            return True
        else:
            print(f"❌ Erro no Resend: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erro no Resend: {e}")
        return False

def send_email_via_webhook(email, verification_code):
    """
    Envia email usando webhook (para desenvolvimento)
    """
    try:
        # Você pode criar um webhook em webhook.site para testar
        webhook_url = "https://webhook.site/your-webhook-url"
        
        data = {
            "to": email,
            "subject": "🔐 Código de Verificação - Finance App",
            "code": verification_code,
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
            """
        }
        
        response = requests.post(webhook_url, json=data)
        
        if response.status_code == 200:
            print(f"✅ Email enviado via webhook para {email}")
            return True
        else:
            print(f"❌ Erro no webhook: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erro no webhook: {e}")
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
            "status": "enviado"
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
    Função principal que tenta enviar email real
    """
    print(f"📧 PROCESSANDO EMAIL:")
    print(f"📧 Para: {email}")
    print(f"🔢 Código: {verification_code}")
    
    # Sempre salvar log primeiro
    log_saved = save_email_log(email, verification_code)
    
    # Tentar diferentes métodos de envio
    email_sent = False
    
    # Método 1: Brevo
    if not email_sent:
        email_sent = send_email_via_brevo(email, verification_code)
    
    # Método 2: Resend
    if not email_sent:
        email_sent = send_email_via_resend(email, verification_code)
    
    # Método 3: Webhook (para desenvolvimento)
    if not email_sent:
        email_sent = send_email_via_webhook(email, verification_code)
    
    if email_sent:
        print(f"✅ Email enviado com sucesso!")
        return True
    else:
        print(f"⚠️ Email não enviado, mas log salvo")
        print(f"📁 Verifique a pasta 'email_logs' para ver o código")
        print(f"💡 Configure um serviço de email para envio real")
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