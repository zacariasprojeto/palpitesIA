from flask import Flask, render_template, request, redirect, session, jsonify
from supabase import create_client, Client
from datetime import datetime, timedelta
import random
import smtplib

app = Flask(__name__)
app.secret_key = "LanzacaIA2025"

# ==============================
# SUPABASE
# ==============================

SUPABASE_URL = "https://tqdhkgpknttphjmfltbg.supabase.co"
SUPABASE_KEY = "SUA_KEY_AQUI"  # <<< COLOQUE SUA CHAVE AQUI

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ==============================
# FUNÇÕES
# ==============================

def gerar_codigo():
    """Gera um código de 6 dígitos"""
    return random.randint(100000, 999999)

def enviar_email(email, codigo):
    """FAKE — Apenas printa o código no terminal (Render mostra nos logs)."""
    print("\n==============================")
    print("⚡ CÓDIGO DE CONFIRMAÇÃO LANZACA IA ⚡")
    print(f"Email: {email}")
    print(f"Código: {codigo}")
    print("==============================\n")


# ==============================
# ROTAS – LOGIN
# ==============================

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    senha = request.form.get("senha")

    dados = supabase.table("users").select("*").eq("email", email).eq("senha", senha).execute()

    if len(dados.data) == 0:
        return render_template("index.html", erro="Erro no login.")

    user = dados.data[0]

    session["email"] = user["email"]
    session["nome"] = user["nome"]

    return redirect("/dashboard")


# ==============================
# ROTAS – CADASTRO
# ==============================

@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "GET":
        return render_template("cadastro.html")

    nome = request.form.get("nome")
    celular = request.form.get("celular")
    email = request.form.get("email")
    senha = request.form.get("senha")

    # Existe usuário definitivo?
    existe = supabase.table("users").select("*").eq("email", email).execute()
    if len(existe.data) > 0:
        return render_template("cadastro.html", erro="Este email já está cadastrado.")

    # Existe pendente?
    pend = supabase.table("pending_users").select("*").eq("email", email).execute()
    if len(pend.data) > 0:
        supabase.table("pending_users").delete().eq("email", email).execute()

    # Salvar pendente
    supabase.table("pending_users").insert({
        "nome": nome,
        "celular": celular,
        "email": email,
        "senha": senha
    }).execute()

    # Gerar código
    codigo = gerar_codigo()

    # Registrar código
    supabase.table("confirm_codes").insert({
        "email": email,
        "codigo": codigo
    }).execute()

    # Enviar (fake)
    enviar_email(email, codigo)

    # Redirecionar para a página de confirmação
    return redirect(f"/confirmar?email={email}")


# ==============================
# ROTAS – CONFIRMAÇÃO DE CÓDIGO
# ==============================

@app.route("/confirmar", methods=["GET"])
def confirmar_tela():
    email = request.args.get("email")
    return render_template("confirmar.html", email=email)


@app.route("/api/confirmar", methods=["POST"])
def api_confirmar():
    dados = request.get_json()
    codigo = dados.get("codigo")
    email = dados.get("email")

    if not codigo or not email:
        return jsonify({"message": "Dados incompletos"}), 400

    consulta = supabase.table("confirm_codes").select("*").eq("email", email).eq("codigo", codigo).execute()

    if len(consulta.data) == 0:
        return jsonify({"message": "Código incorreto"}), 401

    # Buscar pendente
    pend = supabase.table("pending_users").select("*").eq("email", email).execute()
    if len(pend.data) == 0:
        return jsonify({"message": "Nenhum cadastro pendente encontrado"}), 404

    usuario = pend.data[0]

    # Salvar em users (definitivo)
    supabase.table("users").insert({
        "nome": usuario["nome"],
        "celular": usuario["celular"],
        "email": usuario["email"],
        "senha": usuario["senha"],
        "is_admin": False
    }).execute()

    # Remover pendente e código usado
    supabase.table("pending_users").delete().eq("email", email).execute()
    supabase.table("confirm_codes").delete().eq("email", email).execute()

    return jsonify({"message": "Confirmado com sucesso"}), 200


# ==============================
# ROTAS – DASHBOARD / LOGOUT
# ==============================

@app.route("/dashboard")
def dashboard():
    if "email" not in session:
        return redirect("/")
    return render_template("dashboard.html", nome=session["nome"])


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ==============================
# RENDER
# ==============================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
