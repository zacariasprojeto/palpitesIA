from flask import Flask, request, render_template, redirect, session, jsonify
from supabase import create_client
from datetime import datetime, timedelta
import os
import random

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# --- SUPABASE ---
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(supabase_url, supabase_key)

# --- FUNÇÃO AUXILIAR ---
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
        senha = request.form["senha"]
        ip = request.remote_addr

        # Verifica se já existe conta com mesmo email, telefone ou IP
        usuario_existente = supabase.table("usuarios")\
            .select("*")\
            .or_(f"email.eq.{email},telefone.eq.{telefone},ip.eq.{ip}")\
            .execute()

        if usuario_existente.data:
            return render_template("cadastro.html", erro="Você já usou o período de teste.")

        codigo = random.randint(100000, 999999)

        supabase.table("usuarios").insert({
            "nome": nome,
            "email": email,
            "telefone": telefone,
            "senha": senha,
            "codigo": codigo,
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

    if request.method == "POST":
        codigo = request.form["codigo"]

        dados = supabase.table("usuarios").select("*")\
            .eq("email", email).execute()

        if not dados.data:
            return "Erro!"

        usuario = dados.data[0]

        if str(usuario["codigo"]) != codigo:
            return render_template("confirmar.html", email=email, erro="Código incorreto")

        # Confirma usuário
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
        senha = request.form["senha"]

        dados = supabase.table("usuarios").select("*")\
            .eq("email", email)\
            .eq("senha", senha).execute()

        if not dados.data:
            return render_template("login.html", erro="Email ou senha incorretos")

        usuario = dados.data[0]

        # Verifica confirmação
        if not usuario["confirmado"]:
            return render_template("login.html", erro="Confirme seu email antes de entrar!")

        # Verifica trial expirado
        inicio = datetime.fromisoformat(usuario["trial_started_at"])
        if datetime.utcnow() > inicio + timedelta(days=30):
            return render_template("login.html", erro="Seu período grátis expirou. Escolha um plano.")

        # Login OK
        session["usuario_id"] = usuario["id"]
        session["nome"] = usuario["nome"]
        session["plano"] = usuario["plano"]

        return redirect("/painel")

    return render_template("login.html")


# ===============================
#   PÁGINA PRINCIPAL
# ===============================
@app.route("/painel")
def painel():
    if "usuario_id" not in session:
        return redirect("/login")

    return render_template("painel.html",
        nome=session["nome"],
        plano=session["plano"]
    )


# ===============================
#   TOP 3 – BLOQUEADO
# ===============================
@app.route("/top3")
def top3():
    if "usuario_id" not in session:
        return redirect("/login")

    # Só entra se TEM plano ativo
    if session["plano"] == "trial":
        return render_template("bloqueado.html")

    # NO PLANO PAGO → MOSTRA TOP 3
    return render_template("top3.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# =======================================
#           EXECUTAR
# =======================================
if __name__ == "__main__":
    app.run()
