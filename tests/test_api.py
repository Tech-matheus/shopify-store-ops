import pytest
from fastapi.testclient import TestClient

from store_ops.api.app import app, obter_cliente
from store_ops.shopify_client import ShopifyErro


class ClienteFalso:
    def __init__(self, nodes=None, erro=False):
        self.nodes = nodes or []
        self.erro = erro
        self.variaveis = None

    def graphql(self, consulta, variaveis=None):
        if self.erro:
            raise ShopifyErro("detalhe interno secreto")
        self.variaveis = variaveis
        return {"productVariants": {"nodes": self.nodes}}


@pytest.fixture
def api():
    def montar(cliente):
        app.dependency_overrides[obter_cliente] = lambda: cliente
        return TestClient(app)

    yield montar
    app.dependency_overrides.clear()


def variante(sku="CAM-001", preco="59.90", estoque=25, titulo="Camiseta", status="DRAFT"):
    return {
        "sku": sku,
        "price": preco,
        "inventoryQuantity": estoque,
        "product": {"title": titulo, "status": status},
    }


def test_saude(api):
    assert api(ClienteFalso()).get("/saude").json() == {"status": "ok"}


def test_lista_produtos(api):
    resposta = api(ClienteFalso([variante()])).get("/produtos")
    assert resposta.status_code == 200
    assert resposta.json() == [
        {"sku": "CAM-001", "titulo": "Camiseta", "status": "DRAFT", "preco": "59.90", "estoque": 25}
    ]


def test_produto_sem_sku_e_aceito(api):
    resposta = api(ClienteFalso([variante(sku=None)])).get("/produtos")
    assert resposta.status_code == 200
    assert resposta.json()[0]["sku"] is None


def test_limite_vai_para_a_consulta(api):
    cliente = ClienteFalso()
    api(cliente).get("/produtos?limite=5")
    assert cliente.variaveis == {"primeiros": 5}


@pytest.mark.parametrize("limite", [0, 101])
def test_limite_invalido(api, limite):
    assert api(ClienteFalso()).get(f"/produtos?limite={limite}").status_code == 422


def test_erro_da_shopify_vira_502_sem_vazar_detalhe(api):
    resposta = api(ClienteFalso(erro=True)).get("/produtos")
    assert resposta.status_code == 502
    assert "secreto" not in resposta.text

class ClienteComPaginas:
    def __init__(self, nodes=None, erro=False):
        self.nodes = nodes or []
        self.erro = erro

    def graphql(self, consulta, variaveis=None):
        if self.erro:
            raise ShopifyErro("detalhe interno secreto")
        return {
            "productVariants": {
                "nodes": self.nodes,
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }


def variante_estoque(sku, estoque, status="ACTIVE", rastreado=True):
    return {
        "sku": sku,
        "price": "10.00",
        "inventoryQuantity": estoque,
        "inventoryItem": {"tracked": rastreado},
        "product": {"title": "Produto", "status": status},
    }


def test_estoque_baixo_filtra_e_ordena(api):
    cliente = ClienteComPaginas(
        [
            variante_estoque("B", 4),
            variante_estoque("A", 1),
            variante_estoque("C", 50),
            variante_estoque("D", 0, rastreado=False),
        ]
    )
    resposta = api(cliente).get("/estoque/baixo?ate=5")
    assert resposta.status_code == 200
    assert [p["sku"] for p in resposta.json()] == ["A", "B"]


def test_estoque_baixo_limite_invalido(api):
    assert api(ClienteComPaginas()).get("/estoque/baixo?ate=-1").status_code == 422


def test_estoque_baixo_erro_da_shopify_vira_502(api):
    resposta = api(ClienteComPaginas(erro=True)).get("/estoque/baixo")
    assert resposta.status_code == 502
    assert "secreto" not in resposta.text