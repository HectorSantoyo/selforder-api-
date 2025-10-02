# app/repositories/products.py
from typing import Sequence
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

# 🔧 CORRECCIÓN: antes estaba "from app.db.models import Product"
from app.models.product import Product


async def list_products_paginated(
    session: AsyncSession,
    *,
    limit: int,
    offset: int,
    shop_id: int | None = None,
) -> tuple[Sequence[Product], int]:
    """
    Devuelve (items, total) aplicando los mismos filtros a ambas consultas.
    """
    query = select(Product)
    count_query = select(func.count(Product.id))

    if shop_id is not None:
        query = query.where(Product.shop_id == shop_id)
        count_query = count_query.where(Product.shop_id == shop_id)

    total: int = int((await session.scalar(count_query)) or 0)

    query = query.offset(offset).limit(limit)
    result = await session.execute(query)
    items = result.scalars().all()

    return items, total
