import pytest
import pytest_asyncio
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

# Usa la instancia real de tu app
from app.main import app

# Usa la dependencia oficial de DB (no importa cómo se llame tu sessionmaker interno)
from app.db.session import get_session


pytestmark = pytest.mark.skip(reason="Se pospone test de sorting hasta tener fixtures compartidas.")


# ----------------- Fixtures locales ----------------- #


@pytest_asyncio.fixture
async def client():
    """
    Cliente HTTP asíncrono contra la ASGI app (sin levantar servidor real).
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    """
    Sesión de DB usando la dependencia oficial de la app.
    """
    agen = get_session()
    s = await agen.__anext__()  # obtiene AsyncSession
    try:
        yield s
    finally:
        try:
            await agen.aclose()
        except Exception:
            pass


# ----------------- Datos de apoyo ----------------- #


async def _ensure_shop_and_category(session: AsyncSession) -> tuple[int, int]:
    """
    Asegura que existan shop_id=1 y category_id=1. Si no existen, los crea.
    Devuelve (shop_id, category_id).
    """
    from sqlalchemy import select
    from app.models.shop import Shop
    from app.models.category import Category

    # Shop
    res = await session.execute(select(Shop).where(Shop.id == 1))
    shop = res.scalar_one_or_none()
    if shop is None:
        shop = Shop(id=1, name="Test Shop")
        session.add(shop)
        await session.flush()

    # Category (en la misma shop 1)
    res = await session.execute(select(Category).where(Category.id == 1))
    cat = res.scalar_one_or_none()
    if cat is None:
        cat = Category(id=1, name="Test Cat", slug="test-cat", shop_id=1)
        session.add(cat)
        await session.flush()

    await session.commit()
    return shop.id, cat.id


async def _clear_products(session: AsyncSession, shop_id: int):
    """Borra productos del shop para dejar el test determinista."""
    from sqlalchemy import delete
    from app.models.product import Product

    await session.execute(delete(Product).where(Product.shop_id == shop_id))
    await session.commit()


async def _seed(session: AsyncSession):
    """
    Crea un set determinista de productos para shop=1 / category=1.
    """
    from app.models.product import Product

    shop_id, category_id = await _ensure_shop_and_category(session)
    await _clear_products(session, shop_id)

    data = [
        {
            "name": "Americano",
            "slug": "americano",
            "price": Decimal("30.00"),
            "shop_id": shop_id,
            "category_id": category_id,
        },
        {
            "name": "Latte",
            "slug": "latte",
            "price": Decimal("59.90"),
            "shop_id": shop_id,
            "category_id": category_id,
        },
        {
            "name": "Latte",
            "slug": "latte-2",
            "price": Decimal("45.00"),
            "shop_id": shop_id,
            "category_id": category_id,
        },
        {
            "name": "Capuccino",
            "slug": "capuccino",
            "price": Decimal("40.00"),
            "shop_id": shop_id,
            "category_id": category_id,
        },
    ]
    session.add_all([Product(**d) for d in data])
    await session.commit()


# ----------------- Tests ----------------- #


@pytest.mark.asyncio
async def test_sort_by_name_asc(client: AsyncClient, session: AsyncSession):
    await _seed(session)

    r = await client.get("/api/v1/products", params={"shop_id": 1, "sort": "name_asc"})
    assert r.status_code == 200, r.text
    names = [p["name"] for p in r.json()]
    assert names == sorted(names)  # alfabético asc


@pytest.mark.asyncio
async def test_sort_by_price_desc_stable(client: AsyncClient, session: AsyncSession):
    await _seed(session)

    r1 = await client.get("/api/v1/products", params={"shop_id": 1, "sort": "price_desc"})
    assert r1.status_code == 200, r1.text
    rows1 = r1.json()

    # Asegura orden por precio desc
    prices1 = [Decimal(str(p["price"])) for p in rows1]
    assert prices1 == sorted(prices1, reverse=True)

    # Misma request dos veces -> mismo orden (estabilidad con desempate por id)
    r2 = await client.get("/api/v1/products", params={"shop_id": 1, "sort": "price_desc"})
    assert r2.status_code == 200, r2.text
    assert r2.json() == rows1
