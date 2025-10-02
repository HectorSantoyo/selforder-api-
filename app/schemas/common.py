from __future__ import annotations

from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class DeleteResult(BaseModel):
    id: int
    deleted: bool = True


class SingleResponse(BaseModel, Generic[T]):
    data: T


class MetaPagination(BaseModel):
    """Información estándar de paginación."""

    total: int = Field(..., ge=0, description="Total de elementos que cumplen los filtros")
    limit: int = Field(..., ge=1, description="Tamaño de página solicitado")
    offset: int = Field(..., ge=0, description="Desplazamiento inicial")


class ListResponse(BaseModel, Generic[T]):
    """Envelope para respuestas de listado: data + meta (paginación, filtros, etc.)."""

    data: List[T]
    meta: Dict[str, Any] = Field(default_factory=dict)


class ItemResponse(BaseModel, Generic[T]):
    """Envelope para respuestas de detalle (si luego lo usamos)."""

    data: T
    meta: Dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Modelo de error unificado (lo integraremos en el Paso 5)."""

    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
