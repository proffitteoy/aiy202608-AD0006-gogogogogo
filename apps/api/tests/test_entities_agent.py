import json
import uuid
from types import SimpleNamespace

import httpx
import pytest

from risktrace.agents.entities import EntityExtractionAgent, EntityItem


def _sse_response(payload: dict[str, object]) -> httpx.Response:
    """Wrap a JSON payload as a single-frame SSE stream that the agent can parse."""

    body = (
        "data: "
        + json.dumps(
            {
                "choices": [
                    {"delta": {"content": json.dumps(payload)}}
                ]
            }
        )
        + "\n\ndata: [DONE]\n\n"
    )
    return httpx.Response(
        200,
        headers={"content-type": "text/event-stream"},
        content=body.encode("utf-8"),
    )


def _mock_settings(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "llm_provider": "openai",
        "llm_model": "gpt-4o-mini",
        "llm_api_key": "test-key",
        "llm_base_url": "",
        "llm_temperature": 0.3,
        "llm_max_tokens": 256,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_entities_agent_hits_openai_json_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    evidence_id = uuid.UUID("40000000-0000-0000-0000-000000000001")

    monkeypatch.setattr(
        "risktrace.agents.entities.get_settings",
        lambda: _mock_settings(),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("Authorization")
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return _sse_response(
            {
                "entities": [
                    {
                        "name": "隆基绿能",
                        "entity_type": "company",
                        "canonical_code": "601012.SH",
                        "evidence_doc_ids": [str(evidence_id)],
                        "confidence": 0.9,
                    }
                ]
            }
        )

    agent = EntityExtractionAgent(
        object(),  # type: ignore[arg-type]
        transport=httpx.MockTransport(handler),
    )

    output = await agent._run_llm(
        event_title="测试事件",
        doc_text=f"[{evidence_id}] (news, cls) 隆基绿能拟扩产 GW 级 TOPCon 产能",
    )

    assert len(output.entities) == 1
    assert output.entities[0].name == "隆基绿能"
    assert output.entities[0].entity_type == "company"
    assert output.entities[0].evidence_doc_ids == [evidence_id]
    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
    assert captured["auth"] == "Bearer test-key"

    body = captured["body"]
    assert isinstance(body, dict)
    assert body["model"] == "gpt-4o-mini"
    assert body["response_format"]["type"] == "json_schema"
    assert body["messages"][0]["role"] == "system"
    assert body["messages"][1]["role"] == "user"


@pytest.mark.asyncio
async def test_entities_agent_uses_deepseek_json_object_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "risktrace.agents.entities.get_settings",
        lambda: _mock_settings(
            llm_provider="deepseek",
            llm_model="deepseek-v4-flash",
            llm_base_url="https://api.deepseek.com",
        ),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return _sse_response({"entities": []})

    agent = EntityExtractionAgent(
        object(),  # type: ignore[arg-type]
        transport=httpx.MockTransport(handler),
    )

    output = await agent._run_llm(event_title="测试事件", doc_text="测试材料")

    assert output.entities == []
    body = captured["body"]
    assert isinstance(body, dict)
    assert body["response_format"] == {"type": "json_object"}
    assert body["thinking"] == {"type": "disabled"}
    assert '{"entities": [...]}' in body["messages"][0]["content"]


def test_valid_entities_drops_unknown_evidence_and_dedupes() -> None:
    doc_a = uuid.uuid4()
    doc_b = uuid.uuid4()
    doc_unknown = uuid.uuid4()

    items = [
        EntityItem(
            name="隆基绿能",
            entity_type="company",
            canonical_code="601012.SH",
            evidence_doc_ids=[doc_a],
            confidence=0.8,
        ),
        EntityItem(
            name="隆基绿能 ",  # trailing/width variant should collapse to the same key
            entity_type="company",
            canonical_code=None,
            evidence_doc_ids=[doc_b],
            confidence=0.95,
        ),
        EntityItem(
            name="通威股份",
            entity_type="company",
            canonical_code=None,
            evidence_doc_ids=[doc_unknown],
            confidence=0.9,
        ),
    ]

    valid = EntityExtractionAgent._valid_entities(
        items,
        valid_doc_ids=frozenset({doc_a, doc_b}),
    )

    assert [e.name.strip() for e in valid] == ["隆基绿能"]
