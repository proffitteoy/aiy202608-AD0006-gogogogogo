# 开发文档 07｜当前状态评估与纵向交付计划

文档版本：v0.2  |  日期：2026-08-05  |  状态：Delivery Baseline

本文把当前仓库实现与产品、架构、数据、工作台和 Agent 文档交叉比对，回答两个问题：RiskTrace 现在真实完成了什么，以及怎样形成第一条可演示、可验证的业务闭环。

> 当前实现说明：固定场景 importer、事件/证据只读 API、事件规则内核和 Rule 3/4 纯算法已经落库；
> 但自动导入到事件引擎、评分持久化调度和前端工作台仍未接线。规则单元测试不能替代端到端验收。

评估基线为当前 `main` 与本工作区。百分比是用于排序的阶段性判断，不是测试覆盖率、里程碑验收率或工时进度。

| 核心判断：RiskTrace 已建立质量较好的工程基线，但尚未形成业务纵向切片。当前首要风险已经从“架构失控”转为“继续扩充基础设施而迟迟没有产品闭环”。 |
| --- |

## 1. 当前阶段结论

RiskTrace 不是空壳。仓库已有双应用结构、真实依赖就绪检查、固定场景导入器、只读业务 API、事件规则、Rule 3/4 评分内核和追溯迁移；它仍不能称为 MVP 产品，因为这些后端能力尚未串成浏览器可操作的研究闭环。

更准确的定性是：

> 后端纵向切片已形成若干段，浏览器端产品闭环尚未形成。

阶段性完成度可按以下口径理解：

| 维度 | 估计 | 仓库事实 | 解释 |
| --- | ---: | --- | --- |
| 工程基础设施 | 70% | Next.js、FastAPI、Compose、PostgreSQL、Redis、MinIO、Alembic、检查入口均已落库 | 指工程基线完成度，不代表完整栈已在本次评估中运行验证 |
| 数据模型 | 70% | 已有 RawDocument、Event、Evidence、Opinion、Transmission、Metric 与 ScoreCalibration | EventTag、AnalysisSnapshot、Report 和 Alert 尚未落库 |
| 业务后端 | 45% | 固定 importer、只读业务 API、Rule 1/2/3/4 与生命周期纯规则已实现 | 自动导入、持久化编排、后台调度和写入 API 尚未形成 |
| 研究工作台 UI | 5% | 首页只展示真实平台状态和系统边界 | 风险总览、事件工作台、时间线和证据抽屉尚未实现 |
| Agent / LLM | 0% | Agent 1/2 仅有设计与预留依赖；旧独立 Agent 执行入口已移除 | 依赖可用性不计为产品能力 |
| 完整 Demo 闭环 | 15–20% | 后端可导入固定场景并查询事件/证据，Web 仍只显示基础设施状态 | 尚不能从浏览器演示消息如何转化为研究结果 |

整体约为 35–40%，只适合作为方向性判断。后续不再以仓库文件数、第三方源码量或基础设施组件数衡量产品完成度，而以端到端验收场景是否成立衡量。

## 2. 已经做对的事情

### 2.1 模块化单体方向正确

当前实际结构与 `01-platform-architecture.md`、`05-repository-structure.md` 一致：

```text
Next.js Web
  → FastAPI 模块化单体
  → PostgreSQL / Redis / MinIO
```

采集、事件、评分、证据、通知和报告继续作为同一后端内部模块演进。没有独立扩缩容或故障隔离证据前，不拆微服务，不引入 Kafka、Kubernetes 或复杂自治多 Agent 编排。

### 2.2 产品主链与权责边界正确

`docs/README.md` 定义的主链不是“新闻 → LLM → 风险分”，而是：

```text
Source Adapters
  → Raw Store
  → Normalization / Dedup / Quality
  → Rule 1 事件归类 / 匹配
  → Rule 2 入库管理
  → Event
  → Rule 3 确定性评分
  → Rule 4 后验评分校准
  → Agent 1 事件标签
  → Agent 2 Analyze 观点归因 / 传导假设 / 评分解释
  → Evidence Validation
  → AnalysisSnapshot
  → Workspace / Alert / Export / Human Review
  → Agent 2 Render 报告生成
```

