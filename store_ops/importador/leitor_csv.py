import csv

COLUNAS_OBRIGATORIAS = {"sku", "titulo", "preco", "estoque"}


def ler_csv(caminho):
    """Lê o CSV (separado por ; ou ,) e devolve uma lista de dicionários."""
    with open(caminho, newline="", encoding="utf-8-sig") as arquivo:
        primeira_linha = arquivo.readline()
        arquivo.seek(0)
        delimitador = ";" if primeira_linha.count(";") > primeira_linha.count(",") else ","
        leitor = csv.DictReader(arquivo, delimiter=delimitador)

        colunas = {(c or "").strip().lower() for c in (leitor.fieldnames or [])}
        faltando = COLUNAS_OBRIGATORIAS - colunas
        if faltando:
            raise ValueError("Colunas faltando na planilha: " + ", ".join(sorted(faltando)))

        linhas = []
        for linha in leitor:
            linhas.append({(k or "").strip().lower(): v for k, v in linha.items()})
        return linhas