from flask import Flask, render_template, request, redirect, session
from supabase import create_client, Client
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "LanzacaIA2025"

# ==============================
# SUPABASE
# ==============================

SUPABASE_URL = "https://tqdhkgpknttphjmfltbg.supabase.co"
SUPABASE_KEY = "SUA_KEY_AQUI"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==============================
# FUNÇÕES
# ==============================

def usuario_logado():
    return "email" in session

def plano_valido(data):
    if not data:
        return False
    hoje = datetime.now().date()
    validade = datetime.fromisoformat(data).date()
    return validade >= hoje

# ==============================
# ROTAS
# ==============================

# LOGIN (INDEX)
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    senha = request.form.get("senha")

    dados = supabase.table("usuarios").select("*").eq("email", email).eq("senha", senha).execute()

    if len(dados.data) == 0:
        return render_template("index.html", erro="Credenciais inválidas")

    user = dados.data[0]

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

    existe = supabase.table("usuarios").select("*").eq("email", email).execute()
    if len(existe.data) > 0:
        return render_template("cadastro.html", erro="Email já cadastrado")

    validade = (datetime.now() + timedelta(days=30)).date().isoformat()

    supabase.table("usuarios").insert({
        "nome": nome,
        "celular": celular,
        "email": email,
        "senha": senha,
        "validade": validade
    }).execute()

    return redirect("/")

# DASHBOARD (PROTEGIDA)
@app.route("/dashboard")
def dashboard():
    if not usuario_logado():
        return redirect("/")

    if not plano_valido(session["validade"]):
        return redirect("/pagamento")

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

# RENDER
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
