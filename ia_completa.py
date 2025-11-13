# ia_completa.py - VERSÃO FINAL COM INTEGRAÇÃO SUPABASE (PARA RODAR NO RENDER CRON JOB)
import json
from datetime import datetime
import random
import os
from supabase import create_client, Client
from typing import List, Dict, Any

# -----------------------------------------------------------------
# 🎯 CONFIGURAÇÃO SUPABASE (O SERVIDOR DE DADOS)
# -----------------------------------------------------------------
# Use as chaves de ambiente do Render, se configuradas.
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://kctzwwczcthjmdgvxuks.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtjdHp3d2N6Y3Roam1kZ3Z4dWtzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjI5ODIwNDYsImV4cCI6MjA3ODU1ODA0Nn0.HafwqrEnJ5Slm3wRg4_KEvGHiTuNJafztVfWbuSZ_84")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print(f"✅ Supabase inicializado e conectado ao URL: {SUPABASE_URL}")
except Exception as e:
    print(f"❌ Erro Crítico ao inicializar Supabase: {e}")
    supabase = None

# -----------------------------------------------------------------
# CLASSE PRINCIPAL DA IA (Lógica de Mock e Geração de Dados)
# -----------------------------------------------------------------
class LancacaIACompleta:
    def __init__(self):
        self.casas_aposta = {
            'betano': {'nome': 'Betano', 'url_base': 'https://betano.com', 'cor': '#00ff88', 'icone': '🎯'},
            'bet365': {'nome': 'Bet365', 'url_base': 'https://bet365.com', 'cor': '#00aaff', 'icone': '⚡'},
            'sportingbet': {'nome': 'Sportingbet', 'url_base': 'https://sportingbet.com', 'cor': '#ffaa00', 'icone': '🔥'}
        }
        self.jogos_hoje = self._gerar_jogos_mock()

    # (MÉTODOS INTERNOS: _gerar_jogos_mock, traduzir_tipo, calcular_stake, calcular_confianca, gerar_link_aposta)
    def _gerar_jogos_mock(self):
        return [
            {'partida': 'Man City vs Liverpool', 'campeonato': 'PREMIER LEAGUE', 'hora': '16:30', 'odds': {'betano': {'over_2.5': 1.85}, 'bet365': {'over_2.5': 1.80}}},
            {'partida': 'Vasco vs Cruzeiro', 'campeonato': 'BRASILEIRÃO SÉRIE A', 'hora': '19:00', 'odds': {'sportingbet': {'casa': 2.10}, 'betano': {'casa': 2.05}}},
            {'partida': 'Barcelona vs Real Madrid', 'campeonato': 'LA LIGA', 'hora': '21:00', 'odds': {'betano': {'ambos_marcam': 1.70}, 'bet365': {'ambos_marcam': 1.65}}}
        ]
    
    def traduzir_tipo(self, tipo):
        traducoes = {'over_2.5': 'Mais de 2.5 Gols', 'ambos_marcam': 'Ambos Marcam', 'casa': 'Vitória Casa', 'fora': 'Vitória Fora'}
        return traducoes.get(tipo, tipo)

    def calcular_stake(self, valor):
        if valor > 0.20: return "ALTO (4-5%)"
        elif valor > 0.15: return "MÉDIO-ALTO (3-4%)"
        elif valor > 0.10: return "MÉDIO (2-3%)"
        elif valor > 0.05: return "BAIXO (1-2%)"
        else: return "MÍNIMO (0.5-1%)"
    
    def calcular_confianca(self):
        return "ALTA" 

    def gerar_link_aposta(self, casa, partida, tipo_aposta):
        base = self.casas_aposta.get(casa, {}).get('url_base', 'https://aposta.com')
        partida_slug = partida.replace(' ', '_').replace('vs', 'x')
        tipo_slug = tipo_aposta.replace(' ', '-').replace('.', '')
        return f"{base}/match/{partida_slug}/{tipo_slug}"

    def analisar_jogos(self):
        apostas_individuais = self._gerar_value_bets()
        apostas_multiplas = self._gerar_multiplas_mock(apostas_individuais)
        apostas_surebets = self._gerar_surebets_mock() 

        self._salvar_dados_no_supabase(apostas_individuais, apostas_multiplas, apostas_surebets)

    def _gerar_value_bets(self):
        apostas_recomendadas = []
        
        for jogo in self.jogos_hoje:
            for casa, mercados in jogo['odds'].items():
                for tipo, odd in mercados.items():
                    prob_ia = random.uniform(0.65, 0.90) 
                    valor_esperado = (odd * prob_ia) - 1
                    
                    if valor_esperado > 0.05:
                        casa_info = self.casas_aposta.get(casa, {})
                        
                        aposta = {
                            'match': jogo['partida'], 
                            'league': jogo['campeonato'], 
                            'bet_type': self.traduzir_tipo(tipo), 
                            'odd': round(odd, 2), 
                            'value_expected': round(valor_esperado, 4), 
                            'confidence': self.calcular_confianca(), 
                            'probabilidade': round(prob_ia, 4),
                            'stake': self.calcular_stake(valor_esperado),
                            'casa_aposta': casa,
                            'icone_casa': casa_info.get('icone', '?'),
                            'cor_casa': casa_info.get('cor', '#cccccc'),
                            'link_aposta': self.gerar_link_aposta(casa, jogo['partida'], self.traduzir_tipo(tipo)),
                            'timestamp': datetime.now().isoformat()
                        }
                        apostas_recomendadas.append(aposta)

        return sorted(apostas_recomendadas, key=lambda x: x['value_expected'], reverse=True)

    def _gerar_multiplas_mock(self, individuais: List[Dict[str, Any]]):
        top_bets = [b for b in individuais if b.get('confidence') == 'ALTA' and b.get('odd', 0) < 2.0]
        if len(top_bets) < 3: return []

        jogos_multipla = top_bets[:3]
        odd_total = round(jogos_multipla[0]['odd'] * jogos_multipla[1]['odd'] * jogos_multipla[2]['odd'], 2)
        
        multipla = {
            'tipo': 'Multipla do Dia (Alta Confiança)',
            'odd_total': odd_total,
            'probabilidade': random.uniform(0.40, 0.60),
            'confianca': "ALTA",
            'jogos': json.dumps([
                {'match': j['match'], 'bet_type': j['bet_type'], 'odd': j['odd']} 
                for j in jogos_multipla
            ]),
            'timestamp': datetime.now().isoformat()
        }
        return [multipla]

    def _gerar_surebets_mock(self):
        # Surebets simuladas
        return [
            {
                'match': 'Time A vs Time B',
                'odd_casa1': 2.15,
                'odd_casa2': 1.85,
                'lucro_percentual': 2.1,
                'timestamp': datetime.now().isoformat()
            }
        ]

    # -----------------------------------------------------------------
    # 💾 FUNÇÃO DE SALVAMENTO SUPABASE
    # -----------------------------------------------------------------
    def _salvar_dados_no_supabase(self, individuais, multiplas, surebets):
        """Salva os três tipos de apostas em suas respectivas tabelas."""
        if not supabase:
            print("❌ Não foi possível salvar: Conexão com Supabase falhou.")
            return

        dados_a_salvar = [
            ('individuais', individuais),
            ('multiplas', multiplas),
            ('surebets', surebets),
        ]

        for tabela_nome, dados in dados_a_salvar:
            try:
                # 1. Limpar tabela antiga
                print(f"🧹 Limpando e salvando na tabela '{tabela_nome}'...")
                supabase.table(tabela_nome).delete().not_eq("id", -1).execute() 
                
                # 2. Insere os novos dados
                if dados:
                    response = supabase.table(tabela_nome).insert(dados).execute()

                    if response.get('error'):
                         print(f"   ❌ Erro ao inserir dados em {tabela_nome}: {response['error']}")
                    else:
                         print(f"   ✅ {len(response.get('data', []))} registros salvos em {tabela_nome}!")
                else:
                    print(f"⏩ Pulando salvamento: Tabela '{tabela_nome}' está vazia.")
                     
            except Exception as e:
                print(f"❌ Erro durante a operação de salvamento na tabela {tabela_nome}: {e}")

# -----------------------------------------------------------------
# EXECUÇÃO 
# -----------------------------------------------------------------
if __name__ == "__main__":
    if supabase:
        print(f"\n--- Iniciando Análise de IA em {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
        ia = LancacaIACompleta()
        ia.analisar_jogos()
        print("\n--- Processo concluído ---")
    else:
        print("\n--- ERRO: Supabase não configurado. Verifique o Render Cron Job e as chaves. ---")