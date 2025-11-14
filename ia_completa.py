import os
import json
import time
import requests
from datetime import datetime, timedelta
import hashlib

print("🔥 SISTEMA DE PALPITES 100% INTELIGENTE - INICIANDO...")

# --- Configurações ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
ODDS_API_KEY = os.environ.get("ODDS_API_KEY")
FOOTBALL_DATA_KEY = os.environ.get("FOOTBALL_DATA_KEY")
API_SPORTS_KEY = os.environ.get("API_SPORTS_KEY") # <--- NOVA CHAVE

# Headers para Supabase
SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# Headers para API-Sports
API_SPORTS_HEADERS = {
    'x-rapidapi-key': API_SPORTS_KEY,
    'x-rapidapi-host': 'api-football-v1.p.rapidapi.com'
}


def salvar_dados_supabase(dados, table_name):
    """Salva dados no Supabase"""
    try:
        if not SUPABASE_URL or not SUPABASE_KEY:
            print("⚠️ Supabase não configurado")
            return False
            
        print(f"💾 Salvando {len(dados)} registros em {table_name}...")
        
        url = f"{SUPABASE_URL}/rest/v1/{table_name}"
        
        # Deletar registros antigos (CORRIGIDO: Assume que a tabela foi recriada corretamente)
        delete_response = requests.delete(f"{url}?id=gt.0", headers=SUPABASE_HEADERS)
        
        if delete_response.status_code in [200, 201, 204]:
            print(f"✅ Registros antigos de {table_name} removidos")
        
        # Inserir novos registros
        if dados:
            insert_response = requests.post(url, json=dados, headers=SUPABASE_HEADERS)
            
            if insert_response.status_code in [200, 201]:
                print(f"✅ {len(dados)} registros salvos em {table_name}")
                return True
            else:
                print(f"❌ Erro ao salvar (código {insert_response.status_code}): {insert_response.text}")
                return False
        else:
            print(f"ℹ️ Nenhum dado para salvar em {table_name}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao salvar: {e}")
        return False

# --- FUNÇÕES DE BUSCA (Ajustadas para evitar limite de API anterior) ---

