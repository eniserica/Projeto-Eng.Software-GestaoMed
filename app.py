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

if __name__ == "__main__":
    app.run(debug=True)