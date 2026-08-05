# 总开发文档｜金融舆情风险监控与信息归因平台

基于多模型/Agent 协同的“金融事件—社交情绪—市场传导”实时研究工作台

文档版本：v0.2  |  日期：2026-08-05  |  状态：MVP Engineering Baseline

## 文档导航

- [01｜平台形态与部署架构](01-platform-architecture.md)
- [02｜消息源与数据接入治理](02-data-sources-and-ingestion.md)
- [03｜研究工作台与可视化交互](03-research-workbench.md)
- [04｜Agent、规则与模型边界](04-agent-rule-boundary.md)
- [05｜仓库结构与运行契约](05-repository-structure.md)
- [06｜开源组件落库边界](06-third-party-components.md)
- [07｜当前状态评估与纵向交付计划](07-current-state-and-delivery-plan.md)
- [第三方软件与许可证](../THIRD_PARTY_NOTICES.md)
- [自动事件聚类与热点计算设计](自动事件聚类热点计算设计.md)
- [Rule 4 后验评分校准设计](Rule4后验评分校准设计.md)

| 关键决策：产品目标不是预测股价，而是把“突发事件发生后人工浏览海量信息”的研究流程压缩为可追溯的事件识别、观点归因、传导假设与风险优先级判断。 |
| --- |

> 本文定义目标产品和验收边界，不代表所有能力已经交付。当前代码实现、运行验证与剩余风险以
> [当前状态评估](07-current-state-and-delivery-plan.md) 为准；根 [README](../README.md) 只保留操作者需要的快速入口。

## 1. 产品定义

面向证券研究员、私募/资管研究团队和风险研究岗位的桌面 Web SaaS。系统持续接收官方事实、专业新闻、社交讨论和行情数据，在事件发生后形成结构化研究快照：事件是什么、市场在讨论什么、情绪为何变化、潜在影响通过什么机制传到哪些行业/公司，以及每个结论依据哪些证据。

## 2. 明确的非目标

- 不提供自动交易执行。

- 不把“社交讨论与价格同向变化”包装为因果关系。

- 不由 LLM 直接给出权威风险分数、收益预测或投资建议。

- 不以绕过平台访问控制的爬虫作为长期数据基础。

- 不在 MVP 同时开发原生 Android、iOS、Windows 和 macOS 客户端。

## 3. Demo 核心任务

Demo 只验证一个研究者视角的端到端链路，不实现团队角色、审批流、成员管理或权限后台。

| 任务 | 系统价值 |
| --- | --- |
| 回放历史突发事件 | 验证真实数据可以进入统一 RawDocument 和 Event 链路 |
| 查看规则评分与后验校准 | 区分热度、风险分、置信度和数据完整度 |
| 下钻观点、传导假设和证据 | 减少人工浏览大量帖子/新闻的时间 |
| 导出风险卡片或结构化数据 | 形成可复核、可演示的研究交付物 |

## 4. 产品形态

| 层 | 形态 | 作用 |
| --- | --- | --- |
| 主产品 | 桌面 Web SaaS | 完整研究、下钻、对比、导出、配置 |
| 轻入口 | 手机 Web/PWA + 企业微信/邮件等 | 重大告警与一分钟风险卡片 |
| 集成层 | REST API / Webhook | 接入内部研究系统和机器人 |
| 企业版 | 私有化/专有云 | 接入机构内网数据、权限体系和审计要求 |

## 5. 数据源架构

```text
事实源：公告 / 监管 / 政策 / 官方声明
              ↓ 事实锚定
专业新闻：财经媒体 / 行业媒体 / 授权资讯
              ↓ 事件背景与解释
舆情源：微博 / 雪球 / 股吧 / 评论 / 公众号
              ↓ 观点、情绪、争议
行情源：股票 / 行业指数 / 商品等
              ↓ 时间对齐与市场反应
```

## 6. 端到端系统流程

```text
Source Adapters
  → Raw Store（不可变原始数据）
  → Normalization / Dedup / Quality
  → Rule 1：Event Classification / Matching（事件归类）
  → Rule 2：Admission Management（DROP / WAIT / ADMIT / ATTACH）
  → Event（正式事件对象）
  → Rule 3：Deterministic Scoring（确定性评分）
  → Rule 4：Posterior Calibration（后验评分校准）
  → Agent 1：Event Tagger（事件标签）
  → Agent 2 Analyze：观点归因 / 传导假设 / 评分解释
  → Evidence Validation（证据 ID、实体、结构校验）
  → AnalysisSnapshot（冻结事件、评分、校准、标签、分析与证据）
  → Agent 2 Render：基于 Snapshot 生成报告
  → Workspace / Alert / Export / Human Review
```

核心顺序是 `Rule 3/4` 先于 `Agent 1/2`。Agent 可以解释事件、生成标签、归因观点和提出传导假设，但不参与基础分数和后验校准分数的形成。

## 7. 系统分层架构

