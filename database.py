import os

import psycopg


class DatabaseConfigurationError(Exception):
    pass


def conectar():
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return psycopg.connect(database_url)

    required = ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD")
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise DatabaseConfigurationError(
            "Configuração do PostgreSQL ausente: " + ", ".join(missing)
        )

    return psycopg.connect(
        host=os.environ["DB_HOST"],
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        port=os.getenv("DB_PORT", "5432"),
    )


def register_user(nome, email, senha_hash, tipo):
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO usuarios (nome, email, senha_hash, tipo)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (nome, email, senha_hash, tipo),
            )
            usuario_id = cursor.fetchone()[0]

            if tipo == "paciente":
                cursor.execute(
                    "INSERT INTO pacientes (usuario_id) VALUES (%s)",
                    (usuario_id,),
                )
            elif tipo == "medico":
                cursor.execute(
                    "INSERT INTO medicos (usuario_id) VALUES (%s)",
                    (usuario_id,),
                )

def listar_usuarios():
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, nome, email, tipo, ativo
                FROM usuarios
                ORDER BY nome
                """
            )
            return cursor.fetchall()

def listar_pacientes_administrador():
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT u.id, u.nome, u.email, u.ativo
                FROM pacientes p
                JOIN usuarios u ON u.id = p.usuario_id
                ORDER BY u.nome
                """
            )
            return cursor.fetchall()

def listar_consultas_administrador():
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    c.id,
                    c.inicio AT TIME ZONE 'America/Maceio',
                    paciente_usuario.nome,
                    medico_usuario.nome,
                    c.status
                FROM consultas c
                JOIN pacientes p ON p.id = c.paciente_id
                JOIN usuarios paciente_usuario ON paciente_usuario.id = p.usuario_id
                JOIN medicos m ON m.id = c.medico_id
                JOIN usuarios medico_usuario ON medico_usuario.id = m.usuario_id
                ORDER BY c.inicio DESC
                """
            )
            return cursor.fetchall()

def obter_resumo_administrador():
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    (
                        SELECT COUNT(*)
                        FROM pacientes p
                        JOIN usuarios u ON u.id = p.usuario_id
                        WHERE u.ativo = TRUE
                    ),
                    (
                        SELECT COUNT(*)
                        FROM consultas
                    ),
                    (
                        SELECT COUNT(*)
                        FROM medicos m
                        JOIN usuarios u ON u.id = m.usuario_id
                        WHERE u.ativo = TRUE
                    ),
                    (
                        SELECT COUNT(*)
                        FROM exames
                    )
                """
            )
            return cursor.fetchone()

def listar_consultas_por_mes_administrador():
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                WITH meses AS (
                    SELECT generate_series(
                        date_trunc(
                            'month',
                            NOW() AT TIME ZONE 'America/Maceio'
                        ) - interval '5 months',
                        date_trunc(
                            'month',
                            NOW() AT TIME ZONE 'America/Maceio'
                        ),
                        interval '1 month'
                    ) AS mes
                )
                SELECT
                    to_char(meses.mes, 'MM/YY'),
                    COUNT(c.id)
                FROM meses
                LEFT JOIN consultas c
                    ON date_trunc(
                        'month',
                        c.inicio AT TIME ZONE 'America/Maceio'
                    ) = meses.mes
                GROUP BY meses.mes
                ORDER BY meses.mes
                """
            )
            return cursor.fetchall()

def listar_consultas_por_especialidade_administrador():
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    COALESCE(
                        NULLIF(BTRIM(m.especialidade), ''),
                        'Não informada'
                    ),
                    COUNT(c.id)
                FROM consultas c
                JOIN medicos m ON m.id = c.medico_id
                GROUP BY 1
                ORDER BY COUNT(c.id) DESC, 1
                """
            )
            return cursor.fetchall()

