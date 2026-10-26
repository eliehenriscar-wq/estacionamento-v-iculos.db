const API = "http://127.0.0.1:8000/api";

// ==================== UTILITÁRIOS ====================
function showToast(mensagem, tipo = "success") {
    const toast = document.getElementById("toast");
    toast.textContent = mensagem;
    toast.className = `toast ${tipo} show`;
    setTimeout(() => toast.classList.remove("show"), 3500);
}

function formatarData(dataStr) {
    if (!dataStr) return "-";
    const d = new Date(dataStr);
    return d.toLocaleString("pt-BR");
}

// ==================== NAVEGAÇÃO ====================
document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
        document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
        
        btn.classList.add("active");
        document.getElementById(btn.dataset.tab).classList.add("active");

        // Atualiza dados ao trocar de aba
        if (btn.dataset.tab === "dashboard") carregarDashboard();
        if (btn.dataset.tab === "clientes") carregarClientes();
        if (btn.dataset.tab === "veiculos") {
            carregarVeiculos();
            carregarSelectClientes();
        }
        if (btn.dataset.tab === "vagas") carregarVagas();
    });
});

// ==================== DASHBOARD ====================
async function carregarDashboard() {
    try {
        const [relatorio, estacionados] = await Promise.all([
            fetch(`${API}/relatorio`).then(r => r.json()),
            fetch(`${API}/estacionados`).then(r => r.json())
        ]);

        // Cards
        document.getElementById("cards-relatorio").innerHTML = `
            <div class="card">
                <div class="label">Vagas Livres</div>
                <div class="valor">${relatorio.livres}</div>
                <div class="label">de ${relatorio.total_vagas}</div>
            </div>
            <div class="card red">
                <div class="label">Vagas Ocupadas</div>
                <div class="valor">${relatorio.ocupadas}</div>
            </div>
            <div class="card green">
                <div class="label">Normais Livres</div>
                <div class="valor">${relatorio.normais_livres}</div>
            </div>
            <div class="card purple">
                <div class="label">Preferenciais Livres</div>
                <div class="valor">${relatorio.preferenciais_livres}</div>
            </div>
            <div class="card orange">
                <div class="label">Faturamento Hoje</div>
                <div class="valor">R$ ${relatorio.faturamento_hoje.toFixed(2)}</div>
            </div>
            <div class="card">
                <div class="label">Clientes / Veículos</div>
                <div class="valor">${relatorio.total_clientes} / ${relatorio.total_veiculos}</div>
            </div>
        `;

        // Tabela de estacionados
        const tbody = document.querySelector("#tabela-estacionados tbody");
        tbody.innerHTML = estacionados.length === 0
            ? `<tr><td colspan="6" style="text-align:center">Nenhum veículo estacionado no momento</td></tr>`
            : estacionados.map(r => `
                <tr>
                    <td><strong>${r.placa}</strong></td>
                    <td>${r.marca_modelo || "-"}</td>
                    <td>${r.vaga}</td>
                    <td>${r.tipo_vaga}</td>
                    <td>${formatarData(r.entrada)}</td>
                    <td>${r.cliente || "-"}</td>
                </tr>
            `).join("");
    } catch (err) {
        showToast("Erro ao carregar dashboard", "error");
        console.error(err);
    }
}

// ==================== CLIENTES ====================
async function carregarClientes() {
    try {
        const clientes = await fetch(`${API}/clientes`).then(r => r.json());
        const tbody = document.querySelector("#tabela-clientes tbody");
        tbody.innerHTML = clientes.length === 0
            ? `<tr><td colspan="5" style="text-align:center">Nenhum cliente cadastrado</td></tr>`
            : clientes.map(c => `
                <tr>
                    <td>${c.id}</td>
                    <td>${c.nome}</td>
                    <td>${c.documento || "-"}</td>
                    <td>${c.telefone || "-"}</td>
                    <td>${c.email || "-"}</td>
                </tr>
            `).join("");
    } catch (err) {
        showToast("Erro ao carregar clientes", "error");
    }
}

document.getElementById("form-cliente").addEventListener("submit", async (e) => {
    e.preventDefault();
    const dados = {
        nome: document.getElementById("cliente-nome").value,
        documento: document.getElementById("cliente-documento").value,
        telefone: document.getElementById("cliente-telefone").value,
        email: document.getElementById("cliente-email").value
    };

    try {
        const res = await fetch(`${API}/clientes`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(dados)
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.erro || "Erro ao cadastrar");
        
        showToast(data.mensagem);
        e.target.reset();
        carregarClientes();
    } catch (err) {
        showToast(err.message, "error");
    }
});

