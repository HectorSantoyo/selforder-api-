# scripts/seed.py
from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Optional, Dict, Any, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.slugify import slugify
from app.models.shop import Shop
from app.models.category import Category
from app.models.product import Product


# --- Datos demo --------------------------------------------------------------

DEMO_TENANT = "demo"
DEMO_SHOP = {
    "name": "Demo Shop",
    "slug": "demo-shop",
    "timezone": "America/Mexico_City",
    "address": "",
}

CATEGORIES: List[Dict[str, str]] = [
    {"name": "Bebidas", "slug": "bebidas"},
    {"name": "Comidas", "slug": "comidas"},
]

# Productos por categoría (precios en float; se convertirán a Decimal)
PRODUCTS: Dict[str, List[Dict[str, Any]]] = {
    "bebidas": [
        {"name": "Coca 600", "slug": "Coca 600", "price": 25.0},
        {"name": "Agua 600", "slug": "Agua 600", "price": 18.0},
    ],
    "comidas": [
        {"name": "Torta de Jamón", "slug": "Torta de Jamón", "price": 45.0},
        {"name": "Chilaquiles Verdes", "slug": "Chilaquiles Verdes", "price": 70.0},
    ],
}


# --- Helpers get-or-create ---------------------------------------------------


async def get_or_create_shop(
    db: AsyncSession, *, tenant_id: str, name: str, slug: str, timezone: str, address: str
) -> Shop:
    s = slugify(slug)
    result = await db.execute(select(Shop).where(Shop.tenant_id == tenant_id, Shop.slug == s))
    shop = result.scalars().first()
    if shop:
        # Update mínimos si cambió algo
        changed = False
        if shop.name != name:
            shop.name = name
            changed = True
        if shop.timezone != timezone:
            shop.timezone = timezone
            changed = True
        if shop.address != address:
            shop.address = address
            changed = True
        if changed:
            await db.flush()
        return shop

    shop = Shop(
        tenant_id=tenant_id,
        name=name,
        slug=s,
        timezone=timezone,
        address=address,
    )
    db.add(shop)
    await db.flush()
    return shop


async def get_or_create_category(
    db: AsyncSession, *, shop_id: int, name: str, slug: str
) -> Category:
    s = slugify(slug)
    result = await db.execute(
        select(Category).where(Category.shop_id == shop_id, Category.slug == s)
    )
    category = result.scalars().first()
    if category:
        if category.name != name:
            category.name = name
            await db.flush()
        return category

    category = Category(name=name, slug=s, shop_id=shop_id)
    db.add(category)
    await db.flush()
    return category


async def get_or_create_product(
    db: AsyncSession,
    *,
    shop_id: int,
    category_id: Optional[int],
    name: str,
    price: float,
) -> Product:
    s = slugify(name)  # si quisieras usar un slug distinto, cámbialo por el campo correspondiente
    result = await db.execute(select(Product).where(Product.shop_id == shop_id, Product.slug == s))
    product = result.scalars().first()

    # Convertimos el float de entrada a Decimal (mypy-friendly y preciso para dinero)
    new_price: Decimal = Decimal(str(price))

    if product:
        changed = False
        if product.name != name:
            product.name = name
            changed = True
        if product.price != new_price:
            product.price = new_price
            changed = True
        if product.category_id != category_id:
            product.category_id = category_id
            changed = True
        if changed:
            await db.flush()
        return product

    product = Product(
        name=name,
        slug=s,
        price=new_price,
        shop_id=shop_id,
        category_id=category_id,
    )
    db.add(product)
    await db.flush()
    return product


# --- Main --------------------------------------------------------------------


async def main() -> None:
    # Engine y sesión asíncronos
    engine = create_async_engine(settings.DATABASE_URL, future=True)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as db:
        # 1) Shop
        shop = await get_or_create_shop(
            db,
            tenant_id=DEMO_TENANT,
            name=DEMO_SHOP["name"],
            slug=DEMO_SHOP["slug"],
            timezone=DEMO_SHOP["timezone"],
            address=DEMO_SHOP["address"],
        )

        # 2) Categorías
        created_categories: List[Category] = []
        for cat_def in CATEGORIES:
            category = await get_or_create_category(
                db,
                shop_id=shop.id,
                name=cat_def["name"],
                slug=cat_def["slug"],
            )
            created_categories.append(category)

        # Índice slug->objeto para mapear productos
        categories_by_slug: Dict[str, Category] = {c.slug: c for c in created_categories}

        # 3) Productos
        for cat_slug, items in PRODUCTS.items():
            category_obj: Optional[Category] = categories_by_slug.get(cat_slug)
            category_id: int | None = category_obj.id if category_obj else None
            for item in items:
                await get_or_create_product(
                    db,
                    shop_id=shop.id,
                    category_id=category_id,
                    name=item["name"],
                    price=float(item["price"]),
                )

        await db.commit()

        # 4) Resumen
        summary = {
            "shop": {"id": shop.id, "name": shop.name, "slug": shop.slug},
            "categories": [
                {"id": c.id, "name": c.name, "slug": c.slug} for c in created_categories
            ],
        }
        print(summary)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
