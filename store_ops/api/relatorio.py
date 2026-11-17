from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font

FORMATO_DINHEIRO = "#,##0.00"


def _cabecalho(aba, colunas):
    aba.append(colunas)
    for celula in aba[1]:
        celula.font = Font(bold=True)


def _ajustar_larguras(aba):
    for coluna in aba.columns:
        maior = max(len(str(c.value)) if c.value is not None else 0 for c in coluna)
        aba.column_dimensions[coluna[0].column_letter].width = min(maior + 2, 50)


def gerar_relatorio(resumo, produtos_baixos):
    """Monta o Excel em memória e devolve os bytes do arquivo .xlsx."""
    arquivo = Workbook()

    aba = arquivo.active
    aba.title = "Resumo"
    _cabecalho(aba, ["Indicador", "Valor"])
    aba.append(["Período (dias)", resumo.dias])
    aba.append(["Pedidos", resumo.total_pedidos])
    aba.append(["Pedidos cancelados", resumo.pedidos_cancelados])
    aba.append([f"Receita ({resumo.moeda or '-'})", float(resumo.receita)])
    aba.append([f"Ticket médio ({resumo.moeda or '-'})", float(resumo.ticket_medio)])
    aba.append(["Itens vendidos", resumo.itens_vendidos])
    aba["B5"].number_format = FORMATO_DINHEIRO
    aba["B6"].number_format = FORMATO_DINHEIRO
    _ajustar_larguras(aba)

    aba = arquivo.create_sheet("Mais vendidos")
    _cabecalho(aba, ["Produto", "SKU", "Quantidade"])
    for item in resumo.mais_vendidos:
        aba.append([item.titulo, item.sku or "", item.quantidade])
    _ajustar_larguras(aba)

    aba = arquivo.create_sheet("Estoque baixo")
    _cabecalho(aba, ["Produto", "SKU", "Preço", "Estoque"])
    for produto in produtos_baixos:
        aba.append([produto.titulo, produto.sku or "", float(produto.preco), produto.estoque])
    for linha in aba.iter_rows(min_row=2, min_col=3, max_col=3):
        linha[0].number_format = FORMATO_DINHEIRO
    _ajustar_larguras(aba)

    saida = BytesIO()
    arquivo.save(saida)
    return saida.getvalue()