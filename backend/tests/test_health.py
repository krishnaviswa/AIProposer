"""Health + app-boot sanity."""

from __future__ import annotations

from app.services.ai import validate_startup_config as v_ai
from app.services.email import validate_startup_config as v_email
from app.services.payments import validate_startup_config as v_pay
from app.services.storage import validate_startup_config as v_store


async def test_health_open(client):
    r = await client.get("/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


async def test_root(client):
    r = await client.get("/")
    assert r.status_code == 200
    assert r.json()["health"] == "/v1/health"


def test_startup_validation_passes_with_default_mock_config():
    # Same calls the lifespan makes — must not raise on the mock/local defaults.
    v_ai()
    v_pay()
    v_store()
    v_email()
