from flask import Flask, render_template, request, redirect, session, jsonify
from supabase import create_client, Client
from datetime import datetime, timedelta
import os
import random
import requests

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "chave_default")

# ==============================
# SUPABASE CONNECTION
# ==============================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE:
    raise Exception("Erro: SUPABASE_URL ou SUPABASE_SERVICE_KEY não configuradas!")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE)

# ==============================
# RESEND EMAIL CONFIG
# ==============================

RESEND_KEY = os.getenv("RESEND_KEY")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")  # Ex: noreply@seudominio.com


def gerar_codigo():
    return random.randint(100000, 999999)


def enviar_email(destino, codigo):
    url = "https://api.resend.com/emails"

    payload = {
        "from": f"Lanzaca IA <{EMAIL_SENDER}>",
        "to": destino,
        "subject": "Código de Confirmação - Lanzaca IA",
        "html": f"""
        <h2>Seu código de confirmação:</h2>
        <p style='font-size:22px;font-weight:bold;color:#1a1a1a'>
            {codigo}
        </p>
        """
    }

    headers = {
        "Authorization": f"Bearer {RESEND_KEY}",
        "Content-Type": "application/json"
    }

    try:
        r = requests.post(url, json=payload, headers=headers)

        if r.status_code in [200, 202]:
            print(f"📧 Código enviado para: {destino}")
        else:
            print("❌ ERRO NO ENVIO:", r.text)

    except Exception as e:
        print("❌ ERRO NO ENVIO:", e)


# ==============================
# ROTAS FLASK
# ==============================


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    senha = request.form.get("senha")

    dados = (
        supabase.table("users")
        .select("*")
        .eq("email", email)
        .eq("senha", senha)
        .execute()
    )

    if len(dados.data) == 0:
        return render_template("index.html", erro="Erro no login.")

    user = dados.data[0]

    # ========= AQUI É ONDE ALTEREI ========= #
    session["email"] = user["email"]
    session["nome"] = user["nome"]
    session["is_admin"] = user.get("is_admin", False)  # <— ADICIONADO
    # ======================================= #

    return redirect("/dashboard")


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
        return render_template("cadastro.html", erro="Email já cadastrado.")

    supabase.table("pending_users").delete().eq("email", email).execute()

    supabase.table("pending_users").insert({
        "nome": nome,
        "celular": celular,
        "email": email,
        "senha": senha
    }).execute()

    codigo = gerar_codigo()

    supabase.table("confirm_codes").delete().eq("email", email).execute()
    supabase.table("confirm_codes").insert({
        "email": email,
        "codigo": str(codigo)
    }).execute()

    enviar_email(email, codigo)

    return redirect(f"/confirmar?email={email}")


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

    verifica = (
        supabase.table("confirm_codes")
        .select("*")
        .eq("email", email)
        .eq("codigo", codigo)
        .execute()
    )

    if len(verifica.data) == 0:
        return jsonify({"message": "Código incorreto"}), 401

    pendente = (
        supabase.table("pending_users")
        .select("*")
        .eq("email", email)
        .execute()
    )

    if len(pendente.data) == 0:
        return jsonify({"message": "Cadastro pendente não encontrado"}), 404

    usuario = pendente.data[0]

    # SALVAMENTO FINAL
    supabase.table("users").insert({
        "nome": usuario["nome"],
        "celular": usuario["celular"],
        "email": usuario["email"],
        "senha": usuario["senha"],
        "password": usuario["senha"],   # coluna obrigatória do Supabase
        "is_admin": False,
        "status": "ativo",
        "plano": "trial"
    }).execute()

    supabase.table("pending_users").delete().eq("email", email).execute()
    supabase.table("confirm_codes").delete().eq("email", email).execute()

    return jsonify({"message": "Confirmado com sucesso"}), 200


@app.route("/dashboard")
def dashboard():

    # ============= AQUI ALTEREI ============= #
    if "email" not in session:
        return redirect("/")

    return render_template(
        "dashboard.html",
        nome=session["nome"],
        is_admin=session.get("is_admin", False)   # <— ADICIONADO
    )
    # ======================================== #

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")
    # ============================================
# SISTEMA DE ATUALIZAÇÃO (JOGOS, ODDS, PREVISÕES)
# ============================================

from games_engine import atualizar_jogos_do_dia
from odds_engine import atualizar_odds_do_dia
from predictions_engine import atualizar_previsoes

# ---- 1) Atualizar JOGOS (games) ----
@app.route("/atualizar/jogos")
def rota_atualizar_jogos():
    try:
        total = atualizar_jogos_do_dia()
        return jsonify({"status": "ok", "msg": f"{total} jogos atualizados."})
    except Exception as e:
        return jsonify({"status": "erro", "detalhe": str(e)}), 500


# ---- 2) Atualizar ODDS (markets + odds) ----
@app.route("/atualizar/odds")
def rota_atualizar_odds():
    try:
        total = atualizar_odds_do_dia()
        return jsonify({"status": "ok", "msg": f"{total} odds atualizadas."})
    except Exception as e:
        return jsonify({"status": "erro", "detalhe": str(e)}), 500


# ---- 3) Atualizar PREDIÇÕES (predictions) ----
@app.route("/atualizar/previsoes")
def rota_atualizar_previsoes():
    try:
        total = atualizar_previsoes()
        return jsonify({"status": "ok", "msg": f"{total} previsões geradas."})
    except Exception as e:
        return jsonify({"status": "erro", "detalhe": str(e)}), 500


# ---- 4) API usada pelo front-end para mostrar palpites ----
@app.route("/api/palpites")
def api_palpites():
    try:
        dados = (
            supabase.table("predictions")
            .select("*")
            .order("ev", desc=True)
            .limit(50)
            .execute()
        )
        return jsonify(dados.data)
    except Exception as e:
        return jsonify({"status": "erro", "detalhe": str(e)}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
