import logging
import os
import secrets
from functools import wraps
import psycopg
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo

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
    criar_consulta,
    listar_medicos_ativos,
    listar_consultas_paciente,
    obter_perfil_paciente,
    listar_exames_paciente,
    listar_consultas_medico,
    criar_exame_medico,
    listar_agenda_medico,
    listar_consultas_sem_prontuario,
    criar_prontuario_medico,
    listar_prontuarios_medico,
    listar_pacientes_medico,
    obter_resumo_medico,
    listar_usuarios,
    listar_pacientes_administrador,
    listar_consultas_administrador,
    obter_resumo_administrador,
    listar_consultas_por_mes_administrador,
    listar_consultas_por_especialidade_administrador,
    obter_perfil_medico,
    atualizar_especialidade_medico,
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

@app.route("/perfil")
@perfil_obrigatorio("paciente")
def perfil_paciente():
    try:
        perfil = obter_perfil_paciente(session["usuario_id"])
    except (psycopg.Error, DatabaseConfigurationError):
        logger.exception("Falha ao carregar perfil do paciente.")
        return "Não foi possível carregar seu perfil.", 503

    if perfil is None:
        abort(404)

    return render_template(
        "perfil_paciente.html",
        titulo="Meu perfil",
        perfil=perfil,
    )

@app.route("/agendamentos", methods=["GET", "POST"])
@perfil_obrigatorio("paciente")
def agendamentos():
    mensagem = (
        "Consulta agendada com sucesso."
        if request.args.get("sucesso") == "1"
        else None
    )
    status = 200

    try:
        medicos = listar_medicos_ativos()
    except (psycopg.Error, DatabaseConfigurationError):
        logger.exception("Falha ao buscar médicos para agendamento.")
        return "Não foi possível carregar os médicos.", 503

    if request.method == "POST":
        try:
            medico_id = int(request.form.get("medico_id", ""))
            inicio = datetime.fromisoformat(request.form.get("inicio", ""))
        except ValueError:
            mensagem = "Selecione um médico e informe uma data e horário válidos."
        else:
            fuso = ZoneInfo("America/Maceio")
            if inicio.tzinfo is None:
                inicio = inicio.replace(tzinfo=fuso)

            if inicio <= datetime.now(fuso):
                mensagem = "Escolha uma data e horário futuros."
            elif not any(medico[0] == medico_id for medico in medicos):
                mensagem = "O médico selecionado não é válido."
            else:
                try:
                    consulta_id, mensagem = criar_consulta(
                        session["usuario_id"],
                        medico_id,
                        inicio,
                    )
                except (psycopg.Error, DatabaseConfigurationError):
                    logger.exception("Falha ao salvar o agendamento.")
                    mensagem = "Não foi possível salvar o agendamento."
                    status = 503
                else:
                    if consulta_id is not None:
                        return redirect(url_for("agendamentos", sucesso="1"))

    if not medicos and mensagem is None:
        mensagem = "Ainda não há médicos cadastrados."

    return render_template(
        "agendamentos.html",
        titulo="Agendar consulta",
        medicos=medicos,
        mensagem=mensagem,
    ), status


@app.route("/paciente")
@perfil_obrigatorio("paciente")
def paciente():
    erro_consultas = None

    try:
        consultas = listar_consultas_paciente(session["usuario_id"])
    except (psycopg.Error, DatabaseConfigurationError):
        logger.exception("Falha ao buscar consultas do paciente.")
        consultas = []
        erro_consultas = "Não foi possível carregar suas consultas."
    
    agora = datetime.now(ZoneInfo("America/Maceio")).replace(tzinfo=None)
    proximas = [
        consulta
        for consulta in consultas
        if consulta[0] >= agora
        and consulta[1] in ("agendada", "confirmada")
    ]

    return render_template(
        "paciente.html",
        titulo="Área do paciente",
        nome_paciente=session.get("nome", "Paciente"),
        consultas=consultas,
        proximas=proximas,
        erro_consultas=erro_consultas,
    )


