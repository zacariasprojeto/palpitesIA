let isRegisterMode = false;
let lastLoginUser = null;
let codigoEnviado = false;

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
// AUTH MESSAGES
// ==============================
function setAuthMessage(msg, type = "info") {
  const el = document.getElementById("authMsg");
  if (!el) return;
  el.textContent = msg || "";
  el.className = "auth-msg " + type;
}

// ==============================
// MODO LOGIN / REGISTER
// ==============================
function toggleMode() {
  const btnLogin = document.getElementById("loginBtn");
  const btnToggle = document.getElementById("showRegister");
  const nomeField = document.getElementById("nomeField");
  const celField = document.getElementById("celularField");
  const codigoField = document.getElementById("codigoField");
  const sendCodeBtn = document.getElementById("btnSendCode");

  isRegisterMode = !isRegisterMode;

  if (isRegisterMode) {
    btnLogin.textContent = "Concluir Cadastro";
    btnToggle.textContent = "Já tenho conta";
    nomeField.style.display = "block";
    celField.style.display = "block";
    codigoField.style.display = "block";
    sendCodeBtn.style.display = "block";
    setAuthMessage("Preencha seus dados e confirme o código enviado ao e-mail.");
  } else {
    btnLogin.textContent = "Entrar";
    btnToggle.textContent = "Cadastrar";
    nomeField.style.display = "none";
    celField.style.display = "none";
    codigoField.style.display = "none";
    sendCodeBtn.style.display = "none";
    setAuthMessage("");
  }
}

// ==============================
// CALCULAR DIAS RESTANTES
// ==============================
function diasRestantes(dateStr) {
  if (!dateStr) return 0;
  const d = new Date(dateStr);
  const hoje = new Date();
  const diffMs = d.getTime() - hoje.getTime();
  return Math.max(0, Math.ceil(diffMs / (1000 * 60 * 60 * 24)));
}

// ==============================
// BADGE PLANO
// ==============================
function atualizarBadgePlano(user) {
  const badge = document.getElementById("badgePlano");
  if (!badge || !user) return;

  if (user.is_admin) {
    badge.textContent = "Admin • Acesso infinito";
    badge.className = "badge-plano badge-admin";
    return;
  }

  const plan = user.plano || "trial";

  if (plan === "trial") {
    const dias = diasRestantes(user.trial_ate);
    badge.textContent = `Teste grátis • ${dias} dias restantes`;
    badge.className = "badge-plano badge-trial";
  } else {
    badge.textContent = `${plan.toUpperCase()} ativo`;
    badge.className = "badge-plano badge-paid";
  }
}

// ==============================
// PAYWALL
// ==============================
async function abrirPaywall() {
  const resp = await fetch("/api/paywall");
  const data = await resp.json();

  const paywall = document.getElementById("paywallOverlay");
  const planList = document.getElementById("planList");
  const pixKey = document.getElementById("pixKey");

  pixKey.textContent = data.pix;
  planList.innerHTML = "";

  data.planos.forEach((p) => {
    const payload =
      "00020101021226580014BR.GOV.BCB.PIX01" +
      "0325" + // tamanho + chave (pode ajustar)
      data.pix +
      "52040000" +
      "5303986" +
      "54" +
      p.price.toFixed(2).replace(".", "") +
      "5802BR" +
      "5913Lanzaca IA" +
      "6009Sao Paulo" +
      "62070503***";

    const card = document.createElement("div");
    card.className = "paywall-plan-card";

    card.innerHTML = `
      <div class="plan-label">${p.label}</div>
      <div class="plan-price">R$ ${p.price}</div>
      <div class="plan-days">${p.dias} dias de acesso</div>
      <img src="https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=${encodeURIComponent(
        payload
      )}" class="qr-pix-img">

      <button class="botao-login btn-pix-copiar">
        Copiar código PIX
      </button>
    `;

    card.querySelector(".btn-pix-copiar").addEventListener("click", () => {
      navigator.clipboard.writeText(payload);
      showToast("Código PIX copiado!", "success");
    });

    planList.appendChild(card);
  });

  paywall.style.display = "flex";
}

