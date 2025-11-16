<script>
class LanzacaIA {
    constructor() {
        this.apostas = {
            individuais: [],
            multiplas: [],
            seguras: [],
            top: []
        };

        this.usuarioLogado = null;
        this.isAdmin = false;

        // Usuários salvos na memória local
        this.usuarios = [
            {
                nome: "Administrador",
                celular: "00000000000",
                email: "admin@admin.com",
                password: "281500",
                isAdmin: true,
                criadoEm: new Date(),
                verificado: true
            }
        ];
    }

    iniciar() {
        this.configurarEventos();
        this.atualizarListaUsuarios();
    }

    configurarEventos() {
        document.getElementById('senha').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') fazerLogin();
        });

        document.querySelectorAll('.botao-filtro').forEach(botao => {
            botao.addEventListener('click', (e) => {
                document.querySelectorAll('.botao-filtro').forEach(b => b.classList.remove('ativo'));
                e.target.classList.add('ativo');
                this.filtrarApostas(e.target.dataset.filtro);
            });
        });

        document.getElementById('botaoAnalisar').addEventListener('click', () => this.analisarComIA());
        document.getElementById('botaoAtualizar').addEventListener('click', () => this.atualizarDados());
    }

    fazerLogin(usuario, senha) {
        const user = this.usuarios.find(u => 
            (u.email === usuario || u.celular === usuario) && u.password === senha
        );

        if (!user) return false;

        this.usuarioLogado = user;
        this.isAdmin = user.isAdmin;

        this.mostrarTelaPrincipal();
        return true;
    }

    criarUsuario(dados) {
        if (!this.isAdmin)
            throw new Error("Apenas administradores podem criar usuários");

        if (this.usuarios.find(u => u.email === dados.email))
            throw new Error("Email já cadastrado!");

        this.usuarios.push({
            nome: dados.nome,
            celular: dados.celular,
            email: dados.email,
            password: dados.senha,
            isAdmin: false,
            criadoEm: new Date(),
            verificado: false
        });

        this.atualizarListaUsuarios();
        return true;
    }

    atualizarListaUsuarios() {
        const lista = document.getElementById("listaUsuarios");

        lista.innerHTML = this.usuarios.map(user => `
            <div style="padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.1);">
                <strong>${user.nome}</strong><br>
                <span style="color: var(--cinza-claro)">${user.email}</span>
                ${user.isAdmin ? `<span style="color: var(--azul); margin-left:10px">(Admin)</span>` : ""}
            </div>
        `).join("");

        document.getElementById("totalUsuarios").textContent = this.usuarios.length;
        document.getElementById("totalAdmins").textContent = this.usuarios.filter(u => u.isAdmin).length;
    }

    mostrarTelaPrincipal() {
        document.getElementById("telaLogin").style.display = "none";
        document.getElementById("telaCarregamento").style.display = "flex";

        setTimeout(() => {
            document.getElementById("telaCarregamento").style.display = "none";
            document.getElementById("containerPrincipal").style.display = "block";

            document.getElementById("nomeUsuario").textContent = `Olá, ${this.usuarioLogado.nome}!`;

            this.carregarDadosExemplo();
            this.mostrarToast("Bem-vindo ao Lanzaca IA Premium! 🚀");
        }, 1500);
    }

    fazerLogout() {
        this.usuarioLogado = null;
        this.isAdmin = false;

        document.getElementById("containerPrincipal").style.display = "none";
        document.getElementById("telaLogin").style.display = "flex";

        document.getElementById("usuario").value = "";
        document.getElementById("senha").value = "";

        this.mostrarToast("Logout realizado!");
    }

    carregarDadosExemplo() {
        // Mesmos dados que você já tinha
    }

    renderizarTodasApostas() {}
    filtrarApostas() {}
    analisarComIA() {}
    atualizarDados() {}
    apostarAgora() {}

    mostrarToast(msg) {
        const toast = document.getElementById("toast");
        toast.textContent = msg;
        toast.classList.add("mostrar");
        setTimeout(() => toast.classList.remove("mostrar"), 3000);
    }
}

const lanzacaIA = new LanzacaIA();
lanzacaIA.iniciar();

function fazerLogin() {
    const usuario = document.getElementById("usuario").value;
    const senha = document.getElementById("senha").value;

    if (!usuario || !senha) {
        alert("Preencha usuário e senha!");
        return;
    }

    if (!lanzacaIA.fazerLogin(usuario, senha)) {
        alert("Credenciais inválidas!");
    }
}

function criarUsuario() {
    const nome = document.getElementById("cadNome").value;
    const celular = document.getElementById("cadCelular").value;
    const email = document.getElementById("cadEmail").value;
    const senha = document.getElementById("cadSenha").value;

    if (!nome || !celular || !email || !senha) {
        alert("Todos os campos são obrigatórios!");
        return;
    }

    if (senha.length < 6) {
        alert("Senha mínima 6 dígitos!");
        return;
    }

    try {
        lanzacaIA.criarUsuario({ nome, celular, email, senha });
        alert("Usuário criado com sucesso!");

        document.getElementById("cadNome").value = "";
        document.getElementById("cadCelular").value = "";
        document.getElementById("cadEmail").value = "";
        document.getElementById("cadSenha").value = "";
    } catch (e) {
        alert(e.message);
    }
}
</script>
