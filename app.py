import os
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, request, jsonify, session, redirect
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

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise RuntimeError("Variáveis SUPABASE_URL e SUPABASE_SERVICE_KEY não configuradas")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


# ---------------------------------------------------------
# FUNÇÕES AUXILIARES
# ---------------------------------------------------------
def parse_ts(value):
    """Converte timestamp para datetime."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except:
        return None


def user_is_active(user: dict):
    """Valida plano do usuário."""
    if not user:
        return False, "not_found"

    if user.get("is_admin"):
        return True, None

    plano = user.get("plan", "trial")
    trial_end = parse_ts(user.get("trial_end"))
    paid_until = parse_ts(user.get("paid_until"))
    now = datetime.now(timezone.utc)

    if plano == "trial":
        if not trial_end or trial_end < now:
            return False, "trial_expired"
        return True, None

    if plano == "paid":
        if not paid_until or paid_until < now:
            return False, "payment_expired"
        return True, None

    return False, "unknown_plan"


# ---------------------------------------------------------
# PÁGINAS
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

@app.route("/planos")
def planos_page():
    return render_template("planos.html")

@app.route("/pagamento")
def pagamento_page():
    return render_template("pagamento.html")

@app.route("/pagamento_confirmado")
def pagamento_confirmado_page():
    return render_template("pagamento_confirmado.html")

@app.route("/bloqueado")
def bloqueado_page():
    return render_template("bloqueado.html")

@app.route("/palpites")
def palpites_page():
    return render_template("top_palpites.html")

@app.route("/top3")
def top3_page():
    return render_template("top3.html")


# ---------------------------------------------------------
# API: LOGIN
# ---------------------------------------------------------
@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.json or {}
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    res = (
        supabase.table("users")
        .select("*")
        .eq("email", email)
        .eq("password", password)
        .execute()
    )

    if not res.data:
        return jsonify({"status": "error", "msg": "Credenciais inválidas."})

    user = res.data[0]

    ativo, motivo = user_is_active(user)
    if not ativo:
        return jsonify({
            "status": "blocked",
            "reason": motivo
        })

    session["user"] = user["email"]
    session["is_admin"] = user.get("is_admin", False)

    return jsonify({"status": "ok"})


# ---------------------------------------------------------
# API: REGISTRO
# ---------------------------------------------------------
@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.json or {}

    nome = data.get("nome", "").strip()
    cpf = data.get("cpf", "").strip()
    telefone = data.get("telefone", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    # Verifica duplicados
    exists = supabase.table("users").select("email").eq("email", email).execute()
    if exists.data:
        return jsonify({"status": "error", "msg": "Email já registrado."})

    exists_cpf = supabase.table("users").select("cpf").eq("cpf", cpf).execute()
    if exists_cpf.data:
        return jsonify({"status": "error", "msg": "CPF já está em uso."})

    # Salvar no pending_users
    supabase.table("pending_users").insert({
        "nome": nome,
        "cpf": cpf,
        "telefone": telefone,
        "email": email,
        "password": password
    }).execute()

    return jsonify({"status": "ok"})


# ---------------------------------------------------------
# LOGOUT
# ---------------------------------------------------------
@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"status": "ok"})


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
