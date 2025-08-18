#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
📧 SISTEMA DE LOG DE EMAILS - FINANCE APP
Salva emails em arquivo para verificação
"""

import json
import os
from datetime import datetime

def save_email_to_file(email, verification_code):
    """
    Salva o email em um arquivo para verificação
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
    Função principal que salva o email
    """
    print(f"📧 PROCESSANDO EMAIL:")
    print(f"📧 Para: {email}")
    print(f"🔢 Código: {verification_code}")
    
    # Salvar email em arquivo
    success = save_email_to_file(email, verification_code)
    
    if success:
        print(f"✅ Email processado e salvo com sucesso!")
        print(f"📁 Verifique a pasta 'email_logs' para ver os emails")
        return True
    else:
        print(f"❌ Erro ao processar email")
        return False

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