`04-agent-rule-boundary.md` 又把职责限定为：规则和代码负责确定性计算、状态、基础评分和后验校准；传统模型负责高频模式识别；LLM 只输出语义候选、标签、解释和报告文本；研究员负责重大结论和外发。这是 RiskTrace 成为研究工具而不是 AI 包装层的关键。

### 2.3 追溯模型先于语义层落地

当前 ORM 和第一份迁移真实包含：

- `RawDocument`
- `Event`
- `Entity`
- `EventDocument`
- `EvidenceLink`

`RawDocument` 已覆盖来源、发布时间、采集时间、作者哈希、原文、互动、采集方式、许可范围、内容哈希和原始载荷引用；`(platform, source_id)` 有唯一约束。这为以下链路提供了数据库基础：

```text
研究结论
  → EvidenceLink
  → RawDocument
  → 原始帖子 / 新闻 / 公告
```

当前可以称为“追溯数据结构和只读查询已实现”，不能称为“证据下钻产品已实现”，因为前端入口和交互仍不存在。

## 3. 与既有文档的交叉比对

| 主题 | 既有文档已定义 | 代码已实现 | 当前缺口 | 结论 |
| --- | --- | --- | --- | --- |
| 产品形态 | 桌面 Web Demo，移动端只做轻入口 | Next.js 首页和 FastAPI 单体 | 业务页面、通知 | 方向一致，产品入口尚未形成 |
| 基础设施 | PostgreSQL、Redis、对象存储、Compose | 编排、配置和真实就绪探测 | 本评估未重跑完整 Compose；第三方文档仍记录部分构建未验证 | 已定义并部分实现，运行状态需逐次验证 |
| 原始数据契约 | 四类来源、统一 `RawDocument`、UTC、来源许可 | ORM、迁移与固定 seed importer 已有主要字段和幂等检查 | 合规 fixture schema、拒绝记录、通用 Adapter 和来源降级 | 固定回放基础已存在，通用接入未完成 |
| 幂等与去重 | cursor/checkpoint、精确与近似去重 | importer 检查来源键/content hash，规则层有精确与近似去重 | cursor、duplicate group 持久化和传播链 | 当前只覆盖固定场景，不等于生产流水线幂等 |
| Event | 聚类、热度、状态机、历史回放同引擎 | Event 表、复合匹配、聚类中心、热度、确认与生命周期纯规则 | 消息到规则再到数据库的运行编排 | Event Engine 内核已实现，端到端未接线 |
| 研究工作台 | 总览、时间线、观点、传导、影响矩阵、证据 | 首页仅展示平台就绪状态 | 全部业务视图和交互 | #003 先交付总览、最小工作台和证据抽屉 |
| 业务 API | `/api/events`、`/{id}/workspace`、`/{id}/evidence` 等 | 事件、工作台聚合、证据、文档及结构化分析只读查询已实现 | 评分查询、写入流程与前端消费 | 既有契约已开始落地，不另造平行接口体系 |
| 风险评分 | Rule 3 版本化确定性评分、Rule 4 后验校准与 `calculation_id` | `deterministic-scoring-v1`、`score-calibration-v1`、迁移和测试已实现 | 真实特征映射、持久化调用、API/UI 和历史回放 | 算法内核已实现，不等于业务评分已运行 |
| Agent / LLM | Agent 1 事件标签、Agent 2 观点归因/传导假设/报告及严格证据校验 | 第三方依赖、Opinion/Transmission 数据结构和只读查询 | Agent 1/2 调用、schema 校验、降级、Snapshot 与评估 | 旧独立 Agent 写入入口已移除，按新顺序实现 |
| Demo 访问模型 | 服务端固定 Demo 上下文，不做角色系统 | 所有业务查询使用服务端固定 tenant 过滤 | 写操作审计和未来真实租户上下文 | Demo 不实现登录、角色和权限后台 |

### 3.1 对原始建议的三处校正

