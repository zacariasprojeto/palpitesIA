from flask import Flask, render_template, request, redirect, session
from supabase import create_client, Client
from datetime import datetime, timedelta
import random

app = Flask(__name__)
app.secret_key = "LanzacaIA2025"

SUPABASE_URL = "https://tqdhkgpknttphjmfltbg.supabase.co"
SUPABASE_KEY = "SUA_KEY_AQUI"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ===========================
# FUNÇÕES
# ===========================

def gerar_codigo():
    return random.randint(100000, 999999)

def enviar_email_fake(email, codigo):
    print(f"\n====== CODIGO DE CONFIRMAÇÃO ======")
    print(f"Email: {email}")
    print(f"Código: {codigo}")
    print("===================================\n")


# ===========================
# ROTAS
# ===========================

@app.route("/")
def index():
    return render_template("index.html")


# LOGIN
@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    senha = request.form.get("senha")

    dados = supabase.table("users").select("*").eq("email", email).eq("senha", senha).execute()

    if len(dados.data) == 0:
        return render_template("index.html", erro="Credenciais inválidas")

    user = dados.data[0]

    session["email"] = user["email"]
    session["nome"] = user["nome"]

    return redirect("/dashboard")



# CADASTRO
@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "GET":
        return render_template("cadastro.html")

    nome = request.form.get("nome")
    celular = request.form.get("celular")
    email = request.form.get("email")
    senha = request.form.get("senha")

    existe = supabase.table("users").select("*").eq("email", email).execute()
    if len(existe.data) > 0:
        return render_template("cadastro.html", erro="Email já cadastrado")

    codigo = gerar_codigo()

    # salva usuário temporário
    supabase.table("pending_users").insert({
        "nome": nome,
        "celular": celular,
        "email": email,
        "senha": senha
    }).execute()

    # salva código
    supabase.table("confirm_codes").insert({
        "email": email,
        "codigo": codigo
    }).execute()

    enviar_email_fake(email, codigo)

    return redirect(f"/confirmar?email={email}")


# TELA PARA DIGITAR CÓDIGO
@app.route("/confirmar", methods=["GET", "POST"])
def confirmar():
    email = request.args.get("email")

    if request.method == "GET":
        return render_template("confirmar.html", email=email)

    codigo_digitado = request.form.get("codigo")
    email = request.form.get("email")

    dados = supabase.table("confirm_codes").select("*").eq("email", email).eq("codigo", codigo_digitado).execute()

    if len(dados.data) == 0:
        return render_template("confirmar.html", email=email, erro="Código inválido")

    # buscar usuario pendente
    pend = supabase.table("pending_users").select("*").eq("email", email).execute()
    user = pend.data[0]

    # mover para tabela final
    supabase.table("users").insert(user).execute()

    # remover temporários
    supabase.table("pending_users").delete().eq("email", email).execute()
    supabase.table("confirm_codes").delete().eq("email", email).execute()

    return redirect("/")


# DASHBOARD
@app.route("/dashboard")
def dashboard():
    if "email" not in session:
        return redirect("/")

    return render_template("dashboard.html", nome=session["nome"])


# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
