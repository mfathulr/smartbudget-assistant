"""Lightweight smoke tests for health and public config endpoints."""

from main import app


def test_health_endpoint():
    client = app.test_client()
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["service"] == "SmartBudget-Assistant"
    assert "timestamp" in data


def test_public_config_endpoint():
    client = app.test_client()
    resp = client.get("/api/public-config")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "recaptcha_site_key" in data
    assert "recaptcha_enabled" in data
    assert "recaptcha_server_enforced" in data


def test_route_registry_contains_core_endpoints():
    endpoint_names = {rule.endpoint for rule in app.url_map.iter_rules()}
    assert "health_check" in endpoint_names
    assert "public_config" in endpoint_names
    assert "chat_api" in endpoint_names
    # memory blueprint should register at least one route
    assert any(name.startswith("memory.") for name in endpoint_names)
