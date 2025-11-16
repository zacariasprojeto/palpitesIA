import os
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template
from supabase import create_client, Client
from flask_cors import CORS

# --------------------------------------------
# CONFIGURAÇÃO
# --------------------------------------------
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
CORS(app)

PIX_KEY = "SEU PIX AQUI"

# --------------------------------------------
# FUNÇÃO – VERIFICAR ACESSO (trial ou pago)
# --------------------------------------------
def verificar_acesso(user):
    agora = datetime.utcnow()

    # Trial ativo?
    if user["trial_end"]:
        trial = datetime.fromisoformat(user["trial_end"].replace("Z", ""))
        if agora < trial:
            return True
    
    # Plano pago ativo?
    if user["paid_until"]:
        pago = datetime.fromisoformat(user["paid_until"].replace("Z", ""))
        if agora < pago:
            return True

    return False


# --------------------------------------------
# ROTA: TELA PRINCIPAL
# --------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


# --------------------------------------------
# ROTA: TELA DE CADASTRO
# --------------------------------------------
@app.route("/cadastro")
def cadastro():
    return render_template("cadastro.html")


# --------------------------------------------
# ROTA: API DE CADASTRO
# --------------------------------------------
@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    nome = data.get("nome")
    email = data.get("email")
    celular = data.get("celular")
    password = data.get("password")

    # Verifica se já existe
    existe = supabase.table("users").select("*").eq("email", email).execute()

    if existe.data:
        return jsonify({"error": "Email já cadastrado."}), 400

    trial = datetime.utcnow() + timedelta(days=30)

    supabase.table("users").insert({
        "nome": nome,
        "email": email,
        "password": password,
        "celular": celular,
        "plan": "trial",
        "trial_end": trial.isoformat(),
        "paid_until": None,
        "is_admin": False
    }).execute()

    return jsonify({"success": True})


# --------------------------------------------
# ROTA: LOGIN
# --------------------------------------------
@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    user = supabase.table("users").select("*").eq("email", email).eq("password", password).execute()

    if not user.data:
        return jsonify({"error": "Credenciais inválidas"}), 401

    user = user.data[0]

    # Acesso expirado?
    if not verificar_acesso(user):
        return jsonify({
            "error": "acesso_bloqueado",
            "pix": PIX_KEY,
            "mensagem": "Seu acesso expirou. Faça o pagamento para continuar."
        }), 403

    return jsonify({
        "success": True,
        "redirect": "https://lanzacaia.vercel.app/dashboard",
        "user": {
            "id": user["id"],
            "nome": user["nome"],
            "email": user["email"],
            "is_admin": user["is_admin"]
        }
    })


# --------------------------------------------
# ROTA: HEALTH CHECK (Render não dormir)
# --------------------------------------------
@app.route("/health")
def health():
    return "OK", 200


# --------------------------------------------
# EXECUTAR
# --------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
