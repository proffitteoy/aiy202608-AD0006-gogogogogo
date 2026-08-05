# 开发文档 04｜Agent、规则与模型边界

定义确定性规则、传统模型、LLM Agent 与人工研究员的责任边界

文档版本：v0.2  |  日期：2026-08-05  |  状态：MVP Engineering Baseline

| 关键决策：规则决定系统何时触发、如何计算和如何审计；传统模型负责高频可训练任务；LLM 负责语义理解和候选假设；研究员保留重大结论与投资含义的最终判断权。 |
| --- |

## 1. 核心原则

1. 可确定、可复现、可审计的问题优先使用代码/规则，不使用 LLM。

1. 高频、稳定标签、可监督训练的问题优先使用传统模型/小模型。

1. 需要跨句语义理解、开放式归因、自然语言归纳的问题使用 LLM。

1. LLM 不直接写数据库权威字段；其输出先进入候选层，经过 schema、证据与规则校验。

1. 重大风险结论、外发研究报告与投资判断保留人工审批。

## 2. 职责矩阵

| 任务 | 规则/程序 | 传统模型 | LLM | 人工 |
| --- | --- | --- | --- | --- |
| 采集/时间标准化 | 主责 |  |  |  |
| 精确/近似去重 | 主责 | 辅助 |  | 抽查 |
| 垃圾/机器人过滤 | 规则 | 主责 | 辅助 | 抽查 |
| Rule 1 事件归类 | 阈值/状态机 | 主责 | 不参与裁决 | 修正 |
| Rule 2 入库管理 | 主责：DROP / WAIT / ADMIT / ATTACH |  | 不参与裁决 | 审核规则 |
| Rule 3 确定性评分 | 主责 | 参数估计 | 不参与基础分形成 | 参数审批 |
| Rule 4 后验校准 | 主责 | 参数估计 | 不参与校准分形成 | 参数审批 |
| 情绪对象识别 |  | 辅助 | 主责 | 修正 |
| 观点/理由抽取 |  |  | 主责 | 修正 |
| 热度/动量/扩散指标 | 主责 |  | 不参与 | 参数审批 |
| 告警触发 | 主责 | 提供异常分 | 不参与 | 配置 |
| 产业链实体映射 | 硬约束 | 图/检索模型 | 候选解释 | 审核 |
| 传导路径 | 过滤/校验 | 排序 | 提出候选 | 最终判断 |
| 评分解释 | 提供冻结字段 |  | 基于证据解释，不改分 | 审批 |
| 简报撰写 | 模板/引用限制 |  | 主责 | 审批 |
| 证据引用 | 主责 |  | 只能引用给定 ID | 核查 |

## 3. 工作流：Orchestrator 不是 Agent

```text
新数据到达
 → 规则清洗 / 去重
 → Rule 1 事件归类 / 匹配
 → Rule 2 入库管理：DROP / WAIT / ADMIT / ATTACH
 → Event 正式对象与状态机
 → Rule 3 确定性评分：raw_score
 → Rule 4 后验校准：calibrated_score / confidence / score_interval
 → Agent 1 Event Tagger 生成事件标签候选
 → Agent 2 Analyze 生成评分解释、观点归因、传导假设和反向证据
 → 规则验证实体、证据 ID、重复关系与结构化输出
 → AnalysisSnapshot 冻结评分、校准、标签、分析、证据和版本
 → 告警、工作台和导出消费 Snapshot
 → Agent 2 Render 基于冻结 Snapshot 生成报告
 → 人工确认/修改/外发
```

## 4. Rule 1：事件归类 Event Classification / Matching

输入：去重后的 RawDocument、实体候选、时间窗口、已有 Event 候选。输出：事件匹配结果和归类依据。Rule 1 只判断“是否同一事件/应归入哪个事件”，不计算最终风险分。

```text
EventClassification {
  document_id: UUID
  matched_event_id: UUID | null
  match_score: float
  event_type: enum
  subject_entities: [entity_id]
  time_window: {start, end}
  rule_version: string
}
```

## 5. Rule 2：入库管理 Admission Management

输入：Rule 1 结果、来源质量、市场相关性、状态变化、潜在影响、Novelty 和数据完整性。输出是入库裁决，不是评分结果。`Admission Decision` 与 Rule 3 的 `raw_score` 必须解耦。

```text
AdmissionDecision {
  document_id: UUID
  event_id: UUID | null
  decision: "DROP" | "WAIT" | "ADMIT" | "ATTACH"
  factors: {
    market_relevance,
    state_change,
    potential_impact,
    novelty,
    source_quality,
    data_completeness
  }
  rule_version: string
}
```

## 6. Rule 3 与 Rule 4：评分和后验校准

