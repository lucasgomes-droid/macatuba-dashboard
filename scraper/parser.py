"""
Normaliza uma linha extraída do AppSheet (dict: cabeçalho real -> texto da célula)
para o formato interno usado no SQLite (backend/db.py).

O scraper (scraper.py) é responsável por produzir esse dict por linha, pareando
cada célula com o cabeçalho da coluna na mesma posição (extração por DOM, não
por texto corrido — ver nota na Etapa 1 sobre por que get_page_text não é
confiável para isso: ele omite células vazias e quebra o alinhamento).

Todas as chaves de entrada usam o texto EXATO do cabeçalho como aparece no
AppSheet (com o emoji), coletado na Etapa 1. Nada aqui inventa campo novo.
"""
import re

# --- helpers de normalização -------------------------------------------------

def _num_br(value: str | None) -> float | None:
    """Converte número no formato BR ("12.500" = doze mil e quinhentos,
    "25,60" = vinte e cinco vírgula seis) para float. Vazio -> None."""
    if value is None:
        return None
    v = value.strip()
    if v == "" or v == "-":
        return None
    v = v.replace(".", "").replace(",", ".")
    try:
        return float(v)
    except ValueError:
        return None


def kg_to_toneladas(kg: float | None) -> float | None:
    """Regra de padronização (seção 5 do prompt original): t = kg / 1000."""
    if kg is None:
        return None
    return round(kg / 1000, 3)


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    v = value.strip()
    return v if v != "" else None


# --- Pedidos ------------------------------------------------------------------

COLUNAS_PEDIDOS = [
    "🚦 Status Pedido", "📃 Pedido", "🏭 Operação", "💼 Tipo de Pedido",
    "🔢 Qtd (Kg)", "📅 Data Envio PV", "📅 Data Instrução",
    "📅 Data Atualizada ( Se Tiver alguma alteração)",
    "📅 Data Estufagem (Reschedule)",
    "📅 Data Carregamento ( Quando o veículo foi Carregado)",
    "🧑‍💼 Cliente", "País", "📦 Produto", "🎯 Tipo de Carga",
    "🔢 Qtd Tampas", "🔢 Qtd Pallets", "🧩 Tipo de Pallet", "🚢 Csi",
    "🏷️ Lacre", "🚚 Tipo de Frete", "👨‍💼 Vendedor", "🕷️ Fumigação",
    "📅 Data Expurgo", "📅 Data Aeração", "👷 Conferente",
    "📅 Inicio Separação", "📅 Término Separação", "Observação",
]

STATUS_PEDIDO_VALIDOS = {
    "Aguardando OP", "Não Iniciado", "Em Fumigação", "Aguardando Carregamento",
    "Em Separação", "Cancelado", "Carregado", "Suspenso",
}


def parse_pedido(cells: dict) -> dict:
    qtd_kg = _num_br(cells.get("🔢 Qtd (Kg)"))
    status = _clean(cells.get("🚦 Status Pedido"))
    if status and status not in STATUS_PEDIDO_VALIDOS:
        # não derruba o sync — só sinaliza um status novo que a fonte passou a usar
        status = status  # mantém o valor real; validação fica pro backend logar
    return {
        "status_pedido": status,
        "pedido": _clean(cells.get("📃 Pedido")),
        "operacao": _clean(cells.get("🏭 Operação")),
        "tipo_pedido": _clean(cells.get("💼 Tipo de Pedido")),
        "qtd_kg": qtd_kg,
        "qtd_toneladas": kg_to_toneladas(qtd_kg),
        "data_envio_pv": _clean(cells.get("📅 Data Envio PV")),
        "data_instrucao": _clean(cells.get("📅 Data Instrução")),
        "data_atualizada": _clean(cells.get("📅 Data Atualizada ( Se Tiver alguma alteração)")),
        "data_estufagem": _clean(cells.get("📅 Data Estufagem (Reschedule)")),
        "data_carregamento": _clean(cells.get("📅 Data Carregamento ( Quando o veículo foi Carregado)")),
        "cliente": _clean(cells.get("🧑‍💼 Cliente")),
        "pais": _clean(cells.get("País")),
        "produto": _clean(cells.get("📦 Produto")),
        "tipo_carga": _clean(cells.get("🎯 Tipo de Carga")),
        "qtd_tampas": _num_br(cells.get("🔢 Qtd Tampas")),
        "qtd_pallets": _num_br(cells.get("🔢 Qtd Pallets")),
        "tipo_pallet": _clean(cells.get("🧩 Tipo de Pallet")),
        "csi": _clean(cells.get("🚢 Csi")),
        "lacre": _clean(cells.get("🏷️ Lacre")),
        "tipo_frete": _clean(cells.get("🚚 Tipo de Frete")),
        "vendedor": _clean(cells.get("👨‍💼 Vendedor")),
        "fumigacao": _clean(cells.get("🕷️ Fumigação")),
        "data_expurgo": _clean(cells.get("📅 Data Expurgo")),
        "data_aeracao": _clean(cells.get("📅 Data Aeração")),
        "conferente": _clean(cells.get("👷 Conferente")),
        "inicio_separacao": _clean(cells.get("📅 Inicio Separação")),
        "termino_separacao": _clean(cells.get("📅 Término Separação")),
        "observacao": _clean(cells.get("Observação")),
    }


