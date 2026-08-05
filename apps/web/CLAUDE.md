# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

@AGENTS.md

## 定位

`apps/web` 是 RiskTrace 桌面 Web 工作台（Next.js 16 App Router + React 19），是一个 **monorepo 子项目**，仓库根在 `../../`。前端只做展示与研究员本地状态；权威评分、事件识别、观点归因、传导候选全部来自后端 FastAPI（`apps/api`）。**前端不得计算风险评分，也不得用浏览器 mock 补齐后端未产出的字段——降级 / 未生成状态必须显式呈现。**

根仓库的 `README.md`、`AGENTS.md`（项目协作约定）和 `docs/03-research-workbench.md`（工作台交互契约）是本前端所有决策的上位文档，出现冲突以它们为准。

## 常用命令

在**仓库根目录**运行；根 `package.json` 是所有命令的入口：

```powershell
# 起本地基础设施（Postgres 17 + Redis + MinIO），首次或换分支后需要
npm run infra:up
npm run migrate                   # alembic upgrade head（后端表）

# 独立跑前端 / 后端两个进程
npm run dev:web                   # Next.js dev @ 3000
npm run dev:api                   # uvicorn --reload @ 127.0.0.1:8000

# 静态检查（前端）
npm run lint:web                  # eslint .
npm run typecheck:web             # tsc --noEmit
npm run build:web                 # next build

# 全套：前端 lint + typecheck + build + 后端 ruff/pytest + demo ruff/unittest
npm run check
```

在 `apps/web/` 本目录也可以直接跑 `npm run dev / lint / typecheck / build`，脚本转发到根命令。

**没有前端单元测试框架**——`package.json` 里没有 `test` 脚本。前端功能验证走浏览器 + `typecheck` + `build`；后端 API 契约由 `pytest`（在根 `npm run test:api`）保证。

## 与后端接线的关键路径

前端连接后端有**两条通道**，二者不可混用：

1. **Server Component / Route Handler** 走 `apiFetch()`（`src/lib/api/client.ts`），直连 `RISKTRACE_API_URL`（默认 `http://127.0.0.1:8000`）。GET 请求默认 `next: { revalidate: 30 }` 走 Next.js 数据缓存；写请求 `cache: "no-store"`。
2. **Client Component** 只能走同源反向代理 `/api/backend/[...path]`（`src/app/api/backend/[...path]/route.ts`），避开 CORS 并隐藏内网地址。

`RISKTRACE_ALLOW_MOCK_FALLBACK=true` 时，后端不可达才允许回退到本地样例（`isMockFallbackAllowed()`）；**默认不允许，宁可显示"接口降级"**。

## 三层数据模型（拒绝在页面里直接用后端字段）

数据流严格分层，跨层禁止直连：

```
后端 Pydantic Schema (BackendXxx)              — src/lib/api/backend-types.ts
    │  adapters.ts
    ▼
前端展示契约 (EventSummary / EventDetail 等)   — src/lib/types.ts
    │  loaders.ts
    ▼
LoadResult<T> = ready | degraded | not_found | unavailable
```

- **`backend-types.ts`**：镜像后端 Pydantic schema，字段名 snake_case，包含 `BackendEventSummary / BackendTimelineBucket / BackendWorkspaceResponse / BackendOpinionItem / BackendTransmissionEdge / PaginatedResponse<T>`。
- **`types.ts`**：前端展示契约。命名 `Availability = "available" | "not_generated" | "degraded"` 是前端语义层的核心——每块面板都得处理这三态。
- **`adapters.ts`**：唯一的翻译层。所有"从桶算时间线情绪均值"、"从边聚合影响矩阵"这种衍生计算都在这里，不下沉到组件。
- **`loaders.ts`**：server-side 入口。返回 `LoadResult<T>`，页面根据 status 分支渲染。

**新增 API 调用的正确顺序**：`backend-types.ts` 加类型 → `events.ts` 加 fetcher → `adapters.ts` 加 adapter → `loaders.ts` 加 loader → 页面用 loader。