@app.route("/medico")
@perfil_obrigatorio("medico")
def medico():
    try:
        usuario_id = session["usuario_id"]
        consultas_hoje = listar_agenda_medico(usuario_id)
        pacientes = listar_pacientes_medico(usuario_id)
        consultas_sem_prontuario = listar_consultas_sem_prontuario(usuario_id)
        erro_dados = None
    except (psycopg.Error, DatabaseConfigurationError):
        logger.exception("Falha ao carregar dados do médico.")
        consultas_hoje = []
        pacientes = []
        consultas_sem_prontuario = []
        erro_dados = "Não foi possível carregar os dados do painel."

    return render_template(
        "medico.html",
        titulo="Área do médico",
        nome_medico=session.get("nome", "Médico"),
        crm_medico="",
        consultas_hoje=consultas_hoje,
        pacientes=pacientes,
        consultas_sem_prontuario=consultas_sem_prontuario,
        erro_agenda=erro_dados,
        erro_dados=erro_dados,
    )

@app.route("/perfil-medico", methods=["GET", "POST"])
@perfil_obrigatorio("medico")
def perfil_medico():
    mensagem = (
        "Especialidade atualizada."
        if request.args.get("sucesso") == "1"
        else None
    )

    try:
        perfil = obter_perfil_medico(session["usuario_id"])
    except (psycopg.Error, DatabaseConfigurationError):
        logger.exception("Falha ao carregar o perfil do médico.")
        return "Não foi possível carregar seu perfil.", 503

    if perfil is None:
        abort(404)

    if request.method == "POST":
        especialidade = request.form.get("especialidade", "").strip()

        if not especialidade:
            mensagem = "Informe sua especialidade."
        elif len(especialidade) > 120:
            mensagem = "A especialidade deve ter no máximo 120 caracteres."
        else:
            try:
                medico_id = atualizar_especialidade_medico(
                    session["usuario_id"],
                    especialidade,
                )
            except (psycopg.Error, DatabaseConfigurationError):
                logger.exception("Falha ao atualizar a especialidade.")
                mensagem = "Não foi possível atualizar sua especialidade."
            else:
                if medico_id is not None:
                    return redirect(url_for("perfil_medico", sucesso="1"))
                abort(404)

    return render_template(
        "perfil_medico.html",
        titulo="Meu perfil",
        perfil=perfil,
        mensagem=mensagem,
    )

@app.route("/agenda-medico")
@perfil_obrigatorio("medico")
def agenda_medico():
    try:
        consultas_agenda = listar_consultas_medico(session["usuario_id"])
        erro_agenda = None
    except (psycopg.Error, DatabaseConfigurationError):
        logger.exception("Falha ao carregar a agenda completa do médico.")
        consultas_agenda = []
        erro_agenda = "Não foi possível carregar a agenda."

    return render_template(
        "agenda_medico.html",
        titulo="Agenda do médico",
        consultas=consultas_agenda,
        erro_agenda=erro_agenda,
    )

@app.route("/pacientes-medico")
@perfil_obrigatorio("medico")
def pacientes_medico():
    try:
        pacientes = listar_pacientes_medico(session["usuario_id"])
        erro_pacientes = None
    except (psycopg.Error, DatabaseConfigurationError):
        logger.exception("Falha ao carregar pacientes do médico.")
        pacientes = []
        erro_pacientes = "Não foi possível carregar os pacientes."

    return render_template(
        "pacientes_medico.html",
        titulo="Meus pacientes",
        pacientes=pacientes,
        erro_pacientes=erro_pacientes,
    )

@app.route("/solicitar-exame", methods=["GET", "POST"])
@perfil_obrigatorio("medico")
def solicitar_exame():
    mensagem = (
        "Exame solicitado com sucesso."
        if request.args.get("sucesso") == "1"
        else None
    )
    status = 200

    try:
        consultas_medico = listar_consultas_medico(session["usuario_id"])
    except (psycopg.Error, DatabaseConfigurationError):
        logger.exception("Falha ao buscar consultas do médico.")
        return "Não foi possível carregar as consultas.", 503

    if request.method == "POST":
        descricao = request.form.get("descricao", "").strip()

        try:
            consulta_id = int(request.form.get("consulta_id", ""))
        except ValueError:
            mensagem = "Selecione uma consulta válida."
        else:
            if not descricao:
                mensagem = "Informe a descrição do exame."
            elif len(descricao) > 300:
                mensagem = "A descrição deve ter no máximo 300 caracteres."
            else:
                try:
                    exame_id = criar_exame_medico(
                        session["usuario_id"],
                        consulta_id,
                        descricao,
                    )
                except (psycopg.Error, DatabaseConfigurationError):
                    logger.exception("Falha ao solicitar exame.")
                    mensagem = "Não foi possível solicitar o exame."
                    status = 503
                else:
                    if exame_id is not None:
                        return redirect(
                            url_for("solicitar_exame", sucesso="1")
                        )
                    mensagem = "A consulta selecionada não pertence a você."

    return render_template(
        "solicitar_exame.html",
        titulo="Solicitar exame",
        consultas=consultas_medico,
        mensagem=mensagem,
    ), status

