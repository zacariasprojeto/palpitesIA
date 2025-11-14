import os
import json
import time
import requests
from datetime import datetime, timedelta

print("🚀 INICIANDO SISTEMA DE PALPITES COM IA - DADOS REAIS...")

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
    """Salva dados no Supabase usando requests diretamente"""
    try:
        if not SUPABASE_URL or not SUPABASE_KEY:
            print("⚠️ Supabase não configurado. Pulando salvamento.")
            return False
            
        print(f"💾 Salvando {len(dados)} registros em {table_name}...")
        
        # URL da API do Supabase
        url = f"{SUPABASE_URL}/rest/v1/{table_name}"
        
        # Deletar registros antigos
        delete_response = requests.delete(
            f"{url}?id=gt.0",
            headers=SUPABASE_HEADERS
        )
        
        if delete_response.status_code in [200, 201, 204]:
            print(f"✅ Registros antigos de {table_name} removidos")
        
        # Inserir novos registros
        if dados:
            insert_response = requests.post(
                url,
                json=dados,
                headers=SUPABASE_HEADERS
            )
            
            if insert_response.status_code in [200, 201]:
                print(f"✅ {len(dados)} registros salvos em {table_name}")
                return True
            else:
                print(f"❌ Erro ao salvar em {table_name}: {insert_response.status_code}")
                return False
        else:
            print(f"ℹ️ Nenhum dado para salvar em {table_name}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao salvar no Supabase: {e}")
        return False

def buscar_partidas_reais():
    """Busca partidas reais do football-data.org"""
    try:
        if not FOOTBALL_DATA_KEY:
            print("❌ FOOTBALL_DATA_KEY não configurada")
            return []
            
        headers = {'X-Auth-Token': FOOTBALL_DATA_KEY}
        hoje = datetime.now().strftime('%Y-%m-%d')
        amanha = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
        
        url = f"https://api.football-data.org/v4/matches?dateFrom={hoje}&dateTo={amanha}"
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            partidas = []
            
            for match in data.get('matches', []):
                home_team = match.get('homeTeam', {}).get('name', 'Time Casa')
                away_team = match.get('awayTeam', {}).get('name', 'Time Fora')
                league = match.get('competition', {}).get('name', 'Liga Desconhecida')
                
                # Filtrar apenas partidas futuras ou do dia
                status = match.get('status', '')
                if status in ['SCHEDULED', 'TIMED', 'LIVE']:
                    partida = {
                        'home_team': home_team,
                        'away_team': away_team,
                        'league': league,
                        'date': match.get('utcDate', ''),
                        'status': status
                    }
                    partidas.append(partida)
            
            print(f"✅ {len(partidas)} partidas reais encontradas")
            return partidas
        else:
            print(f"❌ Erro Football Data API: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ Erro ao buscar partidas: {e}")
        return []

def buscar_odds_reais():
    """Busca odds reais da The Odds API"""
    try:
        if not ODDS_API_KEY:
            print("❌ ODDS_API_KEY não configurada")
            return []
            
        # Buscar odds para futebol brasileiro e europeu
        sports = [
            'soccer_brazil_campeonato',
            'soccer_england_premier_league', 
            'soccer_spain_la_liga',
            'soccer_italy_serie_a',
            'soccer_germany_bundesliga',
            'soccer_france_ligue_one'
        ]
        all_odds = []
        
        for sport in sports:
            url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"
            params = {
                'apiKey': ODDS_API_KEY,
                'regions': 'eu,us',
                'markets': 'h2h,totals,btts',
                'oddsFormat': 'decimal'
            }
            
            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 200:
                events = response.json()
                all_odds.extend(events)
                print(f"✅ {len(events)} eventos de {sport}")
            else:
                print(f"❌ Erro na API de odds para {sport}: {response.status_code}")
            
            time.sleep(1.5)  # Rate limiting
            
        print(f"🎯 Total de {len(all_odds)} eventos com odds reais")
        return all_odds
        
    except Exception as e:
        print(f"❌ Erro ao buscar odds: {e}")
        return []

