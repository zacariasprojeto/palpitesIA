import os
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, request, jsonify, session, redirect
from supabase import create_client, Client
import random

# =========================================================
# CONFIGURAÇÃO FLASK / SUPABASE
# =========================================================
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.getenv("FLASK_SECRET_KEY", "chave_teste")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise RuntimeError("SUPABASE_URL ou SUPABASE_SERVICE_KEY não configurados!")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================

def parse_ts(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except:
        return None


def user_is_active(usuario):
    """Valida se o usuário tem acesso liberado."""
    if not usuario:
        return False, "not_found"

    if usuario.get("confirmado") is False:
        return False, "not_confirmed"

    if usuario["plano"] == "trial":
        expira = parse_ts(usuario["expira_em"])
        if not expira or expira < datetime.now(timezone.utc):
            return False, "trial_expired"
        return True, None

    if usuario["plano"] == "pago":
        expira = parse_ts(usuario["expira_em"])
        if not expira or expira < datetime.now(timezone.utc):
            return False, "paid_expired"
        return True, None

    return False, "unknown_plan"


def enviar_codigo(email, codigo):
    """Simulando envio de email (Render bloqueia SMTP)."""
    print(f"=== Código enviado para {email}: {codigo} ===")


# =========================================================
# ROTAS DE PÁGINAS
# =========================================================

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
    email = request.args.get("email")
    return render_template("confirmar.html", email=email)


@app.route("/dashboard")
def dashboard_page():
    if "user_email" not in session:
        return redirect("/login")
    return render_template("painel.html", nome=session.get("user_nome"))


@app.route("/top3")
def top3_page():
    if "user_email" not in session:
        return redirect("/login")
    return render_template("top3.html")


# =========================================================
# API: CADASTRO
# =========================================================

@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.json or {}

    nome = data.get("nome", "").strip()
    email = data.get("email", "").strip().lower()
    senha = data.get("senha", "").strip()
    cpf = data.get("cpf", "").strip()
    celular = data.get("celular", "").strip()
    ip = request.remote_addr

    # Remover caracteres do celular
    celular = "".join([c for c in celular if c.isdigit()])

    # VERIFICA SE JÁ EXISTE EMAIL / CPF / CELULAR / IP
    checks = supabase.table("usuarios").select("*").or_(
        f"email.eq.{email},cpf.eq.{cpf},celular.eq.{celular},ip.eq.{ip}"
    ).execute()

    if checks.data:
        return jsonify({"status": "error", "msg": "Você já possui cadastro ou já usou o período de teste."})

    # Gera código de confirmação
    codigo = str(random.randint(100000, 999999))

    supabase.table("usuarios").insert({
        "nome": nome,
        "email": email,
        "senha": senha,
        "cpf": cpf,
        "celular": celular,
        "ip": ip,
        "codigo_confirmacao": codigo,
        "confirmado": False,
        "plano": "trial",
        "expira_em": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    }).execute()

    enviar_codigo(email, codigo)

    return jsonify({"status": "ok", "redirect": f"/confirmar?email={email}"})


# =========================================================
# API: CONFIRMAR CÓDIGO
# =========================================================

@app.route("/api/confirmar", methods=["POST"])
def api_confirmar():
    data = request.json or {}

    email = data.get("email")
    codigo = data.get("codigo")

    res = supabase.table("usuarios").select("*").eq("email", email).execute()

    if not res.data:
        return jsonify({"status": "error", "msg": "Usuário não encontrado."})

    usuario = res.data[0]

    if usuario["codigo_confirmacao"] != codigo:
        return jsonify({"status": "error", "msg": "Código incorreto."})

    supabase.table("usuarios").update({"confirmado": True}).eq("email", email).execute()

    return jsonify({"status": "ok", "redirect": "/login"})


# =========================================================
# API: LOGIN
# =========================================================

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.json or {}

    email = data.get("email", "").strip().lower()
    senha = data.get("senha", "").strip()

    res = supabase.table("usuarios").select("*").eq("email", email).eq("senha", senha).execute()

    if not res.data:
        return jsonify({"status": "error", "msg": "Credenciais incorretas."})

    usuario = res.data[0]

    ativo, motivo = user_is_active(usuario)

    if not ativo:
        return jsonify({
            "status": "blocked",
            "reason": motivo,
            "msg": "Seu acesso está bloqueado. Faça o pagamento para continuar."
        })

    # Login OK
    session["user_email"] = usuario["email"]
    session["user_nome"] = usuario["nome"]

    return jsonify({"status": "ok", "redirect": "/dashboard"})


# =========================================================
# API: LOGOUT
# =========================================================

@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"status": "ok", "redirect": "/login"})


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
