import os
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from supabase import create_client, Client
import requests
import random
import string

# ==========================
# CONFIGURAÇÃO FLASK
# ==========================
app = Flask(__name__)
CORS(app)

# ==========================
# SUPABASE CONFIG
# ==========================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# ==========================
# API DE PALPITES (API-FOOTBALL)
# ==========================
API_FOOTBALL_KEY = os.getenv("ODDS_API_KEY")  # sua key ed6c277617a7e4bfb0ad840ecedce5fc

# ==========================
# FUNÇÃO PARA ENVIAR CÓDIGO POR EMAIL (SUPABASE)
# ==========================
def enviar_codigo_email(email, codigo):
    try:
        supabase.table("pending_users").insert({
            "email": email,
            "codigo": codigo,
            "created_at": datetime.utcnow().isoformat()
        }).execute()
        return True
    except:
        return False

# ==========================
# GERAR CÓDIGO DE 6 DÍGITOS
# ==========================
def gerar_codigo():
    return ''.join(random.choices(string.digits, k=6))

# ==========================
# ROTA HOME → CARREGA O FRONTEND
# ==========================
@app.route("/")
def home():
    return render_template("index.html")

# ==========================
# ROTA DE CADASTRO
# ==========================
@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    nome = data.get("nome")
    celular = data.get("celular")
    email = data.get("email")
    senha = data.get("senha")

    if not all([nome, celular, email, senha]):
        return jsonify({"error": "Campos incompletos"}), 400

    # verifica se email já existe
    check = supabase.table("users").select("*").eq("email", email).execute()
    if check.data:
        return jsonify({"error": "Email já cadastrado"}), 400

    codigo = gerar_codigo()

    # salva pendente até confirmar e-mail
    enviar_codigo_email(email, codigo)

    return jsonify({"success": True, "message": "Código enviado ao email"})


# ==========================
# CONFIRMAR CÓDIGO DO EMAIL
# ==========================
@app.route("/api/confirmar", methods=["POST"])
def confirmar():
    data = request.json
    email = data.get("email")
    codigo_digitado = data.get("codigo")

    pendente = supabase.table("pending_users").select("*").eq("email", email).order("id", desc=True).limit(1).execute()

    if not pendente.data:
        return jsonify({"error": "Nenhum código encontrado"}), 400

    codigo_real = pendente.data[0]["codigo"]

    if codigo_real != codigo_digitado:
        return jsonify({"error": "Código incorreto"}), 400

    # criar usuário com trial de 30 dias
    supabase.table("users").insert({
        "email": email,
        "nome": email.split("@")[0],
        "senha": "definir_senha_no_cadastro",
        "acesso_ate": (datetime.utcnow() + timedelta(days=30)).isoformat(),
        "role": "user"
    }).execute()

    return jsonify({"success": True})


# ==========================
# LOGIN
# ==========================
@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    senha = data.get("senha")

    user = supabase.table("users").select("*").eq("email", email).eq("senha", senha).execute()

    if not user.data:
        return jsonify({"error": "Email ou senha incorretos"}), 400

    user = user.data[0]

    # verificar expiração do plano
    if user["acesso_ate"] and datetime.fromisoformat(user["acesso_ate"]) < datetime.utcnow():
        return jsonify({"error": "Acesso expirado"}), 403

    return jsonify({
        "success": True,
        "user": user
    })


# ==========================
# ROTA ADMIN
# ==========================
@app.route("/api/admin/pendentes")
def admin_pendentes():
    pendentes = supabase.table("pending_users").select("*").execute()
    return jsonify(pendentes.data)


# ==========================
# API DE PALPITES (TOP 5, SEGUROS, MÚLTIPLAS)
# ==========================
@app.route("/api/palpites")
def palpites():
    headers = {
        "x-apisports-key": API_FOOTBALL_KEY
    }

    url = "https://v3.football.api-sports.io/odds?region=eu&sport=soccer"

    r = requests.get(url, headers=headers)

    try:
        return jsonify(r.json())
    except:
        return jsonify({"error": "Erro na API"}), 500


# ==========================
# RUN
# ==========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
