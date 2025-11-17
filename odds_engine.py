# =============================================================
# odds_engine.py
# Captura odds da API-Football e salva no Supabase (markets + odds)
# 100% em português — sem Over/Under em inglês
# =============================================================

import requests
from supabase import create_client
import os

API_KEY = "ed6c277617a7e4bfb0ad840ecedce5fc"
BASE_URL = "https://v3.football.api-sports.io"

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# =============================================================
# TRADUÇÃO dos mercados para português
# =============================================================
MAPEAMENTO_MERCADOS = {
    "Match Winner": "Resultado Final",
    "Goals Over/Under": "Total de Gols",
    "Both Teams Score": "Ambas Marcam",
    "Double Chance": "Dupla Chance",
    "Correct Score": "Placar Exato",
    "Asian Handicap": "Handicap Asiático",
}


# =============================================================
# Converter mercados "Over/Under" para português
# =============================================================
def traduzir_over_under(texto):
    if "Over" in texto:
        return texto.replace("Over", "Mais de")
    if "Under" in texto:
        return texto.replace("Under", "Menos de")
    return texto


# =============================================================
# FUNÇÃO: Buscar odds de 1 jogo (fixture)
# =============================================================
def buscar_odds(fixture_id):
    url = f"{BASE_URL}/odds?fixture={fixture_id}"
    headers = {"x-apisports-key": API_KEY}

    r = requests.get(url, headers=headers).json()

    if "response" not in r or len(r["response"]) == 0:
        print(f"❌ Nenhuma odd encontrada para fixture {fixture_id}")
        return None

    return r["response"][0]  # pacote bruto


# =============================================================
# FUNÇÃO: extrair e padronizar odds
# =============================================================
def extrair_mercados(odds_raw):
    mercados_limpos = []

    if "bookmakers" not in odds_raw:
        return mercados_limpos

    # Para cada casa de aposta
    for casa in odds_raw["bookmakers"]:
        nome_casa = casa["name"].lower().replace(" ", "_")

        # Para cada mercado da casa
        for market in casa["bets"]:
            nome_original = market["name"]
            nome_mercado = MAPEAMENTO_MERCADOS.get(nome_original, nome_original)
            nome_mercado = traduzir_over_under(nome_mercado)

            # Para cada opção dentro do mercado
            for item in market["values"]:
                opcao = traduzir_over_under(item["value"])

                mercados_limpos.append({
                    "casa": nome_casa,
                    "mercado": nome_mercado,
                    "opcao": opcao,
                    "odd": float(item["odd"])
                })

    return mercados_limpos


# =============================================================
# Salvar no Supabase: tabela markets + odds
# =============================================================
def salvar_no_supabase(fixture_id, lista):
    for m in lista:
        # 1) Criar mercado na tabela "markets"
        market_row = supabase.table("markets").insert({
            "game_id": fixture_id,
            "tipo": m["mercado"],
            "sub_tipo": m["opcao"],
            "descricao": f"{m['mercado']} - {m['opcao']}"
        }).execute()

        if not market_row.data:
            print("❌ Erro ao criar mercado")
            continue

        market_id = market_row.data[0]["id"]

        # 2) Criar odd na tabela "odds"
        supabase.table("odds").insert({
            "market_id": market_id,
            "casa": m["casa"],
            "odd": m["odd"],
            "link": ""
        }).execute()

    print(f"✅ Odds salvas para fixture {fixture_id}")


# =============================================================
# MOTOR PRINCIPAL
# =============================================================
def atualizar_odds_para_jogos():
    print("🔍 Carregando jogos do banco...")

    jogos = supabase.table("games").select("*").execute().data

    if not jogos:
        print("⚠ Nenhum jogo encontrado na tabela games!")
        return

    for jogo in jogos:
        fixture_id = jogo["fixture_id"]
        print(f"\n📌 Buscando odds para jogo {jogo['home_name']} vs {jogo['away_name']}...")

        odds_raw = buscar_odds(fixture_id)

        if odds_raw is None:
            continue

        mercados = extrair_mercados(odds_raw)

        if mercados:
            salvar_no_supabase(fixture_id, mercados)
        else:
            print("⚠ Nenhuma odd processável")


# =============================================================
# EXECUTAR DIRETO
# =============================================================
if __name__ == "__main__":
    atualizar_odds_para_jogos()