## 组件树的三个约定

1. **默认 Server Component**。`"use client"` 只在需要状态、effect、事件、浏览器 API 时加；`WorkbenchGrid` / `Timeline` / `TransmissionGraph` / `OpinionCluster` / `ReportModal` 是必然的 client。
2. **面板可放大**：Workbench 四个面板（`timeline / clusters / graph / impact`）通过 `WorkbenchGrid` 的 `ExpandContext` 共享放大态，`<WorkbenchPanel id={PanelId}>` 是纪律接口——新加面板必须扩 `PanelId` union。
3. **图表 resize 靠 `useResize` + gated mount**：ECharts / ReactFlow 的 `chart.resize()` 必须在容器已挂载后触发；Timeline / ImpactMatrix 都把 chart 抽成子组件（`ready === true` 才 mount），否则 `useResize` 的 useEffect 在 `containerRef.current === null` 时挂空。**新加图表面板照抄这个模式。**

## 前端本地状态（研究员研判）

`useOpinionDecisions`（`src/hooks/use-opinion-decisions.ts`）把观点的"纳入 / 排除 / 标记"决策存 `localStorage`，key `risktrace:opinion-decisions:v1`。**没有对应后端 endpoint**——如果后端将来出 `/api/opinions/{id}/decision`，把 hook 内部换成 mutation 即可，调用方 API 不动。ReportModal 也读这个 hook，用于研报里分三组展示观点。

## 已知踩过的坑

- **Next.js 16 是 breaking 版本**：文件里那句 "This is NOT the Next.js you know" 不是玩笑。碰到路由/中间件/元数据 API 时先看 `node_modules/next/dist/docs/`，别按训练数据里的旧 API 写。
- **`vendor/` 是仓库内置源码依赖**：`echarts / @xyflow/react / @xyflow/system` 都是 `file:vendor/...`，不是 npm 拉的。`tsconfig.json` 的 `exclude` 里加了 `"vendor"`——**别把它移除**，否则 `tsc --noEmit` 会淹没在第三方源码错误里。
- **`.tsbuildinfo` 增量缓存**：本地 tsc 用 `--incremental`，第一次冷启慢；PostToolUse hook 建议保留 `--tsBuildInfoFile` 到 `node_modules/.cache/` 里。
- **打印样式**：全局 print 规则里有 `body:has([data-report-root]) > :not([role="dialog"]) { display: none }`——ReportModal 打印时靠这条隐藏页面其余部分。新加 modal-like overlay 时注意别误伤。
- **打开报告模态时 body 会被锁滚动**（`document.body.style.overflow = "hidden"`）；`ReportModal` 卸载时恢复。任何新的全屏遮罩沿用同一模式。

## 设计基调

- **调色板与字体走 CSS 变量**：`globals.css` 里已经定义 `--surface-0..3 / --text-primary/secondary/tertiary / --risk-high/mid/low / --viz-1..8 / --font-serif/sans/mono / --space-1..9 / --dur-* / --ease-*`。**不要在组件里硬编码颜色和字号**，一律引用变量。
- **三态字体**：Sans（Inter / PingFang）= 主 UI；Serif（Source Serif / Noto Serif SC）= **只**用在事件标题、章节标题、报告正文这几处；Mono（JetBrains Mono）+ `data-numeric` 属性 = 所有数字与时间戳，靠 `font-variant-numeric: tabular-nums` 对齐。
- **图表配色不用 `oklch()`**：`src/lib/chart-theme.ts` 里 ECharts 用十六进制的 `chartPalette`，因为 zrender 对 CSS Color 4 支持不稳。想给图表加色请写 hex。

## 提交惯例

- 前端锁文件是 `apps/web/package-lock.json`（npm）；后端是 `apps/api/uv.lock`。改依赖必须同时提交对应锁文件。
- 根仓库的 `AGENTS.md` 有一条铁律："不用假数据掩盖依赖、来源或模型不可用；缺失、延迟和降级必须成为显式状态"——前端所有 fallback UI 都要遵守。