Rule 3 在正式 Event 形成后计算基础分；Rule 4 在基础分之上计算后验校准分、置信度和分数区间。二者都只能使用事件自身和来源/扩散/行情等可观测量，不能依赖 Agent 1/2 的观点或传导产物。

```text
ScoreResult {
  event_id: UUID
  raw_score: float
  scoring_version: string
  input_calculation_ids: [UUID]
}

ScoreCalibration {
  event_id: UUID
  raw_score: float
  calibrated_score: float
  confidence: float
  lower_bound: float
  upper_bound: float
  calibration_version: string
  evidence_ids: [UUID]
}
```

Rule 4 的输出只能由版本化校准程序产生。仓库不提供 Agent 调分、候选解释分或 `proposed_score` 入口；Agent 只能引用冻结分数和 calculation_id 生成解释。

## 7. Agent 1：事件标签 Event Tagger

输入：已入库 Event、Rule 3/4 评分结果、允许引用的证据和实体候选。输出：事件标签、短名称、主体、动作、对象、事实/不确定陈述候选。Agent 1 不得修改 Event 状态、评分或告警级别。

```text
EventTag {
  event_id: UUID
  canonical_title: string
  event_type: enum
  subject_entities: [entity_id]
  action: string
  object_entities: [entity_id]
  factual_claims: [{claim, evidence_ids}]
  uncertain_claims: [{claim, evidence_ids}]
  model_confidence: float
}
```

## 8. Agent 2：研究报告 Agent

Agent 2 是一个 Agent，但分成两个 operation。Analyze 负责结构化研究产物，Render 负责报告文本；中间必须经过证据校验和 Snapshot 冻结。

```text
ReportAnalysis {
  event_id: UUID
  score_interpretation: [{claim, evidence_ids, calculation_ids}]
  opinion_attributions: [OpinionRecord]
  transmission_hypotheses: [TransmissionEdgeCandidate]
  counter_evidence: [{claim, evidence_ids}]
  narrative_outline: string
  model_confidence: float
}
```

保留的结构化对象：

- `OpinionRecord`：单条或小批文本的观点、立场、理由和证据引用。
- `TransmissionEdgeCandidate`：候选传导边，必须引用 evidence_ids 和 knowledge_ids。
- `Report`：基于冻结 snapshot 渲染的报告，不作为评分输入。

```text
OpinionRecord {
  document_id: UUID
  target_entity_id: UUID | null
  stance: "bullish" | "bearish" | "neutral" | "wait"
  emotion: enum
  reason: string
  claim_type: "fact" | "opinion" | "speculation"
  evidence_span: string
  model_confidence: float
}

TransmissionEdgeCandidate {
  from_node_id: UUID
  to_node_id: UUID
  mechanism: string
  direction: "positive" | "negative" | "uncertain"
  horizon: "immediate" | "short" | "medium" | "long"
  evidence_ids: [UUID]
  knowledge_ids: [UUID]
  model_confidence: float
  status: "candidate"
}
```

- 输入只允许使用已冻结 snapshot 的结构化字段和 evidence_id，不允许自由联网补充事实。

- 数值、公司名称、时间和风险等级由系统字段注入，LLM 不重新计算。

- 输出中每个事实性句子必须关联至少一个 evidence_id；没有证据则写为“系统推测/待验证”。

- 支持固定模板：事件摘要、市场主导观点、传导路径、影响对象、反向证据、风险提示。

## 9. 规则系统与状态机

| 规则类别 | 示例 |
| --- | --- |
| 事件归类 | 复合相似度达到阈值则 ATTACH，否则进入新事件候选 |
| 入库管理 | Rule 2 输出 DROP / WAIT / ADMIT / ATTACH |
| 数据完整性 | 至少一个事实/新闻源可用，否则风险置信度上限降低 |
| 分析触发 | 事件达到 confirmed/active 状态且新增样本 > K |
| 告警触发 | calibrated_score > threshold 且 cooldown 到期 |
| 抑制规则 | 重复事件、已静音实体、低质量来源占比过高 |
| 降级规则 | LLM 超时则保留统计视图，不阻塞事件和告警系统 |

## 10. 风险评分边界

Rule 3/4 的权威评分链先于 Agent 运行。基础分和校准分必须由版本化公式计算，输入来自事件可观测量、来源结构、扩散结构、行情反应、事实支持和数据完整度，而不是 Agent 生成的观点归因或传导假设。

```text
raw_score = f(
    event_features,
    source_features,
    diffusion_features,
    market_features,
    data_completeness
)

posterior_calibration(raw_score, evidence_state)
  -> calibrated_score, confidence, score_interval
```

