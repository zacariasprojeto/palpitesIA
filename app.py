from flask import Flask, request, render_template, redirect, session, jsonify
from supabase import create_client
from datetime import datetime, timedelta
import os
import random
import bcrypt

app = Flask(__name__, template_folder="templates")
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# --- SUPABASE ---
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

# --- FUNÇÃO PARA ENVIAR CÓDIGO ---
def enviar_codigo(email, codigo):
    from resend import Emails
    Emails.send({
        "from": os.getenv("EMAIL_SENDER"),
        "to": email,
        "subject": "Seu código de confirmação - Lanzaca IA",
        "html": f"<h2>Seu código é <b>{codigo}</b></h2>"
    })

# ===============================
#   CADASTRO
# ===============================
@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        nome = request.form["nome"]
        email = request.form["email"]
        telefone = request.form["telefone"]
        senha = request.form["senha"].encode()
        ip = request.remote_addr

        # Hash seguro da senha
        senha_hash = bcrypt.hashpw(senha, bcrypt.gensalt()).decode()

        # Verifica se já existe conta
        usuario_existente = supabase.table("usuarios")\
            .select("*")\
            .or_(f"email.eq.{email},telefone.eq.{telefone},ip.eq.{ip}")\
            .execute()

        if usuario_existente.data:
            return render_template("cadastro.html",
                                   erro="Você já utilizou o período de teste.")

        codigo = random.randint(100000, 999999)

        # Salvar no banco
        supabase.table("usuarios").insert({
            "nome": nome,
            "email": email,
            "telefone": telefone,
            "senha": senha_hash,
            "codigo": codigo,
            "confirmado": False,
            "trial_started_at": datetime.utcnow().isoformat(),
            "plano": "trial",
            "status_pagamento": "pendente",
            "ip": ip
        }).execute()

        enviar_codigo(email, codigo)

        return redirect(f"/confirmar?email={email}")

    return render_template("cadastro.html")

# ===============================
#   CONFIRMAR CÓDIGO
# ===============================
@app.route("/confirmar", methods=["GET", "POST"])
def confirmar():
    email = request.args.get("email")

    if not email:
        return redirect("/login")  # evita 400 no Render

    if request.method == "POST":
        codigo = request.form["codigo"]

        dados = supabase.table("usuarios")\
            .select("*").eq("email", email).execute()

        if not dados.data:
            return render_template("confirmar.html", email=email,
                                   erro="Conta não encontrada!")

        usuario = dados.data[0]

        if str(usuario["codigo"]) != codigo:
            return render_template("confirmar.html", email=email,
                                   erro="Código incorreto")

        supabase.table("usuarios").update({
            "confirmado": True
        }).eq("email", email).execute()

        return redirect("/login")

    return render_template("confirmar.html", email=email)

# ===============================
#   LOGIN
# ===============================
@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        senha = request.form["senha"].encode()

        dados = supabase.table("usuarios").select("*")\
            .eq("email", email).execute()

        if not dados.data:
            return render_template("login.html",
                                   erro="Email ou senha incorretos")

        usuario = dados.data[0]

        # Verifica senha
        if not bcrypt.checkpw(senha, usuario["senha"].encode()):
            return render_template("login.html",
                                   erro="Email ou senha incorretos")

        # Verifica confirmação
        if not usuario["confirmado"]:
            return render_template("login.html",
                                   erro="Confirme seu email primeiro.")

        # Verifica trial
        inicio = datetime.fromisoformat(usuario["trial_started_at"])
        if datetime.utcnow() > inicio + timedelta(days=30):
            return render_template("login.html",
                                   erro="Seu teste expirou. Escolha um plano.")

        # Login OK
        session["usuario_id"] = usuario["id"]
        session["nome"] = usuario["nome"]
        session["plano"] = usuario["plano"]

        return redirect("/painel")

    return render_template("login.html")

# ===============================
#   PÁGINA PRINCIPAL / PAINEL
# ===============================
@app.route("/painel")
def painel():
    if "usuario_id" not in session:
        return redirect("/login")

    return render_template("painel.html",
                           nome=session["nome"],
                           plano=session["plano"])

# ===============================
#   TOP 3 – BLOQUEADO PARA TRIAL
# ===============================
@app.route("/top3")
def top3():
    if "usuario_id" not in session:
        return redirect("/login")

    if session["plano"] == "trial":
        return render_template("bloqueado.html")

    return render_template("top3.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# EXECUTAR
if __name__ == "__main__":
    app.run()
