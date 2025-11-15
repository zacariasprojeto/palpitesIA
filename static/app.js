let isRegisterMode = false;
let lastLoginUser = null;

// ---------------- TOAST ----------------
function showToast(msg, type = "info") {
  const toast = document.getElementById("toast");
  if (!toast) return;
  toast.textContent = msg;
  toast.className = "toast " + type;
  toast.style.opacity = "1";
  setTimeout(() => {
    toast.style.opacity = "0";
  }, 3000);
}

// ---------------- AUTH MSG ----------------
function setAuthMessage(msg, type = "info") {
  const el = document.getElementById("authMsg");
  if (!el) return;
  el.textContent = msg || "";
  el.className = "auth-msg " + type;
}

// ---------------- MODO LOGIN/CADASTRO ----------------
function toggleMode() {
  const btnLogin = document.getElementById("loginBtn");
  const btnToggle = document.getElementById("showRegister");

  isRegisterMode = !isRegisterMode;

  if (isRegisterMode) {
    btnLogin.textContent = "Enviar cadastro";
    btnToggle.textContent = "Já tenho conta";
    setAuthMessage("Preencha email e senha para solicitar acesso.");
  } else {
    btnLogin.textContent = "Entrar";
    btnToggle.textContent = "Cadastrar";
    setAuthMessage("");
  }
}

// ---------------- UTIL ----------------
function diasRestantes(dateStr) {
  if (!dateStr) return 0;
  const d = new Date(dateStr);
  const hoje = new Date();
  const diffMs = d.getTime() - hoje.getTime();
  return Math.max(0, Math.ceil(diffMs / (1000 * 60 * 60 * 24)));
}

function atualizarBadgePlano(user) {
  const badge = document.getElementById("badgePlano");
  if (!badge || !user) return;

  if (user.is_admin) {
    badge.textContent = "Admin (acesso ilimitado)";
    badge.className = "badge-plano badge-admin";
    return;
  }

  const plan = user.plan || "trial";

  if (plan === "trial") {
    const dias = diasRestantes(user.trial_end);
    badge.textContent = `Teste grátis • ${dias} dia(s) restante(s)`;
    badge.className = "badge-plano badge-trial";
  } else if (plan === "paid") {
    const dias = diasRestantes(user.paid_until);
    badge.textContent = `Plano ativo • ${dias} dia(s) restante(s)`;
    badge.className = "badge-plano badge-paid";
  } else {
    badge.textContent = "Plano indefinido";
    badge.className = "badge-plano";
  }
}

// ---------------- PAYWALL ----------------
function preencherPaywall(data) {
  const paywall = document.getElementById("paywallOverlay");
  const planList = document.getElementById("planList");
  const pixKey = document.getElementById("pixKey");
  const trialInfo = document.getElementById("trialInfo");

  if (!paywall || !planList || !pixKey || !trialInfo) return;

  planList.innerHTML = "";
  (data.plans || []).forEach((p) => {
    const card = document.createElement("div");
    card.className = "paywall-plan-card";
    card.innerHTML = `
      <div class="plan-label">${p.label}</div>
      <div class="plan-price">R$ ${p.price}</div>
      <div class="plan-days">${p.days} dias de acesso</div>
    `;
    planList.appendChild(card);
  });

  pixKey.textContent = data.pix_key || "SUA_CHAVE_PIX_AQUI";

  if (data.user && data.user.trial_end) {
    const dias = diasRestantes(data.user.trial_end);
    trialInfo.textContent =
      "Seu teste terminou ou termina em breve. Restavam " + dias + " dia(s).";
  } else {
    trialInfo.textContent = "";
  }

  paywall.style.display = "flex";
}

function fecharPaywall() {
  const paywall = document.getElementById("paywallOverlay");
  if (paywall) paywall.style.display = "none";
}

// ---------------- API CALLS ----------------
async function doLogin(email, password) {
  try {
    const resp = await fetch("/api/login", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ email, password }),
    });

    const data = await resp.json();

    if (data.status === "ok") {
      lastLoginUser = data.user;
      setAuthMessage("");
      showToast("Login autorizado!", "success");
      entrarDashboard(data.user);
    } else if (data.status === "blocked") {
      lastLoginUser = data.user;
      setAuthMessage(data.msg || "Acesso bloqueado.", "error");
      preencherPaywall(data);
    } else {
      setAuthMessage(data.msg || "Erro ao fazer login.", "error");
    }
  } catch (e) {
    console.error(e);
    setAuthMessage("Falha ao conectar com o servidor.", "error");
  }
}

