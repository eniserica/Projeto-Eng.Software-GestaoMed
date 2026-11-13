# 🏥 GestãoMed – Sistema de Gestão e Otimização de Consultas Médicas

## Sobre o projeto

O **GestãoMed** é um sistema web desenvolvido com o objetivo de facilitar o gerenciamento de consultas médicas, centralizando informações de pacientes, profissionais da saúde e agendamentos em uma única plataforma.

O sistema busca tornar a administração das consultas mais organizada, prática e eficiente, facilitando o acesso às informações e melhorando a experiência dos pacientes e profissionais de saúde.

## Problema que o software resolve

O projeto busca solucionar problemas comuns na administração de consultas médicas, como:

- Agendamentos desorganizados;
- Horários ociosos;
- Longas filas de espera;
- Cancelamentos e faltas de pacientes;
- Sobrecarga causada pelo controle manual das consultas.

Com a centralização das informações, o sistema pretende facilitar o gerenciamento das agendas, reduzir falhas nos agendamentos e otimizar o atendimento.

## Integrantes da equipe

**Grupo 4**
- Daniel Luis Corato Costa de França
- Érica Barbosa Silveira 
- Jhony Rodrigues Marques 
- Kaylan Alexandre da Silva 
- Luiz Henri Morais Silva 

## Tecnologias utilizadas

As tecnologias utilizadas no desenvolvimento do projeto são:

- **Python:** linguagem de programação utilizada no desenvolvimento do sistema.
- **Flask:** framework utilizado para desenvolver a aplicação web.
- **HTML5:** estruturação das páginas.
- **CSS3:** estilização e organização visual da interface.
- **MySQL:** banco de dados para armazenamento das informações.
- **PostgreSQL:** sistema de gerenciamento de banco de dados relacional utilizado no projeto.
- **Git e GitHub:** controle de versão e colaboração entre os integrantes da equipe.

## Principais funcionalidades

O sistema GestãoMed tem como principais funcionalidades:

- **Login e acesso:** autenticação dos usuários(pacientes, médicos e administradores) no sistema.
- **Gerenciamento de pacientes:** acesso às informações dos pacientes.
- **Agendamento de consultas:** cadastro e organização dos horários.
- **Cancelamento e reagendamento:** possibilidade de alterar consultas.
- **Visualização de agenda:** acompanhamento dos horários dos profissionais.
- **Confirmação de consultas:** controle das consultas agendadas.
- **Fila de espera:** organização de pacientes quando não houver horários disponíveis.
- **Controle de consultas:** acompanhamento de consultas realizadas, canceladas e faltas.


## Instalação e execução

Para executar o projeto localmente, siga as instruções:

### 1. Pré-requisitos

- Python instalado;
- MySQL Server instalado;
- MySQL Workbench (opcional, para gerenciamento do banco de dados);
- Visual Studio Code ou outro editor de código.

### 2. Clone o repositório

```bash
git clone LINK_DO_REPOSITORIO
```

### 3. Entre na pasta do projeto

```bash
cd nome-da-pasta
```

### 4. Crie um ambiente virtual

```bash
python -m venv venv
```

### 5. Ative o ambiente virtual

No Windows:

```bash
venv\Scripts\activate
```

### 6. Instale as dependências

```bash
pip install flask
```

Instale também as demais dependências utilizadas pelo projeto, conforme a configuração do banco de dados.

### 7. Configure o banco de dados

Inicie o MySQL Server e configure as credenciais de acesso ao banco de dados de acordo com as configurações utilizadas na aplicação.

### 8. Execute o sistema

```bash
python app.py
```

Após iniciar o servidor, acesse pelo navegador:

```text
http://127.0.0.1:5000
```

## Imagens do sistema

- Para conferir um pouco do nosso site pode verificar as imagens na pasta chamada **images-readme** 


## Gerenciamento e planejamento do projeto

O desenvolvimento do GestãoMed é organizado em etapas, priorizando inicialmente as funcionalidades essenciais e posteriormente os recursos complementares.

**Ferramenta de gerenciamento:**(https://app.notion.com/p/402ad4c6bd6380d0b08dd42d7a45dd85?v=402ad4c6bd6380f08d89000c5d1768a4&source=copy_link)

**Repositório do projeto:** (https://github.com/eniserica/Projeto-Eng.Software-GestaoMed.git)

## Considerações finais

O GestãoMed tem como finalidade contribuir para a organização e otimização dos serviços de agendamento médico, oferecendo uma solução tecnológica acessível e prática.

Por meio da centralização das informações e do gerenciamento das consultas, o projeto busca facilitar o trabalho dos profissionais de saúde e proporcionar uma experiência mais eficiente aos pacientes.

---

**GestãoMed – Tecnologia a favor de um atendimento mais organizado!** 

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
