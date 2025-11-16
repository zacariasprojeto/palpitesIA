import os
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from supabase import create_client, Client

# -----------------------------------
# CONFIGURAÇÃO DO APP
# -----------------------------------

app = Flask(__name__)
CORS(app)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  # SERVICE KEY!
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

PIX_KEY = os.getenv("PIX_KEY", "0000000000000")
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")

# -----------------------------------
# FUNÇÃO – VERIFICA SE USUÁRIO TEM ACESSO
# -----------------------------------

def verificar_acesso(usuario):
    email = usuario["email"]
    is_admin = usuario.get("is_admin", False)
    trial_end = usuario.get("trial_end")
    paid_until = usuario.get("paid_until")

    if is_admin:
        return True

    agora = datetime.utcnow()

    if paid_until and datetime.fromisoformat(paid_until.replace("Z", "")) > agora:
        return True

    if trial_end and datetime.fromisoformat(trial_end.replace("Z", "")) > agora:
        return True

    return False

# -----------------------------------
# ROTA – HOME
# -----------------------------------

@app.route("/")
def home():
    return render_template("index.html")

# -----------------------------------
# ROTA – CADASTRO
# -----------------------------------

@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    nome = data.get("nome")
    email = data.get("email")
    celular = data.get("celular")
    password = data.get("password")

    # Já existe?
    existe = supabase.table("users").select("*").eq("email", email).execute()
    if existe.data:
        return jsonify({"error": "Email já cadastrado."}), 400

    trial = datetime.utcnow() + timedelta(days=30)

    novo = supabase.table("users").insert({
        "nome": nome,
        "email": email,
        "password": password,
        "celular": celular,
        "plan": "trial",
        "trial_end": trial.isoformat(),
        "paid_until": None,
        "is_admin": False
    }).execute()

    return jsonify({"success": True})

# -----------------------------------
# ROTA – LOGIN
# -----------------------------------

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    user = supabase.table("users").select("*").eq("email", email).eq("password", password).execute()

    if not user.data:
        return jsonify({"error": "Credenciais inválidas"}), 401

    user = user.data[0]

    if not verificar_acesso(user):
        return jsonify({
            "error": "acesso_bloqueado",
            "pix": PIX_KEY,
            "mensagem": "Seu acesso expirou. Faça o pagamento para continuar."
        }), 403

    return jsonify({
        "success": True,
        "user": {
            "id": user["id"],
            "nome": user["nome"],
            "email": user["email"],
            "is_admin": user["is_admin"]
        }
    })

# -----------------------------------
# ROTA – PAGAMENTO PIX (APROVA MANUAL AUTOMÁTICO)
# -----------------------------------

@app.route("/api/pagamento/confirmar", methods=["POST"])
def confirmar_pagamento():
    email = request.json.get("email")

    novo_prazo = datetime.utcnow() + timedelta(days=30)

    supabase.table("users").update({
        "paid_until": novo_prazo.isoformat(),
        "plan": "mensal"
    }).eq("email", email).execute()

    return jsonify({"success": True})

# -----------------------------------
# ROTA – ADMIN LISTA USUÁRIOS
# -----------------------------------

@app.route("/api/admin/usuarios", methods=["GET"])
def admin_usuarios():
    users = supabase.table("users").select("id,nome,email,plan,trial_end,paid_until,is_admin").execute()
    return jsonify(users.data)

# -----------------------------------
# ROTA – ADMIN LIBERAR USUÁRIO
# -----------------------------------

@app.route("/api/admin/liberar", methods=["POST"])
def admin_liberar():
    user_id = request.json.get("user_id")
    dias = request.json.get("dias", 30)

    novo = datetime.utcnow() + timedelta(days=dias)

    supabase.table("users").update({
        "paid_until": novo.isoformat(),
        "plan": "liberado_admin"
    }).eq("id", user_id).execute()

    return jsonify({"success": True})

# -----------------------------------
# ROTA – API DAS ODDS / PALPITES
# -----------------------------------

@app.route("/api/palpites")
def palpites():
    # Aqui depois vamos integrar com sua API de apostas (API-FOOTBALL)
    return jsonify({"status": "ok", "mensagem": "API de palpites conectada!"})

# -----------------------------------
# START
# -----------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
