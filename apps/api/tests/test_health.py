from fastapi.testclient import TestClient

from risktrace.core.health import DependencyCheck
from risktrace.main import app


class ReadyHealthService:
    async def readiness(self) -> dict[str, DependencyCheck]:
        return {
            "database": DependencyCheck(status="up", latency_ms=1.0),
            "redis": DependencyCheck(status="up", latency_ms=1.0),
            "object_storage": DependencyCheck(status="up", latency_ms=1.0),
        }


def test_liveness_does_not_claim_dependency_readiness() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "alive"
    assert response.json()["dependencies"] is None


def test_readiness_reports_real_dependency_result() -> None:
    with TestClient(app) as client:
        client.app.state.health_service = ReadyHealthService()
        response = client.get("/api/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert set(response.json()["dependencies"]) == {
        "database",
        "redis",
        "object_storage",
    }
