from pydantic import BaseModel, field_validator
import re


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9\-_\s]", "", value)
    value = re.sub(r"\s+", "-", value)
    return value


class ShopBase(BaseModel):
    name: str
    slug: str
    timezone: str = "America/Mexico_City"
    address: str = ""

    @field_validator("slug")
    @classmethod
    def normalize_slug(cls, v: str) -> str:
        return _slugify(v)


class ShopCreate(ShopBase):
    tenant_id: str = "selforder-demo"  # MVP: default


class ShopOut(ShopBase):
    id: int
    tenant_id: str

    class Config:
        from_attributes = True  # permite devolver ORM objects
