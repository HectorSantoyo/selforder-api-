# tests/conftest.py
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings


@pytest.fixture(autouse=True)
async def _db_cleanup():
    """
    Limpia tablas entre tests usando un engine NUEVO (mismo loop que pytest-asyncio).
    Evita el error 'Future attached to a different loop'.
    """
    engine = create_async_engine(settings.DATABASE_URL, future=True, pool_pre_ping=True)
    try:
        async with engine.begin() as conn:
            # Orden por FKs: products -> categories -> shops
            await conn.execute(text("TRUNCATE TABLE products RESTART IDENTITY CASCADE;"))
            await conn.execute(text("TRUNCATE TABLE categories RESTART IDENTITY CASCADE;"))
            await conn.execute(text("TRUNCATE TABLE shops RESTART IDENTITY CASCADE;"))
    finally:
        await engine.dispose()
