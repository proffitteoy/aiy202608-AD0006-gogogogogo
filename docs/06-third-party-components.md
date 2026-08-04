# 开源组件落库边界

文档版本：v0.1  |  日期：2026-08-04  |  状态：Dependency Baseline

本文记录 `docs/开源项目.md` 中的采用建议如何映射到当前已经落地的 Next.js + FastAPI 工程。第三方源码目录只用于核对组件入口、版本与许可证；RiskTrace 不修改这些项目，也不复制其内部实现后另行维护。

## 当前提取结果

| 上游项目 | 本地参考快照 | 提取到 RiskTrace 的公开组件 | 接入方式 | 当前状态 |
| --- | --- | --- | --- | --- |
| `pgvector/pgvector` | `第三方库/pgvector-master`，0.8.6 | PostgreSQL `vector` 扩展 | Compose 使用官方 `pgvector/pgvector:0.8.6-pg17-trixie` 镜像 | 已声明，尚未新增 embedding 业务字段 |
| `huggingface/sentence-transformers` | `第三方库/sentence-transformers-main`，5.7.0.dev0 | Python 推理库 | API 依赖 `sentence-transformers` 5.x 稳定发行版 | 已声明，尚未选择模型或下载权重 |
| `pydantic/pydantic-ai` | `第三方库/pydantic-ai-main` | 类型安全 Agent 核心 | API 依赖最小包 `pydantic-ai-slim` 1.x | 已声明，尚未接入模型提供商 |
| `celery/celery` | `第三方库/celery-main`，5.6.2 | Celery + Redis transport | API 依赖 `celery[redis]` 5.6.x | 已声明，尚未创建业务任务或 worker 服务 |
| `apache/echarts` | `第三方库/echarts-master`，6.1.0 | ECharts 浏览器包 | Web 依赖 `echarts` 6.1.0 | 已声明，等待真实时间线/矩阵数据后使用 |
| `xyflow/xyflow` | `第三方库/xyflow-main`，12.11.2 | React Flow | Web 依赖 `@xyflow/react` 12.11.2 | 已声明，等待真实传导图数据后使用 |

上述项目均通过上游公开发行组件接入，而不是把完整仓库复制到 `apps/`。这样保留上游的构建、修复和许可证边界，也避免 RiskTrace 意外维护第三方库的内部代码。

## 没有在本阶段提取的项目

| 上游项目 | 原因 |
| --- | --- |
| `fastapi/full-stack-fastapi-template` | 当前仓库已经落地 Next.js、FastAPI、SQLAlchemy、Alembic 和 Compose。直接覆盖会引入 Vite/SQLModel 第二套骨架；模板继续只作为工程参考，不复制认证、CRUD 或页面代码。 |
| `langfuse/langfuse` | `docs/开源项目.md` 明确标记为第二阶段；待真实 LLM 调用出现后再接入。 |
| `caronc/apprise` | 文档明确标记为后期接入；当前尚无 Alert Engine。 |
| `akfamily/akshare` | `第三方库` 中没有对应源码快照，而且当前尚未建立 Market Adapter；不凭空补写或替代。 |

## 许可证与分发

- ECharts 和 Sentence Transformers 使用 Apache-2.0；ECharts 的上游发行物还包含 `NOTICE`。
- React Flow、Pydantic AI 和 Full Stack FastAPI Template 使用 MIT。
- Celery 使用 BSD-3-Clause。
- pgvector 使用 PostgreSQL License。

依赖锁文件记录实际安装的发行物和传递依赖。若未来从参考目录直接复制任何源码、资源或配置，必须同时复制对应许可证/NOTICE，并在本文记录精确来源路径和修改情况。

## 使用边界

- 现阶段只建立可复现依赖基线，不预建没有真实输入数据的图表、Agent、embedding、任务或通知演示。
- Sentence Transformers 模型名称、向量维度和权重来源必须在首个 embedding 流程实现时显式确定，并记录模型版本与输入哈希。
- Pydantic AI 输出仍必须经过 RiskTrace 服务端的 schema、实体 ID 和 evidence ID 校验；引入框架不改变 `docs/04-agent-rule-boundary.md` 的权限边界。
- Celery 只负责执行已经由业务层定义的任务，不承担事件状态、风险评分或告警级别判断。