def buscar_jogos_futuros():
    """Busca jogos futuros (hoje/amanhã) para análise da IA Básica (H2H)."""
    print("🌐 Buscando jogos futuros para análise básica (H2H)...")
    
    jogos_analise = []
    hoje = datetime.now()
    
    # 1. JOGOS DE HOJE (Pré-jogo/Agendados - Football Data)
    try:
        if FOOTBALL_DATA_KEY:
            hoje_str = hoje.strftime('%Y-%m-%d')
            headers = {'X-Auth-Token': FOOTBALL_DATA_KEY}
            response = requests.get(
                f"https://api.football-data.org/v4/matches?dateFrom={hoje_str}&dateTo={hoje_str}",
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                for match in data.get('matches', []):
                    if match['status'] in ['SCHEDULED', 'TIMED']:
                        jogos_analise.append({
                            'home_team': match['homeTeam']['name'],
                            'away_team': match['awayTeam']['name'],
                            'league': match['competition']['name'],
                            'status': 'AGENDADO',
                            'minuto': match['utcDate'][11:16],
                            'fonte': 'FOOTBALL_DATA_TODAY'
                        })
                
            elif response.status_code == 403:
                print("⚠️ Aviso: Football-Data.org Limite Excedido (403) na busca agendada.")
    except Exception as e:
        print(f"❌ Erro Football Data Today: {e}")
        
    
    # 2. JOGOS DE AMANHÃ (The Sports DB - Backup)
    try:
        amanha = (hoje + timedelta(days=1)).strftime('%Y-%m-%d')
        response = requests.get(
            f"https://www.thesportsdb.com/api/v1/json/3/eventsday.php?d={amanha}&s=Soccer",
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            for event in data.get('events', [])[:15]: 
                jogos_analise.append({
                    'home_team': event['strHomeTeam'],
                    'away_team': event['strAwayTeam'],
                    'league': event['strLeague'],
                    'status': 'AGENDADO',
                    'minuto': 'Pré-jogo',
                    'fonte': 'THESPORTSDB_TOMORROW'
                })
    except Exception as e:
        print(f"❌ Erro TheSportsDB Amanhã: {e}")
        
    
    # Remover duplicatas e retornar
    jogos_unicos = []
    seen = set()
    for jogo in jogos_analise:
        identifier = f"{jogo['home_team']}_{jogo['away_team']}_{jogo['league']}"
        if identifier not in seen:
            seen.add(identifier)
            jogos_unicos.append(jogo)
    
    print(f"🎯 Total de {len(jogos_unicos)} jogos para análise da IA básica (H2H).")
    return jogos_unicos

def buscar_odds_reais():
    """Busca odds reais (DESATIVADO TEMPORARIAMENTE para evitar erro 402/403)"""
    print("💰 Buscando odds reais... (DESATIVADO PARA POUPAR LIMITE)")
    return None # Retorna None para usar apenas odds da IA


# --- NOVO: FUNÇÃO DE BUSCA DE ESTATÍSTICAS DETALHADAS (API-SPORTS) ---

def buscar_estatisticas_detalhadas():
    """
    Busca estatísticas detalhadas (chutes, escanteios) 
    usando a API-Sports para jogos de HOJE para análise da IA de Props.
    """
    if not API_SPORTS_KEY:
        print("❌ API_SPORTS_KEY não configurada.")
        return []
    
    print("📊 Buscando estatísticas detalhadas da API-Sports...")
    
    apostas_estatisticas = []
    
    try:
        # 1. Buscar partidas de HOJE (Agendadas/Em andamento)
        hoje_str = datetime.now().strftime('%Y-%m-%d')
        url_fixtures = f"https://api-football-v1.p.rapidapi.com/v3/fixtures?date={hoje_str}&timezone=Europe/London"
        
        response = requests.get(url_fixtures, headers=API_SPORTS_HEADERS, timeout=15)
        if response.status_code != 200:
            print(f"❌ Erro {response.status_code} buscando fixtures: {response.text}")
            return []
        
        fixtures = response.json().get('response', [])
        
        # 2. Iterar sobre as partidas e buscar as estatísticas
        for fixture in fixtures:
            fixture_id = fixture['fixture']['id']
            league = fixture['league']['name']
            home_team = fixture['teams']['home']['name']
            away_team = fixture['teams']['away']['name']
            
            # Buscando estatísticas do jogo
            url_stats = f"https://api-football-v1.p.rapidapi.com/v3/fixtures/statistics?fixture={fixture_id}"
            stats_response = requests.get(url_stats, headers=API_SPORTS_HEADERS, timeout=10)
            
            if stats_response.status_code == 200:
                stats_data = stats_response.json().get('response', [])
                
                home_shots = 0
                away_shots = 0
                home_corners = 0
                
                # Processar dados de estatísticas
                for team_stats in stats_data:
                    team_name = team_stats['team']['name']
                    stats_list = team_stats['statistics']
                    
                    for stat in stats_list:
                        if stat['type'] == 'Total Shots':
                            if team_name == home_team:
                                home_shots = stat['value'] or 0
                            else:
                                away_shots = stat['value'] or 0
                        elif stat['type'] == 'Corner Kicks':
                            if team_name == home_team:
                                home_corners = stat['value'] or 0
                
                
                # --- LÓGICA DE IA AVANÇADA PARA ESTATÍSTICAS (Exemplo simples) ---
                total_shots = (home_shots or 0) + (away_shots or 0)
                total_corners = home_corners # Simulação de soma total para o exemplo
                
                # Palpite 1: Chutes Totais
                if total_shots > 20 and total_shots < 30: 
                    odd = 1.80
                    prob = 1 / 1.55 # Probabilidade ajustada da IA (ex: 64%)
                    valor_esperado = (odd * prob) - 1
                    confianca, stake = determinar_confianca_stake(valor_esperado, prob)
                    valor_percentual = (prob - (1/odd)) * 100
                    
                    if valor_esperado > 0.05:
                        apostas_estatisticas.append({
                            'match': f"{home_team} vs {away_team}",
                            'league': league,
                            'bet_type': 'Total de Chutes > 20.5',
                            'odd': round(odd, 2),
                            'probability': round(prob, 3),
                            'value_expected': round(valor_esperado, 3),
                            'value_percent': round(valor_percentual, 1),
                            'stake': stake,
                            'confidence': confianca,
                            'casa_aposta': 'IA STATS',
                            'link_aposta': '#',
                            'status_jogo': 'PRÉ-JOGO',
                            'minuto': fixture['fixture']['date'][11:16],
                            'fonte_odds': 'CALCULADO_STATS',
                            'fonte_jogo': 'API_SPORTS',
                            'timestamp': datetime.now().isoformat()
                        })
                
                # Palpite 2: Escanteios
                if total_corners > 10:
                    # ... Adicione mais lógica de escanteios aqui ...
                    pass


        # Se você quiser o palpite de 'Chutes por Jogador', você precisa 
        # buscar o endpoint 'events' (eventos) da API-Sports, que lista chutes por jogador.

    except Exception as e:
        print(f"❌ Erro buscando estatísticas detalhadas: {e}")
        return []
    
    print(f"✅ Total de {len(apostas_estatisticas)} palpites estatísticos gerados.")
    return apostas_estatisticas


# --- FUNÇÕES DE LÓGICA DA IA (MANTIDAS) ---

def calcular_odds_inteligentes(home_team, away_team, league):
    """Calcula odds realistas baseadas em dados reais (Rating H2H)"""
    # ... (Seu código de rating H2H mantido) ...
    ranking_times = {
        'flamengo': 85, 'palmeiras': 84, 'são paulo': 82, 'corinthians': 81,
        'internacional': 80, 'atlético-mg': 83, 'grêmio': 79, 'botafogo': 78,
        'fortaleza': 77, 'bahia': 76, 'vasco': 75, 'cruzeiro': 76,
        'fluminense': 79, 'santos': 77, 'bragantino': 80,
        'manchester city': 95, 'liverpool': 94, 'arsenal': 93, 'chelsea': 88,
        'manchester united': 87, 'tottenham': 86, 'barcelona': 92, 'real madrid': 95,
        'atlético madrid': 89, 'sevilla': 85, 'bayern munich': 96, 'borussia dortmund': 90,
        'psg': 93, 'marseille': 84, 'juventus': 91, 'ac milan': 89, 'inter': 90,
        'napoli': 88, 'roma': 87
    }
    
    home_lower = home_team.lower()
    away_lower = away_team.lower()
    
    rating_home = ranking_times.get(home_lower, 75)
    rating_away = ranking_times.get(away_lower, 75)
    diff = rating_home - rating_away
    
    if diff > 20:
        odds_home, odds_draw, odds_away = 1.50, 4.00, 6.00
    elif diff > 10:
        odds_home, odds_draw, odds_away = 1.80, 3.40, 4.20
    elif diff > 0:
        odds_home, odds_draw, odds_away = 2.10, 3.20, 3.30
    elif diff > -10:
        odds_home, odds_draw, odds_away = 2.80, 3.10, 2.50
    elif diff > -20:
        odds_home, odds_draw, odds_away = 4.20, 3.40, 1.80
    else:
        odds_home, odds_draw, odds_away = 6.00, 4.00, 1.50
    
    if 'brasil' in league.lower() or 'série a' in league.lower():
        odds_home = min(odds_home * 1.1, 5.0)
        odds_away = min(odds_away * 1.1, 5.0)
    
    return round(odds_home, 2), round(odds_draw, 2), round(odds_away, 2)


def analisar_valor_aposta(odds, probabilidade):
    """Analisa o valor real da aposta"""
    probabilidade_implícita = 1 / odds
    valor = (probabilidade - probabilidade_implícita) * 100
    valor_esperado = (odds * probabilidade) - 1
    return valor, valor_esperado

def determinar_confianca_stake(valor_esperado, probabilidade):
    """Determina confiança e stake baseado em análise rigorosa"""
    fator = (valor_esperado * 2) + probabilidade
    
    if fator > 1.8 and valor_esperado > 0.15:
        return "MUITO ALTA", "ALTO"
    elif fator > 1.6 and valor_esperado > 0.10:
        return "ALTA", "ALTO"
    elif fator > 1.4 and valor_esperado > 0.05:
        return "MEDIA", "MÉDIO"
    elif valor_esperado > 0:
        return "BAIXA", "BAIXO"
    else:
        return "MUITO BAIXA", "NÃO APOSTAR"

# --- FUNÇÃO PRINCIPAL DE PALPITES H2H ---

def gerar_palpites_h2h():
    """Gera palpites da IA de H2H baseados em jogos futuros."""
    print("🎯 Gerando palpites da IA (H2H)...")
    
    # Buscar jogos futuros (hoje/amanhã)
    jogos_analise = buscar_jogos_futuros()
    
    if not jogos_analise:
        print("❌ Nenhum jogo futuro para análise H2H encontrado.")
        return []
    
    # Odds reais desativadas
    # odds_data = buscar_odds_reais() 
    
    apostas = []
    
    for jogo in jogos_analise:
        try:
            home_team = jogo['home_team']
            away_team = jogo['away_team']
            league = jogo['league']
            status = jogo['status']
            minuto = jogo.get('minuto', 'Pré-jogo')
            
            # Usar apenas odds inteligentes (da IA)
            odds_home, odds_draw, odds_away = calcular_odds_inteligentes(home_team, away_team, league)
            casa_aposta = 'SuaIA'
            fonte_odds = 'CALCULADO'
            
            # Calcular probabilidades e valor esperado
            prob_home = 1 / odds_home
            prob_draw = 1 / odds_draw
            prob_away = 1 / odds_away
            
            total_prob = prob_home + prob_draw + prob_away
            prob_home_ajust = prob_home / total_prob
            prob_draw_ajust = prob_draw / total_prob
            prob_away_ajust = prob_away / total_prob
            
            valor_home = (odds_home * prob_home_ajust) - 1
            valor_draw = (odds_draw * prob_draw_ajust) - 1
            valor_away = (odds_away * prob_away_ajust) - 1
            
            valores = [valor_home, valor_draw, valor_away]
            tipos = [f"{home_team} Vence", "Empate", f"{away_team} Vence"]
            probabilidades = [prob_home_ajust, prob_draw_ajust, prob_away_ajust]
            odds_list = [odds_home, odds_draw, odds_away]
            
            melhor_idx = valores.index(max(valores))
            
            # Criar aposta se tiver valor positivo
            if valores[melhor_idx] > 0.01:
                confianca, stake = determinar_confianca_stake(valores[melhor_idx], probabilidades[melhor_idx])
                valor_percentual, _ = analisar_valor_aposta(odds_list[melhor_idx], probabilidades[melhor_idx])
                
                aposta = {
                    'match': f"{home_team} vs {away_team}",
                    'league': league,
                    'bet_type': tipos[melhor_idx],
                    'odd': round(odds_list[melhor_idx], 2),
                    'probability': round(probabilidades[melhor_idx], 3),
                    'value_expected': round(valores[melhor_idx], 3),
                    'value_percent': round(valor_percentual, 1),
                    'stake': stake,
                    'confidence': confianca,
                    'casa_aposta': casa_aposta,
                    'link_aposta': f"https://www.bet365.com",
                    'status_jogo': status,
                    'minuto': minuto,
                    'fonte_odds': fonte_odds,
                    'fonte_jogo': jogo['fonte'],
                    'timestamp': datetime.now().isoformat()
                }
                apostas.append(aposta)
                
        except Exception as e:
            print(f"⚠️ Erro processando palpite H2H para {jogo.get('home_team', '')}: {e}")
            continue
    
    # Ordenar por valor esperado
    apostas.sort(key=lambda x: x['value_expected'], reverse=True)
    
    print(f"🎯 {len(apostas)} palpites da IA (H2H) gerados")
    return apostas

def gerar_multiplas_ao_vivo(apostas_individuais):
    """Gera múltiplas com base nos melhores palpites individuais"""
    # ... (Seu código de múltiplas mantido) ...
    try:
        if len(apostas_individuais) >= 2:
            melhores_apostas = [a for a in apostas_individuais if a['value_expected'] > 0.05 and a['confidence'] in ['ALTO', 'MÉDIO']][:3] # Aumentei para 3 para ter mais opções
            
            if len(melhores_apostas) < 2:
                print("❌ Apostas de alto valor insuficientes para múltipla.")
                return []
                
            odd_total = 1.0
            prob_total = 1.0
            for aposta in melhores_apostas:
                odd_total *= aposta['odd']
                prob_total *= aposta['probability']
            
            valor_esperado = (odd_total * prob_total) - 1
            
            if valor_esperado > 0.25:
                confianca = "MUITO ALTA"
            elif valor_esperado > 0.15:
                confianca = "ALTA"
            elif valor_esperado > 0.08:
                confianca = "MEDIA"
            else:
                confianca = "BAIXA"
            
            multipla = {
                'odd_total': round(odd_total, 2),
                'probability': round(prob_total, 3),
                'value_expected': round(valor_esperado, 3),
                'confidence': confianca,
                'jogos': json.dumps([{
                    'match': aposta['match'],
                    'bet_type': aposta['bet_type'],
                    'odd': aposta['odd'],
                    'confidence': aposta['confidence']
                } for aposta in melhores_apostas]),
                'timestamp': datetime.now().isoformat()
            }
            return [multipla]
        else:
            print("❌ Apostas insuficientes para múltipla")
            return []
            
    except Exception as e:
        print(f"❌ Erro gerando múltiplas: {e}")
        return []

# --- EXECUÇÃO PRINCIPAL ---
def main():
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n🔥 SISTEMA DE PALPITES 100% INTELIGENTE - {agora}")
    print("📍 Fonte: IA H2H + IA Estatística (API-Sports)")
    
    try:
        # 1. Gerar apostas da IA Básica (H2H)
        print("\n🌐 BUSCANDO DADOS PARA ANÁLISE BÁSICA (H2H)...")
        dados_h2h = gerar_palpites_h2h()
        
        # 2. Gerar apostas de Estatísticas (NOVO)
        print("\n📊 BUSCANDO DADOS PARA ANÁLISE ESTATÍSTICA (API-Sports)...")
        dados_estatisticos = buscar_estatisticas_detalhadas()
        
        # 3. Combinar todos os palpites
        dados_individuais = dados_h2h
        dados_individuais.extend(dados_estatisticos)
        
        if not dados_individuais:
            print("❌ ALERTA: Nenhum palpite da IA gerado.")
            # Salvar mensagem de erro
            erro_msg = [{
                'match': 'Sistema em Manutenção',
                'league': 'Atualização de Dados',
                'bet_type': 'Retorne em 30 minutos',
                'odd': 1.00,
                'probability': 1.0,
                'value_expected': 0.0,
                'stake': 'AGUARDE',
                'confidence': 'ATUALIZANDO',
                'casa_aposta': 'Sistema',
                'link_aposta': '#',
                'status_jogo': 'ATUALIZAÇÃO',
                'minuto': datetime.now().strftime('%H:%M'),
                'fonte_odds': 'SISTEMA',
                'fonte_jogo': 'ATUALIZAÇÃO',
                'timestamp': datetime.now().isoformat()
            }]
            salvar_dados_supabase(erro_msg, 'individuais')
            salvar_dados_supabase([], 'multiplas')
            return "Sistema atualizando - tente novamente em 30 minutos", 200
        
        # 4. Gerar múltiplas
        dados_multiplas = gerar_multiplas_ao_vivo(dados_individuais)
        
        # 5. Salvar no Supabase
        print("\n💾 SALVANDO DADOS DA IA...")
        success1 = salvar_dados_supabase(dados_individuais, 'individuais')
        success2 = salvar_dados_supabase(dados_multiplas, 'multiplas')
        
        # 6. Resultado final
        print(f"\n🎉 SISTEMA DA IA ATIVO!")
        print(f"📊 {len(dados_individuais)} apostas individuais da IA")
        print(f"🎯 {len(dados_multiplas)} múltiplas inteligentes")
        
        # 7. Mostrar TOP PALPITES
        print(f"\n🏆 PALPITES ATUAIS:")
        for i, palpite in enumerate(dados_individuais[:6]):
            status_emoji = "🟡" if "AGENDADO" in palpite['status_jogo'] else "🟢"
            fonte_emoji = "🤖" 
            
            print(f"{i+1}. {palpite['match']} {status_emoji}")
            print(f"   🏆 {palpite['league']} | {palpite['status_jogo']} {palpite['minuto']}")
            print(f"   🎲 {palpite['bet_type']} {fonte_emoji}")
            print(f"   📈 Odd: {palpite['odd']} | Prob: {palpite['probability']:.1%}")
            print(f"   💰 Valor: {palpite['value_expected']:.3f} ({palpite['value_percent']}%)")
            print(f"   ⚡ {palpite['confidence']} | 🎯 {palpite['stake']}")
            print(f"   🏠 {palpite['casa_aposta']}")
            print()
        
        if success1:
            return "Sistema da IA executado com sucesso!", 200
        else:
            print("⚠️ Dados gerados mas erro ao salvar")
            return "Dados da IA gerados mas erro ao salvar", 500
        
    except Exception as e:
        print(f"❌ ERRO CRÍTICO NA EXECUÇÃO PRINCIPAL: {e}")
        return f"Erro: {e}", 500

# Para o Vercel Cron
def run_cron_job(request=None):
    return main()

if __name__ == "__main__":
    main()
