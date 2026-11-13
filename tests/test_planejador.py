from decimal import Decimal

from store_ops.importador.planejador import planejar
from store_ops.importador.validacao import Produto

LOCAL = "gid://shopify/Location/1"


class ClienteFalso:
    """Finge ser a Shopify: devolve só as variantes cujo SKU está na busca."""

    def __init__(self, variantes):
        self.variantes = variantes

    def graphql(self, consulta, variaveis=None):
        sku = variaveis["consulta"].split('"')[1]
        achadas = [v for v in self.variantes if v["sku"].lower() == sku.lower()]
        return {"productVariants": {"nodes": achadas}}


def produto(sku="CAM-001", titulo="Camiseta", preco="59.90", estoque=25, tipo="Camisetas"):
    return Produto(2, sku, titulo, Decimal(preco), estoque, tipo, "")


def variante(sku="CAM-001", variantes=1, id_final="1", titulo="Camiseta", tipo="Camisetas",
             preco="59.90", estoque=25, no_local=True):
    nivel = {"quantities": [{"name": "available", "quantity": estoque}]} if no_local else None
    return {
        "id": f"gid://shopify/ProductVariant/{id_final}",
        "sku": sku,
        "price": preco,
        "inventoryItem": {"id": f"gid://shopify/InventoryItem/{id_final}", "inventoryLevel": nivel},
        "product": {
            "id": f"gid://shopify/Product/{id_final}",
            "title": titulo,
            "productType": tipo,
            "variantsCount": {"count": variantes},
        },
    }


def planejar_um(variantes, **dados):
    return planejar(ClienteFalso(variantes), [produto(**dados)], LOCAL)[0]


def test_sku_novo_vira_criar():
    assert planejar_um([]).tipo == "criar"


def test_tudo_igual_vira_manter():
    acao = planejar_um([variante()])
    assert acao.tipo == "manter"
    assert acao.mudancas == {}


def test_preco_diferente_vira_atualizar_so_o_preco():
    acao = planejar_um([variante(preco="49.90")])
    assert acao.tipo == "atualizar"
    assert list(acao.mudancas) == ["preco"]
    assert acao.mudancas["preco"] == (Decimal("49.90"), Decimal("59.90"))


def test_estoque_diferente_guarda_o_estoque_atual():
    acao = planejar_um([variante(estoque=10)])
    assert list(acao.mudancas) == ["estoque"]
    assert acao.estoque_atual == 10


def test_varias_mudancas_juntas():
    acao = planejar_um([variante(titulo="Antigo", preco="10.00", estoque=1)])
    assert set(acao.mudancas) == {"titulo", "preco", "estoque"}


def test_produto_com_varias_variantes_e_pulado():
    assert planejar_um([variante(variantes=3)]).tipo == "pular"


def test_sku_repetido_na_loja_e_pulado():
    achados = [variante(id_final="1"), variante(id_final="2")]
    assert planejar_um(achados).tipo == "pular"


def test_produto_fora_do_local_e_pulado():
    acao = planejar_um([variante(no_local=False)])
    assert acao.tipo == "pular"
    assert "local" in acao.motivo


def test_sku_com_maiuscula_diferente_nao_conta_como_igual():
    # A Shopify trata SKU com diferença de maiúscula/minúscula como diferente.
    assert planejar_um([variante(sku="cam-001")]).tipo == "criar"