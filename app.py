import os
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from supabase import create_client, Client

# ---------------------------------------------------------
# CONFIG DO APP
# ---------------------------------------------------------
app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "chave_teste")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# SUA CHAVE PIX
PIX_KEY = "9aacbabc-39ad-4602-b73e-955703ec502e"

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise RuntimeError("Configure SUPABASE_URL e SUPABASE_SERVICE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
def parse_ts(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except:
        return None

def user_is_active(user: dict):
    if not user:
        return False, "not_found"

    if user.get("is_admin"):
        return True, None

    now = datetime.now(timezone.utc)
    plan = user.get("plan") or "trial"
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
# FRONTEND
# ---------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")

# ---------------------------------------------------------
# LOGIN
# ---------------------------------------------------------
@app.route("/api/login", methods=["POST"])
def login():
    data = request.json or {}
    email = data.get("email", "")
    password = data.get("password", "")

    result = supabase.table("users").select("*").eq("email", email).eq("password", password).execute()
    rows = result.data or []
    if not rows:
        return jsonify({"status": "error", "msg": "Email ou senha incorretos."})

    user = rows[0]
    ativo, motivo = user_is_active(user)

    if not ativo:
        msg = "Seu teste acabou. Pague via PIX para liberar."
        if motivo == "payment_expired":
            msg = "Seu plano acabou. Renove via PIX."

        return jsonify({
            "status": "blocked",
            "reason": motivo,
            "msg": msg,
            "pix_key": PIX_KEY,
            "plans": [
                {"label": "Mensal",     "price": "49.90",  "days": 30},
                {"label": "Trimestral", "price": "129.90", "days": 90},
                {"label": "Semestral",  "price": "219.90", "days": 180},
            ],
            "user": user
        })

    session["user"] = user["email"]
    session["is_admin"] = user.get("is_admin", False)

    return jsonify({"status": "ok", "msg": "Login OK!", "user": user})

# ---------------------------------------------------------
# REGISTRO (vai para pending_users)
# ---------------------------------------------------------
@app.route("/api/register", methods=["POST"])
def register():
    data = request.json or {}
    email = data.get("email", "")
    password = data.get("password", "")

    exists = supabase.table("users").select("email").eq("email", email).execute()
    if exists.data:
        return jsonify({"status": "error", "msg": "Email já registrado."})

    pending = supabase.table("pending_users").select("email").eq("email", email).execute()
    if pending.data:
        return jsonify({"status": "error", "msg": "Cadastro já solicitado."})

    supabase.table("pending_users").insert({
        "email": email,
        "password": password
    }).execute()

    return jsonify({"status": "ok", "msg": "Cadastro enviado! Aguarde aprovação."})

# ---------------------------------------------------------
# LISTAR PENDENTES (ADMIN)
# ---------------------------------------------------------
@app.route("/api/pending")
def pending():
    if not session.get("is_admin"):
        return jsonify({"status": "error", "msg": "Não autorizado"}), 403

    result = supabase.table("pending_users").select("*").execute()
    return jsonify({"status": "ok", "pending": result.data})

# ---------------------------------------------------------
# APROVAR USUÁRIO (30 dias)
# ---------------------------------------------------------
@app.route("/api/approve", methods=["POST"])
def approve():
    if not session.get("is_admin"):
        return jsonify({"status": "error", "msg": "Não autorizado"}), 403

    data = request.json or {}
    email = data.get("email", "")

    res = supabase.table("pending_users").select("*").eq("email", email).execute()
    if not res.data:
        return jsonify({"status": "error", "msg": "Pendente não encontrado"})

    pend = res.data[0]
    trial_end = datetime.now(timezone.utc) + timedelta(days=30)

    supabase.table("users").insert({
        "email": pend["email"],
        "password": pend["password"],
        "is_admin": False,
        "plan": "trial",
        "trial_end": trial_end.isoformat(),
        "paid_until": None
    }).execute()

    supabase.table("pending_users").delete().eq("email", email).execute()

    return jsonify({"status": "ok", "msg": "Aprovado com 30 dias de teste"})

# ---------------------------------------------------------
# LOGOUT
# ---------------------------------------------------------
@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"status": "ok"})

# ---------------------------------------------------------
# RUN
# ---------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
