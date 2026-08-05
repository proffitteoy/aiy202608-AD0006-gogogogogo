# RiskTrace Web

Next.js 桌面研究端。当前实现直接读取 FastAPI 的事件、工作台、证据、观点和传导只读契约；
后端不可达或产物尚未生成时明确显示 unavailable/degraded，不回退到本地 mock。

已接线页面包括 Risk Overview、Event Workspace、文档量时间线、Rule 3/4 评分展示、观点归因、
传导假设和只读证据抽屉。ECharts 与 React Flow/XYFlow 的上游实现保存在 `vendor/`，并由
`package-lock.json` 记录本地路径。影响矩阵、Agent 生成、AnalysisSnapshot 和报告 Render 尚未实现，
页面不会在浏览器中启发式补造这些结果。

从仓库根目录运行：

```powershell
npm run bootstrap
npm run dev:web
```

最小静态验证：

```powershell
npm run lint:web
npm run typecheck:web
npm run build:web
```
