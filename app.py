from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from supabase import create_client
from datetime import datetime, timedelta
import random
import string
import os
from openai import OpenAI

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "chavesecreta123")
CORS(app)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

OPENAI_API_KEY = os.getenv("OPENAI_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)


# ----------------------------
# GERADOR DE CÓDIGO
# ----------------------------
def gerar_codigo():
    return ''.join(random.choice(string.digits) for _ in range(6))


# ----------------------------
# ENVIAR EMAIL DE CONFIRMAÇÃO
# ----------------------------
def enviar_email_confirmacao(email, codigo):
    try:
        client.emails.send(
            to=email,
            subject="Código de confirmação",
            html=f"<h2>Seu código é: {codigo}</h2>"
        )
        return True
    except Exception as e:
        print("Erro ao enviar email:", e)
        return False


# ----------------------------
# VERIFICA SE O USUÁRIO ESTÁ LOGADO
# ----------------------------
def login_obrigatorio():
    if "usuario_id" not in session:
        return False
    return True
# -------------------------------------
# ROTA: TELA DE CADASTRO
# -------------------------------------
@app.route("/cadastro")
def cadastro():
    return render_template("cadastro.html")


# -------------------------------------
# API: REGISTRO DE USUÁRIO
# -------------------------------------
@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.json
    nome = data.get("nome")
    email = data.get("email")
    senha = data.get("senha")
    celular = data.get("celular")
    cpf = data.get("cpf")
    ip = request.remote_addr

    # CPF COM PONTOS E TRAÇO → remove formatação
    cpf = cpf.replace(".", "").replace("-", "")

    # Verificar email existente
    if supabase.table("usuarios").select("*").eq("email", email).execute().data:
        return jsonify({"error": "Email já registrado"}), 400

    # Verificar CPF existente
    if supabase.table("usuarios").select("*").eq("cpf", cpf).execute().data:
        return jsonify({"error": "CPF já registrado"}), 400

    codigo = gerar_codigo()
    expira = datetime.utcnow() + timedelta(minutes=15)

    # Inserir no Supabase
    supabase.table("usuarios").insert({
        "nome": nome,
        "email": email,
        "senha": senha,
        "celular": celular,
        "cpf": cpf,
        "ip": ip,
        "plano": "trial",
        "codigo_confirmacao": codigo,
        "expira_em": expira
    }).execute()

    enviar_email_confirmacao(email, codigo)

    return jsonify({"success": True})


# -------------------------------------
# ROTA: CONFIRMAR CÓDIGO
# -------------------------------------
@app.route("/confirmar")
def confirmar():
    return render_template("confirmar.html")


# -------------------------------------
# API: VALIDAR CÓDIGO
# -------------------------------------
@app.route("/api/confirmar", methods=["POST"])
def api_confirmar():
    data = request.json
    email = data.get("email")
    codigo = data.get("codigo")

    resp = supabase.table("usuarios").select("*").eq("email", email).execute()

    if not resp.data:
        return jsonify({"error": "Usuário não encontrado"}), 400

    user = resp.data[0]

    if user["codigo_confirmacao"] != codigo:
        return jsonify({"error": "Código incorreto"}), 400

    if datetime.utcnow() > datetime.fromisoformat(user["expira_em"].replace("Z", "")):
        return jsonify({"error": "Código expirado"}), 400

    supabase.table("usuarios").update({
        "codigo_confirmacao": None
    }).eq("email", email).execute()

    return jsonify({"success": True})
# -------------------------------------
# LOGIN
# -------------------------------------
@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.json
    email = data.get("email")
    senha = data.get("senha")

    resp = supabase.table("usuarios").select("*").eq("email", email).eq("senha", senha).execute()

    if not resp.data:
        return jsonify({"error": "Login inválido"}), 400

    user = resp.data[0]
    session["usuario_id"] = user["id"]
    session["nome"] = user["nome"]
    session["is_admin"] = user["is_admin"]

    return jsonify({"success": True})


# -------------------------------------
# PAINEL PRINCIPAL
# -------------------------------------
@app.route("/painel")
def painel():
    if not login_obrigatorio():
        return redirect("/")

    return render_template("painel.html", nome=session["nome"], is_admin=session["is_admin"])


# -------------------------------------
# ADMIN
# -------------------------------------
@app.route("/admin")
def admin():
    if not login_obrigatorio() or not session["is_admin"]:
        return redirect("/painel")

    usuarios = supabase.table("usuarios").select("*").execute().data
    return render_template("admin.html", usuarios=usuarios)


# -------------------------------------
# LOGOUT
# -------------------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# -------------------------------------
# HOME
# -------------------------------------
@app.route("/")
def home():
    return render_template("login.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
