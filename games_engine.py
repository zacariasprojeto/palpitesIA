# =============================================================
# games_engine.py
# Captura todos os jogos do dia da API-Football e salva no Supabase
# 100% em português
# =============================================================

import requests
from datetime import datetime
from supabase import create_client
import os

# -------------------------------------------
# CONFIGURAÇÕES
# -------------------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

API_FOOTBALL = "ed6c277617a7e4bfb0ad840ecedce5fc"
BASE_URL = "https://v3.football.api-sports.io"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Ligas importantes (pode adicionar mais depois)
LIGAS_VALIDAS = [
    71,   # Brasileirão Série A
    72,   # Brasileirão Série B
    6,    # Libertadores
    9,    # Sul-Americana
    39,   # Premier League
    140,  # La Liga
    135,  # Serie A Itália
    61,   # Ligue 1 França
    78,   # Bundesliga
    94,   # Liga Portugal
    2,    # Champions League
    3,    # Europa League
]


# =============================================================
# FUNÇÃO: pegar jogos do dia
# =============================================================
def buscar_jogos_do_dia():
    hoje = datetime.utcnow().strftime("%Y-%m-%d")

    url = f"{BASE_URL}/fixtures?date={hoje}"
    headers = {"x-apisports-key": API_FOOTBALL}

    print(f"🔍 Buscando jogos do dia ({hoje})...")

    r = requests.get(url, headers=headers).json()

    if "response" not in r:
        print("❌ Erro na API")
        return []

    jogos = r["response"]
    print(f"📌 Total bruto encontrado: {len(jogos)}")

    # Filtro por ligas importantes
    jogos_filtrados = [
        j for j in jogos if j["league"]["id"] in LIGAS_VALIDAS
    ]

    print(f"✔ Jogos em ligas importantes: {len(jogos_filtrados)}")

    return jogos_filtrados


# =============================================================
# FUNÇÃO: salvar jogo na tabela "games"
# =============================================================
def salvar_jogo(jogo):
    fixture = jogo["fixture"]
    teams = jogo["teams"]
    league = jogo["league"]

    home = teams["home"]
    away = teams["away"]

    game_data = {
        "fixture_id": fixture["id"],
        "league_id": league["id"],
        "league_name": league["name"],
        "round": league.get("round", ""),
        "data_jogo": fixture["date"],
        "status": fixture["status"]["short"],

        "home_id": home["id"],
        "home_name": home["name"],
        "home_logo": home["logo"],

        "away_id": away["id"],
        "away_name": away["name"],
        "away_logo": away["logo"],
    }

    # Remover duplicações
    existe = (
        supabase.table("games")
        .select("*")
        .eq("fixture_id", fixture["id"])
        .execute()
    )

    if len(existe.data) > 0:
        print(f"⏭ Jogo já existe: {home['name']} vs {away['name']}")
        return

    supabase.table("games").insert(game_data).execute()

    print(f"✅ Jogo salvo: {home['name']} vs {away['name']}")


# =============================================================
# MOTOR PRINCIPAL
# =============================================================
def atualizar_jogos():
    jogos = buscar_jogos_do_dia()

    if not jogos:
        print("⚠ Nenhum jogo de ligas importantes hoje.")
        return

    print("📥 Salvando jogos no Supabase...")

    for jogo in jogos:
        salvar_jogo(jogo)

    print("\n🎉 FINALIZADO! Jogos atualizados com sucesso.\n")


# Executar se chamado diretamente
if __name__ == "__main__":
    atualizar_jogos()
