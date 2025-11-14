import os
import json
import time
from datetime import datetime
from supabase import create_client, Client
import requests 
from flask import Flask # NOVO: Importa o Flask

# -----------------------------------------------------------
# INICIALIZAÇÃO DO FLASK
# O Render precisa que a variável do aplicativo se chame 'app'
# -----------------------------------------------------------
app = Flask(__name__) 

# --- Funções Auxiliares (Mock Data para Teste) ---

def gerar_apostas_mock_fallback():
    print("⚠️ Usando dados de Mock como Fallback.")
    return [
        {'match': 'MOCK FLAMENGO vs PALMEIRAS', 'league': 'BRASILEIRÃO MOCK', 'bet_type': 'Mais de 2.5 Gols', 'odd': 2.10, 'probability': 0.55, 'value_expected': 0.155, 'stake': 'MÉDIO', 'confidence': 'ALTA', 'casa_aposta': 'Betano', 'link_aposta': 'http://mock.link/1'},
    ]

def gerar_multiplas_mock_fallback():
    return [{'odd_total': 5.25, 'probability': 0.20, 'value_expected': 0.05, 'confidence': 'MÉDIA', 'jogos': json.dumps([{'match': 'MOCK Jogo 1', 'bet_type': 'Vence'}, {'match': 'MOCK Jogo 2', 'bet_type': 'Vence'}])}]

def gerar_surebets_mock_fallback():
    return [{'match': 'MOCK SUREBET 1', 'league': 'Arbitragem', 'odd': 1.95, 'probability': 0.51, 'value_expected': 0.005, 'stake': 'BAIXO', 'confidence': 'MÉDIA', 'casa_aposta': 'Pinnacle', 'link_aposta': 'http://mock.link/s1'}]

def obter_dados_reais_api(odds_api_key):
    if not odds_api_key:
        print("--- ERRO: ODDS_API_KEY não configurada. Usando mock data como fallback. ---")
        return gerar_apostas_mock_fallback()

    ODDS_API_URL = f"https://api.the-odds-api.com/v4/sports/soccer_epl/odds/?regions=eu&markets=h2h&oddsFormat=decimal&apiKey={odds_api_key}"

    try:
        print(f"🌎 Tentando buscar dados da The Odds API...")
        response = requests.get(ODDS_API_URL, timeout=30)
        response.raise_for_status() 

        dados_api = response.json()
        palpites_processados = []

        for jogo in dados_api:
            if not jogo.get('bookmakers'): continue

            odds_source = jogo['bookmakers'][0]['markets'][0]['outcomes']
            match_title = f"{jogo['home_team']} vs {jogo['away_team']}"

            for odd_outcome in odds_source:
                bet_type = odd_outcome['name']
                odd_value = odd_outcome['price']

                probabilidade = 0.50
                value_expected = round((odd_value * probabilidade) - 1, 3) 

                confianca = 'ALTA' if value_expected > 0.10 else 'MÉDIA'
                stake = 'MÉDIO' if value_expected > 0.10 else 'BAIXO'

                palpite = {
                    'match': match_title, 
                    'league': jogo['sport_title'], 
                    'bet_type': bet_type, 
                    'odd': odd_value, 
                    'probability': probabilidade, 
                    'value_expected': value_expected, 
                    'stake': stake, 
                    'confidence': confianca, 
                    'casa_aposta': jogo['bookmakers'][0]['key'], 
                    'link_aposta': 'URL_APROXIMADA' 
                }
                palpites_processados.append(palpite)

        print(f"✅ {len(palpites_processados)} palpites gerados a partir da API.")
        return palpites_processados

    except requests.exceptions.HTTPError as errh:
        print (f"❌ Erro HTTP (API Key, Limite excedido ou 404): {errh}")
        return gerar_apostas_mock_fallback()
    except Exception as e:
        print(f"❌ Erro inesperado ao processar a API: {e}")
        return gerar_apostas_mock_fallback()


def salvar_dados_supabase(dados: list, table_name: str, supabase: Client):
    try:
        print(f"\n🧹 Limpando e salvando na tabela '{table_name}'...")

        response_delete = supabase.table(table_name).delete().gt('id', 0).execute()

        if response_delete.count is not None:
             print(f"   ({response_delete.count} registros antigos deletados)")

        if dados:
            response_insert = supabase.table(table_name).insert(dados).execute()

            if len(response_insert.data) == len(dados):
                print(f"✅ {len(dados)} registros salvos em {table_name}!")
            else:
                print(f"⚠️ Alerta: Tentou salvar {len(dados)} mas Supabase retornou {len(response_insert.data)}. Verifique o log.")
        else:
            print(f"ℹ️ Nenhum dado para salvar em {table_name}.")

    except Exception as e:
        print(f"❌ Erro durante a operação de salvamento na tabela {table_name}: {e}")

# -----------------------------------------------------------
# FUNÇÃO PRINCIPAL DO FLASK (ROTA PADRÃO)
# Esta função será chamada pelo Gunicorn.
# -----------------------------------------------------------
@app.route('/')
def run_cron_job_endpoint(): # O nome da função agora é run_cron_job_endpoint

    # --- Configuração Supabase ---
    try:
        url: str = os.environ.get("SUPABASE_URL")
        key: str = os.environ.get("SUPABASE_KEY")

        odds_api_key: str = os.environ.get("ODDS_API_KEY")

        if not url or not key:
            raise ValueError("URL ou KEY do Supabase não configuradas nas variáveis de ambiente.")

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
