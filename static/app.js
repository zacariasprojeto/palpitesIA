/* static/app.js */

/*
  Requer variáveis no Render:
  - SUPABASE_ANON_KEY (exponha para client)
  - SUPABASE_URL
  Aqui no client usaremos a lib oficial supabase se você quiser; para simplicidade,
  vamos usar fetch para as APIs do backend e a lib Supabase para carregar apostas.
*/

/* --- Configuração Supabase client (front) --- */
/* Se preferir, adicione <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js"></script>
   no index.html; vamos tentar usar apenas fetch para as APIs de backend e Supabase anon
*/
const SUPABASE_URL = window.SUPABASE_URL || ''; // optional, set via inline if needed
const SUPABASE_ANON_KEY = window.SUPABASE_ANON_KEY || ''; // optional

// Helpers
function showToast(msg, time=3000) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(()=> t.classList.remove('show'), time);
}

async function apiPost(path, data) {
  const res = await fetch(path, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    credentials: 'same-origin',
    body: JSON.stringify(data)
  });
  return res.json();
}

async function apiGet(path) {
  const res = await fetch(path, {credentials: 'same-origin'});
  return res.json();
}

/* --- Auth UI --- */
const emailEl = () => document.getElementById('email');
const passwordEl = () => document.getElementById('password');
const authMsg = () => document.getElementById('authMsg');

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('loginBtn').addEventListener('click', async () => {
    const email = emailEl().value.trim();
    const password = passwordEl().value;
    if (!email || !password) { authMsg().textContent = 'Preencha email e senha'; return; }
    authMsg().textContent = 'Entrando...';
    const resp = await apiPost('/api/login', {email, password});
    if (resp.status === 'ok') {
      authMsg().textContent = '';
      showApp(resp.user);
      showToast('Bem-vindo!');
    } else {
      authMsg().textContent = resp.msg || 'Erro ao logar';
    }
  });

  document.getElementById('showRegister').addEventListener('click', async () => {
    const email = emailEl().value.trim();
    const password = passwordEl().value;
    if (!email || !password) { authMsg().textContent = 'Preencha email e senha para cadastrar'; return; }
    authMsg().textContent = 'Enviando cadastro...';
    const resp = await apiPost('/api/register', {email, password});
    if (resp.status === 'ok') {
      authMsg().textContent = resp.msg;
    } else {
      authMsg().textContent = resp.msg || 'Erro ao registrar';
    }
  });

  // logout
  document.getElementById('btnLogout').addEventListener('click', async () => {
    await apiPost('/api/logout', {});
    location.reload();
  });

  // admin toggle
  document.getElementById('btnAdminToggle').addEventListener('click', async () => {
    const panel = document.getElementById('adminPanel');
    if (panel.style.display === 'none' || panel.style.display === '') {
      // fetch pending users
      const resp = await apiGet('/api/pending_users');
      if (resp.status === 'ok') {
        renderPending(resp.pending || []);
        panel.style.display = 'block';
      } else {
        showToast(resp.msg || 'Sem permissão', 3000);
      }
    } else {
      panel.style.display = 'none';
    }
  });

  document.getElementById('btnAnalyze').addEventListener('click', async () => {
    showToast('Analisando (placeholder)...');
    // you could call /api/run_ia to trigger backend job
    await apiPost('/api/run_ia', {});
    showToast('IA executada (placeholder)');
  });

  document.getElementById('btnRefresh').addEventListener('click', async () => {
    await loadBetsFromSupabase();
  });

  // try restore session (optional)
  restoreSession();
});

/* --- Session / UI --- */
async function restoreSession() {
  const s = await apiGet('/api/session');
  if (s && s.user) {
    showApp(s.user);
  }
}

function showApp(user) {
  document.getElementById('authContainer').style.display = 'none';
  document.getElementById('containerPrincipal').style.display = 'block';
  document.getElementById('nomeUsuario').textContent = `Olá, ${user.email}`;
  // load bets
  loadBetsFromSupabase();
}

/* --- Pending users rendering / approval --- */
function renderPending(list) {
  const cont = document.getElementById('pendingList');
  if (!list || list.length === 0) { cont.innerHTML = '<div>Nenhum usuário pendente</div>'; return; }
  cont.innerHTML = list.map(u => `
    <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.06)">
      <div>${u.email}</div>
      <div>
        <button class="botao-acao" data-email="${u.email}" onclick="approveUser('${u.email}')">Aprovar</button>
      </div>
    </div>
  `).join('');
}

async function approveUser(email) {
  const resp = await apiPost('/api/approve_user', {email});
  if (resp.status === 'ok') {
    showToast('Usuário aprovado');
    // refresh list
    const r = await apiGet('/api/pending_users');
    renderPending(r.pending || []);
  } else {
    showToast(resp.msg || 'Erro ao aprovar');
  }
}

