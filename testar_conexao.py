from store_ops.shopify_client import ShopifyClient, ShopifyErro

CONSULTA = """
{
  shop { name myshopifyDomain }
  products(first: 5) {
    nodes { title handle status }
  }
}
"""

try:
    cliente = ShopifyClient()
    dados = cliente.graphql(CONSULTA)
except (ShopifyErro, RuntimeError) as erro:
    print("ERRO:", erro)
else:
    print("Loja:", dados["shop"]["name"], "-", dados["shop"]["myshopifyDomain"])
    print("Primeiros produtos:")
    for produto in dados["products"]["nodes"]:
        print(f"  - {produto['title']} ({produto['status']})")