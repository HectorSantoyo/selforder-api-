import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


# Helpers: crea N productos simples
async def _create_products(session: AsyncSession, n: int, shop_id: int | None = None):
    from app.db.models import Product  # importa local para evitar ciclos

    products = [
        Product(name=f"Prod {i}", slug=f"prod-{i}", price=100 + i, shop_id=shop_id)
        for i in range(n)
    ]
    session.add_all(products)
    await session.commit()


@pytest.mark.asyncio
async def test_products_pagination_basic(client: AsyncClient, session: AsyncSession):
    await _create_products(session, 15)

    # limit default (20) debería devolver todos (<=20)
    r = await client.get("/products")
    assert r.status_code == 200
    assert len(r.json()) == 15
    assert r.headers.get("X-Total-Count") == "15"
    assert r.headers.get("X-Limit") == "20"
    assert r.headers.get("X-Offset") == "0"


@pytest.mark.asyncio
async def test_products_pagination_limit_and_offset(client: AsyncClient, session: AsyncSession):
    await _create_products(session, 15)

    r1 = await client.get("/products", params={"limit": 5, "offset": 0})
    assert r1.status_code == 200
    assert len(r1.json()) == 5
    assert r1.headers["X-Total-Count"] == "15"

    r2 = await client.get("/products", params={"limit": 5, "offset": 5})
    assert r2.status_code == 200
    assert len(r2.json()) == 5

    r3 = await client.get("/products", params={"limit": 5, "offset": 10})
    assert r3.status_code == 200
    assert len(r3.json()) == 5

    # Offset fuera de rango → lista vacía (pero con total correcto)
    r4 = await client.get("/products", params={"limit": 5, "offset": 20})
    assert r4.status_code == 200
    assert len(r4.json()) == 0
    assert r4.headers["X-Total-Count"] == "15"


@pytest.mark.asyncio
async def test_products_pagination_validation(client: AsyncClient):
    # limit > 100 → 422 por validación Query
    r = await client.get("/products", params={"limit": 999})
    assert r.status_code == 422

    # offset negativo → 422
    r = await client.get("/products", params={"offset": -1})
    assert r.status_code == 422
