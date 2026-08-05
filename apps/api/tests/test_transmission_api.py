from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException

from risktrace.api.routes import transmission


def test_build_agent_requires_llm_api_key_before_loading_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "risktrace.core.config.get_settings",
        lambda: SimpleNamespace(llm_api_key=""),
    )
    monkeypatch.setattr(
        transmission,
        "_load_agent_class",
        lambda: pytest.fail("should not try to load the agent runtime without an API key"),
    )

    with pytest.raises(HTTPException) as excinfo:
        transmission._build_agent(object())  # type: ignore[arg-type]

    assert excinfo.value.status_code == 503
    assert "RISKTRACE_LLM_API_KEY" in excinfo.value.detail


def test_build_agent_rejects_placeholder_llm_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "risktrace.core.config.get_settings",
        lambda: SimpleNamespace(llm_api_key="sk-your-key-here"),
    )
    monkeypatch.setattr(
        transmission,
        "_load_agent_class",
        lambda: pytest.fail("placeholder key should not instantiate the agent"),
    )

    with pytest.raises(HTTPException) as excinfo:
        transmission._build_agent(object())  # type: ignore[arg-type]

    assert excinfo.value.status_code == 503
    assert "真实的 RISKTRACE_LLM_API_KEY" in excinfo.value.detail


def test_build_agent_instantiates_transmission_agent_with_existing_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DummyAgent:
        def __init__(self, session: object) -> None:
            self.session = session

    session = object()
    monkeypatch.setattr(
        "risktrace.core.config.get_settings",
        lambda: SimpleNamespace(llm_api_key="test-key"),
    )
    monkeypatch.setattr(transmission, "_load_agent_class", lambda: DummyAgent)

    agent = transmission._build_agent(session)  # type: ignore[arg-type]

    assert isinstance(agent, DummyAgent)
    assert agent.session is session


@pytest.mark.asyncio
async def test_generate_transmission_maps_llm_unavailable_to_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DummyDb:
        async def scalar(self, _query: object) -> object:
            return object()

    class DummyAgent:
        async def generate_for_event(self, _event_id: UUID) -> list[object]:
            raise RuntimeError("LLM 请求失败：All connection attempts failed")

    monkeypatch.setattr(transmission, "_build_agent", lambda _db: DummyAgent())

    with pytest.raises(HTTPException) as excinfo:
        await transmission.generate_transmission(
            UUID("4a897de9-f136-4e25-bc87-06c2920473c8"),
            UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            DummyDb(),  # type: ignore[arg-type]
        )

    assert excinfo.value.status_code == 503
    assert "当前 LLM 服务不可达" in excinfo.value.detail
