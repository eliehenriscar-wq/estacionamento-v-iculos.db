from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

DB_NAME = "estacionamento.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Tabela de clientes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            documento TEXT UNIQUE,
            telefone TEXT,
            email TEXT,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tabela de veículos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS veiculos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            placa TEXT UNIQUE NOT NULL,
            marca_modelo TEXT,
            cor TEXT,
            tamanho TEXT,
            tipo TEXT,
            ano INTEGER,
            cliente_id INTEGER,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        )
    ''')

    # Tabela de vagas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vagas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero INTEGER UNIQUE NOT NULL,
            tipo TEXT NOT NULL,
            status TEXT DEFAULT 'livre'
        )
    ''')

    # Tabela de registros de estacionamento
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS registros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            veiculo_id INTEGER NOT NULL,
            vaga_id INTEGER NOT NULL,
            entrada TEXT NOT NULL,
            saida TEXT,
            valor REAL DEFAULT 0,
            status TEXT DEFAULT 'ativo',
            FOREIGN KEY (veiculo_id) REFERENCES veiculos(id),
            FOREIGN KEY (vaga_id) REFERENCES vagas(id)
        )
    ''')

    # Tabela de preços
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS precos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT UNIQUE NOT NULL,
            valor REAL NOT NULL
        )
    ''')

    # Inserir preços padrão (se não existirem)
    cursor.execute("SELECT COUNT(*) FROM precos")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO precos (tipo, valor) VALUES (?, ?)", [
            ('hora', 8.00),
            ('diaria', 40.00),
            ('mensal', 350.00)
        ])

    # Criar vagas padrão (se não existirem)
    cursor.execute("SELECT COUNT(*) FROM vagas")
    if cursor.fetchone()[0] == 0:
        # 20 vagas normais
        for i in range(1, 21):
            cursor.execute("INSERT INTO vagas (numero, tipo) VALUES (?, ?)", (i, 'normal'))
        # 5 vagas preferenciais
        for i in range(21, 26):
            cursor.execute("INSERT INTO vagas (numero, tipo) VALUES (?, ?)", (i, 'preferencial'))

    conn.commit()
    conn.close()

# ==================== ROTAS ====================

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('.', path)

# ---------- CLIENTES ----------
@app.route('/api/clientes', methods=['GET'])
def listar_clientes():
    conn = get_db()
    clientes = conn.execute("SELECT * FROM clientes ORDER BY nome").fetchall()
    conn.close()
    return jsonify([dict(c) for c in clientes])

@app.route('/api/clientes', methods=['POST'])
def cadastrar_cliente():
    data = request.json
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO clientes (nome, documento, telefone, email) VALUES (?, ?, ?, ?)",
            (data['nome'], data.get('documento'), data.get('telefone'), data.get('email'))
        )
        conn.commit()
        return jsonify({"id": cursor.lastrowid, "mensagem": "Cliente cadastrado com sucesso"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"erro": "Documento já cadastrado"}), 400
    finally:
        conn.close()

# ---------- VEÍCULOS ----------
@app.route('/api/veiculos', methods=['GET'])
def listar_veiculos():
    conn = get_db()
    veiculos = conn.execute('''
        SELECT v.*, c.nome as cliente_nome 
        FROM veiculos v 
        LEFT JOIN clientes c ON v.cliente_id = c.id
        ORDER BY v.placa
    ''').fetchall()
    conn.close()
    return jsonify([dict(v) for v in veiculos])

