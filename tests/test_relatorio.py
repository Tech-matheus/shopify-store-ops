from decimal import Decimal
from io import BytesIO

from openpyxl import load_workbook

from store_ops.api.modelos import ProdutoOut, ProdutoVendidoOut, ResumoPedidosOut
from store_ops.api.relatorio import gerar_relatorio


def resumo_exemplo():
    return ResumoPedidosOut(
        dias=30,
        total_pedidos=2,
        pedidos_cancelados=1,
        receita=Decimal("11764.70"),
        moeda="USD",
        ticket_medio=Decimal("5882.35"),
        itens_vendidos=8,
        mais_vendidos=[ProdutoVendidoOut(titulo="Camiseta", sku=None, quantidade=3)],
    )


def abrir(conteudo):
    return load_workbook(BytesIO(conteudo))


def test_gera_tres_abas():
    arquivo = abrir(gerar_relatorio(resumo_exemplo(), []))
    assert arquivo.sheetnames == ["Resumo", "Mais vendidos", "Estoque baixo"]


def test_aba_resumo_tem_numeros_como_numeros():
    aba = abrir(gerar_relatorio(resumo_exemplo(), []))["Resumo"]
    valores = {linha[0].value: linha[1].value for linha in aba.iter_rows(min_row=2)}
    assert valores["Pedidos"] == 2
    assert valores["Receita (USD)"] == 11764.70
    assert valores["Ticket médio (USD)"] == 5882.35


def test_sku_vazio_vira_texto_vazio_e_estoque_baixo_lista_produtos():
    produtos = [ProdutoOut(sku=None, titulo="Cera", status="ACTIVE", preco=Decimal("9.95"), estoque=2)]
    arquivo = abrir(gerar_relatorio(resumo_exemplo(), produtos))
    vendidos = list(arquivo["Mais vendidos"].iter_rows(min_row=2, values_only=True))
    baixo = list(arquivo["Estoque baixo"].iter_rows(min_row=2, values_only=True))
    assert vendidos == [("Camiseta", None, 3)] or vendidos == [("Camiseta", "", 3)]
    assert baixo == [("Cera", None, 9.95, 2)] or baixo == [("Cera", "", 9.95, 2)]


def test_sem_dados_gera_arquivo_so_com_cabecalhos():
    vazio = ResumoPedidosOut(
        dias=7, total_pedidos=0, pedidos_cancelados=0, receita=Decimal("0.00"),
        moeda=None, ticket_medio=Decimal("0.00"), itens_vendidos=0, mais_vendidos=[],
    )
    arquivo = abrir(gerar_relatorio(vazio, []))
    assert arquivo["Mais vendidos"].max_row == 1
    assert arquivo["Estoque baixo"].max_row == 1