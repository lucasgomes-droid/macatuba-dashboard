"""
Scraper do AppSheet "ICC - Gestão Operacional" (Playwright, headless,
sessão reaproveitada de storage_state.json gerado por login_setup.py).

COMO RODA (Etapa 1/2.1 da análise técnica):
  1) Abre cada view (Pedidos, Recebimentos, Veículos) já logado.
  2) Extrai as linhas da tabela.
  3) Normaliza com scraper/parser.py.
  4) Grava no SQLite (backend/db.py) — upsert, sem apagar histórico.
  5) Registra o resultado em sync_log (pra alimentar o indicador
     ONLINE/OFFLINE e "última atualização" pedidos no prompt original).

AVISO IMPORTANTE (documentado, não escondido):
Os seletores de linha abaixo (`_extract_rows`) foram desenhados a partir da
árvore de acessibilidade que inspecionei manualmente no navegador (cada linha
é um elemento clicável com os valores das células como filhos, na mesma ordem
do cabeçalho). Não tive como testar esse script rodando de fato contra o
AppSheet autenticado a partir daqui (ambiente sem a sua sessão de login).
Na PRIMEIRA execução real, rode com --debug: ele salva o texto bruto de cada
linha em data/debug_rows_<view>.txt para eu (ou você) conferir se o split por
linha está alinhando certo com as colunas antes de confiar nos números.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from scraper.parser import (
    parse_pedido, parse_recebimento, parse_veiculo,
    COLUNAS_PEDIDOS,
)
from backend.db import get_conn, init_db

APP_URL = "https://www.appsheet.com/start/cbc846d6-e5b3-4820-828b-531f66c7093f"
STATE_PATH = Path(__file__).resolve().parent / "storage_state.json"
DEBUG_DIR = Path(__file__).resolve().parent.parent / "data"

VIEWS = {
    "Pedidos": "Pedidos",
    "Recebimentos": "Recebimentos",
    "Veículos": "Veículos",
}

# Cabeçalhos por view, na ordem em que aparecem na tabela (coletados na Etapa 1).
HEADERS = {
    "Pedidos": COLUNAS_PEDIDOS,
    "Recebimentos": [
        "🏷️ Id", "🏭 Operação", "🚦 Status", "📅 Data Criação", "📦 Pedido",
        "📃 Nota Fiscal", "📄 Cte", "💵 Valor Cte", "🧑‍💼 Fornecedor",
        "🛍️ Embalagem", "🔢 Peso (kg)", "🚚 Transportadora", "🧑‍✈️ Motorista",
        "📅 Previsão de Carregamento", "📅 Previsão Recebimento", "🚨 Estadia",
        "💰 Valor Estadia", "Deslocamento", "Valor Deslocamento", "Caruncho?",
        "📒 Obs",
    ],
    "Veículos": [
        "🚦 Status Operação", "📅 Data Chegada Pátio", "🏭 Operação",
        "💼 Tipo de Serviço", "📦 Pedidos", "⚖️ Toneladas",
        "💼 Clientes / Fornecedores", "🧑‍✈️ Nome Motorista", "🚚 Transportadora",
        "🚚 Tipo Veículo", "📍 Doca", "👷 Conferente", "📞 Telefone Motorista",
        "🚀 Tipo de Pedido", "🗺️ País", "🔢 Qtd Pedidos", "Watts",
        "🆎 Placas Veículo", "🗺️ Estado", "📅 Data Entrada Doca",
        "📅 Data Saída Doca", "📅 Data Liberação Nf", "👍 Motorista Liberado?",
        "📅 Data Liberação Motorista", "Observações", "Ultima_Edição",
        "Faturador", "⏳ Tempo de Espera Pátio", "⏳ Tempo de Espera Doca",
        "⏳ Tempo de Espera Nf",
    ],
}


def _extract_rows(page, view: str, debug: bool) -> list[dict]:
    """Extrai as linhas visíveis da tabela e pareia com o cabeçalho da view.

    NOTE: usa row.inner_text().split("\\n") por linha (não o texto da página
    inteira), então cada linha é isolada antes do split — reduz bastante o
    risco de mistura entre registros que existe no get_page_text corrido.
    Ainda assim, se uma célula vier vazia no meio da linha, o número de
    campos pode não bater 1:1 com o cabeçalho. Por isso comparamos o tamanho
    antes de confiar no parse, e com --debug salvamos o bruto pra conferência.
    """
    headers = HEADERS[view]
    rows_locator = page.get_by_role("button").filter(has_text="")  # refinado abaixo
    # Região da tabela: linhas de dado são os "button" dentro da region da view,
    # excluindo os botões de cabeçalho de coluna (esses têm um sub-botão "arrow").
    region = page.get_by_role("region", name=view)
    row_buttons = region.get_by_role("button")

    raw_rows: list[list[str]] = []
    count = row_buttons.count()
    for i in range(count):
        row = row_buttons.nth(i)
        text = row.inner_text()
        # heurística: linha de cabeçalho tem "arrow" no texto (botão de ordenar)
        # e é curta (só o nome da coluna) — pulamos essas.
        if text.strip() in headers or "\narrow" in text:
            continue
        parts = [p for p in text.split("\n")]
        if len(parts) < 2:
            continue
        raw_rows.append(parts)

    if debug:
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        dump = DEBUG_DIR / f"debug_rows_{view}.txt"
        with open(dump, "w", encoding="utf-8") as f:
            for parts in raw_rows[:20]:
                f.write(repr(parts) + "\n---\n")
        print(f"[debug] {view}: {len(raw_rows)} linhas cruas salvas em {dump}")

    parsed = []
    mismatches = 0
    for parts in raw_rows:
        if len(parts) != len(headers):
            mismatches += 1
            continue
        parsed.append(dict(zip(headers, parts)))

    if mismatches:
        print(f"[aviso] {view}: {mismatches} linha(s) com nº de campos "
              f"diferente do cabeçalho ({len(headers)}) — ignoradas nesta "
              f"execução. Rode com --debug pra investigar o alinhamento.")

    return parsed


def _filter_by_unidade(rows: list[dict], operacao_key: str, unidade: str) -> list[dict]:
    return [r for r in rows if r.get(operacao_key) == unidade]


def sync_once(unidade: str = "Macatuba", debug: bool = False, headless: bool = True) -> dict:
    init_db()
    if not STATE_PATH.exists():
        raise SystemExit(
            f"Não encontrei {STATE_PATH}. Rode primeiro: python scraper/login_setup.py"
        )

    counts = {"pedidos": 0, "recebimentos": 0, "veiculos": 0}
    status = "ONLINE"
    erro = None

    with get_conn() as conn:
        sync_id = conn.execute(
            "INSERT INTO sync_log (status) VALUES ('EM_ANDAMENTO')"
        ).lastrowid

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(storage_state=str(STATE_PATH))
            page = context.new_page()
            page.goto(APP_URL, wait_until="networkidle", timeout=30_000)

            for view in VIEWS:
                page.get_by_role("button", name=view, exact=True).click()
                page.wait_for_timeout(1500)  # sync interno do AppSheet
                rows = _extract_rows(page, view, debug=debug)

                if view == "Pedidos":
                    filtrados = _filter_by_unidade(rows, "🏭 Operação", unidade)
                    with get_conn() as conn:
                        for cells in filtrados:
                            rec = parse_pedido(cells)
                            rec["sync_id"] = sync_id
                            _upsert(conn, "pedidos", "pedido_chave", rec.get("pedido"), rec)
                    counts["pedidos"] = len(filtrados)

                elif view == "Recebimentos":
                    filtrados = _filter_by_unidade(rows, "🏭 Operação", unidade)
                    with get_conn() as conn:
                        for cells in filtrados:
                            rec = parse_recebimento(cells)
                            rec["sync_id"] = sync_id
                            _upsert(conn, "recebimentos", "id", rec.get("id"), rec)
                    counts["recebimentos"] = len(filtrados)

                elif view == "Veículos":
                    filtrados = _filter_by_unidade(rows, "🏭 Operação", unidade)
                    with get_conn() as conn:
                        for cells in filtrados:
                            rec = parse_veiculo(cells)
                            rec["sync_id"] = sync_id
                            _upsert(conn, "veiculos", "row_key", rec.get("row_key"), rec)
                    counts["veiculos"] = len(filtrados)

            browser.close()

    except PWTimeout as e:
        status, erro = "OFFLINE", f"timeout: {e}"
    except Exception as e:  # noqa: BLE001 — precisa capturar tudo pra marcar OFFLINE
        status, erro = "ERRO", str(e)

    with get_conn() as conn:
        conn.execute(
            """UPDATE sync_log SET finished_at=datetime('now'), status=?, erro=?,
               pedidos_count=?, recebimentos_count=?, veiculos_count=?
               WHERE sync_id=?""",
            (status, erro, counts["pedidos"], counts["recebimentos"],
             counts["veiculos"], sync_id),
        )

    return {"status": status, "erro": erro, **counts}


def _upsert(conn, table: str, key_col: str, key_val, rec: dict):
    if not key_val:
        return
    cols = list(rec.keys())
    placeholders = ",".join("?" for _ in cols)
    updates = ",".join(f"{c}=excluded.{c}" for c in cols if c != key_col)
    sql = (
        f"INSERT INTO {table} ({key_col},{','.join(c for c in cols if c != key_col)}) "
        f"VALUES (?,{','.join('?' for c in cols if c != key_col)}) "
        f"ON CONFLICT({key_col}) DO UPDATE SET {updates}"
    )
    values = [key_val] + [rec[c] for c in cols if c != key_col]
    conn.execute(sql, values)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--unidade", default="Macatuba")
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--headed", action="store_true", help="abre janela (pra depurar visualmente)")
    args = ap.parse_args()

    result = sync_once(unidade=args.unidade, debug=args.debug, headless=not args.headed)
    print(result)
