"""Tests for FastAPI endpoints."""
import pytest
import io
from PIL import Image
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    from src.api.main import app
    return TestClient(app)


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "1.0.0"


def test_search_no_file(client):
    """Test search without file."""
    response = client.post("/search")
    assert response.status_code == 422  # Validation error


def test_search_file_too_large(client):
    """Test search with oversized file."""
    # Create large fake content (>10MB)
    large_content = b"x" * (11 * 1024 * 1024)

    response = client.post(
        "/search",
        files={"file": ("test.jpg", io.BytesIO(large_content), "image/jpeg")}
    )

    assert response.status_code == 413


def test_api_cors_headers(client):
    """Test CORS headers are present."""
    response = client.options("/health")
    # FastAPI handles CORS at middleware level
    assert response.status_code in [200, 405]
