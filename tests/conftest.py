import pytest


@pytest.fixture(autouse=True)
async def _db_cleanup():
    # Limpia entre tests para evitar fugas
    from app.db.session import engine

    async with engine.begin() as conn:
        # Orden importa por FKs: products -> categories -> shops
        await conn.exec_driver_sql("TRUNCATE TABLE products RESTART IDENTITY CASCADE;")
        await conn.exec_driver_sql("TRUNCATE TABLE categories RESTART IDENTITY CASCADE;")
        await conn.exec_driver_sql("TRUNCATE TABLE shops RESTART IDENTITY CASCADE;")
