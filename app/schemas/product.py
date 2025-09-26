from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal


class ProductCreate(BaseModel):
    name: str
    slug: str = Field(min_length=1)
    # ⇩ mypy-friendly: sin condecimal(...)
    price: Decimal = Field(..., max_digits=10, decimal_places=2)
    shop_id: int
    category_id: Optional[int] = None


class ProductOut(BaseModel):
    id: int
    name: str
    slug: str
    price: float
    shop_id: int
    category_id: Optional[int] = None

    class Config:
        from_attributes = True
