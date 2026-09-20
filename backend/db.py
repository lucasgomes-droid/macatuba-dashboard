"""
Schema SQLite do dataset operacional + relatórios emitidos (snapshot).

Duas áreas lógicas, conforme Etapa 1 (analise-tecnica-etapa1.md):
  1) dataset operacional vivo -> tabelas pedidos / recebimentos / veiculos,
     sobrescritas a cada sync do scraper (upsert por chave natural).
  2) relatorios_emitidos -> nunca alterado depois de criado (snapshot).

Todas as colunas usam os NOMES REAIS encontrados no AppSheet (ver seção 2.4
da análise). Nada foi inventado; onde um campo não existe na fonte, a coluna
correspondente fica NULL e isso é uma limitação documentada, não um bug.
"""
import sqlite3
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "macatuba.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS pedidos (
    pedido_chave        TEXT PRIMARY KEY,   -- campo "Pedido Chave" (id estável da fonte)
    status_pedido       TEXT,
    pedido              TEXT,
    operacao            TEXT,
    tipo_pedido         TEXT,               -- Mercado Interno / Mercado Externo
    qtd_kg              REAL,
    qtd_toneladas       REAL,               -- derivado: qtd_kg / 1000
    data_envio_pv       TEXT,
    data_instrucao      TEXT,
    data_atualizada     TEXT,
    data_estufagem      TEXT,
    data_carregamento   TEXT,
    cliente             TEXT,
    pais                TEXT,
    produto             TEXT,
    tipo_carga          TEXT,
    qtd_tampas          REAL,
    qtd_pallets         REAL,
    tipo_pallet         TEXT,
    csi                 TEXT,
    lacre               TEXT,
    tipo_frete          TEXT,
    vendedor            TEXT,
    fumigacao           TEXT,
    data_expurgo        TEXT,
    data_aeracao        TEXT,
    conferente           TEXT,
    inicio_separacao    TEXT,
    termino_separacao   TEXT,
    observacao          TEXT,
    data_bi             TEXT,
    sync_id             INTEGER,
    updated_at          TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS recebimentos (
    id                  TEXT PRIMARY KEY,   -- campo "Id"
    operacao            TEXT,
    status              TEXT,
    data_criacao        TEXT,
    pedido              TEXT,
    nota_fiscal         TEXT,
    cte                 TEXT,
    valor_cte           REAL,
    fornecedor          TEXT,
    embalagem           TEXT,
    peso_kg             REAL,
    peso_toneladas      REAL,               -- derivado: peso_kg / 1000
    transportadora      TEXT,
    motorista           TEXT,
    previsao_carregamento TEXT,
    previsao_recebimento  TEXT,
    estadia             TEXT,
    valor_estadia       REAL,
    deslocamento        TEXT,
    valor_deslocamento  REAL,
    caruncho            TEXT,
    obs                 TEXT,
    sync_id             INTEGER,
    updated_at          TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS veiculos (
    row_key             TEXT PRIMARY KEY,   -- placas+data_chegada como chave sintética (ver parser.py)
    status_operacao     TEXT,
    data_chegada_patio  TEXT,
    operacao            TEXT,
    tipo_servico        TEXT,               -- Recebimento / Carregamento
    pedidos             TEXT,
    toneladas           REAL,               -- já vem em toneladas na fonte, NÃO dividir por 1000
    clientes_fornecedores TEXT,
    nome_motorista      TEXT,
    transportadora      TEXT,
    tipo_veiculo        TEXT,
    doca                TEXT,
    conferente           TEXT,
    telefone_motorista   TEXT,
    tipo_pedido         TEXT,
    pais                TEXT,
    qtd_pedidos         REAL,
    placas_veiculo      TEXT,
    estado              TEXT,
    data_entrada_doca   TEXT,
    data_saida_doca     TEXT,
    data_liberacao_nf   TEXT,
    motorista_liberado  TEXT,
    data_liberacao_motorista TEXT,
    observacoes         TEXT,
    ultima_edicao       TEXT,
    faturador           TEXT,
    tempo_espera_patio  TEXT,
    tempo_espera_doca   TEXT,
    tempo_espera_nf     TEXT,
    sync_id             INTEGER,
    updated_at          TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sync_log (
    sync_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at   TEXT DEFAULT (datetime('now')),
    finished_at  TEXT,
    status       TEXT,        -- ONLINE / OFFLINE / ERRO
    erro         TEXT,
    pedidos_count INTEGER,
    recebimentos_count INTEGER,
    veiculos_count INTEGER
);

-- Relatórios: snapshot imutável do momento da emissão (Regras 8-11 do prompt original).
CREATE TABLE IF NOT EXISTS relatorios_emitidos (
    relatorio_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    emitido_em      TEXT DEFAULT (datetime('now')),
    usuario         TEXT,
    filtros_json    TEXT NOT NULL,   -- filtros exatamente como selecionados na hora
    resumo_json     TEXT NOT NULL,   -- KPIs/indicadores calculados naquele momento
    detalhe_json    TEXT NOT NULL,   -- registros que compõem o resultado (auditoria)
    arquivo_path    TEXT             -- caminho do xlsx/csv/pdf gerado, se aplicável
);

CREATE INDEX IF NOT EXISTS idx_pedidos_operacao ON pedidos(operacao);
CREATE INDEX IF NOT EXISTS idx_recebimentos_operacao ON recebimentos(operacao);
CREATE INDEX IF NOT EXISTS idx_veiculos_operacao ON veiculos(operacao);
"""


@contextmanager
def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


if __name__ == "__main__":
    init_db()
    print(f"Banco inicializado em {DB_PATH}")
