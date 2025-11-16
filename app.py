from flask import Flask, render_template, request, redirect, session, jsonify
from supabase import create_client, Client
from datetime import datetime, timedelta
import random
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = "LanzacaIA2025"

# ==============================
# SUPABASE
# ==============================

SUPABASE_URL = "https://kctzwwzcthjmdgvxuks.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtjdHp3d2N6Y3Roam1kZ3Z4dWtzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjI5ODIwNDYsImV4cCI6MjA3ODU1ODA0Nn0.HafwqrEnJ5Slm3wRg4_KEvGHiTuNJafztVfWbuSZ_84"   # <-- COLOQUE SUA CHAVE

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==============================
# SMTP BREVO (FUNCIONANDO)
# ==============================

SMTP_HOST = "smtp-relay.brevo.com"
SMTP_PORT = 587
SMTP_USER = "9bb9a5001@smtp-brevo.com"  # Login SMTP
SMTP_PASS = "xsmtpsib-6962cab20aa9f005097326b04d6051b45f2fb6ee134ba1f54d982061a7cbeaf5-PnMJHWR2pLnU3Qqq"

def enviar_email_destino(destino, codigo):
    try:
        corpo = f"""
        <h2>Seu código de confirmação</h2>
        <p>Use o código abaixo para concluir seu cadastro:</p>
        <h1>{codigo}</h1>
        <p>Equipe Lanzaca IA ⚡</p>
        """

        msg = MIMEText(corpo, "html")
        msg["Subject"] = "Código de Confirmação - Lanzaca IA"
        msg["From"] = SMTP_USER
        msg["To"] = destino

        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, destino, msg.as_string())
        server.quit()

        print("📧 EMAIL ENVIADO COM SUCESSO PARA:", destino)

    except Exception as e:
        print("❌ ERRO AO ENVIAR EMAIL:", e)


# ==============================
# FUNÇÕES AUXILIARES
# ==============================

def gerar_codigo():
    return random.randint(100000, 999999)


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

    result = supabase.table("users").select("*").eq("email", email).eq("senha", senha).execute()

    if len(result.data) == 0:
        return render_template("index.html", erro="Erro no login.")

    user = result.data[0]

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

    # Verificar se já existe user cadastrado
    existe = supabase.table("users").select("*").eq("email", email).execute()
    if len(existe.data) > 0:
        return render_template("cadastro.html", erro="Email já cadastrado.")

    # Remover pendente antigo
    supabase.table("pending_users").delete().eq("email", email).execute()

    # Criar pendente
    supabase.table("pending_users").insert({
        "nome": nome,
        "celular": celular,
        "email": email,
        "senha": senha
    }).execute()

    # Gerar código
    codigo = gerar_codigo()

    # Registrar código
    supabase.table("confirm_codes").delete().eq("email", email).execute()
    supabase.table("confirm_codes").insert({
        "email": email,
        "codigo": str(codigo)
    }).execute()

    # Enviar email REAL
    enviar_email_destino(email, codigo)

    return redirect(f"/confirmar?email={email}")


# ==============================
# ROTAS – CONFIRMAR CÓDIGO
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

    consulta = supabase.table("confirm_codes").select("*").eq("email", email).eq("codigo", codigo).execute()

    if len(consulta.data) == 0:
        return jsonify({"message": "Código incorreto"}), 401

    # Pegar pendente
    pend = supabase.table("pending_users").select("*").eq("email", email).execute()
    if len(pend.data) == 0:
        return jsonify({"message": "Cadastro não encontrado"}), 404

    user = pend.data[0]

    # Inserir definitivo
    supabase.table("users").insert({
        "nome": user["nome"],
        "celular": user["celular"],
        "email": user["email"],
        "senha": user["senha"],
        "is_admin": False
    }).execute()

    # Limpar registros temporários
    supabase.table("pending_users").delete().eq("email", email).execute()
    supabase.table("confirm_codes").delete().eq("email", email).execute()

    return jsonify({"message": "Conta confirmada com sucesso"}), 200


# ==============================
# DASHBOARD / LOGOUT
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
