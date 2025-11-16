import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client
from datetime import datetime, timedelta
import random
import smtplib
from email.mime.text import MIMEText
import requests

app = Flask(__name__)
CORS(app)

# ==========================
# CONFIG
# ==========================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")

EMAIL_SENDER = os.getenv("EMAIL_SENDER")       # seu email
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")   # senha do Gmail app

PIX_CHAVE = "9aacbabc-39ad-4602-b73e-955703ec502e"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================
# FUNÇÃO: enviar email
# ==========================
def enviar_email(destino, codigo):
    msg = MIMEText(f"Seu código de confirmação é:\n\n{codigo}\n\nLanzaca IA")
    msg["Subject"] = "Código de verificação"
    msg["From"] = EMAIL_SENDER
    msg["To"] = destino

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
            smtp.send_message(msg)
        return True
    except Exception as e:
        print("ERRO EMAIL:", e)
        return False

# ==========================
# ROTA: enviar código
# ==========================
@app.route("/api/send_code", methods=["POST"])
def send_code():
    data = request.json
    email = data.get("email")

    if not email:
        return jsonify({"error": "Email obrigatório"}), 400

    # impedir duplicados
    req = supabase.table("users").select("*").eq("email", email).execute()
    if req.data:
        return jsonify({"error": "Email já está cadastrado."}), 400

    codigo = str(random.randint(100000, 999999))
    expira = datetime.utcnow() + timedelta(minutes=10)

    supabase.table("confirm_codes").insert({
        "email": email,
        "code": codigo,
        "expires_at": expira.isoformat(),
    }).execute()

    enviar_email(email, codigo)

    return jsonify({"message": "Código enviado!"})

# ==========================
# CONFIRMAR CÓDIGO
# ==========================
@app.route("/api/verify_code", methods=["POST"])
def verify_code():
    data = request.json
    email = data.get("email")
    code = data.get("code")
    nome = data.get("nome")
    celular = data.get("celular")
    senha = data.get("senha")

    if not all([email, code, nome, celular, senha]):
        return jsonify({"error": "Dados incompletos"}), 400

    consulta = supabase.table("confirm_codes").select("*") \
        .eq("email", email).eq("code", code).eq("used", False).execute()

    if not consulta.data:
        return jsonify({"error": "Código incorreto"}), 400

    item = consulta.data[0]

    expira = datetime.fromisoformat(item["expires_at"].replace("Z", ""))
    if expira < datetime.utcnow():
        return jsonify({"error": "Código expirado"}), 400

    # marcar como usado
    supabase.table("confirm_codes").update({"used": True}) \
        .eq("id", item["id"]).execute()

    # criar usuário
    trial_ate = (datetime.utcnow() + timedelta(days=30)).date()

    supabase.table("users").insert({
        "nome": nome,
        "celular": celular,
        "email": email,
        "senha": senha,
        "verificado": True,
        "trial_ate": trial_ate.isoformat(),
        "plano": "trial",
        "status": "ativo"
    }).execute()

    return jsonify({"message": "Conta criada e trial liberado!"})

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
        return jsonify({"status": "error", "msg": "Credenciais inválidas"})

    user = user.data[0]

    if user["plano"] == "trial":
        if datetime.fromisoformat(str(user["trial_ate"])) < datetime.utcnow():
            return jsonify({"status": "blocked", "msg": "Trial expirado", "user": user})

    return jsonify({"status": "ok", "user": user})

# ==========================
# API FOOTBALL
# ==========================
def puxar(endpoint):
    headers = {"x-apisports-key": FOOTBALL_API_KEY}
    r = requests.get(f"https://v3.football.api-sports.io/{endpoint}", headers=headers)
    return r.json()

# TOP 3 DO DIA
@app.route("/api/top")
def top():
    data = puxar("predictions?league=71&season=2023")
    return jsonify(data)

# ==========================
# PAYWALL
# ==========================
@app.route("/api/paywall", methods=["GET"])
def paywall():
    return jsonify({
        "pix": PIX_CHAVE,
        "planos": [
            {"label": "Mensal", "price": 49.90, "dias": 30},
            {"label": "Trimestral", "price": 129.90, "dias": 90},
            {"label": "Semestral", "price": 219.90, "dias": 180},
        ]
    })

# ==========================
# ADMIN: USUÁRIOS PENDENTES
# ==========================
@app.route("/api/pending", methods=["GET"])
def pending():
    users = supabase.table("users").select("*").eq("status", "pendente").execute()
    return jsonify({"status": "ok", "pending": users.data})

# ==========================
# APROVAR USUÁRIO
# ==========================
@app.route("/api/approve", methods=["POST"])
def approve():
    email = request.json.get("email")
    supabase.table("users").update({"status": "ativo"}).eq("email", email).execute()
    return jsonify({"status": "ok", "msg": "Usuário aprovado!"})

# ==========================
# LOGOUT
# ==========================
@app.route("/api/logout", methods=["POST"])
def logout():
    return jsonify({"ok": True})

# ==========================
# SERVIDOR
# ==========================
@app.route("/")
def home():
    return "Backend OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
