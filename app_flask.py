from reportlab.platypus import Table, TableStyle
from flask import redirect, url_for, flash

import io
import json
import os
import functools
import math
import numpy as np
from flask import Flask, render_template, request, session, jsonify, send_file, send_from_directory, redirect, url_for, flash, abort
from werkzeug.utils import secure_filename
from matplotlib import pyplot as plt
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from flask import request
from werkzeug.utils import secure_filename
from functools import wraps
from pathlib import Path
from datetime import datetime
import re
import io
import json
import os
from sqlalchemy import func
from sqlalchemy import func, UniqueConstraint
from decimal import Decimal
from flask_migrate import Migrate


def draw_table_with_pagination(canvas, data, colWidths, y, page_height, margin=60, font_size=9, titulo=None):
    """
    Desenha uma tabela com quebra automática de página se ultrapassar o espaço útil,
    e repete o título (se fornecido) sempre que quebrar.
    Retorna a posição Y do cursor após a tabela.
    """
    from reportlab.platypus import Table, TableStyle
    from reportlab.lib import colors

    # Defina o estilo padrão da tabela
    table_style = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#dce6f2')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), font_size),
        ('LEFTPADDING', (0,1), (-1,-1), 4),
        ('RIGHTPADDING', (0,1), (-1,-1), 4),
    ])

    n_rows = len(data)
    start = 0

    while start < n_rows:
        # Título (se for a primeira página da tabela ou após quebra)
        if titulo:
            canvas.setFont('Helvetica-Bold', 14)
            canvas.drawString(50, y, titulo)
            y -= 20

        # Calcula quantas linhas cabem nesta página
        # Testa o tamanho real com a fatia que cabe, começando pelo máximo possível
        max_rows = n_rows - start
        for test_rows in range(max_rows, 0, -1):
            t = Table(data[start:start+test_rows], colWidths=colWidths)
            t.setStyle(table_style)
            w, h = t.wrapOn(canvas, 0, 0)
            if (y - h) >= margin:
                break

        # Desenha a fatia que cabe
        page_data = data[start:start+test_rows]
        t = Table(page_data, colWidths=colWidths)
        t.setStyle(table_style)
        w, h = t.wrapOn(canvas, 0, 0)
        t.drawOn(canvas, 50, y - h)
        y -= (h + 10)

        start += test_rows

        # Se ainda tem mais linhas, faz quebra de página e repete título
        if start < n_rows:
            canvas.showPage()
            y = page_height - margin

    return y


import os
import functools
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_secret')
# pega senha da env ou usa este valor como padrão
app.config['APP_PASSWORD'] = os.environ.get('APP_PASSWORD', 'Hanier123')


from functools import wraps
from flask import request, Response

# ─── Autenticação simples ──────────────────────────────────────────────
USERNAME = "admin"
PASSWORD = "galo123"

def check_auth(username, password):
    return username == USERNAME and password == PASSWORD

def authenticate():
    return Response(
        'Acesso restrito.\n'
        'Usuário ou senha inválidos.', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated


import os
from flask_sqlalchemy import SQLAlchemy

# ─── Banco de dados ──────────────────────────────────────────────────────
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'sqlite:///tingimento.db'  # fallback para desenvolvimento local
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Produto(db.Model):
    __tablename__ = 'produtos'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), unique=True, nullable=False, index=True)
    funcao = db.Column(db.String(120), nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    atualizado_em = db.Column(db.DateTime, onupdate=db.func.now(), default=db.func.now(), nullable=False)

    # relação com contratipos
    contratipos = db.relationship(
        'ProdutoContratipo',
        backref='produto',
        cascade="all, delete-orphan",
        lazy='selectin'
    )

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "funcao": self.funcao,
            "ativo": self.ativo,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
            "atualizado_em": self.atualizado_em.isoformat() if self.atualizado_em else None,
        }


class ProdutoContratipo(db.Model):
    __tablename__ = 'produto_contratipos'

    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id', ondelete='CASCADE'), nullable=False)
    nome = db.Column(db.String(120), nullable=False)        # nome do contratipo
    forca_pct = db.Column(db.Numeric(5, 2), nullable=False) # força em %

    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    atualizado_em = db.Column(db.DateTime, onupdate=db.func.now(), default=db.func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('produto_id', 'nome', name='uix_contratipo_por_produto_nome'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "produto_id": self.produto_id,
            "nome": self.nome,
            "forca_pct": float(self.forca_pct) if self.forca_pct is not None else None,
            "ativo": self.ativo,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
            "atualizado_em": self.atualizado_em.isoformat() if self.atualizado_em else None,
        }


class Funcao(db.Model):
    __tablename__ = 'funcoes'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), unique=True, nullable=False, index=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    atualizado_em = db.Column(db.DateTime, onupdate=db.func.now(), default=db.func.now(), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "ativo": self.ativo,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
            "atualizado_em": self.atualizado_em.isoformat() if self.atualizado_em else None,
        }




# imports no topo (se já não tiver)
from sqlalchemy import func
from decimal import Decimal

class RegraReceita(db.Model):
    __tablename__ = 'regras_receita'

    id = db.Column(db.Integer, primary_key=True)

    # chaves
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id', ondelete='RESTRICT'), nullable=False)
    fibra_id   = db.Column(db.Integer, db.ForeignKey('fibras.id',    ondelete='RESTRICT'), nullable=False)

    # função do produto (string do próprio Produto.funcao, salva para busca mais fácil)
    funcao_produto = db.Column(db.String(120), nullable=False)

    # parâmetros
    pct_corante_inicial = db.Column(db.Numeric(6, 3), nullable=False)  # ex.: 0.500
    pct_corante_final   = db.Column(db.Numeric(6, 3), nullable=False)  # ex.: 2.000
    quantidade          = db.Column(db.Numeric(10, 3), nullable=False) # ex.: 10.000
    unidade             = db.Column(db.String(10), nullable=False)     # "%", "g/L"

    # regra especial de corante (opcional)
    regra_especial = db.Column(db.Boolean, default=False, nullable=False)
    corante_id     = db.Column(db.Integer, db.ForeignKey('corantes.id', ondelete='RESTRICT'), nullable=True)
    resultado_novo = db.Column(db.Numeric(10, 3), nullable=True)

    # timestamps
    criado_em     = db.Column(db.DateTime, server_default=func.now(), nullable=False)
    atualizado_em = db.Column(db.DateTime, onupdate=func.now(), default=func.now(), nullable=False)

    # relacionamentos (se ainda não tiver)
    produto = db.relationship('Produto')
    fibra   = db.relationship('Fibra')
    corante = db.relationship('Corante')

    def to_dict(self):
        return {
            "id": self.id,
            "produto_id": self.produto_id,
            "produto_nome": self.produto.nome if self.produto else None,
            "funcao_produto": self.funcao_produto,
            "fibra_id": self.fibra_id,
            "fibra_nome": self.fibra.nome if self.fibra else None,
            "pct_corante_inicial": float(self.pct_corante_inicial),
            "pct_corante_final": float(self.pct_corante_final),
            "quantidade": float(self.quantidade),
            "unidade": self.unidade,
            "regra_especial": self.regra_especial,
            "corante_id": self.corante_id,
            "corante_nome": self.corante.nome if self.corante else None,
            "resultado_novo": float(self.resultado_novo) if self.resultado_novo is not None else None,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
        }



# ─── Uploads (Database – Gráficos) ─────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
app.config['UPLOAD_ROOT'] = str(BASE_DIR / 'uploads')
Path(app.config['UPLOAD_ROOT']).mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {'.pdf', '.json'}

def allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


# ─── Modelos ────────────────────────────────────────────────────────────
class Corante(db.Model):
    __tablename__ = 'corantes'
    id               = db.Column(db.Integer, primary_key=True)
    nome             = db.Column(db.String(100), nullable=False)
    fornecedor       = db.Column(db.String(100))
    color_index      = db.Column(db.String(50))
    tamanho_molecula = db.Column(db.String(50))


class Fibra(db.Model):
    __tablename__ = 'fibras'
    id            = db.Column(db.Integer, primary_key=True)
    tipo          = db.Column(db.String(10), nullable=False)
    nome          = db.Column(db.String(100), nullable=False)
    perc_fibra    = db.Column(db.Float, nullable=False)
    perc_elastano = db.Column(db.Float, nullable=False)


