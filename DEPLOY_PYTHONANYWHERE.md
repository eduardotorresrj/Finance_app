# 🚀 Guia de Deploy - Finance App no PythonAnywhere

## 📋 Pré-requisitos
- Conta no PythonAnywhere (gratuita ou paga)
- Projeto funcionando localmente

## 🔧 Passo a Passo Completo

### 1. **Preparar o Projeto**
- ✅ Remover dependências desnecessárias (OpenCV, NumPy, etc.)
- ✅ Configurar variáveis de ambiente
- ✅ Atualizar requirements.txt
- ✅ Configurar wsgi.py

### 2. **Criar Conta no PythonAnywhere**
1. Acesse: https://www.pythonanywhere.com/
2. Clique em "Create a Beginner account" (gratuito)
3. Escolha um nome de usuário
4. Confirme seu email

### 3. **Acessar o Console**
1. Faça login no PythonAnywhere
2. Vá para a aba "Consoles"
3. Clique em "Bash" para abrir um terminal

### 4. **Clonar/Upload do Projeto**

#### Opção A: Se o projeto está no GitHub
```bash
git clone https://github.com/seu-usuario/finance-app.git
cd finance-app
```

#### Opção B: Upload manual
1. Vá para a aba "Files"
2. Navegue até `/home/seu-usuario/`
3. Clique em "Upload a file" e faça upload dos arquivos do projeto
4. No console, navegue até a pasta:
```bash
cd /home/seu-usuario/finance-app
```

### 5. **Criar Ambiente Virtual**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 6. **Instalar Dependências**
```bash
pip install -r requirements.txt
```

### 7. **Configurar Variáveis de Ambiente**
```bash
# Criar arquivo .env
echo "SECRET_KEY=sua_chave_secreta_muito_segura_aqui" > .env
echo "DATABASE_URL=sqlite:///finance.db" >> .env
```

### 8. **Inicializar o Banco de Dados**
```bash
python init_db.py
```

### 9. **Configurar Web App**

#### 9.1 Acessar Web Tab
1. Vá para a aba "Web"
2. Clique em "Add a new web app"

#### 9.2 Configurar Domínio
1. Escolha um domínio: `seu-usuario.pythonanywhere.com`
2. Clique em "Next"

#### 9.3 Escolher Framework
1. Selecione "Flask"
2. Escolha Python 3.9 ou superior
3. Clique em "Next"

#### 9.4 Configurar Caminhos
1. **Source code:** `/home/seu-usuario/finance-app`
2. **Working directory:** `/home/seu-usuario/finance-app`
3. **WSGI configuration file:** Clique em "Edit"

#### 9.5 Editar WSGI
Substitua todo o conteúdo por:
```python
import sys
import os

# Add the project directory to the Python path
path = '/home/seu-usuario/finance-app'
if path not in sys.path:
    sys.path.append(path)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from app import app as application
```

### 10. **Configurar Virtual Environment**
1. No arquivo WSGI, adicione antes do `from app import app`:
```python
# Activate virtual environment
activate_this = '/home/seu-usuario/finance-app/venv/bin/activate_this.py'
with open(activate_this) as file_:
    exec(file_.read(), dict(__file__=activate_this))
```

### 11. **Salvar e Recarregar**
1. Clique em "Save"
2. Volte para a aba "Web"
3. Clique em "Reload seu-usuario.pythonanywhere.com"

### 12. **Verificar Logs**
1. Na aba "Web", clique em "Log files"
2. Verifique se há erros em "Error log"

### 13. **Testar a Aplicação**
1. Acesse: `https://seu-usuario.pythonanywhere.com`
2. Teste o registro e login
3. Verifique se todas as funcionalidades estão funcionando

## 🔧 Configurações Adicionais

### Configurar HTTPS (Recomendado)
1. Na aba "Web", clique em "Security"
2. Marque "Force HTTPS"
3. Clique em "Save"

### Configurar Domínio Personalizado (Opcional)
1. Compre um domínio
2. Configure DNS para apontar para PythonAnywhere
3. Na aba "Web", adicione o domínio

## 🚨 Solução de Problemas

### Erro: ModuleNotFoundError
```bash
# Verificar se o virtual environment está ativo
source venv/bin/activate
pip list
```

### Erro: Database
```bash
# Recriar banco
python init_db.py
```

### Erro: Permissions
```bash
# Verificar permissões
chmod 755 /home/seu-usuario/finance-app
```

### Erro: WSGI
- Verificar se o caminho está correto
- Verificar se o virtual environment está configurado
- Verificar logs de erro

## 📊 Monitoramento

### Logs Importantes
- **Error log:** Erros da aplicação
- **Server log:** Logs do servidor
- **Access log:** Acessos à aplicação

### Métricas
- CPU usage
- Memory usage
- Disk usage

## 🔒 Segurança

### Variáveis de Ambiente
- Nunca commitar SECRET_KEY no GitHub
- Usar variáveis de ambiente para configurações sensíveis

### HTTPS
- Sempre usar HTTPS em produção
- Configurar certificados SSL

### Senhas
- Usar senhas fortes
- Implementar política de senhas

## 📈 Escalabilidade

### Para Contas Pagas
- Mais recursos de CPU/RAM
- Domínios personalizados
- SSL gratuito
- Backups automáticos

### Otimizações
- Usar CDN para arquivos estáticos
- Implementar cache
- Otimizar consultas ao banco

## 🎯 Checklist Final

- [ ] Projeto funcionando localmente
- [ ] Requirements.txt atualizado
- [ ] Variáveis de ambiente configuradas
- [ ] Banco de dados inicializado
- [ ] Web app configurado
- [ ] WSGI configurado
- [ ] Virtual environment ativo
- [ ] HTTPS configurado
- [ ] Testes realizados
- [ ] Logs verificados

## 📞 Suporte

- **PythonAnywhere Help:** https://help.pythonanywhere.com/
- **Documentação Flask:** https://flask.palletsprojects.com/
- **Comunidade:** Stack Overflow, Reddit

---

**🎉 Parabéns! Seu Finance App está no ar!** 