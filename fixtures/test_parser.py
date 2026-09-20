"""
Testa o parser contra dados REAIS lidos manualmente do AppSheet hoje
(detail view do Pedido 56453 e do Recebimento 1355 — ver Etapa 1).
Não são dados inventados: são os mesmos valores que apareceram na tela.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scraper.parser import parse_pedido, parse_recebimento, parse_veiculo

# Registro real: Pedido 56453 (detail view, Etapa 1)
pedido_56453 = {
    "🚦 Status Pedido": "Carregado",
    "📃 Pedido": "56453",
    "🏭 Operação": "Macatuba",
    "💼 Tipo de Pedido": "Mercado Interno",
    "🔢 Qtd (Kg)": "12.500",
    "📅 Data Envio PV": "24/12/2025",
    "📅 Data Instrução": "6/12/2026",
    "📅 Data Carregamento ( Quando o veículo foi Carregado)": "6/1/2026 11:10:00",
    "🧑‍💼 Cliente": "NEOVIA NUTRICAO E SAUDE ANIMAL LTDA",
    "País": "Brasil",
    "📦 Produto": "STARYEAST",
    "🎯 Tipo de Carga": "SACARIA",
    "🧩 Tipo de Pallet": "Palete MI",
    "🚢 Csi": "Não",
    "🏷️ Lacre": "Definitivo",
    "🚚 Tipo de Frete": "Fob",
    "👨‍💼 Vendedor": "MARCIA VILLACA",
    "👷 Conferente": "AGUARDANDO CONFERENTE",
    "📅 Inicio Separação": "29/12/2025",
    "📅 Término Separação": "29/12/2025",
}

# Registro real: Recebimento 1355 (detail view, Etapa 1)
recebimento_1355 = {
    "🏷️ Id": "1355",
    "🏭 Operação": "Macatuba",
    "🚦 Status": "Descarregado",
    "📅 Data Criação": "24/3/2028",
    "📦 Pedido": "159086 - 1º",
    "📃 Nota Fiscal": "48277",
    "🔢 Peso (kg)": "30.000",
    "🧑‍💼 Fornecedor": "CLARIANT",
    "🛍️ Embalagem": "Pallet",
    "🚚 Transportadora": "TRANSVICON",
    "🧑‍✈️ Motorista": "EDUARDO",
    "📅 Previsão de Carregamento": "24/3/2025",
    "📅 Previsão Recebimento": "28/3/2025",
}

# Registro real: primeira linha de Veículos (18/9/2026 23:00:10)
veiculo_1 = {
    "🚦 Status Operação": "Descarregado",
    "📅 Data Chegada Pátio": "18/9/2026 23:00:10",
    "🏭 Operação": "Jundiaí 1",
    "💼 Tipo de Serviço": "Recebimento",
    "📦 Pedidos": "195536",
    "⚖️ Toneladas": "28,00",
    "💼 Clientes / Fornecedores": "SÃO MARTINHO",
    "🧑‍✈️ Nome Motorista": "JOAO CARLOS RODRIGUES DA SILVA",
    "🚚 Transportadora": "LOTS LATIN AMERICA LOGISTICA",
    "🆎 Placas Veículo": "FTQ5H38/STY6E62",
}


def test_pedido():
    r = parse_pedido(pedido_56453)
    assert r["pedido"] == "56453"
    assert r["operacao"] == "Macatuba"
    assert r["status_pedido"] == "Carregado"
    assert r["qtd_kg"] == 12500.0, r["qtd_kg"]
    assert r["qtd_toneladas"] == 12.5, r["qtd_toneladas"]
    assert r["cliente"] == "NEOVIA NUTRICAO E SAUDE ANIMAL LTDA"
    print("OK  parse_pedido: 56453 -> 12.500 kg = 12.5 t, status=Carregado")


def test_recebimento():
    r = parse_recebimento(recebimento_1355)
    assert r["id"] == "1355"
    assert r["operacao"] == "Macatuba"
    assert r["status"] == "Descarregado"
    assert r["peso_kg"] == 30000.0
    assert r["peso_toneladas"] == 30.0
    assert r["fornecedor"] == "CLARIANT"
    print("OK  parse_recebimento: 1355 -> 30.000 kg = 30.0 t, fornecedor=CLARIANT")


def test_veiculo():
    r = parse_veiculo(veiculo_1)
    assert r["status_operacao"] == "Descarregado"
    assert r["toneladas"] == 28.0  # já em toneladas, não dividir
    assert r["operacao"] == "Jundiaí 1"
    assert r["row_key"] == "FTQ5H38/STY6E62|18/9/2026 23:00:10"
    print("OK  parse_veiculo: 28,00 já é 28.0 t (sem dividir por 1000)")


def test_campo_vazio_nao_quebra():
    r = parse_pedido({"🚦 Status Pedido": "Não Iniciado"})
    assert r["qtd_kg"] is None
    assert r["cliente"] is None
    print("OK  campos ausentes viram None, sem exceção")


if __name__ == "__main__":
    test_pedido()
    test_recebimento()
    test_veiculo()
    test_campo_vazio_nao_quebra()
    print("\nTodos os testes passaram com dados reais do AppSheet.")
