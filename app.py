from flask import Flask, request, render_template, redirect, session
from supabase import create_client
from datetime import datetime, timedelta
import os
import random

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# --- Supabase ---
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(supabase_url, supabase_key)

# --- Envio de código por e-mail ---
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

        codigo = random.randint(100000, 999999)

        # cria usuário no Supabase
        supabase.table("usuarios").insert({
            "nome": nome,
            "email": email,
            "telefone": telefone,
            "senha": senha,
            "codigo": codigo,
            "confirmado": False,
            "plano": "trial",
            "trial_started_at": datetime.utcnow().isoformat()
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

        dados = supabase.table("usuarios").select("*").eq("email", email).execute()

        if not dados.data:
            return render_template("confirmar.html", email=email, erro="Conta não encontrada")

        usuario = dados.data[0]

        if str(usuario["codigo"]) != codigo:
            return render_template("confirmar.html", email=email, erro="Código incorreto")

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
            .eq("email", email).eq("senha", senha).execute()

        if not dados.data:
            return render_template("login.html", erro="Email ou senha incorretos")

        usuario = dados.data[0]

        if not usuario["confirmado"]:
            return render_template("login.html", erro="Confirme seu email!")

        session["usuario_id"] = usuario["id"]
        session["nome"] = usuario["nome"]

        return redirect("/painel")

    return render_template("login.html")

# ===============================
#   PAINEL PRINCIPAL
# ===============================
@app.route("/painel")
def painel():
    if "usuario_id" not in session:
        return redirect("/login")

    return render_template("painel.html", nome=session["nome"])

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# --- Rodar local ---
if __name__ == "__main__":
    app.run()
