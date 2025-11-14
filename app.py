import os, json
from flask import Flask, render_template, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
import requests
from urllib.parse import quote_plus

# Config via env
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
FLASK_SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "change-me")

if not SUPABASE_URL:
    raise RuntimeError("Set SUPABASE_URL in env")
# service key may be required for writes/approvals; we check later when used

REST_BASE = SUPABASE_URL.rstrip("/") + "/rest/v1"
HEADERS_ANON = {
    "apikey": SUPABASE_ANON_KEY,
    "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    "Content-Type": "application/json"
}
HEADERS_SERVICE = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    "Content-Type": "application/json"
}

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = FLASK_SECRET_KEY

def supabase_get(table, params=None, headers=HEADERS_ANON):
    url = f"{REST_BASE}/{table}"
    if params:
        url += "?" + params
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()

def supabase_post(table, payload, headers=HEADERS_SERVICE):
    url = f"{REST_BASE}/{table}"
    r = requests.post(url, headers=headers, data=json.dumps(payload))
    r.raise_for_status()
    return r.json()

def supabase_patch(table, payload, params, headers=HEADERS_SERVICE):
    url = f"{REST_BASE}/{table}?{params}"
    r = requests.patch(url, headers=headers, data=json.dumps(payload))
    r.raise_for_status()
    return r

@app.route("/")
def index():
    # inject anon key + url to the page (frontend needs anon key to read bets)
    return render_template("index.html",
                           SUPABASE_URL=SUPABASE_URL,
                           SUPABASE_ANON_KEY=SUPABASE_ANON_KEY)

# Login: only approved users can log in
@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(force=True)
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return jsonify({"status":"error","msg":"email and password required"}), 400

    params = f"email=eq.{quote_plus(email)}"
    users = supabase_get("users", params=params)
    if not users:
        return jsonify({"status":"error","msg":"user not found"}), 404
    user = users[0]
    if not user.get("approved"):
        return jsonify({"status":"error","msg":"Cadastro pendente. Aguarde aprovação."}), 403
    pwdhash = user.get("password_hash")
    if not pwdhash or not check_password_hash(pwdhash, password):
        return jsonify({"status":"error","msg":"email or password incorrect"}), 401

    session["user"] = {"id": user.get("id"), "email": user.get("email"), "is_admin": user.get("is_admin", False)}
    return jsonify({"status":"ok","user": session["user"]})

# Register (create user pending approval) — requires service key (server-side writes)
@app.route("/api/register", methods=["POST"])
def api_register():
    if not SUPABASE_SERVICE_KEY:
        return jsonify({"status":"error","msg":"Service key not configured"}), 500
    data = request.get_json(force=True)
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return jsonify({"status":"error","msg":"email and password required"}), 400

    # check exists
    params = f"email=eq.{quote_plus(email)}"
    existing = supabase_get("users", params=params)
    if existing:
        return jsonify({"status":"error","msg":"User already exists"}), 409

    pwdhash = generate_password_hash(password)
    payload = [{
        "email": email,
        "password_hash": pwdhash,
        "is_admin": False,
        "approved": False
    }]
    supabase_post("users", payload)
    return jsonify({"status":"ok","msg":"Cadastro pendente. Aguarde aprovação do administrador."})

# Admin: list pending users
@app.route("/api/pending_users", methods=["GET"])
def api_pending_users():
    u = session.get("user")
    if not u or not u.get("is_admin"):
        return jsonify({"status":"error","msg":"unauthorized"}), 401
    users = supabase_get("users", params="approved=eq.false")
    return jsonify({"status":"ok","pending": users})

# Admin: approve user
@app.route("/api/approve_user", methods=["POST"])
def api_approve_user():
    u = session.get("user")
    if not u or not u.get("is_admin"):
        return jsonify({"status":"error","msg":"unauthorized"}), 401
    if not SUPABASE_SERVICE_KEY:
        return jsonify({"status":"error","msg":"service key not configured"}), 500
    data = request.get_json(force=True)
    email = data.get("email")
    if not email:
        return jsonify({"status":"error","msg":"email required"}), 400
    params = f"email=eq.{quote_plus(email)}"
    resp = supabase_patch("users", {"approved": True}, params=params)
    if resp.status_code in (200,204):
        return jsonify({"status":"ok","msg":"Usuário aprovado"})
    return jsonify({"status":"error","msg":"Falha ao aprovar"}), 500

@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.pop("user", None)
    return jsonify({"status":"ok"})

@app.route("/api/session", methods=["GET"])
def api_session():
    return jsonify({"user": session.get("user")})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