async function doRegister(email, password) {
  try {
    const resp = await fetch("/api/register", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ email, password }),
    });

    const data = await resp.json();
    if (data.status === "ok") {
      setAuthMessage(data.msg, "success");
      showToast("Cadastro enviado! Aguarde aprovação.", "success");
    } else {
      setAuthMessage(data.msg || "Erro ao enviar cadastro.", "error");
    }
  } catch (e) {
    console.error(e);
    setAuthMessage("Falha ao conectar com o servidor.", "error");
  }
}

async function doLogout() {
  try {
    await fetch("/api/logout", { method: "POST" });
  } catch (e) {
    console.error(e);
  }
  document.getElementById("containerPrincipal").style.display = "none";
  document.getElementById("authContainer").style.display = "flex";
  setAuthMessage("Você saiu da conta.");
}

// -------- ADMIN PENDENTES --------
async function carregarPendentes() {
  const list = document.getElementById("pendingList");
  if (!list) return;

  list.textContent = "Carregando...";

  try {
    const resp = await fetch("/api/pending");
    const data = await resp.json();

    if (data.status !== "ok") {
      list.textContent = data.msg || "Erro ao carregar pendentes.";
      return;
    }

    const pend = data.pending || [];
    if (!pend.length) {
      list.textContent = "Nenhum cadastro pendente.";
      return;
    }

    list.innerHTML = "";
    pend.forEach((u) => {
      const row = document.createElement("div");
      row.className = "pending-row";
      row.innerHTML = `
        <div>
          <strong>${u.email}</strong><br/>
          <span class="pending-date">${new Date(u.created_at).toLocaleString()}</span>
        </div>
        <button class="pending-approve">Aprovar</button>
      `;
      row.querySelector(".pending-approve").addEventListener("click", () => {
        aprovarUsuario(u.email);
      });
      list.appendChild(row);
    });
  } catch (e) {
    console.error(e);
    list.textContent = "Erro ao carregar pendentes.";
  }
}

async function aprovarUsuario(email) {
  if (!confirm(`Aprovar acesso para ${email}?`)) return;

  try {
    const resp = await fetch("/api/approve", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ email }),
    });
    const data = await resp.json();
    if (data.status === "ok") {
      showToast("Usuário aprovado com 30 dias de teste.", "success");
      carregarPendentes();
    } else {
      showToast(data.msg || "Erro ao aprovar usuário.", "error");
    }
  } catch (e) {
    console.error(e);
    showToast("Falha ao comunicar com o servidor.", "error");
  }
}

// ---------------- ENTRAR DASHBOARD ----------------
function entrarDashboard(user) {
  const auth = document.getElementById("authContainer");
  const main = document.getElementById("containerPrincipal");
  const nome = document.getElementById("nomeUsuario");

  if (auth) auth.style.display = "none";
  if (main) main.style.display = "block";
  if (nome && user) nome.textContent = "Olá, " + (user.email || "usuário") + "!";

  atualizarBadgePlano(user);

  // Aqui depois você liga suas funções de análise/atualização dos cards
}

// ---------------- INIT ----------------
document.addEventListener("DOMContentLoaded", () => {
  const emailInput = document.getElementById("email");
  const passInput = document.getElementById("password");
  const btnLogin = document.getElementById("loginBtn");
  const btnToggle = document.getElementById("showRegister");
  const btnLogout = document.getElementById("btnLogout");
  const btnAdminToggle = document.getElementById("btnAdminToggle");
  const adminPanel = document.getElementById("adminPanel");

  const closePaywall = document.getElementById("closePaywall");
  const btnJaPaguei = document.getElementById("btnJaPaguei");

  btnLogin.addEventListener("click", () => {
    const email = emailInput.value.trim();
    const password = passInput.value.trim();
    if (!email || !password) {
      setAuthMessage("Preencha email e senha.", "error");
      return;
    }
    if (isRegisterMode) {
      doRegister(email, password);
    } else {
      doLogin(email, password);
    }
  });

  btnToggle.addEventListener("click", toggleMode);

  passInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") btnLogin.click();
  });

  btnLogout.addEventListener("click", () => {
    fecharPaywall();
    doLogout();
  });

  btnAdminToggle.addEventListener("click", () => {
    if (adminPanel.style.display === "block") {
      adminPanel.style.display = "none";
    } else {
      adminPanel.style.display = "block";
      carregarPendentes();
    }
  });

  if (closePaywall) {
    closePaywall.addEventListener("click", fecharPaywall);
  }
  if (btnJaPaguei) {
    btnJaPaguei.addEventListener("click", () => {
      showToast("Envie o comprovante para o admin liberar seu acesso.", "info");
    });
  }
});