| 层 | 核心组件 | 是否允许 LLM 决策 |
| --- | --- | --- |
| 数据接入层 | Adapters、原始存储、来源健康 | 否 |
| 数据治理层 | 清洗、去重、时间对齐、质量标签 | 否 |
| 事件规则层 | Rule 1 事件归类、Rule 2 入库管理、状态机 | 否 |
| 规则评分层 | Rule 3 确定性评分、Rule 4 后验校准、阈值、告警 | 否 |
| 语义分析层 | Agent 1 事件标签、Agent 2 观点归因/传导假设/报告渲染 | 是，但只输出候选/结构化结果 |
| 研究应用层 | 总览、工作台、证据、对比、导出 | 人工最终决策 |

## 8. 核心业务对象

| 对象 | 含义 | 关键标识 |
| --- | --- | --- |
| RawDocument | 原始来源文档 | document_id |
| Event | 持续演化的事件聚类 | event_id |
| EventTag | Agent 1 生成、经校验的事件标签 | event_tag_id |
| OpinionRecord | 单条文本的结构化观点 | opinion_id |
| OpinionCluster | 相似观点聚合 | opinion_cluster_id |
| Entity | 公司/行业/商品/政策等实体 | entity_id |
| TransmissionEdge | 候选/确认传导关系 | edge_id |
| EvidenceLink | 结论与证据关联 | evidence_link_id |
| Calculation | 一次可复算指标计算 | calculation_id |
| ScoreCalibration | 后验校准分、置信度与区间 | calibration_id |
| AnalysisSnapshot | 研究页面某时点冻结状态 | snapshot_id |
| Alert | 规则触发告警 | alert_id |

## 9. Event 生命周期

```text
candidate
  ├─ 样本不足/降温 → archived
  └─ 多源/高质量证据确认 → confirmed
        └─ 热度或评分达到监控条件 → active
              ├─ 达到分析条件 → analyzed
              ├─ 达到告警条件 → alerted
              └─ 长时间无新增 → cooling → closed
```

- Event 状态由规则状态机控制；LLM 无权直接将事件设为 alerted。

- 事件合并/拆分支持人工操作并生成版本记录。

- 历史回放使用与实时流相同的事件引擎，只替换数据时钟。

## 10. 研究工作台

| 模块 | 回答的问题 | 下钻目标 |
| --- | --- | --- |
| 事件头部卡片 | 事件是否重要、是否已确认？ | 事件元数据/事实源 |
| 多指标时间线 | 讨论、情绪和行情何时变化？ | 时间桶证据 |
| 观点簇 | 大家在争论什么、为什么？ | 原始帖子/新闻 |
| 情绪结构 | 谁对什么对象持何种立场？ | 对象级样本 |
| 传导路径 | 影响通过什么机制扩散？ | 边证据/知识记录 |
| 影响矩阵 | 优先研究哪些行业/公司？ | 评分计算与暴露证据 |
| 证据抽屉 | 每个结论的依据是什么？ | 完整原文与来源 |

## 11. Agent 与规则边界

| 问题类型 | 责任方 | 示例 |
| --- | --- | --- |
| 确定性计算 | 规则/代码 | 帖子量、增速、权重、阈值、风险分 |
| 高频模式识别 | 传统模型 | 去重、聚类、机器人、异常检测 |
| 开放式语义理解 | LLM | 观点、理由、情绪对象、候选机制 |
| 重大结论与外发 | 人工 | 确认传导、修改标签、发布报告 |

统一原则：规则决定系统“做什么以及何时做”；LLM 判断文本“意味着什么”；研究员决定结论“是否可信以及如何使用”。

## 12. 分析与评分

系统至少维护以下量化因子：事件可观测量、来源质量、扩散强度、市场相关性、潜在影响、行情反应、数据完整度、后验置信度和评分区间。Rule 3 的基础评分不得依赖 Agent 1/2 产物；Rule 4 在基础评分之上计算 `calibrated_score`、`confidence` 与 `score_interval`。

```text
raw_score(event, t)
 = f(X_event,
     X_source,
     X_diffusion,
     X_market)

calibration(raw_score, event, evidence_state)
 → calibrated_score, confidence, [lower_bound, upper_bound]
```

观点归因、情绪对象和传导假设可以进入报告解释、工作台展示和人工研究流程，但不能反向写入 Rule 3/4 的权威评分输入。

Agent 只能解释冻结的 Rule 3/4 结果，不能提出或写入任何覆盖 `raw_score`、`calibrated_score`、`confidence` 或评分区间的调分字段。

## 13. 关键 API

| 接口 | 用途 | 当前状态 |
| --- | --- | --- |
| POST /api/v1/ingestion/items | 服务账户提交严格 SourceRecord，幂等写入原始文档并返回接收回执 | 已实现；确定性处理为同步尽力执行，完成状态尚不可查询 |
| GET /api/events | 风险总览事件列表 | 已实现 |
| GET /api/events/{id}/workspace | 事件工作台聚合数据 | 已实现 |
| GET /api/events/{id}/evidence | 证据筛选 | 已实现 |
| GET /api/events/{id}/opinions | 观点归因只读查询 | 已实现 |
| GET /api/events/{id}/transmission | 传导候选只读查询 | 已实现 |
| POST /api/events/{id}/review | 人工确认/拒绝/备注 | 仅设计，未实现 |
| POST /api/events/{id}/reanalyze | 创建新分析版本 | 仅设计，未实现 |
| GET /api/entities/{id}/exposure | 实体风险暴露 | 仅设计，未实现 |
| POST /api/alerts/rules | 配置告警规则 | 仅设计，未实现 |
| POST /api/reports | 基于 snapshot 生成报告 | 仅设计，未实现 |

