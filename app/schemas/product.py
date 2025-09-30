# app/schemas/product.py
from enum import Enum
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator


# ---------- Create ----------
class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str | None = Field(default=None, min_length=1, max_length=220)
    price: Decimal = Field(ge=0)
    shop_id: int
    category_id: int | None = None
    description: str | None = Field(default=None, max_length=2000)
    is_active: bool = True

    @field_validator("price")
    @classmethod
    def price_two_decimals(cls, v: Decimal) -> Decimal:
        # Normaliza a 2 decimales de forma estable
        return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# ---------- Read (usar este en responses) ----------
class ProductRead(BaseModel):
    id: int
    shop_id: int
    category_id: int | None = None
    name: str
    slug: str
    price: Decimal
    description: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# (Opcional) Si conservas ProductOut, hazlo coherente con Read:
class ProductOut(BaseModel):
    id: int
    name: str
    slug: str
    price: Decimal
    shop_id: int
    category_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


# ---------- Listado ----------
class ProductSort(str, Enum):
    name_asc = "name_asc"
    name_desc = "name_desc"
    price_asc = "price_asc"
    price_desc = "price_desc"


class ProductListResponse(BaseModel):
    items: list[ProductRead]
    total: int = Field(ge=0)
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


# ---------- Update (PUT/PATCH) ----------
class ProductBaseUpdate(BaseModel):
    """
    Campos potencialmente actualizables; heredados en PUT/PATCH.
    """

    shop_id: int  # requerido para validar pertenencia (contexto multi-tenant)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    slug: str | None = Field(default=None, min_length=1, max_length=220)
    description: str | None = Field(default=None, max_length=2000)
    price: Decimal | None = Field(default=None, ge=0)
    category_id: int | None = None
    is_active: bool | None = None

    @field_validator("slug")
    @classmethod
    def normalize_slug(cls, v: str | None) -> str | None:
        if v is None:
            return v
        # Normalización ligera; la normalización completa se hace con utils.slugify en el servicio/DAO
        return v.strip().lower().replace(" ", "-")

    @field_validator("price")
    @classmethod
    def price_two_decimals_opt(cls, v: Decimal | None) -> Decimal | None:
        if v is None:
            return v
        return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class ProductUpdate(ProductBaseUpdate):
    """
    PUT = Reemplazo completo (salvo slug que puede omitirse para recalcularse desde name).
    """

    name: str
    price: Decimal
    is_active: bool


class ProductUpdatePartial(ProductBaseUpdate):
    """
    PATCH = Parcial: todos opcionales (salvo shop_id).
    """

    pass
