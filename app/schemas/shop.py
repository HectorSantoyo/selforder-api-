from pydantic import BaseModel


class ShopBase(BaseModel):
    name: str
    slug: str
    timezone: str = "America/Mexico_City"
    address: str = ""


class ShopCreate(ShopBase):
    tenant_id: str = "selforder-demo"  # MVP: default


class ShopOut(ShopBase):
    id: int
    tenant_id: str

    class Config:
        from_attributes = True  # permite devolver ORM objects
