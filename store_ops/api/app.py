from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException, Query

from store_ops.api.modelos import ProdutoOut
from store_ops.api.servico import estoque_baixo, listar_todas_variantes
from store_ops.shopify_client import ShopifyClient, ShopifyErro

app = FastAPI(title="Store Ops API", version="0.2.0")

CONSULTA_PRODUTOS = """
query($primeiros: Int!) {
  productVariants(first: $primeiros) {
    nodes {
      sku
      price
      inventoryQuantity
      product { title status }
    }
  }
}
"""


@lru_cache
def obter_cliente():
    """Um único cliente para toda a API, assim o token é reaproveitado."""
    return ShopifyClient()


@app.get("/saude")
def saude():
    return {"status": "ok"}


@app.get("/produtos", response_model=list[ProdutoOut])
def listar_produtos(
    limite: int = Query(20, ge=1, le=100),
    cliente=Depends(obter_cliente),
):
    try:
        dados = cliente.graphql(CONSULTA_PRODUTOS, {"primeiros": limite})
    except ShopifyErro:
        # Não repassamos o detalhe do erro para quem chama a API.
        raise HTTPException(status_code=502, detail="Não foi possível consultar a Shopify")

    return [
        ProdutoOut(
            sku=v["sku"],
            titulo=v["product"]["title"],
            status=v["product"]["status"],
            preco=v["price"],
            estoque=v["inventoryQuantity"],
        )
        for v in dados["productVariants"]["nodes"]
    ]


@app.get("/estoque/baixo", response_model=list[ProdutoOut])
def listar_estoque_baixo(
    ate: int = Query(5, ge=0, le=100000),
    cliente=Depends(obter_cliente),
):
    try:
        variantes = listar_todas_variantes(cliente)
    except ShopifyErro:
        raise HTTPException(status_code=502, detail="Não foi possível consultar a Shopify")
    return estoque_baixo(variantes, ate)