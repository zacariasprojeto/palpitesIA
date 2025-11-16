import os
import json
from datetime import datetime, date

from flask import Flask, render_template, request, jsonify, redirect
from flask_cors import CORS
from supabase import create_client, Client
import requests

# -----------------------------------------------------------
# CONFIGURAÇÃO SUPABASE
# -----------------------------------------------------------

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  # usa SERVICE_KEY do Render

supabase: Client | None = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase conectado.")
    except Exception as e:
        print("❌ Erro ao conectar Supabase:", e)
else:
    print("❌ Configure SUPABASE_URL e SUPABASE_SERVICE_KEY nas variáveis de ambiente.")

# -----------------------------------------------------------
# CONFIGURAÇÃO FLASK
# -----------------------------------------------------------

app = Flask(__name__, template_folder="templates")
CORS(app)


# -----------------------------------------------------------
# HELPERS
# -----------------------------------------------------------

def parse_date_str(d):
    """
    Converte string (YYYY-MM-DD ou ISO) para date.
    Se não conseguir, retorna None.
    """
    if not d:
        return None
    try:
        # caso venha como '2025-11-16'
        if isinstance(d, date):
            return d
        if isinstance(d, datetime):
            return d.date()
        s = str(d)
        # remove parte de hora, se vier tipo '2025-11-16T00:00:00+00:00'
        s = s.split("T")[0]
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


# -----------------------------------------------------------
# ROTA: PÁGINA INICIAL (TELA DE LOGIN)
# -----------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


# -----------------------------------------------------------
# ROTA: DASHBOARD (APÓS LOGIN OK)
# Aqui você coloca a interface igual às imagens, depois.
# Por enquanto, só um "placeholder" pra saber que logou.
# -----------------------------------------------------------

@app.route("/dashboard")
def dashboard():
    return "<h1>Lanzaca IA - Dashboard</h1><p>Login realizado com sucesso.</p>"


# -----------------------------------------------------------
# ROTA: CADASTRO (A PÁGINA /cadastro QUE VOCÊ VAI FAZER DEPOIS)
# -----------------------------------------------------------

@app.route("/cadastro")
def cadastro_page():
    # Quando tiver o cadastro.html, coloque na pasta templates
    # e descomente abaixo:
    # return render_template("cadastro.html")
    return "<h1>Página de cadastro em desenvolvimento</h1>"


# -----------------------------------------------------------
# API: LOGIN
# Regras:
# - Se admin (is_admin = true) -> entra sempre (acesso vitalício)
# - Se usuário normal:
#     - plan = 'trial' e trial_end >= hoje -> entra
#     - plan = 'paid' e paid_until >= hoje -> entra
#     - senão -> 403 com mensagem para pagamento
# -----------------------------------------------------------

@app.route("/api/login", methods=["POST"])
def api_login():
    if supabase is None:
        return jsonify({"message": "Backend sem conexão com Supabase."}), 500

    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    # aceita tanto "senha" quanto "password" vindo do front
    password_input = data.get("senha") or data.get("password") or ""

    if not email or not password_input:
        return jsonify({"message": "Informe email e senha."}), 400

    try:
        # Busca usuário pelo email
        res = supabase.table("users").select("*").eq("email", email).execute()
        rows = res.data or []
    except Exception as e:
        print("❌ Erro Supabase na consulta de usuário:", e)
        return jsonify({"message": "Erro ao acessar banco de dados."}), 500

    if not rows:
        # nenhum usuário com esse email
        return jsonify({"message": "Credenciais inválidas."}), 401

    user = rows[0]

    # coluna de senha: tenta 'password', se não existir tenta 'senha'
    senha_armazenada = user.get("password") or user.get("senha")
    if not senha_armazenada or senha_armazenada != password_input:
        return jsonify({"message": "Credenciais inválidas."}), 401

    # Se for admin -> acesso ilimitado
    is_admin = bool(user.get("is_admin"))
    if is_admin:
        return jsonify({
            "message": "Login efetuado (admin).",
            "redirect": "/dashboard",
            "user": {
                "email": user.get("email"),
                "is_admin": True
            }
        }), 200

    # Usuário normal -> checa plano e datas
    today = datetime.utcnow().date()
    plan = (user.get("plan") or "trial").lower()

    # Datas possíveis
    trial_str = user.get("trial_end") or user.get("trial_ate")
    paid_str = user.get("paid_until") or user.get("pago_ate")

    trial_end = parse_date_str(trial_str)
    paid_until = parse_date_str(paid_str)

    if plan == "trial":
        # Se não tiver trial_end, por segurança vamos bloquear
        if not trial_end or trial_end < today:
            return jsonify({
                "message": "Seu período de teste grátis acabou. Realize o pagamento para continuar.",
                "reason": "trial_expired"
            }), 403
    elif plan == "paid":
        if not paid_until or paid_until < today:
            return jsonify({
                "message": "Seu plano pago expirou. Realize o pagamento para renovar o acesso.",
                "reason": "paid_expired"
            }), 403
    else:
        # plano desconhecido -> bloquear também
        return jsonify({
            "message": "Seu plano não está configurado corretamente. Fale com o suporte.",
            "reason": "plan_invalid"
        }), 403

    # Se chegou aqui -> acesso liberado
    return jsonify({
        "message": "Login efetuado com sucesso.",
        "redirect": "/dashboard",
        "user": {
            "email": user.get("email"),
            "is_admin": False,
            "plan": plan,
            "trial_end": trial_str,
            "paid_until": paid_str
        }
    }), 200


# -----------------------------------------------------------
# ROTA /run-job (CRON) – AQUI VOCÊ PODE ENCAIXAR SUA LÓGICA DE PALPITES
# POR ENQUANTO VOU SÓ RETORNAR UMA MENSAGEM
# -----------------------------------------------------------

@app.route("/run-job")
def run_cron_job_endpoint():
    return "Cron job em desenvolvimento.", 200


# -----------------------------------------------------------
# MAIN LOCAL
# -----------------------------------------------------------

if __name__ == "__main__":
    # para rodar localmente: python app.py
    app.run(host="0.0.0.0", port=5000, debug=True)
