# Rule 4 后验评分校准设计

定义 Rule 3 确定性评分之后的后验校准、置信度、评分区间与审计机制。

文档版本：v0.3  
状态：MVP Algorithm & Engineering Design

> 关键决策：Rule 3 产生 `raw_score`；Rule 4 基于当前证据状态和数据完整度产生 `calibrated_score`、`confidence` 与 `score_interval`。Agent 不参与基础评分或后验校准，也不得输出覆盖规则结果的调分字段。

---

## 1. 位置与边界

```text
RawDocument
  → 数据导入 / 清洗 / 去重
  → Rule 1 事件归类
  → Rule 2 入库管理
  → Event
  → Rule 3 确定性评分
  → Rule 4 后验评分校准
  → Agent 1 事件标签
  → Agent 2 Analyze / Render
  → AnalysisSnapshot
```

Rule 4 只接收已经形成的 Event、Rule 3 `raw_score`、证据状态、来源健康、数据完整度和历史校准参数。它不调用 LLM，不读取 Agent 观点归因、传导假设或报告文本作为评分输入。

---

## 2. 输入与输出

输入：

```text
ScoreCalibrationInput {
  event_id: UUID
  raw_score: float
  scoring_version: string
  evidence_ids: [UUID]
  source_health_state: object
  data_completeness: object
  market_data_state: object
  calibration_version: string
}
```

输出：

```text
ScoreCalibration {
  event_id: UUID
  raw_score: float
  calibrated_score: float
  confidence: float
  lower_bound: float
  upper_bound: float
  calibration_version: string
  input_evidence_ids: [UUID]
  input_calculation_ids: [UUID]
  degraded_reasons: [string]
  created_at: datetime
}
```

---

## 3. 核心语义

`raw_score` 回答：

> 当前可观测事件、来源、扩散和行情因子下，规则系统给出的基础风险/事件分数是多少？

`calibrated_score` 回答：

> 在当前证据完整度、来源状态和历史校准参数下，这个基础分应如何后验校准？

`confidence` 回答：

> 当前评分有多稳定，而不是事件一定为真的概率。

`score_interval` 回答：

> 在当前信息条件下，合理评分大致落在哪个区间。

---

## 4. 建议计算结构

```text
raw_score = Rule3(event_features, source_features, diffusion_features, market_features)

posterior_state = update(
  evidence_structure,
  source_health_state,
  data_completeness,
  market_data_state,
  historical_calibration_params
)

calibrated_score = calibrate(raw_score, posterior_state)
confidence = stability(posterior_state)
score_interval = interval(raw_score, posterior_state)
```

其中：

- `evidence_structure` 区分事实源、专业新闻源、舆情源和行情源，不把转载传播量当作独立事实证据。
- `source_health_state` 记录来源降级、延迟、错误率和授权状态。
- `data_completeness` 缺失时压低 confidence 或扩大区间，不以 0 冒充已观测数据。
- `historical_calibration_params` 必须版本化，并能在相同输入下复算。

---

## 5. 与 Agent 2 的关系

Agent 2 可以解释 Rule 4 的输出：

```text
score_interpretation {
  claim: string
  evidence_ids: [UUID]
  calculation_ids: [UUID]
}
```

但 Agent 2 不允许：

- 修改 `raw_score`。
- 修改 `calibrated_score`。
- 输出覆盖规则结果的调分字段。
- 以自然语言理由覆盖 `confidence` 或区间。
- 引用不存在的 evidence_id / calculation_id。

报告生成必须满足：

```text
Report = Render(AnalysisSnapshot)
```

也就是先冻结 Snapshot，再由 Agent 2 Render 生成报告。

---

## 6. Snapshot 冻结字段

```text
AnalysisSnapshot {
  event_state
  rule3_score
  rule4_calibration
  agent1_tags
  agent2_structured_analysis
  evidence_references
  rule_version
  calibration_version
  model_version
}
```

导出的报告和工作台展示都消费 Snapshot。历史报告不得因为新数据进入而改变含义。

---

## 7. 降级策略

| 故障 | 系统行为 |
| --- | --- |
| LLM 不可用 | Rule 3 与 Rule 4 正常运行；Agent 标签、观点归因和报告标记 degraded |
| 事实源不可用 | 降低数据完整度，confidence 被压低或封顶 |
| 新闻源不可用 | 保留已有校准结果，来源覆盖标记 degraded |
| 行情源延迟 | 扩大评分区间或标记市场因子 unavailable，不填充假数据 |
| 后验计算失败 | 保留 raw_score，calibrated_score 标记 unavailable，并记录错误 |

---

## 8. MVP 验收标准

1. 相同 Event、输入证据、规则版本和 calibration_version 能得到相同校准结果。
1. 相同 raw_score、不同证据结构的两个事件可以产生不同 confidence 和 score_interval。
1. 新增重复转载不得显著提高 confidence。
1. 来源降级时 confidence 必须下降、封顶或明确标记 degraded。
1. LLM 关闭后，raw_score、calibrated_score、confidence 和 score_interval 仍可计算。
1. Agent 2 的每个评分解释必须引用合法 evidence_id 或 calculation_id。
1. Snapshot 必须同时冻结 raw_score、calibrated_score、confidence、区间和版本信息。

---

## 9. 一句话总结

```text
Rule 3 produces the point estimate.
Rule 4 calibrates uncertainty and stability.
Agent explains frozen results; it does not score.
```
