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
SUPABASE_SERVICE = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE:
    raise Exception("Erro: SUPABASE_URL ou SUPABASE_SERVICE_KEY não configuradas!")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE)

# ==============================
# EMAIL CONFIG (BREVO)
# ==============================

SMTP_SERVER = "smtp-relay.brevo.com"
SMTP_PORT = 587
SMTP_USER = os.getenv("EMAIL_SENDER")
SMTP_PASS = os.getenv("EMAIL_PASSWORD")


def gerar_codigo():
    return random.randint(100000, 999999)


def enviar_email(destino, codigo):
    msg = MIMEText(f"Seu código de confirmação é: {codigo}")
    msg["Subject"] = "Código de Confirmação - Lanzaca IA"
    msg["From"] = SMTP_USER
    msg["To"] = destino

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, destino, msg.as_string())

        print("Código enviado para:", destino)

    except Exception as e:
        print("ERRO AO ENVIAR EMAIL:", e)


# ROTAS -------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


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


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "GET":
        return render_template("cadastro.html")

    nome = request.form.get("nome")
    celular = request.form.get("celular")
    email = request.form.get("email")
    senha = request.form.get("senha")

    existe = supabase.table("users").select("*").eq("email", email).execute()
    if len(existe.data) > 0:
        return render_template("cadastro.html", erro="Email já cadastrado.")

    supabase.table("pending_users").delete().eq("email", email).execute()

    supabase.table("pending_users").insert({
        "nome": nome,
        "celular": celular,
        "email": email,
        "senha": senha
    }).execute()

    codigo = gerar_codigo()

    supabase.table("confirm_codes").delete().eq("email", email).execute()

    supabase.table("confirm_codes").insert({
        "email": email,
        "codigo": str(codigo)
    }).execute()

    enviar_email(email, codigo)

    return redirect(f"/confirmar?email={email}")


@app.route("/confirmar")
def confirmar_tela():
    email = request.args.get("email")
    return render_template("confirmar.html", email=email)


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

    supabase.table("users").insert({
        "nome": usuario["nome"],
        "celular": usuario["celular"],
        "email": usuario["email"],
        "senha": usuario["senha"],
        "is_admin": False
    }).execute()

    supabase.table("pending_users").delete().eq("email", email).execute()
    supabase.table("confirm_codes").delete().eq("email", email).execute()

    return jsonify({"message": "Confirmado com sucesso"}), 200


@app.route("/dashboard")
def dashboard():
    if "email" not in session:
        return redirect("/")
    return render_template("dashboard.html", nome=session["nome"])


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# RENDER PORT FIX
if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
