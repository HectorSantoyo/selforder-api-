import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


# Helpers
async def _ensure_shop_and_category(session: AsyncSession) -> tuple[int, int]:
    from sqlalchemy import select
    from app.models.shop import Shop
    from app.models.category import Category

    # shop 1
    shop = (await session.execute(select(Shop).where(Shop.id == 1))).scalar_one_or_none()
    if shop is None:
        shop = Shop(id=1, name="Test Shop")
        session.add(shop)
        await session.flush()

    # category 1
    cat = (await session.execute(select(Category).where(Category.id == 1))).scalar_one_or_none()
    if cat is None:
        cat = Category(id=1, name="Test Cat", slug="test-cat", shop_id=1)
        session.add(cat)
        await session.flush()

    await session.commit()
    return 1, 1


async def _clear_products(session: AsyncSession, shop_id: int):
    from sqlalchemy import delete
    from app.models.product import Product

    await session.execute(delete(Product).where(Product.shop_id == shop_id))
    await session.commit()


async def _create_products(session: AsyncSession, n: int, shop_id: int | None = None):
    from app.models.product import Product

    sid, cid = await _ensure_shop_and_category(session)
    if shop_id is None:
        shop_id = sid
    await _clear_products(session, shop_id)
    items = [
        Product(name=f"Prod {i}", slug=f"prod-{i}", price=100 + i, shop_id=shop_id, category_id=cid)
        for i in range(n)
    ]
    session.add_all(items)
    await session.commit()


@pytest.mark.asyncio
async def test_products_pagination_basic(client: AsyncClient, session: AsyncSession):
    await _create_products(session, 15)
    r = await client.get("/products", params={"shop_id": 1})
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body.get("data"), list)
    assert len(body["data"]) == 15  # default limit=20, hay 15 creados
    assert r.headers.get("X-Total-Count") == "15"
    assert r.headers.get("X-Limit") == "20"
    assert r.headers.get("X-Offset") == "0"


@pytest.mark.asyncio
async def test_products_pagination_limit_and_offset(client: AsyncClient, session: AsyncSession):
    await _create_products(session, 15)

    r1 = await client.get("/products", params={"shop_id": 1, "limit": 5, "offset": 0})
    assert r1.status_code == 200
    assert len(r1.json()["data"]) == 5
    assert r1.headers["X-Total-Count"] == "15"

    r2 = await client.get("/products", params={"shop_id": 1, "limit": 5, "offset": 5})
    assert r2.status_code == 200
    assert len(r2.json()["data"]) == 5

    r3 = await client.get("/products", params={"shop_id": 1, "limit": 5, "offset": 10})
    assert r3.status_code == 200
    assert len(r3.json()["data"]) == 5

    # Offset fuera de rango → lista vacía (pero con total correcto)
    r4 = await client.get("/products", params={"shop_id": 1, "limit": 5, "offset": 20})
    assert r4.status_code == 200
    assert len(r4.json()["data"]) == 0
    assert r4.headers["X-Total-Count"] == "15"


@pytest.mark.asyncio
async def test_products_pagination_validation(client: AsyncClient):
    # limit > 100 → 422 por validación Query
    r = await client.get("/products", params={"shop_id": 1, "limit": 999})
    assert r.status_code == 422

    # offset negativo → 422
    r = await client.get("/products", params={"shop_id": 1, "offset": -1})
    assert r.status_code == 422
