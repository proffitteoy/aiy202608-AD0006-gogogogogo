import json
import uuid
from types import SimpleNamespace

import httpx
import pytest

from risktrace.agents.transmission import TransmissionGraphAgent


def _sse_response(payload: dict[str, object]) -> httpx.Response:
    body = (
        "data: "
        + json.dumps(
            {"choices": [{"delta": {"content": json.dumps(payload)}}]}
        )
        + "\n\ndata: [DONE]\n\n"
    )
    return httpx.Response(
        200,
        headers={"content-type": "text/event-stream"},
        content=body.encode("utf-8"),
    )


@pytest.mark.asyncio
async def test_transmission_agent_calls_openai_compatible_chat_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    event_id = uuid.UUID("e1000000-0000-0000-0000-000000000001")
    company_id = uuid.UUID("30000000-0000-0000-0000-000000000001")
    evidence_id = uuid.UUID("40000000-0000-0000-0000-000000000001")

    monkeypatch.setattr(
        "risktrace.agents.transmission.get_settings",
        lambda: SimpleNamespace(
            llm_provider="openai",
            llm_model="gpt-4o-mini",
            llm_api_key="test-key",
            llm_base_url="",
            llm_temperature=0.3,
            llm_max_tokens=256,
        ),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("Authorization")
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return _sse_response(
            {
                "edges": [
                    {
                        "from_node_type": "event",
                        "from_node_id": str(event_id),
                        "to_node_type": "entity",
                        "to_node_id": str(company_id),
                        "mechanism": "政策预期升温后，市场资金优先追逐电网设备龙头。",
                        "direction": "positive",
                        "horizon": "short",
                        "evidence_doc_ids": [str(evidence_id)],
                        "confidence": 0.82,
                    }
                ]
            }
        )

    agent = TransmissionGraphAgent(
        object(),  # type: ignore[arg-type]
        transport=httpx.MockTransport(handler),
    )

    output = await agent._run_llm(
        event_title="测试事件",
        node_lines=f"{event_id}: 测试事件\n{company_id}: 特高压龙头",
        doc_text=f"[{evidence_id}] (news, cls) 政策预期升温带动电网设备交易",
    )

    assert len(output.edges) == 1
    assert output.edges[0].from_node_type == "event"
    assert output.edges[0].to_node_type == "entity"
    assert output.edges[0].evidence_doc_ids == [evidence_id]
    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
    assert captured["auth"] == "Bearer test-key"

    body = captured["body"]
    assert isinstance(body, dict)
    assert body["model"] == "gpt-4o-mini"
    assert body["response_format"]["type"] == "json_schema"
    assert body["messages"][0]["role"] == "system"
    assert body["messages"][1]["role"] == "user"


@pytest.mark.asyncio
async def test_transmission_agent_uses_deepseek_compatible_json_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "risktrace.agents.transmission.get_settings",
        lambda: SimpleNamespace(
            llm_provider="deepseek",
            llm_model="deepseek-v4-flash",
            llm_api_key="test-key",
            llm_base_url="https://api.deepseek.com",
            llm_temperature=0.3,
            llm_max_tokens=256,
        ),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return _sse_response({"edges": []})

    agent = TransmissionGraphAgent(
        object(),  # type: ignore[arg-type]
        transport=httpx.MockTransport(handler),
    )

    output = await agent._run_llm(
        event_title="测试事件",
        node_lines="",
        doc_text="测试材料",
    )

    assert output.edges == []
    body = captured["body"]
    assert isinstance(body, dict)
    assert body["response_format"] == {"type": "json_object"}
    assert body["thinking"] == {"type": "disabled"}
    assert '{"edges": [...]}' in body["messages"][0]["content"]
