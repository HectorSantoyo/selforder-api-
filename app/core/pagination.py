# app/core/pagination.py
from typing import Annotated
from fastapi import Query
from pydantic import BaseModel, Field

# Defaults temporales (en Día 7 los moveremos a Settings)
PAGE_SIZE_DEFAULT: int = 20
PAGE_SIZE_MAX: int = 100


class PaginationParams(BaseModel):
    """DTO interno para transportar limit/offset ya validados."""

    limit: int = Field(PAGE_SIZE_DEFAULT, ge=1, le=PAGE_SIZE_MAX)
    offset: int = Field(0, ge=0)


# 🔧 Importante: en Annotated NO se define default dentro de Query(...)
#    El default se pone en el valor por defecto del parámetro (con '=')
LimitQuery = Annotated[int, Query(ge=1, le=PAGE_SIZE_MAX, description="Tamaño de página (1..100)")]
OffsetQuery = Annotated[int, Query(ge=0, description="Desplazamiento inicial (>=0)")]


def pagination_params(
    limit: LimitQuery = PAGE_SIZE_DEFAULT,
    offset: OffsetQuery = 0,
) -> PaginationParams:
    """Construye el objeto PaginationParams desde query params validados."""
    return PaginationParams(limit=limit, offset=offset)
