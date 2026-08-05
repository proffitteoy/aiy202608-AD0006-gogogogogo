# 开发文档 05｜仓库结构与运行契约

文档版本：v0.1  |  日期：2026-08-04  |  状态：Implemented Engineering Baseline

## 1. 结构决策

RiskTrace 当前采用一个仓库、两个应用的轻量结构，不拆分微服务：

```text
浏览器
  → apps/web（Next.js，同源状态代理）
  → apps/api（FastAPI 模块化单体）
  → PostgreSQL / Redis / MinIO
```

`apps/api` 内部继续按 HTTP API、核心配置、数据库模型和后续业务模块分层。采集、事件、评分、证据、通知和报告先作为同一后端内的模块演进，只有出现独立扩缩容或故障隔离证据后才考虑拆分服务。

## 2. 当前目录职责

| 路径 | 职责 | 禁止事项 |
| --- | --- | --- |
| `apps/web/src/app` | 页面、同源 API 代理与视觉状态 | 计算权威风险分数、暴露服务密钥 |
| `apps/api/src/risktrace/api` | HTTP 路由与输入输出契约 | 直接堆积业务规则或数据库细节 |
| `apps/api/src/risktrace/core` | 配置和基础设施健康检查 | 承载金融语义判断 |
| `apps/api/src/risktrace/db` | SQLAlchemy 元数据与持久化模型 | 绕过固定 Demo 上下文或后续租户边界 |
| `apps/api/src/risktrace/events` | 事件准入、匹配、去重、指标与生命周期纯规则 | 发起网络调用、信任 LLM 直接裁决或隐藏缺失因子 |
| `apps/api/src/risktrace/scoring` | Rule 4 后验校准、置信度、区间与持久化映射 | 读取 Agent 产物、覆盖 Rule 3 基础分或用重复传播提高置信度 |
| `apps/api/migrations` | 可审查、可重放的数据库迁移 | 在应用启动时用 `create_all` 替代迁移 |
| `apps/api/tests` | 后端边界和行为验证 | 依赖生产服务或外部付费接口 |
| `apps/api/vendor` | 已提取的后端第三方实现与许可证 | 修改上游运行逻辑后不记录差异 |
| `apps/web/vendor` | 已提取的前端可视化源码、构建产物与许可证 | 把尚未接入的组件描述为已运行 |
| `infra/pgvector` | pgvector 0.8.6 本地镜像构建源码 | 运行时回指一次性 `第三方库` 目录 |
| `compose.yaml` | 本机完整运行栈 | 存放生产凭据 |

## 3. 当前真实能力

- `/api/health/live` 只证明 API 进程存活，不声称依赖就绪。
- `/api/health/ready` 并行探测 PostgreSQL、Redis 和对象存储；任一失败即返回 HTTP 503 和明确降级状态。
- Web 通过 `/api/platform-status` 服务端代理读取真实后端状态；连接失败时展示“后端不可用”，不回退到模拟状态。
- 初始迁移建立 `raw_documents`、`events`、`entities`、`event_documents` 和 `evidence_links`，优先落地来源、租户与证据关系。
- 第二个迁移启用本地构建的 pgvector 扩展；第三个迁移新增事件聚类中心、准入记录、时间桶指标与平台基线。
- 事件规则内核已实现 `event-match-v1`、`admission-v2`、`confirmation-v2`、`deterministic-scoring-v1` 和生命周期规则，并有单元测试。
- 第四个迁移保留 `OpinionRecord` 与 `TransmissionEdge` 结构化对象；旧的独立 Agent 写入入口已退出 API。
- 第五个迁移把 Rule 2 字段校准为 `decision_value`，并新增 Rule 4 校准记录；`score-calibration-v1` 可纯函数复算，但尚未接入业务调度。
- 事件、工作台聚合、证据、文档、观点和传导只读 API 已存在，并由服务端固定 Demo tenant 过滤。
- Sentence Transformers 适配器只在显式配置模型后惰性加载；仓库没有模型权重，当前应用启动不会隐式下载模型。

## 4. 尚未实现

- 生产级登录、RBAC 与真实多租户上下文。
- 合规历史 fixture、通用 Adapter、cursor/checkpoint、拒绝记录和来源降级流水线；当前只有固定 seed importer。
- 历史导入或实时消息到事件引擎的持久化调用路径，以及 Celery 指标调度。
- Evidence 到 Rule 3/4 输入的数值映射、Data Completeness 聚合与 AnalysisSnapshot。
- Rule 3/4 的业务 API、前端页面与实时推送；当前纯规则模块并不等于端到端自动评分已运行。
- 风险总览、事件工作台和证据检索业务页面。
- Agent 1 Event Tagger、Agent 2 Analyze/Render、报告和人工审核闭环。

Demo 业务查询已经使用服务端固定 demo context，前端不能传入任意 `tenant_id` 改变数据范围。Demo 不实现登录、角色、成员管理或权限后台；生产级认证和真实多租户隔离留到企业化阶段。

## 5. 验证层次

1. 静态验证：Ruff、ESLint、TypeScript。
2. 单元验证：pytest 检查健康语义和核心元数据契约。
3. 构建验证：Next.js 生产构建和 Docker Compose 配置解析。
4. 运行验证：完整 Compose 启动后，同时检查 Web HTML、静态资源、API 存活与 API 就绪。

单独通过其中一层不能替代完整运行验证。