# --- Recebimentos ---------------------------------------------------------------

STATUS_RECEBIMENTO_VALIDOS = {
    "Descarregado", "Carregado", "Programado", "Não Descarregado",
    "Confirmado", "Não se Apresentou", "",
}


def parse_recebimento(cells: dict) -> dict:
    peso_kg = _num_br(cells.get("🔢 Peso (kg)"))
    return {
        "id": _clean(cells.get("🏷️ Id")),
        "operacao": _clean(cells.get("🏭 Operação")),
        "status": _clean(cells.get("🚦 Status")) or "",
        "data_criacao": _clean(cells.get("📅 Data Criação")),
        "pedido": _clean(cells.get("📦 Pedido")),
        "nota_fiscal": _clean(cells.get("📃 Nota Fiscal")),
        "cte": _clean(cells.get("📄 Cte")),
        "valor_cte": _num_br(cells.get("💵 Valor Cte")),
        "fornecedor": _clean(cells.get("🧑‍💼 Fornecedor")),
        "embalagem": _clean(cells.get("🛍️ Embalagem")),
        "peso_kg": peso_kg,
        "peso_toneladas": kg_to_toneladas(peso_kg),
        "transportadora": _clean(cells.get("🚚 Transportadora")),
        "motorista": _clean(cells.get("🧑‍✈️ Motorista")),
        "previsao_carregamento": _clean(cells.get("📅 Previsão de Carregamento")),
        "previsao_recebimento": _clean(cells.get("📅 Previsão Recebimento")),
        "estadia": _clean(cells.get("🚨 Estadia")),
        "valor_estadia": _num_br(cells.get("💰 Valor Estadia")),
        "deslocamento": _clean(cells.get("Deslocamento")),
        "valor_deslocamento": _num_br(cells.get("Valor Deslocamento")),
        "caruncho": _clean(cells.get("Caruncho?")),
        "obs": _clean(cells.get("📒 Obs")),
    }


# --- Veículos ---------------------------------------------------------------

STATUS_OPERACAO_VALIDOS = {"Carregado", "Descarregado", "Reprovado", "Desistência"}


def parse_veiculo(cells: dict) -> dict:
    toneladas = _num_br(cells.get("⚖️ Toneladas"))  # já em toneladas na fonte
    placas = _clean(cells.get("🆎 Placas Veículo")) or ""
    chegada = _clean(cells.get("📅 Data Chegada Pátio")) or ""
    return {
        "row_key": f"{placas}|{chegada}",  # chave sintética: não há id único exposto
        "status_operacao": _clean(cells.get("🚦 Status Operação")),
        "data_chegada_patio": chegada,
        "operacao": _clean(cells.get("🏭 Operação")),
        "tipo_servico": _clean(cells.get("💼 Tipo de Serviço")),
        "pedidos": _clean(cells.get("📦 Pedidos")),
        "toneladas": toneladas,
        "clientes_fornecedores": _clean(cells.get("💼 Clientes / Fornecedores")),
        "nome_motorista": _clean(cells.get("🧑‍✈️ Nome Motorista")),
        "transportadora": _clean(cells.get("🚚 Transportadora")),
        "tipo_veiculo": _clean(cells.get("🚚 Tipo Veículo")),
        "doca": _clean(cells.get("📍 Doca")),
        "conferente": _clean(cells.get("👷 Conferente")),
        "telefone_motorista": _clean(cells.get("📞 Telefone Motorista")),
        "tipo_pedido": _clean(cells.get("🚀 Tipo de Pedido")),
        "pais": _clean(cells.get("🗺️ País")),
        "qtd_pedidos": _num_br(cells.get("🔢 Qtd Pedidos")),
        "placas_veiculo": placas,
        "estado": _clean(cells.get("🗺️ Estado")),
        "data_entrada_doca": _clean(cells.get("📅 Data Entrada Doca")),
        "data_saida_doca": _clean(cells.get("📅 Data Saída Doca")),
        "data_liberacao_nf": _clean(cells.get("📅 Data Liberação Nf")),
        "motorista_liberado": _clean(cells.get("👍 Motorista Liberado?")),
        "data_liberacao_motorista": _clean(cells.get("📅 Data Liberação Motorista")),
        "observacoes": _clean(cells.get("Observações")),
        "ultima_edicao": _clean(cells.get("Ultima_Edição")),
        "faturador": _clean(cells.get("Faturador")),
        "tempo_espera_patio": _clean(cells.get("⏳ Tempo de Espera Pátio")),
        "tempo_espera_doca": _clean(cells.get("⏳ Tempo de Espera Doca")),
        "tempo_espera_nf": _clean(cells.get("⏳ Tempo de Espera Nf")),
    }
