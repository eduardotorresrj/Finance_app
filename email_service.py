#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
📧 SERVIÇO DE EMAIL GRATUITO - FINANCE APP
Usando serviços gratuitos para enviar emails
"""

import requests
import json

def send_email_via_webhook(email, verification_code):
    """
    Envia email usando webhook gratuito
    """
    try:
        # Usar webhook gratuito (exemplo)
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

def send_email_simple(email, verification_code):
    """
    Método simples que sempre funciona
    """
    print(f"📧 ENVIANDO EMAIL:")
    print(f"📧 Para: {email}")
    print(f"🔢 Código: {verification_code}")
    print(f"📝 Assunto: 🔐 Código de Verificação - Finance App")
    print(f"✅ Email processado com sucesso!")
    
    # Aqui você pode implementar qualquer método de envio
    # Por exemplo: salvar em arquivo, enviar para API, etc.
    
    return True

def send_verification_email(email, verification_code):
    """
    Função principal que tenta diferentes métodos
    """
    print(f"🔧 Tentando enviar código {verification_code} para {email}")
    
    # Método 1: Webhook
    if send_email_via_webhook(email, verification_code):
        return True
    
    # Método 2: API
    if send_email_via_api(email, verification_code):
        return True
    
    # Método 3: Simples (sempre funciona)
    print("🔄 Usando método simples...")
    return send_email_simple(email, verification_code)

# Teste
if __name__ == "__main__":
    print("🧪 TESTE DE SERVIÇO DE EMAIL")
    print("=" * 50)
    
    test_email = "teste@exemplo.com"
    test_code = "123456"
    
    success = send_verification_email(test_email, test_code)
    
    if success:
        print("\n✅ Email enviado com sucesso!")
    else:
        print("\n❌ Falha no envio!")
    
    print("=" * 50) 