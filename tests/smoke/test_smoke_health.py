import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.anyio
async def test_health_ok():
    # Probar primero con prefijo /api/v1
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # intenta /api/v1/health y si 404, intenta /health
        r = await client.get("/api/v1/health")
        if r.status_code == 404:
            r = await client.get("/health")

        assert r.status_code == 200
        # acepta JSON o texto
        try:
            body = r.json()
            assert body.get("status", "").lower() in {"ok", "healthy", "up"}
        except ValueError:
            assert "ok" in r.text.lower()
