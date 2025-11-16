import os
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template
from supabase import create_client, Client

app = Flask(__name__)

# ============================================================
# FUNÇÃO ESSENCIAL — CRIA O CLIENTE SUPABASE SEM BUGS
# ============================================================
def get_supabase():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")  # service role

    if not url or not key:
        raise Exception("❌ SUPABASE_URL ou SUPABASE_SERVICE_KEY não estão configurados!")

    return create_client(url, key)

# ============================================================
# FUNÇÃO — VERIFICA SE O ACESSO ESTÁ ATIVO  
# (admin é ilimitado automaticamente)
# ============================================================
def verificar_acesso(user):
    if user["is_admin"]:
        return True  # admin tem acesso vitalício

    hoje = datetime.utcnow()

    # Trial ainda ativo?
    if user["trial_end"] and hoje <= datetime.fromisoformat(user["trial_end"]):
        return True

    # Plano pago ainda válido?
    if user["paid_until"] and hoje <= datetime.fromisoformat(user["paid_until"]):
        return True

    return False


# ============================================================
# ROTA — PÁGINA PRINCIPAL (LOGIN)
# ============================================================
@app.route("/")
def index():
    return render_template("index.html")


# ============================================================
# ROTA — PÁGINA DE CADASTRO
# ============================================================
@app.route("/cadastro")
def cadastro_page():
    return render_template("cadastro.html")


# ============================================================
# ROTA — API DE CADASTRO DE NOVO USUÁRIO
# ============================================================
@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json()
    nome = data.get("nome")
    email = data.get("email")
    celular = data.get("celular")
    password = data.get("password")

    supabase = get_supabase()

    # Verifica se e-mail já existe
    existe = supabase.table("users").select("*").eq("email", email).execute()
    if existe.data:
        return jsonify({"error": "Email já cadastrado."}), 400

    # Cria trial de 30 dias
    trial = datetime.utcnow() + timedelta(days=30)

    supabase.table("users").insert({
        "nome": nome,
        "email": email,
        "password": password,
        "celular": celular,
        "is_admin": False,
        "plan": "trial",
        "trial_end": trial.isoformat(),
        "paid_until": None
    }).execute()

    return jsonify({"success": True})


# ============================================================
# ROTA — API DE LOGIN
# ============================================================
@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    supabase = get_supabase()

    user = supabase.table("users").select("*").eq("email", email).eq("password", password).execute()

    if not user.data:
        return jsonify({"error": "Credenciais inválidas"}), 401

    user = user.data[0]

    # Verifica permissão
    if not verificar_acesso(user):
        return jsonify({
            "error": "acesso_bloqueado",
            "pix": os.environ.get("PIX_KEY", "chave não configurada"),
            "mensagem": "Seu acesso expirou. Faça o pagamento para continuar."
        }), 403

    return jsonify({
        "success": True,
        "user": {
            "id": user["id"],
            "nome": user["nome"],
            "email": user["email"],
            "is_admin": user["is_admin"]
        }
    })


# ============================================================
# START
# ============================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
