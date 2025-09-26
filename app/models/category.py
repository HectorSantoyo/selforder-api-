from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import String, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    # Solo para tipado; no crea dependencias en tiempo de ejecución
    from app.models.shop import Shop


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), nullable=False)
    shop_id: Mapped[int] = mapped_column(
        ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # relaciones
    shop: Mapped["Shop"] = relationship(back_populates="categories")

    __table_args__ = (
        UniqueConstraint("shop_id", "slug", name="uq_categories_shop_slug"),
        Index("ix_categories_shop_id", "shop_id"),
    )
