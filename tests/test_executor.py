import pytest
from decimal import Decimal

from store_ops.catalogo import escolher_local
from store_ops.importador.executor import executar, montar_entrada_criacao
from store_ops.importador.planejador import Acao
from store_ops.importador.validacao import Produto
from store_ops.shopify_client import ShopifyErro

LOCAL = "gid://shopify/Location/1"
NOMES = ("productSet", "productUpdate", "productVariantsBulkUpdate", "inventorySetQuantities")


class ClienteGravador:
    """Guarda cada chamada e pode simular erro da loja em uma mutação."""

    def __init__(self, erro_em=None):
        self.chamadas = []
        self.erro_em = erro_em

    def graphql(self, consulta, variaveis=None):
        nome = next(n for n in NOMES if n in consulta)
        self.chamadas.append((nome, variaveis))
        erros = [{"field": ["x"], "message": "falhou"}] if nome == self.erro_em else []
        return {nome: {"product": {"id": "gid://shopify/Product/99", "title": "X"}, "userErrors": erros}}

    def nomes(self):
        return [nome for nome, _ in self.chamadas]


def produto():
    return Produto(2, "CAM-001", "Camiseta", Decimal("59.90"), 30, "Camisetas", "")


def acao(tipo, mudancas=None):
    return Acao(
        "CAM-001", "Camiseta", tipo, "motivo",
        produto_id="gid://shopify/Product/1",
        variante_id="gid://shopify/ProductVariant/1",
        item_estoque_id="gid://shopify/InventoryItem/1",
        estoque_atual=25,
        mudancas=mudancas or {},
    )


def rodar(cliente, a, aplicar=True):
    return executar(cliente, [a], [produto()], LOCAL, aplicar)[0]


def test_entrada_de_criacao_tem_os_dados_certos():
    entrada = montar_entrada_criacao(produto(), LOCAL)
    variante = entrada["variants"][0]
    assert entrada["status"] == "DRAFT"
    assert variante["sku"] == "CAM-001"
    assert variante["price"] == "59.90"
    assert variante["inventoryQuantities"] == [{"locationId": LOCAL, "name": "available", "quantity": 30}]


def test_simulacao_nao_chama_a_loja():
    cliente = ClienteGravador()
    for a in (acao("criar"), acao("atualizar", {"preco": (Decimal("1"), Decimal("2"))})):
        assert rodar(cliente, a, aplicar=False).status == "simulado"
    assert cliente.chamadas == []


def test_simulacao_de_atualizacao_mostra_antes_e_depois():
    r = rodar(ClienteGravador(), acao("atualizar", {"preco": (Decimal("49.90"), Decimal("59.90"))}), aplicar=False)
    assert "49.90" in r.detalhe and "59.90" in r.detalhe


def test_aplicar_cria_o_produto():
    cliente = ClienteGravador()
    r = rodar(cliente, acao("criar"))
    assert cliente.nomes() == ["productSet"]
    assert r.status == "ok" and r.produto_id.endswith("Product/99")


def test_atualizar_so_o_preco_chama_so_o_preco():
    cliente = ClienteGravador()
    r = rodar(cliente, acao("atualizar", {"preco": (Decimal("49.90"), Decimal("59.90"))}))
    assert cliente.nomes() == ["productVariantsBulkUpdate"]
    assert cliente.chamadas[0][1]["variants"] == [{"id": "gid://shopify/ProductVariant/1", "price": "59.90"}]
    assert r.status == "ok"


def test_atualizar_estoque_usa_protecao_e_chave():
    cliente = ClienteGravador()
    rodar(cliente, acao("atualizar", {"estoque": (25, 30)}))
    nome, variaveis = cliente.chamadas[0]
    assert nome == "inventorySetQuantities"
    item = variaveis["input"]["quantities"][0]
    assert item["quantity"] == 30
    assert item["changeFromQuantity"] == 25
    assert item["locationId"] == LOCAL
    assert variaveis["chave"]


def test_atualizar_titulo_chama_product_update():
    cliente = ClienteGravador()
    rodar(cliente, acao("atualizar", {"titulo": ("Antigo", "Camiseta")}))
    assert cliente.nomes() == ["productUpdate"]
    assert cliente.chamadas[0][1]["product"]["id"] == "gid://shopify/Product/1"


def test_erro_no_meio_para_e_informa_o_que_ja_foi_feito():
    cliente = ClienteGravador(erro_em="inventorySetQuantities")
    r = rodar(cliente, acao("atualizar", {"preco": (Decimal("1"), Decimal("2")), "estoque": (25, 30)}))
    assert r.status == "erro"
    assert "preço" in r.detalhe
    assert cliente.nomes() == ["productVariantsBulkUpdate", "inventorySetQuantities"]


def test_erro_da_loja_na_criacao_vira_resultado_de_erro():
    r = rodar(ClienteGravador(erro_em="productSet"), acao("criar"))
    assert r.status == "erro" and "falhou" in r.detalhe


def test_manter_e_pular_nao_chamam_a_loja():
    cliente = ClienteGravador()
    resultados = executar(cliente, [acao("manter"), acao("pular")], [produto()], LOCAL, True)
    assert cliente.chamadas == []
    assert [r.status for r in resultados] == ["igual", "pulado"]


LOCAIS = [{"id": "1", "name": "Shop location"}, {"id": "2", "name": "My Custom Location"}]


def test_escolher_local_pelo_nome():
    assert escolher_local(LOCAIS, "Shop location")["id"] == "1"


def test_varios_locais_sem_nome_da_erro():
    with pytest.raises(ShopifyErro):
        escolher_local(LOCAIS, "")


def test_local_inexistente_da_erro():
    with pytest.raises(ShopifyErro):
        escolher_local(LOCAIS, "Outro")


def test_um_unico_local_nao_precisa_de_nome():
    assert escolher_local(LOCAIS[:1], "")["id"] == "1"