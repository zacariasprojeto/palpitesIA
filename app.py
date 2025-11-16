import os
from datetime import datetime, timedelta, timezone

from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from supabase import create_client, Client

# ---------------------------------------------------------
# APP / SUPABASE
# ---------------------------------------------------------
app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

app.secret_key = os.getenv("FLASK_SECRET_KEY", "chave_teste")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# sua chave pix de fallback (pode sobrescrever com variável PIX_KEY no Render)
PIX_KEY = os.getenv(
    "PIX_KEY",
    "9aacbabc-39ad-4602-b73e-955703ec502e"
)

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise RuntimeError("Variáveis SUPABASE_URL / SUPABASE_SERVICE_KEY não configuradas!")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
def parse_ts(value):
    """Converte string/timestamp do Supabase em datetime ou None."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        # Supabase costuma mandar '2025-11-15T22:22:55.955288+00:00' ou com 'Z'
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def user_is_active(user: dict) -> tuple[bool, str | None]:
    """
    Retorna (ativo, motivo_bloqueio)
    motivo_bloqueio: 'trial_expired' | 'payment_expired' | None
    """
    if not user:
        return False, "not_found"

    if user.get("is_admin"):
        # Admin sempre pode entrar
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

    # Plano desconhecido → bloquear por segurança
    return False, "unknown_plan"


# ---------------------------------------------------------
# FRONT
# ---------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------
# API: LOGIN
# ---------------------------------------------------------
@app.route("/api/login", methods=["POST"])
def login():
    data = request.json or {}
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if not email or not password:
        return jsonify({"status": "error", "msg": "Informe email e senha."})

    result = (
        supabase.table("users")
        .select("*")
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
        # Usuário existe, mas não tem mais acesso
        msg = "Seu período de teste acabou. Para continuar, faça o pagamento via PIX."
        if motivo == "payment_expired":
            msg = "Seu plano venceu. Renove via PIX para continuar usando."

        return jsonify({
            "status": "blocked",
            "reason": motivo,
            "msg": msg,
            "pix_key": PIX_KEY,
            "plans": [
                {"label": "Mensal",     "price": "49,90",  "days": 30},
                {"label": "Trimestral", "price": "129,90", "days": 90},
                {"label": "Semestral",  "price": "219,90", "days": 180},
            ],
            "user": {
                "email": user.get("email"),
                "name": user.get("name"),
                "phone": user.get("phone"),
                "plan": user.get("plan"),
                "trial_end": user.get("trial_end"),
                "paid_until": user.get("paid_until"),
                "is_admin": user.get("is_admin", False),
            },
        })

    # Ativo → guardar sessão e liberar dashboard
    session["user"] = user["email"]
    session["is_admin"] = user.get("is_admin", False)

    return jsonify({
        "status": "ok",
        "msg": "Login autorizado!",
        "user": {
            "email": user.get("email"),
            "name": user.get("name"),
            "phone": user.get("phone"),
            "is_admin": user.get("is_admin", False),
            "plan": user.get("plan"),
            "trial_end": user.get("trial_end"),
            "paid_until": user.get("paid_until"),
        },
    })


# ---------------------------------------------------------
# API: REGISTRO → vai para pending_users (aguardando aprovação)
# ---------------------------------------------------------
@app.route("/api/register", methods=["POST"])
def register():
    data = request.json or {}
    name = data.get("name", "").strip()
    phone = data.get("phone", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if not name or not phone or not email or not password:
        return jsonify({
            "status": "error",
            "msg": "Informe nome, celular, email e senha."
        })

    # Já existe na users?
    exists = (
        supabase.table("users")
        .select("email")
        .eq("email", email)
        .execute()
    )
    if exists.data:
        return jsonify({"status": "error", "msg": "Email já registrado."})

    # Já está pendente?
    pending = (
        supabase.table("pending_users")
        .select("email")
        .eq("email", email)
        .execute()
    )
    if pending.data:
        return jsonify({"status": "error", "msg": "Cadastro já solicitado. Aguarde aprovação."})

    # Inserir na pending_users
    supabase.table("pending_users").insert({
        "name": name,
        "phone": phone,
        "email": email,
        "password": password,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }).execute()

    return jsonify({
        "status": "ok",
        "msg": "Cadastro enviado! Aguarde o admin aprovar."
    })


# ---------------------------------------------------------
# API: LISTAR PENDENTES (apenas admin)
# ---------------------------------------------------------
@app.route("/api/pending", methods=["GET"])
def pending_users():
    if not session.get("is_admin"):
        return jsonify({"status": "error", "msg": "Não autorizado."}), 403

    result = (
        supabase.table("pending_users")
        .select("id, name, phone, email, created_at")
        .order("created_at", desc=True)
        .execute()
    )
    return jsonify({"status": "ok", "pending": result.data or []})


# ---------------------------------------------------------
# API: APROVAR USUÁRIO (cria users com 30 dias trial)
# ---------------------------------------------------------
@app.route("/api/approve", methods=["POST"])
def approve_user():
    if not session.get("is_admin"):
        return jsonify({"status": "error", "msg": "Não autorizado."}), 403

    data = request.json or {}
    email = data.get("email", "").strip()

    if not email:
        return jsonify({"status": "error", "msg": "Email não informado."}), 400

    res = (
        supabase.table("pending_users")
        .select("*")
        .eq("email", email)
        .execute()
    )
    rows = res.data or []
    if not rows:
        return jsonify({"status": "error", "msg": "Usuário pendente não encontrado."})

    pend = rows[0]

    trial_end = datetime.now(timezone.utc) + timedelta(days=30)

    # Cria na users
    supabase.table("users").insert({
        "name": pend.get("name"),
        "phone": pend.get("phone"),
        "email": pend["email"],
        "password": pend["password"],
        "is_admin": False,
        "plan": "trial",
        "trial_end": trial_end.isoformat(),
        "paid_until": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }).execute()

    # Remove da pending_users
    supabase.table("pending_users").delete().eq("email", email).execute()

    return jsonify({"status": "ok", "msg": "Usuário aprovado com 30 dias de teste."})


# ---------------------------------------------------------
# API: LOGOUT
# ---------------------------------------------------------
@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"status": "ok"})


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
if __name__ == "__main__":
    # Local
    app.run(host="0.0.0.0", port=5000)
