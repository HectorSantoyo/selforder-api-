# tests/conftest.py
from typing import AsyncGenerator

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.db.session import get_session


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    # Prefijamos /api/v1 para que las rutas cortas funcionen en tests
    async with AsyncClient(app=app, base_url="http://test/api/v1") as ac:
        yield ac


@pytest_asyncio.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    agen = get_session()
    s = await agen.__anext__()
    try:
        yield s
    finally:
        try:
            await agen.aclose()
        except Exception:
            pass
