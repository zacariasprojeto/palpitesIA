import os
import qrcode
import base64
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from supabase import create_client, Client

# ======================================================
# CONFIGURAÇÃO APP / SUPABASE
# ======================================================
app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

app.secret_key = os.getenv("FLASK_SECRET_KEY", "chave_teste")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# SUA CHAVE PIX FIXA (NUBANK)
PIX_KEY = "9aacbabc-39ad-4602-b73e-955703ec502e"

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise RuntimeError("SUPABASE_URL ou SUPABASE_SERVICE_KEY não configuradas.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


# ======================================================
# GERADOR DE PIX COPIA E COLA
# ======================================================
def gerar_pix_qr(valor, descricao="Pagamento Lanzaca IA"):
    """
    Gera o código PIX copia e cola seguindo o padrão BRCode.
    """

    def brcode(id, value):
        size = str(len(value)).zfill(2)
        return f"{id}{size}{value}"

    merchant_account = brcode("00", "BR.GOV.BCB.PIX")
    merchant_account += brcode("01", PIX_KEY)

    transaction = brcode("00", descricao)

    valor_formatado = f"{valor:.2f}"

    payload = (
        brcode("00", "01")
        + brcode("26", merchant_account)
        + brcode("52", "0000")
        + brcode("53", "986")
        + brcode("54", valor_formatado)
        + brcode("59", "ZACARIAS APRIGIO")
        + brcode("60", "BRASIL")
        + brcode("62", transaction)
    )

    tamanho = str(len(payload)).zfill(2)
    payload = "01" + tamanho + payload

    # QR CODE em base64
    img = qrcode.make(payload)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img64 = base64.b64encode(buf.getvalue()).decode()

    return {
        "qrcode_base64": img64,
        "pix_copia_cola": payload
    }


# ======================================================
# HELPERS
# ======================================================
def parse_ts(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except:
        return None


def user_is_active(user):
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


# ======================================================
# ROTAS
# ======================================================

@app.route("/")
def index():
    return render_template("index.html")


# ------------------------------------------------------
# LOGIN
# ------------------------------------------------------
@app.route("/api/login", methods=["POST"])
def login():
    data = request.json or {}
    email = data.get("email")
    password = data.get("password")

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
        planos = [
            {"label": "Mensal", "price": 49.90, "days": 30},
            {"label": "Trimestral", "price": 129.90, "days": 90},
            {"label": "Semestral", "price": 219.90, "days": 180},
        ]

        return jsonify({
            "status": "blocked",
            "reason": motivo,
            "plans": planos,
            "user": user
        })

    session["user"] = user["email"]
    session["is_admin"] = user.get("is_admin", False)

    return jsonify({"status": "ok", "user": user})


# ------------------------------------------------------
# GERAR QR DE PLANO
# ------------------------------------------------------
@app.route("/api/qr_plano", methods=["POST"])
def qr_plano():
    data = request.json
    plano = data.get("plano")

    if plano == "mensal":
        valor = 49.90
    elif plano == "trimestral":
        valor = 129.90
    elif plano == "semestral":
        valor = 219.90
    else:
        return jsonify({"status": "error", "msg": "Plano inválido."})

    qr = gerar_pix_qr(valor, f"Plano {plano}")

    return jsonify({
        "status": "ok",
        "qrcode": qr["qrcode_base64"],
        "copia_cola": qr["pix_copia_cola"]
    })


# ------------------------------------------------------
# LOGOUT
# ------------------------------------------------------
@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"status": "ok"})


# ------------------------------------------------------
# LOCAL
# ------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
