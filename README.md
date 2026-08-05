<p align="center">
  <img src="apps/web/public/mark.svg" width="88" height="88" alt="RiskTrace 标志">
</p>

<h1 align="center">RiskTrace</h1>

<p align="center">
  <strong>金融事件 × 社交情绪 × 市场传导的可追溯研究平台</strong>
</p>

<p align="center">
  <img alt="项目状态：MVP 工程基线" src="https://img.shields.io/badge/status-MVP%20Engineering%20Baseline-B7791F">
  <img alt="Next.js 16" src="https://img.shields.io/badge/Next.js-16-000000?logo=nextdotjs&amp;logoColor=white">
  <img alt="Python 3.13" src="https://img.shields.io/badge/Python-3.13-3776AB?logo=python&amp;logoColor=white">
  <img alt="FastAPI" src="https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&amp;logoColor=white">
  <a href="LICENSE"><img alt="MIT License" src="https://img.shields.io/badge/license-MIT-2F855A.svg"></a>
</p>

> 将突发事件后的海量信息浏览，压缩为事件识别、风险评分、观点归因、传导候选与证据复核流程。当前仓库处于 **MVP 工程基线阶段**，不提供自动交易，也不构成投资建议。

## 团队分工

| 成员 | 负责方向 |
| --- | --- |
| 李炫良 | 架构设计 |
| 林昭漫 | 后端开发 |
| 陈泽江 | 测试 |
| 吴思霖 | 市场调研 |
| 林楠浚 | 前端设计 |

## 项目概览

RiskTrace 面向证券研究员、资管研究团队和风险研究岗位，围绕“事件是什么、市场在讨论什么、风险如何变化、影响可能如何传导、结论依据哪些证据”组织研究流程。

系统坚持三条边界：确定性程序负责可复算的状态与评分，LLM 只输出经过约束的语义候选，重大结论与对外内容由研究员最终确认。行情与舆情的同步变化只表示时间相关，不自动解释为因果关系。

### 当前实现状态

| 模块 | 状态 | 说明 |
| --- | --- | --- |
| 工程基线 | 已实现 | Next.js Web、FastAPI API、PostgreSQL / Redis / MinIO 编排及真实就绪探测 |
| 事件与证据 | 后端源码已实现 | 固定研究场景幂等导入器，以及事件列表、工作台聚合、证据与文档查询 API |
| 事件引擎 | 内核已实现 | `event-match-v1`、`admission-v2`、`confirmation-v2`、去重、聚类中心、热度、动量与生命周期规则；尚未接入自动采集和后台调度 |
| Rule 3/4 评分链 | 内核已实现 | `deterministic-scoring-v1` 与 `score-calibration-v1` 可复算并有迁移记录；拒绝 Agent 分数输入，尚未接入业务 API 和前端 |
| 语义候选 | 数据结构与查询已实现 | OpinionRecord / TransmissionEdge 候选持久化结构和固定 Demo 租户查询已提供；Agent 1/2 生成实现按评分链前置条件暂缓 |
| 历史数据回放 | 来源侧已实现 | 3 个真实 DOCX 场景可转换、隔离坏记录并按可控时钟回放；统一 ingestion API 尚未接线 |
| 研究工作台 | 尚未实现 | 当前 Web 只展示真实基础设施状态，不展示伪事件；风险总览、图表、传导图和证据下钻仍待接线 |

## 本地演示

按下文快速启动完整本地栈后，可访问：

- Web 状态页：<http://localhost:3000>
- API 交互文档：<http://localhost:8000/api/docs>
- API 存活检查：<http://localhost:8000/api/health/live>
- API 就绪检查：<http://localhost:8000/api/health/ready>
- MinIO 控制台：<http://localhost:9001>

当前 Web 首屏用于验证 Web → FastAPI → PostgreSQL / Redis / MinIO 的真实运行链路，不代表完整研究工作台已经交付。事件、证据和语义候选查询接口以 API 文档中的实际路由为准。

### 历史资料转换与回放

`demo/data` 中的三份历史资料通过来源侧转换器生成标准 SourceRecord JSONL；缺失发布时间的记录会进入 rejected 结果，不会被静默补值。当前可验证入口为：

```powershell
npm run demo:list
npm run demo:convert
npm run test:demo
```

回放状态机、checkpoint 和 HTTP 发送端已经实现；由于统一 ingestion 路由尚未在 FastAPI 中落地，当前只完成了 dry-run 和发送端契约测试，未完成真实 API/数据库端到端验证。详细数据质量与命令见 [Demo 历史回放说明](demo/README.md)。

