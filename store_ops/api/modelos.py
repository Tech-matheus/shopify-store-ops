from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class ProdutoOut(BaseModel):
    sku: Optional[str] = None
    titulo: str
    status: str
    preco: Decimal
    estoque: Optional[int] = None

class ProdutoVendidoOut(BaseModel):
    titulo: str
    sku: Optional[str] = None
    quantidade: int


class ResumoPedidosOut(BaseModel):
    dias: int
    total_pedidos: int
    pedidos_cancelados: int
    receita: Decimal
    moeda: Optional[str] = None
    ticket_medio: Decimal
    itens_vendidos: int
    mais_vendidos: list[ProdutoVendidoOut]