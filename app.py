import os
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from supabase import create_client, Client

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

app.secret_key = os.getenv("FLASK_SECRET_KEY", "chave_teste")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

# cliente certo (anon)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


# =========================================================
@app.route("/")
def index():
    return render_template("index.html")


# =========================================================
# LOGIN
# =========================================================
@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    result = (
        supabase.table("users")
        .select("*")
        .eq("email", email)
        .eq("password", password)
        .maybe_single()
        .execute()
    )

    user = result.data

    if not user:
        return jsonify({"status": "error", "msg": "Email ou senha incorretos."})

    session["user"] = user["email"]
    session["is_admin"] = user.get("is_admin", False)

    return jsonify({"status": "ok", "user": user})


# =========================================================
# REGISTRO
# =========================================================
@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    exists = supabase.table("users").select("email").eq("email", email).execute()
    pending = supabase.table("pending_users").select("email").eq("email", email).execute()

    if exists.data:
        return jsonify({"status": "error", "msg": "Email já usado."})

    if pending.data:
        return jsonify({"status": "error", "msg": "Cadastro já solicitado."})

    supabase.table("pending_users").insert({
        "email": email,
        "password": password
    }).execute()

    return jsonify({"status": "ok", "msg": "Solicitação enviada!"})


# =========================================================
# LISTAR PENDENTES
# =========================================================
@app.route("/api/pending", methods=["GET"])
def pending_users():
    if not session.get("is_admin"):
        return jsonify({"status": "error", "msg": "Não autorizado."})

    rows = supabase.table("pending_users").select("*").execute()
    return jsonify({"status": "ok", "pending": rows.data})


# =========================================================
# APROVAR PENDENTE
# =========================================================
@app.route("/api/approve", methods=["POST"])
def approve_user():
    if not session.get("is_admin"):
        return jsonify({"status": "error", "msg": "Não autorizado."})

    email = request.json.get("email")

    res = supabase.table("pending_users").select("*").eq("email", email).maybe_single().execute()

    pend = res.data
    if not pend:
        return jsonify({"status": "error", "msg": "Não encontrado."})

    supabase.table("users").insert({
        "email": pend["email"],
        "password": pend["password"],
        "is_admin": False
    }).execute()

    supabase.table("pending_users").delete().eq("email", email).execute()

    return jsonify({"status": "ok", "msg": "Aprovado!"})


# =========================================================
@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"status": "ok"})


# =========================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
