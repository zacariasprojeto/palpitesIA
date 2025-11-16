from flask import Flask, render_template, request, redirect, session, jsonify
from supabase import create_client, Client
from datetime import datetime, timedelta
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = "LanzacaIA2025"

# ==============================
# SUPABASE CONFIG
# ==============================

SUPABASE_URL = "https://kctzwwzcthjmdgvxuks.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtjdHp3d2N6Y3Roam1kZ3Z4dWtzIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2Mjk4MjA0NiwiZXhwIjoyMDc4NTU4MDQ2fQ.gXOpswZ8zoedalvpKcBKNuZwTBC0EY_GYZum1C3lxFs"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ==============================
# EMAIL (BREVO SMTP)
# ==============================

SMTP_SERVER = "smtp-relay.brevo.com"
SMTP_PORT = 587
SMTP_LOGIN = "9bb9a5001@smtp-brevo.com"
SMTP_PASSWORD = "xsmtpsib-6962cab20aa9f005097326b04d6051b45f2fb6ee134ba1f54d982061a7cbeaf5-PnMJHWR2pLnU3Qqq"

def enviar_email_real(destino, codigo):
    try:
        msg = MIMEMultipart()
        msg["From"] = "lanzacaia@smtp-brevo.com"
        msg["To"] = destino
        msg["Subject"] = "Seu código de confirmação - Lanzaca IA"

        corpo = f"""
        <h2>Seu código de confirmação</h2>
        <p>Use este código para concluir seu cadastro:</p>
        <h1>{codigo}</h1>
        """

        msg.attach(MIMEText(corpo, "html"))

        smtp = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        smtp.starttls()
        smtp.login(SMTP_LOGIN, SMTP_PASSWORD)
        smtp.sendmail(msg["From"], destino, msg.as_string())
        smtp.quit()

        print("EMAIL ENVIADO PARA:", destino)

    except Exception as e:
        print("ERRO AO ENVIAR EMAIL:", e)


# ==============================
# FUNÇÕES
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

    # Verifica se email já existe
    existe = supabase.table("users").select("*").eq("email", email).execute()
    if len(existe.data) > 0:
        return render_template("cadastro.html", erro="Este email já está cadastrado.")

    # Remove pendente antigo
    supabase.table("pending_users").delete().eq("email", email).execute()

    # Salvar pendente
    supabase.table("pending_users").insert({
        "nome": nome,
        "celular": celular,
        "email": email,
        "senha": senha
    }).execute()

    # Criar código
    codigo = gerar_codigo()

    # Registrar código
    supabase.table("confirm_codes").insert({
        "email": email,
        "codigo": str(codigo)
    }).execute()

    # Enviar email real
    enviar_email_real(email, codigo)

    # Redirecionar
    return redirect(f"/confirmar?email={email}")


# ==============================
# CONFIRMAÇÃO DE CÓDIGO
# ==============================

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

    consulta = supabase.table("confirm_codes").select("*").eq("email", email).eq("codigo", codigo).execute()

    if len(consulta.data) == 0:
        return jsonify({"message": "Código incorreto"}), 401

    pend = supabase.table("pending_users").select("*").eq("email", email).execute()
    if len(pend.data) == 0:
        return jsonify({"message": "Cadastro não encontrado"}), 404

    usuario = pend.data[0]

    supabase.table("users").insert({
        "nome": usuario["nome"],
        "celular": usuario["celular"],
        "email": usuario["email"],
        "senha": usuario["senha"],
        "is_admin": False
    }).execute()

    supabase.table("pending_users").delete().eq("email", email).execute()
    supabase.table("confirm_codes").delete().eq("email", email).execute()

    return jsonify({"message": "Confirmado com sucesso"}), 200


# ==============================
# DASHBOARD E LOGOUT
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
