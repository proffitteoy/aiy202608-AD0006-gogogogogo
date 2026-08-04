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
| `apps/api/src/risktrace/db` | SQLAlchemy 元数据与持久化模型 | 绕过租户和审计边界 |
| `apps/api/migrations` | 可审查、可重放的数据库迁移 | 在应用启动时用 `create_all` 替代迁移 |
| `apps/api/tests` | 后端边界和行为验证 | 依赖生产服务或外部付费接口 |
| `compose.yaml` | 本机完整运行栈 | 存放生产凭据 |

## 3. 当前真实能力

- `/api/health/live` 只证明 API 进程存活，不声称依赖就绪。
- `/api/health/ready` 并行探测 PostgreSQL、Redis 和对象存储；任一失败即返回 HTTP 503 和明确降级状态。
- Web 通过 `/api/platform-status` 服务端代理读取真实后端状态；连接失败时展示“后端不可用”，不回退到模拟状态。
- 初始迁移建立 `raw_documents`、`events`、`entities`、`event_documents` 和 `evidence_links`，优先落地来源、租户与证据关系。

## 4. 尚未实现

- 登录、RBAC 与真实租户上下文。
- 历史事件数据导入、Adapter、checkpoint 和幂等流水线。
- 事件聚类、状态机、确定性评分与实时推送。
- 风险总览、事件工作台和证据检索业务页面。
- LLM 语义候选、报告和人工审核闭环。

在认证落地前，不新增会返回租户业务数据的公开接口。

## 5. 验证层次

1. 静态验证：Ruff、ESLint、TypeScript。
2. 单元验证：pytest 检查健康语义和核心元数据契约。
3. 构建验证：Next.js 生产构建和 Docker Compose 配置解析。
4. 运行验证：完整 Compose 启动后，同时检查 Web HTML、静态资源、API 存活与 API 就绪。

单独通过其中一层不能替代完整运行验证。
