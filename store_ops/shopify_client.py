import time

import requests

from store_ops import config


class ShopifyErro(Exception):
    pass


class ShopifyClient:
    def __init__(self):
        config.validar()
        self._token = None
        self._expira_em = 0.0

    def _base(self):
        return f"https://{config.SHOP}.myshopify.com"

    def _obter_token(self):
        # Reaproveita o token até 5 minutos antes de vencer (ele dura 24 h).
        if self._token and time.time() < self._expira_em - 300:
            return self._token

        resposta = requests.post(
            f"{self._base()}/admin/oauth/access_token",
            data={
                "grant_type": "client_credentials",
                "client_id": config.CLIENT_ID,
                "client_secret": config.CLIENT_SECRET,
            },
            timeout=15,
        )
        if resposta.status_code != 200:
            raise ShopifyErro(
                f"Falha ao obter o token ({resposta.status_code}): {resposta.text[:300]}"
            )

        dados = resposta.json()
        self._token = dados["access_token"]
        self._expira_em = time.time() + dados.get("expires_in", 86399)
        return self._token

    def graphql(self, consulta, variaveis=None):
        resposta = requests.post(
            f"{self._base()}/admin/api/{config.API_VERSION}/graphql.json",
            json={"query": consulta, "variables": variaveis or {}},
            headers={
                "X-Shopify-Access-Token": self._obter_token(),
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        if resposta.status_code != 200:
            raise ShopifyErro(
                f"Erro HTTP {resposta.status_code}: {resposta.text[:300]}"
            )

        corpo = resposta.json()
        if "errors" in corpo:
            raise ShopifyErro(f"Erro GraphQL: {str(corpo['errors'])[:500]}")
        return corpo["data"]