# --- Modelo: Regra da Receita Inteligente ---
class RegraRI(db.Model):
    __tablename__ = 'regras_ri'

    id = db.Column(db.Integer, primary_key=True)

    # função escolhida (texto, vindo de 'funcoes' mas armazenamos o nome)
    funcao = db.Column(db.String(120), nullable=False)

    # relacionamentos
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id', ondelete='RESTRICT'), nullable=False)
    fibra_id   = db.Column(db.Integer, db.ForeignKey('fibras.id', ondelete='RESTRICT'), nullable=False)
    corante_id = db.Column(db.Integer, db.ForeignKey('corantes.id', ondelete='RESTRICT'), nullable=True)  # apenas se regra especial

    # parâmetros
    pct_corante_ini = db.Column(db.Numeric(6, 3), nullable=False)  # ex.: 0.50 = 0,50%
    pct_corante_fim = db.Column(db.Numeric(6, 3), nullable=False)
    qtde_produto    = db.Column(db.Numeric(12, 3), nullable=False) # unidade livre (ex.: g/L)
    unidade         = db.Column(db.String(10), nullable=False, default='%')  # "%", "g/L"


    regra_especial_corante = db.Column(db.Boolean, default=False, nullable=False)
    resultado_novo         = db.Column(db.Numeric(12, 3), nullable=True)  # usado se regra especial

    ativo      = db.Column(db.Boolean, default=True, nullable=False)
    criado_em  = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    atualizado_em = db.Column(db.DateTime, onupdate=db.func.now(), default=db.func.now(), nullable=False)

    # (opcional) atalho de backrefs se quiser
    produto = db.relationship('Produto')
    fibra   = db.relationship('Fibra')
    corante = db.relationship('Corante')

    def to_dict(self):
        return {
            "id": self.id,
            "funcao": self.funcao,
            "produto_id": self.produto_id,
            "fibra_id": self.fibra_id,
            "corante_id": self.corante_id,
            "pct_corante_ini": float(self.pct_corante_ini),
            "pct_corante_fim": float(self.pct_corante_fim),
            "qtde_produto": float(self.qtde_produto),
            "regra_especial_corante": self.regra_especial_corante,
            "resultado_novo": float(self.resultado_novo) if self.resultado_novo is not None else None,
            "ativo": self.ativo,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
            "atualizado_em": self.atualizado_em.isoformat() if self.atualizado_em else None,
        }







# ─── Database – Gráficos ───────────────────────────────────────────────
class Cliente(db.Model):
    __tablename__ = 'clientes'
    id   = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False, unique=True)
    obs  = db.Column(db.String(255))


class Arquivo(db.Model):
    __tablename__ = 'arquivos'
    id          = db.Column(db.Integer, primary_key=True)
    cliente_id  = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False, index=True)
    nome        = db.Column(db.String(255), nullable=False)     # nome original
    caminho     = db.Column(db.String(512), nullable=False)     # relativo a UPLOAD_ROOT
    mimetype    = db.Column(db.String(100), nullable=False)
    tamanho     = db.Column(db.Integer, nullable=False, default=0)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    cliente     = db.relationship('Cliente', backref='arquivos')


def _cliente_dir(cliente: Cliente) -> Path:
    slug = secure_filename(cliente.nome) or f'cliente-{cliente.id}'
    d = Path(app.config['UPLOAD_ROOT']) / f'{cliente.id}_{slug}'
    d.mkdir(parents=True, exist_ok=True)
    return d

# cria as tabelas (execute uma vez)
with app.app_context():
    db.create_all()

LOGO_PATH = os.path.join(app.root_path, 'static', 'logo_hanier.png')

