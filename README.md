# RiskTrace

RiskTrace 是面向证券研究员、资管研究团队和风险研究岗位的“金融事件—社交情绪—市场传导”可追溯研究平台。目标是把突发事件后的海量信息浏览，压缩为事件识别、观点归因、传导候选、风险优先级判断与证据复核流程。

## 当前状态

仓库已经完成 MVP 工程结构初始化：

- `apps/web`：Next.js / React / TypeScript 桌面 Web 入口。
- `apps/api`：Python 3.13 / FastAPI 模块化后端、SQLAlchemy 核心模型与 Alembic 迁移。
- `compose.yaml`：PostgreSQL、Redis、MinIO、API 和 Web 的本地完整编排。
- `apps/*/vendor` 与 `infra/pgvector`：从已核对上游项目提取的组件源码、构建产物和许可证。
- 真实运行链路：Web 同源代理 → FastAPI 就绪接口 → PostgreSQL / Redis / MinIO 探测。
- 事件引擎内核：已实现版本化的事件准入、复合相似度、去重、加权聚类中心、热度/动量/风险与生命周期纯规则，并新增可追溯迁移。

当前页面不会展示伪事件数据。事件引擎内核尚未接入历史导入、后台任务、业务 API
和研究工作台，因此还不能声称消息已经能自动形成事件；LLM 语义层也仍未接入。

## 环境要求

- Node.js 22 或更高版本
- npm 10 或更高版本
- uv（负责安装和管理 Python 3.13 环境）
- Docker 与 Docker Compose

## 快速启动完整本地栈

```powershell
Copy-Item .env.example .env
docker compose up --build
```

启动后访问：

- Web：<http://localhost:3000>
- API 文档：<http://localhost:8000/api/docs>
- API 存活检查：<http://localhost:8000/api/health/live>
- API 就绪检查：<http://localhost:8000/api/health/ready>
- MinIO 控制台：<http://localhost:9001>

首次启动会构建镜像、创建基础设施卷、创建 `risktrace` 对象存储桶并执行数据库迁移。根 `.env.example` 中的凭据只适用于本机开发，生产环境必须替换。

停止服务：

```powershell
npm run infra:down
```

如需同时删除本地数据库、缓存和对象存储卷，必须明确执行 `docker compose down -v`；该操作会删除本地运行数据，因此不包含在普通停止命令中。

## 分进程开发

安装并锁定前后端依赖：

```powershell
npm run bootstrap
```

启动基础设施并迁移数据库：

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

`npm run check` 会依次运行前端 ESLint、TypeScript 检查、生产构建、后端 Ruff 和 pytest。依赖就绪状态必须通过 `/api/health/ready` 验证；仅有 `/api/health/live` 成功不代表数据库、缓存和对象存储可用。

## 目录结构

```text
RiskTrace/
├── apps/
│   ├── api/                  FastAPI、核心模型、迁移与测试
│   └── web/                  Next.js 桌面 Web
├── infra/                    从上游源码提取的基础设施组件
├── docs/                     产品与工程设计基线
├── .env.example              本地配置示例
├── compose.yaml              完整本地栈
├── package.json              根命令入口
└── AGENTS.md                 项目协作与安全边界
```

详细边界见 [仓库结构与运行契约](docs/05-repository-structure.md)。

## 设计文档

- [总开发文档](docs/README.md)：产品定义、端到端流程、对象模型与 MVP 范围。
- [平台形态与部署架构](docs/01-platform-architecture.md)：Web 产品、服务边界、基础设施、权限与 SLO。
- [消息源、数据接入与治理](docs/02-data-sources-and-ingestion.md)：数据源、RawDocument、幂等接入和数据血缘。
- [研究工作台与可视化交互](docs/03-research-workbench.md)：页面体系、证据下钻、人工操作和版本化。
- [Agent、规则与模型边界](docs/04-agent-rule-boundary.md)：确定性规则、传统模型、LLM 和人工的职责。
- [开源组件落库边界](docs/06-third-party-components.md)：第三方参考项目的实际依赖、延期项与许可证边界。
- [项目协作约定](AGENTS.md)：实现、测试、文档与安全规则。

## 下一实现切片

下一步应围绕一条历史事件回放链路展开：实现 `RawDocument` 的 schema 校验与幂等导入，
把真实消息接入现有事件引擎，持久化热度时间桶，再提供从事件下钻到原始证据的最小页面。
此阶段仍不接入 LLM，避免在数据契约和证据链尚未成立前扩展语义层。
