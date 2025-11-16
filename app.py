from flask import Flask, render_template, request, redirect, session
from supabase import create_client, Client
from datetime import datetime, timedelta
import random

app = Flask(__name__)
app.secret_key = "LanzacaIA2025"

SUPABASE_URL = "https://tqdhkgpknttphjmfltbg.supabase.co"
SUPABASE_KEY = "SUA_KEY_AQUI"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def usuario_logado():
    return "email" in session

def plano_valido(data):
    if not data:
        return False
    hoje = datetime.now().date()
    validade = datetime.fromisoformat(data).date()
    return validade >= hoje

# ==============================
# TELAS
# ==============================

@app.route("/", methods=["GET"])
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

    if not user.get("confirmado", False):
        return render_template("index.html", erro="Confirme seu e-mail antes de entrar.")

    session["email"] = user["email"]
    session["nome"] = user["nome"]
    session["validade"] = user["validade"]

    if not plano_valido(user["validade"]):
        return redirect("/pagamento")

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

    validade = (datetime.now() + timedelta(days=30)).date().isoformat()

    supabase.table("users").insert({
        "nome": nome,
        "celular": celular,
        "email": email,
        "senha": senha,
        "validade": validade,
        "confirmado": False
    }).execute()

    # GERAR E SALVAR CÓDIGO
    codigo = str(random.randint(100000, 999999))

    supabase.table("confirm_codes").insert({
        "email": email,
        "codigo": codigo
    }).execute()

    print(f"⚠ Código de confirmação: {codigo}")  # (mostrar no log)

    return redirect("/confirmar?email=" + email)

# TELA PARA DIGITAR O CÓDIGO
@app.route("/confirmar")
def confirmar():
    email = request.args.get("email")
    return render_template("confirmar.html", email=email)

# VALIDAR CÓDIGO
@app.route("/validar_codigo", methods=["POST"])
def validar_codigo():
    email = request.form.get("email")
    codigo = request.form.get("codigo")

    dados = supabase.table("confirm_codes").select("*").eq("email", email).eq("codigo", codigo).execute()

    if len(dados.data) == 0:
        return render_template("confirmar.html", email=email, erro="Código inválido")

    supabase.table("users").update({"confirmado": True}).eq("email", email).execute()

    # remover código usado
    supabase.table("confirm_codes").delete().eq("email", email).execute()

    return render_template("confirmar.html", email=email, sucesso="Conta confirmada! Agora você pode entrar.")

# DASHBOARD
@app.route("/dashboard")
def dashboard():
    if not usuario_logado():
        return redirect("/")
    return render_template("dashboard.html", nome=session["nome"])

# PAGAMENTO
@app.route("/pagamento")
def pagamento():
    if not usuario_logado():
        return redirect("/")
    return render_template("pagamento.html")

# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