# decorator para proteger rotas
def login_required(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapped

def admin_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        # se já passou pela checagem
        if session.get('admin_authenticated'):
            return f(*args, **kwargs)

        # se for envio do formulário de senha
        if request.method == 'POST':
            if request.form.get('admin_password') == 'galo123':
                session['admin_authenticated'] = True
                return redirect(request.path)
            else:
                return render_template('admin_login.html', error='Senha incorreta')

        # na primeira vez, mostra o form
        return render_template('admin_login.html', error=None)
    return wrapped

@app.before_request
def init_session():
    session.setdefault('etapas', [])
    session.setdefault('receita', [])
    session.setdefault('titulo', 'Gráficos de Tingimento')

# página de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password') == app.config['APP_PASSWORD']:
            session['logged_in'] = True
            return redirect(url_for('menu_view'))
    return render_template('login.html')

# ─── ROTA RAIZ ───
@app.route('/')
@login_required
def home_view():
    return redirect(url_for('menu_view'))

@app.route('/menu')
@login_required
def menu_view():
    return render_template('menu.html')

@app.route('/processo')
@login_required
def processo_view():
    etapas = session.get('etapas', [])
    total_min = sum(et.get('dados', {}).get('tempo', 0) for et in etapas)
    horas, minutos = divmod(int(total_min), 60)
    tempo_str = f"{horas}:{minutos:02d}"
    return render_template(
        'index.html',
        etapas=etapas,
        tempo_total=tempo_str,
        titulo=session.get('titulo', ''),
        etapas_json=json.dumps(etapas, ensure_ascii=False),
        receita_json=json.dumps(session.get('receita', []), ensure_ascii=False)
    )
# rota “custo”
@app.route('/custo')
@login_required
def custo_view():
    return render_template('custo.html')

@app.route("/arquivos")
@requires_auth
def arquivos():
    clientes = Cliente.query.order_by(Cliente.nome.asc()).all()
    return render_template("arquivos.html", clientes=clientes)

# rota “receita inteligente”
@app.route('/receita-inteligente')
@requires_auth
def receita_inteligente_view():
    # lê todos os corantes e fibras cadastrados
    corantes = Corante.query.all()
    fibras = Fibra.query.order_by(Fibra.tipo, Fibra.nome).all()
    return render_template('ri.html', corantes=corantes, fibras=fibras)

# ─── ROTAS DE CADASTRO ───────────────────────────────────────────────────
# ─── CADASTRO DE CORANTE ────────────────────────────────────────────────
# ─── CADASTRO / EDIÇÃO DE CORANTE ─────────────────────────────────────────
from sqlalchemy import asc

@app.route('/cadastro/corante', methods=['GET', 'POST'])
@login_required
@admin_required
def cadastro_corante():
    # sempre buscar em ordem alfabética
    corantes = Corante.query.order_by(asc(Corante.nome)).all()

    if request.method == 'POST':
        cid = request.form.get('id')
        if cid:
            c = Corante.query.get(int(cid))
            if not c:
                flash('Corante não encontrado.', 'error')
                return redirect(url_for('cadastro_corante'))
        else:
            c = Corante()
            db.session.add(c)

        # garante apenas a primeira letra maiúscula
        raw_nome = request.form.get('nome', '').strip()
        if raw_nome:
            c.nome = raw_nome[0].upper() + raw_nome[1:]
        else:
            c.nome = ''

        c.fornecedor       = request.form.get('fornecedor') or None
        c.color_index      = request.form.get('color_index') or None
        c.tamanho_molecula = request.form.get('tamanho_molecula') or None

        db.session.commit()
        flash(f'Corante {"editado" if cid else "cadastrado"} com sucesso!', 'success')
        return redirect(url_for('cadastro_corante'))


    return render_template('cadastro_corante.html', corantes=corantes)

# ─── API Clientes (Database – Gráficos) ────────────────────────────────
@app.route('/api/clientes', methods=['GET'])
@login_required
def api_listar_clientes():
    try:
        rows = Cliente.query.order_by(Cliente.nome.asc()).all()
        return jsonify([{'id': c.id, 'nome': c.nome} for c in rows])
    except Exception as e:
        app.logger.error('Erro ao listar clientes: %s', e, exc_info=True)
        return jsonify(success=False, error=str(e)), 500

@app.route('/api/clientes', methods=['POST'])
@login_required
def api_criar_cliente():
    try:
        data = request.get_json(silent=True) or {}
        nome = (data.get('nome') or '').strip()
        if not nome:
            return jsonify(success=False, error='Nome do cliente é obrigatório'), 400
        ex = Cliente.query.filter(db.func.lower(Cliente.nome) == nome.lower()).first()
        if ex:
            return jsonify(success=True, id=ex.id, nome=ex.nome, ja_existia=True)
        c = Cliente(nome=nome)
        db.session.add(c); db.session.commit()
        return jsonify(success=True, id=c.id, nome=c.nome)
    except Exception as e:
        db.session.rollback()
        app.logger.error('Erro ao criar cliente: %s', e, exc_info=True)
        return jsonify(success=False, error=str(e)), 500

    
from sqlalchemy.orm import selectinload
from flask import request, jsonify, render_template, redirect, url_for, flash

# --- Página: Cadastrar Regra ---
@app.route('/cadastro_regra', methods=['GET', 'POST'])
def cadastro_regra():
    # se vier ?id=... vamos editar
    regra_id = request.args.get('id') or request.form.get('regra_id')

    if request.method == 'POST':
        funcao       = (request.form.get('funcao') or '').strip()
        produto_id   = request.form.get('produto_id')
        fibra_id     = request.form.get('fibra_id')
        pct_ini      = request.form.get('pct_corante_inicial')
        pct_fim      = request.form.get('pct_corante_final')
        qtde_produto = request.form.get('quantidade_produto')
        unidade      = (request.form.get('unidade') or '%').strip()

        regra_especial = request.form.get('regra_especial_corante') in ('on', 'true', '1')
        corante_id     = request.form.get('corante_id') if regra_especial else None
        resultado_novo = request.form.get('resultado_novo') if regra_especial else None

        if not funcao or not produto_id or not fibra_id:
            flash('Selecione Função, Produto e Fibra.', 'error')
            return redirect(url_for('cadastro_regra', id=regra_id) if regra_id else url_for('cadastro_regra'))

        def _num(v):
            if v is None or str(v).strip() == '':
                return None
            return float(str(v).replace(',', '.'))

        try:
            pct_ini_f   = _num(pct_ini)
            pct_fim_f   = _num(pct_fim)
            qtde_prod_f = _num(qtde_produto)
            if pct_ini_f is None or pct_fim_f is None or qtde_prod_f is None:
                raise ValueError('Valores numéricos obrigatórios.')
        except Exception:
            flash('Valores inválidos. Use números (ex.: 0,500).', 'error')
            return redirect(url_for('cadastro_regra', id=regra_id) if regra_id else url_for('cadastro_regra'))

        # valida campos da regra especial (se marcada)
        if regra_especial:
            try:
                if not corante_id:
                    raise ValueError('Selecione o corante da regra especial.')
                resultado_novo_f = _num(resultado_novo)
                if resultado_novo_f is None:
                    raise ValueError('Informe o "resultado novo" da regra especial.')
            except Exception as e:
                flash(str(e), 'error')
                return redirect(url_for('cadastro_regra', id=regra_id) if regra_id else url_for('cadastro_regra'))
        else:
            resultado_novo_f = None
            corante_id = None

        if regra_id:  # EDITAR
            r = RegraRI.query.get_or_404(int(regra_id))
            r.funcao = funcao
            r.produto_id = int(produto_id)
            r.fibra_id = int(fibra_id)
            r.pct_corante_ini = pct_ini_f
            r.pct_corante_fim = pct_fim_f
            r.qtde_produto = qtde_prod_f
            if hasattr(r, 'unidade'):
                r.unidade = unidade
            r.regra_especial_corante = regra_especial
            r.corante_id = int(corante_id) if corante_id else None
            r.resultado_novo = resultado_novo_f
            db.session.commit()
            flash('Regra atualizada.', 'success')
        else:
            # CRIAR: se "regra especial" estiver marcada, criar DUAS regras (normal + especial)
            try:
                # 1) Regra NORMAL (sempre criada)
                regra_normal = RegraRI(
                    funcao=funcao,
                    produto_id=int(produto_id),
                    fibra_id=int(fibra_id),
                    pct_corante_ini=pct_ini_f,
                    pct_corante_fim=pct_fim_f,
                    qtde_produto=qtde_prod_f,
                    regra_especial_corante=False,
                    corante_id=None,
                    resultado_novo=None
                )
                if hasattr(regra_normal, 'unidade'):
                    regra_normal.unidade = unidade
                db.session.add(regra_normal)

                # 2) Regra ESPECIAL (apenas se marcado)
                if regra_especial:
                    regra_critica = RegraRI(
                        funcao=funcao,
                        produto_id=int(produto_id),
                        fibra_id=int(fibra_id),
                        pct_corante_ini=pct_ini_f,
                        pct_corante_fim=pct_fim_f,
                        qtde_produto=qtde_prod_f,
                        regra_especial_corante=True,
                        corante_id=int(corante_id),
                        resultado_novo=resultado_novo_f
                    )
                    if hasattr(regra_critica, 'unidade'):
                        regra_critica.unidade = unidade
                    db.session.add(regra_critica)

                db.session.commit()
                flash(
                    'Regra padrão criada'
                    + (' e regra de corante crítico criada.' if regra_especial else '.'),
                    'success'
                )
            except Exception as e:
                db.session.rollback()
                flash('Erro ao salvar as regras. Tente novamente.', 'error')
                return redirect(url_for('cadastro_regra'))

        return redirect(url_for('cadastro_regra'))

    # GET: carregar listas e (se houver) a regra para preencher
    funcoes  = Funcao.query.filter_by(ativo=True).order_by(Funcao.nome.asc()).all()
    fibras   = Fibra.query.order_by(Fibra.nome.asc()).all()
    corantes = Corante.query.order_by(Corante.nome.asc()).all()

    regras = (
        RegraRI.query
        .options(
            selectinload(RegraRI.produto),
            selectinload(RegraRI.fibra),
            selectinload(RegraRI.corante)
        )
        .order_by(RegraRI.id.desc())
        .all()
    )

    regra_obj = None
    if regra_id:
        regra_obj = RegraRI.query.get_or_404(int(regra_id))

    return render_template(
        'cadastro_regra.html',
        funcoes=funcoes, fibras=fibras, corantes=corantes, regras=regras, regra=regra_obj
    )


@app.route('/api/produtos', methods=['GET'])
def api_listar_produtos():
    funcao = (request.args.get('funcao') or '').strip()
    q = Produto.query
    if funcao:
        q = q.filter(Produto.funcao == funcao)
    itens = q.filter_by(ativo=True).order_by(Produto.nome.asc()).all()
    return jsonify([p.to_dict() for p in itens]), 200

@app.route('/api/fibras', methods=['GET'])
def api_listar_fibras():
    fibras = Fibra.query.order_by(Fibra.nome.asc()).all()
    return jsonify([
        {
            "id": f.id,
            # concatenando tipo + nome para aparecer igual na listagem
            "nome": f"{f.tipo} – {f.nome} ({f.perc_fibra}% {f.tipo}, {f.perc_elastano}% PUE)"
        }
        for f in fibras
    ])


@app.route('/api/corantes', methods=['GET'])
def api_listar_corantes():
    itens = Corante.query.order_by(Corante.nome.asc()).all()
    return jsonify([
        {
            "id": c.id,
            "nome": c.nome,
            "fornecedor": c.fornecedor or ""
        } for c in itens
    ]), 200







# --- APIs auxiliares ---

# lista produtos pela função (nome da função, não id)
@app.route('/api/produtos/by_funcao')
def api_produtos_by_funcao():
    nome = (request.args.get('nome') or '').strip()
    q = Produto.query
    if nome:
        q = q.filter(Produto.funcao == nome)
    itens = q.order_by(Produto.nome.asc()).all()
    return jsonify([{"id": p.id, "nome": p.nome} for p in itens])

# (opcionais; caso você queira usar via ajax também)
@app.route('/api/fibras')
def api_fibras():
    itens = Fibra.query.order_by(Fibra.nome.asc()).all()
    return jsonify([{"id": f.id, "nome": f.nome} for f in itens])




# ─── EXCLUSÃO DE CORANTE ──────────────────────────────────────────────────
@app.route('/cadastro/corante/<int:cid>/delete', methods=['POST'])
@login_required
def excluir_corante(cid):
    c = Corante.query.get_or_404(cid)
    db.session.delete(c)
    db.session.commit()
    flash('Corante excluído com sucesso!', 'success')
    return redirect(url_for('cadastro_corante'))


    # para GET, busca tudo e passa pra template
    corantes = Corante.query.all()
    return render_template('cadastro_corante.html', corantes=corantes)


# app.py (ou suas rotas)


from sqlalchemy.orm import selectinload
from flask import request, jsonify

@app.route('/cadastro_produto', methods=['GET', 'POST'])
def cadastro_produto():
    if request.method == 'POST':
        pid = request.form.get('id')
        nome = (request.form.get('nome') or '').strip()
        funcao = (request.form.get('funcao') or '').strip()
        ativo = True if request.form.get('ativo') in ('on', 'true', '1') else False

        if not nome or not funcao:
            flash('Preencha Nome e Função.', 'error')
            return redirect(url_for('cadastro_produto'))

        if pid:  # editar
            p = Produto.query.get_or_404(pid)
            # checa duplicidade de nome
            ja = Produto.query.filter(Produto.id != p.id, Produto.nome == nome).first()
            if ja:
                flash('Já existe outro produto com esse nome.', 'error')
                return redirect(url_for('cadastro_produto'))

            p.nome = nome
            p.funcao = funcao
            p.ativo = ativo
            db.session.commit()
            flash('Produto atualizado.', 'success')
        else:  # criar
            if Produto.query.filter_by(nome=nome).first():
                flash('Já existe um produto com esse nome.', 'error')
                return redirect(url_for('cadastro_produto'))

            p = Produto(nome=nome, funcao=funcao, ativo=ativo)
            db.session.add(p)
            db.session.commit()
            flash('Produto cadastrado.', 'success')

        return redirect(url_for('cadastro_produto'))

    # consulta já carregando os contratipos
    produtos = (Produto.query
                .options(selectinload(Produto.contratipos))
                .order_by(Produto.nome.asc())
                .all())

    return render_template('cadastro_produto.html', produtos=produtos)


@app.route('/excluir_produto/<int:pid>', methods=['POST'])
def excluir_produto(pid):
    p = Produto.query.get_or_404(pid)
    db.session.delete(p)
    db.session.commit()
    flash('Produto excluído.', 'success')
    return redirect(url_for('cadastro_produto'))


# =========================
# API de Contratipos
# =========================

@app.route('/api/produtos/<int:produto_id>/contratipos', methods=['GET'])
def api_listar_contratipos(produto_id):
    # opcional: validar existência do produto
    if not Produto.query.get(produto_id):
        return jsonify({"erro": "Produto não encontrado."}), 404

    itens = (ProdutoContratipo.query
             .filter_by(produto_id=produto_id)
             .order_by(ProdutoContratipo.nome.asc())
             .all())
    return jsonify([c.to_dict() for c in itens]), 200


@app.route('/api/produtos/<int:produto_id>/contratipos', methods=['POST'])
def api_criar_contratipo(produto_id):
    if not Produto.query.get(produto_id):
        return jsonify({"erro": "Produto não encontrado."}), 404

    data = request.get_json(force=True, silent=True) or {}
    nome = (data.get('nome') or '').strip()
    forca = data.get('forca_pct')

    # validações
    if not nome:
        return jsonify({"erro": "Informe o nome do contratipo."}), 400

    try:
        forca = float(str(forca).replace(',', '.'))
    except (TypeError, ValueError):
        return jsonify({"erro": "Força inválida. Use número entre 0 e 100."}), 400

    if not (0 <= forca <= 100):
        return jsonify({"erro": "Força deve estar entre 0 e 100."}), 400

    # unicidade por produto+nome
    ja = ProdutoContratipo.query.filter_by(produto_id=produto_id, nome=nome).first()
    if ja:
        return jsonify({"erro": "Já existe um contratipo com esse nome para este produto."}), 409

    c = ProdutoContratipo(produto_id=produto_id, nome=nome, forca_pct=forca, ativo=True)
    db.session.add(c)
    db.session.commit()
    return jsonify(c.to_dict()), 201


@app.route('/api/contratipos/<int:cid>', methods=['PUT', 'PATCH'])
def api_atualizar_contratipo(cid):
    c = ProdutoContratipo.query.get_or_404(cid)
    data = request.get_json(force=True, silent=True) or {}

    nome = data.get('nome')
    forca = data.get('forca_pct')
    ativo = data.get('ativo')

    if nome is not None:
        nome = nome.strip()
        if not nome:
            return jsonify({"erro": "Nome não pode ser vazio."}), 400
        # checa unicidade por produto+nome
        ja = ProdutoContratipo.query.filter(
            ProdutoContratipo.id != c.id,
            ProdutoContratipo.produto_id == c.produto_id,
            ProdutoContratipo.nome == nome
        ).first()
        if ja:
            return jsonify({"erro": "Já existe outro contratipo com esse nome neste produto."}), 409
        c.nome = nome

    if forca is not None:
        try:
            forca = float(str(forca).replace(',', '.'))
        except (TypeError, ValueError):
            return jsonify({"erro": "Força inválida. Use número entre 0 e 100."}), 400
        if not (0 <= forca <= 100):
            return jsonify({"erro": "Força deve estar entre 0 e 100."}), 400
        c.forca_pct = forca

    if ativo is not None:
        c.ativo = bool(ativo)

    db.session.commit()
    return jsonify(c.to_dict()), 200


@app.route('/api/contratipos/<int:cid>', methods=['DELETE'])
def api_excluir_contratipo(cid):
    c = ProdutoContratipo.query.get_or_404(cid)
    db.session.delete(c)
    db.session.commit()
    return jsonify({"ok": True}), 200


@app.route('/api/funcoes', methods=['GET'])
def api_listar_funcoes():
    q = (request.args.get('q') or '').strip()
    query = Funcao.query
    if q:
        like = f"%{q}%"
        query = query.filter(Funcao.nome.ilike(like))
    itens = query.filter_by(ativo=True).order_by(Funcao.nome.asc()).all()
    return jsonify([f.to_dict() for f in itens]), 200


@app.route('/api/funcoes', methods=['POST'])
def api_criar_funcao():
    data = request.get_json(force=True, silent=True) or {}
    nome = (data.get('nome') or '').strip()
    if not nome:
        return jsonify({"erro": "Informe o nome da função."}), 400

    ja = Funcao.query.filter_by(nome=nome).first()
    if ja:
        if not ja.ativo:
            ja.ativo = True
            db.session.commit()
            return jsonify(ja.to_dict()), 200
        return jsonify({"erro": "Já existe uma função com esse nome."}), 409

    f = Funcao(nome=nome, ativo=True)
    db.session.add(f)
    db.session.commit()
    return jsonify(f.to_dict()), 201



@app.route('/regras', methods=['GET'])
def regras_list():
    regras = (
        db.session.query(RegraRI)
        .join(Produto)  # produto_id é NOT NULL, join simples é OK
        .options(
            selectinload(RegraRI.produto),
            selectinload(RegraRI.fibra),
            selectinload(RegraRI.corante)
        )
        .order_by(
            Produto.nome.asc(),
            RegraRI.pct_corante_ini.asc(),
            RegraRI.pct_corante_fim.asc(),
            RegraRI.regra_especial_corante.asc()  # False primeiro, True depois
        )
        .all()
    )
    return render_template('regras_list.html', regras=regras)


@app.route('/api/regras', methods=['GET'])
def api_regras():
    regras = (RegraReceita.query
              .options(selectinload(RegraReceita.produto),
                       selectinload(RegraReceita.fibra),
                       selectinload(RegraReceita.corante))
              .order_by(RegraReceita.id.desc())
              .all())
    return jsonify([r.to_dict() for r in regras]), 200


@app.route('/regras/<int:regra_id>/excluir', methods=['POST'])
def excluir_regra(regra_id):
    r = RegraRI.query.get_or_404(regra_id)
    db.session.delete(r)
    db.session.commit()
    flash('Regra excluída.', 'success')
    return redirect(url_for('regras_list'))


# ─── CADASTRO DE FIBRA ─────────────────────────────────────────────────
@app.route('/cadastro/fibra', methods=['GET', 'POST'])
@login_required
@admin_required
def cadastro_fibra():
    # busca por tipo e nome em ordem alfabética; se nomes iguais, maior % de fibra primeiro
    from sqlalchemy import desc
    fibras = (
        Fibra.query
             .order_by(Fibra.tipo, Fibra.nome, desc(Fibra.perc_fibra))
             .all()
    )

    if request.method == 'POST':
        fid = request.form.get('id')
        if fid:
            # edição
            f = Fibra.query.get(int(fid))
            if not f:
                flash('Fibra não encontrada.', 'error')
                return redirect(url_for('cadastro_fibra'))
        else:
            # criação
            f = Fibra()
            db.session.add(f)

        # preenche/atualiza campos
        f.tipo          = request.form['tipo']
        f.nome          = request.form['nome']
        f.perc_fibra    = float(request.form['perc_fibra'])
        f.perc_elastano = float(request.form['perc_elastano'])

        db.session.commit()
        flash(f'Fibra {"editada" if fid else "cadastrada"} com sucesso!', 'success')
        return redirect(url_for('cadastro_fibra'))

# ─── API Arquivos (Database – Gráficos) ────────────────────────────────
@app.route('/api/arquivos', methods=['GET'])
@login_required
def api_listar_arquivos():
    cliente_id = request.args.get('cliente_id', type=int)
    if not cliente_id:
        return jsonify(success=False, error='cliente_id ausente'), 400
    q = Arquivo.query.filter_by(cliente_id=cliente_id).order_by(Arquivo.created_at.desc())
    return jsonify(success=True, arquivos=[
        {
            'id': a.id,
            'nome': a.nome,
            'mimetype': a.mimetype,
            'tamanho': a.tamanho,
            'created_at': a.created_at.isoformat()
        } for a in q.all()
    ])

@app.route('/api/upload', methods=['POST'])
@login_required
def api_upload_arquivo():
    cliente_id = request.form.get('cliente_id', type=int)
    if not cliente_id:
        return jsonify(success=False, error='cliente_id ausente'), 400
    cliente = Cliente.query.get(cliente_id)
    if not cliente:
        return jsonify(success=False, error='Cliente não encontrado'), 404

    files = request.files.getlist('files')
    if not files:
        return jsonify(success=False, error='Nenhum arquivo recebido'), 400

    saved = []
    base_dir = _cliente_dir(cliente)
    for f in files:
        if not f or not f.filename:
            continue
        if not allowed_file(f.filename):
            return jsonify(success=False, error=f'Extensão não permitida: {f.filename}'), 400
        fname = secure_filename(f.filename)
        dest = base_dir / fname
        i = 1
        while dest.exists():
            stem, ext = Path(fname).stem, Path(fname).suffix
            dest = base_dir / f"{stem}({i}){ext}"; i += 1
        f.save(str(dest))
        relpath = dest.relative_to(app.config['UPLOAD_ROOT'])
        arq = Arquivo(
            cliente_id=cliente.id,
            nome=fname,
            caminho=str(relpath),
            mimetype=f.mimetype or ('application/pdf' if fname.lower().endswith('.pdf') else 'application/json'),
            tamanho=dest.stat().st_size
        )
        db.session.add(arq); saved.append(arq)
    db.session.commit()
    return jsonify(success=True, count=len(saved), ids=[a.id for a in saved])

@app.route('/download/<int:arquivo_id>')
@login_required
def download_arquivo(arquivo_id):
    a = Arquivo.query.get_or_404(arquivo_id)
    full = Path(app.config['UPLOAD_ROOT']) / a.caminho
    if not full.exists():
        abort(404)
    return send_from_directory(str(full.parent), full.name, as_attachment=True, download_name=a.nome)

@app.route('/api/arquivo/<int:arquivo_id>', methods=['DELETE'])
@login_required
def api_excluir_arquivo(arquivo_id):
    a = Arquivo.query.get_or_404(arquivo_id)
    full = Path(app.config['UPLOAD_ROOT']) / a.caminho
    try:
        if full.exists():
            full.unlink()
        db.session.delete(a); db.session.commit()
        return jsonify(success=True)
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, error=str(e)), 500




    # GET — renderiza a página com a lista
    return render_template('cadastro_fibra.html', fibras=fibras)


    # para GET
    return render_template('cadastro_fibra.html', fibras=fibras)

