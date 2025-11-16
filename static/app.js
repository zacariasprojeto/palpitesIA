let isRegisterMode = false;
let lastLoginUser = null;

// ==============================
// TOAST
// ==============================
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

// ==============================
// AUTH MESSAGE
// ==============================
function setAuthMessage(msg, type = "info") {
  const el = document.getElementById("authMsg");
  if (!el) return;
  el.textContent = msg || "";
  el.className = "auth-msg " + type;
}

// ==============================
// LOGIN / REGISTER MODE
// ==============================
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

// ==============================
// DIAS RESTANTES
// ==============================
function diasRestantes(dateStr) {
  if (!dateStr) return 0;
  const d = new Date(dateStr);
  const hoje = new Date();
  const diffMs = d.getTime() - hoje.getTime();
  return Math.max(0, Math.ceil(diffMs / (1000 * 60 * 60 * 24)));
}

// ==============================
// BADGE DE PLANO
// ==============================
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

// ==============================
// QR CODE PIX
// ==============================

// Chave PIX fixa do usuário
const CHAVE_PIX = "9aacbabc-39ad-4602-b73e-955703ec502e";

// Gera payload BRCode PIX (versão simples fixa)
function gerarPayloadPIX(valor, nomePlano) {
  const p = valor.toFixed(2).replace(".", "");
  // IMPORTANTE: isso é um payload simplificado apenas para testes/demonstração.
  // Para produção, o ideal é usar um gerador de BRCode homologado.
  return (
    "000201" + // Payload format
    "010212" + // Transação dinâmica
    "26580014BR.GOV.BCB.PIX01" +
    (CHAVE_PIX.length < 10 ? "0" : "") +
    CHAVE_PIX.length +
    CHAVE_PIX +
    "52040000" + // Merchant category
    "5303986" +  // Moeda BRL
    "54" +
    (p.length < 10 ? "0" : "") +
    p +
    "5802BR" +
    "5913Lanzaca IA" +
    "6009Sao Paulo" +
    "62070503***"
  );
}

// Gera URL de imagem de QR Code a partir do payload
function gerarQRCodePlano(valor, nomePlano) {
  const payload = gerarPayloadPIX(valor, nomePlano);
  const qrUrl =
    "https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=" +
    encodeURIComponent(payload);
  return { qrUrl, payload };
}

// ==============================
// PAYWALL
// ==============================
function preencherPaywall(data) {
  const paywall = document.getElementById("paywallOverlay");
  const planList = document.getElementById("planList");
  const pixKey = document.getElementById("pixKey");
  const trialInfo = document.getElementById("trialInfo");

  if (!paywall || !planList || !pixKey || !trialInfo) return;

  // Mostra a chave PIX fixa
  pixKey.textContent = CHAVE_PIX;

  planList.innerHTML = "";

  // Planos fixos (pode bater com o backend, mas aqui garantimos os 3)
  const planos = [
    { label: "Mensal", price: 49.9, days: 30 },
    { label: "Trimestral", price: 129.9, days: 90 },
    { label: "Semestral", price: 219.9, days: 180 },
  ];

  planos.forEach((p) => {
    const { qrUrl, payload } = gerarQRCodePlano(p.price, p.label);

    const card = document.createElement("div");
    card.className = "paywall-plan-card";
    card.innerHTML = `
      <div class="plan-label">${p.label}</div>
      <div class="plan-price">R$ ${p.price}</div>
      <div class="plan-days">${p.days} dias de acesso</div>
      <img src="${qrUrl}" class="qr-pix-img" alt="QR PIX ${p.label}"/>
      <button class="botao-login btn-pix-copiar" data-payload="${payload}">
        Copiar código PIX
      </button>
    `;
    planList.appendChild(card);
  });

  // Se o backend mandar info de trial, mostra texto
  if (data && data.user && data.user.trial_end) {
    const dias = diasRestantes(data.user.trial_end);
    trialInfo.textContent =
      "Seu teste terminou ou termina em breve. Restavam " + dias + " dia(s).";
  } else {
    trialInfo.textContent = "";
  }

  // Botão "Copiar código PIX"
  document.querySelectorAll(".btn-pix-copiar").forEach((btn) => {
    btn.addEventListener("click", () => {
      const payload = btn.getAttribute("data-payload");
      if (!payload) return;
      navigator.clipboard
        .writeText(payload)
        .then(() => showToast("Código PIX copiado!", "success"))
        .catch(() =>
          showToast("Não foi possível copiar o código PIX.", "error")
        );
    });
  });

  paywall.style.display = "flex";
}

function fecharPaywall() {
  const paywall = document.getElementById("paywallOverlay");
  if (paywall) paywall.style.display = "none";
}

// ==============================
// LOGIN
// ==============================
async function doLogin(email, password) {
  try {
    const resp = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
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
      preencherPaywall(data || {});
    } else {
      setAuthMessage(data.msg || "Erro ao fazer login.", "error");
    }
  } catch (e) {
    console.error(e);
    setAuthMessage("Falha ao conectar com o servidor.", "error");
  }
}

// ==============================
// REGISTRO
// (alinha com /api/register atual: email + password, e admin aprova)
// ==============================
async function doRegister(email, password) {
  try {
    const resp = await fetch("/api/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
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

// ==============================
// LOGOUT
// ==============================
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

// ==============================
// ADMIN LISTAR PENDENTES
// ==============================
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
          <span class="pending-date">${new Date(
            u.created_at
          ).toLocaleString()}</span>
        </div>
        <button class="pending-approve">Aprovar</button>
      `;
      row
        .querySelector(".pending-approve")
        .addEventListener("click", () => {
          aprovarUsuario(u.email);
        });
      list.appendChild(row);
    });
  } catch (e) {
    console.error(e);
    list.textContent = "Erro ao carregar pendentes.";
  }
}

// ==============================
// APROVAR
// ==============================
async function aprovarUsuario(email) {
  if (!confirm(`Aprovar acesso para ${email}?`)) return;

  try {
    const resp = await fetch("/api/approve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
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

// ==============================
// ENTRAR NO PAINEL
// ==============================
function entrarDashboard(user) {
  document.getElementById("authContainer").style.display = "none";
  document.getElementById("containerPrincipal").style.display = "block";

  const nome = document.getElementById("nomeUsuario");
  if (nome && user) {
    // Mostra apenas o "nome" (parte antes do @) caso não exista campo name
    const displayName =
      user.name ||
      (user.email ? user.email.split("@")[0] : "usuário");
    nome.textContent = "Olá, " + displayName + "!";
  }

  atualizarBadgePlano(user);
}

// ==============================
// INIT
// ==============================
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

  // Login / Cadastro
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

  // Enter no campo senha também faz login/cadastro
  passInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      btnLogin.click();
    }
  });

  // Alternar modo login/cadastro
  btnToggle.addEventListener("click", toggleMode);

  // Logout
  btnLogout.addEventListener("click", () => {
    fecharPaywall();
    doLogout();
  });

  // Painel admin
  btnAdminToggle.addEventListener("click", () => {
    if (adminPanel.style.display === "block") {
      adminPanel.style.display = "none";
    } else {
      adminPanel.style.display = "block";
      carregarPendentes();
    }
  });

  // Paywall
  if (closePaywall) {
    closePaywall.addEventListener("click", fecharPaywall);
  }
  if (btnJaPaguei) {
    btnJaPaguei.addEventListener("click", () => {
      showToast("Envie o comprovante para o admin liberar seu acesso.", "info");
    });
  }
});