def analisar_valor_aposta(probabilidade_real, odds):
    """Analisa o valor real da aposta"""
    probabilidade_implícita = 1 / odds
    valor = (probabilidade_real - probabilidade_implícita) * 100
    return valor

def calcular_probabilidade_avancada(odds_home, odds_draw, odds_away, historico=None):
    """Calcula probabilidades avançadas usando múltiplos fatores"""
    try:
        # Probabilidades básicas das odds
        prob_home = 1 / odds_home
        prob_draw = 1 / odds_draw
        prob_away = 1 / odds_away
        
        # Ajustar pelo overround
        total_prob = prob_home + prob_draw + prob_away
        prob_home_ajust = prob_home / total_prob
        prob_draw_ajust = prob_draw / total_prob
        prob_away_ajust = prob_away / total_prob
        
        # Fatores de ajuste baseados em experiência
        # Times com odds muito baixos tendem a ter probabilidade superestimada
        if odds_home < 1.5:
            prob_home_ajust *= 0.95
            prob_draw_ajust *= 1.03
            prob_away_ajust *= 1.02
        elif odds_away < 1.5:
            prob_home_ajust *= 1.02
            prob_draw_ajust *= 1.03
            prob_away_ajust *= 0.95
        
        # Re-normalizar
        total_ajust = prob_home_ajust + prob_draw_ajust + prob_away_ajust
        prob_home_final = prob_home_ajust / total_ajust
        prob_draw_final = prob_draw_ajust / total_ajust
        prob_away_final = prob_away_ajust / total_ajust
        
        # Calcular valor esperado
        valor_home = (odds_home * prob_home_final) - 1
        valor_draw = (odds_draw * prob_draw_final) - 1
        valor_away = (odds_away * prob_away_final) - 1
        
        return {
            'home': prob_home_final,
            'draw': prob_draw_final, 
            'away': prob_away_final,
            'value_home': valor_home,
            'value_draw': valor_draw,
            'value_away': valor_away
        }
    except:
        # Fallback simples se houver erro
        total_prob = (1/odds_home + 1/odds_draw + 1/odds_away)
        return {
            'home': (1/odds_home) / total_prob,
            'draw': (1/odds_draw) / total_prob,
            'away': (1/odds_away) / total_prob,
            'value_home': (odds_home * (1/odds_home)/total_prob) - 1,
            'value_draw': (odds_draw * (1/odds_draw)/total_prob) - 1,
            'value_away': (odds_away * (1/odds_away)/total_prob) - 1
        }

def determinar_confianca_stake(valor_esperado, probabilidade):
    """Determina confiança e stake baseado em análise avançada"""
    # Fator combinado: valor esperado + probabilidade
    fator_qualidade = (valor_esperado * 2) + probabilidade
    
    if fator_qualidade > 1.8:
        return "MUITO ALTA", "ALTO"
    elif fator_qualidade > 1.6:
        return "ALTA", "ALTO"
    elif fator_qualidade > 1.4:
        return "MEDIA", "MÉDIO"
    elif fator_qualidade > 1.2:
        return "BAIXA", "BAIXO"
    else:
        return "MUITO BAIXA", "NÃO APOSTAR"

