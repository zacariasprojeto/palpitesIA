from flask import Flask, render_template, request, redirect, session, jsonify
from supabase import create_client, Client
from datetime import datetime, timedelta
import os
import random
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "chave_default")

# ==============================
# SUPABASE CONNECTION
# ==============================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE = os.getenv("SUPABASE_SERVICE")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE)


# ==============================
# EMAIL CONFIG (BREVO SMTP)
# ==============================

SMTP_SERVER = "smtp-relay.brevo.com"
SMTP_PORT = 587
SMTP_USER = os.getenv("EMAIL_SENDER")        # seu email do Brevo
SMTP_PASS = os.getenv("EMAIL_PASSWORD")      # senha SMTP do Brevo


# ==============================
# FUNÇÕES
# ==============================

def gerar_codigo():
    return random.randint(100000, 999999)


def enviar_email(destino, codigo):
    """Envia código de confirmação pelo SMTP da Brevo"""

    msg = MIMEText(f"Seu código de confirmação é: {codigo}")
    msg["Subject"] = "Código de Confirmação - Lanzaca IA"
    msg["From"] = SMTP_USER
    msg["To"] = destino

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, destino, msg.as_string())

        print("Código enviado para o email:", destino)

    except Exception as e:
        print("ERRO AO ENVIAR EMAIL:", e)


# ==============================
# ROTAS
# ==============================

@app.route("/")
def index():
    return render_template("index.html")

# LOGIN
@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    senha = request.form.get("senha")

    dados = supabase.table("users").select("*").eq("email", email).eq("senha", senha).execute()

    if len(dados.data) == 0:
        return render_template("index.html", erro="Erro no login.")

    user = dados.data[0]
    session["email"] = user["email"]
    session["nome"] = user["nome"]

    return redirect("/dashboard")


# CADASTRO
@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "GET":
        return render_template("cadastro.html")

    nome = request.form.get("nome")
    celular = request.form.get("celular")
    email = request.form.get("email")
    senha = request.form.get("senha")

    # verifica se já existe em users
    existe = supabase.table("users").select("*").eq("email", email).execute()
    if len(existe.data) > 0:
        return render_template("cadastro.html", erro="Email já cadastrado.")

    # remove pendente antigo
    supabase.table("pending_users").delete().eq("email", email).execute()

    # salva pendente
    supabase.table("pending_users").insert({
        "nome": nome,
        "celular": celular,
        "email": email,
        "senha": senha
    }).execute()

    # gerando código
    codigo = gerar_codigo()

    # limpando códigos antigos do email
    supabase.table("confirm_codes").delete().eq("email", email).execute()

    # registrando novo código
    supabase.table("confirm_codes").insert({
        "email": email,
        "codigo": str(codigo)
    }).execute()

    # enviando email SMTP
    enviar_email(email, codigo)

    return redirect(f"/confirmar?email={email}")


# TELA CONFIRMAR
@app.route("/confirmar")
def confirmar_tela():
    email = request.args.get("email")
    return render_template("confirmar.html", email=email)


# VALIDAÇÃO DO CÓDIGO
@app.route("/api/confirmar", methods=["POST"])
def api_confirmar():
    dados = request.get_json()
    codigo = dados.get("codigo")
    email = dados.get("email")

    if not codigo or not email:
        return jsonify({"message": "Dados incompletos"}), 400

    verifica = supabase.table("confirm_codes").select("*").eq("email", email).eq("codigo", codigo).execute()

    if len(verifica.data) == 0:
        return jsonify({"message": "Código incorreto"}), 401

    pendente = supabase.table("pending_users").select("*").eq("email", email).execute()
    if len(pendente.data) == 0:
        return jsonify({"message": "Cadastro pendente não encontrado"}), 404

    usuario = pendente.data[0]

    # cria usuário definitivo
    supabase.table("users").insert({
        "nome": usuario["nome"],
        "celular": usuario["celular"],
        "email": usuario["email"],
        "senha": usuario["senha"],
        "is_admin": False
    }).execute()

    # remove pendente e código
    supabase.table("pending_users").delete().eq("email", email).execute()
    supabase.table("confirm_codes").delete().eq("email", email).execute()

    return jsonify({"message": "Confirmado com sucesso"}), 200


# DASHBOARD
@app.route("/dashboard")
def dashboard():
    if "email" not in session:
        return redirect("/")
    return render_template("dashboard.html", nome=session["nome"])


# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# RUN RENDER
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