@app.route('/cadastro/fibra/<int:fid>/delete', methods=['POST'])
@login_required
def excluir_fibra(fid):
    f = Fibra.query.get_or_404(fid)
    db.session.delete(f)
    db.session.commit()
    flash('Fibra excluída com sucesso!', 'success')
    return redirect(url_for('cadastro_fibra'))

# logout (opcional)
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    etapas = session.get('etapas', [])
    total_min = sum(
        et.get('dados', {}).get('tempo', 0)
        for et in etapas
    )
    horas, minutos = divmod(int(total_min), 60)
    tempo_str = f"{horas}:{minutos:02d}"
    return render_template(
        'index.html',
        etapas=etapas,
        tempo_total=tempo_str,
        titulo=session.get('titulo', ''),
        etapas_json=json.dumps(etapas),
        receita_json=json.dumps(session.get('receita', []))
    )

@app.route('/inserir_etapa/<int:index>', methods=['POST'])
def inserir_etapa(index):
    etapas = session.get('etapas', [])
    data = request.get_json()
    # Use insert no índice certo!
    etapas.insert(index, {'tipo': data['tipo'], 'dados': data['dados']})
    session['etapas'] = etapas
    return jsonify(success=True)

@app.route('/adicionar_etapa', methods=['POST'])
def adicionar_etapa():
    data = request.get_json()
    session['etapas'].append(data)
    session.modified = True
    total_min = sum(
        et.get('dados', {}).get('tempo', 0)
        for et in session['etapas']
    )
    horas, minutos = divmod(int(total_min), 60)
    tempo_str = f"{horas}:{minutos:02d}"
    return jsonify(success=True, tempo_total=tempo_str)


