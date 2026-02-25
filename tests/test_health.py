from fastapi.testclient import TestClient


def test_health_endpoint_ok():
    # Import inside test so conftest env defaults are applied first.
    from webapp.api import app, APP_VERSION

    client = TestClient(app)
    resp = client.get("/health")

    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "ok"
    assert data["service"] == "epicservice"
    assert data["version"] == APP_VERSION
