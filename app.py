from flask import Flask, request, jsonify, render_template, redirect, session
from flask_cors import CORS
from datetime import datetime, timedelta
from supabase import create_client
import os
import random
import qrcode
import io
import base64

app = Flask(__name__)
CORS(app)

app.secret_key = os.getenv("FLASK_SECRET_KEY")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

API_FOOTBALL_KEY = "ed6c277617a7e4bfb0ad840ecedce5fc"


# -----------------------------
# FUNÇÃO DE EMAIL (placeholder)
# -----------------------------
def enviar_email_confirmacao(email, codigo):
    # aqui vamos mudar depois para Gmail SMTP
    print(f"----- CÓDIGO PARA {email}: {codigo} -----")
    return True


# -----------------------------
# CADASTRO
# -----------------------------
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    nome = data.get("nome")
    celular = data.get("celular")
    email = data.get("email")
    senha = data.get("senha")

    if not nome or not celular or not email or not senha:
        return jsonify({"error": "Preencha todos os campos"}), 400

    codigo = random.randint(100000, 999999)

    enviar_email_confirmacao(email, codigo)

    supabase.table("pending_users").insert({
        "nome": nome,
        "celular": celular,
        "email": email,
        "senha": senha,
        "codigo_confirmacao": codigo,
        "created_at": datetime.utcnow().isoformat()
    }).execute()

    return jsonify({"message": "Código enviado para o seu e-mail!"})


# -----------------------------
# CONFIRMAR CÓDIGO
# -----------------------------
@app.route('/api/confirmar-codigo', methods=['POST'])
def confirmar_codigo():
    data = request.json
    email = data.get("email")
    codigo = data.get("codigo")

    r = supabase.table("pending_users").select("*").eq("email", email).eq("codigo_confirmacao", codigo).execute()

    if len(r.data) == 0:
        return jsonify({"error": "Código incorreto"}), 400

    usuario = r.data[0]

    supabase.table("users").insert({
        "nome": usuario["nome"],
        "celular": usuario["celular"],
        "email": usuario["email"],
        "senha": usuario["senha"],
        "is_admin": False,
        "inicio_plano": datetime.utcnow().isoformat(),
        "fim_plano": (datetime.utcnow() + timedelta(days=30)).isoformat()
    }).execute()

    supabase.table("pending_users").delete().eq("email", email).execute()

    return jsonify({"message": "Conta confirmada! Faça login."})


# -----------------------------
# LOGIN
# -----------------------------
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get("email")
    senha = data.get("senha")

    r = supabase.table("users").select("*").eq("email", email).eq("senha", senha).execute()

    if len(r.data) == 0:
        return jsonify({"error": "Email ou senha incorretos"}), 400

    user = r.data[0]

    agora = datetime.utcnow()

    if agora > datetime.fromisoformat(user["fim_plano"]):
        return jsonify({"error": "Acesso expirado, renove seu plano"}), 403

    session["user"] = user

    return jsonify({
        "message": "Login OK",
        "nome": user["nome"],
        "email": user["email"],
        "is_admin": user["is_admin"]
    })
