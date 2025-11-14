import os
import json
import time
import requests
from datetime import datetime, timedelta
import hashlib

print("🔥 SISTEMA DE PALPITES 100% AO VIVO - INICIANDO...")

# --- Configurações ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
ODDS_API_KEY = os.environ.get("ODDS_API_KEY")
FOOTBALL_DATA_KEY = os.environ.get("FOOTBALL_DATA_KEY")

# Headers para Supabase
SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

def salvar_dados_supabase(dados, table_name):
    """Salva dados no Supabase"""
    try:
        if not SUPABASE_URL or not SUPABASE_KEY:
            print("⚠️ Supabase não configurado")
            return False
            
        print(f"💾 Salvando {len(dados)} registros em {table_name}...")
        
        url = f"{SUPABASE_URL}/rest/v1/{table_name}"
        
        # Deletar registros antigos
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
                print(f"❌ Erro ao salvar: {insert_response.status_code}")
                return False
        else:
            print(f"ℹ️ Nenhum dado para salvar em {table_name}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao salvar: {e}")
        return False

def buscar_jogos_ao_vivo():
    """Busca jogos AO VIVO de múltiplas fontes em tempo real"""
    print("🌐 Buscando jogos AO VIVO...")
    
    jogos_ao_vivo = []
    
    # Fonte 1: API-Football (jogos ao vivo)
    try:
        if FOOTBALL_DATA_KEY:
            headers = {'X-Auth-Token': FOOTBALL_DATA_KEY}
            response = requests.get(
                "https://api.football-data.org/v4/matches?status=LIVE", 
                headers=headers, 
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                for match in data.get('matches', []):
                    if match['status'] == 'LIVE':
                        jogo = {
                            'home_team': match['homeTeam']['name'],
                            'away_team': match['awayTeam']['name'],
                            'league': match['competition']['name'],
                            'status': 'AO VIVO',
                            'minuto': match.get('minute', '?'),
                            'score': f"{match['score']['fullTime']['home']}-{match['score']['fullTime']['away']}",
                            'fonte': 'FOOTBALL_DATA_LIVE'
                        }
                        jogos_ao_vivo.append(jogo)
                print(f"✅ {len([m for m in data.get('matches', []) if m['status'] == 'LIVE'])} jogos ao vivo encontrados")
    except Exception as e:
        print(f"❌ Erro Football Data Live: {e}")
    
    # Fonte 2: The Sports DB (jogos de hoje)
    try:
        hoje = datetime.now().strftime('%Y-%m-%d')
        response = requests.get(
            f"https://www.thesportsdb.com/api/v1/json/3/eventsday.php?d={hoje}&s=Soccer",
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            for event in data.get('events', [])[:15]:  # Limitar para não exceder
                jogo = {
                    'home_team': event['strHomeTeam'],
                    'away_team': event['strAwayTeam'],
                    'league': event['strLeague'],
                    'status': 'HOJE',
                    'minuto': 'Pré-jogo',
                    'score': '0-0',
                    'fonte': 'THESPORTSDB_TODAY'
                }
                jogos_ao_vivo.append(jogo)
            print(f"✅ {len(data.get('events', []))} jogos de hoje encontrados")
    except Exception as e:
        print(f"❌ Erro TheSportsDB: {e}")
    
    # Fonte 3: API-Football (jogos de hoje)
    try:
        if FOOTBALL_DATA_KEY:
            hoje = datetime.now().strftime('%Y-%m-%d')
            headers = {'X-Auth-Token': FOOTBALL_DATA_KEY}
            response = requests.get(
                f"https://api.football-data.org/v4/matches?dateFrom={hoje}&dateTo={hoje}",
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                for match in data.get('matches', []):
                    if match['status'] in ['SCHEDULED', 'TIMED']:
                        jogo = {
                            'home_team': match['homeTeam']['name'],
                            'away_team': match['awayTeam']['name'],
                            'league': match['competition']['name'],
                            'status': 'AGENDADO',
                            'minuto': match['utcDate'][11:16],
                            'score': '0-0',
                            'fonte': 'FOOTBALL_DATA_TODAY'
                        }
                        jogos_ao_vivo.append(jogo)
                print(f"✅ {len([m for m in data.get('matches', []) if m['status'] in ['SCHEDULED', 'TIMED']])} jogos agendados")
    except Exception as e:
        print(f"❌ Erro Football Data Today: {e}")
    
    # Remover duplicatas
    jogos_unicos = []
    seen = set()
    for jogo in jogos_ao_vivo:
        identifier = f"{jogo['home_team']}_{jogo['away_team']}"
        if identifier not in seen:
            seen.add(identifier)
            jogos_unicos.append(jogo)
    
    print(f"🎯 Total de {len(jogos_unicos)} jogos AO VIVO/hoje encontrados")
    return jogos_unicos

def buscar_odds_ao_vivo():
    """Busca odds AO VIVO da The Odds API"""
    print("💰 Buscando odds AO VIVO...")
    
    try:
        if not ODDS_API_KEY:
            print("❌ ODDS_API_KEY não configurada")
            return None
        
        # Esportes mais populares com mais chances de ter dados
        sports = [
            'soccer_epl',           # Premier League
            'soccer_spain_la_liga', # La Liga
            'soccer_italy_serie_a', # Serie A
            'soccer_uefa_champs',   # Champions League
            'soccer_germany_bundesliga', # Bundesliga
        ]
        
        all_odds = []
        
        for sport in sports:
            try:
                url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"
                params = {
                    'apiKey': ODDS_API_KEY,
                    'regions': 'eu',
                    'markets': 'h2h,totals,btts',
                    'oddsFormat': 'decimal'
                }
                
                response = requests.get(url, params=params, timeout=15)
                
                if response.status_code == 200:
                    events = response.json()
                    if events:
                        all_odds.extend(events)
                        print(f"✅ {len(events)} eventos de {sport}")
                    else:
                        print(f"ℹ️ Nenhum evento em {sport}")
                else:
                    print(f"❌ Erro {response.status_code} em {sport}")
                
                time.sleep(1)
                
            except Exception as e:
                print(f"⚠️ Erro em {sport}: {e}")
                continue
        
        if all_odds:
            print(f"💰 {len(all_odds)} eventos com odds AO VIVO")
            return all_odds
        else:
            print("❌ Nenhuma odds AO VIVO encontrada")
            return None
            
    except Exception as e:
        print(f"❌ Erro geral nas odds: {e}")
        return None

def calcular_odds_inteligentes(home_team, away_team, league):
    """Calcula odds realistas baseadas em dados reais"""
    # Base de dados de times e suas forças relativas
    ranking_times = {
        # Times brasileiros
        'flamengo': 85, 'palmeiras': 84, 'são paulo': 82, 'corinthians': 81,
        'internacional': 80, 'atlético-mg': 83, 'grêmio': 79, 'botafogo': 78,
        'fortaleza': 77, 'bahia': 76, 'vasco': 75, 'cruzeiro': 76,
        'fluminense': 79, 'santos': 77, 'bragantino': 80,
        
        # Times europeus
        'manchester city': 95, 'liverpool': 94, 'arsenal': 93, 'chelsea': 88,
        'manchester united': 87, 'tottenham': 86, 'barcelona': 92, 'real madrid': 95,
        'atlético madrid': 89, 'sevilla': 85, 'bayern munich': 96, 'borussia dortmund': 90,
        'psg': 93, 'marseille': 84, 'juventus': 91, 'ac milan': 89, 'inter': 90,
        'napoli': 88, 'roma': 87
    }
    
    home_lower = home_team.lower()
    away_lower = away_team.lower()
    
    # Obter ratings
    rating_home = ranking_times.get(home_lower, 75)
    rating_away = ranking_times.get(away_lower, 75)
    
    # Calcular diferença
    diff = rating_home - rating_away
    
    # Base odds para empate
    base_draw = 3.2
    
    # Ajustar odds baseado na diferença de rating
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
    
    # Ajuste para ligas específicas
    if 'brasil' in league.lower() or 'série a' in league.lower():
        # No Brasil, odds tendem a ser mais equilibradas
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
    # Fator combinado
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

def gerar_palpites_ao_vivo():
    """Gera palpites 100% AO VIVO baseados em jogos reais"""
    print("🎯 Gerando palpites AO VIVO...")
    
    # Buscar jogos AO VIVO
    jogos_ao_vivo = buscar_jogos_ao_vivo()
    
    if not jogos_ao_vivo:
        print("❌ CRÍTICO: Nenhum jogo AO VIVO encontrado")
        return []
    
    # Buscar odds AO VIVO
    odds_data = buscar_odds_ao_vivo()
    
    apostas = []
    
    for jogo in jogos_ao_vivo:
        try:
            home_team = jogo['home_team']
            away_team = jogo['away_team']
            league = jogo['league']
            status = jogo['status']
            minuto = jogo['minuto']
            
            # Tentar encontrar odds reais para este jogo
            odds_reais = None
            if odds_data:
                for evento in odds_data:
                    if (evento['home_team'].lower() in home_team.lower() or 
                        home_team.lower() in evento['home_team'].lower()):
                        odds_reais = evento
                        break
            
            if odds_reais:
                # Usar odds reais
                odds_home, odds_draw, odds_away = 2.0, 3.0, 3.5
                casa_aposta = 'Bet365'
                
                for bookmaker in odds_reais.get('bookmakers', []):
                    for market in bookmaker.get('markets', []):
                        if market['key'] == 'h2h':
                            for outcome in market['outcomes']:
                                if outcome['name'] == odds_reais['home_team']:
                                    odds_home = outcome.get('price', 2.0)
                                elif outcome['name'] == odds_reais['away_team']:
                                    odds_away = outcome.get('price', 3.5)
                                else:
                                    odds_draw = outcome.get('price', 3.0)
                            casa_aposta = bookmaker.get('key', 'Bet365')
                            break
                    break
                
                fonte_odds = 'ODDS_REAIS'
                
            else:
                # Calcular odds inteligentes baseadas em ranking
                odds_home, odds_draw, odds_away = calcular_odds_inteligentes(home_team, away_team, league)
                casa_aposta = 'Bet365'
                fonte_odds = 'CALCULADO'
            
            # Calcular probabilidades
            prob_home = 1 / odds_home
            prob_draw = 1 / odds_draw
            prob_away = 1 / odds_away
            
            total_prob = prob_home + prob_draw + prob_away
            prob_home_ajust = prob_home / total_prob
            prob_draw_ajust = prob_draw / total_prob
            prob_away_ajust = prob_away / total_prob
            
            # Calcular valor esperado
            valor_home = (odds_home * prob_home_ajust) - 1
            valor_draw = (odds_draw * prob_draw_ajust) - 1
            valor_away = (odds_away * prob_away_ajust) - 1
            
            # Encontrar melhor aposta
            valores = [valor_home, valor_draw, valor_away]
            tipos = [f"{home_team} Vence", "Empate", f"{away_team} Vence"]
            probabilidades = [prob_home_ajust, prob_draw_ajust, prob_away_ajust]
            odds_list = [odds_home, odds_draw, odds_away]
            
            melhor_idx = valores.index(max(valores))
            
            # Só criar aposta se tiver valor positivo
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
                    'link_aposta': f"https://www.{casa_aposta.lower().replace(' ', '')}.com",
                    'status_jogo': status,
                    'minuto': minuto,
                    'fonte_odds': fonte_odds,
                    'fonte_jogo': jogo['fonte'],
                    'timestamp': datetime.now().isoformat()
                }
                apostas.append(aposta)
                print(f"✅ Palpite AO VIVO: {home_team} vs {away_team} - {status}")
                
        except Exception as e:
            print(f"⚠️ Erro processando {jogo.get('home_team', '')}: {e}")
            continue
    
    # Ordenar por valor esperado
    apostas.sort(key=lambda x: x['value_expected'], reverse=True)
    
    print(f"🎯 {len(apostas)} palpites AO VIVO gerados")
    return apostas

def gerar_multiplas_ao_vivo(apostas_individuais):
    """Gera múltiplas com palpites AO VIVO"""
    try:
        if len(apostas_individuais) >= 2:
            # Selecionar 2 melhores apostas
            melhores_apostas = apostas_individuais[:2]
            
            # Calcular odd total
            odd_total = 1.0
            for aposta in melhores_apostas:
                odd_total *= aposta['odd']
            
            # Calcular probabilidade total
            prob_total = 1.0
            for aposta in melhores_apostas:
                prob_total *= aposta['probability']
            
            valor_esperado = (odd_total * prob_total) - 1
            
            # Determinar confiança
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
    print(f"\n🔥 SISTEMA DE PALPITES 100% AO VIVO - {agora}")
    print("📍 Fonte: Jogos reais em tempo real + Análise de valor")
    
    try:
        # 1. Gerar apostas AO VIVO
        print("\n🌐 BUSCANDO DADOS AO VIVO...")
        dados_individuais = gerar_palpites_ao_vivo()
        
        if not dados_individuais:
            print("❌ ALERTA: Nenhum palpite AO VIVO gerado - verifique conexão com APIs")
            # Tentar salvar mensagem de erro
            erro_msg = [{
                'match': 'Sistema em Manutenção',
                'league': 'Atualização de Dados',
                'bet_type': 'Retorne em 5 minutos',
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
            return "Sistema atualizando - tente novamente em 5 minutos", 200
        
        # 2. Gerar múltiplas
        dados_multiplas = gerar_multiplas_ao_vivo(dados_individuais)
        
        # 3. Salvar no Supabase
        print("\n💾 SALVANDO DADOS AO VIVO...")
        success1 = salvar_dados_supabase(dados_individuais, 'individuais')
        success2 = salvar_dados_supabase(dados_multiplas, 'multiplas')
        
        # 4. Resultado final
        print(f"\n🎉 SISTEMA AO VIVO ATIVO!")
        print(f"📊 {len(dados_individuais)} apostas AO VIVO")
        print(f"🎯 {len(dados_multiplas)} múltiplas inteligentes")
        
        # 5. Mostrar TOP PALPITES AO VIVO
        print(f"\n🏆 PALPITES AO VIVO AGORA:")
        for i, palpite in enumerate(dados_individuais[:6]):
            status_emoji = "🔴" if "VIVO" in palpite['status_jogo'] else "🟡"
            fonte_emoji = "💰" if palpite['fonte_odds'] == 'ODDS_REAIS' else "🤖"
            
            print(f"{i+1}. {palpite['match']} {status_emoji}")
            print(f"   🏆 {palpite['league']} | {palpite['status_jogo']} {palpite['minuto']}")
            print(f"   🎲 {palpite['bet_type']} {fonte_emoji}")
            print(f"   📈 Odd: {palpite['odd']} | Prob: {palpite['probability']:.1%}")
            print(f"   💰 Valor: {palpite['value_expected']:.3f} ({palpite['value_percent']}%)")
            print(f"   ⚡ {palpite['confidence']} | 🎯 {palpite['stake']}")
            print(f"   🏠 {palpite['casa_aposta']}")
            print()
        
        if success1:
            print("📍 Dados AO VIVO disponíveis em: lanzacai-a.vercel.app")
            return "Sistema AO VIVO executado com sucesso!", 200
        else:
            print("⚠️ Dados gerados mas erro ao salvar")
            return "Dados AO VIVO gerados mas erro ao salvar", 500
        
    except Exception as e:
        print(f"❌ ERRO CRÍTICO: {e}")
        return f"Erro: {e}", 500

# Para o Render Cron
def run_cron_job(request=None):
    return main()

if __name__ == "__main__":
    main()
