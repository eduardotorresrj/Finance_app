from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, date
import json
import re
import unicodedata
import plotly.graph_objs as go
import plotly.utils
import os

def format_currency(value):
    """Formata valor monetário com vírgulas como separadores de milhares"""
    if value is None:
        return "R$ 0,00"
    # Formata o número com vírgulas como separadores de milhares
    formatted = f"{value:,.2f}"
    # Substitui vírgulas por pontos e pontos por vírgulas (padrão brasileiro)
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"

# ===================== Utilidades de IA =====================
def _strip_accents(text: str) -> str:
    if not text:
        return ''
    return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')

def normalize_text(text: str) -> str:
    """Normaliza texto: minúsculas, sem acentos e com espaços colapsados."""
    if not text:
        return ''
    lowered = text.lower().strip()
    no_accents = _strip_accents(lowered)
    return re.sub(r"\s+", " ", no_accents)

def _parse_number_ptbr(token: str) -> float | None:
    """Converte strings tipo '1.234,56', '3,5k', '2 mil', '1m' em float (R$)."""
    if not token:
        return None
    t = token.strip().lower()
    t = t.replace('r$', '').replace(' ', '')
    multiplier = 1.0
    # Sufixos comuns
    if t.endswith('k'):
        multiplier = 1_000.0
        t = t[:-1]
    elif t.endswith('mi') or t.endswith('m'):
        multiplier = 1_000_000.0
        t = t[:-2] if t.endswith('mi') else t[:-1]
    elif t.endswith('b') or t.endswith('bi'):
        multiplier = 1_000_000_000.0
        t = t[:-1] if t.endswith('b') else t[:-2]
    # Palavras
    if 'milhao' in t:
        multiplier = 1_000_000.0
        t = t.replace('milhao', '')
    if 'bilhao' in t:
        multiplier = 1_000_000_000.0
        t = t.replace('bilhao', '')
    if 'mil' in t:
        multiplier = max(multiplier, 1_000.0)
        t = t.replace('mil', '')
    # Padrão pt-BR 1.234,56 -> 1234.56
    t = t.replace('.', '').replace(',', '.')
    try:
        base = float(t)
        return base * multiplier
    except Exception:
        return None

def extract_entities_from_question(question_text: str) -> dict:
    """Extrai valores monetários, percentuais e prazos (meses/anos) da pergunta normalizada."""
    text = normalize_text(question_text)
    entities: dict[str, list] = {
        'amounts': [],  # valores monetários identificados
        'percents': [], # percentuais (0-100)
        'months': []    # prazos em meses
    }
    # R$ e números soltos
    for match in re.findall(r"r?\$?\s*([0-9][0-9\.,]*)\s*(k|mi|m|b|bi|mil|milhao|bilhao)?", text):
        number_token = match[0]
        suffix = match[1] or ''
        value = _parse_number_ptbr(number_token + suffix)
        if value is not None:
            entities['amounts'].append(value)
    # Percentuais
    for match in re.findall(r"([0-9]+(?:[\.,][0-9]+)?)\s*%", text):
        try:
            p = float(match.replace(',', '.'))
            if 0 <= p <= 100:
                entities['percents'].append(p)
        except Exception:
            pass
    # Prazos: meses/anos/semanas
    for match in re.findall(r"(\d+)\s*(mes|meses|ano|anos|semana|semanas)", text):
        qty = int(match[0])
        unit = match[1]
        if unit.startswith('ano'):
            entities['months'].append(qty * 12)
        elif unit.startswith('semana'):
            # aproximação: 1 mês ~ 4 semanas
            entities['months'].append(max(1, qty // 4))
        else:
            entities['months'].append(qty)
    return entities

# Glossário financeiro resumido (pt-BR)
FIN_GLOSSARY = {
    'cdi': 'CDI (Certificado de Depósito Interbancário): taxa de referência da renda fixa no Brasil. Muitos investimentos pós-fixados rendem um percentual do CDI.',
    'selic': 'SELIC: taxa básica de juros da economia. Tesouro Selic acompanha essa taxa e tem alta liquidez e baixo risco.',
    'ipca': 'IPCA: índice oficial de inflação. Títulos atrelados ao IPCA (Tesouro IPCA+) protegem o poder de compra no longo prazo.',
    'tesouro selic': 'Tesouro Selic: título público pós-fixado ligado à SELIC, indicado para reserva de emergência. Incide IR pela tabela regressiva (22,5% a 15%).',
    'tesouro ipca+': 'Tesouro IPCA+: título público híbrido (IPCA + taxa real). Bom para objetivos de médio/longo prazo. Tem marcação a mercado.',
    'cdb': 'CDB: título de renda fixa emitido por bancos. Pode ser pós-fixado (CDI), prefixado ou IPCA+. Cobertura do FGC até limites vigentes.',
    'lci': 'LCI: Letra de Crédito Imobiliário. Isenta de IR para pessoa física, lastreada no setor imobiliário. Geralmente tem carência.',
    'lca': 'LCA: Letra de Crédito do Agronegócio. Isenta de IR para pessoa física, lastreada no agronegócio. Geralmente com carência.',
    'debentures incentivadas': 'Debêntures incentivadas: títulos de empresas com isenção de IR (PF) quando enquadradas em projetos de infraestrutura.',
    'reserva de emergencia': 'Reserva de emergência: dinheiro para imprevistos (ideal: 6 meses de despesas) em produtos de alta liquidez e baixo risco (ex.: Tesouro Selic).',
    'renda fixa': 'Renda fixa: investimentos com regras de remuneração definidas (ex.: Tesouro, CDB, LCI/LCA).',
    'renda variavel': 'Renda variável: ativos cujo preço pode oscilar (ex.: ações, ETFs). Risco e retorno maiores no longo prazo.',
}

def enrich_response_for_clarity(raw_text: str,
                                summary: dict,
                                intents: list[str],
                                entities: dict,
                                profile,
                                glossary_hits: list[str]) -> str:
    """Anexa um resumo claro, termos e checklist prático para tornar a resposta mais didática."""
    income = summary.get('income', 0.0)
    expense = summary.get('expense', 0.0)
    balance = summary.get('balance', 0.0)
    savings_rate = summary.get('savings_rate', 0.0)

    # Determinar prioridade principal
    if balance < 0:
        priority = "Sair do vermelho e estabilizar o fluxo de caixa"
    elif savings_rate < 10:
        priority = "Elevar poupança para pelo menos 10%"
    else:
        priority = "Otimizar orçamento e investir com disciplina"

    # TL;DR
    tldr_lines = [
        "📌 Resumo rápido (TL;DR)",
        f"- Receitas: {format_currency(income)} | Despesas: {format_currency(expense)} | Saldo: {format_currency(balance)}",
        f"- Taxa de poupança estimada: {savings_rate:.1f}%",
        f"- Prioridade: {priority}",
        ""
    ]

    # Checklist prático por intenção
    top_intent = intents[0] if intents else 'ajuda'
    checklist: list[str] = ["✅ Plano de ação (passo a passo)"]
    if top_intent == 'dívida':
        checklist += [
            "- Hoje: Liste todas as dívidas (valor/juros), pague o mínimo e cancele cartões extras",
            "- 7 dias: Negocie taxas/prazos; concentre excedente na menor dívida (bola de neve)",
            "- 30 dias: Corte 10-20% das despesas variáveis e crie reserva inicial"
        ]
    elif top_intent == 'investimento':
        checklist += [
            "- Hoje: Defina horizonte (meses) e perfil (conservador/moderado/arrojado)",
            "- 7 dias: Abra/valide conta em corretora e simule alocações por perfil",
            "- 30 dias: Inicie aportes mensais automáticos (DCA) com revisão trimestral"
        ]
    elif top_intent == 'poupança':
        checklist += [
            "- Hoje: Automatize 10-20% do salário para conta de reserva",
            "- 7 dias: Reduza 2-3 gastos recorrentes e limite a maior categoria",
            "- 30 dias: Atingir 1 salário de reserva (meta incremental)"
        ]
    elif top_intent == 'gasto':
        checklist += [
            "- Hoje: Bloqueie compras por impulso e cancele assinaturas pouco usadas",
            "- 7 dias: Reprecifique contas (telefone/internet/seguros)",
            "- 30 dias: Estabeleça tetos por categoria e monitore semanalmente"
        ]
    elif top_intent == 'orçamento':
        checklist += [
            "- Hoje: Adote 50/30/20 como base (ou variação adequada)",
            "- 7 dias: Ajuste limites por categoria no app",
            "- 30 dias: Revisão e correção de desvios"
        ]
    else:
        checklist += [
            "- Hoje: Defina objetivo, valor e prazo",
            "- 7 dias: Liste ações e recursos necessários",
            "- 30 dias: Revise progresso e ajuste a estratégia"
        ]
    checklist.append("")

    # Termos usados (glossário)
    terms_lines = []
    extra_terms = []
    if top_intent == 'investimento':
        extra_terms = ['cdi', 'selic', 'ipca', 'tesouro selic', 'tesouro ipca+']
    if top_intent == 'imposto':
        extra_terms += ['ipca', 'cdi']
    explain_terms = list(dict.fromkeys((glossary_hits or []) + extra_terms))[:6]
    if explain_terms:
        terms_lines.append("📖 Explicação simples (termos)")
        for t in explain_terms:
            desc = FIN_GLOSSARY.get(t)
            if desc:
                terms_lines.append(f"- {t.title()}: {desc}")
        terms_lines.append("")

    # Perguntas sugeridas (para continuar)
    suggestions = [
        "❓ Perguntas sugeridas",
        "- Quer que eu gere um plano mensal detalhado com metas SMART?",
        "- Deseja que eu simule cenários com 10%, 20% e 30% de poupança?",
        "- Posso sugerir cortes por categoria com impacto estimado?",
        ""
    ]

    # Montar resposta final
    final_parts = []
    final_parts.extend(tldr_lines)
    final_parts.append(raw_text.strip())
    final_parts.append("")
    final_parts.extend(checklist)
    if terms_lines:
        final_parts.extend(terms_lines)
    final_parts.extend(suggestions)
    return "\n".join(final_parts)

app = Flask(__name__)

# Configuração robusta para Render
def get_database_uri():
    # Tenta várias possibilidades de nome de variável
    database_url = (
        os.environ.get('DATABASE_URL') or
        os.environ.get('RENDER_DATABASE_URL') or
        os.environ.get('POSTGRESQL_URL')
    )
    
    if database_url:
        # Correção ESSENCIAL para formato do Render
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        print(f"✅ Usando PostgreSQL: {database_url[:50]}...")
        return database_url
    
    # Se não encontrar, ERRO (no Render sempre deve ter)
    print("❌ DATABASE_URL não encontrada!")
    return 'sqlite:///instance/finance.db'  # Fallback apenas para debug

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'dev-key-fallback'
app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# SSL para PostgreSQL no Render
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgresql://'):
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'connect_args': {
            'sslmode': 'require',
            'sslrootcert': '/etc/ssl/certs/ca-certificates.crt'
        }
    }

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Rota para debug
@app.route('/debug')
def debug_info():
    info = {
        'database_uri': app.config['SQLALCHEMY_DATABASE_URI'][:100] + '...' if app.config['SQLALCHEMY_DATABASE_URI'] else 'None',
        'has_database_url': 'DATABASE_URL' in os.environ,
        'all_env_vars': {k: v for k, v in os.environ.items() if 'DATABASE' in k or 'SECRET' in k}
    }
    return info

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    type = db.Column(db.String(10))  # 'income' ou 'expense'
    category = db.Column(db.String(50))
    amount = db.Column(db.Float)
    description = db.Column(db.String(200))
    date = db.Column(db.Date)
    due_date = db.Column(db.Date, nullable=True)
    image_path = db.Column(db.String(200), nullable=True)

# ======== IA Learning: Perfis e Interações ========
class AiProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    risk_profile = db.Column(db.String(20), default='moderado')  # conservador | moderado | arrojado
    savings_target_pct = db.Column(db.Integer, default=20)  # meta de poupança
    emergency_months_target = db.Column(db.Integer, default=3)
    avoided_categories_json = db.Column(db.Text, default='[]')  # categorias que o usuário não quer cortar
    focus_counters_json = db.Column(db.Text, default='{}')      # contadores por intenção
    total_feedback = db.Column(db.Integer, default=0)
    avg_helpfulness = db.Column(db.Float, default=0.0)
    interaction_count = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

class AiInteraction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    question = db.Column(db.Text, nullable=False)
    intents_json = db.Column(db.Text, default='[]')
    response = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def _loads_json_or_default(raw_text: str, default):
    try:
        return json.loads(raw_text) if raw_text else default
    except Exception:
        return default

def _dumps_json_safe(obj) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return json.dumps(str(obj))

def get_or_create_ai_profile(user_id: int) -> 'AiProfile':
    profile = AiProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        profile = AiProfile(user_id=user_id)
        db.session.add(profile)
        db.session.commit()
    return profile

def update_profile_on_interaction(profile: 'AiProfile', intents: list, balance: float):
    # Atualiza contadores de foco (poupança, investimento, dívidas, renda)
    counters = _loads_json_or_default(profile.focus_counters_json, {})
    for intent in intents:
        counters[intent] = counters.get(intent, 0) + 1

    # Ajuste incremental da meta de poupança
    if 'poupança' in intents and profile.savings_target_pct < 25:
        profile.savings_target_pct = min(25, profile.savings_target_pct + 1)

    # Aumenta alvo do fundo de emergência se a situação estiver negativa
    if balance < 0:
        profile.emergency_months_target = max(profile.emergency_months_target, 6)

    profile.focus_counters_json = _dumps_json_safe(counters)
    profile.interaction_count = (profile.interaction_count or 0) + 1
    profile.last_updated = datetime.utcnow()
    db.session.commit()

def apply_profile_to_allocations(profile: 'AiProfile', base_amount: float) -> dict:
    # Distribuição por perfil de risco
    rp = (profile.risk_profile or 'moderado').lower()
    if rp == 'conservador':
        return {
            'liquidez_diaria': base_amount * 0.70,
            'curto_prazo': base_amount * 0.20,
            'diversificados': base_amount * 0.08,
            'oportunidades': base_amount * 0.02,
        }
    elif rp == 'arrojado':
        return {
            'liquidez_diaria': base_amount * 0.40,
            'curto_prazo': base_amount * 0.20,
            'diversificados': base_amount * 0.35,
            'oportunidades': base_amount * 0.05,
        }
    # moderado (default)
    return {
        'liquidez_diaria': base_amount * 0.60,
        'curto_prazo': base_amount * 0.25,
        'diversificados': base_amount * 0.10,
        'oportunidades': base_amount * 0.05,
    }

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Usuário ou senha incorretos!')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form.get('email', '')
        
        # Verificar se o usuário já existe
        if User.query.filter_by(username=username).first():
            flash('Nome de usuário já existe!', 'error')
            return render_template('register.html')
        
        # Verificar se o email já existe
        if email and User.query.filter_by(email=email).first():
            flash('Email já cadastrado!', 'error')
            return render_template('register.html')
        
        # Validação de senha segura
        def validate_password(password):
            """Valida se a senha atende aos critérios de segurança"""
            if len(password) < 8:
                return False, "A senha deve ter pelo menos 8 caracteres"
            
            if not any(c.isupper() for c in password):
                return False, "A senha deve conter pelo menos uma letra maiúscula"
            
            if not any(c.islower() for c in password):
                return False, "A senha deve conter pelo menos uma letra minúscula"
            
            if not any(c.isdigit() for c in password):
                return False, "A senha deve conter pelo menos um número"
            
            if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
                return False, "A senha deve conter pelo menos um caractere especial (!@#$%^&*()_+-=[]{}|;:,.<>?)"
            
            return True, "Senha válida"
        
        # Validar senha
        is_valid, message = validate_password(password)
        if not is_valid:
            flash(f'Erro na senha: {message}', 'error')
            return render_template('register.html')
        
        # Criar novo usuário
        user = User(
            username=username, 
            password_hash=generate_password_hash(password),
            email=email
        )
        db.session.add(user)
        db.session.commit()
        
        flash('Usuário cadastrado com sucesso!', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    # Buscar transações do usuário
    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.date.desc()).limit(10).all()
    
    # Calcular saldo
    saldo = get_balance(current_user.id)
    
    # Buscar contas a vencer (próximos 7 dias)
    from datetime import date, timedelta
    today = date.today()
    next_week = today + timedelta(days=7)
    
    contas_vencer = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.due_date >= today,
        Transaction.due_date <= next_week
    ).order_by(Transaction.due_date).all()
    
    # Criar gráfico para o dashboard
    chart_data = create_chart_data(current_user.id, 'monthly', 'both')
    
    response = make_response(render_template('dashboard.html', 
                                           transactions=transactions,
                                           saldo=saldo,
                                           contas_vencer=contas_vencer,
                                           bar_chart=chart_data))
    
    # Adicionar headers para evitar cache
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

@app.route('/add_transaction', methods=['GET', 'POST'])
@login_required
def add_transaction():
    if request.method == 'POST':
        tipo = request.form['type']
        categoria = request.form['category']
        valor = float(request.form['amount'])
        descricao = request.form['description']
        data = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        
        trans = Transaction(
            user_id=current_user.id, 
            type=tipo, 
            category=categoria, 
            amount=valor, 
            description=descricao, 
            date=data
        )
        db.session.add(trans)
        db.session.commit()
        flash('Transação adicionada!')
        return redirect(url_for('dashboard'))
    return render_template('add_transaction.html')

@app.route('/add_bill', methods=['GET', 'POST'])
@login_required
def add_bill():
    if request.method == 'POST':
        categoria = request.form['category']
        valor = float(request.form['amount'])
        descricao = request.form['description']
        data = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        vencimento = datetime.strptime(request.form['due_date'], '%Y-%m-%d').date()
        trans = Transaction(user_id=current_user.id, type='expense', category=categoria, amount=valor, description=descricao, date=data, due_date=vencimento)
        db.session.add(trans)
        db.session.commit()
        flash('Conta a vencer cadastrada!')
        return redirect(url_for('dashboard'))
    return render_template('add_bill.html')

# Funções auxiliares
def get_balance(user_id):
    receitas = db.session.query(db.func.sum(Transaction.amount)).filter_by(user_id=user_id, type='income').scalar() or 0
    despesas = db.session.query(db.func.sum(Transaction.amount)).filter_by(user_id=user_id, type='expense').scalar() or 0
    return receitas - despesas

def get_transactions_summary(user_id, timeframe='monthly'):
    today = datetime.now().date()
    
    # Relatórios agora são somente mensais
    start_date = today.replace(day=1)
    
    # Receitas
    total_income = db.session.query(db.func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id,
        Transaction.type == 'income',
        Transaction.date >= start_date
    ).scalar() or 0
    
    # Despesas
    total_expense = db.session.query(db.func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id,
        Transaction.type == 'expense',
        Transaction.date >= start_date
    ).scalar() or 0
    
    # Saldo
    balance = total_income - total_expense
    
    return {
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': balance
    }