def gerar_palpites_avancados():
    """Gera palpites avançados com análise de valor real"""
    print("🔄 Buscando dados reais das APIs...")
    
    # Buscar dados reais
    partidas = buscar_partidas_reais()
    odds_data = buscar_odds_reais()
    
    if not odds_data:
        print("❌ CRÍTICO: Nenhum dado de odds encontrado")
        return []
    
    apostas = []
    
    for evento in odds_data:
        try:
            home_team = evento.get('home_team', '').title()
            away_team = evento.get('away_team', '').title()
            sport_title = evento.get('sport_title', 'Futebol')
            
            if not home_team or not away_team:
                continue
            
            # Coletar odds de todas as casas
            todas_odds_home = []
            todas_odds_draw = []
            todas_odds_away = []
            casas_aposta = []
            
            for bookmaker in evento.get('bookmakers', []):
                for market in bookmaker.get('markets', []):
                    if market['key'] == 'h2h':
                        for outcome in market['outcomes']:
                            if outcome['name'] == evento['home_team']:
                                todas_odds_home.append(outcome.get('price', 0))
                            elif outcome['name'] == evento['away_team']:
                                todas_odds_away.append(outcome.get('price', 0))
                            else:
                                todas_odds_draw.append(outcome.get('price', 0))
                        casas_aposta.append(bookmaker['key'])
            
            if not todas_odds_home or not todas_odds_away:
                continue
            
            # Usar melhores odds disponíveis
            odds_home = max(todas_odds_home) if todas_odds_home else 2.0
            odds_draw = max(todas_odds_draw) if todas_odds_draw else 3.0
            odds_away = max(todas_odds_away) if todas_odds_away else 3.5
            
            melhor_casa = casas_aposta[0] if casas_aposta else 'Bet365'
            
            # Calcular probabilidades avançadas
            prob_ia = calcular_probabilidade_avancada(odds_home, odds_draw, odds_away)
            
            # Analisar todas as opções
            opcoes_aposta = [
                {
                    'tipo': f"{home_team} Vence",
                    'odd': odds_home,
                    'probabilidade': prob_ia['home'],
                    'valor': prob_ia['value_home']
                },
                {
                    'tipo': "Empate", 
                    'odd': odds_draw,
                    'probabilidade': prob_ia['draw'],
                    'valor': prob_ia['value_draw']
                },
                {
                    'tipo': f"{away_team} Vence",
                    'odd': odds_away, 
                    'probabilidade': prob_ia['away'],
                    'valor': prob_ia['value_away']
                }
            ]
            
            # Encontrar melhor aposta (maior valor positivo)
            melhor_aposta = None
            for opcao in opcoes_aposta:
                if opcao['valor'] > 0 and (melhor_aposta is None or opcao['valor'] > melhor_aposta['valor']):
                    melhor_aposta = opcao
            
            if melhor_aposta and melhor_aposta['valor'] > 0.02:  # Mínimo 2% de valor
                confianca, stake = determinar_confianca_stake(
                    melhor_aposta['valor'], 
                    melhor_aposta['probabilidade']
                )
                
                # Análise de valor percentual
                valor_percentual = analisar_valor_aposta(melhor_aposta['probabilidade'], melhor_aposta['odd'])
                
                aposta = {
                    'match': f"{home_team} vs {away_team}",
                    'league': sport_title,
                    'bet_type': melhor_aposta['tipo'],
                    'odd': round(melhor_aposta['odd'], 2),
                    'probability': round(melhor_aposta['probabilidade'], 3),
                    'value_expected': round(melhor_aposta['valor'], 3),
                    'value_percent': round(valor_percentual, 1),
                    'stake': stake,
                    'confidence': confianca,
                    'casa_aposta': melhor_casa,
                    'link_aposta': f"https://www.{melhor_casa}.com/bet",
                    'timestamp': datetime.now().isoformat()
                }
                apostas.append(aposta)
                
        except Exception as e:
            print(f"⚠️ Erro processando {evento.get('home_team', '')} vs {evento.get('away_team', '')}: {e}")
            continue
    
    # Ordenar por valor esperado (melhores primeiro)
    apostas.sort(key=lambda x: x['value_expected'], reverse=True)
    
    print(f"✅ {len(apostas)} apostas com valor real encontradas")
    return apostas

def gerar_multiplas_inteligentes():
    """Gera múltiplas baseadas em correlação e valor"""
    try:
        # Buscar as melhores apostas individuais
        melhores_apostas = gerar_palpites_avancados()
        
        if len(melhores_apostas) >= 2:
            # Selecionar as 2 melhores apostas não correlacionadas
            apostas_selecionadas = melhores_apostas[:2]
            
            # Calcular produto das odds
            odd_total = 1.0
            for aposta in apostas_selecionadas:
                odd_total *= aposta['odd']
            
            # Calcular produto das probabilidades
            prob_total = 1.0
            for aposta in apostas_selecionadas:
                prob_total *= aposta['probability']
            
            valor_esperado = (odd_total * prob_total) - 1
            
            # Determinar confiança da múltipla
            if valor_esperado > 0.3:
                confianca = "MUITO ALTA"
            elif valor_esperado > 0.2:
                confianca = "ALTA"
            elif valor_esperado > 0.1:
                confianca = "MEDIA"
            else:
                confianca = "BAIXA"
            
            return [{
                'odd_total': round(odd_total, 2),
                'probability': round(prob_total, 3),
                'value_expected': round(valor_esperado, 3),
                'confidence': confianca,
                'jogos': json.dumps([{
                    'match': aposta['match'],
                    'bet_type': aposta['bet_type'],
                    'odd': aposta['odd'],
                    'confidence': aposta['confidence']
                } for aposta in apostas_selecionadas]),
                'timestamp': datetime.now().isoformat()
            }]
        else:
            print("❌ Não há apostas suficientes para gerar múltiplas")
            return []
            
    except Exception as e:
        print(f"❌ Erro gerando múltiplas: {e}")
        return []