1. **`#003` 与 `#004` 继续分责。** 固定场景 importer 和只读 API 不得宣称自动事件发现；只有消息无需预绑定即可经过 Rule 1/2、聚类、热度和状态机并持久化，才算 Event Engine 运行链完成。

2. **业务接口已使用固定 Demo 上下文。** Demo 不实现登录、角色或权限后台；服务端依赖提供固定 tenant，前端不能传入任意 `tenant_id` 决定数据范围。

3. **API 继续复用既有契约。** `GET /api/events`、`GET /api/events/{id}/workspace`、`GET /api/events/{id}/evidence`、事件详情和文档详情已存在；后续评分与 Snapshot API 应在同一资源体系下扩展。

## 4. 立即生效的开发策略

继续冻结横向基础设施扩张：

- 不新增数据库、中间件、消息系统、Agent 框架或大体量第三方源码。
- 已 vendored 的 Celery、Sentence Transformers、Pydantic AI、ECharts、XYFlow 和 pgvector 暂不推翻，但“存在于仓库”不计为已接入。
- 只有当前纵向切片出现可复现阻塞，并证明现有能力无法解决时，才讨论新增依赖。
- LLM 在历史回放、Event、时间线、证据下钻和 Rule 3/4 评分链通过验收前保持关闭。
- 历史 fixture 必须有来源说明、采集/整理方式、许可范围和时间语义；不能使用看似真实但无法追溯的假数据。
- 每个提交以可运行的业务结果为边界，避免把迁移、后端、前端拆成长期互不可用的半成品。

下一条必须证明的产品链是：

```text
historical_event.jsonl
  → RawDocument schema 校验
  → 幂等导入 / 精确去重
  → 已知历史 Event 与文档关联
  → 事件列表 / 时间线 API
  → Risk Overview
  → Event Workspace
  → Evidence Drawer
```

## 5. `#003`：Historical Replay & Evidence Slice

### 5.1 目标

让一个合规、可追溯的历史事件第一次完整穿过数据库、后端接口和前端页面。这个提交验证“证据闭环和产品形态”，不验证自动事件发现、LLM 语义理解或风险预测。

### 5.2 实现范围

#### 历史场景与数据契约

- 建立一个历史事件 fixture 目录，包含事件清单、`historical_event.jsonl` 和来源/许可说明。
- 初始数据至少覆盖事实、新闻、舆情三类；行情若无法合法、稳定取得，显式标记缺失，不填 0、不伪造曲线。
- 解析并校验现有 `RawDocument` 契约；内部统一 UTC，展示默认 Asia/Shanghai。
- 不合格记录进入可观察的 rejected 结果，包含行号和原因，不静默跳过。

#### 导入与幂等

- 提供一个明确的导入入口和汇总结果：读取数、写入数、重复数、拒绝数。
- `(platform, source_id)` 作为来源级幂等键；`content_hash` 用于发现跨 ID 内容重复，不直接覆盖原始记录。
- 同一 fixture 连续导入两次，第二次不得新增 `RawDocument`、`Event` 或重复关联。
- `#003` 允许由 fixture 的显式场景标识创建一个已知 Event；页面必须标记为“历史回放”。

#### 服务端 Demo 上下文

- 建立服务端固定 demo tenant/context，不做登录页、RBAC、Token scope 或成员管理。
- 所有事件、工作台和证据查询都使用固定 demo context 过滤，拒绝用前端传入的 `tenant_id` 直接决定数据范围。
- 这一阶段可以公开 Demo 只读业务接口；如果支持人工修改或导出，至少记录时间和输入快照。

#### API 与 UI

- `GET /api/events`：返回历史回放事件列表、来源结构、文档数和更新时间。
- `GET /api/events/{id}/workspace`：第一版只返回事件头部、数据质量和文档数量时间线；未实现字段明确为空或 unavailable。
- `GET /api/events/{id}/evidence`：按来源、平台、时间桶分页读取原始证据。
- Risk Overview：展示真实导入事件，不展示风险分、情绪分或虚构状态。
- Event Workspace：展示事件信息、热度时间线、来源结构和关联实体的已知部分。
- Evidence Drawer：从事件或时间桶打开对应 `RawDocument`，显示来源、发布时间、采集时间、原文/许可状态。