@app.route('/editar_etapa/<int:idx>', methods=['POST'])
def editar_etapa(idx):
    data = request.get_json()
    if 0 <= idx < len(session['etapas']):
        session['etapas'][idx] = data
        session.modified = True
    return jsonify(success=True)


@app.route('/excluir_etapa/<int:idx>', methods=['POST'])
def excluir_etapa(idx):
    if 0 <= idx < len(session['etapas']):
        session['etapas'].pop(idx)
        session.modified = True
    return jsonify(success=True)


@app.route('/subir_etapa/<int:idx>', methods=['POST'])
def subir_etapa(idx):
    et = session['etapas']
    if 0 < idx < len(et):
        et[idx-1], et[idx] = et[idx], et[idx-1]
        session.modified = True
    return jsonify(success=True)


@app.route('/descer_etapa/<int:idx>', methods=['POST'])
def descer_etapa(idx):
    et = session['etapas']
    if 0 <= idx < len(et)-1:
        et[idx], et[idx+1] = et[idx+1], et[idx]
        session.modified = True
    return jsonify(success=True)


@app.route('/limpar_etapas', methods=['POST'])
def limpar_etapas():
    session['etapas'].clear()
    session['receita'].clear()   # ← limpa também o array de receita
    session['titulo'] = ''
    session.modified = True
    return jsonify(success=True)


@app.route('/atualizar_titulo', methods=['POST'])
def atualizar_titulo():
    data = request.get_json()
    session['titulo'] = data.get('titulo', session['titulo'])
    session.modified = True
    return jsonify(success=True)


@app.route('/salvar_dados')
def salvar_dados():
    dados = {
        'titulo': session['titulo'],
        'etapas': session['etapas'],
        'receita': session['receita']
    }
    buf = io.BytesIO()
    buf.write(json.dumps(dados, indent=2).encode())
    buf.seek(0)
    # Gera nome do arquivo a partir do título, removendo caracteres inválidos
    filename = secure_filename(titulo) + '.pdf'
    
    return send_file(
        buf,
        mimetype='application/pdf',
        download_name=filename,
        as_attachment=True
    )


@app.route('/carregar_dados', methods=['POST'])
def carregar_dados():
    file = request.files.get('file')
    try:
        # carrega JSON (pode ser dict ou lista)
        data = json.load(file)

        if isinstance(data, dict):
            # formato { "titulo":..., "etapas":[...], "receita":[...] }
            session['titulo']  = data.get('titulo', session['titulo'])
            session['etapas']  = data.get('etapas', [])
            session['receita'] = data.get('receita', [])
        elif isinstance(data, list):
            # formato antigo: raiz é lista de etapas
            session['etapas'] = data
            # mantém titulo/receita atuais, se houver
        else:
            # tipo inesperado
            return jsonify(success=False, error="JSON deve ser objeto ou lista"), 400

        session.modified = True
        return jsonify(success=True)

    except Exception as e:
        return jsonify(success=False, error=str(e))



@app.route('/grafico.png')
def grafico_png():
    etapas = session.get('etapas', [])
    if not etapas:
        return '', 204

    # ─── PASSO 1: inicialize as listas ───
    tempos = [0]
    injetores = []
    patamares = []
    dosadores = []
    termoregs = []

    acum = 0

    # Descobre temp inicial corretamente (água quente/fria)
    if etapas[0]['tipo'] == 'Encher Máquina':
        resumo = etapas[0]['dados'].get('resumo', '').lower()
        temp_atual = 40 if 'quente' in resumo else 25
        # Começa do zero até temp_atual em 3 min (linha inclinada)
        tempos.append(acum + 3)
        temps = [0, temp_atual]
        acum += 3
        start_index = 1  # <- já processou a etapa 0!
    else:
        temp_atual = etapas[0]['dados'].get('temperatura', 0)
        temps = [temp_atual]
        start_index = 0

    # Processa todas as etapas na ordem, atualizando temp e tempo corretamente
    for et in etapas[start_index:]:
        tipo = et.get('tipo')
        dados = et.get('dados', {})
        t = dados.get('tempo', 0)

        if tipo == 'Encher Máquina':
            resumo = dados.get('resumo', '').lower()
            temp_final = 40 if 'quente' in resumo else 25
            # Linha inclinada sempre em 3 min de temp_atual até temp_final
            tempos.append(acum + 3)
            temps.append(temp_final)
            acum += 3
            temp_atual = temp_final

        elif tipo == 'Termoregulação':
            temp_final = dados.get('temperatura', temp_atual)
            grad_raw = dados.get('gradiente', None)
            try:
                grad = float(grad_raw)
                if grad == 0:
                    grad = 5   # usar 5 se gradiente for zero (mas mostrar 0 no texto)
            except (TypeError, ValueError):
                grad = 1
            t_rampa = abs(float(temp_final) - float(temp_atual)) / grad if grad else 0
            xs, ys = acum, temp_atual
            xe, ye = acum + t_rampa, temp_final
            tempos.append(xe)
            temps.append(ye)
            termoregs.append((xs, xe, ys, ye, grad if grad_raw != 0 else 0))
            acum += t_rampa
            temp_atual = temp_final

        elif tipo == 'Patamar':
            tempos.append(acum + t)
            temps.append(temp_atual)
            patamares.append((acum, acum + t, temp_atual, t))
            acum += t

        elif tipo == 'Injetar Produto':
            resumo = dados.get('resumo', '')
            # pega só a parte antes da vírgula (ex: "Seq A")
            seq_full = resumo.split(',')[0].strip()
            # remove "Seq " para ficar apenas "A"
            letter = seq_full.replace('Seq ', '')
            injetores.append((acum + t/2, temp_atual, letter))
            tempos.append(acum + t)
            temps.append(temp_atual)
            acum += t

        elif tipo == 'Dosagem de Produto':
            parts = [p.strip() for p in dados.get('resumo','').split(',')]
            seq   = parts[0].replace('Seq','').strip()
            td    = next((int(p.split()[1]) for p in parts if 'Dosagem' in p), t)
            curva = next((p for p in parts if 'curva' in p.lower()), '')
            dosadores.append((acum + t/2, temp_atual, seq, td, curva))
            tempos.append(acum + t)
            temps.append(temp_atual)
            acum += t

        elif tipo.lower() == 'soltar banho':
            # Linha inclinada de temp_atual até 0 em 2 minutos
            tempos.append(acum + 2)
            temps.append(0)
            acum += 2
            temp_atual = 0



        elif tipo == 'Transbordo':
            tf = dados.get('tf')
            temp_atual = int(tf) if tf is not None else temp_atual
            tempos.append(acum + t)
            temps.append(temp_atual)
            acum += t

        else:
            tempos.append(acum + t)
            temps.append(temp_atual)
            acum += t

    # ─── PASSO 3: plotagem ───
    buf = io.BytesIO()
    fig, ax = plt.subplots(figsize=(8,4))
    ax.plot(tempos, temps, marker='o', lw=1.5, markersize=3)
    ax.set_xlabel('Tempo (min)')
    ax.set_ylabel('Temperatura (°C)')
    ax.set_title(session.get('titulo',''), pad=15)

    # Injetores
    for x0, y0, seq in injetores:
        ax.annotate('', xy=(x0, y0-10.5), xytext=(x0, y0+0.2),
                    arrowprops=dict(arrowstyle='->', lw=1, mutation_scale=8),
                    clip_on=True)
        ax.text(x0, y0-11, seq, ha='center', va='top', fontsize=9)

    # Dosadores
    for x0, y0, seq, td, curva in dosadores:
        ax.annotate('', xy=(x0, y0-13.5), xytext=(x0, y0+0.2),
                    arrowprops=dict(arrowstyle='->', lw=1, mutation_scale=8),
                    clip_on=True)
        label = f"{seq}\n{td}'" + (f"\n{curva}" if curva else "")
        ax.text(x0, y0-14.0, label, ha='center', va='top', fontsize=8)

    # ─── Patamares (dwell) — agora acima da linha ───
    for xs, xe, y0, dur in patamares:
        ax.text(
            (xs + xe) / 2,   # x no meio do trecho
            y0 ,        # y 1 grau acima do nível
            f"{int(dur)}'",  # ex: "10'"
            ha='center',
            va='bottom',     # ancorado embaixo do texto (sobre a linha)
            fontsize=7,
            zorder=5,
            clip_on=False
        )

    cor_linha = ax.get_lines()[0].get_color()

    # Termoregulação — marcador, temp final à esquerda e gradiente no meio
    for xs, xe, ys, ye, grad in termoregs:
        # marca o ponto
        ax.scatter(xe, ye, s=10, color=cor_linha, zorder=5)

        # temperatura à esquerda
        ax.annotate(
            f"{ye}°C",
            xy=(xe, ye),
            xytext=(-6, 0),
            textcoords='offset points',
            ha='right',
            va='center',
            fontsize=6,
            fontweight='bold',
            zorder=6,
            clip_on=False
        )

        if grad is None:
            continue

        # calcula ponto médio da subida
        x_mid = (xs + xe) / 2
        y_mid = (ys + ye) / 2

        # desloca em DATA: 5% da largura do segmento para a direita
        dx = xe - xs
        x_grad = x_mid + dx * 0.05
        y_grad = y_mid - 1.0

        ax.text(
            x_grad, y_grad,
            f"{grad:.1f}°C/min",
            ha='left',         # alinha texto à esquerda
            va='center',       # verticalmente centrado
            fontsize=6,
            fontstyle='italic',
            zorder=6,
            clip_on=False
        )
 
   
    # Tempo total (baseado na soma dos minutos declarados em cada etapa)
    total_min = sum(
        int(et.get('dados', {}).get('tempo', 0))
        for et in etapas
    )
    h, m = divmod(total_min, 60)
    ax.text(0.98, 1.02, f"Tempo Total: {h}:{m:02d}",
            transform=ax.transAxes, ha='right', va='bottom')

    plt.tight_layout()
    fig.savefig(buf, format='png')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')










