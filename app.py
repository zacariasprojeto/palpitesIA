from flask import Flask, render_template, request, redirect, session, jsonify
from supabase import create_client, Client
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = "SUA_CHAVE_SECRETA_AQUI"  # troque se quiser

# ==========================================
# 🔥 CONFIGURAÇÃO SUPABASE
# ==========================================

SUPABASE_URL = "https://tqdhkgpknttphjmfltbg.supabase.co"
SUPABASE_KEY = "SUA_KEY_AQUI"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# 🔥 FUNÇÃO PARA VERIFICAR LOGIN
# ==========================================

def usuario_logado():
    return "usuario" in session

def plano_valido(data_validade):
    if not data_validade:
        return False
    hoje = datetime.now().date()
    validade = datetime.fromisoformat(data_validade).date()
    return validade >= hoje

# ==========================================
# 🔥 ROTA: LOGIN (index)
# ==========================================

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    senha = request.form.get("senha")

    user = supabase.table("usuarios").select("*").eq("email", email).eq("senha", senha).execute()

    if len(user.data) == 0:
        return render_template("index.html", erro="Credenciais inválidas")

    user = user.data[0]

    # Salvando sessão
    session["usuario"] = user["email"]
    session["nome"] = user["nome"]
    session["validade"] = user["validade"]

    # Se não tiver pagamento, manda para pagamento
    if not plano_valido(user["validade"]):
        return redirect("/pagamento")

    return redirect("/dashboard")

# ==========================================
# 🔥 ROTA: CADASTRO
# ==========================================

@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "GET":
        return render_template("cadastro.html")

    # POST – criar usuário
    nome = request.form.get("nome")
    celular = request.form.get("celular")
    email = request.form.get("email")
    senha = request.form.get("senha")

    # Verifica se já existe
    existe = supabase.table("usuarios").select("*").eq("email", email).execute()
    if len(existe.data) > 0:
        return render_template("cadastro.html", erro="E-mail já cadastrado!")

    validade_30_dias = (datetime.now() + timedelta(days=30)).date().isoformat()

    supabase.table("usuarios").insert({
        "nome": nome,
        "celular": celular,
        "email": email,
        "senha": senha,
        "validade": validade_30_dias
    }).execute()

    return redirect("/")

# ==========================================
# 🔥 ROTA: DASHBOARD (protegida)
# ==========================================

@app.route("/dashboard")
def dashboard():
    if not usuario_logado():
        return redirect("/")

    if not plano_valido(session.get("validade")):
        return redirect("/pagamento")

    return render_template("dashboard.html", nome=session.get("nome"))

# ==========================================
# 🔥 ROTA: PAGAMENTO
# ==========================================

@app.route("/pagamento")
def pagamento():
    if not usuario_logado():
        return redirect("/")

    return render_template("pagamento.html")

# ==========================================
# 🔥 LOGOUT
# ==========================================

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ==========================================
# 🔥 RODAR NO RENDER
# ==========================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
