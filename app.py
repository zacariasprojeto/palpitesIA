from flask import Flask, render_template, request, redirect, session, jsonify
from supabase import create_client, Client
from datetime import datetime
import random
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = "LanzacaIA2025"

# ============================================
# SUPABASE CONFIGURAÇÃO
# ============================================

SUPABASE_URL = "https://kctzwwzcthjmdgvxuks.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtjdHp3d2N6Y3Roam1kZ3Z4dWtzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjI5ODIwNDYsImV4cCI6MjA3ODU1ODA0Nn0.HafwqrEnJ5Slm3wRg4_KEvGHiTuNJafztVfWbuSZ_84"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ============================================
# FUNÇÕES ÚTEIS
# ============================================

def gerar_codigo():
    return random.randint(100000, 999999)


# === Envio de e-mail REAL via BREVO ===
def enviar_email(email, codigo):
    smtp_host = "smtp-relay.brevo.com"
    smtp_port = 587
    smtp_user = "9bb9a5001@smtp-brevo.com"
    smtp_pass = "xsmtpsib-6962cab20aa9f005097326b04d6051b45f2fb6ee134ba1f54d982061a7cbeaf5-PnMJHWR2pLnU3Qqq"

    corpo = f"""
Olá! 👋

Seu código de confirmação para acessar o sistema *Lanzaca IA* é:

👉 **{codigo}**

Use este código para concluir seu cadastro.

Atenciosamente,  
Equipe Lanzaca IA ⚡
"""

    msg = MIMEText(corpo, "plain", "utf-8")
    msg["Subject"] = "Código de Confirmação - Lanzaca IA"
    msg["From"] = smtp_user
    msg["To"] = email

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, [email], msg.as_string())
            print("✔ EMAIL ENVIADO PARA:", email)
    except Exception as e:
        print("❌ ERRO AO ENVIAR EMAIL:", e)


# ============================================
# ROTAS DO SISTEMA
# ============================================

# LOGIN (Tela inicial)
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    senha = request.form.get("senha")

    user = supabase.table("users").select("*").eq("email", email).eq("senha", senha).execute()

    if len(user.data) == 0:
        return render_template("index.html", erro="Erro no login.")

    session["email"] = user.data[0]["email"]
    session["nome"] = user.data[0]["nome"]

    return redirect("/dashboard")


# ============================================
# CADASTRO
# ============================================

@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "GET":
        return render_template("cadastro.html")

    nome = request.form.get("nome")
    celular = request.form.get("celular")
    email = request.form.get("email")
    senha = request.form.get("senha")

    # Se já existe usuário definitivo
    existe = supabase.table("users").select("*").eq("email", email).execute()
    if len(existe.data) > 0:
        return render_template("cadastro.html", erro="Email já cadastrado.")

    # Remover pendente antigo
    supabase.table("pending_users").delete().eq("email", email).execute()

    # Salvar novo cadastro pendente
    supabase.table("pending_users").insert({
        "nome": nome,
        "celular": celular,
        "email": email,
        "senha": senha
    }).execute()

    # Criar código
    codigo = gerar_codigo()

    # Salvar na tabela de confirmação
    supabase.table("confirm_codes").delete().eq("email", email).execute()
    supabase.table("confirm_codes").insert({
        "email": email,
        "codigo": codigo
    }).execute()

    # Enviar por email
    enviar_email(email, codigo)

    # Redirecionar para tela de código
    return redirect(f"/confirmar?email={email}")


# ============================================
# CONFIRMAÇÃO DE CÓDIGO
# ============================================

@app.route("/confirmar")
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

    check = supabase.table("confirm_codes").select("*").eq("email", email).eq("codigo", codigo).execute()
    if len(check.data) == 0:
        return jsonify({"message": "Código incorreto"}), 401

    pend = supabase.table("pending_users").select("*").eq("email", email).execute()

    if len(pend.data) == 0:
        return jsonify({"message": "Nenhum cadastro pendente encontrado"}), 404

    user = pend.data[0]

    # Criar usuário definitivo
    supabase.table("users").insert({
        "nome": user["nome"],
        "celular": user["celular"],
        "email": user["email"],
        "senha": user["senha"],
        "is_admin": False
    }).execute()

    # Limpar pendentes
    supabase.table("pending_users").delete().eq("email", email).execute()
    supabase.table("confirm_codes").delete().eq("email", email).execute()

    return jsonify({"message": "Confirmado com sucesso"}), 200


# ============================================
# DASHBOARD
# ============================================

@app.route("/dashboard")
def dashboard():
    if "email" not in session:
        return redirect("/")
    return render_template("dashboard.html", nome=session["nome"])


# ============================================
# LOGOUT
# ============================================

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ============================================
# RENDER
# ============================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
