# Configuração de Email para Finance App
# Para usar Gmail, siga os passos abaixo:

"""
🔧 CONFIGURAÇÃO DE EMAIL - GMAIL

1. ATIVE A AUTENTICAÇÃO DE 2 FATORES:
   - Vá para https://myaccount.google.com/security
   - Ative "Verificação em duas etapas"

2. GERE UMA SENHA DE APP:
   - Vá para https://myaccount.google.com/apppasswords
   - Selecione "Email" e "Windows Computer" (ou outro dispositivo)
   - Clique em "Gerar"
   - Copie a senha gerada (16 caracteres)

3. CONFIGURE ABAIXO:
   - Substitua "seu-email@gmail.com" pelo seu email real
   - Substitua "sua-senha-de-app" pela senha de 16 caracteres gerada

4. TESTE:
   - Execute o app e teste a funcionalidade "Esqueci a senha"
   - Verifique se o email chega na sua caixa de entrada
"""

# Configurações SMTP
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Suas credenciais (SUBSTITUA pelos seus dados reais)
SENDER_EMAIL = "seu-email@gmail.com"  # ⚠️ Substitua pelo seu email real
SENDER_PASSWORD = "sua-senha-de-app"  # ⚠️ Substitua pela senha de app de 16 caracteres

# Configurações do email
EMAIL_SUBJECT = "🔐 Redefinição de Senha - Finance App"
EMAIL_FROM_NAME = "Finance App"

# Template do email
EMAIL_TEMPLATE = """
Olá! 👋

Você solicitou a redefinição de sua senha no Finance App.

🔗 **Clique no link abaixo para criar uma nova senha:**
{reset_link}

⏰ **Este link é válido por 1 hora.**

🔒 **Se você não solicitou esta redefinição, ignore este email.**

📧 **Dúvidas?** Entre em contato conosco.

Atenciosamente,
Equipe Finance App 💰
"""

# Verificar se as configurações estão corretas
def is_email_configured():
    """Verifica se o email está configurado corretamente"""
    return (SENDER_EMAIL != "seu-email@gmail.com" and 
            SENDER_PASSWORD != "sua-senha-de-app" and
            "@" in SENDER_EMAIL and
            len(SENDER_PASSWORD) >= 16)

# Teste de configuração
if __name__ == "__main__":
    print("🔧 CONFIGURAÇÃO DE EMAIL - FINANCE APP")
    print("=" * 50)
    
    if is_email_configured():
        print("✅ Email configurado corretamente!")
        print(f"📧 Email: {SENDER_EMAIL}")
        print(f"🔑 Senha: {'*' * len(SENDER_PASSWORD)}")
    else:
        print("❌ Email não configurado!")
        print("\n📋 Para configurar:")
        print("1. Ative autenticação de 2 fatores no Gmail")
        print("2. Gere uma senha de app em: https://myaccount.google.com/apppasswords")
        print("3. Edite este arquivo e substitua as credenciais")
        print("4. Execute novamente para verificar")
    
    print("\n" + "=" * 50) 