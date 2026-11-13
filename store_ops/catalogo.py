from store_ops.shopify_client import ShopifyErro

CONSULTA_SKU = """
query($consulta: String!, $localId: ID!) {
  productVariants(first: 5, query: $consulta) {
    nodes {
      id
      sku
      price
      inventoryItem {
        id
        inventoryLevel(locationId: $localId) {
          quantities(names: ["available"]) { name quantity }
        }
      }
      product { id title productType variantsCount { count } }
    }
  }
}
"""

CONSULTA_LOCAIS = """
{
  locations(first: 10) {
    nodes { id name isActive }
  }
}
"""


def buscar_variantes_por_sku(cliente, sku, local_id):
    """Procura o SKU na loja. Só devolve variantes com SKU exatamente igual."""
    # O SKU já foi validado (só letras, números e hífen), então é seguro na busca.
    dados = cliente.graphql(CONSULTA_SKU, {"consulta": f'sku:"{sku}"', "localId": local_id})
    return [v for v in dados["productVariants"]["nodes"] if v["sku"] == sku]


def listar_locais(cliente):
    dados = cliente.graphql(CONSULTA_LOCAIS)
    return [local for local in dados["locations"]["nodes"] if local["isActive"]]


def escolher_local(locais, nome=""):
    """Escolhe o local de estoque. Com mais de um local, o nome é obrigatório."""
    nomes = ", ".join(local["name"] for local in locais) or "nenhum"
    if nome:
        for local in locais:
            if local["name"] == nome:
                return local
        raise ShopifyErro(f'Local "{nome}" não encontrado. Disponíveis: {nomes}')
    if len(locais) == 1:
        return locais[0]
    raise ShopifyErro(
        "A loja tem mais de um local. Defina SHOPIFY_LOCAL_ESTOQUE no .env. "
        f"Disponíveis: {nomes}"
    )