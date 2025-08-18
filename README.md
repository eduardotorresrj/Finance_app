# 💰 Finance App - Sistema de Controle Financeiro

Um sistema completo de controle financeiro pessoal desenvolvido em Flask, com interface moderna e funcionalidades avançadas de relatórios.

## ✨ Funcionalidades

- 🔐 **Autenticação de Usuários** - Login e registro seguro
- 💳 **Gestão de Transações** - Adicionar receitas e despesas
- 📅 **Contas a Vencer** - Controle de contas com data de vencimento
- 📊 **Dashboard Interativo** - Visão geral das finanças
- 📈 **Relatórios Avançados** - Gráficos e análises detalhadas
- 📱 **Interface Responsiva** - Funciona em desktop e mobile
- 🎨 **Design Moderno** - Interface limpa e intuitiva

## 🚀 Tecnologias

- **Backend:** Flask, SQLAlchemy, Flask-Login
- **Frontend:** HTML5, CSS3, JavaScript, Bootstrap 5
- **Gráficos:** Plotly.js
- **Banco de Dados:** SQLite
- **Deploy:** PythonAnywhere

## 📋 Pré-requisitos

- Python 3.8+
- pip
- Git (opcional)

## 🔧 Instalação

### 1. Clone o repositório
```bash
git clone https://github.com/seu-usuario/finance-app.git
cd finance-app
```

### 2. Crie um ambiente virtual
```bash
python -m venv venv
```

### 3. Ative o ambiente virtual

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### 4. Instale as dependências
```bash
pip install -r requirements.txt
```

### 5. Configure as variáveis de ambiente
Crie um arquivo `.env` na raiz do projeto:
```env
SECRET_KEY=sua_chave_secreta_aqui
DATABASE_URL=sqlite:///finance.db
```

### 6. Inicialize o banco de dados
```bash
python init_db.py
```

### 7. Execute a aplicação
```bash
python app.py
```

### 8. Acesse a aplicação
Abra seu navegador e acesse: `http://localhost:5000`

## 👤 Usuário Padrão

- **Usuário:** `teste`
- **Senha:** `123456`
- **Email:** `teste@example.com`

## 📁 Estrutura do Projeto

```
finance-app/
├── app.py                 # Aplicação principal
├── config.py             # Configurações
├── wsgi.py               # Configuração WSGI para produção
├── init_db.py            # Inicialização do banco
├── requirements.txt      # Dependências Python
├── templates/            # Templates HTML
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── add_transaction.html
│   ├── add_bill.html
│   └── reports.html
├── static/               # Arquivos estáticos
│   └── uploads/
└── instance/             # Banco de dados SQLite
    └── finance.db
```

## 🚀 Deploy no PythonAnywhere

Para fazer o deploy da aplicação no PythonAnywhere, consulte o guia completo:
[Guia de Deploy](DEPLOY_PYTHONANYWHERE.md)

## 🔧 Configuração de Desenvolvimento

### Variáveis de Ambiente
- `SECRET_KEY`: Chave secreta para sessões
- `DATABASE_URL`: URL do banco de dados
- `DEBUG`: Modo debug (True/False)

### Banco de Dados
O sistema usa SQLite por padrão. Para usar outros bancos:
1. Instale o driver apropriado
2. Configure `DATABASE_URL`
3. Execute `python init_db.py`

## 📊 Funcionalidades Detalhadas

### Dashboard
- Saldo atual
- Gráfico de receitas vs despesas
- Contas a vencer
- Transações recentes

### Transações
- Adicionar receitas e despesas
- Categorização
- Descrições detalhadas
- Data da transação

### Contas a Vencer
- Data de vencimento
- Valor da conta
- Categoria
- Descrição

### Relatórios
- Filtros por período (mensal/quinzenal)
- Gráficos interativos
- Análise por categoria
- Resumo financeiro

## 🔒 Segurança

- Senhas criptografadas com bcrypt
- Sessões seguras
- Proteção CSRF
- Validação de entrada
- Sanitização de dados

## 🐛 Solução de Problemas

### Erro: "No module named 'flask'"
```bash
pip install -r requirements.txt
```

### Erro: "Database is locked"
- Verifique se não há outro processo usando o banco
- Reinicie a aplicação

### Erro: "Port already in use"
```bash
# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :5000
kill -9 <PID>
```

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 📞 Suporte

- **Email:** seu-email@exemplo.com
- **Issues:** [GitHub Issues](https://github.com/seu-usuario/finance-app/issues)
- **Documentação:** [Wiki](https://github.com/seu-usuario/finance-app/wiki)

## 🙏 Agradecimentos

- Flask Framework
- Bootstrap
- Plotly.js
- PythonAnywhere
- Comunidade Python

---

**Desenvolvido com ❤️ para facilitar o controle financeiro pessoal** 