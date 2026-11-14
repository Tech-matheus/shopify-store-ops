from store_ops.api.modelos import ProdutoOut

CONSULTA_VARIANTES = """
query($primeiros: Int!, $depois: String) {
  productVariants(first: $primeiros, after: $depois) {
    nodes {
      sku
      price
      inventoryQuantity
      inventoryItem { tracked }
      product { title status }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""


def listar_todas_variantes(cliente, limite_total=1000):
    """Busca as variantes página por página (100 por vez) até o limite total."""
    variantes = []
    cursor = None
    while len(variantes) < limite_total:
        dados = cliente.graphql(CONSULTA_VARIANTES, {"primeiros": 100, "depois": cursor})
        pagina = dados["productVariants"]
        variantes.extend(pagina["nodes"])
        if not pagina["pageInfo"]["hasNextPage"]:
            break
        cursor = pagina["pageInfo"]["endCursor"]
    return variantes[:limite_total]


def para_produto(variante):
    return ProdutoOut(
        sku=variante["sku"],
        titulo=variante["product"]["title"],
        status=variante["product"]["status"],
        preco=variante["price"],
        estoque=variante["inventoryQuantity"],
    )


def estoque_baixo(variantes, ate):
    """Produtos ativos, com controle de estoque ligado e estoque até o limite (inclusive).

    Itens sem controle de estoque (como vale-presente) mostram 0 na Shopify,
    mas não estão "acabando", então ficam de fora.
    """
    achados = [
        v
        for v in variantes
        if v["product"]["status"] == "ACTIVE"
        and v["inventoryItem"]["tracked"]
        and v["inventoryQuantity"] is not None
        and v["inventoryQuantity"] <= ate
    ]
    achados.sort(key=lambda v: v["inventoryQuantity"])
    return [para_produto(v) for v in achados]