"""LLM prompt & schema definitions for the report agent.

3 段（overview / recommendations / risk-notes）走 LLM，共享同一个输出契约：
每段产出 1-4 条 statement，每条必须挂 ≥1 条 evidence_id，evidence_id 必须来自
snapshot 中已冻结的证据集合。整报的其它 4 段仍走模板拼接（在 service 里）。
"""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field

from risktrace.reports.schemas import AnalysisSnapshotPayload

SectionKey = Literal["overview", "recommendations", "risk-notes"]

MAX_STATEMENTS = 4
MIN_STATEMENT_LEN = 12
MAX_STATEMENT_LEN = 280


class LLMStatement(BaseModel):
    """LLM 输出的单条 statement，evidence_ids 必须非空且来自 snapshot。"""

    text: str = Field(min_length=MIN_STATEMENT_LEN, max_length=MAX_STATEMENT_LEN)
    evidence_ids: list[uuid.UUID] = Field(min_length=1, max_length=8)


class LLMSectionOutput(BaseModel):
    """一个 section 的 LLM 输出契约。"""

    statements: list[LLMStatement] = Field(min_length=1, max_length=MAX_STATEMENTS)


SYSTEM_PROMPTS: dict[SectionKey, str] = {
    "overview": (
        "你是金融事件研究助手，负责撰写事件摘要段落。\n"
        "规则：\n"
        "- 只根据用户提供的冻结 snapshot 数据写作，不引入外部知识、不预测点位、不给出投资建议。\n"
        "- 输出 2-4 条 statement：先讲事件当前状态与时间锚点，再补充证据覆盖与评分情况。\n"
        "- 每条 statement 必须挂至少 1 个 evidence_id，且必须来自输入证据列表。\n"
        "- 语气保持中性、客观；避免夸张、感叹、绝对化措辞。\n"
        "- 用简体中文输出，严格按 JSON schema 返回，不要写解释、不要输出多余文字。"
    ),
    "recommendations": (
        "你是金融事件研究助手，负责撰写研究建议段落。\n"
        "规则：\n"
        "- 只根据用户提供的冻结 snapshot 数据写建议，不给出任何形式的投资建议、不预测价格。\n"
        "- 输出 2-3 条 statement：以“建议…”开头，聚焦研究方法（如复核证据、跟踪指标、补做梳理）。\n"
        "- 每条 statement 必须挂至少 1 个 evidence_id 或 calculation_id 的引用。\n"
        "- 涉及具体主体或路径时，措辞用“建议复核”、“建议追踪”，避免断言。\n"
        "- 用简体中文输出，严格按 JSON schema 返回。"
    ),
    "risk-notes": (
        "你是金融事件研究助手，负责撰写风险提示段落。\n"
        "规则：\n"
        "- 只根据用户提供的冻结 snapshot 中的降级原因、缺失产物、置信度水平写风险点。\n"
        "- 输出 2-4 条 statement：指出评分降级、证据类型缺口、观点或传导未覆盖等具体风险。\n"
        "- 每条 statement 必须挂至少 1 个 evidence_id。\n"
        "- 结尾一条建议“报告结论需研究员复核后再对外使用”。\n"
        "- 用简体中文输出，严格按 JSON schema 返回。"
    ),
}


def build_user_prompt(section: SectionKey, payload: AnalysisSnapshotPayload) -> str:
    """把 snapshot payload 序列化成给 LLM 的 user 消息。"""

    lines: list[str] = []
    lines.append(f"# 段落：{section}")
    lines.append("")
    lines.append("## 事件")
    lines.append(f"- title: {payload.event.title}")
    lines.append(f"- status: {payload.event.status}")
    lines.append(f"- first_published_at: {payload.event.first_published_at.isoformat()}")
    lines.append(
        f"- source_count: {payload.event.source_count}"
        f" (authoritative: {payload.event.authoritative_source_count})"
    )
    breakdown = "，".join(
        f"{key} {value}" for key, value in sorted(payload.event.source_breakdown.items())
    )
    lines.append(f"- source_breakdown: {breakdown or '无'}")

    lines.append("")
    lines.append("## 评分")
    lines.append(f"- status: {payload.score.status}")
    lines.append(f"- calibrated_score: {payload.score.calibrated_score}")
    lines.append(f"- confidence: {payload.score.confidence}")
    if payload.score.score_interval:
        lines.append(
            f"- score_interval: [{payload.score.score_interval.lower_bound},"
            f" {payload.score.score_interval.upper_bound}]"
        )
    if payload.score.degradation_reasons:
        lines.append(f"- degradation_reasons: {payload.score.degradation_reasons}")

    lines.append("")
    lines.append("## 证据（evidence_id 必须来自这里）")
    for item in payload.evidence[:12]:
        lines.append(
            f"- {item.id} · {item.source_type} · {item.title}"
            f" · 采集于 {item.collected_at.isoformat()}"
        )

    if payload.opinions:
        lines.append("")
        lines.append("## 观点归因")
        for op in payload.opinions[:6]:
            lines.append(
                f"- stance={op.stance} emotion={op.emotion} claim_type={op.claim_type}"
                f" reason={op.reason}"
            )

    if payload.transmission:
        lines.append("")
        lines.append("## 传导候选")
        for edge in payload.transmission[:6]:
            lines.append(
                f"- {edge.from_node_label or '?'} -> {edge.to_node_label or '?'}"
                f" 方向={edge.direction} 期限={edge.horizon}"
                f" 机制={edge.mechanism}"
            )

    if payload.impact_matrix:
        lines.append("")
        lines.append("## 影响对象")
        for row in payload.impact_matrix[:6]:
            lines.append(
                f"- {row.entity_name} 方向={row.direction}"
                f" 综合置信度={row.composite_confidence:.2f}"
                f" 影响强度={row.impact_strength:.2f}"
                f" 证据数={row.evidence_count}"
            )

    lines.append("")
    lines.append("请严格按下述 JSON schema 返回：")
    lines.append("{")
    lines.append('  "statements": [')
    lines.append('    { "text": "...", "evidence_ids": ["<uuid>", ...] }')
    lines.append("  ]")
    lines.append("}")
    return "\n".join(lines)