def listar_medicos_ativos():
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT m.id, u.nome, COALESCE(m.especialidade, 'Especialidade não informada')
                FROM medicos m
                JOIN usuarios u ON u.id = m.usuario_id
                WHERE u.ativo = TRUE
                ORDER BY u.nome
                """
            )
            return cursor.fetchall()

def criar_consulta(usuario_id, medico_id, inicio):
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM pacientes WHERE usuario_id = %s",
                (usuario_id,),
            )
            paciente = cursor.fetchone()
            if paciente is None:
                return None, "Sua conta não está cadastrada como paciente."

            paciente_id = paciente[0]

            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM consultas
                    WHERE (medico_id = %s OR paciente_id = %s)
                      AND status IN ('agendada', 'confirmada')
                      AND inicio < %s::timestamptz + interval '30 minutes'
                      AND inicio + make_interval(mins => duracao_minutos)
                          > %s::timestamptz
                )
                """,
                (medico_id, paciente_id, inicio, inicio),
            )
            if cursor.fetchone()[0]:
                return None, "Esse horário já conflita com outra consulta."

            cursor.execute(
                """
                INSERT INTO consultas (paciente_id, medico_id, inicio)
                SELECT %s, m.id, %s
                FROM medicos m
                JOIN usuarios u ON u.id = m.usuario_id
                WHERE m.id = %s AND u.ativo = TRUE
                RETURNING id
                """,
                (paciente_id, inicio, medico_id),
            )
            consulta = cursor.fetchone()
            if consulta is None:
                return None, "O médico selecionado não está disponível."

            return consulta[0], None

def listar_consultas_paciente(usuario_id):
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    c.inicio AT TIME ZONE 'America/Maceio',
                    c.status,
                    c.duracao_minutos,
                    u.nome,
                    COALESCE(m.especialidade, 'Especialidade não informada')
                FROM consultas c
                JOIN pacientes p ON p.id = c.paciente_id
                JOIN medicos m ON m.id = c.medico_id
                JOIN usuarios u ON u.id = m.usuario_id
                WHERE p.usuario_id = %s
                ORDER BY c.inicio
                """,
                (usuario_id,),
            )
            return cursor.fetchall()

def listar_exames_paciente(usuario_id):
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    e.descricao,
                    e.solicitado_em AT TIME ZONE 'America/Maceio',
                    e.status,
                    e.resultado,
                    e.arquivo_url,
                    u.nome
                FROM exames e
                JOIN pacientes p ON p.id = e.paciente_id
                JOIN medicos m ON m.id = e.medico_id
                JOIN usuarios u ON u.id = m.usuario_id
                WHERE p.usuario_id = %s
                ORDER BY e.solicitado_em DESC
                """,
                (usuario_id,),
            )
            return cursor.fetchall()

def listar_consultas_medico(usuario_id):
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    c.id,
                    c.inicio AT TIME ZONE 'America/Maceio',
                    p_usuario.nome,
                    c.status
                FROM consultas c
                JOIN medicos m ON m.id = c.medico_id
                JOIN pacientes p ON p.id = c.paciente_id
                JOIN usuarios p_usuario ON p_usuario.id = p.usuario_id
                WHERE m.usuario_id = %s
                  AND c.status IN ('agendada', 'confirmada', 'concluida')
                ORDER BY c.inicio DESC
                """,
                (usuario_id,),
            )
            return cursor.fetchall()

def listar_agenda_medico(usuario_id):
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    c.id,
                    c.inicio AT TIME ZONE 'America/Maceio',
                    p_usuario.nome,
                    c.status
                FROM consultas c
                JOIN medicos m ON m.id = c.medico_id
                JOIN pacientes p ON p.id = c.paciente_id
                JOIN usuarios p_usuario ON p_usuario.id = p.usuario_id
                WHERE m.usuario_id = %s
                  AND (c.inicio AT TIME ZONE 'America/Maceio')::date =
                      (NOW() AT TIME ZONE 'America/Maceio')::date
                  AND c.status IN ('agendada', 'confirmada', 'concluida')
                ORDER BY c.inicio
                """,
                (usuario_id,),
            )
            return cursor.fetchall()

def listar_pacientes_medico(usuario_id):
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT DISTINCT p.id, u.nome, u.email
                FROM pacientes p
                JOIN usuarios u ON u.id = p.usuario_id
                JOIN consultas c ON c.paciente_id = p.id
                JOIN medicos m ON m.id = c.medico_id
                WHERE m.usuario_id = %s
                  AND c.status IN ('agendada', 'confirmada', 'concluida')
                  AND u.ativo = TRUE
                ORDER BY u.nome
                """,
                (usuario_id,),
            )
            return cursor.fetchall()

def obter_resumo_medico(usuario_id):
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    COUNT(DISTINCT c.id),
                    COUNT(DISTINCT c.paciente_id)
                        FILTER (
                            WHERE c.status IN (
                                'agendada',
                                'confirmada',
                                'concluida'
                            )
                        ),
                    COUNT(DISTINCT e.id),
                    COUNT(DISTINCT pr.id)
                FROM medicos m
                LEFT JOIN consultas c ON c.medico_id = m.id
                LEFT JOIN exames e ON e.medico_id = m.id
                LEFT JOIN prontuarios pr ON pr.consulta_id = c.id
                WHERE m.usuario_id = %s
                """,
                (usuario_id,),
            )
            return cursor.fetchone()


