import logging
import os
import secrets
from functools import wraps

import psycopg
from dotenv import load_dotenv
from flask import (
    Flask,
    abort,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from database import (
    DatabaseConfigurationError,
    authenticate_user,
    register_user,
)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY") or secrets.token_hex(32)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)
logger = logging.getLogger(__name__)

TIPOS_VALIDOS = {"paciente", "medico", "administrador"}
TIPOS_CADASTRO_PUBLICO = {"paciente", "medico"}


def perfil_obrigatorio(*perfis):
    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            perfil = session.get("tipo")
            if not session.get("usuario_id"):
                return redirect(url_for("login", tipo=perfis[0]))
            if perfil not in perfis:
                abort(403)
            return view(*args, **kwargs)

        return wrapped_view

    return decorator


@app.route("/images/<path:filename>")
def imagens(filename):
    return send_from_directory(os.path.join(app.root_path, "images"), filename)


@app.route("/")
def inicio():
    return render_template(
        "index.html",
        titulo="GestãoMed",
        mensagem="Tecnologia que otimiza sua rotina médica.",
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    tipo = request.values.get("tipo", "")
    if tipo not in TIPOS_VALIDOS:
        tipo = None

    mensagem = None
    status = 200
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        senha = request.form.get("senha", "")
        try:
            usuario = authenticate_user(email)
        except (psycopg.Error, DatabaseConfigurationError):
            logger.exception("Falha ao consultar usuário no PostgreSQL.")
            mensagem = "Não foi possível acessar o banco de dados. Tente novamente mais tarde."
            status = 503
        else:
            if (
                usuario
                and usuario["ativo"]
                and check_password_hash(usuario["senha_hash"], senha)
                and (tipo is None or usuario["tipo"] == tipo)
            ):
                session.clear()
                session["usuario_id"] = usuario["id"]
                session["tipo"] = usuario["tipo"]
                session["nome"] = usuario["nome"]
                destinos = {
                    "paciente": "paciente",
                    "medico": "medico",
                    "administrador": "administrador",
                }
                return redirect(url_for(destinos[usuario["tipo"]]))
            mensagem = "E-mail, senha ou perfil inválido."

    return render_template(
        "acessar.html",
        titulo="Acessar o sistema",
        tipo=tipo,
        mensagem=mensagem,
    ), status


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    tipo = request.values.get("tipo", "")
    if tipo not in TIPOS_VALIDOS:
        tipo = None

    mensagem = None
    status = 200
    if request.method == "POST":
        tipo = request.form.get("tipo", "")
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip()
        senha = request.form.get("senha", "")
        repeat_senha = request.form.get("repeat_senha", "")

        if tipo not in TIPOS_CADASTRO_PUBLICO:
            mensagem = "O perfil administrador só pode ser criado pela ferramenta create_admin.py."
        elif not nome or not email or len(senha) < 8:
            mensagem = "Preencha todos os campos e use uma senha com pelo menos 8 caracteres."
        elif senha != repeat_senha:
            mensagem = "As senhas precisam ser iguais."
        else:
            try:
                register_user(nome, email, generate_password_hash(senha), tipo)
            except psycopg.errors.UniqueViolation:
                mensagem = "Este e-mail já está cadastrado."
            except (psycopg.Error, DatabaseConfigurationError):
                logger.exception("Falha ao salvar cadastro no PostgreSQL.")
                mensagem = "Não foi possível salvar o cadastro. Tente novamente mais tarde."
                status = 503
            else:
                mensagem = "Cadastro realizado. Você já pode acessar sua conta."

    return render_template(
        "cadastro.html",
        titulo="Criar conta",
        tipo=tipo,
        mensagem=mensagem,
    ), status


@app.route("/paciente")
@perfil_obrigatorio("paciente")
def paciente():
    return render_template(
        "paciente.html",
        titulo="Área do paciente",
        nome_paciente=session.get("nome", "Paciente"),
    )


@app.route("/medico")
@perfil_obrigatorio("medico")
def medico():
    return render_template(
        "medico.html",
        titulo="Área do médico",
        nome_medico=session.get("nome", "Médico"),
        crm_medico="",
    )


@app.route("/exames")
@perfil_obrigatorio("paciente")
def exames():
    return render_template("exames.html")


@app.route("/prontuario")
@perfil_obrigatorio("medico", "administrador")
def prontuario():
    return render_template("prontuario.html")


@app.route("/administrador")
@perfil_obrigatorio("administrador")
def administrador():
    return render_template("administrador.html")


@app.route("/usuarios")
@perfil_obrigatorio("administrador")
def usuarios():
    return render_template("usuarios.html")


@app.route("/relatorios")
@perfil_obrigatorio("administrador")
def relatorios():
    return render_template("relatorios.html")


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG") == "1")
