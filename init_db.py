from pathlib import Path

from dotenv import load_dotenv

from database import conectar

load_dotenv()


def main():
    schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
    with conectar() as conn:
        conn.execute(schema)
    print("Esquema do GestãoMed aplicado com sucesso.")


if __name__ == "__main__":
    main()
