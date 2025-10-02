# ruff: noqa: E402

# --- ensure repo root on sys.path for "from app import ..." ---
import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
# ----------------------------------------------------------------

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.anyio
async def test_health_ok():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/v1/health")
        if r.status_code == 404:
            r = await client.get("/health")
        assert r.status_code == 200
        try:
            body = r.json()
            assert body.get("status", "").lower() in {"ok", "healthy", "up"}
        except ValueError:
            assert "ok" in r.text.lower()