function fecharPaywall() {
  const pw = document.getElementById("paywallOverlay");
  pw.style.display = "none";
}

// ==============================
// LOGIN
// ==============================
async function doLogin(email, senha) {
  try {
    const resp = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, senha }),
    });

    const data = await resp.json();

    if (data.status === "ok") {
      localStorage.setItem("usuario", JSON.stringify(data.user));
      entrarDashboard(data.user);
      showToast("Login autorizado!", "success");
    } else if (data.status === "blocked") {
      showToast("Seu acesso expirou.", "error");
      abrirPaywall();
    } else {
      showToast("Credenciais inválidas.", "error");
    }
  } catch (e) {
    console.error(e);
    showToast("Erro ao conectar com servidor.", "error");
  }
}

// ==============================
// CADASTRO - ENVIAR CÓDIGO
// ==============================
async function enviarCodigo(email) {
  try {
    const resp = await fetch("/api/send_code", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });

    const data = await resp.json();

    if (data.error) {
      showToast(data.error, "error");
      return;
    }

    showToast("Código enviado ao e-mail!", "success");
    codigoEnviado = true;
  } catch (e) {
    console.error(e);
    showToast("Erro ao enviar código.", "error");
  }
}

// ==============================
// CADASTRO - VALIDAR CÓDIGO
// ==============================
async function validarCadastro(obj) {
  try {
    const resp = await fetch("/api/verify_code", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(obj),
    });

    const data = await resp.json();

    if (data.error) {
      showToast(data.error, "error");
      return;
    }

    showToast("Cadastro concluído! Agora faça login.", "success");
    toggleMode();
  } catch (e) {
    console.error(e);
    showToast("Falha ao criar conta.", "error");
  }
}

// ==============================
// ADMIN - LISTAR PENDENTES
// ==============================
async function carregarPendentes() {
  const list = document.getElementById("pendingList");
  list.textContent = "Carregando...";

  try {
    const resp = await fetch("/api/pending");
    const data = await resp.json();

    if (!data.pending.length) {
      list.textContent = "Nenhum usuário pendente.";
      return;
    }

    list.innerHTML = "";

    data.pending.forEach((u) => {
      const row = document.createElement("div");
      row.className = "pending-row";

      row.innerHTML = `
        <div>
          <strong>${u.nome}</strong><br>
          <span>${u.email}</span><br>
          <span>${u.celular}</span>
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
    showToast("Erro ao carregar pendentes.", "error");
  }
}

async function aprovarUsuario(email) {
  await fetch("/api/approve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });

  showToast("Usuário aprovado!", "success");
  carregarPendentes();
}

// ==============================
// ENTRAR NO PAINEL
// ==============================
function entrarDashboard(user) {
  document.getElementById("authContainer").style.display = "none";
  document.getElementById("containerPrincipal").style.display = "block";

  document.getElementById("nomeUsuario").textContent = `Olá, ${user.nome}`;
  atualizarBadgePlano(user);
}

// ==============================
// INÍCIO
// ==============================
document.addEventListener("DOMContentLoaded", () => {
  const emailInput = document.getElementById("email");
  const passInput = document.getElementById("password");
  const nomeInput = document.getElementById("nome");
  const celInput = document.getElementById("celular");
  const codigoInput = document.getElementById("codigo");

  document.getElementById("loginBtn").addEventListener("click", () => {
    if (isRegisterMode) {
      validarCadastro({
        email: emailInput.value,
        senha: passInput.value,
        nome: nomeInput.value,
        celular: celInput.value,
        code: codigoInput.value,
      });
    } else {
      doLogin(emailInput.value, passInput.value);
    }
  });

  document.getElementById("showRegister").addEventListener("click", toggleMode);

  document.getElementById("btnSendCode").addEventListener("click", () => {
    if (!emailInput.value) {
      showToast("Digite seu e-mail.", "error");
      return;
    }
    enviarCodigo(emailInput.value);
  });

  document.getElementById("btnLogout").addEventListener("click", () => {
    localStorage.removeItem("usuario");
    location.reload();
  });
});