所有输入因子、归一化方式、权重、阈值和后验参数写入 `scoring_version` / `calibration_version`。模型不得直接输出“风险=87”作为权威结果，也不得通过“Agent 调整分”覆盖 Rule 3/4 的结果。

## 11. LLM 安全与可靠性约束

- 结构化输出：JSON Schema 严格校验；解析失败自动重试一次，仍失败则进入 degraded 状态。

- 证据约束：只能引用输入中存在的 ID；服务端校验不存在的引用并拒绝结果。

- 实体约束：公司/行业优先从 entity registry 选择；新实体进入候选表，不直接写主数据。

- 数值约束：LLM 只生成枚举、模型置信度或解释性排序；不得输出可覆盖 `raw_score`、`calibrated_score`、`confidence` 或评分区间的字段。业务指标和评分只能从数据库冻结字段读取。

- 提示词注入防护：外部文本视为不可信数据，不允许其覆盖系统指令或工具权限。

- 模型故障隔离：LLM 不可用时，采集、聚类、指标、告警与证据浏览必须继续工作。

## 12. 版本与可观测性

| 记录项 | 必须保存 |
| --- | --- |
| 模型调用 | provider/model、temperature、prompt_version、输入哈希、输出、耗时、token/cost |
| 分析版本 | event_id、analysis_version、输入文档集合、知识库版本 |
| 规则计算 | calculation_id、scoring_version、calibration_version、参数、结果 |
| 人工修改 | 用户、时间、字段前后值、原因 |
| 报告 | snapshot_id、brief_prompt_version、引用证据集合 |

## 13. 模型评估体系

| 任务 | 离线指标 | 人工抽检 |
| --- | --- | --- |
| 观点抽取 | Target/stance/emotion F1、reason span accuracy | 金融语义准确性 |
| 事件标签 | 实体/动作抽取 F1、事实/推测分类 | 事件命名是否稳定 |
| 观点归因/传导候选 | Precision@K、证据覆盖率、无效边率 | 经济逻辑合理性 |
| 简报 | 引用正确率、数值一致率、事实幻觉率 | 可读性与研究价值 |

## 14. 成本与调用策略

- 不对每条原始帖子调用大模型：先去重、聚类和采样，再对代表文本/高价值文本调用。

- Agent 1 标签可以优先使用小模型或批处理结构化输出；Agent 2 的观点归因、传导分析和报告渲染使用能力更强模型。

- 缓存键包含文本哈希 + prompt_version + model_version；同内容同版本尽量复用。

- 设置单事件 token/cost budget，超过预算进入抽样模式并在 UI 标记分析覆盖率。

## 15. MVP 验收标准

1. 关闭 LLM 服务后，系统仍能采集、归类、入库、计算 Rule 3/4 评分、告警并显示事件。

1. LLM 输出不存在的 evidence_id 时，服务端能够拒绝结果并记录错误。

1. `raw_score`、`calibrated_score`、`confidence` 和 `score_interval` 可由 calculation_id 完整复算，不依赖模型自然语言输出。

1. 研究员可拒绝一条传导边，系统保留原候选和人工决策记录。

1. 每次报告生成可以追溯到模型版本、提示词版本、snapshot 与证据集合。

## 16. 当前事件引擎实现边界

当前纯规则代码已实现 `event-match-v1`、`admission-v2`、`confirmation-v2`、
`deterministic-scoring-v1`、`event-lifecycle-v1` 和 `score-calibration-v1`。Rule 2 使用
`DROP / WAIT / ADMIT / ATTACH`；Rule 3 的输入仅包含事件、来源、扩散、行情和完整度等可观测量；
Rule 4 直接校准 `raw_score`，没有 Agent 调分入口。第五个迁移保存 Rule 3/4 版本、冻结证据、
校准分、置信度和区间。

`confirmation-v2` 将事实源、专业新闻和社交证据分层累积，并用聚类一致性和反证修正；传播速度
只进入 Heat/Momentum，不再用于证明事实成立。缺失互动基线、行情或平台覆盖时，对应因子保持
`null` 或显式 degraded，不能以 0 冒充已观测数据。

当前已有固定场景导入器、统一接入和只读事件/证据 API，且查询由服务端固定 Demo tenant 过滤。
首次统一接入会同步尽力执行确定性流水线，写入 Rule 1/2 准入、Event/Evidence 关联、EventMetric 和
Rule 3/4 校准记录；但该数据库调用路径尚未完成真实回放验收，也没有可靠处理状态、重试或后台调度。
旧的 Opinion/Transmission 独立 Agent 执行入口已移除，只保留结构化对象、只读查询和前端展示。
Agent 1、Agent 2、Evidence Mapper、AnalysisSnapshot 与报告生成仍未实现，因此不能声称 Agent
闭环或完整 MVP 已运行。
