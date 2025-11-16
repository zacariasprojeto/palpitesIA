from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client, Client
from datetime import datetime, timedelta
import random
import smtplib
from email.mime.text import MIMEText
import os

app = Flask(__name__)
CORS(app)

# ============================
#  SUPABASE
# ============================
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

# ============================
# 1) GERAR CÓDIGO
# ============================
def gerar_codigo():
    return str(random.randint(100000, 999999))  # 6 dígitos


# ============================
# 2) ENVIAR E-MAIL (SMTP)
# ============================
def enviar_email(destino, codigo):
    remetente = "SEU_EMAIL"
    senha = "SUA_SENHA_DO_EMAIL"

    msg = MIMEText(f"Seu código de confirmação é: {codigo}")
    msg["Subject"] = "Código de Confirmação - Lanzaca IA"
    msg["From"] = remetente
    msg["To"] = destino

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(remetente, senha)
            smtp.send_message(msg)
        return True
    except Exception as e:
        print("ERRO ENVIO EMAIL:", e)
        return False


# ============================
# 3) ROTA /send_code
# ============================
@app.route("/api/send_code", methods=["POST"])
def send_code():
    data = request.json
    email = data.get("email")

    if not email:
        return jsonify({"error": "Email obrigatório"}), 400

    # verificar se já existe usuário cadastrado
    user = supabase.table("users").select("*").eq("email", email).execute()
    if len(user.data) > 0:
        return jsonify({"error": "Email já cadastrado"}), 400

    # gerar código
    codigo = gerar_codigo()
    expira = datetime.utcnow() + timedelta(minutes=10)

    # salvar no banco
    supabase.table("confirm_codes").insert({
        "email": email,
        "code": codigo,
        "expires_at": expira.isoformat()
    }).execute()

    # enviar e-mail
    enviar_email(email, codigo)

    return jsonify({"message": "Código enviado"}), 200


# ============================
# 4) ROTA /verify_code
# ============================
@app.route("/api/verify_code", methods=["POST"])
def verify_code():
    data = request.json
    email = data.get("email")
    code = data.get("code")
    nome = data.get("nome")
    celular = data.get("celular")
    senha = data.get("senha")

    if not all([email, code, nome, celular, senha]):
        return jsonify({"error": "Dados incompletos"}), 400

    # buscar código
    registro = supabase.table("confirm_codes")\
        .select("*")\
        .eq("email", email)\
        .eq("code", code)\
        .eq("used", False)\
        .execute()

    if len(registro.data) == 0:
        return jsonify({"error": "Código inválido"}), 400

    registro = registro.data[0]

    # verificar expiração
    if datetime.fromisoformat(registro["expires_at"].replace("Z", "")) < datetime.utcnow():
        return jsonify({"error": "Código expirado"}), 400

    # marcar como usado
    supabase.table("confirm_codes")\
        .update({"used": True})\
        .eq("id", registro["id"])\
        .execute()

    # criar usuário pendente
    supabase.table("users").insert({
        "email": email,
        "nome": nome,
        "celular": celular,
        "senha": senha,
        "role": "user",
        "status": "ativo"
    }).execute()

    # gerar 30 dias grátis
    supabase.table("pagamentos").insert({
        "email": email,
        "plano": "Teste grátis",
        "valor": 0,
        "dias": 30,
        "status": "ativo",
        "created_at": datetime.utcnow().isoformat()
    }).execute()

    return jsonify({"message": "Cadastro confirmado! Acesso liberado."}), 200