### 5.3 验收门槛

1. 空库导入一次成功，重复导入数据行数和关联数不增长。
2. 一条 schema 错误记录被拒绝并给出稳定错误原因；其余合法记录继续处理或按明确的原子批策略回滚。
3. 浏览器可从事件总览进入工作台，点击时间桶后看到对应原始证据。
4. 页面每个数量都能由数据库查询复核；缺失行情或来源显示为缺失/降级。
5. 请求中传入任意 `tenant_id` 不会改变返回数据范围。
6. 不存在 LLM 调用、Celery 任务、embedding 或权威风险分数。

## 6. `#004`：Event Engine

### 6.1 目标

把 `#003` 的“已知场景回放”升级为“消息逐条进入后自动形成 Event”，并让热度和状态转换可复算。

### 6.2 实现范围

- 引入可控的 replay clock，按 `published_at` 加速注入同一历史数据。
- 完成文本标准化、精确去重和满足演示需求的近似去重；独立样本数与传播量分离。
- 以确定性规则和轻量传统方法形成事件候选；LLM 最多在后续负责命名，不能参与状态转换。
- 生成版本化时间桶：总量、独立样本数、来源结构、采集延迟和完整性状态。
- 落地最小状态机：`candidate → confirmed → active → cooling → closed`；`confirmed` 由事实/新闻/独立来源等证据确认规则推动，热度不等于事实确认。
- `#003` 页面改为消费 Event Engine 结果，不保留一套演示专用计算路径。

### 6.3 验收门槛

1. 同一输入、时钟和规则版本得到相同事件、时间桶和状态轨迹。
2. 消息无需 fixture 预写 event ID 即可自动形成目标 Event。
3. 重复/转发洪峰不会被计算成相同数量的独立观点样本。
4. 达到确认规则阈值后 Event 自动进入 `confirmed`；达到监控/热度阈值后进入 `active` 并出现在总览。
5. 每个时间桶可下钻到输入文档集合；延迟或缺失来源降低完整性，不伪造满置信度。

## 7. `#005`：Rule 3/4 Scoring & Calibration（内核已实现，待接线）

### 7.1 前置条件

纯算法、迁移和单元测试已经先行实现；只有 `#004` 的去重、Event、证据 ID、状态机和降级路径通过运行验收后，才允许把评分链接入业务调度。评分链必须先于 Agent，并以 `04-agent-rule-boundary.md` 的 Rule 3/4 边界为权威契约。

### 7.2 实现范围

- Rule 3 只使用事件可观测量、来源结构、扩散结构、行情反应和数据完整度计算 `raw_score`。
- Rule 4 基于 `raw_score` 与后验证据状态输出 `calibrated_score`、`confidence`、`lower_bound` 和 `upper_bound`。
- 每次计算保存 `calculation_id`、`scoring_version`、`calibration_version`、参数和输入文档集合。
- 告警规则可以消费冻结评分字段，但不得从前端或 Agent 输出读取权威分数。
- UI 可以展示评分和区间，但必须显式标记数据缺失、来源降级和置信度封顶。

### 7.3 验收门槛

1. 相同输入集合、规则版本和时钟得到相同 `raw_score`、`calibrated_score`、`confidence` 和区间。
2. `calculation_id` 可追溯到输入文档集合和参数版本。
3. LLM 关闭时评分、告警和证据浏览仍正常运行。
4. 缺失行情、事实源或来源降级不会被填成 0 或伪造满置信度。

## 8. `#006`：Agent 1 Event Tagger

### 8.1 前置条件

需要 `#005` 的评分链通过验收，且已有可引用的 Event、证据 ID 和实体候选。Agent 1 不得修改 Event 状态、评分或告警级别。

### 8.2 实现范围

