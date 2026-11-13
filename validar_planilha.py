import csv
import sys
from pathlib import Path

from store_ops.importador.leitor_csv import ler_csv
from store_ops.importador.validacao import validar_planilha

caminho = sys.argv[1] if len(sys.argv) > 1 else "dados/produtos_exemplo.csv"

try:
    linhas = ler_csv(caminho)
except (OSError, ValueError) as erro:
    print("ERRO ao ler a planilha:", erro)
    sys.exit(1)

resultado = validar_planilha(linhas)
linhas_com_erro = {e.linha for e in resultado.erros}

print(f"Linhas lidas: {len(linhas)}")
print(f"Produtos válidos: {len(resultado.validos)}")
print(f"Linhas com erro: {len(linhas_com_erro)}")

for e in resultado.erros:
    print(f"  linha {e.linha} | {e.campo}: {e.mensagem}")

Path("relatorios").mkdir(exist_ok=True)
with open("relatorios/validacao.csv", "w", newline="", encoding="utf-8-sig") as arquivo:
    escritor = csv.writer(arquivo, delimiter=";")
    escritor.writerow(["linha", "campo", "mensagem"])
    for e in resultado.erros:
        escritor.writerow([e.linha, e.campo, e.mensagem])
print("Relatório salvo em relatorios/validacao.csv")