from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors

import re
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors



@app.route('/atualizar_insumos', methods=['POST'])
def atualizar_insumos():
    # recebe um JSON com a lista de insumos do JS
    session['insumos'] = request.get_json(force=True)
    session.modified = True
    return jsonify(success=True)

import re

def calcular_vapor_total(etapas, volume_litros):
    volume_m3 = volume_litros / 1000.0

    # Coeficiente ajustado (igual JS)
    total_vapor = 0
    hold_chart = {
        40: 7, 45: 8.75, 50: 10.5, 55: 12.25, 60: 14,
        65: 15.75, 70: 17.5, 75: 19.25, 80: 21, 85: 23,
        90: 25, 95: 27, 100: 29, 105: 30.55, 110: 32,
        115: 33.5, 120: 35, 125: 36.5, 130: 38, 135: 40
    }

    def get_nearest_hold(temp):
        nearest = min(hold_chart, key=lambda x: abs(x - temp))
        return nearest, hold_chart[nearest]

    # Termoregulação
    for et in etapas:
        if et['tipo'] == 'Termoregulação':
            m = re.search(r'de\s+(\d+)→(\d+)', et['dados'].get('resumo', ''))
            if m:
                Ti, Tf = int(m.group(1)), int(m.group(2))
                if Tf > Ti:
                    dT = Tf - Ti
                    kg_per_m3 = 1.93 * dT
                    total_vapor += volume_m3 * kg_per_m3

    # Patamar
    for et in etapas:
        if et['tipo'] == 'Patamar':
            m = re.search(r'(\d+)°C por (\d+)\s*min', et['dados'].get('resumo', ''))
            if m:
                T = int(m.group(1))
                mins = int(m.group(2))
                if T in hold_chart:
                    rate = hold_chart[T]
                else:
                    _, rate = get_nearest_hold(T)
                hours = mins / 60.0
                total_vapor += volume_m3 * rate * hours

    return total_vapor

def calcular_hora_maquina(etapas):
    tempo_total_min = sum(float(et['dados'].get('tempo', 0)) for et in etapas)
    return round(tempo_total_min / 60.0, 2)

def calcular_insumos(etapas, carga, relacao):
    """
    Gera a lista de insumos igual ao frontend (Vapor, Hora máquina)
    """
    volume = carga * relacao
    total_vapor = calcular_vapor_total(etapas, volume)
    custo_hora = calcular_hora_maquina(etapas)
    insumos = []

    # Vapor
    insumos.append({
        'produto': 'Vapor',
        'preco': 0.08,
        'quantidade': round(total_vapor, 2),
        'unidade': 'Kg Vapor',
        'rskg': round((0.08 * total_vapor) / carga if carga else 0, 3)
    })

    # Hora máquina
    insumos.append({
        'produto': 'Hora máquina',
        'preco': 0.80,
        'quantidade': round(custo_hora, 2),
        'unidade': 'h',
        'rskg': round(0.80 * custo_hora, 3)
    })

    return insumos


@app.route('/atualizar_receita', methods=['POST'])
def atualizar_receita():
    session['receita'] = request.get_json(force=True)
    session.modified = True
    return jsonify(success=True)

from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.utils import ImageReader



