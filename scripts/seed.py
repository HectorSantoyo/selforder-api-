# scripts/seed.py
from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.slugify import slugify
from app.models.shop import Shop
from app.models.category import Category
from app.models.product import Product

TENANT_ID = "demo"
SHOP_NAME = "Demo Shop"
SHOP_SLUG = "demo-shop"
SHOP_TIMEZONE = "America/Mexico_City"

CATEGORIES: Sequence[str] = ["Bebidas", "Comidas"]

# Products por categoría (referenciamos por slug de category)
PRODUCTS: dict[str, Sequence[dict]] = {
    "bebidas": [
        {"name": "Coca 600", "slug": "Coca 600", "price": Decimal("25.00")},
        {"name": "Agua 600", "slug": "Agua 600", "price": Decimal("18.00")},
    ],
    "comidas": [
        {"name": "Torta de Jamón", "slug": "Torta de Jamón", "price": Decimal("45.00")},
        {"name": "Chilaquiles Verdes", "slug": "Chilaquiles Verdes", "price": Decimal("70.00")},
    ],
}


async def get_or_create_shop(db: AsyncSession) -> Shop:
    res = await db.execute(select(Shop).where(Shop.slug == SHOP_SLUG))
    shop = res.scalar_one_or_none()
    if shop:
        return shop

    shop = Shop(
        tenant_id=TENANT_ID,
        name=SHOP_NAME,
        slug=SHOP_SLUG,
        timezone=SHOP_TIMEZONE,
        address="",
    )
    db.add(shop)
    await db.flush()
    return shop


async def get_or_create_category(db: AsyncSession, *, shop_id: int, name: str) -> Category:
    s = slugify(name)
    res = await db.execute(select(Category).where(Category.shop_id == shop_id, Category.slug == s))
    cat = res.scalar_one_or_none()
    if cat:
        # mantén el nombre sincronizado si cambió
        if cat.name != name:
            cat.name = name
        return cat

    cat = Category(name=name, slug=s, shop_id=shop_id)
    db.add(cat)
    await db.flush()
    return cat


async def get_or_create_product(
    db: AsyncSession,
    *,
    shop_id: int,
    category_id: int | None,
    name: str,
    price: Decimal,
) -> Product:
    s = slugify(name)  # usamos name como base del slug
    res = await db.execute(select(Product).where(Product.shop_id == shop_id, Product.slug == s))
    prod = res.scalar_one_or_none()
    if prod:
        # sincroniza datos básicos
        updated = False
        if prod.name != name:
            prod.name = name
            updated = True
        if prod.price != price:
            prod.price = price
            updated = True
        if category_id is not None and prod.category_id != category_id:
            prod.category_id = category_id
            updated = True
        if updated:
            await db.flush()
        return prod

    prod = Product(
        name=name,
        slug=s,
        price=price,
        shop_id=shop_id,
        category_id=category_id,
    )
    db.add(prod)
    await db.flush()
    return prod


async def main() -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_pre_ping=True)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with SessionLocal() as db:
        shop = await get_or_create_shop(db)

        # crea/obtiene categorías
        cats: list[Category] = []
        for name in CATEGORIES:
            cat = await get_or_create_category(db, shop_id=shop.id, name=name)
            cats.append(cat)

        # índice por slug para usarlo al crear productos
        cat_by_slug = {c.slug: c for c in cats}

        # crea/actualiza productos por categoría (si la categoría existe)
        prods: list[Product] = []
        for cat_slug, items in PRODUCTS.items():
            cat = cat_by_slug.get(cat_slug)
            category_id = cat.id if cat else None
            for item in items:
                prod = await get_or_create_product(
                    db,
                    shop_id=shop.id,
                    category_id=category_id,
                    name=item["name"],
                    price=item["price"],
                )
                prods.append(prod)

        await db.commit()

        # imprime IDs reales para pruebas
        print(
            {
                "shop": {"id": shop.id, "name": shop.name, "slug": shop.slug},
                "categories": [{"id": c.id, "name": c.name, "slug": c.slug} for c in cats],
                "products": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "slug": p.slug,
                        "price": str(p.price),
                        "shop_id": p.shop_id,
                        "category_id": p.category_id,
                    }
                    for p in prods
                ],
            }
        )

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
