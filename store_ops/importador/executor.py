import uuid
from dataclasses import dataclass

from store_ops.shopify_client import ShopifyErro

MUTACAO_CRIAR = """
mutation($input: ProductSetInput!) {
  productSet(input: $input, synchronous: true) {
    product { id title }
    userErrors { field message code }
  }
}
"""

MUTACAO_PRODUTO = """
mutation($product: ProductUpdateInput!) {
  productUpdate(product: $product) {
    product { id }
    userErrors { field message }
  }
}
"""

MUTACAO_PRECO = """
mutation($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
  productVariantsBulkUpdate(productId: $productId, variants: $variants) {
    productVariants { id price }
    userErrors { field message }
  }
}
"""

MUTACAO_ESTOQUE = """
mutation($input: InventorySetQuantitiesInput!, $chave: String!) {
  inventorySetQuantities(input: $input) @idempotent(key: $chave) {
    inventoryAdjustmentGroup { reason }
    userErrors { code field message }
  }
}
"""


@dataclass
class Resultado:
    sku: str
    acao: str
    status: str  # "ok", "erro", "simulado", "pulado" ou "igual"
    detalhe: str = ""
    produto_id: str = ""


def descrever_mudancas(mudancas):
    return "; ".join(f"{campo}: {antes} → {depois}" for campo, (antes, depois) in mudancas.items())


def _checar(resposta):
    if resposta["userErrors"]:
        raise ShopifyErro("; ".join(e["message"] for e in resposta["userErrors"]))


def montar_entrada_criacao(produto, local_id):
    """Monta os dados de um produto simples (sem variações) para o productSet."""
    return {
        "title": produto.titulo,
        "productType": produto.tipo,
        "status": "DRAFT",  # rascunho: o lojista revisa antes de publicar
        "productOptions": [
            {"name": "Title", "position": 1, "values": [{"name": "Default Title"}]}
        ],
        "variants": [
            {
                "optionValues": [{"optionName": "Title", "name": "Default Title"}],
                "sku": produto.sku,
                "price": str(produto.preco),
                "inventoryItem": {"tracked": True},
                "inventoryQuantities": [
                    {"locationId": local_id, "name": "available", "quantity": produto.estoque}
                ],
            }
        ],
    }


def criar_produto(cliente, produto, local_id):
    dados = cliente.graphql(MUTACAO_CRIAR, {"input": montar_entrada_criacao(produto, local_id)})
    resposta = dados["productSet"]
    _checar(resposta)
    return resposta["product"]["id"]


def atualizar_produto(cliente, acao, produto, local_id, feito):
    """Aplica só o que mudou. Vai anotando em 'feito' cada parte concluída."""
    mudancas = acao.mudancas

    if "titulo" in mudancas or "tipo" in mudancas:
        dados = cliente.graphql(
            MUTACAO_PRODUTO,
            {"product": {"id": acao.produto_id, "title": produto.titulo, "productType": produto.tipo}},
        )
        _checar(dados["productUpdate"])
        feito.append("título/tipo")

    if "preco" in mudancas:
        dados = cliente.graphql(
            MUTACAO_PRECO,
            {
                "productId": acao.produto_id,
                "variants": [{"id": acao.variante_id, "price": str(produto.preco)}],
            },
        )
        _checar(dados["productVariantsBulkUpdate"])
        feito.append("preço")

    if "estoque" in mudancas:
        entrada = {
            "name": "available",
            "reason": "correction",
            "quantities": [
                {
                    "inventoryItemId": acao.item_estoque_id,
                    "locationId": local_id,
                    "quantity": produto.estoque,
                    # Só grava se o estoque na loja ainda for o que lemos no plano.
                    "changeFromQuantity": acao.estoque_atual,
                }
            ],
        }
        dados = cliente.graphql(MUTACAO_ESTOQUE, {"input": entrada, "chave": str(uuid.uuid4())})
        _checar(dados["inventorySetQuantities"])
        feito.append("estoque")


def executar(cliente, acoes, produtos, local_id, aplicar):
    """Executa o plano. Sem aplicar=True, nada é enviado para a loja."""
    por_sku = {p.sku: p for p in produtos}
    resultados = []

    for acao in acoes:
        if acao.tipo == "pular":
            resultados.append(Resultado(acao.sku, "pular", "pulado", acao.motivo, acao.produto_id))
        elif acao.tipo == "manter":
            resultados.append(Resultado(acao.sku, "manter", "igual", acao.motivo, acao.produto_id))
        elif not aplicar:
            detalhe = descrever_mudancas(acao.mudancas) if acao.tipo == "atualizar" else "nada foi enviado"
            resultados.append(Resultado(acao.sku, acao.tipo, "simulado", detalhe, acao.produto_id))
        elif acao.tipo == "criar":
            try:
                produto_id = criar_produto(cliente, por_sku[acao.sku], local_id)
            except ShopifyErro as erro:
                resultados.append(Resultado(acao.sku, "criar", "erro", str(erro)[:300]))
            else:
                resultados.append(
                    Resultado(acao.sku, "criar", "ok", "produto criado como rascunho", produto_id)
                )
        else:  # atualizar
            feito = []
            try:
                atualizar_produto(cliente, acao, por_sku[acao.sku], local_id, feito)
            except ShopifyErro as erro:
                parte = f" (já feito: {', '.join(feito)})" if feito else ""
                resultados.append(
                    Resultado(acao.sku, "atualizar", "erro", str(erro)[:300] + parte, acao.produto_id)
                )
            else:
                resultados.append(
                    Resultado(acao.sku, "atualizar", "ok", descrever_mudancas(acao.mudancas), acao.produto_id)
                )
    return resultados