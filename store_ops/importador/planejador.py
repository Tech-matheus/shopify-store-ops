from dataclasses import dataclass, field
from decimal import Decimal

from store_ops.catalogo import buscar_variantes_por_sku


@dataclass
class Acao:
    sku: str
    titulo: str
    tipo: str  # "criar", "atualizar", "manter" ou "pular"
    motivo: str
    produto_id: str = ""
    variante_id: str = ""
    item_estoque_id: str = ""
    estoque_atual: int = 0
    mudancas: dict = field(default_factory=dict)  # campo -> (antes, depois)


def _estoque_disponivel(variante):
    """Estoque 'available' no local escolhido, ou None se o item não está nesse local."""
    nivel = variante["inventoryItem"]["inventoryLevel"]
    if nivel is None:
        return None
    for quantidade in nivel["quantities"]:
        if quantidade["name"] == "available":
            return quantidade["quantity"]
    return None


def planejar(cliente, produtos, local_id):
    """Decide o que fazer com cada produto válido, sem escrever nada na loja."""
    acoes = []
    for produto in produtos:
        achados = buscar_variantes_por_sku(cliente, produto.sku, local_id)

        if not achados:
            acoes.append(Acao(produto.sku, produto.titulo, "criar", "SKU não existe na loja"))
            continue

        if len(achados) > 1:
            acoes.append(
                Acao(produto.sku, produto.titulo, "pular", "SKU aparece mais de uma vez na loja")
            )
            continue

        variante = achados[0]
        loja = variante["product"]
        base = dict(
            produto_id=loja["id"],
            variante_id=variante["id"],
            item_estoque_id=variante["inventoryItem"]["id"],
        )

        if loja["variantsCount"]["count"] > 1:
            acoes.append(
                Acao(
                    produto.sku,
                    produto.titulo,
                    "pular",
                    "produto com várias variantes: não vamos mexer",
                    **base,
                )
            )
            continue

        estoque_atual = _estoque_disponivel(variante)
        if estoque_atual is None:
            acoes.append(
                Acao(
                    produto.sku,
                    produto.titulo,
                    "pular",
                    "produto não está estocado no local escolhido",
                    **base,
                )
            )
            continue

        mudancas = {}
        if loja["title"] != produto.titulo:
            mudancas["titulo"] = (loja["title"], produto.titulo)
        if (loja["productType"] or "") != produto.tipo:
            mudancas["tipo"] = (loja["productType"] or "", produto.tipo)
        if Decimal(variante["price"]) != produto.preco:
            mudancas["preco"] = (Decimal(variante["price"]), produto.preco)
        if estoque_atual != produto.estoque:
            mudancas["estoque"] = (estoque_atual, produto.estoque)

        if mudancas:
            acoes.append(
                Acao(
                    produto.sku,
                    produto.titulo,
                    "atualizar",
                    "mudou: " + ", ".join(mudancas),
                    estoque_atual=estoque_atual,
                    mudancas=mudancas,
                    **base,
                )
            )
        else:
            acoes.append(
                Acao(
                    produto.sku,
                    produto.titulo,
                    "manter",
                    "já está igual à planilha",
                    estoque_atual=estoque_atual,
                    **base,
                )
            )
    return acoes