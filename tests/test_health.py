import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.anyio
async def test_health_ok():
    # Usamos ASGITransport para no levantar servidor real
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test/api/v1") as client:
        r = await client.get("/health")
        assert r.status_code == 200
        # acepta JSON o texto, según tu implementación
        # si es JSON con {"status":"ok"}:
        try:
            body = r.json()
            assert body.get("status", "").lower() in {"ok", "healthy", "up"}
        except ValueError:
            # o si responde texto plano:
            assert "ok" in r.text.lower()
