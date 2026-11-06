from flask import Flask, render_template, send_from_directory

app = Flask(__name__)

@app.route("/images/<path:filename>")
def imagens(filename):
    return send_from_directory(f"{app.root_path}/images", filename)

@app.route("/")
def inicio():
    return render_template(
        "index.html",
        titulo="GestãoMed",
        mensagem="Tecnologia que otimiza sua rotina médica."
    )

@app.route("/login")
def login():
    return render_template(
        "acessar.html",
        titulo="Acessar o sistema"
    )

@app.route("/paciente")
def paciente():
    return render_template(
        "paciente.html",
        titulo="Área do paciente",
        nome_paciente="Paciente"
    )
@app.route("/medico")
def medico():
    return render_template(
        "medico.html",
        titulo="Área do médico",
        nome_medico="Dr. João Silva",
        crm_medico="12345"
    )

@app.route("/exames")
def exames():
    return render_template("exames.html")

@app.route("/prontuario")
def prontuario():
    return render_template("prontuario.html")

@app.route("/administrador")
def administrador():
    return render_template("administrador.html")

@app.route("/usuarios")
def usuarios():
    return render_template("usuarios.html")


@app.route("/relatorios")
def relatorios():
    return render_template("relatorios.html")

if __name__ == "__main__":
    app.run(debug=True)