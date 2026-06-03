import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestSmokeEndpoints:
    def test_health_check(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy", "service": "marketforge-api"}

    def test_readiness_check(self):
        response = client.get("/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ready"}

    def test_openapi_schema(self):
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "paths" in schema
        assert "/health" in schema["paths"]
        assert "/ready" in schema["paths"]
        assert "/auth/register" in schema["paths"]
        assert "/auth/login" in schema["paths"]
        assert "/orders" in schema["paths"]
        assert "/vendor/orders" in schema["paths"]

    def test_docs_endpoint(self):
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_redoc_endpoint(self):
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]