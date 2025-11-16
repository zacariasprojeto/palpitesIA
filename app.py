import os
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from supabase import create_client, Client
import qrcode
import base64
from io import BytesIO

# ---------------------------------------------------------
# CONFIG DO APP
# ---------------------------------------------------------
app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "chave_teste")

# ---------------------------------------------------------
# CONFIG SUPABASE
# ---------------------------------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

PIX_KEY = "9aacbabc-39ad-4602-b73e-955703ec502e"  # SUA CHAVE PIX ÚNICA

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise RuntimeError("Variáveis SUPABASE_URL / SUPABASE_SERVICE_KEY não configuradas!")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


# ---------------------------------------------------------
# FUNÇÃO GERAR CÓDIGO PIX (COPIA & COLA)
# ---------------------------------------------------------
def gerar_codigo_pix(chave, nome_recebedor, cidade, valor, descricao):
    """
    Gera o código EMV + QR Code para pagamento PIX.
    """
    valor = f"{valor:.2f}"

    payload = (
        "000201"
        "010212"
        "26" + str(14 + len(chave)) +
        "0014BR.GOV.BCB.PIX01" + str(len(chave)).zfill(2) + chave +
        "52040000"
        "5303986"
        "54" + str(len(valor)).zfill(2) + valor +
        "5802BR"
        "59" + str(len(nome_recebedor)).zfill(2) + nome_recebedor +
        "60" + str(len(cidade)).zfill(2) + cidade +
        "62070503***"
    )

    soma = 0
    polinomio = 0x1021

    def calc_crc(payload):
        crc = 0xFFFF
        for c in payload:
            crc ^= ord(c) << 8
            for _ in range(8):
                if (crc & 0x8000):
                    crc = (crc << 1) ^ polinomio
                else:
                    crc <<= 1
                crc &= 0xFFFF
        return format(crc, '04X')

    crc16 = calc_crc(payload + "6304")
    return payload + "6304" + crc16


# ---------------------------------------------------------
# GERA QR CODE BASE64
# ---------------------------------------------------------
def gerar_qr_base64(text):
    img = qrcode.make(text)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


# ---------------------------------------------------------
# HELPER TRIAL/PAGAMENTO
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

    now = datetime.now(timezone.utc)
    trial_end = parse_ts(user.get("trial_end"))
    paid_until = parse_ts(user.get("paid_until"))
    plan = user.get("plan", "trial")

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
# API: LOGIN
# ---------------------------------------------------------
@app.route("/api/login", methods=["POST"])
def login():
    data = request.json or {}
    email = data.get("email")
    password = data.get("password")

    result = supabase.table("users").select("*").eq("email", email).eq("password", password).execute()
    rows = result.data or []

    if not rows:
        return jsonify({"status": "error", "msg": "Email ou senha incorretos."})

    user = rows[0]

    ativo, motivo = user_is_active(user)
    if not ativo:
        planos = [
            {"label": "Mensal", "price": "49.90", "days": 30},
            {"label": "Trimestral", "price": "129.90", "days": 90},
            {"label": "Semestral", "price": "219.90", "days": 180},
        ]

        return jsonify({
            "status": "blocked",
            "reason": motivo,
            "msg": "Plano inativo. Escolha um plano abaixo.",
            "pix_key": PIX_KEY,
            "plans": planos,
            "user": user,
        })

    session["user"] = user["email"]
    session["is_admin"] = user.get("is_admin", False)

    return jsonify({"status": "ok", "user": user})


# ---------------------------------------------------------
# API GERAR QR DO PLANO
# ---------------------------------------------------------
@app.route("/api/qrpix", methods=["POST"])
def gerar_qr():
    data = request.json
    plano = data.get("plano")

    precos = {
        "mensal": 49.90,
        "trimestral": 129.90,
        "semestral": 219.90
    }

    if plano not in precos:
        return jsonify({"status": "error", "msg": "Plano inválido."})

    valor = precos[plano]

    emv = gerar_codigo_pix(
        chave=PIX_KEY,
        nome_recebedor="LanzacaIA",
        cidade="BRASIL",
        valor=valor,
        descricao=f"Plano {plano}"
    )

    qr_b64 = gerar_qr_base64(emv)

    return jsonify({
        "status": "ok",
        "emv": emv,
        "qr": qr_b64,
        "valor": f"{valor:.2f}"
    })


# ---------------------------------------------------------
# API: REGISTRO
# ---------------------------------------------------------
@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    exists = supabase.table("users").select("email").eq("email", email).execute()
    if exists.data:
        return jsonify({"status": "error", "msg": "Email já registrado."})

    supabase.table("pending_users").insert({"email": email, "password": password}).execute()

    return jsonify({"status": "ok", "msg": "Cadastro enviado! Aguarde aprovação do Admin."})


# ---------------------------------------------------------
# API ADMIN LISTAR PENDENTES
# ---------------------------------------------------------
@app.route("/api/pending")
def pending():
    if not session.get("is_admin"):
        return jsonify({"status": "error", "msg": "Não autorizado."}), 403

    r = supabase.table("pending_users").select("*").execute()
    return jsonify({"status": "ok", "pending": r.data})


# ---------------------------------------------------------
# API ADMIN APROVAR
# ---------------------------------------------------------
@app.route("/api/approve", methods=["POST"])
def approve():
    if not session.get("is_admin"):
        return jsonify({"status": "error", "msg": "Não autorizado."}), 403

    data = request.json
    email = data.get("email")

    r = supabase.table("pending_users").select("*").eq("email", email).execute()
    if not r.data:
        return jsonify({"status": "error", "msg": "Usuário não encontrado."})

    pend = r.data[0]

    trial_end = datetime.now(timezone.utc) + timedelta(days=30)

    supabase.table("users").insert({
        "email": pend["email"],
        "password": pend["password"],
        "is_admin": False,
        "plan": "trial",
        "trial_end": trial_end.isoformat(),
        "paid_until": None,
    }).execute()

    supabase.table("pending_users").delete().eq("email", email).execute()

    return jsonify({"status": "ok", "msg": "Usuário aprovado!"})


# ---------------------------------------------------------
# LOGOUT
# ---------------------------------------------------------
@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