## 14. 数据与模型可追溯要求

- 原始数据保存 source_id、source_url、published_at、collected_at、received_at、可选 replay_at、collection_method 和 license_scope；每次投递另存 ingestion receipt。

- 模型输出保存 model_version、prompt_version、输入集合与输出 JSON。

- 指标保存 calculation_id、scoring_version、参数与输入集合。

- 报告保存 snapshot_id 和引用证据集合；之后系统更新不得改变历史报告含义。

- 人工修改保存完整审计日志。

## 15. 降级策略

| 故障 | 系统行为 |
| --- | --- |
| 某舆情源不可用 | 显示来源降级；剩余来源继续运行；降低覆盖度 |
| LLM 不可用 | 继续采集、事件检测、统计、告警；暂停语义层更新 |
| 行情源延迟 | 时间线标记数据延迟，不填充假数据 |
| 事实源不可用 | 事件可继续观察，但事实支持度和综合置信度封顶 |
| 报告生成失败 | 不影响事件工作台，允许重试 |

## 16. MVP 交付范围（黑客松/首版）

| 模块 | 必须 | 不做 |
| --- | --- | --- |
| 平台 | 桌面 Web + 一个通知渠道 | 原生手机 App |
| 数据 | 1 事实源 + 1 新闻源/历史新闻 + 1 舆情源 + 行情 | 全网实时抓取 |
| 事件 | 历史事件实时回放 + 聚类/热度 | 复杂跨事件因果推断 |
| Agent | Agent 1 事件标签 + Agent 2 观点归因/传导假设/报告生成 | 自由自治多 Agent 对话、Agent 直接给分 |
| UI | 总览 + 事件工作台 + 证据下钻 | 复杂自定义仪表板 |
| 输出 | 风险卡片 + CSV/JSON/HTML/PDF 其一 | 自动交易 |

## 17. 推荐开发顺序

1. 先建立统一 RawDocument、Event、Entity、Evidence 数据模型。

1. 实现历史数据回放、去重、事件聚类和热度时间线，先不要接 LLM。

1. 完成风险总览与事件工作台骨架，确保所有数据可下钻。

1. 实现 Rule 3 确定性评分和 Rule 4 后验评分校准，确保评分链在 Agent 接入前可复算。

1. 接入 Agent 1 Event Tagger，生成可校验、可审计的事件标签。

1. 接入 Agent 2 Analyze，将文本和知识记录转成观点归因、传导假设、评分解释和反向证据。

1. 冻结 AnalysisSnapshot 后，用 Agent 2 Render 生成报告，并完成导出和人工反馈闭环。

## 18. 端到端验收场景

1. 回放一个历史突发事件；系统在消息流进入后自动形成 Event。

1. Rule 1 将消息归入候选事件，Rule 2 输出 DROP / WAIT / ADMIT / ATTACH 决策；多源/高质量证据确认后 Event 进入 confirmed。

1. Rule 3 计算可复算 `raw_score`，Rule 4 生成 `calibrated_score`、`confidence` 和评分区间，并留下 calculation_id。

1. Agent 1 生成事件标签；Agent 2 Analyze 输出 3–5 个主要观点归因和至少一条 Event→Mechanism→Industry→Company 候选链，每条结论可下钻证据。

1. 告警规则触发并发送到一个外部渠道。

1. 研究员拒绝一条错误传导边并添加备注；系统保留版本。

1. 基于当前 snapshot 生成一份风险卡片；其中所有数字来自冻结评分字段，所有事实句均可追溯。

## 19. 四份专项文档之间的依赖

| 专项文档 | 负责回答 | 上游依赖 | 下游影响 |
| --- | --- | --- | --- |
| 01 平台形态与部署架构 | 在哪里运行、如何部署、用户怎么进入 | 产品目标 | 前后端、权限、通知 |
| 02 消息源与数据接入治理 | 数据从哪里来、如何统一和追溯 | 合规与供应商 | 事件引擎、证据层 |
| 03 研究工作台与可视化交互 | 研究员看到什么、如何下钻 | 数据模型、指标 | 前端实现、研究流程 |
| 04 Agent规则与模型边界 | 谁负责判断、谁负责计算 | 数据/知识/状态机 | 分析、评分、审计、成本 |

## 20. 第一阶段成功标准

第一阶段不是以“模型准确预测股票”为成功，而是证明以下流程成立：面对一个突发事件，研究员不再人工浏览数百条帖子和新闻，而能在统一工作台中快速看到规则评分、后验校准、主导观点、传导候选、影响对象和原始证据，并能对机器结论进行修正、复核和导出。