@app.route('/api/veiculos', methods=['POST'])
def cadastrar_veiculo():
    data = request.json
    conn = get_db()
    try:
        cursor = conn.execute('''
            INSERT INTO veiculos (placa, marca_modelo, cor, tamanho, tipo, ano, cliente_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['placa'].upper().replace(" ", ""),
            data.get('marca_modelo'),
            data.get('cor'),
            data.get('tamanho'),
            data.get('tipo'),
            data.get('ano'),
            data.get('cliente_id')
        ))
        conn.commit()
        return jsonify({"id": cursor.lastrowid, "mensagem": "Veículo cadastrado com sucesso"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"erro": "Placa já cadastrada"}), 400
    finally:
        conn.close()

# ---------- VAGAS ----------
@app.route('/api/vagas', methods=['GET'])
def listar_vagas():
    conn = get_db()
    vagas = conn.execute("SELECT * FROM vagas ORDER BY numero").fetchall()
    conn.close()
    return jsonify([dict(v) for v in vagas])

# ---------- ENTRADA / SAÍDA ----------
@app.route('/api/entrada', methods=['POST'])
def registrar_entrada():
    data = request.json
    placa = data['placa'].upper().replace(" ", "")
    tipo_vaga = data.get('tipo_vaga', 'normal')

    conn = get_db()
    try:
        # Busca veículo
        veiculo = conn.execute("SELECT * FROM veiculos WHERE placa = ?", (placa,)).fetchone()
        if not veiculo:
            return jsonify({"erro": "Veículo não cadastrado. Cadastre primeiro."}), 404

        # Verifica se já está estacionado
        ativo = conn.execute('''
            SELECT * FROM registros 
            WHERE veiculo_id = ? AND status = 'ativo'
        ''', (veiculo['id'],)).fetchone()
        if ativo:
            return jsonify({"erro": "Este veículo já está estacionado"}), 400

        # Busca vaga livre do tipo desejado
        vaga = conn.execute('''
            SELECT * FROM vagas 
            WHERE tipo = ? AND status = 'livre' 
            ORDER BY numero LIMIT 1
        ''', (tipo_vaga,)).fetchone()

        if not vaga:
            return jsonify({"erro": f"Não há vagas {tipo_vaga} disponíveis"}), 400

        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Cria registro
        cursor = conn.execute('''
            INSERT INTO registros (veiculo_id, vaga_id, entrada, status)
            VALUES (?, ?, ?, 'ativo')
        ''', (veiculo['id'], vaga['id'], agora))

        # Ocupa a vaga
        conn.execute("UPDATE vagas SET status = 'ocupada' WHERE id = ?", (vaga['id'],))
        conn.commit()

        return jsonify({
            "mensagem": "Entrada registrada com sucesso",
            "vaga": vaga['numero'],
            "tipo_vaga": vaga['tipo'],
            "entrada": agora
        }), 201

    finally:
        conn.close()

@app.route('/api/saida', methods=['POST'])
def registrar_saida():
    data = request.json
    placa = data['placa'].upper().replace(" ", "")

    conn = get_db()
    try:
        veiculo = conn.execute("SELECT * FROM veiculos WHERE placa = ?", (placa,)).fetchone()
        if not veiculo:
            return jsonify({"erro": "Veículo não encontrado"}), 404

        registro = conn.execute('''
            SELECT r.*, v.numero as vaga_numero, v.tipo as vaga_tipo
            FROM registros r
            JOIN vagas v ON r.vaga_id = v.id
            WHERE r.veiculo_id = ? AND r.status = 'ativo'
        ''', (veiculo['id'],)).fetchone()

        if not registro:
            return jsonify({"erro": "Este veículo não está estacionado"}), 400

        agora = datetime.now()
        entrada = datetime.strptime(registro['entrada'], "%Y-%m-%d %H:%M:%S")
        horas = (agora - entrada).total_seconds() / 3600

        # Busca preço por hora
        preco_hora = conn.execute("SELECT valor FROM precos WHERE tipo = 'hora'").fetchone()['valor']

        # Cálculo: cobra por hora (mínimo 1 hora)
        horas_cobradas = max(1, round(horas + 0.49))
        valor = horas_cobradas * preco_hora

        # Atualiza registro
        conn.execute('''
            UPDATE registros 
            SET saida = ?, valor = ?, status = 'finalizado'
            WHERE id = ?
        ''', (agora.strftime("%Y-%m-%d %H:%M:%S"), valor, registro['id']))

        # Libera vaga
        conn.execute("UPDATE vagas SET status = 'livre' WHERE id = ?", (registro['vaga_id'],))
        conn.commit()

        return jsonify({
            "mensagem": "Saída registrada com sucesso",
            "entrada": registro['entrada'],
            "saida": agora.strftime("%Y-%m-%d %H:%M:%S"),
            "tempo_horas": round(horas, 2),
            "valor": valor,
            "vaga": registro['vaga_numero']
        })

    finally:
        conn.close()

# ---------- DASHBOARD / RELATÓRIOS ----------
@app.route('/api/estacionados', methods=['GET'])
def listar_estacionados():
    conn = get_db()
    registros = conn.execute('''
        SELECT r.*, v.placa, v.marca_modelo, v.cor, vg.numero as vaga, vg.tipo as tipo_vaga,
               c.nome as cliente
        FROM registros r
        JOIN veiculos v ON r.veiculo_id = v.id
        JOIN vagas vg ON r.vaga_id = vg.id
        LEFT JOIN clientes c ON v.cliente_id = c.id
        WHERE r.status = 'ativo'
        ORDER BY r.entrada DESC
    ''').fetchall()
    conn.close()
    return jsonify([dict(r) for r in registros])

@app.route('/api/relatorio', methods=['GET'])
def relatorio():
    conn = get_db()
    
    total_vagas = conn.execute("SELECT COUNT(*) FROM vagas").fetchone()[0]
    livres = conn.execute("SELECT COUNT(*) FROM vagas WHERE status = 'livre'").fetchone()[0]
    ocupadas = total_vagas - livres
    
    preferenciais_livres = conn.execute("SELECT COUNT(*) FROM vagas WHERE tipo = 'preferencial' AND status = 'livre'").fetchone()[0]
    normais_livres = conn.execute("SELECT COUNT(*) FROM vagas WHERE tipo = 'normal' AND status = 'livre'").fetchone()[0]
    
    total_clientes = conn.execute("SELECT COUNT(*) FROM clientes").fetchone()[0]
    total_veiculos = conn.execute("SELECT COUNT(*) FROM veiculos").fetchone()[0]
    
    # Faturamento do dia
    hoje = datetime.now().strftime("%Y-%m-%d")
    faturamento = conn.execute('''
        SELECT COALESCE(SUM(valor), 0) FROM registros 
        WHERE status = 'finalizado' AND date(saida) = ?
    ''', (hoje,)).fetchone()[0]
    
    conn.close()
    
    return jsonify({
        "total_vagas": total_vagas,
        "livres": livres,
        "ocupadas": ocupadas,
        "preferenciais_livres": preferenciais_livres,
        "normais_livres": normais_livres,
        "total_clientes": total_clientes,
        "total_veiculos": total_veiculos,
        "faturamento_hoje": faturamento
    })

@app.route('/api/precos', methods=['GET'])
def listar_precos():
    conn = get_db()
    precos = conn.execute("SELECT * FROM precos").fetchall()
    conn.close()
    return jsonify([dict(p) for p in precos])

# ==================== INICIALIZAÇÃO ====================
if __name__ == '__main__':
    init_db()
    print("=" * 50)
    print("  Estacionamento Flash rodando!")
    print("  Acesse: http://127.0.0.1:8000")
    print("=" * 50)
    app.run(debug=True, port=8000)