@app.route('/imprimir_pdf_inline')
def imprimir_pdf_inline():
    import io
    from flask import send_file, session, request
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib.utils import ImageReader
    from werkzeug.utils import secure_filename

    def ajustar_tabela_para_uma_pagina(data, colWidths, canvas, y_top, margem_inferior):
        n_linhas = len(data)
        altura_util = y_top - margem_inferior
        font_size = 9
        row_height = 12  # altura mínima por linha para encolher mais se necessário
        while font_size >= 5:
            table = Table(data, colWidths=colWidths, rowHeights=[row_height]*n_linhas)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#dce6f2')),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), font_size),
                ('LEFTPADDING', (0,1), (-1,-1), 2),
                ('RIGHTPADDING', (0,1), (-1,-1), 2),
                ('BOTTOMPADDING', (0,0), (-1,-1), 1),
                ('TOPPADDING', (0,0), (-1,-1), 1),
            ]))
            w, h = table.wrapOn(canvas, 0, 0)
            if h < altura_util:
                table.drawOn(canvas, 50, y_top - h)
                return y_top - h
            font_size -= 1
            row_height -= 0.7  # reduz também a altura da linha

        table.drawOn(canvas, 50, y_top - h)
        return y_top - h

    com_custo = request.args.get('com_custo', 'false').lower() in ('1','true','yes')
    titulo    = session.get('titulo', 'Relatório de Tingimento')
    filename  = secure_filename(titulo) + '.pdf'

    receita = session.get('receita', [])
    etapas  = session.get('etapas', [])
    carga   = session.get('relacao_banho_carga', 300)
    relacao = session.get('relacao_banho',        8)
    insumos = calcular_insumos(etapas, carga, relacao)
    session['insumos'] = insumos
    session.modified   = True

    # Consumo de água igual frontend
    # -- soma relações de encher máquina e transbordo --
    rels = []
    for et in etapas:
        if et.get('tipo') in ('Encher Máquina', 'Transbordo'):
            m = None
            if 'resumo' in et.get('dados', {}):
                import re
                m = re.search(r'1:(\d+)', et['dados']['resumo'])
            if m:
                rels.append(int(m.group(1)))
    rel_total = sum(rels)
    agua_litros = carga * rel_total
    agua_lkg    = rel_total if carga == 0 else agua_litros / carga

    buf = io.BytesIO()
    c   = pdf_canvas.Canvas(buf, pagesize=letter)
    c.setTitle(filename)

    # --- Logo ---
    def draw_logo():
        try:
            logo = ImageReader(LOGO_PATH)
            c.drawImage(logo, 10, letter[1] - 40, width=80, height=40, mask='auto')
        except Exception:
            pass

    # --- Dados das tabelas ---
    data_etapas = [['Tipo de Etapa','Resumo','Tempo (min)']]
    for et in etapas:
        data_etapas.append([
            et.get('tipo',''),
            et['dados'].get('resumo',''),
            str(int(et['dados'].get('tempo',0)))
        ])
    col_etapas = [150, 270, 80]

    # Receita
    if com_custo:
        headers = ['Produto','Sequência','Preço (R$)','Quantidade','Unidade','R$/kg']
        col_rec  = [120,60,60,60,60,80]
    else:
        headers = ['Produto','Sequência','Quantidade','Unidade']
        col_rec  = [150,80,80,120]

    data_rec = [headers]
    for r in receita:
        if com_custo:
            data_rec.append([
                r.get('produto',''),
                r.get('sequencia',''),
                f"{r.get('preco',0):.2f}",
                str(r.get('quantidade',0)),
                r.get('percent',''),
                f"{r.get('rskg',0):.3f}"
            ])
        else:
            data_rec.append([
                r.get('produto',''),
                r.get('sequencia',''),
                str(r.get('quantidade',0)),
                r.get('percent','')
            ])

    # Insumos (água como no frontend)
    data_ins = [['Insumo','Preço (R$)','Quantidade','Unidade','L/kg']]
    for ins in insumos:
        data_ins.append([
            ins.get('produto',''),
            f"{ins.get('preco',0):.2f}",
            f"{ins.get('quantidade',0):.2f}",
            ins.get('unidade',''),
            ""
        ])
    data_ins.append([
        'Água', "0.00", f"{agua_litros:.2f}", 'Litros', f"{agua_lkg:.1f}"
    ])
    col_ins = [120, 60, 80, 60, 60]

    # --- Página 1: descrição das etapas ---
    draw_logo()
    y_cursor = letter[1] - 60

    # Título centralizado
    c.setFont('Helvetica-Bold', 14)
    c.drawCentredString(letter[0] / 2, y_cursor, titulo)
    y_cursor -= 20

    # Só as etapas
    y_cursor = ajustar_tabela_para_uma_pagina(data_etapas, col_etapas, c, y_cursor, 80)

    # Finaliza página 1
    c.showPage()

    # --- Página 2: gráfico + receita ---
    from io import BytesIO
    from reportlab.lib.pagesizes import landscape

    # define página em paisagem
    c.setPageSize(landscape(letter))
    page_w, page_h = landscape(letter)

    # --- Gera o buffer do gráfico ---
    resp = grafico_png()
    resp.direct_passthrough = False
    img_data  = resp.get_data()
    chart_buf = BytesIO(img_data)

    # Ajusta tamanho do gráfico para ocupar 60% da altura da página
    chart_w = page_w - 100
    chart_h = page_h * 0.6
    x       = (page_w - chart_w) / 2
    y       = page_h - chart_h - 30  # margem superior

    # Desenha título e gráfico
    c.setFont('Helvetica-Bold', 16)
    c.drawCentredString(page_w / 2, page_h - 30, titulo)
    c.drawImage(
        ImageReader(chart_buf),
        x, y,
        width=chart_w,
        height=chart_h,
        mask='auto'
    )

    # Receita abaixo do gráfico
    y_rec = y - 20
    c.setFont('Helvetica-Bold', 18)
    c.drawString(40, y_rec, 'Receita')
    y_rec -= 18

    # Colunas igualmente largas (preenchendo toda a largura útil)
    n_cols    = len(data_rec[0])
    available = page_w - 80   # marge 40pt cada lado
    col_rec   = [available / n_cols] * n_cols

    ajustar_tabela_para_uma_pagina(
        data_rec,
        col_rec,
        c,
        y_rec,
        margem_inferior=10  # aproxima a última linha do rodapé
    )

    # Finaliza PDF
    c.showPage()
    c.save()
    buf.seek(0)
    return send_file(
        buf,
        mimetype='application/pdf',
        download_name=filename,
        as_attachment=False
    )



@app.route('/custo')
def custo():
    receita = session.get('receita', [])
    tempo = session.get('tempo_processo', 0)
    return render_template('custo.html', receita_json=receita, tempo=tempo)

@app.route('/atualizar_receita_custo', methods=['POST'])
def atualizar_receita_custo():
    data = request.get_json()
    session['receita_custo'] = data.get('receita', [])
    session['tempo_processo'] = data.get('tempo', 0)
    session['relacao_banho'] = data.get('relacao_banho', 8)
    session.modified = True
    return jsonify(success=True)


@app.route('/imprimir_pdf_custo')
def imprimir_pdf_custo():
    import io
    from flask import send_file, session
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import Table, TableStyle
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas as pdf_canvas
    from reportlab.lib.utils import ImageReader

    LOGO_PATH = 'static/logo_hanier.png'  # Atualize para seu caminho real

    receita = session.get('receita_custo', [])
    tempo = session.get('tempo_processo', 0)
    relacao_banho = session.get('relacao_banho', 8)

    horas = tempo // 60
    minutos = tempo % 60

    buf = io.BytesIO()
    c = pdf_canvas.Canvas(buf, pagesize=letter)
    c.setTitle("Cálculo de Custo")

    # Logo
    try:
        logo = ImageReader(LOGO_PATH)
        c.drawImage(logo, 25, letter[1] - 75, width=115, height=38, mask='auto')
    except Exception:
        pass

    c.setFont('Helvetica-Bold', 22)
    c.drawCentredString(letter[0]/2, letter[1] - 40, "Cálculo de Custo")

    c.setFont('Helvetica', 15)
    c.drawString(80, letter[1] - 95, f"Tempo do Processo: {horas:02d}:{minutos:02d} ")
    c.drawString(350, letter[1] - 95, f"Relação de Banho 1: {relacao_banho}")

    # Tabela receita
    table_data = [['Produto', 'Sequência', 'Preço (R$)', 'Quantidade', 'Unidade', 'R$/kg']]
    total = 0
    for r in receita:
        table_data.append([
            r.get('produto',''),
            r.get('sequencia',''),
            f"{float(r.get('preco',0)):.2f}",
            str(r.get('quantidade','')),
            r.get('percent',''),
            f"{float(r.get('rskg',0)):.3f}"
        ])
        total += float(r.get('rskg',0) or 0)
    # Rodapé custo total
    table_data.append(['','','','','Custo total:', f'R$ {total:.2f}'])

    col_widths = [100, 80, 90, 80, 80, 80]

    table = Table(table_data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#dce6f2')),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 12),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#f4f8fc')),
        ('FONTNAME', (0,-1), (4,-1), 'Helvetica-Bold'),
        ('FONTNAME', (5,-1), (5,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (5,-1), (5,-1), 13),
        ('ALIGN', (5,-1), (5,-1), 'RIGHT'),
    ]))
    y_start = letter[1] - 150
    w, h = table.wrap(0, 0)
    table.drawOn(c, (letter[0] - sum(col_widths))/2, y_start - h)

    c.showPage()
    c.save()
    buf.seek(0)

    return send_file(
        buf,
        mimetype='application/pdf',
        download_name='custo.pdf',
        as_attachment=False
    )

