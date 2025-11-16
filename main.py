import os
import json
import time
from datetime import datetime
from supabase import create_client, Client
import requests
# IMPORTAÇÕES ESSENCIAIS PARA O FLASK
from flask import Flask, render_template, request, jsonify 

# -----------------------------------------------------------
# INICIALIZAÇÃO DO FLASK
# -----------------------------------------------------------
app = Flask(__name__) 

# --- Funções Auxiliares de Coleta e Salvação ---

def gerar_apostas_mock_fallback():
    print("⚠️ Usando dados de Mock como Fallback.")
    return [
        {'match': 'MOCK FLAMENGO vs PALMEIRAS', 'league': 'BRASILEIRÃO MOCK', 'bet_type': 'Mais de 2.5 Gols', 'odd': 2.10, 'probability': 0.55, 'value_expected': 0.155, 'stake': 'MÉDIO', 'confidence': 'ALTA', 'casa_aposta': 'Betano', 'link_aposta': 'http://mock.link/1'},
    ]

def gerar_multiplas_mock_fallback():
    return [{'odd_total': 5.25, 'probability': 0.20, 'value_expected': 0.05, 'confidence': 'MÉDIA', 'jogos': json.dumps([{'match': 'MOCK Jogo 1', 'bet_type': 'Vence'}, {'match': 'MOCK Jogo 2', 'bet_type': 'Vence'}])}]

def gerar_surebets_mock_fallback():
    return [{'match': 'MOCK SUREBET 1', 'league': 'Arbitragem', 'odd': 1.95, 'probability': 0.51, 'value_expected': 0.005, 'stake': 'BAIXO', 'confidence': 'MÉDIA', 'casa_aposta': 'Pinnacle', 'link_aposta': 'http://mock.link/s1'}]

# (Mantenha as funções obter_dados_reais_api e salvar_dados_supabase aqui, como no original)
# ...
# ...

# Definições de obter_dados_reais_api e salvar_dados_supabase (Seu código original)
def obter_dados_reais_api(odds_api_key):
    # ... (Seu código original completo aqui) ...
    # ...
    # ...
    pass

def salvar_dados_supabase(dados: list, table_name: str, supabase: Client):
    # ... (Seu código original completo aqui) ...
    # ...
    # ...
    pass


# -----------------------------------------------------------
# ROTA 1: ACIONAMENTO DO CRON JOB (O NOVO ENDPOINT DE EXECUÇÃO)
# URL para o Cron-Job.org: /run-job
# -----------------------------------------------------------
@app.route('/run-job')
def run_cron_job_endpoint():

    # --- Configuração Supabase ---
    try:
        url: str = os.environ.get("SUPABASE_URL")
        key: str = os.environ.get("SUPABASE_KEY")

        odds_api_key: str = os.environ.get("ODDS_API_KEY")

        if not url or not key:
            raise ValueError("URL ou KEY do Supabase não configuradas.")

        supabase: Client = create_client(url, key)
        print(f"✅ Supabase inicializado e conectado ao URL: {url}")
    except Exception as e:
        print(f"❌ Erro Crítico ao inicializar Supabase: {e}")
        return f"Erro Crítico ao inicializar Supabase: {e}", 500 

    # --- Execução Principal do Script ---
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n--- Iniciando Análise de IA em {agora} ---")

    # 1. Obter Dados 
    dados_individuais = obter_dados_reais_api(odds_api_key)
    dados_multiplas = gerar_multiplas_mock_fallback() 
    dados_surebets = gerar_surebets_mock_fallback() 

    # 2. Salvar no Supabase
    salvar_dados_supabase(dados_individuais, 'individuais', supabase)
    salvar_dados_supabase(dados_multiplas, 'multiplas', supabase)
    salvar_dados_supabase(dados_surebets, 'surebets', supabase)

    print("\n--- Processo concluído ---")
    return "Execução do Cron Job concluída com sucesso.", 200

# -----------------------------------------------------------
# ROTA 2: PÁGINA INICIAL (FRONTEND)
# Rota raiz (/) agora serve o index.html, não o Cron Job.
# -----------------------------------------------------------
@app.route('/')
def index():
    # Isso exige que o arquivo 'index.html' esteja na pasta 'templates'
    return render_template('index.html')

# -----------------------------------------------------------
# ROTA 3: CADASTRO (FRONTEND)
# Resolve o erro 404 para /cadastro
# -----------------------------------------------------------
@app.route('/cadastro')
def cadastro_page():
    # Isso exige que o arquivo 'cadastro.html' esteja na pasta 'templates'
    return render_template('cadastro.html')

# -----------------------------------------------------------
# ROTA 4: API DE LOGIN (POST)
# Onde o seu app.js envia as credenciais (estava recebendo 401, mas a rota não existia)
# -----------------------------------------------------------
@app.route('/api/login', methods=['POST'])
def api_login():
    # Aqui você deve colocar a lógica de verificação de login com o Supabase.
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    # ... (Lógica de Auth Supabase e aprovação Admin aqui) ...

    # Retorno temporário para evitar 500/404 (retorna o 401 esperado do log)
    return jsonify({"error": "Unauthorized", "message": "Autenticação em desenvolvimento."}), 401

# -----------------------------------------------------------
# ROTA 5: API DE CADASTRO PENDENTE (POST)
# -----------------------------------------------------------
@app.route('/api/cadastro', methods=['POST'])
def api_cadastro():
    # Aqui você deve colocar a lógica de inserção na tabela 'pending_users' do Supabase.
    data = request.get_json()
    # ... (Lógica de Inserção Supabase para pending_users) ...
    
    return jsonify({"success": True, "message": "Cadastro enviado para aprovação."}), 201