@app.route("/exames")
@perfil_obrigatorio("paciente")
def exames():
    try:
        exames_paciente = listar_exames_paciente(session["usuario_id"])
        erro_exames = None
    except (psycopg.Error, DatabaseConfigurationError):
        logger.exception("Falha ao buscar exames do paciente.")
        exames_paciente = []
        erro_exames = "Não foi possível carregar seus exames."

    return render_template(
        "exames.html",
        exames=exames_paciente,
        erro_exames=erro_exames,
    )


@app.route("/prontuario", methods=["GET", "POST"])
@perfil_obrigatorio("medico")
def prontuario():
    mensagem = (
        "Prontuário salvo com sucesso."
        if request.args.get("sucesso") == "1"
        else None
    )

    try:
        consultas = listar_consultas_sem_prontuario(session["usuario_id"])
        prontuarios = listar_prontuarios_medico(session["usuario_id"])
    except (psycopg.Error, DatabaseConfigurationError):
        logger.exception("Falha ao carregar dados do prontuário.")
        return "Não foi possível carregar os prontuários.", 503

    if request.method == "POST":
        diagnostico = request.form.get("diagnostico", "").strip()
        tratamento = request.form.get("tratamento", "").strip()
        notas = request.form.get("notas", "").strip()

        try:
            consulta_id = int(request.form.get("consulta_id", ""))
        except ValueError:
            mensagem = "Selecione uma consulta válida."
        else:
            if not diagnostico:
                mensagem = "Informe o diagnóstico."
            else:
                try:
                    prontuario_id = criar_prontuario_medico(
                        session["usuario_id"],
                        consulta_id,
                        diagnostico,
                        tratamento or None,
                        notas or None,
                    )
                except psycopg.errors.UniqueViolation:
                    mensagem = "Essa consulta já possui um prontuário."
                except (psycopg.Error, DatabaseConfigurationError):
                    logger.exception("Falha ao salvar prontuário.")
                    mensagem = "Não foi possível salvar o prontuário."
                else:
                    if prontuario_id is not None:
                        return redirect(url_for("prontuario", sucesso="1"))
                    mensagem = "A consulta selecionada não pertence a você."

    return render_template(
        "prontuario.html",
        titulo="Prontuário",
        consultas=consultas,
        mensagem=mensagem,
        prontuarios=prontuarios
    )


@app.route("/administrador")
@perfil_obrigatorio("administrador")
def administrador():
    try:
        resumo = obter_resumo_administrador()
        consultas_por_mes = listar_consultas_por_mes_administrador()
        consultas_por_especialidade = (
            listar_consultas_por_especialidade_administrador()
        )
        erro_resumo = None
    except (psycopg.Error, DatabaseConfigurationError):
        logger.exception("Falha ao carregar o painel do administrador.")
        resumo = None
        consultas_por_mes = []
        consultas_por_especialidade = []
        erro_resumo = "Não foi possível carregar os indicadores."

    maior_quantidade = max(
        (linha[1] for linha in consultas_por_mes),
        default=0,
    )
    meses_grafico = [
        {
            "mes": mes,
            "quantidade": quantidade,
            "altura": quantidade * 100 / maior_quantidade
            if maior_quantidade
            else 0,
        }
        for mes, quantidade in consultas_por_mes
    ]

    cores = [
        "#123f70",
        "#e7cda3",
        "#79b8ed",
        "#a6d0f3",
        "#2e80c8",
        "#20a77b",
        "#7d6bc4",
    ]
    total_especialidades = sum(
        quantidade for _, quantidade in consultas_por_especialidade
    )
    especialidades_grafico = []
    fatias_pizza = []
    inicio_fatia = 0

    for indice, (nome, quantidade) in enumerate(consultas_por_especialidade):
        percentual = (
            quantidade * 100 / total_especialidades
            if total_especialidades
            else 0
        )
        fim_fatia = inicio_fatia + percentual
        cor = cores[indice % len(cores)]

        especialidades_grafico.append(
            {
                "nome": nome,
                "quantidade": quantidade,
                "percentual": round(percentual),
                "cor": cor,
            }
        )
        fatias_pizza.append(
            f"{cor} {inicio_fatia:.2f}% {fim_fatia:.2f}%"
        )
        inicio_fatia = fim_fatia

    donut_gradient = (
        f"conic-gradient({', '.join(fatias_pizza)})"
        if fatias_pizza
        else "conic-gradient(#dce8f2 0 100%)"
    )

    return render_template(
        "administrador.html",
        titulo="Área do administrador",
        nome_administrador=session.get("nome", "Administrador"),
        resumo=resumo,
        erro_resumo=erro_resumo,
        meses_grafico=meses_grafico,
        especialidades_grafico=especialidades_grafico,
        donut_gradient=donut_gradient,
    )

