import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

SKU_REGEX = re.compile(r"^[A-Z0-9][A-Z0-9-]{2,29}$")


@dataclass
class Produto:
    linha: int
    sku: str
    titulo: str
    preco: Decimal
    estoque: int
    tipo: str
    imagem_url: str


@dataclass
class ErroLinha:
    linha: int
    campo: str
    mensagem: str


@dataclass
class ResultadoValidacao:
    validos: list
    erros: list


def converter_preco(texto):
    """Aceita 19.90, 19,90 e 1.299,90. Devolve Decimal ou None."""
    limpo = texto.strip().replace("R$", "").replace(" ", "")
    if "," in limpo:
        limpo = limpo.replace(".", "").replace(",", ".")
    try:
        return Decimal(limpo)
    except InvalidOperation:
        return None


def validar_linha(numero, dados):
    """Valida uma linha da planilha. Devolve (Produto ou None, lista de erros)."""
    erros = []

    def erro(campo, mensagem):
        erros.append(ErroLinha(numero, campo, mensagem))

    sku = (dados.get("sku") or "").strip().upper()
    if not sku:
        erro("sku", "SKU obrigatório")
    elif not SKU_REGEX.match(sku):
        erro("sku", "SKU inválido: use de 3 a 30 letras, números ou hífen")

    titulo = (dados.get("titulo") or "").strip()
    if not titulo:
        erro("titulo", "Título obrigatório")
    elif len(titulo) > 255:
        erro("titulo", "Título com mais de 255 caracteres")

    preco = converter_preco(dados.get("preco") or "")
    if preco is None:
        erro("preco", "Preço obrigatório ou inválido")
    elif preco <= 0:
        erro("preco", "Preço deve ser maior que zero")
    elif preco != preco.quantize(Decimal("0.01")):
        erro("preco", "Preço com mais de 2 casas decimais")

    estoque = None
    try:
        estoque = int((dados.get("estoque") or "").strip())
    except ValueError:
        erro("estoque", "Estoque deve ser um número inteiro")
    else:
        if estoque < 0:
            erro("estoque", "Estoque não pode ser negativo")

    imagem_url = (dados.get("imagem_url") or "").strip()
    if imagem_url and not imagem_url.startswith("https://"):
        erro("imagem_url", "A imagem deve ser um link que começa com https://")

    if erros:
        return None, erros

    produto = Produto(
        linha=numero,
        sku=sku,
        titulo=titulo,
        preco=preco,
        estoque=estoque,
        tipo=(dados.get("tipo") or "").strip(),
        imagem_url=imagem_url,
    )
    return produto, []


def validar_planilha(linhas):
    """Valida todas as linhas e detecta SKU repetido. A linha 1 é o cabeçalho."""
    validos = []
    erros = []
    vistos = {}

    for indice, dados in enumerate(linhas, start=2):
        produto, erros_linha = validar_linha(indice, dados)
        if produto is not None and produto.sku in vistos:
            erros_linha.append(
                ErroLinha(
                    indice,
                    "sku",
                    f"SKU repetido (já usado na linha {vistos[produto.sku]})",
                )
            )
            produto = None

        if produto is not None:
            vistos[produto.sku] = indice
            validos.append(produto)
        erros.extend(erros_linha)

    return ResultadoValidacao(validos=validos, erros=erros)