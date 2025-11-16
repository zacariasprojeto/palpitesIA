import os
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from supabase import create_client, Client
import qrcode
import base64
from io import BytesIO

# ---------------------------------------------------------
# CONFIGURAÇÃO DO APP
# ---------------------------------------------------------
app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

app.secret_key = os.getenv("FLASK_SECRET_KEY", "chave_teste")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

PIX_KEY = "9aacbabc-39ad-4602-b73e-955703ec502e"

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise RuntimeError("Variáveis SUPABASE_URL / SUPABASE_SERVICE_KEY não configuradas!")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# ---------------------------------------------------------
# FUNÇÃO: GERAR QR ESTÁTICO BR CODE
# ---------------------------------------------------------
def gerar_payload_pix(valor, descricao="Lanzaca IA"):
    valor_format = f"{valor:.2f}"
    payload = (
        f"000201"
        f"010212"
        f"26"
        f"0014BR.GOV.BCB.PIX"
        f"01{len(PIX_KEY):02}{PIX_KEY}"
        f"52"
        f"0015BR.GOV.BCB.PIX"
        f"53"
        f"000986"
        f"54{len(valor_format):02}{valor_format}"
        f"58"
        f"0002BR"
        f"59"
        f"0010LanzacaIA"
        f"60"
        f"0008BRASIL"
        f"62"
        f"0005LZ001"
    )
    return payload

def gerar_qrcode_base64(payload):
    img = qrcode.make(payload)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()

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

    plan = user.get("plan") or "trial"
    trial_end = parse_ts(user.get("trial_end"))
    paid_until = parse_ts(user.get("paid_until"))
    now = datetime.now(timezone.utc)

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
# FRONT
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
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    result = (
        supabase.table("users").select("*")
        .eq("email", email)
        .eq("password", password)
        .execute()
    )

    rows = result.data or []
    if not rows:
        return jsonify({"status": "error", "msg": "Email ou senha incorretos."})

    user = rows[0]

    ativo, motivo = user_is_active(user)
    if not ativo:
        planos = [
            {"label": "Mensal", "price": 49.90, "dias": 30},
            {"label": "Trimestral", "price": 129.90, "dias": 90},
            {"label": "Semestral", "price": 219.90, "dias": 180},
        ]

        # Gera QR de cada plano
        for plano in planos:
            payload = gerar_payload_pix(plano["price"])
            plano["qr"] = gerar_qrcode_base64(payload)

        return jsonify({
            "status": "blocked",
            "msg": "Seu acesso está bloqueado. Realize o pagamento via PIX.",
            "plans": planos,
            "pix_key": PIX_KEY
        })

    session["user"] = user["email"]
    session["is_admin"] = user.get("is_admin", False)

    return jsonify({"status": "ok", "user": user})

# ---------------------------------------------------------
# REGISTRO
# ---------------------------------------------------------
@app.route("/api/register", methods=["POST"])
def register():
    data = request.json or {}
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    exists = supabase.table("users").select("email").eq("email", email).execute()
    if exists.data:
        return jsonify({"status": "error", "msg": "Email já cadastrado."})

    pend = supabase.table("pending_users").select("email").eq("email", email).execute()
    if pend.data:
        return jsonify({"status": "error", "msg": "Cadastro já solicitado."})

    supabase.table("pending_users").insert({
        "email": email,
        "password": password,
        "created_at": datetime.now(timezone.utc).isoformat()
    }).execute()

    return jsonify({"status": "ok", "msg": "Cadastro enviado!"})

# ---------------------------------------------------------
# LISTAR PENDENTES
# ---------------------------------------------------------
@app.route("/api/pending")
def pending_users():
    if not session.get("is_admin"):
        return jsonify({"status": "error"}), 403

    res = supabase.table("pending_users").select("*").execute()
    return jsonify({"status": "ok", "pending": res.data})

# ---------------------------------------------------------
# APROVAR
# ---------------------------------------------------------
@app.route("/api/approve", methods=["POST"])
def approve():
    if not session.get("is_admin"):
        return jsonify({"status": "error"}), 403

    email = request.json.get("email", "").strip()

    pend = supabase.table("pending_users").select("*").eq("email", email).execute()
    if not pend.data:
        return jsonify({"status": "error", "msg": "Usuário não encontrado."})

    trial_end = datetime.now(timezone.utc) + timedelta(days=30)

    supabase.table("users").insert({
        "email": pend.data[0]["email"],
        "password": pend.data[0]["password"],
        "plan": "trial",
        "trial_end": trial_end.isoformat(),
        "paid_until": None,
        "is_admin": False
    }).execute()

    supabase.table("pending_users").delete().eq("email", email).execute()

    return jsonify({"status": "ok"})

# ---------------------------------------------------------
# LOGOUT
# ---------------------------------------------------------
@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"status": "ok"})

# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
