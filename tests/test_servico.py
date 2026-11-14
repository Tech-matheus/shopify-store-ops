from store_ops.api.servico import estoque_baixo, listar_todas_variantes


def variante(sku="A", estoque=3, status="ACTIVE", rastreado=True, titulo="Produto"):
    return {
        "sku": sku,
        "price": "10.00",
        "inventoryQuantity": estoque,
        "inventoryItem": {"tracked": rastreado},
        "product": {"title": titulo, "status": status},
    }


class ClientePaginado:
    """Devolve páginas de 100 variantes e guarda os cursores recebidos."""

    def __init__(self, total):
        self.total = total
        self.cursores = []

    def graphql(self, consulta, variaveis=None):
        cursor = variaveis["depois"]
        self.cursores.append(cursor)
        inicio = int(cursor) if cursor else 0
        fim = min(inicio + 100, self.total)
        return {
            "productVariants": {
                "nodes": [variante(sku=f"S{i}") for i in range(inicio, fim)],
                "pageInfo": {"hasNextPage": fim < self.total, "endCursor": str(fim)},
            }
        }


def test_so_ativos_e_rastreados():
    variantes = [
        variante("OK"),
        variante("RASCUNHO", status="DRAFT"),
        variante("ARQUIVADO", status="ARCHIVED"),
        variante("SEM-CONTROLE", rastreado=False, estoque=0),
    ]
    assert [p.sku for p in estoque_baixo(variantes, ate=5)] == ["OK"]


def test_ordena_do_menor_para_o_maior():
    variantes = [variante("C", 4), variante("A", 0), variante("B", 2)]
    assert [p.sku for p in estoque_baixo(variantes, ate=5)] == ["A", "B", "C"]


def test_limite_e_inclusivo():
    variantes = [variante("IGUAL", 5), variante("ACIMA", 6)]
    assert [p.sku for p in estoque_baixo(variantes, ate=5)] == ["IGUAL"]


def test_ignora_estoque_vazio():
    assert estoque_baixo([variante("X", estoque=None)], ate=5) == []


def test_paginacao_junta_as_paginas():
    cliente = ClientePaginado(250)
    todas = listar_todas_variantes(cliente)
    assert len(todas) == 250
    assert cliente.cursores == [None, "100", "200"]


def test_paginacao_respeita_o_limite_total():
    cliente = ClientePaginado(1000)
    todas = listar_todas_variantes(cliente, limite_total=150)
    assert len(todas) == 150
    assert len(cliente.cursores) == 2