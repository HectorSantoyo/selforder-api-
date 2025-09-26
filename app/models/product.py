from __future__ import annotations
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, ForeignKey, UniqueConstraint, Index, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from decimal import Decimal

if TYPE_CHECKING:
    from app.models.shop import Shop
    from app.models.category import Category


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(160), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    shop_id: Mapped[int] = mapped_column(
        ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True
    )

    shop: Mapped["Shop"] = relationship(back_populates="products")
    category: Mapped["Category"] = relationship(back_populates="products")

    __table_args__ = (
        UniqueConstraint("shop_id", "slug", name="uq_products_shop_slug"),
        Index("ix_products_shop_id", "shop_id"),
        Index("ix_products_category_id", "category_id"),
    )
