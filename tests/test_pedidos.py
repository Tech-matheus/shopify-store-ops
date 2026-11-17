from datetime import datetime, timezone
from decimal import Decimal

from store_ops.api.pedidos import filtro_desde, listar_pedidos, resumir_pedidos


def pedido(valor="100.00", itens=None, cancelado=False):
    itens = itens if itens is not None else [("Camiseta", "CAM-001", 1)]
    return {
        "createdAt": "2026-11-10T12:00:00Z",
        "cancelledAt": "2026-11-11T12:00:00Z" if cancelado else None,
        "currentTotalPriceSet": {"shopMoney": {"amount": valor, "currencyCode": "USD"}},
        "lineItems": {"nodes": [{"title": t, "sku": s, "quantity": q} for t, s, q in itens]},
    }


class ClientePaginado:
    def __init__(self, total):
        self.total = total
        self.chamadas = []

    def graphql(self, consulta, variaveis=None):
        self.chamadas.append(variaveis)
        inicio = int(variaveis["depois"]) if variaveis["depois"] else 0
        fim = min(inicio + 25, self.total)
        return {
            "orders": {
                "nodes": [pedido() for _ in range(inicio, fim)],
                "pageInfo": {"hasNextPage": fim < self.total, "endCursor": str(fim)},
            }
        }


def test_soma_receita_e_calcula_ticket_medio():
    resumo = resumir_pedidos([pedido("100.00"), pedido("50.50")], dias=30)
    assert resumo.total_pedidos == 2
    assert resumo.receita == Decimal("150.50")
    assert resumo.ticket_medio == Decimal("75.25")
    assert resumo.moeda == "USD"


def test_cancelado_e_contado_mas_nao_soma():
    resumo = resumir_pedidos([pedido("100.00"), pedido("999.00", cancelado=True)], dias=30)
    assert resumo.total_pedidos == 1
    assert resumo.pedidos_cancelados == 1
    assert resumo.receita == Decimal("100.00")


def test_mais_vendidos_soma_quantidades_entre_pedidos():
    pedidos = [
        pedido(itens=[("Camiseta", "CAM-001", 2), ("Boné", "BON-001", 1)]),
        pedido(itens=[("Camiseta", "CAM-001", 3)]),
    ]
    resumo = resumir_pedidos(pedidos, dias=30)
    assert resumo.itens_vendidos == 6
    assert [(p.titulo, p.quantidade) for p in resumo.mais_vendidos] == [("Camiseta", 5), ("Boné", 1)]


def test_mostra_so_os_5_mais_vendidos():
    itens = [(f"Produto {i}", f"P{i}", i + 1) for i in range(8)]
    resumo = resumir_pedidos([pedido(itens=itens)], dias=30)
    assert len(resumo.mais_vendidos) == 5
    assert resumo.mais_vendidos[0].titulo == "Produto 7"


def test_sem_pedidos_devolve_zeros():
    resumo = resumir_pedidos([], dias=7)
    assert resumo.total_pedidos == 0
    assert resumo.receita == Decimal("0.00")
    assert resumo.ticket_medio == Decimal("0.00")
    assert resumo.moeda is None
    assert resumo.mais_vendidos == []


def test_filtro_de_data():
    agora = datetime(2026, 11, 14, 12, 0, 0, tzinfo=timezone.utc)
    assert filtro_desde(30, agora) == "created_at:>='2026-10-15T12:00:00Z'"


def test_paginacao_e_limite_total():
    cliente = ClientePaginado(100)
    assert len(listar_pedidos(cliente, dias=30)) == 100
    assert [c["depois"] for c in cliente.chamadas] == [None, "25", "50", "75"]
    cliente = ClientePaginado(1000)
    assert len(listar_pedidos(cliente, dias=30, limite_total=30)) == 30
    assert len(cliente.chamadas) == 2