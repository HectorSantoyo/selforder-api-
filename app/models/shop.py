from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin
from sqlalchemy.orm import relationship


class Shop(TimestampMixin, Base):
    __tablename__ = "shops"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(50), index=True)
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    timezone: Mapped[str] = mapped_column(String(50), default="America/Mexico_City")
    address: Mapped[str] = mapped_column(String(255), default="")

    categories = relationship("Category", back_populates="shop", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="shop", cascade="all, delete-orphan")
