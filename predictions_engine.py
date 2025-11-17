# =============================================================
# predictions_engine.py
# IA gera probabilidades para cada jogo e salva no Supabase
# =============================================================

import os
import requests
from supabase import create_client
from openai import OpenAI

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

OPENAI_KEY = os.getenv("OPENAI_API_KEY")  # sua chave sk-proj….

client = OpenAI(api_key=OPENAI_KEY)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =============================================================
# PROMPT PRINCIPAL — Inteligência de Palpites
# =============================================================

PROMPT = """
Você é o maior gerador de palpites de futebol do mundo, 
com índice de acerto acima de 80%.

Analise o jogo abaixo e gere probabilidades reais para:

1. Resultado Final:
   - Vitória da Casa
   - Empate
   - Vitória do Visitante

2. Total de Gols:
   - Mais de 1.5
   - Mais de 2.5
   - Menos de 1.5
   - Menos de 2.5

3. Ambas Marcam:
   - Sim
   - Não

4. Placar Provável (somente 1 placar)

5. Probabilidades por Jogador:
   - Jogador mais provável de marcar gol
   - Jogador mais provável de receber cartão
   (retornar apenas 1 jogador de cada lado)

6. Estatísticas:
   - Probabilidade de +8 escanteios
   - Probabilidade de +10 escanteios
   - Probabilidade de +3 cartões no jogo

7. Mercado Especial:
   - Jogador que chuta mais ao gol
   - Jogador que cria mais chances

RESPOSTA OBRIGATORIAMENTE NO FORMATO JSON:
{
 "resultado_final": {"casa": 0.0, "empate": 0.0, "fora": 0.0},
 "gols": {
     "mais_1_5": 0.0, "mais_2_5": 0.0,
     "menos_1_5": 0.0, "menos_2_5": 0.0
 },
 "ambas_marcam": {"sim": 0.0, "nao": 0.0},
 "placar_provavel": "X-Y",
 "jogadores": {
     "gol_marcador": "Nome",
     "cartao": "Nome"
 },
 "escanteios": {
     "mais_8": 0.0,
     "mais_10": 0.0
 },
 "cartoes": {
     "mais_3": 0.0
 },
 "especial": {
     "finalizacoes": "Nome",
     "criacao_chances": "Nome"
 }
}
"""

# =============================================================
# FUNÇÃO — gerar probabilidades com IA
# =============================================================

def gerar_predicao(jogo):
    texto_jogo = f"""
    {jogo['home_name']} vs {jogo['away_name']}
    Liga: {jogo['league']}
    """

    resposta = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": texto_jogo},
        ]
    )

    conteudo = resposta.choices[0].message.content
    return eval(conteudo)  # transforma JSON em Python


# =============================================================
# SALVAR NA TABELA predictions
# =============================================================

def salvar_predicao(fixture_id, pred):
    supabase.table("predictions").insert({
        "game_id": fixture_id,
        "dados": pred
    }).execute()

    print(f"✅ Predição salva para fixture {fixture_id}")


# =============================================================
# MOTOR PRINCIPAL
# =============================================================

def gerar_predicoes_para_todos_os_jogos():
    jogos = supabase.table("games").select("*").execute().data

    if not jogos:
        print("⚠ Nenhum jogo encontrado.")
        return

    for jogo in jogos:
        print(f"\n🔮 Gerando palpites para {jogo['home_name']} vs {jogo['away_name']}...")

        try:
            pred = gerar_predicao(jogo)
            salvar_predicao(jogo["fixture_id"], pred)
        except Exception as e:
            print("❌ Erro:", e)


# EXECUTAR DIRETO
if __name__ == "__main__":
    gerar_predicoes_para_todos_os_jogos()