- 输入为已入库 Event、Rule 3/4 评分结果、代表证据和实体候选。
- 输出 `EventTag`：事件短名称、事件类型、主体、动作、对象、事实陈述和不确定陈述。
- 服务端校验 schema、实体 ID、证据 ID 和枚举；无效输出进入 degraded，不写权威字段。
- UI 可展示事件标签和事实/不确定陈述，每个陈述必须可下钻证据。

### 8.3 验收门槛

1. 不存在的 evidence/document/entity ID 被拒绝并记录。
2. 关闭 LLM 后，导入、事件、评分、告警和证据浏览继续可用并显示语义层降级。
3. Agent 1 输出不能修改 `raw_score`、`calibrated_score`、Event 状态或告警级别。
4. 相同分析版本可重现相同输入集合；模型版本和提示词版本有记录。

## 9. `#007` 以后：完成 MVP 闭环

在前三个业务切片稳定后，再按既有总开发文档推进：

| 提交主题 | 主要结果 | 关键门槛 |
| --- | --- | --- |
| `#007` Agent 2 Analyze | 观点归因、评分解释、传导假设和反向证据 | 输出只引用有效 evidence/knowledge/calculation ID；不改 Rule 3/4 分数 |
| `#008` 人工审核与快照 | 观点/传导审核、研究备注、analysis version、snapshot | Snapshot 冻结 Event、Score、Calibration、Tags、Agent 2 结构化分析、Evidence 和版本 |
| `#009` Agent 2 Render 与导出 | 基于冻结 snapshot 生成风险卡片和 CSV/JSON/HTML 中至少一种 | 所有数字来自冻结字段，事实句有 evidence ID |
| `#010` MVP 演示加固 | 至少 10 个历史回放事件、固定 Demo 上下文、一个可选外部通知渠道、性能与故障演练 | 满足 `01-platform-architecture.md` 与 `docs/README.md` 的端到端验收场景 |

编号表示推荐的可审查交付顺序，不要求机械地一项只对应一个 Git 提交；若某项过大，应继续拆分，但每个合并点必须保持可运行。

## 10. 每个后续切片的统一完成定义

一个切片只有同时满足以下条件才算完成：

1. **文档已定义**：输入、输出、Demo 上下文、降级和非目标明确。
2. **代码已实现**：真实调用路径使用该能力，不是孤立脚本或未接线组件。
3. **测试已验证**：至少覆盖正常路径、幂等/复算、失败降级和越权边界。
4. **运行已验证**：从实际入口触发，检查 API、数据库结果、页面和静态资源；不能只以 health endpoint 代替。
5. **证据可下钻**：页面结论、时间桶、观点或传导边能回到 `evidence_id` 或 `calculation_id`。
6. **缺失不伪造**：未接入来源、行情、模型或企业权限能力显示 unavailable/degraded，不用假数据补齐。

## 11. 当前剩余风险

- 完整 Compose 和 vendored 依赖的构建状态具有环境依赖，执行每个切片前仍需现场预检，不能沿用旧结论。
- 当前 `RawDocument.tenant_id` 可空，而其他业务对象多数不可空；Demo 导入可以使用固定 demo tenant/context，不应临时用空值绕过后续边界。
- `(platform, source_id)` 是全局唯一约束；Demo 阶段先按固定数据集处理，未来多租户共享原始文档时再单独设计。
- 现有 Event 状态枚举多于 `#004` 首版状态机；未启用状态必须保持不可达或有明确转换规则。
- 当前第三方源码显著放大仓库体积和依赖面；在形成产品闭环前继续 vendoring 会增加维护、许可证和供应链审查成本，却不会提高演示完成度。

## 12. 下一步唯一优先事项

下一次业务开发应完成 Historical Replay & Evidence Slice 的剩余部分：把合规 fixture、现有 importer/只读 API 与 Risk Overview、Event Workspace、Evidence Drawer 接成浏览器可下钻链路。完成之前不接 LLM、不新增基础设施，也不以静态 mock 页面替代真实导入与证据查询。

当评委能看到一个历史事件逐步出现、点击时间桶查看真实来源文档，并理解“这些数量从哪里来”时，RiskTrace 才第一次从工程仓库变成可解释的产品。
