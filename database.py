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
