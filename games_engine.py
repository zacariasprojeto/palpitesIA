# ===============================================================
# games_engine.py
# Atualiza lista de jogos do dia a partir da API-Football
# e salva na tabela "games" do Supabase
# ===============================================================

import requests
from datetime import datetime
from supabase import create_client, Client
import os

# ------------------------------------------
# CONFIGURAÇÕES
# ------------------------------------------

API_KEY = "ed6c277617a7e4bfb0ad840ecedce5fc"
BASE_URL = "https://v3.football.api-sports.io"

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE = os.getenv("SUPABASE_SERVICE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE)


# ------------------------------------------
# Função auxiliar: normalizar nomes
# ------------------------------------------
def limpar_nome(texto):
    if not texto:
        return ""
    return texto.replace("'", "").replace('"', "").strip()


# ------------------------------------------
# Buscar todos os jogos do dia
# ------------------------------------------
def buscar_jogos_do_dia():
    hoje = datetime.utcnow().strftime("%Y-%m-%d")

    url = f"{BASE_URL}/fixtures?date={hoje}"

    headers = {
        "x-apisports-key": API_KEY
    }

    r = requests.get(url, headers=headers)
    dados = r.json()

    print("STATUS:", r.status_code)
    print("Jogos encontrados:", len(dados.get("response", [])))

    return dados.get("response", [])


# ------------------------------------------
# Inserir jogo no banco
# ------------------------------------------
def salvar_jogo(jogo):
    fixture = jogo["fixture"]
    teams = jogo["teams"]
    league = jogo["league"]

    jogo_data = {
        "api_id": fixture["id"],
        "date": fixture["date"],
        "liga_id": league["id"],
        "liga_nome": limpar_nome(league["name"]),
        "liga_pais": limpar_nome(league["country"]),
        "time_casa": limpar_nome(teams["home"]["name"]),
        "time_fora": limpar_nome(teams["away"]["name"]),
        "status": fixture["status"]["short"],
    }

    # Verificar se já existe no banco
    existente = (
        supabase.table("games")
        .select("*")
        .eq("api_id", fixture["id"])
        .execute()
    )

    if len(existente.data) > 0:
        print("⚠ Já existe:", fixture["id"])
        return existente.data[0]["id"]

    # Inserir novo
    novo = (
        supabase.table("games")
        .insert(jogo_data)
        .execute()
    )

    print("✔ Inserido:", fixture["id"])
    return novo.data[0]["id"]


# ------------------------------------------
# PROCESSO PRINCIPAL
# ------------------------------------------
def atualizar_jogos():
    print("\n==============================")
    print(" ATUALIZANDO JOGOS DO DIA")
    print("==============================\n")

    jogos = buscar_jogos_do_dia()

    ids = []

    for jogo in jogos:
        game_id = salvar_jogo(jogo)
        ids.append(game_id)

    print("\n==============================")
    print(" FINALIZADO!")
    print(f" Jogos salvos no banco: {len(ids)}")
    print("==============================\n")

    return ids


# ------------------------------------------
# Execução direta
# ------------------------------------------
if __name__ == "__main__":
    atualizar_jogos()
