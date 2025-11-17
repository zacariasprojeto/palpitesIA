# odds_engine.py
# ============================================
# GERENCIADOR PROFISSIONAL DE ODDS
# COMPLETO PARA TODOS OS MERCADOS
# BASE PARA IA DE PALPITES
# ============================================

import os
import requests
from supabase import create_client

# Configurações
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE = os.getenv("SUPABASE_SERVICE_KEY")
API_FOOTBALL = os.getenv("API_FOOTBALL_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE)

BASE_URL = "https://v3.football.api-sports.io"

# ============================================
# 1) Buscar Odds da API-Football
# ============================================

def buscar_odds_api_football(game_id):
    """Busca odds brutas da API-Football e retorna as casas normalizadas"""

    url = f"{BASE_URL}/odds?fixture={game_id}"
    headers = {"x-apisports-key": API_FOOTBALL}

    r = requests.get(url, headers=headers)
    dados = r.json()

    if not dados.get("response"):
        print(f"NENHUMA ODD ENCONTRADA PARA O JOGO {game_id}")
        return []

    odds_raw = dados["response"][0]  # Primeiro pacote de odds
    return odds_raw

# ============================================
# 2) Extrair e organizar mercados da API
# ============================================

def extrair_mercados(odds_raw):
    """
    Converte odds crus da API-Football
    e retorna mercados padronizados:

    Estrutura final:
    [
        {
            "casa": "bet365",
            "mercado": "resultado_final",
            "opcao": "casa",
            "odd": 1.85
        }
    ]
    """

    mercados_limpos = []

    if "bookmakers" not in odds_raw:
        return mercados_limpos

    for casa in odds_raw["bookmakers"]:

        nome_casa = casa["name"].lower().replace(" ", "_")

        # Cada mercado
        for market in casa["bets"]:

            tipo_mercado = market["name"]  # ex: "Match Winner", "Over/Under"

            for item in market["values"]:

                mercados_limpos.append({
                    "casa": nome_casa,
                    "mercado": tipo_mercado,
                    "opcao": item["value"],    # "Home", "Away", "Over 2.5"
                    "odd": float(item["odd"])
                })

    return mercados_limpos

# ============================================
# 2) Processar odds e mercados
# ============================================

def extrair_mercados(odds_raw):
    mercados_limpos = []

    if "bookmakers" not in odds_raw:
        return mercados_limpos

    for casa in odds_raw["bookmakers"]:

        nome_casa = casa["name"].lower().replace(" ", "_")

        # Cada mercado
        for market in casa["bets"]:

            tipo_mercado = market["name"]  # ex: "Match Winner", "Over/Under"

            for item in market["values"]:

                mercados_limpos.append({
                    "casa": nome_casa,
                    "mercado": tipo_mercado,
                    "opcao": item["value"],    # "Home", "Away", "Over 2.5"
                    "odd": float(item["odd"])
                })

    return mercados_limpos

# ============================================
# 3) Ajustes matemáticos (xG, forma, força)
# ============================================

def ajustar_por_stats(game_id, fair_value):
    """Ajuste híbrido usando estatísticas reais"""
    return fair_value


# ============================================
# 4) Construir todos os mercados (principal + avançados)
# ============================================

def construir_mercados(game_id, odds_raw):
    """Monta TODOS os mercados:
        - 1X2
        - Dupla chance
        - BTTS
        - OU 0.5 a 5.5
        - Handicap Asiático
        - HT/FT
        - Escanteios
        - Cartões
        - Jogadores (gol, assist, finalização)
    """
    return []


# ============================================
# 5) Salvar mercados no banco
# ============================================

def salvar_mercados(game_id, mercados):
    """Salva os mercados na tabela markets + odds"""
    pass


# ============================================
# 6) Função principal
# ============================================

def processar_odds(game_id):
    """Fluxo completo:
        1. buscar odds
        2. extrair mercados
        3. corrigir overround
        4. calcular fair odds
        5. aplicar ajustes
        6. salvar no banco
    """
    print(f"Processando odds para o jogo {game_id}...")

    odds_raw = buscar_odds_api_football(game_id)
    mercados = construir_mercados(game_id, odds_raw)
    salvar_mercados(game_id, mercados)

    print(f"Finalizado!")
    return True
# ============================================================
# 4) Função principal: salvar odds no Supabase
# ============================================================

from supabase import create_client
import os

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE)


def salvar_odds_no_banco(game_id):
    print(f"🔍 Buscando odds para game_id={game_id}")

    dados = buscar_odds_api(game_id)
    if not dados:
        print("❌ Nenhuma odd encontrada na API.")
        return False

    mercados = extrair_mercados(dados)
    if len(mercados) == 0:
        print("❌ Nenhum mercado extraído.")
        return False

    print(f"📊 {len(mercados)} mercados encontrados. Salvando no banco...")

    for m in mercados:
        # 1) Inserir mercado
        mercado_resp = supabase.table("markets").insert({
            "game_id": game_id,
            "tipo": m["mercado"],
            "sub_tipo": m["opcao"],
            "descricao": m["mercado"] + " - " + m["opcao"]
        }).execute()

        mercado_id = mercado_resp.data[0]["id"]

        # 2) Inserir odd
        supabase.table("odds").insert({
            "market_id": mercado_id,
            "casa": m["casa"],
            "odd": m["odd"],
            "link": ""
        }).execute()

    print("✅ Odds salvas com sucesso!")
    return True
