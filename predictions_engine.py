# =============================================================
# predictions_engine.py
# Gera previsões completas para cada jogo usando IA + estatísticas
# 100% em Português – sem Over/Under, sem inglês
# =============================================================

import requests
from datetime import datetime
from supabase import create_client
import os
import math

# -------------------------------------------------------------
# CONFIGURAÇÕES
# -------------------------------------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

API_FOOTBALL = "ed6c277617a7e4bfb0ad840ecedce5fc"
BASE_URL = "https://v3.football.api-sports.io"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# -------------------------------------------------------------
# 1) FUNÇÃO AUXILIAR: PEGAR ESTATÍSTICAS DE UM TIME
# -------------------------------------------------------------
def get_team_strength(team_id):
    url = f"{BASE_URL}/teams/statistics?team={team_id}&season=2024&league=71"

    headers = {"x-apisports-key": API_FOOTBALL}

    r = requests.get(url, headers=headers).json()

    try:
        stats = r["response"]
    except:
        return {"ataque": 1, "defesa": 1, "forma": 1}

    ataque = stats["goals"]["for"]["average"]["total"]
    defesa = stats["goals"]["against"]["average"]["total"]
    forma = stats["form"].count("W") * 2 + stats["form"].count("D")

    return {
        "ataque": ataque,
        "defesa": defesa,
        "forma": max(1, forma)
    }


# -------------------------------------------------------------
# 2) MODELO DE PREVISÃO (xG SIMPLIFICADO)
# -------------------------------------------------------------
def calcular_probabilidades(home, away):
    # força total
    ataque_casa = home["ataque"] * home["forma"]
    ataque_fora = away["ataque"] * away["forma"]

    defesa_casa = home["defesa"]
    defesa_fora = away["defesa"]

    xg_casa = max(0.1, ataque_casa / defesa_fora)
    xg_fora = max(0.1, ataque_fora / defesa_casa)

    # probabilidades aproximadas
    prob_vitoria_casa = 1 / (1 + math.exp(-(xg_casa - xg_fora)))
    prob_vitoria_fora = 1 - prob_vitoria_casa
    prob_empate = 1 - (prob_vitoria_casa + prob_vitoria_fora) * 0.65

    if prob_empate < 0:
        prob_empate = abs(prob_empate)

    # normalização
    total = prob_vitoria_casa + prob_empate + prob_vitoria_fora

    return {
        "resultado": {
            "casa": prob_vitoria_casa / total,
            "empate": prob_empate / total,
            "fora": prob_vitoria_fora / total
        },
        "gols": {
            "mais_2": (xg_casa + xg_fora) / 3,
            "menos_3": 1 - ((xg_casa + xg_fora) / 3)
        },
        "ambas_marcam": min(1, (xg_casa + xg_fora) / 2),
        "escanteios": (xg_casa + xg_fora) * 4.2,
        "cartoes": (xg_casa + xg_fora) * 1.3
    }


# -------------------------------------------------------------
# 3) SALVAR PREVISÕES NA TABELA
# -------------------------------------------------------------
def salvar_predicao(game_id, pred):
    supabase.table("predictions").insert({
        "game_id": game_id,
        "prob_casa": pred["resultado"]["casa"],
        "prob_empate": pred["resultado"]["empate"],
        "prob_fora": pred["resultado"]["fora"],
        "mais_de_2_gols": pred["gols"]["mais_2"],
        "menos_de_3_gols": pred["gols"]["menos_3"],
        "ambas_marcam": pred["ambas_marcam"],
        "media_escanteios": pred["escanteios"],
        "media_cartoes": pred["cartoes"],
        "criado_em": datetime.utcnow().isoformat()
    }).execute()


# -------------------------------------------------------------
# 4) MOTOR PRINCIPAL
# -------------------------------------------------------------
def gerar_predicoes():
    print("🔥 INICIANDO CÁLCULO DE PREVISÕES...")

    jogos = supabase.table("games").select("*").execute().data

    for jogo in jogos:
        home_id = jogo["home_id"]
        away_id = jogo["away_id"]

        print(f"🔍 Calculando: {jogo['home_name']} vs {jogo['away_name']}")

        home_stats = get_team_strength(home_id)
        away_stats = get_team_strength(away_id)

        pred = calcular_probabilidades(home_stats, away_stats)

        salvar_predicao(jogo["id"], pred)

    print("✅ TODAS AS PREVISÕES FORAM GERADAS!")


if __name__ == "__main__":
    gerar_predicoes()
