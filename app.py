import os
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
from supabase import create_client, Client
from flask_cors import CORS # Adicionado CORS para ambiente de produção

# -----------------------------------------
# INICIALIZAÇÃO DO FLASK
# -----------------------------------------

app = Flask(__name__)
# Habilita CORS para permitir chamadas de frontend em outros domínios (como o Vercel)
CORS(app) 

# Variável Mock para pagamento
PIX_KEY = "SEU PIX AQUI"

# -----------------------------------------
# FUNÇÃO AUXILIAR: Inicializa Supabase LOCALMENTE
# Esta função PREVINE O ERRO DE INICIALIZAÇÃO (SupabaseException)
# -----------------------------------------
def get_supabase_client() -> Client | None:
    """Cria e retorna o cliente Supabase usando variáveis de ambiente."""
    url = os.environ.get("SUPABASE_URL")
    # Usando SUPABASE_SERVICE_KEY conforme você especificou no seu código
    key = os.environ.get("SUPABASE_SERVICE_KEY") 
    
    if not url or not key:
        print("ERRO DE CONFIGURAÇÃO: SUPABASE_URL ou SUPABASE_SERVICE_KEY não encontrados.")
        return None
    
    return create_client(url, key)


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
    # 1. Inicializa Supabase (DEVE SER FEITO DENTRO DA ROTA)
    supabase = get_supabase_client()
    if not supabase:
        return jsonify({"error": "Erro de configuração no servidor. Chaves Supabase não encontradas."}), 500

    data = request.get_json()
    email = data.get("email")
    # A variável 'senha' aqui é a 'password' que você usou anteriormente no front/log
    senha = data.get("senha") 

    try:
        # 🔎 Busca usuário pelo email + senha
        # Nota: O uso de .single() exige que apenas um resultado seja retornado, 
        # o que é bom para login.
        user_response = (
            supabase.table("users")
            .select("*")
            .eq("email", email)
            .eq("senha", senha)
            .single()
            .execute()
        )

        if not user_response.data:
            return jsonify({"error": "Credenciais inválidas"}), 401

        user = user_response.data  # simplificar

        # 🌟 ADMIN = ACESSO ILIMITADO
        if user.get("is_admin") == True:
            return jsonify({"redirect": "/dashboard"}), 200

        # ⏳ VALIDAR PRAZO DE ACESSO
        hoje = datetime.utcnow()

        trial_end = user.get("trial_end")
        paid_until = user.get("paid_until")
        expira = None

        # Se tiver paid_until → usa isso primeiro
        if paid_until:
            try:
                expira = datetime.fromisoformat(paid_until.replace("Z", "+00:00"))
            except ValueError:
                print(f"ERRO: Formato inválido para paid_until: {paid_until}")
        
        # Se paid_until falhou ou era None, tenta trial_end
        if not expira and trial_end:
            try:
                # Adiciona o fuso horário para evitar problemas de conversão
                expira = datetime.fromisoformat(trial_end.replace("Z", "+00:00")) 
            except ValueError:
                print(f"ERRO: Formato inválido para trial_end: {trial_end}")
        
        # Se não há data válida OU se expirou
        if not expira or hoje > expira:
            # CORREÇÃO DA INDENTAÇÃO APLICADA AQUI (era a linha 134)
            return jsonify({
                "error": "expired",
                "message": "Sua licença está vencida.",
                "redirect": "/pagamento"
            }), 403

        return jsonify({"redirect": "/dashboard"}), 200

    except Exception as e:
        print("ERRO LOGIN:", e)
        # Se a consulta falhar (por exemplo, erro de coluna ou configuração), retorna 500
        return jsonify({"error": "Erro no servidor"}), 500


# ---------------------------------------------------------------------------------------------------
# CADASTRO FUNCIONAL (trial 30 dias)
# ---------------------------------------------------------------------------------------------------

@app.route("/api/cadastro", methods=["POST"])
def api_cadastro():
    # 1. Inicializa Supabase
    supabase = get_supabase_client()
    if not supabase:
        return jsonify({"error": "Erro de configuração no servidor."}), 500

    data = request.get_json()
    
    # 2. Verifica se o email já existe ANTES de tentar inserir
    existe_response = supabase.table("users").select("email").eq("email", data.get("email")).execute()
    if existe_response.data:
        return jsonify({"error": "Email já cadastrado."}), 400

    novo = {
        "nome": data.get("nome"),
        "email": data.get("email"),
        "celular": data.get("celular"),
        "senha": data.get("senha"),
        "is_admin": False,
        "plan": "trial",
        "trial_end": (datetime.utcnow() + timedelta(days=30)).isoformat() + 'Z', # Adiciona 'Z' ao final para consistência
        "paid_until": None
    }

    try:
        supabase.table("users").insert(novo).execute()
        return jsonify({"success": True}), 201
    except Exception as e:
        print("ERRO CADASTRO:", e)
        # Em caso de erro de DB, retorna 500
        return jsonify({"error": "Erro ao cadastrar"}), 500


# ---------------------------------------------------------------------------------------------------
# CRON JOB
# ---------------------------------------------------------------------------------------------------

@app.route("/run-job")
def run_job():
    # 1. Inicializa Supabase
    supabase = get_supabase_client()
    if not supabase:
        return "Erro de configuração no servidor.", 500

    try:
        # A inserção de dados deve ser feita em blocos separados.
        supabase.table("individuais").insert(gerar_apostas_mock_fallback()).execute()
        supabase.table("multiplas").insert(gerar_multiplas_mock_fallback()).execute()
        supabase.table("surebets").insert(gerar_surebets_mock_fallback()).execute()
    except Exception as e:
        print("ERRO CRON:", e)
        return "Erro ao executar job", 500

    return "OK", 200


# ---------------------------------------------------------------------------------------------------
# MAIN LOCAL
# ---------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    # Removeu 'debug=True' para evitar conflitos de reloader em alguns ambientes, se necessário.
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
