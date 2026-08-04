# 开发文档 04｜Agent、规则与模型边界

定义确定性规则、传统模型、LLM Agent 与人工研究员的责任边界

文档版本：v0.1  |  日期：2026-08-04  |  状态：MVP Engineering Baseline

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
| 事件聚类 | 阈值/状态机 | 主责 | 命名解释 | 修正 |
| 情绪对象识别 |  | 辅助 | 主责 | 修正 |
| 观点/理由抽取 |  |  | 主责 | 修正 |
| 情绪/热度指数 | 主责 |  | 不参与 | 参数审批 |
| 告警触发 | 主责 | 提供异常分 | 不参与 | 配置 |
| 产业链实体映射 | 硬约束 | 图/检索模型 | 候选解释 | 审核 |
| 传导路径 | 过滤/校验 | 排序 | 提出候选 | 最终判断 |
| 风险评分 | 主责 | 参数估计 | 不直接给最终分 | 调整/审批 |
| 简报撰写 | 模板/引用限制 |  | 主责 | 审批 |
| 证据引用 | 主责 |  | 只能引用给定 ID | 核查 |

## 3. 工作流：Orchestrator 不是 Agent

```text
新数据到达
 → 规则清洗 / 去重
 → 聚类模型更新事件
 → 状态机判断是否满足分析条件
 → Opinion Agent 结构化抽取
 → 程序聚合统计
 → Transmission Agent 生成候选路径
 → 规则验证实体、证据、重复关系
 → Scoring Engine 计算风险分数
 → 告警规则判断是否触发
 → Brief Agent 基于冻结数据生成简报
 → 人工确认/修改/外发
```

## 4. Agent A：事件理解 Event Interpreter

输入：已完成聚类的文本代表样本、事实源片段、实体候选。输出：事件标准名称、动作、主体、对象、事实陈述与不确定陈述。不得决定告警级别。

```text
EventInterpretation {
  event_type: enum
  subject_entities: [entity_id]
  action: string
  object_entities: [entity_id]
  factual_claims: [{claim, evidence_ids}]
  uncertain_claims: [{claim, evidence_ids}]
  summary: string
  model_confidence: float
}
```

## 5. Agent B：观点归因 Opinion Extractor

输入：单条或小批量去重文本 + 当前事件上下文。输出结构化观点，不承担聚合。

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
```

## 6. Agent C：传导假设 Transmission Hypothesis

输入必须包含：已确认事件、产业链/公司业务知识记录、观点簇、历史相似事件。输出只能是候选路径，并引用证据与知识记录。

```text
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

## 7. Agent D：简报生成 Brief Writer

- 输入只允许使用已冻结 snapshot 的结构化字段和 evidence_id，不允许自由联网补充事实。

- 数值、公司名称、时间和风险等级由系统字段注入，LLM 不重新计算。

- 输出中每个事实性句子必须关联至少一个 evidence_id；没有证据则写为“系统推测/待验证”。

- 支持固定模板：事件摘要、市场主导观点、传导路径、影响对象、反向证据、风险提示。

## 8. 规则系统与状态机

| 规则类别 | 示例 |
| --- | --- |
| 事件触发 | 10 分钟独立样本数 > N 且增速 > X |
| 数据完整性 | 至少一个事实/新闻源可用，否则风险置信度上限降低 |
| 分析触发 | 事件达到 active 状态且新增样本 > K |
| 告警触发 | risk_score > threshold 且 cooldown 到期 |
| 抑制规则 | 重复事件、已静音实体、低质量来源占比过高 |
| 降级规则 | LLM 超时则保留统计视图，不阻塞事件和告警系统 |

## 9. 风险评分边界

LLM 可以输出语义因子，但最终 risk_score 必须由版本化公式计算。示例结构：

```text
risk_score = f(
    heat_anomaly,
    sentiment_intensity,
    disagreement,
    entity_exposure,
    fact_support,
    source_quality,
    transmission_support
)
```

所有输入因子、归一化方式、权重和阈值写入 scoring_version。模型不得直接输出“风险=87”作为权威结果。

## 10. LLM 安全与可靠性约束

- 结构化输出：JSON Schema 严格校验；解析失败自动重试一次，仍失败则进入 degraded 状态。

- 证据约束：只能引用输入中存在的 ID；服务端校验不存在的引用并拒绝结果。

- 实体约束：公司/行业优先从 entity registry 选择；新实体进入候选表，不直接写主数据。

- 数值约束：LLM 生成的数值字段只允许枚举/置信度；业务指标从数据库读取。

- 提示词注入防护：外部文本视为不可信数据，不允许其覆盖系统指令或工具权限。

- 模型故障隔离：LLM 不可用时，采集、聚类、指标、告警与证据浏览必须继续工作。

## 11. 版本与可观测性

| 记录项 | 必须保存 |
| --- | --- |
| 模型调用 | provider/model、temperature、prompt_version、输入哈希、输出、耗时、token/cost |
| 分析版本 | event_id、analysis_version、输入文档集合、知识库版本 |
| 规则计算 | calculation_id、scoring_version、参数、结果 |
| 人工修改 | 用户、时间、字段前后值、原因 |
| 报告 | snapshot_id、brief_prompt_version、引用证据集合 |

## 12. 模型评估体系

| 任务 | 离线指标 | 人工抽检 |
| --- | --- | --- |
| 观点抽取 | Target/stance/emotion F1、reason span accuracy | 金融语义准确性 |
| 事件理解 | 实体/动作抽取 F1、事实/推测分类 | 事件命名是否稳定 |
| 传导候选 | Precision@K、证据覆盖率、无效边率 | 经济逻辑合理性 |
| 简报 | 引用正确率、数值一致率、事实幻觉率 | 可读性与研究价值 |

## 13. 成本与调用策略

- 不对每条原始帖子调用大模型：先去重、聚类和采样，再对代表文本/高价值文本调用。

- 观点抽取优先使用小模型或批处理结构化输出；传导分析和简报使用能力更强模型。

- 缓存键包含文本哈希 + prompt_version + model_version；同内容同版本尽量复用。

- 设置单事件 token/cost budget，超过预算进入抽样模式并在 UI 标记分析覆盖率。

## 14. MVP 验收标准

1. 关闭 LLM 服务后，系统仍能采集、聚类、计算热度并显示事件。

1. LLM 输出不存在的 evidence_id 时，服务端能够拒绝结果并记录错误。

1. 风险分数可由 calculation_id 完整复算，不依赖模型自然语言输出。

1. 研究员可拒绝一条传导边，系统保留原候选和人工决策记录。

1. 每次报告生成可以追溯到模型版本、提示词版本、snapshot 与证据集合。
