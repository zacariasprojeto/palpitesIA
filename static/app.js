function gerarPayloadPix(chave, valor, descricao) {
  const pad = (str) => String(str.length).padStart(2, "0") + str;

  const gui = "BR.GOV.BCB.PIX";
  const guiField = "00" + pad(gui);

  const chaveField = "01" + pad(chave);

  const descricaoField = "02" + pad(descricao);

  const merchantAccountInfo = "26" + pad(guiField + chaveField + descricaoField);

  const merchantCategoryCode = "52040000";
  const transactionCurrency = "5303986";

  const transactionAmount = "54" + pad(valor);

  const countryCode = "5802BR";
  const name = "59" + pad("ZACARIAS IA");

  const city = "6008BRASILIA";

  const additionalData = "62070503***";

  let payload =
    "000201" +
    merchantAccountInfo +
    merchantCategoryCode +
    transactionCurrency +
    transactionAmount +
    countryCode +
    name +
    city +
    additionalData +
    "6304";

  function crc16(data) {
    let crc = 0xffff;
    for (let i = 0; i < data.length; i++) {
      crc ^= data.charCodeAt(i) << 8;
      for (let j = 0; j < 8; j++) {
        crc = crc & 0x8000 ? (crc << 1) ^ 0x1021 : crc << 1;
      }
    }
    return ((crc & 0xffff).toString(16)).toUpperCase().padStart(4, "0");
  }

  payload += crc16(payload);
  return payload;
}

function gerarQrPlano(plano) {
  const chave = "9aacbabc-39ad-4602-b73e-955703ec502e";

  const valores = {
    "Mensal": "49.90",
    "Trimestral": "129.90",
    "Semestral": "219.90"
  };

  const descricao = "Assinatura " + plano;

  const payload = gerarPayloadPix(chave, valores[plano], descricao);

  const qrImg = document.getElementById("qrCodePix");
  qrImg.src = "https://chart.googleapis.com/chart?cht=qr&chs=300x300&chl=" + encodeURIComponent(payload);

  document.getElementById("pixPayloadText").textContent = payload;
}

// ==============================
// PAYWALL RECEBE O PLANO CLICADO
// ==============================
document.addEventListener("click", (ev) => {
  if (ev.target.classList.contains("paywall-plan-card")) {
    const plano = ev.target.dataset.plano;
    gerarQrPlano(plano);
  }
});
