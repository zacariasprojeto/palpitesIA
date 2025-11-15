import os
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from supabase import create_client, Client

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------
app.secret_key = os.getenv("FLASK_SECRET_KEY", "chave_teste")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY or not SUPABASE_SERVICE_KEY:
    raise RuntimeError("Variáveis do Supabase ausentes no Render!")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

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
    data = request.json
    email = data.get("email")
    password = data.get("password")

    result = (
        supabase
        .table("users")
        .select("*")
        .eq("email", email)
        .eq("password", password)
        .execute()
    )

    if not result.data:
        return jsonify({"status": "error", "msg": "Email ou senha incorretos."})

    user = result.data[0]

    session["user"] = user["email"]
    session["is_admin"] = user.get("is_admin", False)

    return jsonify({"status": "ok", "msg": "Login autorizado!", "user": user})

# ---------------------------------------------------------
# REGISTRO
# ---------------------------------------------------------
@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    exists = (
        supabase
        .table("users")
        .select("email")
        .eq("email", email)
        .execute()
    )

    pending = (
        supabase
        .table("pending_users")
        .select("email")
        .eq("email", email)
        .execute()
    )

    if exists.data:
        return jsonify({"status": "error", "msg": "Email já registrado."})

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
@app.route("/api/pending", methods=["GET"])
def pending_users():
    if not session.get("is_admin"):
        return jsonify({"status": "error", "msg": "Não autorizado."})

    result = supabase.table("pending_users").select("*").execute()
    return jsonify({"status": "ok", "pending": result.data})

# ---------------------------------------------------------
# APROVAR
# ---------------------------------------------------------
@app.route("/api/approve", methods=["POST"])
def approve_user():
    if not session.get("is_admin"):
        return jsonify({"status": "error", "msg": "Não autorizado."})

    data = request.json
    email = data.get("email")

    result = (
        supabase
        .table("pending_users")
        .select("*")
        .eq("email", email)
        .execute()
    )

    if not result.data:
        return jsonify({"status": "error", "msg": "Usuário não encontrado."})

    user = result.data[0]

    supabase.table("users").insert({
        "email": user["email"],
        "password": user["password"],
        "is_admin": False
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

# ---------------------------------------------------------
# SERVER
# ---------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
