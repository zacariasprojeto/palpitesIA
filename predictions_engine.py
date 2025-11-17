# ===============================================================
# predictions_engine.py
# IA para gerar probabilidades, análises e palpites completos
# ===============================================================

import os
from openai import OpenAI
from datetime import datetime
from supabase import create_client, Client

# -----------------------------------------------------------
# CONFIGURAÇÕES
# -----------------------------------------------------------

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_KEY:
    OPENAI_KEY = "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"

client = OpenAI(api_key=OPENAI_KEY)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE = os.getenv("SUPABASE_SERVICE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE)


# -----------------------------------------------------------
# ❗ PROMPT ULTRA-PODEROSO PARA IA
# Gera análises + probabilidades + odds fair + palpites completos
# -----------------------------------------------------------

def gerar_prompt(jogo):
    prompt = f"""
Você é o **maior especialista de futebol do mundo** e também um analista estatístico avançado.

GERAR PREVISÕES COMPLETAS para o jogo:

🏆 **{jogo["liga_nome"]} - {jogo["liga_pais"]}**  
⚽ **{jogo["time_casa"]} vs {jogo["time_fora"]}**  
📅 Data: {jogo["date"]}

Use:
- estatísticas históricas reais
- forma recente
- gols marcados / sofridos
- média de escanteios
- média de cartões
- xG / xGA estimados
- força das equipes
- status atual da competição
- motivação e elenco provável

GERE O SEGUINTE EM FORMATO JSON:

{{
  "resultado_final": {{
      "casa": probabilidade_em_percentual,
      "empate": probabilidade_em_percentual,
      "fora": probabilidade_em_percentual,
      "palpite": "Casa / Empate / Fora"
  }},
  
  "ambas_marcam": {{
      "sim": percentual,
      "nao": percentual,
      "palpite": "Sim ou Não"
  }},

  "gols": {{
      "mais_0_5": percentual,
      "mais_1_5": percentual,
      "mais_2_5": percentual,
      "mais_3_5": percentual,
      "menos_2_5": percentual
  }},

  "escanteios": {{
      "mais_8_5": percentual,
      "mais_9_5": percentual,
      "mais_10_5": percentual
  }},

  "cartoes": {{
      "mais_3_5": percentual,
      "mais_4_5": percentual
  }},

  "chance_dupla": {{
      "1x": percentual,
      "12": percentual,
      "x2": percentual
  }},

  "placar_correto": {{
      "placar": "ex: 2x1"
  }},

  "analise": "texto com análise completa do jogo"
}}

RETORNE SOMENTE JSON VÁLIDO.
"""
    return prompt


# -----------------------------------------------------------
# CHAMADA À IA
# -----------------------------------------------------------

def gerar_previsao_ia(jogo):
    prompt = gerar_prompt(jogo)

    resposta = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Você é um analista de futebol especialista mundial."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )

    texto = resposta.choices[0].message.content

    # Tenta converter JSON
    try:
        import json
        dados = json.loads(texto)
        return dados

    except Exception:
        print("ERRO ao converter JSON da IA. Conteúdo retornado:")
        print(texto)
        return None


# -----------------------------------------------------------
# SALVAR PREVISÃO NO BANCO
# -----------------------------------------------------------

def salvar_previsao(game_id, previsao):
    return supabase.table("predictions").insert({
        "game_id": game_id,
        "previsao": previsao,
        "criado_em": datetime.utcnow().isoformat()
    }).execute()


# -----------------------------------------------------------
# PROCESSO COMPLETO
# -----------------------------------------------------------

def processar_jogo(game_id):
    print(f"\n🔍 Gerando previsões para o jogo ID {game_id}...")

    jogo = (
        supabase.table("games")
        .select("*")
        .eq("id", game_id)
        .execute()
    ).data[0]

    previsao = gerar_previsao_ia(jogo)

    if previsao:
        salvar_previsao(game_id, previsao)
        print("✅ Previsão salva com sucesso!")
        return True

    print("❌ Falha ao gerar previsão para o jogo.")
    return False


# -----------------------------------------------------------
# EXECUÇÃO DIRETA
# -----------------------------------------------------------

if __name__ == "__main__":
    print("Rodar manualmente: predictions_engine.processar_jogo(id)")
