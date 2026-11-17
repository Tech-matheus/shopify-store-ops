from datetime import datetime, timedelta, timezone
from decimal import Decimal

from store_ops.api.modelos import ProdutoVendidoOut, ResumoPedidosOut

CONSULTA_PEDIDOS = """
query($primeiros: Int!, $depois: String, $filtro: String!) {
  orders(first: $primeiros, after: $depois, query: $filtro, sortKey: CREATED_AT, reverse: true) {
    nodes {
      createdAt
      cancelledAt
      currentTotalPriceSet { shopMoney { amount currencyCode } }
      lineItems(first: 20) { nodes { title sku quantity } }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""


def filtro_desde(dias, agora=None):
    """Filtro de busca da Shopify: pedidos criados nos últimos 'dias' dias."""
    agora = agora or datetime.now(timezone.utc)
    inicio = agora - timedelta(days=dias)
    return f"created_at:>='{inicio.strftime('%Y-%m-%dT%H:%M:%SZ')}'"


def listar_pedidos(cliente, dias, limite_total=500):
    """Busca os pedidos do período, 25 por página, até o limite total."""
    pedidos = []
    cursor = None
    filtro = filtro_desde(dias)
    while len(pedidos) < limite_total:
        dados = cliente.graphql(
            CONSULTA_PEDIDOS, {"primeiros": 25, "depois": cursor, "filtro": filtro}
        )
        pagina = dados["orders"]
        pedidos.extend(pagina["nodes"])
        if not pagina["pageInfo"]["hasNextPage"]:
            break
        cursor = pagina["pageInfo"]["endCursor"]
    return pedidos[:limite_total]


def resumir_pedidos(pedidos, dias):
    """Receita e itens vendidos. Pedidos cancelados são contados, mas não somam."""
    ativos = [p for p in pedidos if p["cancelledAt"] is None]

    receita = sum(
        (Decimal(p["currentTotalPriceSet"]["shopMoney"]["amount"]) for p in ativos),
        Decimal("0"),
    )
    moeda = (
        pedidos[0]["currentTotalPriceSet"]["shopMoney"]["currencyCode"] if pedidos else None
    )

    vendidos = {}
    for pedido in ativos:
        for item in pedido["lineItems"]["nodes"]:
            chave = (item["title"], item["sku"])
            vendidos[chave] = vendidos.get(chave, 0) + item["quantity"]

    ranking = sorted(vendidos.items(), key=lambda par: (-par[1], par[0][0]))
    mais_vendidos = [
        ProdutoVendidoOut(titulo=titulo, sku=sku, quantidade=quantidade)
        for (titulo, sku), quantidade in ranking[:5]
    ]
    ticket = (receita / len(ativos)).quantize(Decimal("0.01")) if ativos else Decimal("0.00")

    return ResumoPedidosOut(
        dias=dias,
        total_pedidos=len(ativos),
        pedidos_cancelados=len(pedidos) - len(ativos),
        receita=receita.quantize(Decimal("0.01")),
        moeda=moeda,
        ticket_medio=ticket,
        itens_vendidos=sum(vendidos.values()),
        mais_vendidos=mais_vendidos,
    )