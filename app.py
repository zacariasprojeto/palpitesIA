import os
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
from supabase import create_client, Client

# -----------------------------------------
# CONFIG SUPABASE
# -----------------------------------------

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# -----------------------------------------
# INICIALIZAÇÃO DO FLASK
# -----------------------------------------

app = Flask(__name__)


# =====================================================
# FUNÇÕES MOCK – (mantidas do seu arquivo original)
# =====================================================

def gerar_apostas_mock_fallback():
    return [
        {
            'match': 'MOCK FLAMENGO vs PALMEIRAS',
            'league': 'BRASILEIRÃO MOCK',
            'bet_type': 'Mais de 2.5 Gols',
            'odd': 2.10,
            'probability': 0.55,
            'value_expected': 0.155,
            'stake': 'MÉDIO',
            'confidence': 'ALTA',
            'casa_aposta': 'Betano',
            'link_aposta': 'http://mock.link/1'
        }
    ]


def gerar_multiplas_mock_fallback():
    return [{
        'odd_total': 5.25,
        'probability': 0.20,
        'value_expected': 0.05,
        'confidence': 'MÉDIA',
        'jogos': json.dumps([
            {'match': 'MOCK Jogo 1', 'bet_type': 'Vence'},
            {'match': 'MOCK Jogo 2', 'bet_type': 'Vence'}
        ])
    }]


def gerar_surebets_mock_fallback():
    return [{
        'match': 'MOCK SUREBET 1',
        'league': 'Arbitragem',
        'odd': 1.95,
        'probability': 0.51,
        'value_expected': 0.005,
        'stake': 'BAIXO',
        'confidence': 'MÉDIA',
        'casa_aposta': 'Pinnacle',
        'link_aposta': 'http://mock.link/s1'
    }]


# ---------------------------------------------------------------------------------------------------
# ROTAS FRONTEND
# ---------------------------------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/cadastro")
def cadastro():
    return render_template("cadastro.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


# ---------------------------------------------------------------------------------------------------
# LOGIN FUNCIONAL COM SUPABASE + VALIDAR TEMPO + ADMIN ILIMITADO
# ---------------------------------------------------------------------------------------------------

@app.route("/api/login", methods=["POST"])
def api_login():

    data = request.get_json()
    email = data.get("email")
    senha = data.get("senha")

    try:
        # 🔎 Busca usuário pelo email + senha
        user = (
            supabase.table("users")
            .select("*")
            .eq("email", email)
            .eq("senha", senha)
            .single()
            .execute()
        )

        if not user.data:
            return jsonify({"error": "Credenciais inválidas"}), 401

        user = user.data  # simplificar

        # 🌟 ADMIN = ACESSO ILIMITADO
        if user["is_admin"] == True:
            return jsonify({"redirect": "/dashboard"}), 200

        # ⏳ VALIDAR PRAZO DE ACESSO
        hoje = datetime.utcnow()

        trial_end = user.get("trial_end")
        paid_until = user.get("paid_until")

        # Se tiver paid_until → usa isso primeiro
        if paid_until:
            expira = datetime.fromisoformat(paid_until.replace("Z", ""))
        else:
            expira = datetime.fromisoformat(trial_end.replace("Z", ""))

        if hoje > expira:
        return jsonify({"error": "expired","message": "Sua licença está vencida.",
        "redirect": "/pagamento"}), 403

        return jsonify({"redirect": "/dashboard"}), 200

    except Exception as e:
        print("ERRO LOGIN:", e)
        return jsonify({"error": "Erro no servidor"}), 500


# ---------------------------------------------------------------------------------------------------
# CADASTRO FUNCIONAL (trial 30 dias)
# ---------------------------------------------------------------------------------------------------

@app.route("/api/cadastro", methods=["POST"])
def api_cadastro():

    data = request.get_json()
    
    novo = {
        "nome": data.get("nome"),
        "email": data.get("email"),
        "celular": data.get("celular"),
        "senha": data.get("senha"),
        "is_admin": False,
        "plan": "trial",
        "trial_end": (datetime.utcnow() + timedelta(days=30)).isoformat(),
        "paid_until": None
    }

    try:
        supabase.table("users").insert(novo).execute()
        return jsonify({"success": True}), 201
    except Exception as e:
        print("ERRO CADASTRO:", e)
        return jsonify({"error": "Erro ao cadastrar"}), 500


# ---------------------------------------------------------------------------------------------------
# CRON JOB
# ---------------------------------------------------------------------------------------------------

@app.route("/run-job")
def run_job():

    try:
        supabase.table("individuais").insert(gerar_apostas_mock_fallback()).execute()
        supabase.table("multiplas").insert(gerar_multiplas_mock_fallback()).execute()
        supabase.table("surebets").insert(gerar_surebets_mock_fallback()).execute()
    except Exception as e:
        print("ERRO CRON:", e)
        return "Erro", 500

    return "OK", 200


# ---------------------------------------------------------------------------------------------------
# MAIN LOCAL
# ---------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
