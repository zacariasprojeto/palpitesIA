async function confirmar() {
    const codigo = document.getElementById("codigo").value.trim();
    const email = new URLSearchParams(window.location.search).get("email");
    const erro = document.getElementById("erro");

    erro.style.display = "none";

    if (codigo.length !== 6) {
        erro.innerText = "Código inválido.";
        erro.style.display = "block";
        return;
    }

    const resp = await fetch("/api/confirmar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ codigo, email })
    });

    const data = await resp.json();

    if (resp.status === 200) {
        alert("Conta confirmada com sucesso!");
        window.location.href = "/";
    } else {
        erro.innerText = data.message || "Código incorreto.";
        erro.style.display = "block";
    }
}
