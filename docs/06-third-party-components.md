# 开源组件提取边界

文档版本：v0.2  |  日期：2026-08-04  |  状态：Vendored Source Baseline

本文记录 `docs/开源项目.md` 中当前阶段组件的实际提取结果。`第三方库` 只作为一次性输入；构建和运行路径不得引用该目录，删除它不应删除已提取实现。

## 已提取实现

| 上游项目 | 提取目标 | 提取内容 | 必要改动 | 当前验证状态 |
| --- | --- | --- | --- | --- |
| `pgvector/pgvector` 0.8.6 | `infra/pgvector` | C 扩展源码、SQL、Makefile、控制文件、Dockerfile、许可证 | Dockerfile 从远程 `ADD` 改为构建本目录源码；Compose 构建本地镜像 | Compose 已接线；镜像尚未实际构建 |
| `celery/celery` 5.6.2 | `apps/api/vendor/celery` | `celery` Python 包、构建元数据、Redis extra 依赖定义、许可证 | 无实现改动 | 已由 `apps/api/uv.lock` 锁定为本地路径源 |
| `huggingface/sentence-transformers` 5.7.0.dev0 | `apps/api/vendor/sentence-transformers` | `sentence_transformers` Python 包、模型卡模板、构建元数据、LICENSE/NOTICE | 无实现改动 | 已由 `apps/api/uv.lock` 锁定为本地路径源；未下载模型权重 |
| `pydantic/pydantic-ai` 源码快照 | `apps/api/vendor/pydantic-ai-slim`、`apps/api/vendor/pydantic-graph` | `pydantic_ai` 与其必需的 `pydantic_graph` 实现、许可证 | 仅把依赖于上游 Git 标签的动态版本元数据改成相同的 vendored 内部版本；未改运行实现 | 已由 `apps/api/uv.lock` 锁定为本地路径源；未接入模型提供商 |
| `apache/echarts` 6.1.0 | `apps/web/vendor/echarts` | 完整 `src`、已生成的 `echarts.esm.min.mjs`、LICENSE/NOTICE | 新增只指向本地 ESM 产物的 vendor 包清单 | 已由 `package-lock.json` 锁定到本地路径；尚未接入页面 |
| `xyflow/xyflow` 12.11.2 / system 0.0.79 | `apps/web/vendor/xyflow-react`、`apps/web/vendor/xyflow-system` | React Flow、XYFlow System 源码和原始 CSS、许可证 | 新增指向原始 TypeScript 源码的 vendor 包清单，并由 Next.js 转译 | 已由 `package-lock.json` 锁定到本地路径；本地快照不含 `dist`，尚未执行安装或构建验证 |

后端依赖通过 `tool.uv.sources` 指向 `apps/api/vendor`，API Dockerfile 会在安装前复制 vendor 目录。PostgreSQL 镜像通过 `infra/pgvector` 本地构建，并由迁移 `20260804_0002` 启用 `vector` 扩展。

前端 `package.json` 和 `package-lock.json` 均指向 `apps/web/vendor`。锁文件已通过 JSON 解析与本地路径检查，但当前网络环境下依赖安装命令超时，因此没有执行 Next.js 构建；不能把“已锁定”描述为“已构建运行”。

## 没有在本阶段提取的项目

| 上游项目 | 原因 |
| --- | --- |
| `fastapi/full-stack-fastapi-template` | 当前仓库已落地 Next.js + FastAPI + SQLAlchemy + Alembic。模板的 Vite、SQLModel、同步数据库与认证组件不能直接放入现有调用链；本阶段不复制一套未使用的第二骨架。 |
| `langfuse/langfuse` | `docs/开源项目.md` 明确标记为第二阶段；当前没有真实 LLM 调用。 |
| `caronc/apprise` | 文档明确标记为后期接入；当前没有 Alert Engine。 |
| `akfamily/akshare` | `第三方库` 中没有对应源码，且 Market Adapter 尚未实现；不自行替代。 |

## 许可证

- ECharts 和 Sentence Transformers：Apache-2.0；对应 NOTICE 已随源码保留。
- React Flow、Pydantic AI：MIT。
- Celery：BSD-3-Clause。
- pgvector：PostgreSQL License。

任何后续裁剪都必须保留各 vendor 目录内的 LICENSE/NOTICE。若修改上游运行实现，需在本文记录文件、原因和差异；不能以 RiskTrace 自写代码冒充上游组件。

## 尚未实现的业务能力

组件源码落库不等于业务能力已经实现：当前仍没有 embedding 模型选择、向量字段、Celery 任务、LLM Agent、研究图表或传导图页面。实现这些能力时仍须遵守模型版本、证据 ID 校验、租户隔离和降级显示边界。