@app.route("/pacientes-administrador")
@perfil_obrigatorio("administrador")
def pacientes_administrador():
    try:
        pacientes = listar_pacientes_administrador()
        erro_pacientes = None
    except (psycopg.Error, DatabaseConfigurationError):
        logger.exception("Falha ao carregar pacientes para o administrador.")
        pacientes = []
        erro_pacientes = "Não foi possível carregar os pacientes."

    return render_template(
        "pacientes_administrador.html",
        titulo="Pacientes",
        pacientes=pacientes,
        erro_pacientes=erro_pacientes,
    )

@app.route("/agenda-administrador")
@perfil_obrigatorio("administrador")
def agenda_administrador():
    try:
        consultas = listar_consultas_administrador()
        erro_agenda = None
    except (psycopg.Error, DatabaseConfigurationError):
        logger.exception("Falha ao carregar a agenda do administrador.")
        consultas = []
        erro_agenda = "Não foi possível carregar as consultas."

    return render_template(
        "agenda_administrador.html",
        titulo="Agenda",
        consultas=consultas,
        erro_agenda=erro_agenda,
    )

@app.route("/usuarios", methods=["GET", "POST"])
@perfil_obrigatorio("administrador")
def usuarios():
    mensagem = (
        "Usuário cadastrado com sucesso."
        if request.args.get("sucesso") == "1"
        else None
    )

    try:
        usuarios_cadastrados = listar_usuarios()
    except (psycopg.Error, DatabaseConfigurationError):
        logger.exception("Falha ao carregar usuários.")
        return "Não foi possível carregar os usuários.", 503

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip()
        senha = request.form.get("senha", "")
        tipo = request.form.get("tipo", "")

        if not nome or not email or len(senha) < 8:
            mensagem = "Preencha nome e e-mail e use uma senha com pelo menos 8 caracteres."
        elif tipo not in TIPOS_VALIDOS:
            mensagem = "Selecione um tipo de usuário válido."
        else:
            try:
                register_user(
                    nome,
                    email,
                    generate_password_hash(senha),
                    tipo,
                )
            except psycopg.errors.UniqueViolation:
                mensagem = "Este e-mail já está cadastrado."
            except (psycopg.Error, DatabaseConfigurationError):
                logger.exception("Falha ao cadastrar usuário pelo administrador.")
                mensagem = "Não foi possível cadastrar o usuário."
            else:
                return redirect(url_for("usuarios", sucesso="1"))

    return render_template(
        "usuarios.html",
        titulo="Gestão de usuários",
        usuarios=usuarios_cadastrados,
        mensagem=mensagem,
    )


@app.route("/relatorios")
@perfil_obrigatorio("administrador")
def relatorios():
    try:
        resumo = obter_resumo_administrador()
        erro_relatorio = None
    except (psycopg.Error, DatabaseConfigurationError):
        logger.exception("Falha ao carregar relatórios do administrador.")
        resumo = None
        erro_relatorio = "Não foi possível carregar os dados do relatório."

    return render_template(
        "relatorios.html",
        titulo="Relatórios",
        resumo=resumo,
        erro_relatorio=erro_relatorio,
    )

@app.route("/relatorios-medico")
@perfil_obrigatorio("medico")
def relatorios_medico():
    try:
        resumo = obter_resumo_medico(session["usuario_id"])
        erro_relatorio = None
    except (psycopg.Error, DatabaseConfigurationError):
        logger.exception("Falha ao carregar o resumo do médico.")
        resumo = None
        erro_relatorio = "Não foi possível carregar o relatório."

    return render_template(
        "relatorios_medico.html",
        titulo="Relatórios do médico",
        resumo=resumo,
        erro_relatorio=erro_relatorio,
    )

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG") == "1")
