import os
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, request, jsonify, session, redirect
from flask_cors import CORS
from supabase import create_client, Client

# ---------------------------------------------------------
# APP
# ---------------------------------------------------------
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.getenv("FLASK_SECRET_KEY", "chave_teste")
CORS(app)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# ---------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------
def parse_ts(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except:
        return None

def user_is_active(user):
    if not user:
        return False, "not_found"

    if user.get("is_admin"):
        return True, None

    plan = user.get("plan", "trial")
    now = datetime.now(timezone.utc)

    trial_end = parse_ts(user.get("trial_end"))
    paid_until = parse_ts(user.get("paid_until"))

    if plan == "trial":
        if not trial_end or trial_end < now:
            return False, "trial_expired"
        return True, None

    if plan == "paid":
        if not paid_until or paid_until < now:
            return False, "payment_expired"
        return True, None

    return False, "unknown_plan"

# ---------------------------------------------------------
# ROTAS DAS PÁGINAS
# ---------------------------------------------------------
@app.route("/")
def loader_page():
    return render_template("loader.html")

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/cadastro")
def cadastro_page():
    return render_template("cadastro.html")

@app.route("/confirmar")
def confirmar_page():
    return render_template("confirmar.html")

@app.route("/dashboard")
def dashboard_page():
    if "user" not in session:
        return redirect("/login")
    return render_template("painel.html")

@app.route("/palpites")
def palpites_page():
    return render_template("top_palpites.html")

@app.route("/top3")
def top3_page():
    return render_template("top3.html")

@app.route("/pagamento")
def pagamento_page():
    return render_template("pagamento.html")

# ---------------------------------------------------------
# API – CADASTRO
# ---------------------------------------------------------
@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.json or {}

    nome = data.get("nome", "").strip()
    cpf = data.get("cpf", "").strip()
    telefone = data.get("telefone", "").strip()
    email = data.get("email", "").strip()
    senha = data.get("senha", "").strip()

    if not nome or not cpf or not telefone or not email or not senha:
        return jsonify({"status": "error", "msg": "Preencha todos os campos."})

    # Já existe?
    exists = supabase.table("users").select("email").eq("email", email).execute()
    if exists.data:
        return jsonify({"status": "error", "msg": "Email já registrado."})

    # Inserir pendente
    supabase.table("pending_users").insert({
        "nome": nome,
        "cpf": cpf,
        "telefone": telefone,
        "email": email,
        "password": senha
    }).execute()

    return jsonify({"status": "ok"})

# ---------------------------------------------------------
# API – LOGIN
# ---------------------------------------------------------
@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.json or {}

    email = data.get("email", "").strip()
    senha = data.get("password", "").strip()

    res = supabase.table("users").select("*").eq("email", email).eq("password", senha).execute()

    if not res.data:
        return jsonify({"status": "error", "msg": "Email ou senha inválidos"})

    user = res.data[0]

    ativo, motivo = user_is_active(user)
    if not ativo:
        return jsonify({"status": "blocked", "reason": motivo})

    session["user"] = user["email"]
    session["nome"] = user.get("nome")

    return jsonify({"status": "ok"})

# ---------------------------------------------------------
# API – LOGOUT
# ---------------------------------------------------------
@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"status": "ok"})

# ---------------------------------------------------------
# RUN
# ---------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