## 技术栈

| 层 | 技术 |
| --- | --- |
| Web | Next.js 16、React 19、TypeScript |
| API | Python 3.13、FastAPI、SQLAlchemy、Alembic |
| 事件与评分 | 版本化 Python 规则、Sentence Transformers、pgvector |
| 语义层预留 | Pydantic AI（已落库，Agent 1/2 生成实现暂缓） |
| 数据与基础设施 | PostgreSQL 17、Redis 8、MinIO、Docker Compose |
| 质量检查 | ESLint、TypeScript、Next.js Build、Ruff、pytest |

ECharts、React Flow、Celery、Sentence Transformers、Pydantic AI 和 pgvector 等组件已按仓库边界落库，但“源码或依赖已存在”不等于对应业务能力已经接线。详情见 [开源组件提取边界](docs/06-third-party-components.md)。

## 快速开始

### 环境要求

- Node.js 22 或更高版本
- npm 10 或更高版本
- uv（安装并管理 Python 3.13 环境）
- Docker 与 Docker Compose

### 启动完整本地栈

```powershell
Copy-Item .env.example .env
docker compose up --build
```

首次启动会构建镜像、创建本地数据卷与 `risktrace` 对象存储桶，并执行数据库迁移。`.env.example` 中的凭据只适用于本机开发，生产环境必须替换。

停止服务但保留本地数据：

```powershell
npm run infra:down
```

> `docker compose down -v` 会同时删除本地数据库、缓存和对象存储卷，请勿将其作为普通停止命令。

### 分进程开发

安装并锁定前后端依赖：

```powershell
npm run bootstrap
```

启动基础设施并执行迁移：

```powershell
npm run infra:up
npm run migrate
```

随后在两个终端分别运行：

```powershell
npm run dev:api
npm run dev:web
```

## 验证

```powershell
npm run check
docker compose config --quiet
```

`npm run check` 依次执行前端 ESLint、TypeScript 检查、生产构建、后端与 Demo Ruff、后端 pytest，以及 Demo 回放单元测试。`/api/health/live` 只表示 API 进程存活；数据库、缓存和对象存储是否可用必须以 `/api/health/ready` 为准。

## 目录结构

```text
RiskTrace/
├── apps/
│   ├── api/                  FastAPI、规则内核、数据模型、迁移与测试
│   └── web/                  Next.js 桌面 Web
├── demo/                     历史资料转换、SourceRecord 场景与可控回放
├── docs/                     产品与工程设计基线
├── infra/                    本地基础设施组件
├── .env.example              本地配置示例
├── compose.yaml              完整本地栈编排
├── package.json              根命令入口
├── AGENTS.md                 项目协作与安全边界
└── LICENSE                   MIT License
```

详细边界见 [仓库结构与运行契约](docs/05-repository-structure.md)。

## 后续计划

- 将固定研究场景、现有事件/证据 API 与前端工作台接成可下钻的演示闭环。
- 接入合规数据源、checkpoint、幂等重跑和明确的来源降级状态。
- 将事件引擎与 Rule 3/4 评分内核接入持久化业务调用链和后台任务。
- 实现 AnalysisSnapshot、风险总览、事件工作台、告警、导出与人工复核。
- 按顺序实现 Agent 1 Event Tagger、Agent 2 Analyze 和基于 Snapshot 的 Agent 2 Render。
- 在企业化阶段补齐认证、真实多租户隔离与完整审计。

## 设计文档

- [总开发文档](docs/README.md)：产品定义、端到端流程、对象模型与 MVP 范围。
- [平台形态与部署架构](docs/01-platform-architecture.md)：产品形态、服务边界、基础设施与 SLO。
- [消息源、数据接入与治理](docs/02-data-sources-and-ingestion.md)：数据源、统一契约、幂等接入和血缘。
- [研究工作台与可视化交互](docs/03-research-workbench.md)：页面体系、证据下钻和版本化研究操作。
- [Agent、规则与模型边界](docs/04-agent-rule-boundary.md)：确定性规则、传统模型、LLM 与人工职责。
- [项目协作约定](AGENTS.md)：实现、测试、文档和安全规则。

## 版权与许可

Copyright © 2026 李炫良、林昭漫、陈泽江、吴思霖、林楠浚。

除各文件或目录另有许可说明外，本项目自有代码与文档采用 [MIT License](LICENSE) 开源。`apps/*/vendor` 与 `infra/pgvector` 中的第三方组件不受根目录 MIT License 覆盖，其版权归各自权利人所有，并适用对应目录内的 `LICENSE` / `NOTICE`。
