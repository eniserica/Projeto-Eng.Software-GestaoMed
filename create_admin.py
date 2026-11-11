from getpass import getpass

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

from database import conectar

load_dotenv()


def main():
    nome = input("Nome do administrador: ").strip()
    email = input("E-mail do administrador: ").strip()
    senha = getpass("Senha (mínimo 8 caracteres): ")
    if not nome or not email or len(senha) < 8:
        raise SystemExit("Nome e e-mail são obrigatórios; a senha deve ter ao menos 8 caracteres.")

    with conectar() as conn:
        conn.execute(
            """
            INSERT INTO usuarios (nome, email, senha_hash, tipo)
            VALUES (%s, %s, %s, 'administrador')
            """,
            (nome, email, generate_password_hash(senha)),
        )

    print("Administrador cadastrado com sucesso.")


if __name__ == "__main__":
    main()
