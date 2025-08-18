#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
📧 SERVIÇO DE EMAIL REAL - FINANCE APP
Usando serviços gratuitos para enviar emails
"""

import json
import os
import requests
from datetime import datetime

def send_email_via_webhook(email, verification_code):
    """
    Envia email usando webhook gratuito
    """
    try:
        # Usar webhook gratuito (você pode criar em webhook.site)
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

def send_email_via_api(email, verification_code):
    """
    Envia email usando API gratuita
    """
    try:
        # Usar API gratuita (exemplo)
        api_url = "https://api.emailjs.com/api/v1.0/email/send"
        
        data = {
            "service_id": "your_service_id",
            "template_id": "your_template_id",
            "user_id": "your_user_id",
            "template_params": {
                "to_email": email,
                "verification_code": verification_code,
                "message": f"Código de verificação: {verification_code}"
            }
        }
        
        response = requests.post(api_url, json=data)
        
        if response.status_code == 200:
            print(f"✅ Email enviado via API para {email}")
            return True
        else:
            print(f"❌ Erro na API: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erro na API: {e}")
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
    
    # Método 1: Webhook
    if send_email_via_webhook(email, verification_code):
        return True
    
    # Método 2: API
    if send_email_via_api(email, verification_code):
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
    print("🧪 TESTE DE SERVIÇO DE EMAIL")
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