/* --- Load bets from Supabase public REST (or use client) --- */
async function loadBetsFromSupabase() {
  // This demo assumes you have the tables 'individuais' and 'multiplas' in Supabase.
  // We'll call them via your backend-less public REST using the anon key (CORS must allow)
  try {
    // If you provided SUPABASE_URL and SUPABASE_ANON_KEY it is possible to fetch directly:
    if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
      // If not available, show example data
      showToast('Supabase não configurado no front — mostrando dados de exemplo', 2500);
      loadExampleData();
      return;
    }
    const base = SUPABASE_URL.replace(/\/$/,'') + '/rest/v1';
    // Example: GET individuais?select=*&order=value_expected.desc
    const ind = await fetch(`${base}/individuais?select=*&order=value_expected.desc`, {
      headers: {apikey: SUPABASE_ANON_KEY, Authorization: `Bearer ${SUPABASE_ANON_KEY}`}
    }).then(r=>r.json());
    const mult = await fetch(`${base}/multiplas?select=*`, {
      headers: {apikey: SUPABASE_ANON_KEY, Authorization: `Bearer ${SUPABASE_ANON_KEY}`}
    }).then(r=>r.json());

    // map to UI
    // this is naive mapping — adapt field names to your schema
    const individuais = (ind || []).map(b => ({
      id: b.id,
      partida: b.match || b.partida || 'Partida',
      campeonato: b.league || b.campeonato || '',
      tipoAposta: b.bet_type || b.tipo || '',
      probabilidade: b.probabilidade || (b.probability || 0.7),
      odds: { betano: {valor: b.odd || 1.5, link: b.link || '#'}, sportingbet: {valor: b.odd || 1.5, link:'#'} },
      valor: b.value_expected || 0,
      stake: b.stake || 'MÉDIO',
      categoria: b.category || 'top',
      genero: b.gender || 'M',
      data: b.date || 'HOJE'
    }));

    const multiplas = (mult || []).map(m => ({
      id: m.id,
      partidas: JSON.parse(m.jogos || '[]'),
      probabilidade: m.probabilidade || 0.6,
      odds: { betano: {valor: m.odd_total || 2.5, link: m.link || '#'}, sportingbet: {valor: m.odd_total || 2.5, link:'#'} },
      valor: m.valor_esperado || 0.5,
      categoria: m.category || 'top'
    }));

    // render
    renderBets(individuais, multiplas);
  } catch (err) {
    console.error(err);
    showToast('Erro ao carregar Supabase — mostrando dados de exemplo', 3000);
    loadExampleData();
  }
}

function renderBets(individuais, multiplas) {
  // top: top 5 by valor
  const all = [...individuais, ...multiplas];
  all.sort((a,b)=> (b.valor||0) - (a.valor||0));
  const top = all.slice(0,5);
  document.getElementById('topApostas').innerHTML = top.map(makeCard).join('');
  document.getElementById('gridApostasSeguras').innerHTML = individuais.filter(i=>i.valor>0.25 && i.probabilidade>0.7).map(makeCard).join('');
  document.getElementById('gridMultiplas').innerHTML = multiplas.map(makeCard).join('');
  document.getElementById('gridTodasApostas').innerHTML = individuais.map(makeCard).join('');
  document.getElementById('apostasIndividuais').textContent = individuais.length;
  document.getElementById('apostasMultiplas').textContent = multiplas.length;
  document.getElementById('apostasSeguras').textContent = document.querySelectorAll('#gridApostasSeguras .cartao-aposta').length;
}

function makeCard(a){
  if (a.partidas) {
    // multipla
    return `<div class="cartao-aposta">
      <div class="cabecalho-aposta"><div class="info-partida"><h3>Múltipla</h3><div class="meta-partida">${a.partidas.length} seleções</div></div><div class="tipo-aposta">MÚLTIPLA</div></div>
      <div class="detalhes-aposta">${(a.partidas||[]).map(p=>`<div class="partida-multipla"><div class="nome-partida">${p.partida||p.match}</div></div>`).join('')}</div>
      <div class="rodape-aposta"><div class="badge-stake">${a.stake||'MÉDIO'}</div></div></div>`;
  } else {
    return `<div class="cartao-aposta">
      <div class="cabecalho-aposta"><div class="info-partida"><h3>${a.partida||'Partida'}</h3><div class="meta-partida">${a.campeonato||''} • ${a.data||''}</div></div><div class="tipo-aposta">${a.tipoAposta||''}</div></div>
      <div class="detalhes-aposta"><div class="item-detalhe"><span class="rotulo-detalhe">Probabilidade</span><span>${Math.round((a.probabilidade||a.probability||0)*100)}%</span></div><div class="item-detalhe"><span class="rotulo-detalhe">Melhor Odd</span><span class="valor-odd">${(a.odds && a.odds.betano)?a.odds.betano.valor:'-'}</span></div></div>
      <div class="rodape-aposta"><div class="badge-stake">${a.stake||'MÉDIO'}</div></div></div>`;
  }
}

function loadExampleData() {
  // fallback small sample so UI doesn't break
  const sample = [
    {id:1,partida:'Flamengo x Palmeiras',campeonato:'Brasileirão',tipoAposta:'Mais de 2.5',probabilidade:0.82,odds:{betano:{valor:1.95,link:'#'}} ,valor:0.59,stake:'ALTO',categoria:'top',genero:'M',data:'HOJE 19:30'}
  ];
  renderBets(sample, []);
}