def criar_exame_medico(usuario_id, consulta_id, descricao):
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO exames (consulta_id, paciente_id, medico_id, descricao)
                SELECT c.id, c.paciente_id, m.id, %s
                FROM consultas c
                JOIN medicos m ON m.id = c.medico_id
                WHERE c.id = %s
                  AND m.usuario_id = %s
                RETURNING id
                """,
                (descricao, consulta_id, usuario_id),
            )
            exame = cursor.fetchone()
            return exame[0] if exame else None

def listar_consultas_sem_prontuario(usuario_id):
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    c.id,
                    c.inicio AT TIME ZONE 'America/Maceio',
                    p_usuario.nome
                FROM consultas c
                JOIN medicos m ON m.id = c.medico_id
                JOIN pacientes p ON p.id = c.paciente_id
                JOIN usuarios p_usuario ON p_usuario.id = p.usuario_id
                LEFT JOIN prontuarios pr ON pr.consulta_id = c.id
                WHERE m.usuario_id = %s
                  AND c.status IN ('agendada', 'confirmada', 'concluida')
                  AND pr.id IS NULL
                ORDER BY c.inicio DESC
                """,
                (usuario_id,),
            )
            return cursor.fetchall()

def listar_prontuarios_medico(usuario_id):
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    pr.id,
                    c.inicio AT TIME ZONE 'America/Maceio',
                    p_usuario.nome,
                    pr.diagnostico,
                    pr.tratamento,
                    pr.notas
                FROM prontuarios pr
                JOIN consultas c ON c.id = pr.consulta_id
                JOIN medicos m ON m.id = c.medico_id
                JOIN pacientes p ON p.id = c.paciente_id
                JOIN usuarios p_usuario ON p_usuario.id = p.usuario_id
                WHERE m.usuario_id = %s
                ORDER BY c.inicio DESC
                """,
                (usuario_id,),
            )
            return cursor.fetchall()


def criar_prontuario_medico(
    usuario_id,
    consulta_id,
    diagnostico,
    tratamento,
    notas,
):
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO prontuarios (
                    consulta_id,
                    diagnostico,
                    tratamento,
                    notas
                )
                SELECT c.id, %s, %s, %s
                FROM consultas c
                JOIN medicos m ON m.id = c.medico_id
                WHERE c.id = %s
                  AND m.usuario_id = %s
                RETURNING id
                """,
                (diagnostico, tratamento, notas, consulta_id, usuario_id),
            )
            prontuario = cursor.fetchone()
            return prontuario[0] if prontuario else None

def obter_perfil_paciente(usuario_id):
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT u.nome, u.email, p.cpf, p.telefone, p.data_nascimento
                FROM usuarios u
                JOIN pacientes p ON p.usuario_id = u.id
                WHERE u.id = %s
                """,
                (usuario_id,),
            )
            return cursor.fetchone()

def obter_perfil_medico(usuario_id):
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT u.nome, u.email, m.crm, m.especialidade
                FROM usuarios u
                JOIN medicos m ON m.usuario_id = u.id
                WHERE u.id = %s
                """,
                (usuario_id,),
            )
            return cursor.fetchone()


def atualizar_especialidade_medico(usuario_id, especialidade):
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE medicos
                SET especialidade = %s
                WHERE usuario_id = %s
                RETURNING id
                """,
                (especialidade, usuario_id),
            )
            medico = cursor.fetchone()
            return medico[0] if medico else None

def authenticate_user(email):
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, nome, tipo, senha_hash, ativo
                FROM usuarios
                WHERE lower(email) = lower(%s)
                """,
                (email,),
            )
            row = cursor.fetchone()

    if row is None:
        return None

    return {
        "id": row[0],
        "nome": row[1],
        "tipo": row[2],
        "senha_hash": row[3],
        "ativo": row[4],
    }