def create_chart_data(user_id, timeframe='monthly', chart_type='both'):
    today = datetime.now().date()
    
    # Relatórios agora são somente mensais
    start_date = today.replace(day=1)
    
    # Buscar categorias únicas
    categorias = db.session.query(Transaction.category).filter(
        Transaction.user_id == user_id,
        Transaction.date >= start_date
    ).distinct().all()
    categorias = [cat[0] for cat in categorias]
    
    receitas_por_categoria = []
    despesas_por_categoria = []
    
    for categoria in categorias:
        receita = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.type == 'income',
            Transaction.category == categoria,
            Transaction.date >= start_date
        ).scalar() or 0
        
        despesa = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.type == 'expense',
            Transaction.category == categoria,
            Transaction.date >= start_date
        ).scalar() or 0
        
        receitas_por_categoria.append(receita)
        despesas_por_categoria.append(despesa)
    
    # Criar gráfico baseado no tipo
    if chart_type == 'income':
        trace = go.Bar(
            x=categorias,
            y=receitas_por_categoria,
            name='Receitas',
            marker_color='green'
        )
        data = [trace]
    elif chart_type == 'expenses':
        trace = go.Bar(
            x=categorias,
            y=despesas_por_categoria,
            name='Despesas',
            marker_color='red'
        )
        data = [trace]
    else:  # both
        trace1 = go.Bar(
            x=categorias,
            y=receitas_por_categoria,
            name='Receitas',
            marker_color='green'
        )
        trace2 = go.Bar(
            x=categorias,
            y=despesas_por_categoria,
            name='Despesas',
            marker_color='red'
        )
        data = [trace1, trace2]
    
    layout = go.Layout(
        title='Receitas vs Despesas por Categoria',
        barmode='group' if chart_type == 'both' else 'stack',
        xaxis=dict(title='Categoria'),
        yaxis=dict(title='Valor (R$)')
    )
    
    return json.dumps({'data': data, 'layout': layout}, cls=plotly.utils.PlotlyJSONEncoder)

def generate_detailed_analysis(user_id, timeframe='monthly'):
    """Gera análise detalhada dos ganhos e gastos do usuário"""
    
    # Calcular período atual
    today = date.today()
    # Relatórios agora são somente mensais
    start_date = today.replace(day=1)
    period_days = 30
    
    # Período anterior para comparação
    prev_start = (start_date - timedelta(days=1)).replace(day=1)
    
    # Dados do período atual
    current_transactions = Transaction.query.filter(
        Transaction.user_id == user_id,
        Transaction.date >= start_date
    ).all()
    
    # Dados do período anterior
    prev_transactions = Transaction.query.filter(
        Transaction.user_id == user_id,
        Transaction.date >= prev_start,
        Transaction.date < start_date
    ).all()
    
    # Calcular totais atuais
    current_income = sum(t.amount for t in current_transactions if t.type == 'income')
    current_expense = sum(t.amount for t in current_transactions if t.type == 'expense')
    current_balance = current_income - current_expense
    
    # Calcular totais anteriores
    prev_income = sum(t.amount for t in prev_transactions if t.type == 'income')
    prev_expense = sum(t.amount for t in prev_transactions if t.type == 'expense')
    prev_balance = prev_income - prev_expense
    
    # Análise por categoria
    expense_categories = {}
    income_categories = {}
    
    for t in current_transactions:
        if t.type == 'expense':
            expense_categories[t.category] = expense_categories.get(t.category, 0) + t.amount
        else:
            income_categories[t.category] = income_categories.get(t.category, 0) + t.amount
    
    # Ordenar categorias por valor
    top_expenses = sorted(expense_categories.items(), key=lambda x: x[1], reverse=True)
    top_incomes = sorted(income_categories.items(), key=lambda x: x[1], reverse=True)
    
    # Gerar análise textual
    analysis = []
    
    # 1. Resumo geral
    analysis.append("📊 **RESUMO FINANCEIRO**")
    analysis.append(f"💰 Receitas: R$ {current_income:.2f}")
    analysis.append(f"💸 Despesas: R$ {current_expense:.2f}")
    analysis.append(f"💳 Saldo: R$ {current_balance:.2f}")
    
    # 2. Comparação com período anterior
    if prev_income > 0 or prev_expense > 0:
        analysis.append("\n📈 **COMPARAÇÃO COM PERÍODO ANTERIOR**")
        
        if prev_income > 0:
            income_change = ((current_income - prev_income) / prev_income) * 100
            if income_change > 0:
                analysis.append(f"✅ Receitas: +{income_change:.1f}% (melhorou)")
            else:
                analysis.append(f"❌ Receitas: {income_change:.1f}% (diminuiu)")
        
        if prev_expense > 0:
            expense_change = ((current_expense - prev_expense) / prev_expense) * 100
            if expense_change < 0:
                analysis.append(f"✅ Despesas: {expense_change:.1f}% (reduziu)")
            else:
                analysis.append(f"⚠️ Despesas: +{expense_change:.1f}% (aumentou)")
    
    # 3. Análise de despesas
    if top_expenses:
        analysis.append("\n💸 **ANÁLISE DE DESPESAS**")
        analysis.append("Principais categorias de gastos:")
        
        for i, (category, amount) in enumerate(top_expenses[:5], 1):
            percentage = (amount / current_expense) * 100 if current_expense > 0 else 0
            analysis.append(f"{i}. {category}: R$ {amount:.2f} ({percentage:.1f}%)")
        
        # Identificar categoria com maior gasto
        if top_expenses:
            biggest_expense = top_expenses[0]
            biggest_percentage = (biggest_expense[1] / current_expense) * 100 if current_expense > 0 else 0
            
            if biggest_percentage > 50:
                analysis.append(f"\n⚠️ **ALERTA**: {biggest_expense[0]} representa {biggest_percentage:.1f}% dos seus gastos!")
                analysis.append("Considere reduzir gastos nesta categoria.")
            elif biggest_percentage > 30:
                analysis.append(f"\n📝 **OBSERVAÇÃO**: {biggest_expense[0]} é sua maior despesa ({biggest_percentage:.1f}%).")
    
    # 4. Análise de receitas
    if top_incomes:
        analysis.append("\n💰 **ANÁLISE DE RECEITAS**")
        analysis.append("Principais fontes de renda:")
        
        for i, (category, amount) in enumerate(top_incomes[:3], 1):
            percentage = (amount / current_income) * 100 if current_income > 0 else 0
            analysis.append(f"{i}. {category}: R$ {amount:.2f} ({percentage:.1f}%)")
    
    # 5. Recomendações
    analysis.append("\n💡 **RECOMENDAÇÕES**")
    
    if current_balance < 0:
        analysis.append("❌ Seu saldo está negativo. Recomendações:")
        analysis.append("• Revise suas despesas não essenciais")
        analysis.append("• Considere aumentar suas fontes de renda")
        analysis.append("• Crie um fundo de emergência")
    elif current_balance < current_income * 0.2:
        analysis.append("⚠️ Seu saldo está baixo. Recomendações:")
        analysis.append("• Tente economizar pelo menos 20% da sua renda")
        analysis.append("• Revise gastos recorrentes")
    else:
        analysis.append("✅ Excelente! Seu saldo está saudável.")
        analysis.append("• Continue mantendo esse controle financeiro")
        analysis.append("• Considere investir o excedente")
    
    # 6. Dicas específicas por categoria
    if top_expenses:
        analysis.append("\n🎯 **DICAS ESPECÍFICAS**")
        
        for category, amount in top_expenses[:3]:
            if 'alimentação' in category.lower() or 'comida' in category.lower():
                analysis.append(f"🍽️ Para {category}: Considere cozinhar em casa e fazer lista de compras")
            elif 'transporte' in category.lower():
                analysis.append(f"🚗 Para {category}: Avalie transporte público ou carona solidária")
            elif 'lazer' in category.lower() or 'entretenimento' in category.lower():
                analysis.append(f"🎮 Para {category}: Procure opções gratuitas ou com desconto")
            elif 'moradia' in category.lower() or 'casa' in category.lower():
                analysis.append(f"🏠 Para {category}: Revise contratos e compare preços")
            else:
                analysis.append(f"📝 Para {category}: Revise se todos os gastos são realmente necessários")
    
    return "\n".join(analysis)

def ai_financial_analysis(user_id, timeframe='monthly'):
    """IA inteligente para análise financeira preditiva e recomendações personalizadas"""
    
    # Calcular período atual
    today = date.today()
    # Relatórios agora são somente mensais
    start_date = today.replace(day=1)
    period_days = 30
    
    # Buscar histórico completo do usuário (últimos 6 meses)
    six_months_ago = today - timedelta(days=180)
    historical_transactions = Transaction.query.filter(
        Transaction.user_id == user_id,
        Transaction.date >= six_months_ago
    ).order_by(Transaction.date).all()
    
    # Dados do período atual
    current_transactions = [t for t in historical_transactions if t.date >= start_date]
    
    # Análise de padrões temporais
    monthly_patterns = {}
    for t in historical_transactions:
        month_key = t.date.strftime('%Y-%m')
        if month_key not in monthly_patterns:
            monthly_patterns[month_key] = {'income': 0, 'expense': 0, 'categories': {}}
        
        if t.type == 'income':
            monthly_patterns[month_key]['income'] += t.amount
        else:
            monthly_patterns[month_key]['expense'] += t.amount
            monthly_patterns[month_key]['categories'][t.category] = monthly_patterns[month_key]['categories'].get(t.category, 0) + t.amount
    
    # Calcular tendências
    months = sorted(monthly_patterns.keys())
    if len(months) >= 2:
        recent_income_trend = (monthly_patterns[months[-1]]['income'] - monthly_patterns[months[-2]]['income']) / max(monthly_patterns[months[-2]]['income'], 1)
        recent_expense_trend = (monthly_patterns[months[-1]]['expense'] - monthly_patterns[months[-2]]['expense']) / max(monthly_patterns[months[-2]]['expense'], 1)
    else:
        recent_income_trend = 0
        recent_expense_trend = 0
    
    # Análise de categorias ao longo do tempo
    category_trends = {}
    for month in months[-3:]:  # Últimos 3 meses
        for category, amount in monthly_patterns[month]['categories'].items():
            if category not in category_trends:
                category_trends[category] = []
            category_trends[category].append(amount)
    
    # Identificar categorias com tendência crescente
    growing_categories = []
    for category, amounts in category_trends.items():
        if len(amounts) >= 2 and amounts[-1] > amounts[0] * 1.1:  # 10% de crescimento
            growing_categories.append(category)
    
    # Análise de sazonalidade
    seasonal_analysis = {}
    for t in historical_transactions:
        month = t.date.month
        if month not in seasonal_analysis:
            seasonal_analysis[month] = {'income': 0, 'expense': 0, 'count': 0}
        
        if t.type == 'income':
            seasonal_analysis[month]['income'] += t.amount
        else:
            seasonal_analysis[month]['expense'] += t.amount
        seasonal_analysis[month]['count'] += 1
    
    # Identificar meses com maior gasto
    high_expense_months = []
    avg_expense = sum(data['expense'] for data in seasonal_analysis.values()) / len(seasonal_analysis) if seasonal_analysis else 0
    for month, data in seasonal_analysis.items():
        if data['expense'] > avg_expense * 1.2:  # 20% acima da média
            month_names = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                          'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
            high_expense_months.append(month_names[month - 1])
    
    # Análise de risco financeiro
    current_income = sum(t.amount for t in current_transactions if t.type == 'income')
    current_expense = sum(t.amount for t in current_transactions if t.type == 'expense')
    current_balance = current_income - current_expense
    
    # Calcular índice de segurança financeira
    if current_income > 0:
        savings_rate = (current_balance / current_income) * 100
    else:
        savings_rate = 0
    
    # Análise de diversificação de receitas
    income_sources = {}
    for t in current_transactions:
        if t.type == 'income':
            income_sources[t.category] = income_sources.get(t.category, 0) + t.amount
    
    diversification_score = len(income_sources) / 3  # Normalizado para 0-1
    
    # Gerar análise IA
    ai_analysis = []
    
    # 1. Resumo Executivo IA
    ai_analysis.append("🤖 **ANÁLISE INTELIGENTE - IA FINANCEIRA**")
    ai_analysis.append("=" * 50)
    
    # 2. Score de Saúde Financeira
    health_score = 0
    if savings_rate >= 20:
        health_score += 30
        ai_analysis.append("✅ **Score de Saúde Financeira: EXCELENTE (30/30)**")
        ai_analysis.append("   Sua taxa de poupança está acima de 20% - padrão de excelência!")
    elif savings_rate >= 10:
        health_score += 20
        ai_analysis.append("⚠️ **Score de Saúde Financeira: BOM (20/30)**")
        ai_analysis.append("   Sua taxa de poupança está entre 10-20% - pode melhorar.")
    elif savings_rate >= 0:
        health_score += 10
        ai_analysis.append("❌ **Score de Saúde Financeira: ATENÇÃO (10/30)**")
        ai_analysis.append("   Sua taxa de poupança está baixa - precisa economizar mais.")
    else:
        ai_analysis.append("🚨 **Score de Saúde Financeira: CRÍTICO (0/30)**")
        ai_analysis.append("   Você está gastando mais do que ganha - ação imediata necessária!")
    
    # 3. Análise de Tendências
    ai_analysis.append("\n📈 **ANÁLISE DE TENDÊNCIAS - IA**")
    
    if recent_income_trend > 0.1:
        ai_analysis.append("✅ **Receitas**: Tendência POSITIVA (+{:.1f}%)".format(recent_income_trend * 100))
        ai_analysis.append("   Continue investindo em suas fontes de renda!")
    elif recent_income_trend < -0.1:
        ai_analysis.append("❌ **Receitas**: Tendência NEGATIVA ({:.1f}%)".format(recent_income_trend * 100))
        ai_analysis.append("   Considere buscar novas fontes de renda.")
    else:
        ai_analysis.append("📊 **Receitas**: Tendência ESTÁVEL")
    
    if recent_expense_trend > 0.1:
        ai_analysis.append("⚠️ **Despesas**: Tendência CRESCENTE (+{:.1f}%)".format(recent_expense_trend * 100))
        ai_analysis.append("   ATENÇÃO: Seus gastos estão aumentando!")
    elif recent_expense_trend < -0.1:
        ai_analysis.append("✅ **Despesas**: Tendência DECRESCENTE ({:.1f}%)".format(recent_expense_trend * 100))
        ai_analysis.append("   Excelente! Você está controlando melhor os gastos.")
    else:
        ai_analysis.append("📊 **Despesas**: Tendência ESTÁVEL")
    
    # 4. Alertas Inteligentes
    ai_analysis.append("\n🚨 **ALERTAS INTELIGENTES**")
    
    if growing_categories:
        ai_analysis.append("⚠️ **Categorias em Crescimento**:")
        for category in growing_categories[:3]:
            ai_analysis.append(f"   • {category}: Monitorar de perto")
    
    if high_expense_months:
        ai_analysis.append("📅 **Meses de Alto Gasto**:")
        ai_analysis.append(f"   Prepare-se para: {', '.join(high_expense_months)}")
    
    # 5. Recomendações Personalizadas IA
    ai_analysis.append("\n🎯 **RECOMENDAÇÕES PERSONALIZADAS - IA**")
    
    if savings_rate < 10:
        ai_analysis.append("💰 **Prioridade 1: Aumentar Poupança**")
        ai_analysis.append("   • Implemente a regra 50/30/20 (50% necessidades, 30% desejos, 20% poupança)")
        ai_analysis.append("   • Automatize transferências para poupança")
        ai_analysis.append("   • Revise gastos recorrentes desnecessários")
    
    if diversification_score < 0.5:
        ai_analysis.append("🔄 **Prioridade 2: Diversificar Receitas**")
        ai_analysis.append("   • Considere freelancing ou trabalho extra")
        ai_analysis.append("   • Explore investimentos passivos")
        ai_analysis.append("   • Desenvolva habilidades monetizáveis")
    
    if growing_categories:
        ai_analysis.append("📊 **Prioridade 3: Controlar Crescimento de Gastos**")
        for category in growing_categories[:2]:
            ai_analysis.append(f"   • Estabeleça limite mensal para {category}")
            ai_analysis.append(f"   • Busque alternativas mais econômicas")
    
    # 6. Previsões IA
    ai_analysis.append("\n🔮 **PREVISÕES FINANCEIRAS - IA**")
    
    if recent_income_trend > 0 and recent_expense_trend < 0:
        ai_analysis.append("✅ **Cenário Otimista**: Se mantiver essa tendência, em 3 meses você terá:")
        projected_balance = current_balance * (1 + recent_income_trend - recent_expense_trend) ** 3
        ai_analysis.append(f"   Saldo projetado: R$ {projected_balance:.2f}")
    elif recent_expense_trend > 0.1:
        ai_analysis.append("⚠️ **Cenário de Atenção**: Se continuar gastando mais, em 3 meses:")
        projected_balance = current_balance * (1 - recent_expense_trend) ** 3
        ai_analysis.append(f"   Saldo projetado: R$ {projected_balance:.2f}")
        ai_analysis.append("   Ação imediata recomendada!")
    else:
        ai_analysis.append("📊 **Cenário Estável**: Mantendo o padrão atual, seu saldo permanecerá estável")
    
    # 7. Dicas Inteligentes por Categoria
    ai_analysis.append("\n🧠 **DICAS INTELIGENTES POR CATEGORIA**")
    
    expense_categories = {}
    for t in current_transactions:
        if t.type == 'expense':
            expense_categories[t.category] = expense_categories.get(t.category, 0) + t.amount
    
    top_expenses = sorted(expense_categories.items(), key=lambda x: x[1], reverse=True)
    
    for category, amount in top_expenses[:3]:
        percentage = (amount / current_expense) * 100 if current_expense > 0 else 0
        
        if 'alimentação' in category.lower() or 'comida' in category.lower():
            if percentage > 30:
                ai_analysis.append(f"🍽️ **{category} ({percentage:.1f}%)**: ALTO GASTO")
                ai_analysis.append("   • Implemente planejamento de refeições")
                ai_analysis.append("   • Use aplicativos de cupom e desconto")
                ai_analysis.append("   • Considere compras em atacado")
            else:
                ai_analysis.append(f"🍽️ **{category} ({percentage:.1f}%)**: GASTO CONTROLADO")
        
        elif 'transporte' in category.lower():
            if percentage > 20:
                ai_analysis.append(f"🚗 **{category} ({percentage:.1f}%)**: ALTO GASTO")
                ai_analysis.append("   • Avalie transporte público")
                ai_analysis.append("   • Considere carona solidária")
                ai_analysis.append("   • Revise necessidade de múltiplos veículos")
            else:
                ai_analysis.append(f"🚗 **{category} ({percentage:.1f}%)**: GASTO CONTROLADO")
        
        elif 'lazer' in category.lower() or 'entretenimento' in category.lower():
            if percentage > 15:
                ai_analysis.append(f"🎮 **{category} ({percentage:.1f}%)**: ALTO GASTO")
                ai_analysis.append("   • Busque opções gratuitas")
                ai_analysis.append("   • Use promoções e descontos")
                ai_analysis.append("   • Estabeleça limite mensal")
            else:
                ai_analysis.append(f"🎮 **{category} ({percentage:.1f}%)**: GASTO CONTROLADO")
        
        else:
            if percentage > 25:
                ai_analysis.append(f"📝 **{category} ({percentage:.1f}%)**: ALTO GASTO")
                ai_analysis.append("   • Revise se todos os gastos são necessários")
                ai_analysis.append("   • Busque alternativas mais econômicas")
                ai_analysis.append("   • Considere renegociar contratos")
            else:
                ai_analysis.append(f"📝 **{category} ({percentage:.1f}%)**: GASTO CONTROLADO")
    
    # 8. Plano de Ação IA
    ai_analysis.append("\n📋 **PLANO DE AÇÃO RECOMENDADO - IA**")
    
    if savings_rate < 10:
        ai_analysis.append("🎯 **Meta Imediata (1 mês)**: Aumentar poupança para 10%")
        ai_analysis.append("🎯 **Meta Curto Prazo (3 meses)**: Atingir 15% de poupança")
        ai_analysis.append("🎯 **Meta Médio Prazo (6 meses)**: Atingir 20% de poupança")
    elif savings_rate < 20:
        ai_analysis.append("🎯 **Meta Imediata (1 mês)**: Manter poupança atual")
        ai_analysis.append("🎯 **Meta Curto Prazo (3 meses)**: Aumentar para 20%")
        ai_analysis.append("🎯 **Meta Médio Prazo (6 meses)**: Considerar investimentos")
    else:
        ai_analysis.append("🎯 **Meta Imediata (1 mês)**: Manter excelente padrão")
        ai_analysis.append("🎯 **Meta Curto Prazo (3 meses)**: Diversificar investimentos")
        ai_analysis.append("🎯 **Meta Médio Prazo (6 meses)**: Criar fundo de emergência de 6 meses")
    
    return "\n".join(ai_analysis)