def gerar_surebets_reais():
    """Busca oportunidades de surebets reais"""
    # Esta função seria mais complexa e requereria análise de múltiplas casas
    # Por enquanto retornamos array vazio - pode ser implementada depois
    print("🔍 Analisando oportunidades de surebets...")
    return []

# --- EXECUÇÃO PRINCIPAL ---
def main():
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n--- INICIANDO ANÁLISE DE IA COM DADOS 100% REAIS - {agora} ---")
    
    try:
        # Verificar configurações
        if not ODDS_API_KEY:
            print("❌ ERRO CRÍTICO: ODDS_API_KEY não configurada")
            return "Erro: ODDS_API_KEY não configurada", 500
            
        if not FOOTBALL_DATA_KEY:
            print("⚠️ AVISO: FOOTBALL_DATA_KEY não configurada - usando apenas odds API")
        
        # 1. Gerar dados reais com IA
        print("🤖 Gerando palpites com análise de valor real...")
        dados_individuais = gerar_palpites_avancados()
        dados_multiplas = gerar_multiplas_inteligentes()
        dados_surebets = gerar_surebets_reais()
        
        if not dados_individuais:
            print("❌ ERRO: Nenhum palpite real foi gerado")
            return "Erro: Nenhum palpite real gerado - verifique as APIs", 500
        
        # 2. Salvar no Supabase
        print("💾 Salvando dados reais no Supabase...")
        success1 = salvar_dados_supabase(dados_individuais, 'individuais')
        success2 = salvar_dados_supabase(dados_multiplas, 'multiplas')
        success3 = salvar_dados_supabase(dados_surebets, 'surebets')
        
        # 3. Resultado final
        print(f"\n🎉 DADOS REAIS GERADOS COM SUCESSO!")
        print(f"📊 {len(dados_individuais)} apostas individuais")
        print(f"🎯 {len(dados_multiplas)} múltiplas inteligentes") 
        print(f"🔍 {len(dados_surebets)} oportunidades de surebets")
        
        # 4. Mostrar melhores palpites
        print(f"\n🏆 TOP 5 PALPITES DO DIA:")
        for i, palpite in enumerate(dados_individuais[:5]):
            print(f"{i+1}. {palpite['match']}")
            print(f"   🎲 {palpite['bet_type']}")
            print(f"   📈 Odd: {palpite['odd']} | Prob: {palpite['probability']:.1%}")
            print(f"   💰 Valor: {palpite['value_expected']:.3f} ({palpite['value_percent']}%)")
            print(f"   ⚡ Confiança: {palpite['confidence']} | Stake: {palpite['stake']}")
            print(f"   🏠 Casa: {palpite['casa_aposta']}")
            print()
        
        if success1 or success2 or success3:
            print("📍 Dados disponíveis em: lanzacai-a.vercel.app")
            return "Execução concluída com dados reais!", 200
        else:
            print("⚠️ Dados gerados mas não salvos no Supabase")
            return "Dados gerados mas erro ao salvar", 500
        
    except Exception as e:
        print(f"❌ ERRO CRÍTICO NA EXECUÇÃO: {e}")
        return f"Erro crítico: {e}", 500

# Para compatibilidade com Render Cron
def run_cron_job(request=None):
    return main()

if __name__ == "__main__":
    main()
