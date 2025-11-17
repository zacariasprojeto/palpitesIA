import os
import requests
from datetime import datetime
from supabase import create_client
from openai import OpenAI
import numpy as np

# -----------------------------
# CONFIGURAÇÕES DE AMBIENTE
# -----------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE = os.getenv("SUPABASE_SERVICE_KEY")
API_FOOTBALL = os.getenv("API_FOOTBALL_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE)

client = OpenAI(api_key=OPENAI_API_KEY)

BASE_URL = "https://v3.football.api-sports.io"

# -----------------------------
# FUNÇÕES DE COLETA DE DADOS
# -----------------------------

def buscar_jogos_do_dia():
    hoje = datetime.now().strftime("%Y-%m-%d")
    url = f"{BASE_URL}/fixtures?date={hoje}"

    headers = { "x-apisports-key": API_FOOTBALL }

    r = requests.get(url, headers=headers)
    dados = r.json()

    return dados["response"]

def buscar_stats(jogo_id):
    url = f"{BASE_URL}/fixtures/statistics?fixture={jogo_id}"
    headers = { "x-apisports-key": API_FOOTBALL }
    r = requests.get(url, headers=headers)

    return r.json().get("response", [])


# -----------------------------
# PROBABILIDADES MATEMÁTICAS
# -----------------------------

def calcular_prob_gols(stats):
    # Simples para começar — usa posse + ataques perigosos
    if not stats:
        return 0.50

    try:
        home = stats[0]["statistics"]
        away = stats[1]["statistics"]

        ataques_home = next(x["value"] for x in home if x["type"] == "Attacks")
        ataques_away = next(x["value"] for x in away if x["type"] == "Attacks")

        total = ataques_home + ataques_away
        prob = ataques_home / total

        return float(prob)

    except:
        return 0.50


def calcular_ev(probabilidade, odd):
    return (probabilidade * odd) - 1


# -----------------------------
# IA – ANÁLISE COMPLETA DO JOGO
# -----------------------------

def gerar_analise_ia(jogo, prob, ev):
    prompt = f"""
Analise o jogo abaixo como um especialista em apostas esportivas.

Jogo: {jogo['teams']['home']['name']} vs {jogo['teams']['away']['name']}
Competição: {jogo['league']['name']}
Probabilidade estimada da aposta principal: {prob*100:.1f}%
Valor Esperado (EV): {ev:.2f}

Quero que responda em tópicos, em português:

1. Resumo técnico do confronto
2. Forma recente dos times
3. Destaques individuais
4. Chances reais de gols e ambas marcam
5. Aposta recomendada
6. Chance de acerto da aposta (%)
7. Justificativa final (profissional, estilo site premium)
"""

    resposta = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role":"user","content":prompt}],
        temperature=0.5,
    )

    return resposta.choices[0].message["content"]


# -----------------------------
# GERAR TODOS OS PALPITES
# -----------------------------

def gerar_palpites():
    jogos = buscar_jogos_do_dia()

    for jogo in jogos:
        jogo_id = jogo["fixture"]["id"]

        stats = buscar_stats(jogo_id)
        prob = calcular_prob_gols(stats)
        odd_exemplo = 1.85

        ev = calcular_ev(prob, odd_exemplo)

        # IA gera texto premium
        analise = gerar_analise_ia(jogo, prob, ev)

        # SALVA PREDIÇÃO COMPLETA
        supabase.table("predictions").insert({
            "game_id": jogo_id,
            "home": jogo["teams"]["home"]["name"],
            "away": jogo["teams"]["away"]["name"],
            "league": jogo["league"]["name"],
            "probabilidade": float(prob),
            "ev": float(ev),
            "odd_principal": odd_exemplo,
            "palpite": "Mais de 2.5 gols",
            "analise": analise
        }).execute()

    return True
