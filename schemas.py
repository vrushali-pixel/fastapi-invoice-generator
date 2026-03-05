from pydantic import BaseModel, Field
from typing import List

class ProductCreate(BaseModel):
    name: str
    current_price: float = Field(..., gt=0)
    stock_quantity: int = Field(..., ge=0)

class InvoiceItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)

class InvoiceCreate(BaseModel):
    customer_name: str
    items: List[InvoiceItemCreate]