# GestãoMed

## PostgreSQL

1. Crie um banco PostgreSQL chamado `gestaomed`.
2. Copie `.env.example` para `.env` e preencha as credenciais locais. Nunca envie o `.env` ao GitHub.
3. Instale as dependências e crie as tabelas:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   python init_db.py
   ```

4. Crie o primeiro administrador com `python create_admin.py`. Os cadastros públicos aceitam apenas pacientes e médicos.
5. Inicie o site com `python app.py`.

Também é possível configurar `DATABASE_URL` no lugar das variáveis `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` e `DB_PASSWORD`. Em produção, configure uma `SECRET_KEY` estável e secreta.

O esquema inclui usuários, pacientes, médicos, consultas, prontuários e exames. Nesta versão, os fluxos persistidos no site são o cadastro e a autenticação de contas; as páginas de consultas, prontuários e exames ainda não oferecem operações para gravar esses registros.
