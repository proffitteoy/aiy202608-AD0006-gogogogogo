import json
import uuid
from types import SimpleNamespace

import httpx
import pytest

from risktrace.agents.opinions import OpinionExtractionAgent, OpinionItem


def _sse_response(payload: dict[str, object]) -> httpx.Response:
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
async def test_opinions_agent_hits_openai_json_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    doc_id = uuid.UUID("40000000-0000-0000-0000-000000000001")
    entity_id = uuid.UUID("30000000-0000-0000-0000-000000000001")

    monkeypatch.setattr(
        "risktrace.agents.opinions.get_settings",
        lambda: _mock_settings(),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("Authorization")
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return _sse_response(
            {
                "opinions": [
                    {
                        "document_id": str(doc_id),
                        "target_entity_id": str(entity_id),
                        "stance": "bullish",
                        "emotion": "乐观",
                        "claim_type": "opinion",
                        "reason": "机构一致认为扩产提升行业景气度。",
                        "evidence_span": "机构预计明年电池片供需持续偏紧。",
                        "confidence": 0.86,
                    }
                ]
            }
        )

    agent = OpinionExtractionAgent(
        object(),  # type: ignore[arg-type]
        transport=httpx.MockTransport(handler),
    )

    output = await agent._run_llm(
        event_title="测试事件",
        entity_lines=f"  {entity_id}: 隆基绿能 (company)",
        doc_text=f"[{doc_id}] (news, cls) 政策预期升温带动电网设备交易",
    )

    assert len(output.opinions) == 1
    op = output.opinions[0]
    assert op.stance == "bullish"
    assert op.claim_type == "opinion"
    assert op.document_id == doc_id
    assert op.target_entity_id == entity_id
    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
    assert captured["auth"] == "Bearer test-key"

    body = captured["body"]
    assert isinstance(body, dict)
    assert body["model"] == "gpt-4o-mini"
    assert body["response_format"]["type"] == "json_schema"
    assert body["messages"][0]["role"] == "system"
    assert body["messages"][1]["role"] == "user"


@pytest.mark.asyncio
async def test_opinions_agent_uses_deepseek_json_object_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "risktrace.agents.opinions.get_settings",
        lambda: _mock_settings(
            llm_provider="deepseek",
            llm_model="deepseek-v4-flash",
            llm_base_url="https://api.deepseek.com",
        ),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return _sse_response({"opinions": []})

    agent = OpinionExtractionAgent(
        object(),  # type: ignore[arg-type]
        transport=httpx.MockTransport(handler),
    )

    output = await agent._run_llm(
        event_title="测试事件",
        entity_lines="",
        doc_text="测试材料",
    )

    assert output.opinions == []
    body = captured["body"]
    assert isinstance(body, dict)
    assert body["response_format"] == {"type": "json_object"}
    assert body["thinking"] == {"type": "disabled"}
    assert '{"opinions": [...]}' in body["messages"][0]["content"]


def test_valid_opinions_drops_unknown_docs_and_scrubs_bad_entities() -> None:
    doc_ok = uuid.uuid4()
    doc_missing = uuid.uuid4()
    entity_ok = uuid.uuid4()
    entity_missing = uuid.uuid4()

    items = [
        # Kept — everything resolves.
        OpinionItem(
            document_id=doc_ok,
            target_entity_id=entity_ok,
            stance="bullish",
            emotion="乐观",
            claim_type="opinion",
            reason="机构一致看多。",
            evidence_span="机构预计明年供需偏紧。",
            confidence=0.9,
        ),
        # Dropped — document not in registry.
        OpinionItem(
            document_id=doc_missing,
            target_entity_id=entity_ok,
            stance="bearish",
            emotion="悲观",
            claim_type="opinion",
            reason="担忧产能过剩。",
            evidence_span="部分投资者担忧价格战。",
            confidence=0.7,
        ),
        # Kept, but target_entity_id scrubbed because it's not in tenant registry.
        OpinionItem(
            document_id=doc_ok,
            target_entity_id=entity_missing,
            stance="wait",
            emotion="观望",
            claim_type="speculation",
            reason="政策落地前维持观望。",
            evidence_span="市场观望政策细则。",
            confidence=0.6,
        ),
    ]

    valid = OpinionExtractionAgent._valid_opinions(
        items,
        valid_doc_ids=frozenset({doc_ok}),
        valid_entity_ids=frozenset({entity_ok}),
    )

    assert len(valid) == 2
    assert valid[0].stance == "bullish"
    assert valid[0].target_entity_id == entity_ok
    assert valid[1].stance == "wait"
    assert valid[1].target_entity_id is None
