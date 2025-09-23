import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_create_and_list_shops():
    # Transporte ASGI recomendado (evita el 'app=' deprecado)
    transport = ASGITransport(app=app)

    # Slug único por corrida para no chocar con datos existentes
    unique_slug = f"cafeteria-central-{uuid.uuid4().hex[:8]}"

    payload = {
        "tenant_id": "selforder-demo",
        "name": "Cafetería Central",
        "slug": unique_slug,
        "timezone": "America/Mexico_City",
        "address": "Centro",
    }

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/shops", json=payload)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["slug"] == unique_slug

        resp2 = await client.get("/api/v1/shops")
        assert resp2.status_code == 200
        items = resp2.json()
        assert any(s["slug"] == unique_slug for s in items)
