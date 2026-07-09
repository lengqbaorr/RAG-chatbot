from app.api.dependencies import get_health_service
from app.main import app
from app.services.health import HealthStatus
from fastapi.testclient import TestClient


class FakeHealthService:
    def check(self) -> HealthStatus:
        return HealthStatus(
            app="ok",
            embedding_service="ok",
            vector_store="ok",
            llm_provider="gemini",
            collection="test_collection",
            collection_count=3,
            ready=True,
        )


def test_health_check() -> None:
    app.dependency_overrides[get_health_service] = lambda: FakeHealthService()
    client = TestClient(app)

    response = client.get("/health")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["app"] == "ok"
    assert response.json()["ready"] is True


def test_legacy_health_prefix_still_works() -> None:
    app.dependency_overrides[get_health_service] = lambda: FakeHealthService()
    client = TestClient(app)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["collection_count"] == 3
    app.dependency_overrides.clear()
