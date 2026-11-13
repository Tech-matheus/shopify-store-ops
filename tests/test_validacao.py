from decimal import Decimal

from store_ops.importador.validacao import converter_preco, validar_linha, validar_planilha


def linha_ok(**mudancas):
    dados = {
        "sku": "CAM-001",
        "titulo": "Camiseta",
        "preco": "59,90",
        "estoque": "10",
        "tipo": "Camisetas",
        "imagem_url": "",
    }
    dados.update(mudancas)
    return dados


def campos_com_erro(dados):
    _, erros = validar_linha(2, dados)
    return {e.campo for e in erros}


def test_linha_valida():
    produto, erros = validar_linha(2, linha_ok())
    assert erros == []
    assert produto.sku == "CAM-001"
    assert produto.preco == Decimal("59.90")
    assert produto.estoque == 10


def test_sku_e_normalizado_para_maiusculas():
    produto, _ = validar_linha(2, linha_ok(sku=" cam-001 "))
    assert produto.sku == "CAM-001"


def test_sku_vazio_ou_invalido():
    assert campos_com_erro(linha_ok(sku="")) == {"sku"}
    assert campos_com_erro(linha_ok(sku="ab")) == {"sku"}
    assert campos_com_erro(linha_ok(sku="CAM 001!")) == {"sku"}


def test_titulo_obrigatorio():
    assert campos_com_erro(linha_ok(titulo="")) == {"titulo"}


def test_precos_validos():
    assert converter_preco("19.90") == Decimal("19.90")
    assert converter_preco("19,90") == Decimal("19.90")
    assert converter_preco("R$ 1.299,90") == Decimal("1299.90")


def test_precos_invalidos():
    assert campos_com_erro(linha_ok(preco="")) == {"preco"}
    assert campos_com_erro(linha_ok(preco="abc")) == {"preco"}
    assert campos_com_erro(linha_ok(preco="0")) == {"preco"}
    assert campos_com_erro(linha_ok(preco="-10")) == {"preco"}
    assert campos_com_erro(linha_ok(preco="19,999")) == {"preco"}


def test_estoque_invalido():
    assert campos_com_erro(linha_ok(estoque="abc")) == {"estoque"}
    assert campos_com_erro(linha_ok(estoque="3.5")) == {"estoque"}
    assert campos_com_erro(linha_ok(estoque="-1")) == {"estoque"}
    assert campos_com_erro(linha_ok(estoque="")) == {"estoque"}


def test_estoque_zero_e_permitido():
    assert campos_com_erro(linha_ok(estoque="0")) == set()


def test_imagem_opcional_mas_precisa_de_https():
    assert campos_com_erro(linha_ok(imagem_url="")) == set()
    assert campos_com_erro(linha_ok(imagem_url="https://a.com/x.jpg")) == set()
    assert campos_com_erro(linha_ok(imagem_url="http://a.com/x.jpg")) == {"imagem_url"}


def test_varios_erros_na_mesma_linha():
    assert campos_com_erro(linha_ok(sku="", preco="abc", estoque="x")) == {"sku", "preco", "estoque"}


def test_sku_repetido_na_planilha():
    resultado = validar_planilha([linha_ok(), linha_ok(titulo="Outra")])
    assert len(resultado.validos) == 1
    assert len(resultado.erros) == 1
    assert resultado.erros[0].linha == 3
    assert "repetido" in resultado.erros[0].mensagem


def test_numeracao_comeca_na_linha_2():
    resultado = validar_planilha([linha_ok(sku="")])
    assert resultado.erros[0].linha == 2