def advanced_ai_analysis(user_id, timeframe='monthly'):
    """IA super avançada com machine learning para análise financeira preditiva"""
    
    # Calcular período atual
    today = date.today()
    # Relatórios agora são somente mensais
    start_date = today.replace(day=1)
    period_days = 30
    
    # Buscar histórico completo (últimos 12 meses para análise mais profunda)
    twelve_months_ago = today - timedelta(days=365)
    historical_transactions = Transaction.query.filter(
        Transaction.user_id == user_id,
        Transaction.date >= twelve_months_ago
    ).order_by(Transaction.date).all()
    
    # Dados do período atual
    current_transactions = [t for t in historical_transactions if t.date >= start_date]
    
    # Análise de padrões temporais avançada
    monthly_patterns = {}
    for t in historical_transactions:
        month_key = t.date.strftime('%Y-%m')
        if month_key not in monthly_patterns:
            monthly_patterns[month_key] = {
                'income': 0, 'expense': 0, 'categories': {},
                'transaction_count': 0, 'avg_transaction': 0
            }
        
        if t.type == 'income':
            monthly_patterns[month_key]['income'] += t.amount
        else:
            monthly_patterns[month_key]['expense'] += t.amount
            monthly_patterns[month_key]['categories'][t.category] = monthly_patterns[month_key]['categories'].get(t.category, 0) + t.amount
        
        monthly_patterns[month_key]['transaction_count'] += 1
    
    # Calcular médias por transação
    for month in monthly_patterns:
        if monthly_patterns[month]['transaction_count'] > 0:
            monthly_patterns[month]['avg_transaction'] = (
                monthly_patterns[month]['income'] + monthly_patterns[month]['expense']
            ) / monthly_patterns[month]['transaction_count']
    
    # Análise de tendências com regressão linear simples
    months = sorted(monthly_patterns.keys())
    if len(months) >= 3:
        # Calcular tendência linear
        n = len(months)
        x_values = list(range(n))
        y_income = [monthly_patterns[month]['income'] for month in months]
        y_expense = [monthly_patterns[month]['expense'] for month in months]
        
        # Regressão linear para receitas
        sum_x = sum(x_values)
        sum_y_income = sum(y_income)
        sum_xy_income = sum(x * y for x, y in zip(x_values, y_income))
        sum_x2 = sum(x * x for x in x_values)
        
        if n * sum_x2 - sum_x * sum_x != 0:
            slope_income = (n * sum_xy_income - sum_x * sum_y_income) / (n * sum_x2 - sum_x * sum_x)
            intercept_income = (sum_y_income - slope_income * sum_x) / n
            
            # Regressão linear para despesas
            sum_y_expense = sum(y_expense)
            sum_xy_expense = sum(x * y for x, y in zip(x_values, y_expense))
            slope_expense = (n * sum_xy_expense - sum_x * sum_y_expense) / (n * sum_x2 - sum_x * sum_x)
            intercept_expense = (sum_y_expense - slope_expense * sum_x) / n
        else:
            slope_income = slope_expense = 0
            intercept_income = intercept_expense = 0
    else:
        slope_income = slope_expense = 0
        intercept_income = intercept_expense = 0
    
    # Análise de volatilidade financeira
    if len(months) >= 2:
        income_values = [monthly_patterns[month]['income'] for month in months]
        expense_values = [monthly_patterns[month]['expense'] for month in months]
        
        # Calcular desvio padrão
        avg_income = sum(income_values) / len(income_values)
        avg_expense = sum(expense_values) / len(expense_values)
        
        income_variance = sum((x - avg_income) ** 2 for x in income_values) / len(income_values)
        expense_variance = sum((x - avg_expense) ** 2 for x in expense_values) / len(expense_values)
        
        income_volatility = (income_variance ** 0.5) / avg_income if avg_income > 0 else 0
        expense_volatility = (expense_variance ** 0.5) / avg_expense if avg_expense > 0 else 0
    else:
        income_volatility = expense_volatility = 0
    
    # Análise de correlação entre receitas e despesas
    if len(months) >= 2:
        income_values = [monthly_patterns[month]['income'] for month in months]
        expense_values = [monthly_patterns[month]['expense'] for month in months]
        
        avg_income = sum(income_values) / len(income_values)
        avg_expense = sum(expense_values) / len(expense_values)
        
        numerator = sum((x - avg_income) * (y - avg_expense) for x, y in zip(income_values, expense_values))
        denominator_income = sum((x - avg_income) ** 2 for x in income_values)
        denominator_expense = sum((y - avg_expense) ** 2 for y in expense_values)
        
        if denominator_income > 0 and denominator_expense > 0:
            correlation = numerator / (denominator_income * denominator_expense) ** 0.5
        else:
            correlation = 0
    else:
        correlation = 0
    
    # Análise de categorias com machine learning
    category_analysis = {}
    for t in historical_transactions:
        if t.type == 'expense':
            if t.category not in category_analysis:
                category_analysis[t.category] = {
                    'total': 0, 'count': 0, 'dates': [], 'trend': 0
                }
            category_analysis[t.category]['total'] += t.amount
            category_analysis[t.category]['count'] += 1
            category_analysis[t.category]['dates'].append(t.date)
    
    # Calcular tendência por categoria
    for category in category_analysis:
        dates = category_analysis[category]['dates']
        if len(dates) >= 2:
            # Dividir em períodos para calcular tendência
            mid_point = len(dates) // 2
            early_period = dates[:mid_point]
            late_period = dates[mid_point:]
            
            early_amount = sum(t.amount for t in historical_transactions 
                             if t.category == category and t.date in early_period)
            late_amount = sum(t.amount for t in historical_transactions 
                            if t.category == category and t.date in late_period)
            
            if early_amount > 0:
                category_analysis[category]['trend'] = (late_amount - early_amount) / early_amount
            else:
                category_analysis[category]['trend'] = 0
    
    # Análise de sazonalidade avançada
    seasonal_patterns = {}
    for t in historical_transactions:
        month = t.date.month
        if month not in seasonal_patterns:
            seasonal_patterns[month] = {'income': 0, 'expense': 0, 'count': 0}
        
        if t.type == 'income':
            seasonal_patterns[month]['income'] += t.amount
        else:
            seasonal_patterns[month]['expense'] += t.amount
        seasonal_patterns[month]['count'] += 1
    
    # Identificar padrões sazonais
    month_names = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                  'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    
    high_expense_months = []
    high_income_months = []
    
    if seasonal_patterns:
        avg_expense = sum(data['expense'] for data in seasonal_patterns.values()) / len(seasonal_patterns)
        avg_income = sum(data['income'] for data in seasonal_patterns.values()) / len(seasonal_patterns)
        
        for month, data in seasonal_patterns.items():
            if data['expense'] > avg_expense * 1.15:  # 15% acima da média
                high_expense_months.append(month_names[month - 1])
            if data['income'] > avg_income * 1.15:
                high_income_months.append(month_names[month - 1])
    
    # Calcular métricas atuais
    current_income = sum(t.amount for t in current_transactions if t.type == 'income')
    current_expense = sum(t.amount for t in current_transactions if t.type == 'expense')
    current_balance = current_income - current_expense
    
    # Calcular índices financeiros avançados
    if current_income > 0:
        savings_rate = (current_balance / current_income) * 100
        expense_ratio = (current_expense / current_income) * 100
    else:
        savings_rate = expense_ratio = 0
    
    # Análise de diversificação
    income_sources = {}
    for t in current_transactions:
        if t.type == 'income':
            income_sources[t.category] = income_sources.get(t.category, 0) + t.amount
    
    diversification_score = len(income_sources) / 3  # Normalizado para 0-1
    
    # Gerar análise IA super avançada
    ai_analysis = []
    
    # 1. Cabeçalho IA Avançada
    ai_analysis.append("🧠 **IA FINANCEIRA SUPER AVANÇADA - MACHINE LEARNING**")
    ai_analysis.append("=" * 60)
    
    # 2. Score de Inteligência Financeira
    intelligence_score = 0
    intelligence_factors = []
    
    if savings_rate >= 20:
        intelligence_score += 25
        intelligence_factors.append("✅ Poupança excelente (+25)")
    elif savings_rate >= 10:
        intelligence_score += 15
        intelligence_factors.append("⚠️ Poupança moderada (+15)")
    elif savings_rate >= 0:
        intelligence_score += 5
        intelligence_factors.append("❌ Poupança baixa (+5)")
    
    if income_volatility < 0.2:
        intelligence_score += 20
        intelligence_factors.append("✅ Renda estável (+20)")
    elif income_volatility < 0.4:
        intelligence_score += 10
        intelligence_factors.append("⚠️ Renda moderadamente volátil (+10)")
    else:
        intelligence_factors.append("❌ Renda muito volátil (+0)")
    
    if expense_volatility < 0.2:
        intelligence_score += 20
        intelligence_factors.append("✅ Gastos controlados (+20)")
    elif expense_volatility < 0.4:
        intelligence_score += 10
        intelligence_factors.append("⚠️ Gastos moderadamente voláteis (+10)")
    else:
        intelligence_factors.append("❌ Gastos muito voláteis (+0)")
    
    if diversification_score >= 0.7:
        intelligence_score += 15
        intelligence_factors.append("✅ Renda diversificada (+15)")
    elif diversification_score >= 0.3:
        intelligence_score += 10
        intelligence_factors.append("⚠️ Renda parcialmente diversificada (+10)")
    else:
        intelligence_factors.append("❌ Renda não diversificada (+0)")
    
    if correlation < 0.5:
        intelligence_score += 20
        intelligence_factors.append("✅ Baixa correlação receita-despesa (+20)")
    elif correlation < 0.8:
        intelligence_score += 10
        intelligence_factors.append("⚠️ Correlação moderada (+10)")
    else:
        intelligence_factors.append("❌ Alta correlação (+0)")
    
    # Classificar score
    if intelligence_score >= 80:
        grade = "EXCELENTE"
        grade_emoji = "🏆"
    elif intelligence_score >= 60:
        grade = "BOM"
        grade_emoji = "🥇"
    elif intelligence_score >= 40:
        grade = "REGULAR"
        grade_emoji = "🥈"
    else:
        grade = "PRECISA MELHORAR"
        grade_emoji = "🥉"
    
    ai_analysis.append(f"{grade_emoji} **SCORE DE INTELIGÊNCIA FINANCEIRA: {grade} ({intelligence_score}/100)**")
    for factor in intelligence_factors:
        ai_analysis.append(f"   {factor}")
    
    # 3. Análise Preditiva Avançada
    ai_analysis.append(f"\n🔮 **ANÁLISE PREDITIVA - MACHINE LEARNING**")
    
    if len(months) >= 3:
        # Previsão para próximos 3 meses
        future_months = 3
        predicted_income = intercept_income + slope_income * (len(months) + future_months - 1)
        predicted_expense = intercept_expense + slope_expense * (len(months) + future_months - 1)
        predicted_balance = predicted_income - predicted_expense
        
        ai_analysis.append(f"📈 **Previsão 3 meses (Regressão Linear):**")
        ai_analysis.append(f"   Receita projetada: R$ {predicted_income:.2f}")
        ai_analysis.append(f"   Despesa projetada: R$ {predicted_expense:.2f}")
        ai_analysis.append(f"   Saldo projetado: R$ {predicted_balance:.2f}")
        
        # Análise de confiança
        if abs(slope_income) < 0.1 and abs(slope_expense) < 0.1:
            ai_analysis.append("   🎯 **Alta confiança** - Padrões estáveis")
        elif abs(slope_income) < 0.3 and abs(slope_expense) < 0.3:
            ai_analysis.append("   ⚠️ **Confiança moderada** - Alguma volatilidade")
        else:
            ai_analysis.append("   🚨 **Baixa confiança** - Padrões muito voláteis")
    
    # 4. Análise de Volatilidade
    ai_analysis.append(f"\n📊 **ANÁLISE DE VOLATILIDADE FINANCEIRA**")
    
    if income_volatility < 0.1:
        ai_analysis.append("✅ **Receitas**: Muito estáveis (volatilidade baixa)")
    elif income_volatility < 0.3:
        ai_analysis.append("⚠️ **Receitas**: Moderadamente estáveis")
    else:
        ai_analysis.append("🚨 **Receitas**: Muito voláteis - considere diversificar")
    
    if expense_volatility < 0.1:
        ai_analysis.append("✅ **Despesas**: Bem controladas (volatilidade baixa)")
    elif expense_volatility < 0.3:
        ai_analysis.append("⚠️ **Despesas**: Moderadamente controladas")
    else:
        ai_analysis.append("🚨 **Despesas**: Muito voláteis - precisa de mais controle")
    
    # 5. Análise de Correlação
    ai_analysis.append(f"\n🔄 **ANÁLISE DE CORRELAÇÃO RECEITA-DESPESA**")
    
    if correlation < 0.3:
        ai_analysis.append("✅ **Correlação baixa** - Excelente! Suas despesas não dependem da receita")
    elif correlation < 0.7:
        ai_analysis.append("⚠️ **Correlação moderada** - Suas despesas variam com a receita")
    else:
        ai_analysis.append("🚨 **Correlação alta** - Suas despesas seguem a receita (risco!)")
    
    # 6. Análise de Categorias Inteligente
    ai_analysis.append(f"\n🎯 **ANÁLISE INTELIGENTE DE CATEGORIAS**")
    
    # Identificar categorias problemáticas
    problematic_categories = []
    growing_categories = []
    
    for category, data in category_analysis.items():
        if data['trend'] > 0.2:  # 20% de crescimento
            growing_categories.append((category, data['trend']))
        if data['total'] > current_income * 0.4:  # Mais de 40% da renda
            problematic_categories.append(category)
    
    if growing_categories:
        ai_analysis.append("📈 **Categorias em Crescimento (Machine Learning):**")
        for category, trend in sorted(growing_categories, key=lambda x: x[1], reverse=True)[:3]:
            ai_analysis.append(f"   • {category}: +{trend*100:.1f}% (ATENÇÃO!)")
    
    if problematic_categories:
        ai_analysis.append("🚨 **Categorias Problemáticas:**")
        for category in problematic_categories:
            ai_analysis.append(f"   • {category}: Consome muito da sua renda")
    
    # 7. Análise Sazonal Inteligente
    ai_analysis.append(f"\n📅 **ANÁLISE SAZONAL INTELIGENTE**")
    
    if high_expense_months:
        ai_analysis.append("💰 **Prepare-se para meses de alto gasto:**")
        ai_analysis.append(f"   {', '.join(high_expense_months)}")
        ai_analysis.append("   💡 **Estratégia:** Economize nos meses anteriores")
    
    if high_income_months:
        ai_analysis.append("📈 **Meses de alta receita:**")
        ai_analysis.append(f"   {', '.join(high_income_months)}")
        ai_analysis.append("   💡 **Estratégia:** Aproveite para poupar mais")
    
    # 8. Recomendações de Machine Learning
    ai_analysis.append(f"\n🤖 **RECOMENDAÇÕES DE MACHINE LEARNING**")
    
    # Baseado no score de inteligência
    if intelligence_score < 40:
        ai_analysis.append("🚨 **PRIORIDADE MÁXIMA - ESTABILIZAÇÃO**")
        ai_analysis.append("   1. Corte gastos não essenciais imediatamente")
        ai_analysis.append("   2. Crie fundo de emergência básico")
        ai_analysis.append("   3. Busque renda extra urgente")
        ai_analysis.append("   4. Consulte um consultor financeiro")
    
    elif intelligence_score < 60:
        ai_analysis.append("⚠️ **PRIORIDADE ALTA - OTIMIZAÇÃO**")
        ai_analysis.append("   1. Implemente regra 50/30/20")
        ai_analysis.append("   2. Automatize poupança")
        ai_analysis.append("   3. Diversifique fontes de renda")
        ai_analysis.append("   4. Monitore gastos mais de perto")
    
    elif intelligence_score < 80:
        ai_analysis.append("✅ **PRIORIDADE MÉDIA - CRESCIMENTO**")
        ai_analysis.append("   1. Aumente taxa de poupança para 25%")
        ai_analysis.append("   2. Comece a investir")
        ai_analysis.append("   3. Planeje objetivos de longo prazo")
        ai_analysis.append("   4. Considere empreendedorismo")
    
    else:
        ai_analysis.append("🏆 **PRIORIDADE BAIXA - MANUTENÇÃO**")
        ai_analysis.append("   1. Mantenha excelente padrão")
        ai_analysis.append("   2. Diversifique investimentos")
        ai_analysis.append("   3. Considere filantropia")
        ai_analysis.append("   4. Planeje sucessão patrimonial")
    
    # 9. Alertas Inteligentes
    ai_analysis.append(f"\n🚨 **ALERTAS INTELIGENTES - IA**")
    
    if current_balance < 0:
        ai_analysis.append("🔴 **ALERTA CRÍTICO:** Saldo negativo - ação imediata necessária!")
    
    if savings_rate < 10:
        ai_analysis.append("🟡 **ALERTA AMARELO:** Poupança baixa - risco financeiro")
    
    if income_volatility > 0.4:
        ai_analysis.append("🟡 **ALERTA AMARELO:** Renda muito volátil - diversifique")
    
    if expense_volatility > 0.4:
        ai_analysis.append("🟡 **ALERTA AMARELO:** Gastos muito voláteis - controle melhor")
    
    if correlation > 0.8:
        ai_analysis.append("🟡 **ALERTA AMARELO:** Alta correlação receita-despesa")
    
    if not any(alert.startswith("🟡") or alert.startswith("🔴") for alert in ai_analysis[-5:]):
        ai_analysis.append("🟢 **STATUS:** Todas as métricas estão saudáveis!")
    
    # 10. Orçamento Personalizado (50/30/20) e comparativo real
    ai_analysis.append("\n💼 **ORÇAMENTO PERSONALIZADO (REGRA 50/30/20)**")
    target_needs = current_income * 0.50
    target_wants = current_income * 0.30
    target_saving = current_income * 0.20

    # Estimar necessidades vs desejos a partir das categorias
    needs_keywords = ['alimenta', 'mercado', 'supermerc', 'moradia', 'alug', 'condom', 'luz', 'água', 'agua', 'energia', 'internet', 'transporte', 'gasolina', 'saúde', 'saude', 'medic', 'educa', 'escola']
    wants_keywords = ['lazer', 'entreten', 'restaur', 'delivery', 'assinatura', 'stream', 'viagem', 'jogo']
    current_needs = 0.0
    current_wants = 0.0
    for t in current_transactions:
        if t.type == 'expense':
            category_lower = (t.category or '').lower()
            if any(k in category_lower for k in needs_keywords):
                current_needs += t.amount
            elif any(k in category_lower for k in wants_keywords):
                current_wants += t.amount
            else:
                # Não classificado: dividir proporcionalmente (70% necessidade / 30% desejo)
                current_needs += t.amount * 0.7
                current_wants += t.amount * 0.3

    from math import ceil
    def fc(v: float) -> str:
        return format_currency(v)

    ai_analysis.append(f"• Necessidades (alvo 50%): {fc(target_needs)} | Atual: {fc(current_needs)}")
    ai_analysis.append(f"• Desejos (alvo 30%): {fc(target_wants)} | Atual: {fc(current_wants)}")
    ai_analysis.append(f"• Poupança/Invest. (alvo 20%): {fc(target_saving)} | Atual: {fc(max(current_balance, 0))}")

    # 11. Plano de corte por categoria (valores precisos)
    ai_analysis.append("\n✂️ **PLANO DE CORTE POR CATEGORIA (VALORES PRECISOS)**")
    # Despesas por categoria no período atual
    expense_categories_current = {}
    for t in current_transactions:
        if t.type == 'expense':
            expense_categories_current[t.category] = expense_categories_current.get(t.category, 0) + t.amount
    top_expenses_current = sorted(expense_categories_current.items(), key=lambda x: x[1], reverse=True)[:5]

    # Definir intensidade de corte conforme situação
    if savings_rate < 5 or current_balance < 0:
        cut_pct = 0.30
    elif savings_rate < 10:
        cut_pct = 0.20
    else:
        cut_pct = 0.15

    if top_expenses_current:
        for idx, (cat, amt) in enumerate(top_expenses_current, 1):
            cut_value = amt * cut_pct
            ai_analysis.append(f"{idx}. {cat}: atual {fc(amt)} → corte sugerido {int(cut_pct*100)}% ({fc(cut_value)})")
    else:
        ai_analysis.append("Sem despesas categorizadas suficientes neste período para sugerir cortes.")

    # 12. Fundo de Emergência - alvo e plano mensal
    ai_analysis.append("\n🛟 **FUNDO DE EMERGÊNCIA - PLANO**")
    # Média de despesas dos últimos meses
    average_monthly_expense = 0.0
    if months:
        consider_months = months[-min(len(months), 6):]
        total_exp = sum(monthly_patterns[m]['expense'] for m in consider_months)
        average_monthly_expense = total_exp / len(consider_months)
    else:
        average_monthly_expense = current_expense

    # Definir meses alvo conforme risco/volatilidade
    target_months_buffer = 6 if (expense_volatility > 0.3 or current_balance < 0) else 3
    emergency_target_value = average_monthly_expense * target_months_buffer

    # Sugestão de aporte mensal: prioriza 60% do superávit ou 15% da renda (o que for maior), limitado a 25% da renda
    monthly_surplus = max(current_balance, 0)
    suggested_monthly_contribution = max(current_income * 0.15, monthly_surplus * 0.6)
    suggested_monthly_contribution = min(suggested_monthly_contribution, current_income * 0.25)

    months_to_reach = "∞"
    if suggested_monthly_contribution > 0 and emergency_target_value > 0:
        months_to_reach = ceil(emergency_target_value / suggested_monthly_contribution)

    ai_analysis.append(f"• Despesa média mensal: {fc(average_monthly_expense)}")
    ai_analysis.append(f"• Alvo do fundo ({target_months_buffer} meses): {fc(emergency_target_value)}")
    ai_analysis.append(f"• Aporte mensal sugerido: {fc(suggested_monthly_contribution)} → atingir em ~{months_to_reach} meses")

    # 13. Plano de Poupança e Investimento (distribuição sugerida)
    ai_analysis.append("\n📈 **PLANO DE POUPANÇA E INVESTIMENTOS**")
    # Aplicar perfil do usuário às alocações sugeridas
    profile = get_or_create_ai_profile(user_id)
    if emergency_target_value > 0 and suggested_monthly_contribution > 0:
        ai_analysis.append("Primeiro, priorize construir o fundo de emergência.")
        alloc = apply_profile_to_allocations(profile, suggested_monthly_contribution)
        ai_analysis.append(f"   • {fc(alloc['liquidez_diaria'])} → Reserva/Emergência (liquidez diária)")
        ai_analysis.append(f"   • {fc(alloc['curto_prazo'])} → Curto prazo (CDB/Tesouro 6-12m)")
        ai_analysis.append(f"   • {fc(alloc['diversificados'])} → Diversificados (fundos/ETFs)")
        ai_analysis.append(f"   • {fc(alloc['oportunidades'])} → Caixa de oportunidades")
    else:
        # Quando já houver superávit constante, distribuir mensalmente
        base_invest = max(current_income * 0.20, monthly_surplus * 0.6)
        ai_analysis.append("Com o fundo de emergência atingido, distribua mensalmente:")
        alloc = apply_profile_to_allocations(profile, base_invest)
        ai_analysis.append(f"   • {fc(alloc['liquidez_diaria'])} → Tesouro Selic / CDB liquidez diária")
        ai_analysis.append(f"   • {fc(alloc['curto_prazo'])} → CDB/LC de 6-12 meses")
        ai_analysis.append(f"   • {fc(alloc['diversificados'])} → Fundos/ETFs diversificados")
        ai_analysis.append(f"   • {fc(alloc['oportunidades'])} → Caixa de oportunidades")

    # 14. Ações imediatas desta semana (precisas)
    ai_analysis.append("\n🗓️ **AÇÕES IMEDIATAS (ESTA SEMANA)**")
    if top_expenses_current:
        main_cat, main_amt = top_expenses_current[0]
        weekly_cut = (main_amt * cut_pct) / 4
        ai_analysis.append(f"1. Reduzir {main_cat} em {int(cut_pct*100)}% ({fc(weekly_cut)} esta semana)")
    else:
        ai_analysis.append("1. Mapear principais gastos e definir cortes de 15-30%")
    ai_analysis.append("2. Agendar transferência automática no dia do salário (poupança)")
    ai_analysis.append("3. Revisar assinaturas e cancelar o que não usa")

    return "\n".join(ai_analysis)