@app.route('/imprimir_pdf', methods=['POST'])
def imprimir_pdf():
    data      = request.get_json()
    titulo = data.get('titulo', 'Relatório de Tingimento')  # usa título enviado, ou um padrão
    com_custo = data.get('com_custo', False)
    receita   = session.get('receita', [])  # <-- sempre pega só da sessão!
    etapas = session.get('etapas', [])
    carga = session.get('relacao_banho_carga', 300)
    relacao = session.get('relacao_banho', 8)
    insumos = calcular_insumos(etapas, carga, relacao)
    session['insumos'] = insumos
    session.modified = True

    buf = io.BytesIO()
    c   = pdf_canvas.Canvas(buf, pagesize=letter)
    # Faz com que o PDF interno carregue o título
    c.setTitle(titulo)

    # ——— Logo e Título no topo ———
    page_width, page_height = letter

    try:
        logo = ImageReader(LOGO_PATH)
        # define tamanho do logo
        logo_width  = 100
        logo_height = 40
        margin      = 5

        # calcula canto superior-direito
        page_width, page_height = letter
        x = page_width  - logo_width  - margin
        y = page_height - logo_height - margin

        # desenha no Canvas
        c.drawImage(
            logo,
            x, y,
            width=logo_width,
            height=logo_height,
            mask='auto'
        )
    except Exception as e:
        # só para debug
        print("Erro ao carregar logo:", e)



    # ——— Página 1: gráfico + autoajuste de tabela ———
    resp = grafico_png()
    resp.direct_passthrough = False
    png_bytes  = resp.get_data()
    chart_buf  = io.BytesIO(png_bytes)

    # --- BLOCO DE QUEBRA DE PÁGINA DAS ETAPAS ---
    etapas = session.get('etapas', [])
    data_table = [['Tipo de Etapa', 'Resumo', 'Tempo (min)']]
    for et in etapas:
        data_table.append([
            et.get('tipo', ''),
            et['dados'].get('resumo', ''),
            str(int(et['dados'].get('tempo', 0)))
        ])

    col_widths = [150, 270, 80]
    table = Table(data_table, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#dce6f2')),
        ('TEXTCOLOR',   (0,0), (-1,0), colors.black),
        ('ALIGN',       (0,0), (-1,-1), 'CENTER'),
        ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
        ('GRID',        (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTNAME',    (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME',    (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE',    (0,0), (-1,-1), 9),
        ('TOPPADDING', (0,0), (-1,-1), 1),              # padding topo menor
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),           # padding base menor
        ('LEFTPADDING', (1,1), (1,-1), 2),
        ('RIGHTPADDING',(1,1), (1,-1), 2),
    ]))

    w, h = table.wrapOn(c, 0, 0)
    chart_height = 200
    logo_height = 40
    gap = 10
    chart_y = page_height - logo_height - gap - chart_height
    table_top = chart_y - gap
    y_tabela = table_top - h

    if y_tabela < 60:
        # Precisa quebrar para outra página
        linhas_cabecalho = 1
        altura_disponivel = table_top - 60
        altura_linha = h / (len(data_table)) if len(data_table) > 1 else 15
        linhas_max = int(altura_disponivel // altura_linha)
        if linhas_max < linhas_cabecalho + 1:
            linhas_max = linhas_cabecalho + 1

        primeira_parte = data_table[:linhas_max]
        segunda_parte = data_table[linhas_max:]

        c.drawImage(
            ImageReader(chart_buf),
            x=50, y=chart_y, width=500, height=chart_height
        )
        table1 = Table(primeira_parte, colWidths=col_widths)
        table1.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#dce6f2')),
            ('TEXTCOLOR',   (0,0), (-1,0), colors.black),
            ('ALIGN',       (0,0), (-1,-1), 'CENTER'),
            ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
            ('GRID',        (0,0), (-1,-1), 0.5, colors.grey),
            ('FONTNAME',    (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTNAME',    (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE',    (0,0), (-1,-1), 9),
            ('TOPPADDING', (0,0), (-1,-1), 1),              # padding topo menor
            ('BOTTOMPADDING', (0,0), (-1,-1), 1),           # padding base menor
            ('LEFTPADDING', (1,1), (1,-1), 2),
            ('RIGHTPADDING',(1,1), (1,-1), 2),
        ]))
        w1, h1 = table1.wrapOn(c, 0, 0)
        table1.drawOn(c, 50, table_top - h1)

        # Tempo total só na última página das etapas
        if not segunda_parte:
            total_min = sum(et['dados'].get('tempo',0) for et in etapas)
            horas, minutos = divmod(int(total_min), 60)
            c.setFont('Helvetica', 11)
            texto = f"Tempo total: {horas}:{minutos:02d}"
            c.drawString(50, table_top - h1 - 15, texto)
            c.showPage()

        if segunda_parte:
            c.showPage()  # só agora, ao entrar na segunda parte!
            table2 = Table([data_table[0]] + segunda_parte, colWidths=col_widths)
            table2.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#dce6f2')),
                ('TEXTCOLOR',   (0,0), (-1,0), colors.black),
                ('ALIGN',       (0,0), (-1,-1), 'CENTER'),
                ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
                ('GRID',        (0,0), (-1,-1), 0.5, colors.grey),
                ('FONTNAME',    (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTNAME',    (0,1), (-1,-1), 'Helvetica'),
                ('FONTSIZE',    (0,0), (-1,-1), 9),
                ('LEFTPADDING', (1,1), (1,-1), 4),
                ('RIGHTPADDING',(1,1), (1,-1), 4),
            ]))
            w2, h2 = table2.wrapOn(c, 0, 0)
            table2.drawOn(c, 50, page_height - 60 - h2)

            total_min = sum(et['dados'].get('tempo',0) for et in etapas)
            horas, minutos = divmod(int(total_min), 60)
            c.setFont('Helvetica', 11)
            texto = f"Tempo total: {horas}:{minutos:02d}"
            c.drawString(50, page_height - 60 - h2 - 15, texto)
            c.showPage()
    else:
        # Cabe tudo, desenha tudo na primeira página
        c.drawImage(
            ImageReader(chart_buf),
            x=50, y=chart_y, width=500, height=chart_height
        )
        table.drawOn(c, 50, table_top - h)
        total_min = sum(et['dados'].get('tempo',0) for et in etapas)
        horas, minutos = divmod(int(total_min), 60)
        c.setFont('Helvetica', 11)
        texto = f"Tempo total: {horas}:{minutos:02d}"
        c.drawString(50, table_top - h - 15, texto)
        c.showPage()    # --- FIM DO BLOCO DE QUEBRA DE PÁGINA DAS ETAPAS ---

    # ——— Página 2: receita ———
    c.setFont('Helvetica-Bold', 14)
    c.drawString(50, 800, 'Receita')

    # Relação de banho (opcional)
    rel = session.get('relacao_banho')
    if rel:
        c.setFont('Helvetica', 11)
        c.drawString(350, 800, f'Relação de banho: 1:{rel}')

    # Define cabeçalho e larguras conforme com_custo
    if com_custo:
        headers = ['Produto','Sequência','Preço (R$)','Quantidade','Unidade','R$/kg']
        col_widths = [120, 60, 60, 60, 60, 80]
    else:
        headers = ['Produto','Sequência','Quantidade','Unidade']
        col_widths = [150, 80, 80, 120]

    data_rec = [headers]
    for r in receita:
        if com_custo:
            data_rec.append([
                r.get('produto',''),
                r.get('sequencia',''),
                f"{r.get('preco',0):.2f}",
                str(r.get('quantidade',0)),
                r.get('percent',''),
                f"{r.get('rskg',0):.3f}"
            ])
        else:
            data_rec.append([
                r.get('produto',''),
                r.get('sequencia',''),
                str(r.get('quantidade',0)),
                r.get('percent','')
            ])

    table_rec = Table(data_rec, colWidths=col_widths)
    table_rec.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#dce6f2')),
        ('TEXTCOLOR',   (0,0), (-1,0), colors.black),
        ('ALIGN',       (0,0), (-1,-1), 'CENTER'),
        ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
        ('GRID',        (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTNAME',    (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME',    (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE',    (0,0), (-1,-1), 9),
        ('LEFTPADDING', (0,1), (-1,-1), 4),
        ('RIGHTPADDING',(0,1), (-1,-1), 4),
    ]))

    # Desenha a tabela começando em y=780
    w_rec, h_rec = table_rec.wrapOn(c, 0, 0)
    table_rec.drawOn(c, 50, 780 - h_rec)

    # ——— Custo total da receita ———
    total_custo = sum(r.get('rskg', 0) for r in receita)
    c.setFont('Helvetica-Bold', 11)
    c.drawString(50, (780 - h_rec) - 15,
                 f"Custo total da receita: R$ {total_custo:.2f}")

    # ——— Tabela de Insumos ———
    insumos = session.get('insumos', [])
    if insumos:
        data_ins = [['Insumo','Preço (R$)','Quantidade','Unidade','R$/kg']]
        for ins in insumos:
            data_ins.append([
                ins.get('produto',''),
                f"{ins.get('preco',0):.2f}",
                f"{ins.get('quantidade',0):.2f}",
                ins.get('unidade',''),
                f"{ins.get('rskg',0):.3f}"
            ])
        col_widths = [120, 60, 80, 60, 60]
        table_ins = Table(data_ins, colWidths=col_widths)
        table_ins.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#dce6f2')),
            ('TEXTCOLOR',   (0,0), (-1,0), colors.black),
            ('ALIGN',       (0,0), (-1,-1), 'CENTER'),
            ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
            ('GRID',        (0,0), (-1,-1), 0.5, colors.grey),
            ('FONTNAME',    (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',    (0,0), (-1,-1), 9),
        ]))
        w_ins, h_ins = table_ins.wrapOn(c, 0, 0)
        y = 780 - h_rec - 25 - h_ins
        table_ins.drawOn(c, 50, y)

        # ——— Tabela de Água ———
        etapas = session.get('etapas', [])
        consumo = 0
        for et in etapas:
            if et['tipo'] in ('Encher Máquina','Transbordo'):
                m = re.search(r'1:(\d+)', et['dados'].get('resumo',''))
                if m:
                    consumo += int(m.group(1))
        carga = session.get('relacao_banho_carga', 300)
        agua_qtd = consumo * carga

        data_agua = [['Insumo','Preço (R$)','Quantidade','Unidade','L/kg'],
                     ['Água','0.00', f"{agua_qtd:.2f}", 'Litros', str(consumo)]]
        table_agua = Table(data_agua, colWidths=[120, 60, 80, 60, 60])
        table_agua.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dce6f2')),
            ('GRID',(0,0),(-1,-1),0.5,colors.grey),
            ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ]))
        w_agua, h_agua = table_agua.wrapOn(c, 0, 0)
        table_agua.drawOn(c, 50, y - h_agua - 10)

    # Finaliza PDF
    c.save()
    buf.seek(0)
    return send_file(
        buf,
        mimetype='application/pdf',
        download_name='processo.pdf'
    )