// ==================== VEÍCULOS ====================
async function carregarSelectClientes() {
    const clientes = await fetch(`${API}/clientes`).then(r => r.json());
    const select = document.getElementById("veiculo-cliente");
    select.innerHTML = `<option value="">Sem cliente vinculado</option>` +
        clientes.map(c => `<option value="${c.id}">${c.nome}</option>`).join("");
}

async function carregarVeiculos() {
    try {
        const veiculos = await fetch(`${API}/veiculos`).then(r => r.json());
        const tbody = document.querySelector("#tabela-veiculos tbody");
        tbody.innerHTML = veiculos.length === 0
            ? `<tr><td colspan="6" style="text-align:center">Nenhum veículo cadastrado</td></tr>`
            : veiculos.map(v => `
                <tr>
                    <td><strong>${v.placa}</strong></td>
                    <td>${v.marca_modelo || "-"}</td>
                    <td>${v.cor || "-"}</td>
                    <td>${v.tipo || "-"}</td>
                    <td>${v.ano || "-"}</td>
                    <td>${v.cliente_nome || "-"}</td>
                </tr>
            `).join("");
    } catch (err) {
        showToast("Erro ao carregar veículos", "error");
    }
}

document.getElementById("form-veiculo").addEventListener("submit", async (e) => {
    e.preventDefault();
    const dados = {
        placa: document.getElementById("veiculo-placa").value,
        marca_modelo: document.getElementById("veiculo-modelo").value,
        cor: document.getElementById("veiculo-cor").value,
        tamanho: document.getElementById("veiculo-tamanho").value,
        tipo: document.getElementById("veiculo-tipo").value,
        ano: document.getElementById("veiculo-ano").value || null,
        cliente_id: document.getElementById("veiculo-cliente").value || null
    };

    try {
        const res = await fetch(`${API}/veiculos`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(dados)
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.erro || "Erro ao cadastrar");
        
        showToast(data.mensagem);
        e.target.reset();
        carregarVeiculos();
    } catch (err) {
        showToast(err.message, "error");
    }
});

// ==================== ENTRADA / SAÍDA ====================
document.getElementById("form-entrada").addEventListener("submit", async (e) => {
    e.preventDefault();
    const dados = {
        placa: document.getElementById("placa-entrada").value,
        tipo_vaga: document.getElementById("tipo-vaga").value
    };

    try {
        const res = await fetch(`${API}/entrada`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(dados)
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.erro || "Erro ao registrar entrada");
        
        showToast(`Entrada registrada! Vaga ${data.vaga} (${data.tipo_vaga})`);
        e.target.reset();
    } catch (err) {
        showToast(err.message, "error");
    }
});

document.getElementById("form-saida").addEventListener("submit", async (e) => {
    e.preventDefault();
    const placa = document.getElementById("placa-saida").value;

    try {
        const res = await fetch(`${API}/saida`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ placa })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.erro || "Erro ao registrar saída");
        
        const div = document.getElementById("resultado-saida");
        div.innerHTML = `
            <strong>Saída registrada!</strong><br>
            Entrada: ${formatarData(data.entrada)}<br>
            Saída: ${formatarData(data.saida)}<br>
            Tempo: ${data.tempo_horas} horas<br>
            <strong>Valor a pagar: R$ ${data.valor.toFixed(2)}</strong>
        `;
        div.classList.add("show");
        showToast("Saída registrada com sucesso!");
        e.target.reset();
    } catch (err) {
        showToast(err.message, "error");
    }
});

// ==================== VAGAS ====================
async function carregarVagas() {
    try {
        const vagas = await fetch(`${API}/vagas`).then(r => r.json());
        const container = document.getElementById("mapa-vagas");
        container.innerHTML = vagas.map(v => `
            <div class="vaga ${v.status} ${v.tipo}">
                Vaga ${v.numero}
                <small>${v.tipo}</small>
                <small>${v.status === "livre" ? "Livre" : "Ocupada"}</small>
            </div>
        `).join("");
    } catch (err) {
        showToast("Erro ao carregar vagas", "error");
    }
}

// ==================== INICIALIZAÇÃO ====================
carregarDashboard();