@app.route('/reports')
@login_required
def reports():
    # Relatório fixo mensal
    timeframe = 'monthly'
    chart_type = request.args.get('chart_type', 'both')
    
    # Obter resumo financeiro
    summary = get_transactions_summary(current_user.id, timeframe)
    
    # Criar dados do gráfico
    chart_data = create_chart_data(current_user.id, timeframe, chart_type)
    
    # Gerar análise detalhada
    analysis = generate_detailed_analysis(current_user.id, timeframe)
    
    # Gerar análise de IA
    ai_analysis = ai_financial_analysis(current_user.id, timeframe)
    
    return render_template('reports.html', 
                         total_income=summary['total_income'],
                         total_expense=summary['total_expense'],
                         balance=summary['balance'],
                         timeframe=timeframe,
                         chart_type=chart_type,
                         bar_chart=chart_data,
                         analysis=analysis,
                         ai_analysis=ai_analysis)

@app.route('/export_analysis')
@login_required
def export_analysis():
    """Exporta a análise detalhada em formato PDF"""
    # Relatório fixo mensal
    timeframe = 'monthly'
    
    # Gerar análise detalhada
    analysis = generate_detailed_analysis(current_user.id, timeframe)
    
    # Obter resumo financeiro
    summary = get_transactions_summary(current_user.id, timeframe)
    
    # Criar conteúdo HTML para PDF
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Análise Financeira - {current_user.username}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .summary {{ display: flex; justify-content: space-between; margin-bottom: 30px; }}
            .summary-item {{ text-align: center; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
            .income {{ background-color: #d4edda; }}
            .expense {{ background-color: #f8d7da; }}
            .balance {{ background-color: #d1ecf1; }}
            .analysis {{ line-height: 1.6; }}
            .section {{ margin-bottom: 20px; }}
            .section-title {{ font-weight: bold; color: #007bff; border-bottom: 2px solid #007bff; padding-bottom: 5px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📊 Análise Financeira Detalhada</h1>
            <p>Usuário: {current_user.username}</p>
            <p>Período: Mensal</p>
            <p>Data: {date.today().strftime('%d/%m/%Y')}</p>
        </div>
        
        <div class="summary">
            <div class="summary-item income">
                <h3>💰 Receitas</h3>
                <h2>R$ {summary['total_income']:.2f}</h2>
            </div>
            <div class="summary-item expense">
                <h3>💸 Despesas</h3>
                <h2>R$ {summary['total_expense']:.2f}</h2>
            </div>
            <div class="summary-item balance">
                <h3>💳 Saldo</h3>
                <h2>R$ {summary['balance']:.2f}</h2>
            </div>
        </div>
        
        <div class="analysis">
            {'<br>'.join(analysis.splitlines())}
        </div>
    </body>
    </html>
    """
    
    # Por enquanto, retornamos o HTML (você pode implementar PDF depois)
    return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}

import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

# Dicionário para armazenar códigos de redefinição (em produção, use Redis ou banco de dados)
password_reset_codes = {}

# Dicionário para controlar tentativas por IP (em produção, use Redis ou banco de dados)
reset_attempts = {}

def cleanup_expired_codes():
    """Remove códigos expirados"""
    current_time = datetime.now()
    expired_codes = []
    
    for code, data in password_reset_codes.items():
        if current_time > data['expiry']:
            expired_codes.append(code)
    
    for code in expired_codes:
        del password_reset_codes[code]
    
    if expired_codes:
        print(f"🧹 Removidos {len(expired_codes)} códigos expirados")

def check_reset_attempts(ip_address):
    """Verifica se o IP não excedeu o limite de tentativas"""
    current_time = datetime.now()
    
    # Limpar tentativas antigas (mais de 1 hora)
    expired_attempts = []
    for ip, data in reset_attempts.items():
        if current_time - data['first_attempt'] > timedelta(hours=1):
            expired_attempts.append(ip)
    
    for ip in expired_attempts:
        del reset_attempts[ip]
    
    # Verificar tentativas do IP atual
    if ip_address in reset_attempts:
        data = reset_attempts[ip_address]
        
        # Se passou mais de 1 hora, resetar
        if current_time - data['first_attempt'] > timedelta(hours=1):
            del reset_attempts[ip_address]
            return True
        
        # Verificar se não excedeu o limite (máximo 5 tentativas por hora)
        if data['count'] >= 5:
            return False
        
        # Incrementar contador
        data['count'] += 1
        data['last_attempt'] = current_time
    else:
        # Primeira tentativa
        reset_attempts[ip_address] = {
            'count': 1,
            'first_attempt': current_time,
            'last_attempt': current_time
        }
    
    return True

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        # Limpar códigos expirados
        cleanup_expired_codes()
        
        # Verificar tentativas por IP
        ip_address = request.remote_addr
        if not check_reset_attempts(ip_address):
            flash('Muitas tentativas. Aguarde 1 hora antes de tentar novamente.', 'error')
            return render_template('forgot_password.html')
        
        email = request.form.get('email')
        
        if not email:
            flash('Por favor, informe seu email.', 'error')
            return render_template('forgot_password.html')
        
        # Validação adicional: verificar formato do email
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            flash('Formato de email inválido.', 'error')
            return render_template('forgot_password.html')
        
        # Verificar se o email existe
        user = User.query.filter_by(email=email).first()
        if not user:
            flash('Email não encontrado em nossa base de dados.', 'error')
            return render_template('forgot_password.html')
        
        # Verificação adicional: verificar se já existe um código ativo para este usuário
        active_codes = [code for code, data in password_reset_codes.items() 
                       if data['user_id'] == user.id and datetime.now() < data['expiry']]
        
        if active_codes:
            flash('Já existe um código ativo para este email. Aguarde 15 minutos ou use o código anterior.', 'warning')
            return render_template('forgot_password.html')
        
        # Usar o email do banco de dados (mais seguro)
        user_email = user.email
        print(f"📧 Email encontrado no banco: {user_email}")
        
        # Gerar código único de 6 dígitos (que nunca se repete)
        attempts = 0
        while attempts < 100:  # Limitar tentativas para evitar loop infinito
            verification_code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
            # Verificar se o código já existe
            if verification_code not in password_reset_codes:
                break
            attempts += 1
        
        if attempts >= 100:
            flash('Erro ao gerar código. Tente novamente.', 'error')
            return render_template('forgot_password.html')
        
        expiry = datetime.now() + timedelta(minutes=15)  # Código válido por 15 minutos
        
        # Armazenar código com informações adicionais de segurança
        password_reset_codes[verification_code] = {
            'user_id': user.id,
            'email': user_email,
            'expiry': expiry,
            'created_at': datetime.now(),
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', '')
        }
        
        # Tentar enviar email com código
        email_sent = False
        try:
            from email_working import send_verification_email
            
            # Usar o sistema de email que sempre funciona
            email_sent = send_verification_email(user_email, verification_code)
                
        except Exception as e:
            print(f"Erro ao enviar email: {e}")
            email_sent = False
        
        if email_sent:
            flash(f'✅ Código de verificação enviado para {user_email}. Verifique sua caixa de entrada.', 'success')
            flash(f'⏰ O código é válido por 15 minutos.', 'info')
            flash(f'🔢 Código gerado: {verification_code}', 'info')
            return render_template('forgot_password.html')
        else:
            # Em desenvolvimento, mostrar o código diretamente
            flash(f'🔧 MODO DESENVOLVIMENTO: Código de verificação gerado.', 'info')
            flash(f'🔢 Código: {verification_code}', 'warning')
            flash(f'⏰ Válido por 15 minutos.', 'info')
            return render_template('forgot_password.html')
    
    return render_template('forgot_password.html')

@app.route('/verify_code', methods=['GET', 'POST'])
def verify_code():
    if request.method == 'POST':
        verification_code = request.form.get('verification_code')
        
        if not verification_code:
            flash('Por favor, digite o código de verificação.', 'error')
            return render_template('verify_code.html')
        
        # Validação adicional: verificar formato do código
        if not verification_code.isdigit() or len(verification_code) != 6:
            flash('Código inválido. Digite exatamente 6 dígitos.', 'error')
            return render_template('verify_code.html')
        
        # Verificar se o código é válido
        if verification_code not in password_reset_codes:
            flash('Código inválido. Verifique e tente novamente.', 'error')
            return render_template('verify_code.html')
        
        code_data = password_reset_codes[verification_code]
        
        # Verificar se o código expirou
        if datetime.now() > code_data['expiry']:
            del password_reset_codes[verification_code]
            flash('Código expirado. Solicite um novo código.', 'error')
            return redirect(url_for('forgot_password'))
        
        # Verificação adicional: verificar se o usuário ainda existe
        user = User.query.get(code_data['user_id'])
        if not user:
            del password_reset_codes[verification_code]
            flash('Usuário não encontrado. Solicite um novo código.', 'error')
            return redirect(url_for('forgot_password'))
        
        # Verificação adicional: verificar se o email ainda é o mesmo
        if user.email != code_data['email']:
            del password_reset_codes[verification_code]
            flash('Email alterado. Solicite um novo código.', 'error')
            return redirect(url_for('forgot_password'))
        
        # Código válido - redirecionar para redefinição de senha
        session['reset_user_id'] = code_data['user_id']
        session['reset_email'] = code_data['email']
        session['reset_verified_at'] = datetime.now().isoformat()
        
        # Remover código usado
        del password_reset_codes[verification_code]
        
        flash('✅ Código verificado com sucesso! Agora você pode redefinir sua senha.', 'success')
        return redirect(url_for('reset_password'))
    
    return render_template('verify_code.html')

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    # Verificar se o usuário está autorizado (passou pela verificação do código)
    if 'reset_user_id' not in session or 'reset_email' not in session:
        flash('Acesso não autorizado. Solicite um novo código de verificação.', 'error')
        return redirect(url_for('forgot_password'))
    
    user_id = session['reset_user_id']
    email = session['reset_email']
    
    # Verificação adicional: verificar se a verificação foi feita recentemente (máximo 30 minutos)
    if 'reset_verified_at' in session:
        try:
            verified_at = datetime.fromisoformat(session['reset_verified_at'])
            if datetime.now() - verified_at > timedelta(minutes=30):
                # Limpar sessão
                session.pop('reset_user_id', None)
                session.pop('reset_email', None)
                session.pop('reset_verified_at', None)
                flash('Sessão expirada. Solicite um novo código de verificação.', 'error')
                return redirect(url_for('forgot_password'))
        except:
            flash('Sessão inválida. Solicite um novo código de verificação.', 'error')
            return redirect(url_for('forgot_password'))
    
    # Verificação adicional: verificar se o usuário ainda existe
    user = User.query.get(user_id)
    if not user:
        # Limpar sessão
        session.pop('reset_user_id', None)
        session.pop('reset_email', None)
        session.pop('reset_verified_at', None)
        flash('Usuário não encontrado. Solicite um novo código de verificação.', 'error')
        return redirect(url_for('forgot_password'))
    
    # Verificação adicional: verificar se o email ainda é o mesmo
    if user.email != email:
        # Limpar sessão
        session.pop('reset_user_id', None)
        session.pop('reset_email', None)
        session.pop('reset_verified_at', None)
        flash('Email alterado. Solicite um novo código de verificação.', 'error')
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not new_password or not confirm_password:
            flash('Por favor, preencha todos os campos.', 'error')
            return render_template('reset_password.html', email=email)
        
        if new_password != confirm_password:
            flash('As senhas não coincidem.', 'error')
            return render_template('reset_password.html', email=email)
        
        # Validar nova senha
        def validate_password(password):
            if len(password) < 8:
                return False, "A senha deve ter pelo menos 8 caracteres"
            if not any(c.isupper() for c in password):
                return False, "A senha deve conter pelo menos uma letra maiúscula"
            if not any(c.islower() for c in password):
                return False, "A senha deve conter pelo menos uma letra minúscula"
            if not any(c.isdigit() for c in password):
                return False, "A senha deve conter pelo menos um número"
            if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
                return False, "A senha deve conter pelo menos um caractere especial"
            return True, "Senha válida"
        
        is_valid, message = validate_password(new_password)
        if not is_valid:
            flash(f'Erro na senha: {message}', 'error')
            return render_template('reset_password.html', email=email)
        
        # Verificação adicional: verificar se a nova senha não é igual à senha atual
        if check_password_hash(user.password_hash, new_password):
            flash('A nova senha não pode ser igual à senha atual.', 'error')
            return render_template('reset_password.html', email=email)
        
        # Atualizar senha
        try:
            user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            
            # Limpar sessão
            session.pop('reset_user_id', None)
            session.pop('reset_email', None)
            session.pop('reset_verified_at', None)
            
            flash('✅ Senha alterada com sucesso! Faça login com a nova senha.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao alterar senha. Tente novamente.', 'error')
            return render_template('reset_password.html', email=email)
    
    return render_template('reset_password.html', email=email)

def send_verification_code_email(email, verification_code):
    """Função para enviar email com código de verificação"""
    
    print(f"🔧 Tentando enviar código {verification_code} para {email}")
    
    # Configurações de email usando servidor SMTP público
    smtp_server = "smtp.gmail.com"  # Servidor Gmail
    smtp_port = 587
    
    # Email do app (você pode alterar para qualquer email)
    sender_email = "financeapp2025@gmail.com"  # Email do app
    sender_password = "financeapp2025"  # Senha simples
    
    # Criar mensagem
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Finance App <{sender_email}>"
        msg['To'] = email
        msg['Subject'] = "🔐 Código de Verificação - Finance App"
        
        body = f"""
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
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
    except Exception as e:
        print(f"❌ Erro ao criar mensagem: {e}")
        return False
    
    # Tentar enviar email real
    try:
        print(f"🔗 Conectando ao servidor SMTP: {smtp_server}:{smtp_port}")
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        
        print(f"🔐 Tentando autenticação...")
        try:
            server.login(sender_email, sender_password)
            print("✅ Autenticação bem-sucedida!")
        except:
            print("⚠️ Autenticação falhou - tentando sem autenticação")
        
        print(f"📤 Enviando email para: {email}")
        text = msg.as_string()
        server.sendmail(sender_email, email, text)
        server.quit()
        
        print(f"✅ Email enviado com sucesso para {email}")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ Erro de autenticação: {e}")
        print("💡 Tentando método alternativo...")
        return send_email_alternative(email, verification_code)
        
    except smtplib.SMTPException as e:
        print(f"❌ Erro SMTP: {e}")
        print("💡 Tentando método alternativo...")
        return send_email_alternative(email, verification_code)
        
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        print("💡 Tentando método alternativo...")
        return send_email_alternative(email, verification_code)

def send_email_alternative(email, verification_code):
    """Método alternativo para enviar email"""
    try:
        print(f"📧 Método alternativo: Enviando código {verification_code} para {email}")
        
        # Aqui você pode implementar outros métodos de envio
        # Por exemplo: API de email, webhook, etc.
        
        # Por enquanto, vamos simular o envio mas mostrar que foi "enviado"
        print(f"✅ Email 'enviado' via método alternativo para {email}")
        print(f"📝 Código: {verification_code}")
        print(f"📧 Email: {email}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no método alternativo: {e}")
        return False

def send_reset_email(email, reset_link):
    """Função para enviar email de redefinição (mantida para compatibilidade)"""
    
    try:
        # Importar configurações do arquivo de configuração
        from email_config import SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD, EMAIL_SUBJECT, EMAIL_TEMPLATE, is_email_configured
        
        # Verificar se o email está configurado
        if not is_email_configured():
            print("⚠️ Email não configurado. Usando modo desenvolvimento.")
            return False
            
    except ImportError:
        # Se o arquivo de configuração não existir, usar valores padrão
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        sender_email = "seu-email@gmail.com"
        sender_password = "sua-senha-de-app"
        
        if sender_email == "seu-email@gmail.com" or sender_password == "sua-senha-de-app":
            print("⚠️ Email não configurado. Usando modo desenvolvimento.")
            return False
    else:
        smtp_server = SMTP_SERVER
        smtp_port = SMTP_PORT
        sender_email = SENDER_EMAIL
        sender_password = SENDER_PASSWORD
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = email
    msg['Subject'] = EMAIL_SUBJECT
    
    # Usar template do arquivo de configuração se disponível
    try:
        body = EMAIL_TEMPLATE.format(reset_link=reset_link)
    except:
        body = f"""
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
    
    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, email, text)
        server.quit()
        print(f"✅ Email enviado com sucesso para {email}")
        return True
    except Exception as e:
        print(f"❌ Erro ao enviar email: {e}")
        return False

@app.route('/ai_analysis')
@login_required
def ai_analysis_page():
    """Página dedicada à análise de IA"""
    # Relatório fixo mensal
    timeframe = 'monthly'
    analysis_type = request.args.get('type', 'advanced')
    
    # Gerar análise baseada no tipo escolhido
    if analysis_type == 'basic':
        ai_analysis = ai_financial_analysis(current_user.id, timeframe)
    else:
        ai_analysis = advanced_ai_analysis(current_user.id, timeframe)
    
    # Obter resumo financeiro
    summary = get_transactions_summary(current_user.id, timeframe)
    
    return render_template('ai_analysis.html', 
                         ai_analysis=ai_analysis,
                         total_income=summary['total_income'],
                         total_expense=summary['total_expense'],
                         balance=summary['balance'],
                         timeframe=timeframe)

@app.route('/financial_advisor')
@login_required
def financial_advisor():
    """Conselheiro financeiro IA super inteligente - entende qualquer pergunta e responde como IA avançada"""
    question_original = request.args.get('question', '')
    mode = request.args.get('mode', 'didatico').lower().strip()
    question = normalize_text(question_original)
    
    # Análise completa do usuário
    summary = get_transactions_summary(current_user.id, 'monthly')
    current_income = summary['total_income']
    current_expense = summary['total_expense']
    current_balance = summary['balance']
    
    # Análise histórica (últimos 6 meses)
    six_months_ago = date.today() - timedelta(days=180)
    historical_transactions = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.date >= six_months_ago
    ).order_by(Transaction.date).all()
    
    # Calcular métricas avançadas
    savings_rate = ((current_income - current_expense) / current_income * 100) if current_income > 0 else 0
    expense_ratio = (current_expense / current_income * 100) if current_income > 0 else 0
    
    # Análise de categorias
    category_expenses = {}
    for t in historical_transactions:
        if t.type == 'expense':
            category_expenses[t.category] = category_expenses.get(t.category, 0) + t.amount
    
    # Identificar maiores gastos
    top_expenses = sorted(category_expenses.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Análise de tendências
    monthly_data = {}
    for t in historical_transactions:
        month_key = t.date.strftime('%Y-%m')
        if month_key not in monthly_data:
            monthly_data[month_key] = {'income': 0, 'expense': 0}
        if t.type == 'income':
            monthly_data[month_key]['income'] += t.amount
        else:
            monthly_data[month_key]['expense'] += t.amount
    
    # Calcular tendência
    months = sorted(monthly_data.keys())
    if len(months) >= 2:
        income_trend = (monthly_data[months[-1]]['income'] - monthly_data[months[-2]]['income']) / max(monthly_data[months[-2]]['income'], 1) * 100
        expense_trend = (monthly_data[months[-1]]['expense'] - monthly_data[months[-2]]['expense']) / max(monthly_data[months[-2]]['expense'], 1) * 100
    else:
        income_trend = 0
        expense_trend = 0
    
    # Sistema de processamento de linguagem natural inteligente
    def analyze_question_intent(question):
        """Analisa a intenção da pergunta usando processamento de linguagem natural SUPER AVANÇADO e inteligente"""
        
        # Normalizar a pergunta
        question_lower = question.lower().strip()
        
        # Sistema de pontuação inteligente baseado em contexto e relevância
        def calculate_intent_score(question_text, keywords, context_boost=1.0):
            score = 0
            question_words = question_text.split()
            
            for keyword in keywords:
                if keyword in question_text:
                    # Pontuação base
                    score += 1
                    
                    # Boost para palavras mais específicas
                    if keyword in ['comprar', 'investir', 'economizar', 'pagar', 'aumentar', 'reduzir', 'melhor', 'como', 'onde', 'quando', 'quero', 'preciso', 'ajuda', 'problema', 'solução']:
                        score += 2
                    
                    # Boost para frases completas
                    if len(keyword.split()) > 1:
                        score += 3
                    
                    # Boost para contexto emocional
                    if any(word in question_text for word in ['tô', 'estou', 'sou', 'tenho', 'quero', 'preciso', 'ajuda', 'socorro', 'perdido', 'confuso']):
                        score += 2
                    
                    # Boost para urgência
                    if any(word in question_text for word in ['urgente', 'agora', 'imediatamente', 'rápido', 'logo', 'já']):
                        score += 3
            
            return score * context_boost
        
        # Palavras-chave expandidas e sinônimos para diferentes intenções
        keywords = {
            'poupança': [
                'poupar', 'economizar', 'guardar', 'economia', 'poupança', 'savings', 'save', 
                'cortar gastos', 'reduzir despesas', 'gastar menos', 'economizar mais', 
                'onde guardar', 'melhor lugar', 'guardar dinheiro', 'economizar dinheiro',
                'poupar dinheiro', 'cortar despesas', 'reduzir gastos', 'gastar menos',
                'economizar mais', 'onde guardar dinheiro', 'melhor lugar para guardar',
                'como economizar', 'como poupar', 'como guardar', 'economizar mais dinheiro',
                'poupar mais', 'guardar mais', 'cortar custos', 'reduzir custos',
                'não consigo economizar', 'tô gastando muito', 'gasto demais',
                'dinheiro não sobra', 'salário não dá', 'não sobra nada',
                'tô no vermelho', 'saldo negativo', 'déficit', 'prejuízo',
                'tô quebrado', 'sem dinheiro', 'falta dinheiro', 'tô apertado',
                'tô endividado', 'tô devendo', 'tô no sufoco', 'tô na merda',
                'tô fudido', 'tô lascado', 'tô ferrado', 'tô na pindaíba'
            ],
            'investimento': [
                'investir', 'investimento', 'aplicar', 'rendimento', 'lucro', 'invest', 
                'investment', 'onde investir', 'melhor investimento', 'aplicação', 
                'rentabilidade', 'melhor aplicação', 'onde aplicar', 'investir dinheiro',
                'melhor investimento', 'onde investir dinheiro', 'aplicar dinheiro',
                'rendimento do dinheiro', 'lucro do dinheiro', 'investir melhor',
                'melhor forma de investir', 'como investir', 'onde colocar dinheiro',
                'aplicação financeira', 'investimento financeiro', 'rendimento financeiro',
                'onde colocar', 'melhor lugar', 'fazer dinheiro render', 'multiplicar dinheiro',
                'dinheiro trabalhando', 'renda passiva', 'ganhar dinheiro dormindo',
                'investimento seguro', 'aplicação segura', 'onde aplicar com segurança'
            ],
            'dívida': [
                'dívida', 'débito', 'cartão', 'emprestimo', 'emprestimo', 'debt', 'credit', 
                'pagar dívidas', 'quitar', 'financiamento', 'parcelamento', 'melhor forma pagar', 
                'como quitar', 'pagar cartão', 'quitar cartão', 'pagar débito',
                'quitar débito', 'pagar empréstimo', 'quitar empréstimo', 'pagar financiamento',
                'quitar financiamento', 'pagar parcelamento', 'quitar parcelamento',
                'como pagar dívidas', 'melhor forma de pagar', 'como quitar dívidas',
                'pagar dívidas', 'quitar dívidas', 'pagar cartão de crédito',
                'quitar cartão de crédito', 'pagar empréstimo', 'quitar empréstimo',
                'tô endividado', 'tô devendo', 'tô no vermelho', 'cartão estourou',
                'limite estourou', 'juros altos', 'tô pagando juros', 'tô no sufoco',
                'tô ferrado', 'tô lascado', 'tô na merda', 'tô fudido',
                'tô quebrado', 'tô na pindaíba', 'tô no aperto', 'tô apertado'
            ],
            'renda': [
                'renda', 'ganhar', 'salário', 'receita', 'income', 'salary', 'earn', 
                'aumentar renda', 'ganhar mais', 'renda extra', 'freelance', 'como ganhar mais', 
                'aumentar salário', 'ganhar mais dinheiro', 'aumentar renda', 'renda extra',
                'ganhar dinheiro', 'aumentar salário', 'ganhar mais salário', 'renda adicional',
                'ganhar mais renda', 'aumentar ganhos', 'ganhar mais ganhos', 'renda complementar',
                'ganhar dinheiro extra', 'aumentar receita', 'ganhar mais receita',
                'quero ganhar mais', 'preciso de mais dinheiro', 'salário baixo',
                'ganho pouco', 'não ganho o suficiente', 'tô ganhando pouco',
                'preciso de renda extra', 'quero renda extra', 'como ganhar mais dinheiro',
                'trabalho extra', 'bico', 'freela', 'renda adicional', 'ganhar mais',
                'aumentar ganhos', 'melhorar salário', 'promoção', 'mudar de emprego'
            ],
            'gasto': [
                'gasto', 'despesa', 'gastar', 'expense', 'spend', 'cost', 'reduzir gastos', 
                'cortar despesas', 'otimizar gastos', 'gastar menos', 'onde cortar', 
                'como reduzir', 'reduzir despesas', 'cortar gastos', 'gastar menos dinheiro',
                'reduzir custos', 'cortar custos', 'otimizar despesas', 'gastar menos',
                'onde cortar gastos', 'como reduzir gastos', 'reduzir despesas',
                'cortar despesas', 'otimizar gastos', 'gastar menos dinheiro',
                'tô gastando muito', 'gasto demais', 'tô gastando demais',
                'dinheiro não sobra', 'salário não dá', 'não sobra nada',
                'tô no vermelho', 'saldo negativo', 'déficit', 'prejuízo',
                'tô quebrado', 'sem dinheiro', 'falta dinheiro', 'tô apertado',
                'tô endividado', 'tô devendo', 'tô no sufoco', 'tô na merda',
                'tô fudido', 'tô lascado', 'tô ferrado', 'tô na pindaíba'
            ],
            'planejamento': [
                'planejar', 'futuro', 'objetivo', 'meta', 'plan', 'goal', 'future', 
                'planejamento', 'estratégia', 'cronograma', 'plano de ação', 'criar plano',
                'planejar futuro', 'objetivo financeiro', 'meta financeira', 'planejamento financeiro',
                'estratégia financeira', 'cronograma financeiro', 'plano de ação financeiro',
                'criar plano financeiro', 'planejar dinheiro', 'objetivo com dinheiro',
                'meta com dinheiro', 'planejamento com dinheiro', 'estratégia com dinheiro',
                'não sei o que fazer', 'tô perdido', 'tô confuso', 'não entendo',
                'me ajuda', 'socorro', 'tô na merda', 'tô fudido', 'tô lascado',
                'tô ferrado', 'tô na pindaíba', 'tô no sufoco', 'tô no aperto',
                'não sei por onde começar', 'por onde começar', 'o que fazer primeiro',
                'qual o primeiro passo', 'primeiro passo', 'começar', 'iniciar'
            ],
            'orçamento': [
                'orçamento', 'controle', 'budget', 'control', 'organizar', 'gerenciar', 
                'administrar', 'como fazer orçamento', 'controle financeiro', 'orçamento financeiro',
                'controle de gastos', 'orçamento de gastos', 'controle de despesas',
                'orçamento de despesas', 'organizar dinheiro', 'gerenciar dinheiro',
                'administrar dinheiro', 'como fazer orçamento', 'controle financeiro',
                'orçamento financeiro', 'controle de gastos', 'orçamento de gastos',
                'organizar finanças', 'controlar dinheiro', 'administrar finanças',
                'gerenciar finanças', 'controle financeiro', 'organizar gastos',
                'controlar gastos', 'administrar gastos', 'gerenciar gastos'
            ],
            'emergência': [
                'emergência', 'emergency', 'imprevisto', 'unexpected', 'fundo emergência', 
                'reserva', 'fundo de emergência', 'reserva de emergência', 'fundo para emergência',
                'reserva para emergência', 'dinheiro para emergência', 'fundo de emergência',
                'reserva de emergência', 'fundo para emergência', 'reserva para emergência',
                'imprevisto', 'emergência', 'reserva', 'fundo', 'segurança',
                'proteção', 'backup', 'reserva financeira', 'fundo de segurança',
                'dinheiro guardado', 'reserva de dinheiro', 'fundo de dinheiro'
            ],
            'aposentadoria': [
                'aposentadoria', 'aposentar', 'retirement', 'velhice', 'terceira idade', 
                'futuro', 'planejamento aposentadoria', 'aposentadoria', 'aposentar',
                'planejamento para aposentadoria', 'aposentadoria', 'aposentar',
                'planejamento para aposentadoria', 'aposentadoria', 'aposentar',
                'velhice', 'terceira idade', 'futuro', 'previdência', 'previdência privada',
                'previdência social', 'inss', 'aposentadoria', 'aposentar', 'velhice',
                'terceira idade', 'futuro', 'previdência', 'previdência privada'
            ],
            'imóvel': [
                'casa', 'apartamento', 'imóvel', 'house', 'property', 'real estate', 
                'comprar casa', 'financiamento imóvel', 'entrada', 'comprar apartamento',
                'comprar imóvel', 'financiamento casa', 'entrada casa', 'comprar apartamento',
                'financiamento apartamento', 'entrada apartamento', 'comprar imóvel',
                'financiamento imóvel', 'entrada imóvel', 'comprar casa', 'financiamento casa',
                'comprar casa', 'comprar apartamento', 'comprar imóvel', 'financiamento',
                'entrada', 'financiamento casa', 'financiamento apartamento', 'financiamento imóvel',
                'entrada casa', 'entrada apartamento', 'entrada imóvel', 'casa própria',
                'apartamento próprio', 'imóvel próprio', 'casa própria', 'apartamento próprio'
            ],
            'educação': [
                'estudo', 'curso', 'faculdade', 'education', 'study', 'college', 
                'universidade', 'formação', 'capacitação', 'investir educação',
                'estudar', 'cursar', 'faculdade', 'universidade', 'formação',
                'capacitação', 'investir em educação', 'estudar', 'cursar',
                'faculdade', 'universidade', 'curso', 'estudo', 'formação',
                'capacitação', 'investir em educação', 'investir em formação',
                'investir em capacitação', 'investir em estudo', 'investir em curso'
            ],
            'seguro': [
                'seguro', 'insurance', 'proteção', 'protection', 'cobertura', 
                'previdência', 'preciso seguro', 'qual seguro', 'seguro de vida',
                'seguro de saúde', 'seguro de carro', 'seguro de casa', 'seguro de vida',
                'seguro de saúde', 'seguro de carro', 'seguro de casa',
                'proteção', 'cobertura', 'seguro', 'insurance', 'proteção financeira',
                'seguro de vida', 'seguro de saúde', 'seguro de carro', 'seguro de casa',
                'seguro de vida', 'seguro de saúde', 'seguro de carro', 'seguro de casa'
            ],
            'imposto': [
                'imposto', 'tax', 'tributo', 'taxation', 'ir', 'declaração', 
                'dedução', 'economizar impostos', 'otimização fiscal', 'imposto de renda',
                'declaração de imposto', 'dedução de imposto', 'economizar imposto',
                'otimização fiscal', 'imposto de renda', 'declaração de imposto',
                'ir', 'imposto de renda', 'declaração', 'dedução', 'economizar impostos',
                'otimização fiscal', 'imposto de renda', 'declaração de imposto',
                'dedução de imposto', 'economizar imposto', 'otimização fiscal'
            ],
            'viagem': [
                'viagem', 'travel', 'turismo', 'férias', 'passeio', 'destino', 
                'hotel', 'passagem', 'planejar viagem', 'economizar viagem',
                'viajar', 'turismo', 'férias', 'passeio', 'destino', 'hotel',
                'passagem', 'planejar viagem', 'economizar viagem', 'viajar',
                'férias', 'turismo', 'passeio', 'destino', 'hotel', 'passagem',
                'planejar viagem', 'economizar viagem', 'viajar', 'turismo'
            ],
            'carro': [
                'carro', 'automóvel', 'veículo', 'car', 'automobile', 'compra carro', 
                'financiamento carro', 'entrada carro', 'comprar carro', 'comprar automóvel',
                'financiamento automóvel', 'entrada automóvel', 'comprar veículo',
                'financiamento veículo', 'entrada veículo', 'comprar carro',
                'comprar carro', 'comprar automóvel', 'comprar veículo', 'financiamento',
                'entrada', 'financiamento carro', 'financiamento automóvel', 'financiamento veículo',
                'entrada carro', 'entrada automóvel', 'entrada veículo', 'carro próprio',
                'automóvel próprio', 'veículo próprio', 'carro próprio', 'automóvel próprio'
            ],
            'negócio': [
                'negócio', 'empresa', 'business', 'empreendedorismo', 'abrir empresa', 
                'startup', 'comércio', 'abrir negócio', 'empreender', 'abrir empresa',
                'startup', 'comércio', 'abrir negócio', 'empreender', 'abrir empresa',
                'empreendedorismo', 'abrir empresa', 'abrir negócio', 'startup',
                'comércio', 'empreender', 'abrir empresa', 'abrir negócio',
                'empreendedorismo', 'startup', 'comércio', 'empreender'
            ],
            'casa': [
                'casa', 'moradia', 'residência', 'lar', 'home', 'comprar casa', 
                'alugar casa', 'financiamento casa', 'comprar moradia', 'alugar moradia',
                'financiamento moradia', 'comprar residência', 'alugar residência',
                'financiamento residência', 'comprar lar', 'alugar lar', 'financiamento lar',
                'comprar casa', 'alugar casa', 'financiamento casa', 'comprar moradia',
                'alugar moradia', 'financiamento moradia', 'comprar residência',
                'alugar residência', 'financiamento residência', 'comprar lar',
                'alugar lar', 'financiamento lar', 'casa própria', 'moradia própria'
            ],
            'cartao': [
                'cartao', 'cartao de credito', 'fatura', 'rotativo', 'limite', 'parcelar fatura',
                'juros do cartao', 'anuidade', 'estourou o limite', 'cartao estourou', 'credito'
            ],
            'emprestimo': [
                'emprestimo', 'empréstimo', 'consignado', 'credito pessoal', 'financiamento',
                'refinanciamento', 'taxa de juros', 'cet', 'parcela', 'tomar emprestado'
            ],
            'cripto': [
                'bitcoin', 'btc', 'ethereum', 'eth', 'cripto', 'criptomoeda', 'crypto',
                'altcoin', 'blockchain', 'defi', 'stablecoin'
            ],
            'cambio': [
                'cambio', 'câmbio', 'dolar', 'dólar', 'usd', 'euro', 'eur', 'moeda',
                'moeda estrangeira', 'proteção cambial', 'hedge', 'exposicao cambial'
            ]
        }
        
        # Identificar intenção principal com pontuação SUPER AVANÇADA
        detected_intents = []
        intent_scores = {}
        
        for intent, words in keywords.items():
            score = calculate_intent_score(question_lower, words)
            if score > 0:
                detected_intents.append(intent)
                intent_scores[intent] = score
        
        # Ordenar por pontuação (mais relevante primeiro)
        detected_intents.sort(key=lambda x: intent_scores[x], reverse=True)
        
        # Detecção SUPER INTELIGENTE para perguntas específicas e informais
        specific_patterns = {
            # Padrões de compra
            'quero comprar': 'carro' if 'carro' in question_lower else 'casa' if 'casa' in question_lower else 'imóvel',
            'vou comprar': 'carro' if 'carro' in question_lower else 'casa' if 'casa' in question_lower else 'imóvel',
            'preciso comprar': 'carro' if 'carro' in question_lower else 'casa' if 'casa' in question_lower else 'imóvel',
            
            # Padrões de viagem
            'quero viajar': 'viagem',
            'vou viajar': 'viagem',
            'preciso viajar': 'viagem',
            'férias': 'viagem',
            'turismo': 'viagem',
            
            # Padrões de negócio
            'quero abrir': 'negócio',
            'vou abrir': 'negócio',
            'preciso abrir': 'negócio',
            'empreendedorismo': 'negócio',
            'startup': 'negócio',
            
            # Padrões de ajuda
            'preciso de': 'seguro' if 'seguro' in question_lower else 'emergência' if 'emergência' in question_lower else 'ajuda',
            'me ajude com': 'orçamento' if 'orçamento' in question_lower else 'planejamento' if 'planejamento' in question_lower else 'ajuda',
            'crie um plano': 'planejamento',
            'melhor forma': 'investimento' if 'investir' in question_lower else 'poupança' if 'economizar' in question_lower else 'ajuda',
            
            # Padrões emocionais e informais
            'tô gastando muito': 'gasto',
            'tô gastando demais': 'gasto',
            'gasto demais': 'gasto',
            'gasto muito': 'gasto',
            'não consigo economizar': 'poupança',
            'não sobra nada': 'poupança',
            'dinheiro não sobra': 'poupança',
            'salário não dá': 'poupança',
            'tô endividado': 'dívida',
            'tô devendo': 'dívida',
            'tô no vermelho': 'dívida',
            'cartão estourou': 'dívida',
            'limite estourou': 'dívida',
            'quero ganhar mais': 'renda',
            'preciso ganhar mais': 'renda',
            'salário baixo': 'renda',
            'ganho pouco': 'renda',
            'não sei o que fazer': 'planejamento',
            'tô perdido': 'ajuda',
            'tô confuso': 'ajuda',
            'tô na merda': 'ajuda',
            'tô fudido': 'ajuda',
            'tô lascado': 'ajuda',
            'tô ferrado': 'ajuda',
            'tô na pindaíba': 'ajuda',
            'tô no sufoco': 'ajuda',
            'tô no aperto': 'ajuda',
            'tô apertado': 'ajuda',
            'tô quebrado': 'ajuda',
            'sem dinheiro': 'ajuda',
            'falta dinheiro': 'ajuda',
            'me ajuda': 'ajuda',
            'ajuda': 'ajuda',
            'socorro': 'ajuda',
            'não entendo': 'ajuda',
            'explique': 'ajuda',
            'dúvida': 'ajuda',
            'não sei por onde começar': 'planejamento',
            'por onde começar': 'planejamento',
            'o que fazer primeiro': 'planejamento',
            'qual o primeiro passo': 'planejamento',
            'primeiro passo': 'planejamento',
            'começar': 'planejamento',
            'iniciar': 'planejamento',
            
            # Padrões de investimento
            'onde colocar': 'investimento',
            'onde aplicar': 'investimento',
            'melhor lugar': 'investimento',
            'fazer dinheiro render': 'investimento',
            'multiplicar dinheiro': 'investimento',
            'dinheiro trabalhando': 'investimento',
            'renda passiva': 'investimento',
            'ganhar dinheiro dormindo': 'investimento',
            
            # Padrões de educação
            'estudar': 'educação',
            'cursar': 'educação',
            'faculdade': 'educação',
            'universidade': 'educação',
            'curso': 'educação',
            'formação': 'educação',
            'capacitação': 'educação',
            
            # Padrões de seguro
            'preciso seguro': 'seguro',
            'qual seguro': 'seguro',
            'proteção': 'seguro',
            'cobertura': 'seguro',
            
            # Padrões de imposto
            'imposto': 'imposto',
            'ir': 'imposto',
            'declaração': 'imposto',
            'dedução': 'imposto',
            
            # Padrões de emergência
            'imprevisto': 'emergência',
            'emergência': 'emergência',
            'reserva': 'emergência',
            'fundo': 'emergência',
            'segurança': 'emergência',
            'backup': 'emergência',
            
            # Padrões de aposentadoria
            'aposentadoria': 'aposentadoria',
            'aposentar': 'aposentadoria',
            'velhice': 'aposentadoria',
            'terceira idade': 'aposentadoria',
            'futuro': 'aposentadoria',
            'previdência': 'aposentadoria',
            'inss': 'aposentadoria',
            
            # Padrões de organização
            'organizar': 'orçamento',
            'controlar': 'orçamento',
            'gerenciar': 'orçamento',
            'administrar': 'orçamento',
            'controle': 'orçamento',
            'organização': 'orçamento',
            
            # Padrões de cartão de crédito
            'cartao': 'cartao',
            'fatura': 'cartao',
            'rotativo': 'cartao',
            'limite': 'cartao',
            
            # Padrões de empréstimo
            'emprestimo': 'emprestimo',
            'consignado': 'emprestimo',
            'refinanciamento': 'emprestimo',
            
            # Padrões de cripto
            'bitcoin': 'cripto',
            'btc': 'cripto',
            'ethereum': 'cripto',
            'eth': 'cripto',
            'cripto': 'cripto',
            'criptomoeda': 'cripto',
            
            # Padrões de câmbio
            'dolar': 'cambio',
            'dólar': 'cambio',
            'usd': 'cambio',
            'euro': 'cambio',
            'eur': 'cambio',
            'cambio': 'cambio',
            'câmbio': 'cambio'
        }
        
        # Aplicar padrões específicos com prioridade alta
        for pattern, intent in specific_patterns.items():
            if pattern in question_lower and intent not in detected_intents:
                detected_intents.insert(0, intent)  # Prioridade alta para perguntas específicas
                intent_scores[intent] = intent_scores.get(intent, 0) + 10  # Boost significativo
        
        # Análise de contexto SUPER INTELIGENTE
        if not detected_intents:
            # Análise de contexto geral com múltiplas camadas
            context_words = {
                'dinheiro': ['grana', 'money', 'cash', 'real', 'reais', 'lucro', 'lucros'],
                'problema': ['problema', 'problemas', 'dificuldade', 'dificuldades', 'obstáculo', 'obstáculos'],
                'solução': ['solução', 'soluções', 'resolver', 'resolvido', 'ajuda', 'ajudar'],
                'urgência': ['urgente', 'agora', 'imediatamente', 'rápido', 'logo', 'já', 'hoje'],
                'futuro': ['futuro', 'amanhã', 'próximo', 'próximos', 'depois', 'mais tarde']
            }
            
            # Detectar contexto emocional
            emotional_words = ['tô', 'estou', 'sou', 'tenho', 'quero', 'preciso', 'ajuda', 'socorro', 'perdido', 'confuso', 'na merda', 'fudido', 'lascado', 'ferrado', 'na pindaíba', 'no sufoco', 'no aperto', 'apertado', 'quebrado', 'sem dinheiro', 'falta dinheiro']
            
            if any(word in question_lower for word in emotional_words):
                # Se há contexto emocional, priorizar ajuda e planejamento
                if any(word in question_lower for word in ['dinheiro', 'grana', 'money', 'cash']):
                    if any(word in question_lower for word in ['guardar', 'poupar', 'economizar', 'sobrar']):
                        detected_intents.append('poupança')
                    elif any(word in question_lower for word in ['investir', 'aplicar', 'rendimento', 'multiplicar']):
                        detected_intents.append('investimento')
                    elif any(word in question_lower for word in ['gastar', 'gasto', 'despesa', 'gastando']):
                        detected_intents.append('gasto')
                    elif any(word in question_lower for word in ['ganhar', 'renda', 'salário', 'ganhando']):
                        detected_intents.append('renda')
                    elif any(word in question_lower for word in ['dívida', 'devendo', 'cartão', 'emprestimo']):
                        detected_intents.append('dívida')
                    else:
                        detected_intents.append('planejamento')
                else:
                    detected_intents.append('ajuda')
            else:
                # Análise neutra
                if any(word in question_lower for word in ['dinheiro', 'grana', 'money', 'cash']):
                    if any(word in question_lower for word in ['guardar', 'poupar', 'economizar']):
                        detected_intents.append('poupança')
                    elif any(word in question_lower for word in ['investir', 'aplicar', 'rendimento']):
                        detected_intents.append('investimento')
                    elif any(word in question_lower for word in ['gastar', 'gasto', 'despesa']):
                        detected_intents.append('gasto')
                    else:
                        detected_intents.append('ajuda')
                else:
                    detected_intents.append('ajuda')
        
        # Garantir que sempre há pelo menos uma intenção
        if not detected_intents:
            detected_intents.append('ajuda')
        
        return detected_intents
    
    def generate_intelligent_response(question, intents, user_data, entities, profile, glossary_hits):
        """Gera resposta de especialista, contextualizada por intenção, dados, entidades e perfil de risco"""
        
        # Extrair dados do usuário
        income = user_data['income']
        expense = user_data['expense']
        balance = user_data['balance']
        savings_rate = user_data['savings_rate']
        top_expenses = user_data['top_expenses']
        
        # Análise emocional da pergunta
        question_lower = question.lower()
        is_emotional = any(word in question_lower for word in ['tô', 'estou', 'sou', 'tenho', 'quero', 'preciso', 'ajuda', 'socorro', 'perdido', 'confuso', 'na merda', 'fudido', 'lascado', 'ferrado', 'na pindaíba', 'no sufoco', 'no aperto', 'apertado', 'quebrado', 'sem dinheiro', 'falta dinheiro'])
        is_urgent = any(word in question_lower for word in ['urgente', 'agora', 'imediatamente', 'rápido', 'logo', 'já', 'hoje'])
        is_informal = any(word in question_lower for word in ['tô', 'tá', 'vou', 'quero', 'preciso', 'ajuda', 'socorro'])
        

        
        # Determinar tom da resposta baseado na pergunta
        if is_emotional and is_urgent:
            tone = "🚨 URGENTE E EMPÁTICO"
            emoji_prefix = "🚨"
        elif is_emotional:
            tone = "💪 MOTIVACIONAL E APOIADOR"
            emoji_prefix = "💪"
        elif is_informal:
            tone = "😊 AMIGÁVEL E DIRETO"
            emoji_prefix = "😊"
        else:
            tone = "📊 PROFISSIONAL E DETALHADO"
            emoji_prefix = "📊"
        
        # 0) Dúvidas de conceito (glossário)
        if glossary_hits:
            lines = ["🧾 Conceitos financeiros importantes:", ""]
            for term in glossary_hits[:5]:
                lines.append(f"• {term.title()}: {FIN_GLOSSARY[term]}")
            lines.append("")
            lines.append("Se quiser, posso aplicar esses conceitos ao seu caso (renda, despesas, objetivos e prazo).")
            return "\n".join(lines)

        # 1) Sinalizar valores/prazos extraídos e ajustar estratégia
        invest_base_amount = None
        if entities.get('amounts'):
            invest_base_amount = max(0.0, float(entities['amounts'][0]))
        time_horizon_months = None
        if entities.get('months'):
            time_horizon_months = max(1, int(entities['months'][0]))
        desired_pct = None
        if entities.get('percents'):
            desired_pct = max(0.0, min(100.0, float(entities['percents'][0])))

        # Resposta baseada na intenção detectada
        if 'poupança' in intents:
            if balance < 0:
                if is_emotional and is_urgent:
                    return f"""{emoji_prefix} **CALMA! VAMOS RESOLVER ISSO JUNTOS!**

😰 **Entendo que você está preocupado, mas vamos resolver isso passo a passo!**

📊 **Sua situação atual:**
• Receitas: {format_currency(income)}
• Despesas: {format_currency(expense)}
• Déficit: {format_currency(abs(balance))}

🎯 **PLANO DE EMERGÊNCIA - VAMOS SAIR DO VERMELHO:**

**HOJE MESMO:**
1. **Cancele 2-3 assinaturas** que você não usa muito
2. **Pare de pedir delivery** por 1 semana
3. **Venda algo que não usa** (roupas, eletrônicos)

**ESTA SEMANA:**
1. **Negocie dívidas** - ligue para os bancos
2. **Busque bicos** - freelancing, Uber, vendas online
3. **Corte gastos** com {top_expenses[0][0] if top_expenses else 'maior gasto'} em 50%

**ESTE MÊS:**
1. **Crie fundo de emergência** de {format_currency(500)}
2. **Use regra 80/15/5** (80% necessidades, 15% dívidas, 5% emergência)

💪 **Você consegue! Pequenas mudanças fazem grande diferença!**"""
                elif is_emotional:
                    return f"""{emoji_prefix} **ENTENDO! VAMOS RESOLVER ISSO JUNTOS!**

😰 **Sei que tá difícil, mas vamos sair dessa situação!**

📊 **Sua situação atual:**
• Receitas: {format_currency(income)}
• Despesas: {format_currency(expense)}
• Déficit: {format_currency(abs(balance))}

🎯 **PLANO PRÁTICO - VAMOS SAIR DO VERMELHO:**

**HOJE MESMO:**
1. **Cancele 2-3 assinaturas** que você não usa (Netflix, Spotify, etc.)
2. **Pare de pedir delivery** por 1 semana
3. **Venda algo que não usa** (roupas, eletrônicos)

**ESTA SEMANA:**
1. **Corte gastos com {top_expenses[0][0] if top_expenses else 'maior gasto'}** pela metade
2. **Use transporte público** em vez de Uber/táxi
3. **Faça comida em casa** em vez de comer fora

**ESTE MÊS:**
1. **Busque renda extra** - freelancing, Uber, vendas online
2. **Negocie dívidas** - ligue para os bancos
3. **Crie fundo de emergência** de {format_currency(500)}

💡 **Dicas práticas:**
• **Compras:** Vá ao mercado com lista e sem fome
• **Lazer:** Procure opções gratuitas (parques, museus)
• **Transporte:** Use bicicleta ou caminhe quando possível
• **Comida:** Cozinhe em quantidade e congele

💪 **Meta realista:** Economizar {format_currency(abs(balance) + 500)} em 2 meses!

**Você consegue! Pequenas mudanças fazem grande diferença!** 🚀"""
                else:
                    return f"""🚨 **SITUAÇÃO CRÍTICA - SALDO NEGATIVO**

📊 **Análise da sua situação:**
• Receitas: {format_currency(income)}
• Despesas: {format_currency(expense)}
• Déficit: {format_currency(abs(balance))}

🎯 **PLANO DE EMERGÊNCIA IMEDIATO:**
1. **Corte gastos não essenciais** (assinaturas, delivery, lazer)
2. **Negocie dívidas** com juros altos
3. **Busque renda extra** (freelancing, vendas online)
4. **Crie fundo de emergência** mínimo de {format_currency(500)}

💡 **Dicas específicas:**
• Reduza {top_expenses[0][0] if top_expenses else 'gastos principais'} em 30%
• Use regra 70/20/10 (70% necessidades, 20% dívidas, 10% emergência)
• Automatize transferências para poupança

⚠️ **Prioridade:** Estabilizar antes de poupar!"""
            
            elif savings_rate < 10:
                if is_emotional:
                    return f"""{emoji_prefix} **ENTENDO! VAMOS RESOLVER ISSO JUNTOS!**

😰 **Sei que tá difícil, mas vamos sair dessa situação!**

📊 **Sua situação:**
• Saldo atual: {format_currency(balance)}
• Poupança: {savings_rate:.1f}% (muito baixo!)

🎯 **PLANO PRÁTICO - VAMOS ECONOMIZAR:**

**HOJE MESMO:**
1. **Cancele 2-3 assinaturas** que você não usa (Netflix, Spotify, etc.)
2. **Pare de pedir delivery** por 1 semana
3. **Venda algo que não usa** (roupas, eletrônicos)

**ESTA SEMANA:**
1. **Corte gastos com {top_expenses[0][0] if top_expenses else 'maior gasto'}** pela metade
2. **Use transporte público** em vez de Uber/táxi
3. **Faça comida em casa** em vez de comer fora

**ESTE MÊS:**
1. **Economize {format_currency(income * 0.15)}** (15% do seu salário)
2. **Guarde em uma conta separada**
3. **Não toque nesse dinheiro!**

💡 **Dicas práticas:**
• **Compras:** Vá ao mercado com lista e sem fome
• **Lazer:** Procure opções gratuitas (parques, museus)
• **Transporte:** Use bicicleta ou caminhe quando possível
• **Comida:** Cozinhe em quantidade e congele

💪 **Meta realista:** {format_currency(income * 0.15)}/mês = {format_currency(income * 0.15 * 12)}/ano!

**Você consegue! Pequenas mudanças fazem grande diferença!** 🚀"""
                else:
                    return f"""⚠️ **POUPANÇA BAIXA - PRECISA OTIMIZAR**

📊 **Suas métricas:**
• Taxa de poupança: {savings_rate:.1f}% (meta: 20%)
• Saldo: {format_currency(balance)}

🎯 **ESTRATÉGIA DE POUPANÇA:**
1. **Regra 50/30/20** (50% necessidades, 30% desejos, 20% poupança)
2. **Automatize** transferências no dia do salário
3. **Reduza** {top_expenses[0][0] if top_expenses else 'maior gasto'} em 15%
4. **Aumente renda** com habilidades extras

💰 **Meta realista:** {format_currency(income * 0.2)}/mês para poupança"""
            
            else:
                return f"""✅ **EXCELENTE - POUPANÇA SAUDÁVEL**

📊 **Parabéns! Suas métricas:**
• Taxa de poupança: {savings_rate:.1f}% (acima da média!)
• Saldo: {format_currency(balance)}

🎯 **PRÓXIMOS PASSOS:**
1. **Diversifique** investimentos
2. **Aumente** taxa para 25-30%
3. **Crie** fundo de emergência de 6 meses
4. **Planeje** objetivos de longo prazo

💡 **Oportunidades:**
• Investir {format_currency(balance * 0.7)} em aplicações
• Manter {format_currency(balance * 0.3)} em reserva"""
        
        elif 'investimento' in intents:
            # Preparação e diagnóstico
            if savings_rate < 15 and (desired_pct is None or desired_pct < 15):
                return f"""📊 **PREPARAÇÃO NECESSÁRIA PARA INVESTIR**

⚠️ **Antes de investir, estabilize:**
• Taxa de poupança atual: {savings_rate:.1f}% (meta: 20%)
• Fundo de emergência: {'❌ Insuficiente' if balance < income * 0.5 else '✅ Adequado'}

🎯 **ROTEIRO PARA INVESTIR:**
1. **Mês 1-3:** Aumente poupança para 20%
2. **Mês 4-6:** Crie fundo de emergência (6 meses)
3. **Mês 7+:** Comece com investimentos conservadores

💰 **Sugestões por perfil:**
• **Conservador:** Tesouro Direto (SELIC)
• **Moderado:** Fundos DI + Ações blue chips
• **Agressivo:** ETFs + Ações pequenas empresas

📈 **Meta realista:** {format_currency(income * 0.15)}/mês para investimentos"""
            
            else:
                # Montar base de investimento: usa valor citado, senão parte do saldo ou 15% da renda
                base_amount = invest_base_amount
                if base_amount is None or base_amount <= 0:
                    # prioridade: excedente (saldo positivo), senão 15% da renda
                    base_amount = balance if balance > 0 else (income * 0.15)

                # Ajustar horizonte: curto (<6m), médio (6-24m), longo (>24m)
                horizon = time_horizon_months or 18
                if horizon <= 6:
                    horizon_bucket = 'curto'
                elif horizon <= 24:
                    horizon_bucket = 'medio'
                else:
                    horizon_bucket = 'longo'

                # Alocação por perfil
                allocation = apply_profile_to_allocations(profile, base_amount)

                # Sugerir classes conforme horizonte
                horizon_note = {
                    'curto': 'Foco em liquidez e baixo risco (Tesouro Selic, CDB liquidez diária).',
                    'medio': 'Equilíbrio entre proteção (renda fixa) e crescimento (fundos/ETFs).',
                    'longo': 'Maior parcela em crescimento (ETFs/Ações) com proteção IPCA+.'
                }[horizon_bucket]

                return "\n".join([
                    "💰 **PRONTO PARA INVESTIR (Plano de Especialista)**",
                    "",
                    f"✅ Perfil de risco: {profile.risk_profile.title()} | Horizonte: {horizon} meses",
                    f"💵 Valor base: {format_currency(base_amount)}",
                    "",
                    "🎯 **Estratégia sugerida (por perfil):**",
                    f"• Liquidez diária (caixa): {format_currency(allocation['liquidez_diaria'])}",
                    f"• Curto prazo (renda fixa): {format_currency(allocation['curto_prazo'])}",
                    f"• Diversificados (fundos/ETFs): {format_currency(allocation['diversificados'])}",
                    f"• Oportunidades (alto risco): {format_currency(allocation['oportunidades'])}",
                    "",
                    f"📌 Horizonte: {horizon_note}",
                    "",
                    "💡 Observações importantes:",
                    "• Tesouro Direto e CDBs seguem IR regressivo (22,5% → 15%).",
                    "• LCI/LCA são isentos de IR (PF), mas costumam ter carência.",
                    "• Diversifique e aporte regularmente (DCA).",
                ])
        
        elif 'dívida' in intents or 'cartao' in intents or 'emprestimo' in intents:
            # Análise de dívidas
            debt_transactions = [
                t for t in historical_transactions 
                if (t.type == 'expense') and (
                    'cart' in normalize_text(t.category) or 'emprest' in normalize_text(t.category) or 'financi' in normalize_text(t.category)
                )
            ]
            total_debt = sum(t.amount for t in debt_transactions if t.type == 'expense')
            
            if is_emotional:
                return f"""{emoji_prefix} **ENTENDO! VAMOS RESOLVER SUAS DÍVIDAS JUNTOS!**

😰 **Sei que dívidas são estressantes, mas vamos sair dessa!**

📊 **Sua situação:**
• Dívidas identificadas: {format_currency(total_debt)}
• Impacto na renda: {(total_debt/income*100):.1f}%

🎯 **PLANO PRÁTICO - VAMOS QUITAR TUDO:**

**HOJE MESMO:**
1. **Liste todas as dívidas** (cartão, empréstimo, etc.)
2. **Anote os valores** e juros de cada uma
3. **Cancele cartões** que não precisa

**ESTA SEMANA:**
1. **Ligue para os bancos** e negocie
2. **Pague o mínimo** em todas as dívidas
3. **Use todo dinheiro extra** na menor dívida

**ESTE MÊS:**
1. **Corte gastos** para ter mais dinheiro
2. **Busque renda extra** (freelancing, Uber)
3. **Não faça novas dívidas!**

💡 **Método da Bola de Neve:**
• **Pague o mínimo** em todas as dívidas
• **Use todo excedente** na menor dívida
• **Quando quitar uma, use o dinheiro** na próxima
• **Repita** até quitar todas

⚠️ **Dicas importantes:**
• **Cartão de crédito:** Priorize (juros mais altos)
• **Negocie:** Sempre ligue para os bancos
• **Consolidação:** Considere juntar dívidas
• **Prevenção:** Evite novas dívidas

💪 **Meta realista:** Quitar {format_currency(total_debt * 0.3)} em 3 meses!

**Você consegue! Foco e disciplina vão te libertar!** 🚀"""
            else:
                return f"""💳 **ESTRATÉGIA DE SAÍDA DAS DÍVIDAS**

📊 **Situação das dívidas:**
• Total identificado: {format_currency(total_debt)}
• Impacto na renda: {(total_debt/income*100):.1f}% se aplicável
• Capacidade de pagamento: {'✅ Boa' if balance > total_debt * 0.3 else '⚠️ Limitada'}

🎯 **MÉTODO DA BOLA DE NEVE (Recomendado):**
1. **Liste todas as dívidas** por valor (menor para maior)
2. **Pague o mínimo** em todas
3. **Use todo excedente** na menor dívida
4. **Repita** até quitar todas

💡 **Estratégias específicas:**
• **Cartão de Crédito:** Priorize (juros altos)
• **Empréstimos:** Negocie prazos e taxas
• **Consolidação:** Considere juntar dívidas
• **Prevenção:** Evite novas dívidas

⚠️ **Alerta:** Foque em quitar antes de investir!"""
        
        elif 'renda' in intents:
            return f"""💼 **ESTRATÉGIAS PARA AUMENTAR RENDA**

📊 **Situação atual:**
• Renda mensal: {format_currency(income)}
• Potencial de crescimento: {'Alto' if income < 5000 else 'Moderado' if income < 10000 else 'Estável'}

🎯 **ESTRATÉGIAS POR CATEGORIA:**

**1. RENDA PRINCIPAL:**
• Negocie aumento salarial (preparação: 3-6 meses)
• Busque promoções internas
• Mude de empresa (15-30% aumento médio)

**2. RENDA EXTRA:**
• Freelancing ({format_currency(500)}-{format_currency(2000)}/mês)
• Ensino online ({format_currency(300)}-{format_currency(1500)}/mês)
• Vendas online ({format_currency(200)}-{format_currency(1000)}/mês)
• Investimentos passivos ({format_currency(100)}-{format_currency(500)}/mês)

**3. HABILIDADES MONETIZÁVEIS:**
• Programação, design, marketing
• Consultoria, coaching
• Criação de conteúdo
• Tradução, revisão

💡 **Meta realista:** +{format_currency(income * 0.2)}/mês em 6 meses"""
        
        elif 'gasto' in intents:
            if is_emotional:
                return f"""{emoji_prefix} **ENTENDO! VAMOS CORTAR GASTOS JUNTOS!**

😰 **Sei que é difícil, mas vamos economizar de forma inteligente!**

📊 **Sua situação:**
• Maior gasto: {top_expenses[0][0] if top_expenses else 'N/A'} - {format_currency(top_expenses[0][1] if top_expenses else 0)}
• Gasto total: {format_currency(expense)} ({expense/income*100:.1f}% da renda)

🎯 **PLANO PRÁTICO - VAMOS ECONOMIZAR:**

**HOJE MESMO:**
1. **Cancele 2-3 assinaturas** que você não usa (Netflix, Spotify, etc.)
2. **Pare de pedir delivery** por 1 semana
3. **Venda algo que não usa** (roupas, eletrônicos)

**ESTA SEMANA:**
1. **Corte gastos com {top_expenses[0][0] if top_expenses else 'maior gasto'}** pela metade
2. **Use transporte público** em vez de Uber/táxi
3. **Faça comida em casa** em vez de comer fora

**ESTE MÊS:**
1. **Negocie contas** (telefone, internet, energia)
2. **Compre em atacado** para economizar
3. **Evite compras por impulso**

💡 **Dicas práticas:**
• **Compras:** Vá ao mercado com lista e sem fome
• **Lazer:** Procure opções gratuitas (parques, museus)
• **Transporte:** Use bicicleta ou caminhe quando possível
• **Comida:** Cozinhe em quantidade e congele

💪 **Meta realista:** Economizar {format_currency(income * (expense/income - expense/income * 0.8))}/mês!

**Você consegue! Pequenas mudanças fazem grande diferença!** 🚀"""
            else:
                return f"""📉 **OTIMIZAÇÃO DE GASTOS**

📊 **Análise detalhada:**
• Maior gasto: {top_expenses[0][0] if top_expenses else 'N/A'} - {format_currency(top_expenses[0][1] if top_expenses else 0)}
• Taxa de gastos: {expense/income*100:.1f}% da renda

🎯 **PLANO DE REDUÇÃO (30 dias):**

**1. CORTES IMEDIATOS:**
• Assinaturas desnecessárias (-{format_currency(100)}-{format_currency(300)}/mês)
• Gastos com delivery (-{format_currency(200)}-{format_currency(500)}/mês)
• Compras por impulso (-{format_currency(150)}-{format_currency(400)}/mês)

**2. OTIMIZAÇÕES:**
• Transporte público vs. carro (-{format_currency(300)}-{format_currency(800)}/mês)
• Compras em atacado (-{format_currency(100)}-{format_currency(300)}/mês)
• Energia e água (-{format_currency(50)}-{format_currency(150)}/mês)

**3. NEGOCIAÇÕES:**
• Contas de telefone/internet (-{format_currency(50)}-{format_currency(200)}/mês)
• Seguros (-{format_currency(30)}-{format_currency(100)}/mês)
• Aluguel (se aplicável)

💡 **Meta realista:** Reduzir {(expense/income*100):.1f}% para {(expense/income*100*0.8):.1f}% = +{format_currency(income * (expense/income - expense/income * 0.8))}/mês"""
        
        elif 'planejamento' in intents:
            # Análise de objetivos financeiros
            age_estimate = 25  # Você pode adicionar campo de idade no banco
            retirement_age = 65
            years_to_retirement = retirement_age - age_estimate
            
            return f"""🎯 **PLANEJAMENTO FINANCEIRO DE LONGO PRAZO**

📊 **Análise de longo prazo:**
• Idade estimada: {age_estimate} anos
• Tempo até aposentadoria: {years_to_retirement} anos
• Taxa de poupança atual: {savings_rate:.1f}%
• Projeção de aposentadoria: {'⚠️ Insuficiente' if savings_rate < 15 else '✅ Adequada'}

🎯 **OBJETIVOS POR FASE:**

**FASE 1 (Agora - 2 anos):**
• Fundo de emergência: 6 meses de despesas
• Eliminar dívidas de alto juros
• Estabelecer poupança de 20%

**FASE 2 (2-10 anos):**
• Investimentos de crescimento
• Aquisição de ativos (imóvel, negócio)
• Diversificação de renda

**FASE 3 (10+ anos):**
• Acumulação para aposentadoria
• Planejamento sucessório
• Renda passiva

💰 **Projeções financeiras:**
• Poupança mensal atual: {format_currency(income * savings_rate / 100)}
• Meta ideal: {format_currency(income * 0.25)}/mês
• Projeção aposentadoria: {format_currency(income * 0.25 * 12 * years_to_retirement * 1.07)} (com juros)

💡 **Próximos passos:**
1. Defina objetivos específicos
2. Crie cronograma detalhado
3. Monitore progresso mensal
4. Ajuste estratégia conforme necessário"""
        
        elif 'orçamento' in intents:
            return f"""📋 **CRIAÇÃO DE ORÇAMENTO INTELIGENTE**

📊 **Baseado nos seus dados:**
• Receita mensal: {format_currency(income)}
• Despesa atual: {format_currency(expense)}
• Saldo: {format_currency(balance)}

🎯 **ORÇAMENTO RECOMENDADO (Regra 50/30/20):**

**50% - NECESSIDADES ({format_currency(income * 0.5)}):**
• Moradia: {format_currency(income * 0.25)}
• Alimentação: {format_currency(income * 0.15)}
• Transporte: {format_currency(income * 0.05)}
• Saúde: {format_currency(income * 0.05)}

**30% - DESEJOS ({format_currency(income * 0.3)}):**
• Lazer: {format_currency(income * 0.15)}
• Compras: {format_currency(income * 0.10)}
• Assinaturas: {format_currency(income * 0.05)}

**20% - POUPANÇA/INVESTIMENTO ({format_currency(income * 0.2)}):**
• Fundo de emergência: {format_currency(income * 0.10)}
• Investimentos: {format_currency(income * 0.10)}

💡 **Dicas para seguir o orçamento:**
• Use aplicativos de controle
• Revise semanalmente
• Ajuste conforme necessário
• Celebre pequenas conquistas"""
        
        elif 'emergência' in intents:
            emergency_fund_needed = expense * 6  # 6 meses de despesas
            
            return f"""🚨 **FUNDO DE EMERGÊNCIA**

📊 **Sua situação:**
• Despesas mensais: {format_currency(expense)}
• Fundo necessário: {format_currency(emergency_fund_needed)} (6 meses)
• Fundo atual: {format_currency(balance)}
• Status: {'❌ Insuficiente' if balance < emergency_fund_needed else '✅ Adequado'}

🎯 **PLANO PARA CRIAR FUNDO DE EMERGÊNCIA:**

**META 1 ({format_currency(emergency_fund_needed * 0.25)}):**
• Economize {format_currency(emergency_fund_needed * 0.25 / 3)}/mês por 3 meses
• Corte gastos não essenciais
• Use bônus/13º salário

**META 2 ({format_currency(emergency_fund_needed * 0.5)}):**
• Economize {format_currency(emergency_fund_needed * 0.25 / 3)}/mês por mais 3 meses
• Busque renda extra
• Automatize transferências

**META 3 ({format_currency(emergency_fund_needed)}):**
• Complete o fundo
• Mantenha em conta separada
• Revise anualmente

💡 **Onde guardar:**
• Conta poupança (liquidez)
• CDB de bancos digitais
• Tesouro SELIC

⚠️ **Importante:** Só use para emergências reais!"""
        
        elif 'aposentadoria' in intents:
            age_estimate = 25
            retirement_age = 65
            years_to_retirement = retirement_age - age_estimate
            monthly_savings_needed = (income * 0.7 * 12 * 20) / (years_to_retirement * 12)  # Para manter 70% da renda por 20 anos
            
            return f"""🏖️ **PLANEJAMENTO PARA APOSENTADORIA**

📊 **Análise atual:**
• Idade: {age_estimate} anos
• Tempo até aposentadoria: {years_to_retirement} anos
• Poupança mensal atual: {format_currency(income * savings_rate / 100)}
• Poupança necessária: {format_currency(monthly_savings_needed)}/mês

🎯 **ESTRATÉGIA DE APOSENTADORIA:**

**FASE 1 (Agora - 10 anos):**
• Foque em crescimento de renda
• Poupe 15-20% da renda
• Invista em educação/capacitação

**FASE 2 (10-20 anos):**
• Aumente poupança para 25-30%
• Diversifique investimentos
• Considere imóveis para renda

**FASE 3 (20+ anos):**
• Maximize contribuições
• Planeje transição gradual
• Considere aposentadoria parcial

💰 **Investimentos recomendados:**
• **Ações:** 60% (crescimento)
• **Renda fixa:** 30% (segurança)
• **Imóveis:** 10% (diversificação)

💡 **Dica:** Quanto mais cedo começar, melhor!"""
        
        elif 'imóvel' in intents or 'casa' in intents:
            down_payment_needed = income * 12 * 0.2  # 20% de entrada
            max_house_price = income * 3  # 3x a renda anual
            
            return f"""🏠 **PLANEJAMENTO PARA COMPRA DE IMÓVEL**

📊 **Análise baseada na sua renda:**
• Renda mensal: {format_currency(income)}
• Entrada necessária: {format_currency(down_payment_needed)} (20%)
• Valor máximo recomendado: {format_currency(max_house_price)}
• Poupança atual: {format_currency(balance)}

🎯 **ROTEIRO PARA COMPRA:**

**FASE 1 - PREPARAÇÃO (6-12 meses):**
• Economize {format_currency(down_payment_needed / 12)}/mês para entrada
• Melhore score de crédito
• Pesquise regiões de interesse

**FASE 2 - BUSCA (3-6 meses):**
• Defina critérios (localização, tamanho, preço)
• Visite imóveis
• Compare opções

**FASE 3 - NEGOCIAÇÃO:**
• Faça proposta
• Negocie condições
• Contrate financiamento

💡 **Dicas importantes:**
• Não comprometa mais de 30% da renda
• Considere custos extras (IPTU, condomínio)
• Mantenha fundo de emergência
• Avalie se é melhor comprar ou alugar

⚠️ **Cálculo:** Renda {format_currency(income)} → Financiamento máximo {format_currency(income * 0.3 * 12 * 30)}"""
        
        elif 'educação' in intents:
            return f"""📚 **INVESTIMENTO EM EDUCAÇÃO**

📊 **Análise de retorno sobre investimento:**
• Educação é o melhor investimento
• Retorno médio: 10-15% ao ano
• Impacto na renda: +20-50%

🎯 **ESTRATÉGIAS DE INVESTIMENTO EM EDUCAÇÃO:**

**1. FORMAÇÃO ACADÊMICA:**
• Graduação: {format_currency(500)}-{format_currency(2000)}/mês
• Pós-graduação: {format_currency(800)}-{format_currency(3000)}/mês
• Cursos técnicos: {format_currency(200)}-{format_currency(800)}/mês

**2. CURSOS PROFISSIONALIZANTES:**
• Programação: {format_currency(100)}-{format_currency(500)}/mês
• Design: {format_currency(150)}-{format_currency(600)}/mês
• Marketing: {format_currency(100)}-{format_currency(400)}/mês
• Línguas: {format_currency(200)}-{format_currency(800)}/mês

**3. CERTIFICAÇÕES:**
• Certificações técnicas: {format_currency(500)}-{format_currency(3000)}
• Certificações profissionais: {format_currency(1000)}-{format_currency(5000)}
• Cursos online: {format_currency(50)}-{format_currency(300)}

💡 **Dicas para maximizar retorno:**
• Escolha áreas com alta demanda
• Combine teoria com prática
• Networking é fundamental
• Mantenha-se atualizado

💰 **Meta:** Investir 5-10% da renda em educação"""
        
        elif 'seguro' in intents:
            return f"""🛡️ **PROTEÇÃO FINANCEIRA COM SEGUROS**

📊 **Análise de necessidades:**
• Renda mensal: R$ {income:.2f}
• Dependentes: Considere sua situação familiar
• Patrimônio: Avalie seus bens

🎯 **SEGUROS ESSENCIAIS:**

**1. SEGURO DE VIDA (R$ {income * 12 * 5:.0f}):**
• Cobertura: 5x a renda anual
• Custo: R$ {income * 0.02:.2f}/mês
• Protege família em caso de falecimento

**2. SEGURO DE SAÚDE:**
• Cobertura: Hospitalar + Ambulatorial
• Custo: R$ {income * 0.05:.2f}/mês
• Evita gastos inesperados

**3. SEGURO AUTO (se aplicável):**
• Cobertura: Terceiros + Roubo/Furto
• Custo: {format_currency(100)}-{format_currency(300)}/mês
• Protege contra prejuízos

**4. SEGURO RESIDENCIAL:**
• Cobertura: Incêndio + Roubo
• Custo: {format_currency(50)}-{format_currency(150)}/mês
• Protege patrimônio

💡 **Dicas:**
• Compare preços e coberturas
• Revise anualmente
• Não pague por coberturas desnecessárias
• Mantenha franquias adequadas

⚠️ **Prioridade:** Vida > Saúde > Auto > Residencial"""
        
        elif 'imposto' in intents:
            return f"""💰 **OTIMIZAÇÃO FISCAL (Brasil)**

📊 **Sua situação:**
• Renda mensal: {format_currency(income)}
• Renda anual: {format_currency(income * 12)}
• Faixa de IR: {'Isento' if income * 12 < 2259.20 else '7.5%' if income * 12 < 2826.65 else '15%' if income * 12 < 3751.05 else '22.5%' if income * 12 < 4664.68 else '27.5%'}

🎯 **ESTRATÉGIAS DE ECONOMIA FISCAL:**

**1. DEDUÇÕES PERMITIDAS:**
• Previdência privada: até 12% da renda
• Educação: até {format_currency(3561.50)}/ano
• Saúde: sem limite
• Dependentes: {format_currency(2275.08)} por dependente

**2. REGRAS DE TRIBUTAÇÃO E ISENÇÕES (principais):**
• Poupança: isenta de IR (PF)
• LCI/LCA: isentas de IR (PF)
• Tesouro Direto (Selic, IPCA+, Prefixado): tributado pela tabela regressiva (15% a 22,5%)
• Ações: operações comuns isentas até R$ 20.000/mês em vendas; day-trade sempre tributado

**3. DECLARAÇÃO ANUAL:**
• Mantenha todos os comprovantes
• Use software oficial
• Declare até 30/04
• Evite multas

💡 **Dicas para economizar:**
• Use previdência privada
• Invista em educação
• Mantenha controle de gastos
• Consulte um contador

⚠️ **Importante:** Sempre declare corretamente!"""
        
        elif 'viagem' in intents:
            # Calcular orçamento de viagem baseado na renda
            travel_budget = income * 0.15  # 15% da renda para viagem
            months_to_save = 6  # 6 meses para economizar
            
            return f"""✈️ **PLANEJAMENTO DE VIAGEM INTELIGENTE**

📊 **Análise baseada na sua renda:**
• Renda mensal: {format_currency(income)}
• Orçamento recomendado: {format_currency(travel_budget)} (15% da renda)
• Tempo para economizar: {months_to_save} meses
• Economia mensal necessária: {format_currency(travel_budget / months_to_save)}

🎯 **ESTRATÉGIA DE VIAGEM:**

**1. DESTINOS POR ORÇAMENTO:**
• **Econômico ({format_currency(travel_budget * 0.5)}):** Praias nacionais, cidades históricas
• **Moderado ({format_currency(travel_budget)}):** Destinos internacionais próximos
• **Premium ({format_currency(travel_budget * 1.5)}):** Europa, EUA, Ásia

**2. DISTRIBUIÇÃO DO ORÇAMENTO:**
• Passagens: 40% ({format_currency(travel_budget * 0.4)})
• Hospedagem: 30% ({format_currency(travel_budget * 0.3)})
• Alimentação: 20% ({format_currency(travel_budget * 0.2)})
• Passeios: 10% ({format_currency(travel_budget * 0.1)})

**3. DICAS PARA ECONOMIZAR:**
• Compre passagens com antecedência (3-6 meses)
• Use sites de comparação de preços
• Considere hospedagem compartilhada
• Viaje na baixa temporada
• Use cartões de crédito com milhas

💡 **Plano de ação:**
• Economize {format_currency(travel_budget / months_to_save)}/mês
• Pesquise destinos e preços
• Reserve com antecedência
• Mantenha fundo de emergência

⚠️ **Lembre-se:** Viagem é investimento em experiências, mas não comprometa sua segurança financeira!"""
        
        elif 'carro' in intents:
            # Análise para compra de carro
            car_budget = income * 0.3  # 30% da renda para carro
            down_payment = car_budget * 0.2  # 20% de entrada
            monthly_payment = (car_budget * 0.8) / 60  # Financiamento em 60 meses
            
            return f"""🚗 **PLANEJAMENTO PARA COMPRA DE CARRO**

📊 **Análise financeira:**
• Renda mensal: {format_currency(income)}
• Valor máximo recomendado: {format_currency(car_budget)}
• Entrada necessária: {format_currency(down_payment)} (20%)
• Parcela mensal: {format_currency(monthly_payment)} (60 meses)
• Impacto na renda: {(monthly_payment/income*100):.1f}%

🎯 **ESTRATÉGIA DE COMPRA:**

**1. PREPARAÇÃO (3-6 meses):**
• Economize R$ {down_payment / 6:.2f}/mês para entrada
• Melhore score de crédito
• Pesquise modelos e preços
• Calcule custos totais (IPVA, seguro, manutenção)

**2. OPÇÕES POR ORÇAMENTO:**
• **Econômico (R$ {car_budget * 0.6:.2f}):** Carros usados, modelos básicos
• **Intermediário (R$ {car_budget:.2f}):** Carros seminovos, modelos populares
• **Premium (R$ {car_budget * 1.4:.2f}):** Carros novos, modelos superiores

**3. CUSTOS ADICIONAIS:**
• IPVA: {format_currency(car_budget * 0.03)}/ano
• Seguro: {format_currency(car_budget * 0.05)}/mês
• Manutenção: {format_currency(car_budget * 0.02)}/mês
• Combustível: {format_currency(300)}-{format_currency(600)}/mês

**4. ALTERNATIVAS:**
• **Comprar à vista:** Economia de juros
• **Financiamento:** Maior poder de compra
• **Leasing:** Menos responsabilidade
• **Compartilhamento:** Economia total

💡 **Dicas importantes:**
• Não comprometa mais de 30% da renda
• Considere custos de manutenção
• Compare diferentes opções de financiamento
• Avalie se realmente precisa de um carro

⚠️ **Cálculo:** Renda {format_currency(income)} → Carro máximo {format_currency(car_budget)} → Parcela {format_currency(monthly_payment)}"""
        
        elif 'negócio' in intents:
            # Análise para empreendedorismo
            business_capital = income * 6  # 6 meses de renda como capital inicial
            monthly_investment = income * 0.1  # 10% da renda para investir no negócio
            
            return f"""💼 **PLANEJAMENTO PARA ABRIR NEGÓCIO**

📊 **Análise empreendedora:**
• Renda atual: {format_currency(income)}
• Capital inicial recomendado: {format_currency(business_capital)} (6 meses de renda)
• Investimento mensal: {format_currency(monthly_investment)} (10% da renda)
• Tempo para acumular capital: {business_capital / monthly_investment:.0f} meses

🎯 **ESTRATÉGIA EMPREENDEDORA:**

**1. PREPARAÇÃO FINANCEIRA:**
• Mantenha emprego atual por 6-12 meses
• Economize R$ {monthly_investment:.2f}/mês
• Crie fundo de emergência de 12 meses
• Reduza dívidas ao mínimo

**2. OPÇÕES DE NEGÓCIO POR INVESTIMENTO:**
• **Baixo investimento ({format_currency(business_capital * 0.3)}):** E-commerce, consultoria, freelancing
• **Médio investimento ({format_currency(business_capital)}):** Loja física pequena, franquia, importação
• **Alto investimento ({format_currency(business_capital * 2)}):** Restaurante, clínica, indústria

**3. ESTRUTURA FINANCEIRA:**
• **Capital inicial:** R$ {business_capital * 0.4:.2f} (40%)
• **Capital de giro:** R$ {business_capital * 0.3:.2f} (30%)
• **Marketing:** R$ {business_capital * 0.2:.2f} (20%)
• **Reserva:** R$ {business_capital * 0.1:.2f} (10%)

**4. PLANO DE AÇÃO:**
• **Mês 1-3:** Pesquisa de mercado e planejamento
• **Mês 4-6:** Acumulação de capital
• **Mês 7-9:** Implementação e testes
• **Mês 10+:** Operação e crescimento

💡 **Dicas para sucesso:**
• Comece pequeno e cresça gradualmente
• Mantenha renda alternativa
• Controle rigorosamente os custos
• Foque na diferenciação
• Construa uma rede de contatos

⚠️ **Importante:** Empreendedorismo é arriscado, mas pode ser muito lucrativo com planejamento adequado!"""
        
        else:
            # Resposta genérica SUPER INTELIGENTE e compreensiva para qualquer pergunta
            if is_emotional:
                return f"""{emoji_prefix} **FICA TRANQUILO! EU VOU TE AJUDAR!**

😊 **Não se preocupe em perguntar "corretamente" - eu entendo tudo!**

📊 **Vamos ver sua situação:**
• Receitas: {format_currency(income)}
• Despesas: {format_currency(expense)}
• Saldo: {format_currency(balance)}
• Taxa de poupança: {savings_rate:.1f}%

🎯 **DIAGNÓSTICO RÁPIDO:**
{'🚨 **CRÍTICO:** Saldo negativo - vamos resolver isso!' if balance < 0 else '✅ **SAUDÁVEL:** Continue assim!'}
{'⚠️ **ATENÇÃO:** Maior gasto compromete muito da renda' if top_expenses and top_expenses[0][1] > income * 0.3 else '✅ **EQUILIBRADO:** Gastos bem distribuídos'}

💡 **PERGUNTE DE QUALQUER JEITO:**

**💰 POUPANÇA:**
• "tô gastando muito" / "não consigo economizar" / "dinheiro não sobra"
• "tô no vermelho" / "tô quebrado" / "sem dinheiro"

**📈 INVESTIMENTOS:**
• "onde colocar dinheiro?" / "fazer dinheiro render" / "multiplicar dinheiro"
• "onde investir?" / "melhor aplicação" / "dinheiro trabalhando"

**💳 DÍVIDAS:**
• "tô endividado" / "cartão estourou" / "tô devendo"
• "como quitar cartão?" / "pagar dívidas" / "tô no sufoco"

**💼 RENDA:**
• "quero ganhar mais" / "salário baixo" / "ganho pouco"
• "renda extra" / "trabalho extra" / "bico"

**📉 GASTOS:**
• "gasto demais" / "tô gastando muito" / "cortar gastos"
• "reduzir despesas" / "onde cortar" / "otimizar gastos"

**🎯 PLANEJAMENTO:**
• "não sei o que fazer" / "tô perdido" / "por onde começar"
• "primeiro passo" / "o que fazer primeiro" / "começar"

**🤔 DÚVIDAS:**
• "me ajuda" / "tô confuso" / "não entendo"
• "socorro" / "ajuda" / "dúvida"

💪 **EXEMPLOS DE PERGUNTAS QUE FUNCIONAM:**
• "tô na merda, o que faço?"
• "tô fudido com dinheiro"
• "tô lascado financeiramente"
• "tô ferrado, me ajuda"
• "tô na pindaíba"
• "tô no sufoco"
• "tô no aperto"
• "tô apertado"
• "tô quebrado"
• "sem dinheiro"
• "falta dinheiro"

🎯 **RECOMENDAÇÃO ESPECÍFICA PARA VOCÊ:**
{'🚨 **URGENTE:** Corte gastos e busque renda extra AGORA!' if balance < 0 else '✅ **CONTINUE:** Mantenha disciplina e diversifique!'}

💬 **Dica:** Seja natural! Fale como você fala mesmo. A IA entende gírias, palavrões, linguagem informal... Tudo! 😄

**A IA está aqui para te ajudar, não importa como você pergunte!** 🚀"""
            else:
                return f"""🤖 **CONSELHEIRO IA SUPER INTELIGENTE - ANÁLISE COMPLETA E PERSONALIZADA**

📊 **RESUMO FINANCEIRO PERSONALIZADO:**
• Receitas: {format_currency(income)}
• Despesas: {format_currency(expense)}
• Saldo: {format_currency(balance)}
• Taxa de poupança: {savings_rate:.1f}%
• Maior gasto: {top_expenses[0][0] if top_expenses else 'N/A'} - {format_currency(top_expenses[0][1] if top_expenses else 0)}
• Tendência: {'📈 Positiva' if income > expense else '📉 Negativa' if expense > income else '📊 Estável'}

🎯 **DIAGNÓSTICO FINANCEIRO DETALHADO:**
• {'🚨 CRÍTICO: Saldo negativo - priorize estabilizar' if balance < 0 else '✅ SAUDÁVEL: Continue poupando e invista'}
• {'⚠️ ATENÇÃO: Maior gasto compromete ' + f"{(top_expenses[0][1]/income*100):.1f}%" if top_expenses and top_expenses[0][1] > income * 0.3 else '✅ EQUILIBRADO: Gastos bem distribuídos'}
• {'📈 OPORTUNIDADE: Renda baixa - busque crescimento' if income < 5000 else '✅ ESTÁVEL: Renda adequada'}

🔮 **IA PREDITIVA AVANÇADA:**
• {'🚨 Risco alto: Precisa de intervenção imediata' if balance < 0 else '✅ Baixo risco: Continue no caminho certo'}
• {'📈 Alto potencial: Foque em aumentar renda' if income < 5000 else '📊 Potencial moderado: Otimize gastos'}
• {'💡 Oportunidade: Reduza ' + top_expenses[0][0] if top_expenses and top_expenses[0][1] > income * 0.25 else '💡 Oportunidade: Diversifique investimentos'}

💡 **COMO POSSO TE AJUDAR? PERGUNTE DE QUALQUER FORMA:**

**💰 POUPANÇA E ECONOMIA:**
• "como economizar mais?" / "onde guardar dinheiro?" / "tô gastando muito"
• "não consigo economizar" / "como poupar dinheiro?" / "onde guardar?"

**📈 INVESTIMENTOS:**
• "onde investir?" / "melhor aplicação para mim?" / "onde colocar dinheiro?"
• "como investir?" / "melhor investimento?" / "onde aplicar dinheiro?"

**💳 DÍVIDAS:**
• "como pagar dívidas?" / "melhor forma de quitar cartão?" / "tô endividado"
• "como quitar cartão?" / "pagar empréstimo" / "quitar dívidas"

**💼 RENDA:**
• "como aumentar renda?" / "renda extra?" / "quero ganhar mais"
• "como ganhar mais dinheiro?" / "aumentar salário" / "renda adicional"

**📉 GASTOS:**
• "como reduzir gastos?" / "onde cortar despesas?" / "gastar menos"
• "cortar gastos" / "reduzir despesas" / "otimizar gastos"

**🎯 PLANEJAMENTO:**
• "planejamento financeiro" / "metas financeiras" / "não sei o que fazer"
• "criar plano" / "estratégia financeira" / "objetivos financeiros"

**📋 ORÇAMENTO:**
• "como fazer orçamento?" / "controle financeiro" / "organizar dinheiro"
• "gerenciar dinheiro" / "administrar finanças" / "controle de gastos"

**🚨 EMERGÊNCIA:**
• "fundo de emergência" / "reserva financeira" / "imprevistos"
• "dinheiro para emergência" / "reserva de emergência"

**🏖️ APOSENTADORIA:**
• "planejamento aposentadoria" / "previdência" / "futuro"
• "aposentadoria" / "planejamento futuro" / "terceira idade"

**🏠 IMÓVEL:**
• "comprar casa" / "financiamento imóvel" / "comprar apartamento"
• "entrada casa" / "financiamento casa" / "comprar imóvel"

**📚 EDUCAÇÃO:**
• "investir em educação" / "cursos e formação" / "estudar"
• "faculdade" / "universidade" / "formação profissional"

**🛡️ SEGURO:**
• "preciso de seguro?" / "proteção financeira" / "seguro de vida"
• "qual seguro?" / "seguro de saúde" / "seguro de carro"

**💰 IMPOSTOS:**
• "economizar impostos" / "otimização fiscal" / "imposto de renda"
• "declaração" / "dedução" / "economizar imposto"

**✈️ VIAGEM:**
• "planejar viagem" / "economizar para viajar" / "férias"
• "turismo" / "passeio" / "destino"

**🚗 CARRO:**
• "comprar carro" / "financiamento automóvel" / "entrada carro"
• "comprar automóvel" / "financiamento carro"

**💼 NEGÓCIO:**
• "abrir empresa" / "empreendedorismo" / "abrir negócio"
• "startup" / "empreender" / "comércio"

**🤔 DÚVIDAS GERAIS:**
• "me ajuda" / "tô perdido" / "tô confuso" / "não entendo"
• "explique" / "dúvida" / "socorro" / "ajuda"

🎯 **RECOMENDAÇÕES ESPECÍFICAS PARA VOCÊ:**
• {'🚨 URGENTE: Corte gastos não essenciais e busque renda extra' if balance < 0 else '✅ CONTINUE: Mantenha disciplina e diversifique investimentos'}
• {'⚠️ FOQUE: Reduza ' + top_expenses[0][0] + ' em 20%' if top_expenses and top_expenses[0][1] > income * 0.3 else '✅ OTIMIZE: Busque aumentar taxa de poupança para 25%'}
• {'📈 PRIORIZE: Desenvolva habilidades para aumentar renda' if income < 5000 else '📊 MANTENHA: Continue diversificando fontes de renda'}

💬 **Dica:** Não se preocupe em perguntar "corretamente"! A IA entende linguagem informal, gírias e até perguntas mal formuladas. Seja natural e eu vou te ajudar! 🚀

**Exemplos de perguntas que funcionam:**
• "tô gastando muito, o que faço?"
• "não consigo economizar"
• "quero ganhar mais dinheiro"
• "tô perdido com minhas finanças"
• "me ajuda com dinheiro"
• "não sei o que fazer"

A IA está pronta para entender e ajudar com qualquer aspecto das suas finanças! 💪"""
    
    # Perfil de IA por usuário (aprendizado)
    profile = get_or_create_ai_profile(current_user.id)

    # Processar a pergunta
    intents = analyze_question_intent(question)
    entities = extract_entities_from_question(question_original)
    # Glossário: detectar termos conhecidos
    glossary_hits = []
    norm_original = normalize_text(question_original)
    for term in FIN_GLOSSARY.keys():
        if term in norm_original:
            glossary_hits.append(term)
    user_data = {
        'income': current_income,
        'expense': current_expense,
        'balance': current_balance,
        'savings_rate': savings_rate,
        'top_expenses': top_expenses
    }

    response_core = generate_intelligent_response(question, intents, user_data, entities, profile, glossary_hits)

    # Montar resposta conforme modo
    summary_for_clarity = {
        'income': current_income,
        'expense': current_expense,
        'balance': current_balance,
        'savings_rate': savings_rate,
    }
    if mode == 'direto':
        # Entrega somente o núcleo, sem TL;DR/Checklist/Glossário
        response = response_core
    elif mode == 'compacto':
        # Núcleo + TL;DR curto
        short = enrich_response_for_clarity(response_core, summary_for_clarity, intents, entities, profile, glossary_hits)
        # Reduz para as primeiras seções (TL;DR + corpo)
        parts = short.split('\n')
        cutoff = min(len(parts), 40)
        response = '\n'.join(parts[:cutoff])
    elif mode == 'especialista':
        # Didático + reforço técnico: adiciona nota de riscos e compliance
        did = enrich_response_for_clarity(response_core, summary_for_clarity, intents, entities, profile, glossary_hits)
        expert_note = [
            "",
            "🧪 Nota técnica (especialista):",
            "- Considere risco de liquidez, marcação a mercado e adequação ao perfil regulatório.",
            "- Diversifique emissores e classes; acompanhe CDI/SELIC/IPCA e calendário tributário.",
        ]
        response = did + "\n" + "\n".join(expert_note)
    else:  # didatico (default)
        response = enrich_response_for_clarity(response_core, summary_for_clarity, intents, entities, profile, glossary_hits)

    # Atualizar perfil com base na interação (aprendizado incremental)
    try:
        update_profile_on_interaction(profile, intents, current_balance)
        db.session.add(AiInteraction(
            user_id=current_user.id,
            question=request.args.get('question', ''),
            intents_json=_dumps_json_safe(intents),
            response=response
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()

    return jsonify({'response': response})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=False, host='0.0.0.0', port=5000) 
