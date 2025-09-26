from pydantic import BaseModel, Field, condecimal
from typing import Optional


class ProductCreate(BaseModel):
    name: str
    slug: str = Field(min_length=1)
    price: condecimal(max_digits=10, decimal_places=2) = 0
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
