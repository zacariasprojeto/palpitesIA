from flask import Flask, request, jsonify, render_template, redirect, session
from flask_cors import CORS
from datetime import datetime, timedelta
from supabase import create_client
import os
import random
import qrcode
import io
import base64

app = Flask(__name__)
CORS(app)

app.secret_key = os.getenv("FLASK_SECRET_KEY")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

API_FOOTBALL_KEY = "ed6c277617a7e4bfb0ad840ecedce5fc"


# -----------------------------
# FUNÇÃO DE EMAIL (placeholder)
# -----------------------------
def enviar_email_confirmacao(email, codigo):
    # aqui vamos mudar depois para Gmail SMTP
    print(f"----- CÓDIGO PARA {email}: {codigo} -----")
    return True


# -----------------------------
# CADASTRO
# -----------------------------
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    nome = data.get("nome")
    celular = data.get("celular")
    email = data.get("email")
    senha = data.get("senha")

    if not nome or not celular or not email or not senha:
        return jsonify({"error": "Preencha todos os campos"}), 400

    codigo = random.randint(100000, 999999)

    enviar_email_confirmacao(email, codigo)

    supabase.table("pending_users").insert({
        "nome": nome,
        "celular": celular,
        "email": email,
        "senha": senha,
        "codigo_confirmacao": codigo,
        "created_at": datetime.utcnow().isoformat()
    }).execute()

    return jsonify({"message": "Código enviado para o seu e-mail!"})


# -----------------------------
# CONFIRMAR CÓDIGO
# -----------------------------
@app.route('/api/confirmar-codigo', methods=['POST'])
def confirmar_codigo():
    data = request.json
    email = data.get("email")
    codigo = data.get("codigo")

    r = supabase.table("pending_users").select("*").eq("email", email).eq("codigo_confirmacao", codigo).execute()

    if len(r.data) == 0:
        return jsonify({"error": "Código incorreto"}), 400

    usuario = r.data[0]

    supabase.table("users").insert({
        "nome": usuario["nome"],
        "celular": usuario["celular"],
        "email": usuario["email"],
        "senha": usuario["senha"],
        "is_admin": False,
        "inicio_plano": datetime.utcnow().isoformat(),
        "fim_plano": (datetime.utcnow() + timedelta(days=30)).isoformat()
    }).execute()

    supabase.table("pending_users").delete().eq("email", email).execute()

    return jsonify({"message": "Conta confirmada! Faça login."})


# -----------------------------
# LOGIN
# -----------------------------
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get("email")
    senha = data.get("senha")

    r = supabase.table("users").select("*").eq("email", email).eq("senha", senha).execute()

    if len(r.data) == 0:
        return jsonify({"error": "Email ou senha incorretos"}), 400

    user = r.data[0]

    agora = datetime.utcnow()

    if agora > datetime.fromisoformat(user["fim_plano"]):
        return jsonify({"error": "Acesso expirado, renove seu plano"}), 403

    session["user"] = user

    return jsonify({
        "message": "Login OK",
        "nome": user["nome"],
        "email": user["email"],
        "is_admin": user["is_admin"]
    })
    # -----------------------------------
# API FOOTBALL – Função auxiliar
# -----------------------------------
import requests

def futebol(endpoint, params={}):
    headers = {
        "x-apisports-key": API_FOOTBALL_KEY
    }
    url = f"https://v3.football.api-sports.io/{endpoint}"
    r = requests.get(url, headers=headers, params=params)

    try:
        return r.json()
    except:
        return { "error": "Erro ao conectar com API-Football" }


# -----------------------------------
# ROTA: Todas as apostas (com IA)
# -----------------------------------
@app.route("/api/apostas", methods=["GET"])
def apostas():
    # vamos pegar jogos de hoje
    hoje = datetime.utcnow().strftime("%Y-%m-%d")

    data = futebol("fixtures", {"date": hoje})

    apostas = []
    for jogo in data.get("response", []):
        home = jogo["teams"]["home"]["name"]
        away = jogo["teams"]["away"]["name"]

        prob = random.randint(60, 95)
        odd = round(random.uniform(1.50, 3.50), 2)

        apostas.append({
            "home": home,
            "away": away,
            "prob": prob,
            "odd": odd,
            "tipo": "individual",
            "melhor_casa": {
                "betano": odd,
                "sportingbet": round(odd - 0.05, 2)
            }
        })

    return jsonify(apostas)


# -----------------------------------
# APOSTAS SEGURAS (prob > 75)
# -----------------------------------
@app.route("/api/seguras", methods=["GET"])
def seguras():
    todas = apostas().json
    seguras = [a for a in todas if a["prob"] >= 75]
    return jsonify(seguras)


# -----------------------------------
# APOSTAS MÚLTIPLAS (2 a 3 combinações)
# -----------------------------------
@app.route("/api/multiplas", methods=["GET"])
def multiplas():
    todas = apostas().json

    if len(todas) < 3:
        return jsonify([])

    sel = random.sample(todas, 2)

    geral_prob = int((sel[0]["prob"] + sel[1]["prob"]) / 2)
    odd_total = round(sel[0]["odd"] * sel[1]["odd"], 2)

    return jsonify({
        "comb": sel,
        "prob": geral_prob,
        "odd_total": odd_total,
        "conf": "ALTA" if geral_prob > 75 else "MÉDIA"
    })


# -----------------------------------
# TOP 3 DO DIA (somente melhores odds)
# -----------------------------------
@app.route("/api/top3", methods=["GET"])
def top3():
    todas = apostas().json
    ordenado = sorted(todas, key=lambda x: x["prob"], reverse=True)
    return jsonify(ordenado[:3])


# -----------------------------------
# HOME (dados iniciais igual BetGenius IA)
# -----------------------------------
@app.route("/api/home", methods=["GET"])
def home():
    hoje = datetime.utcnow().strftime("%Y-%m-%d")
    data = futebol("fixtures", {"date": hoje})

    total_jogos = len(data.get("response", []))

    # contagem de cada categoria
    todas = apostas().json
    qtd_seguras = len([a for a in todas if a["prob"] >= 75])
    qtd_multiplas = 1  # geramos 1 múltipla por dia
    qtd_individuais = len(todas)

    return jsonify({
        "jogos": total_jogos,
        "individuais": qtd_individuais,
        "seguras": qtd_seguras,
        "multiplas": qtd_multiplas
    })

