import uuid

from risktrace.core.config import Settings
from risktrace.main import create_app


def test_demo_tenant_is_server_owned_and_not_an_api_query_parameter() -> None:
    assert Settings().demo_tenant_id == uuid.UUID(
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    )

    schema = create_app().openapi()
    for operation in schema["paths"]["/api/events"].values():
        parameter_names = {parameter["name"] for parameter in operation.get("parameters", [])}
        assert "tenant_id" not in parameter_names


def test_old_independent_agent_execution_routes_are_not_exposed() -> None:
    paths = create_app().openapi()["paths"]

    assert "/api/events/{event_id}/extract-opinions" not in paths
    assert "/api/events/{event_id}/generate-transmission" not in paths
    assert "/api/events/{event_id}/opinions" in paths
    assert "/api/events/{event_id}/transmission" in paths
