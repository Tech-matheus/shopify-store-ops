import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

from store_ops import config
from store_ops.catalogo import escolher_local, listar_locais
from store_ops.importador.executor import executar
from store_ops.importador.leitor_csv import ler_csv
from store_ops.importador.planejador import planejar
from store_ops.importador.validacao import validar_planilha
from store_ops.shopify_client import ShopifyClient, ShopifyErro

parser = argparse.ArgumentParser(description="Importa produtos de uma planilha para a loja Shopify.")
parser.add_argument("planilha", nargs="?", default="dados/produtos_exemplo.csv")
parser.add_argument(
    "--aplicar",
    action="store_true",
    help="Envia de verdade para a loja. Sem esta opção, só simula.",
)
args = parser.parse_args()

print("MODO: APLICAR (vai alterar a loja)" if args.aplicar else "MODO: SIMULAÇÃO (nada será enviado)")

try:
    linhas = ler_csv(args.planilha)
except (OSError, ValueError) as erro:
    print("ERRO ao ler a planilha:", erro)
    sys.exit(1)

validacao = validar_planilha(linhas)
print(
    f"Produtos válidos: {len(validacao.validos)} | "
    f"linhas com erro: {len({e.linha for e in validacao.erros})} (ficam de fora)"
)

try:
    cliente = ShopifyClient()
    local = escolher_local(listar_locais(cliente), config.LOCAL_ESTOQUE)
    print("Local de estoque:", local["name"])
    acoes = planejar(cliente, validacao.validos, local["id"])
    resultados = executar(cliente, acoes, validacao.validos, local["id"], args.aplicar)
except (ShopifyErro, RuntimeError) as erro:
    print("ERRO:", erro)
    sys.exit(1)

print()
for r in resultados:
    print(f"  {r.status.upper():9} {r.acao:10} {r.sku:10} {r.detalhe}")

Path("relatorios").mkdir(exist_ok=True)
with open("relatorios/resultado_importacao.csv", "w", newline="", encoding="utf-8-sig") as arquivo:
    escritor = csv.writer(arquivo, delimiter=";")
    escritor.writerow(["sku", "acao", "status", "detalhe", "produto_id"])
    for r in resultados:
        escritor.writerow([r.sku, r.acao, r.status, r.detalhe, r.produto_id])

contagem = Counter(r.status for r in resultados)
print("\nResumo:", ", ".join(f"{status}: {total}" for status, total in sorted(contagem.items())))
print("Relatório salvo em relatorios/resultado_importacao.csv")