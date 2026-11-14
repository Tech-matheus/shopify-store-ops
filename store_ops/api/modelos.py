from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class ProdutoOut(BaseModel):
    sku: Optional[str] = None
    titulo: str
    status: str
    preco: Decimal
    estoque: Optional[int] = None