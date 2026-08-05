# 开源组件提取边界

文档版本：v0.3  |  日期：2026-08-05  |  状态：Lean Runtime Baseline

本文记录 `docs/开源项目.md` 中当前阶段组件的实际提取结果。`第三方库` 只作为一次性输入；构建和运行路径不得引用该目录，删除它不应删除已提取实现。

## 已提取实现

| 上游项目 | 提取目标 | 提取内容 | 必要改动 | 当前验证状态 |
| --- | --- | --- | --- | --- |
| `pgvector/pgvector` 0.8.6 | `infra/pgvector` | C 扩展源码、SQL、Makefile、控制文件、Dockerfile、许可证 | Dockerfile 从远程 `ADD` 改为构建本目录源码；Compose 构建本地镜像 | Compose 已接线；迁移已新增无固定维度的事件中心字段，镜像尚未实际构建 |
| `huggingface/sentence-transformers` 5.7.0.dev0 | `apps/api/vendor/sentence-transformers` | `sentence_transformers` Python 包、模型卡模板、构建元数据、LICENSE/NOTICE | 无上游实现改动；RiskTrace 新增惰性适配器 | 由 `apps/api/uv.lock` 锁定为本地可选源；仅在执行 `npm run bootstrap:api:embeddings` 时安装，未下载模型权重 |
| `apache/echarts` 6.1.0 | `apps/web/vendor/echarts` | 已生成的 `echarts.esm.min.mjs`、RiskTrace 最小类型声明、LICENSE/NOTICE | vendor 包清单只公开本地 ESM 产物；删除构建不引用的上游 `src` | 已由 `package-lock.json` 锁定到本地路径，并用于工作台时间线 |
| `xyflow/xyflow` 12.11.2 / system 0.0.79 | `apps/web/vendor/xyflow-react`、`apps/web/vendor/xyflow-system` | React Flow、XYFlow System 源码和原始 CSS、许可证 | 新增指向原始 TypeScript 源码的 vendor 包清单，并由 Next.js 转译 | 已由 `package-lock.json` 锁定到本地路径，并用于工作台传导图 |

后端可选 embedding 依赖通过 `tool.uv.sources` 指向 `apps/api/vendor`，API Dockerfile 会在安装前
复制 vendor 目录，但默认 `uv sync --no-dev` 不安装该 extra。
PostgreSQL 镜像通过 `infra/pgvector` 本地构建，并由迁移 `20260804_0002` 启用 `vector`
扩展；Python 侧使用锁定的 `pgvector` SQLAlchemy 绑定，`20260804_0003` 保存事件聚类中心。

前端 `package.json` 和 `package-lock.json` 均指向 `apps/web/vendor`。ECharts 与 XYFlow 已由当前页面
源码实际导入；每次裁剪后仍须用 TypeScript 检查和 Next.js 生产构建验证本地包边界。

## 本次移除的预置组件

| 上游项目 | 移除原因 | 后续引入条件 |
| --- | --- | --- |
| `celery/celery` | 当前没有 Celery app、任务或 worker 服务，默认安装只会扩大依赖树 | 出现真实异步任务调用链，并补齐 worker、失败降级和运行验证 |
| `pydantic/pydantic-ai` / `pydantic-graph` | 当前没有 Agent 1/2 模型调用，业务源码没有导入 | 实现严格 schema、证据 ID 校验和降级路径时按实际最小依赖重新评估 |

## 没有在本阶段提取的项目

| 上游项目 | 原因 |
| --- | --- |
| `fastapi/full-stack-fastapi-template` | 当前仓库已落地 Next.js + FastAPI + SQLAlchemy + Alembic。模板的 Vite、SQLModel、同步数据库与认证组件不能直接放入现有调用链；本阶段不复制一套未使用的第二骨架。 |
| `langfuse/langfuse` | `docs/开源项目.md` 明确标记为第二阶段；当前没有真实 LLM 调用。 |
| `caronc/apprise` | 文档明确标记为后期接入；当前没有 Alert Engine。 |
| `akfamily/akshare` | `第三方库` 中没有对应源码，且 Market Adapter 尚未实现；不自行替代。 |

## 许可证

- ECharts 和 Sentence Transformers：Apache-2.0；对应 NOTICE 已随源码保留。
- React Flow：MIT。
- pgvector：PostgreSQL License。

集中索引、上游链接、版本和本地许可证路径见根目录
[`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md)。任何后续裁剪都必须保留仍分发组件的
LICENSE/NOTICE。若修改上游运行实现，需在本文记录文件、原因和差异；不能以 RiskTrace 自写代码
冒充上游组件。

## 尚未实现的业务能力

组件源码落库不等于业务能力已经实现：当前已有可选 embedding 适配器、向量字段、时间线和
传导图展示，但仍没有已选定/已下载的模型权重、异步任务编排或 LLM Agent。实现这些能力时
仍须遵守模型版本、证据 ID 校验、租户隔离和降级显示边界。
