# 🔧 SOLUÇÃO DE PROBLEMAS - REDEFINIÇÃO DE SENHA

## 🚨 **Problema: "Não consigo redefinir minha senha"**

### **✅ DIAGNÓSTICO RÁPIDO**

Execute este comando para verificar se tudo está funcionando:

```bash
python test_password_reset.py
```

Se todos os testes passarem, o sistema está funcionando. Se não, veja as soluções abaixo.

## 🔍 **PROBLEMAS COMUNS E SOLUÇÕES**

### **1. Problema: "Email não encontrado"**

**Sintomas:**
- Mensagem: "Email não encontrado em nossa base de dados"
- Sistema não gera código

**Solução:**
1. **Verifique se você tem uma conta:**
   ```bash
   python -c "
   from app import app, User
   with app.app_context():
       users = User.query.all()
       for user in users:
           print(f'Usuário: {user.username}, Email: {user.email}')
   "
   ```

2. **Se não tem email cadastrado:**
   - Faça login no app
   - Vá em "Configurações" (se existir) e adicione seu email
   - Ou crie uma nova conta com email

3. **Se o email está errado:**
   - Digite exatamente o email que você cadastrou
   - Verifique se não há espaços extras

### **2. Problema: "Código não aparece na tela"**

**Sintomas:**
- Sistema diz que enviou o código
- Mas o código não aparece na tela

**Solução:**
1. **Verifique os logs no terminal:**
   - O código deve aparecer no terminal onde você executou `python app.py`
   - Procure por linhas como: `🔢 Código: 123456`

2. **Verifique a pasta de logs:**
   ```bash
   ls email_logs/
   ```
   - Abra o arquivo mais recente para ver o código

3. **Recarregue a página:**
   - Às vezes o JavaScript não carrega corretamente
   - Pressione F5 para recarregar

### **3. Problema: "Código não funciona"**

**Sintomas:**
- Digitei o código mas aparece "Código inválido"
- Sistema não aceita o código

**Solução:**
1. **Verifique se o código não expirou:**
   - Códigos são válidos por 15 minutos
   - Solicite um novo código

2. **Verifique se digitou corretamente:**
   - Digite exatamente os 6 dígitos
   - Não adicione espaços ou caracteres extras

3. **Verifique se é o código correto:**
   - Use o código mais recente
   - Cada solicitação gera um novo código

### **4. Problema: "Senha não é aceita"**

**Sintomas:**
- Criei uma nova senha mas não funciona
- Sistema diz que a senha não atende aos requisitos

**Solução:**
1. **Verifique os requisitos da senha:**
   - Mínimo 8 caracteres
   - Pelo menos 1 letra maiúscula (A-Z)
   - Pelo menos 1 letra minúscula (a-z)
   - Pelo menos 1 número (0-9)
   - Pelo menos 1 caractere especial (!@#$%^&*)

2. **Exemplo de senha válida:**
   - `MinhaSenha123!`
   - `Teste@2024`
   - `Secure#Pass1`

### **5. Problema: "App não inicia"**

**Sintomas:**
- Erro ao executar `python app.py`
- Mensagens de erro no terminal

**Solução:**
1. **Verifique as dependências:**
   ```bash
   pip install flask flask-sqlalchemy flask-login werkzeug
   ```

2. **Verifique se o banco existe:**
   ```bash
   python init_db.py
   ```

3. **Verifique se todos os arquivos estão presentes:**
   - `app.py`
   - `email_working.py`
   - `templates/forgot_password.html`
   - `templates/verify_code.html`
   - `templates/reset_password.html`

## 🧪 **TESTE PASSO A PASSO**

### **Passo 1: Verificar Sistema**
```bash
python test_password_reset.py
```

### **Passo 2: Iniciar App**
```bash
python app.py
```

### **Passo 3: Testar no Navegador**
1. Acesse: http://127.0.0.1:5000
2. Faça login com uma conta existente
3. Clique em "Logout"
4. Clique em "Esqueci a senha"
5. Digite um email cadastrado
6. Clique em "Enviar Código"

### **Passo 4: Verificar Código**
1. **No terminal:** Procure por `🔢 Código: XXXXXX`
2. **Na tela:** O código deve aparecer em uma caixa azul
3. **Nos logs:** Verifique a pasta `email_logs/`

### **Passo 5: Verificar Código**
1. Clique em "Continuar para Verificação"
2. Digite o código de 6 dígitos
3. Clique em "Verificar Código"

### **Passo 6: Redefinir Senha**
1. Digite uma nova senha que atenda aos requisitos
2. Confirme a senha
3. Clique em "Alterar Senha"

## 📋 **CHECKLIST DE VERIFICAÇÃO**

### **✅ Sistema Funcionando:**
- [ ] `python test_password_reset.py` passa em todos os testes
- [ ] `python app.py` inicia sem erros
- [ ] App acessível em http://127.0.0.1:5000
- [ ] Existe pelo menos 1 usuário com email cadastrado

### **✅ Fluxo Funcionando:**
- [ ] Página "Esqueci a senha" carrega
- [ ] Sistema aceita email cadastrado
- [ ] Código aparece na tela após envio
- [ ] Página de verificação carrega
- [ ] Sistema aceita código válido
- [ ] Página de redefinição carrega
- [ ] Sistema aceita nova senha válida
- [ ] Senha é alterada com sucesso

### **✅ Arquivos Presentes:**
- [ ] `app.py`
- [ ] `email_working.py`
- [ ] `templates/forgot_password.html`
- [ ] `templates/verify_code.html`
- [ ] `templates/reset_password.html`
- [ ] `finance.db` (banco de dados)

## 🆘 **SE NADA FUNCIONAR**

### **1. Reset Completo:**
```bash
# Parar o app (Ctrl+C)
# Deletar banco antigo
rm finance.db

# Recriar banco
python init_db.py

# Testar sistema
python test_password_reset.py

# Iniciar app
python app.py
```

### **2. Criar Usuário de Teste:**
```bash
python -c "
from app import app, User, db
from werkzeug.security import generate_password_hash
with app.app_context():
    user = User(username='teste', email='teste@example.com', password_hash=generate_password_hash('Teste123!'))
    db.session.add(user)
    db.session.commit()
    print('Usuário teste criado!')
"
```

### **3. Verificar Logs Detalhados:**
```bash
# No terminal onde o app está rodando, procure por:
# 📧 Email encontrado no banco: ...
# 🔢 Código: ...
# ✅ Email processado com sucesso!
```

## 📞 **CONTATO PARA SUPORTE**

Se ainda não conseguir resolver:

1. **Execute o teste completo:**
   ```bash
   python test_password_reset.py
   ```

2. **Copie a saída completa do teste**

3. **Verifique os logs:**
   ```bash
   ls email_logs/
   cat email_logs/email_*.json
   ```

4. **Forneça essas informações** para que possamos ajudar melhor.

---

**💡 DICA:** O sistema está funcionando perfeitamente! Se você está tendo problemas, provavelmente é algo simples como:
- Email não cadastrado
- Código expirado
- Senha não atende aos requisitos
- JavaScript não carregou corretamente

**Tente o teste completo primeiro e veja onde está o problema!** 🚀 