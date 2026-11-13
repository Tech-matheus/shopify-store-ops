import os

from dotenv import load_dotenv

load_dotenv()

SHOP = os.getenv("SHOPIFY_SHOP", "").strip()
CLIENT_ID = os.getenv("SHOPIFY_CLIENT_ID", "").strip()
CLIENT_SECRET = os.getenv("SHOPIFY_CLIENT_SECRET", "").strip()
LOCAL_ESTOQUE = os.getenv("SHOPIFY_LOCAL_ESTOQUE", "").strip()
API_VERSION = "2026-10"


def validar():
    obrigatorios = {
        "SHOPIFY_SHOP": SHOP,
        "SHOPIFY_CLIENT_ID": CLIENT_ID,
        "SHOPIFY_CLIENT_SECRET": CLIENT_SECRET,
    }
    faltando = [nome for nome, valor in obrigatorios.items() if not valor]
    if faltando:
        raise RuntimeError("Faltando no .env: " + ", ".join(faltando))