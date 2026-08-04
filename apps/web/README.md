# RiskTrace Web

Next.js 桌面研究端。当前首页通过服务端代理读取 FastAPI 的真实就绪状态；依赖不可用时明确显示降级，不提供伪造业务数据。

ECharts 与 React Flow/XYFlow 的上游实现保存在 `vendor/`，并由 `package-lock.json` 记录本地路径。源码已经提取，但研究图表和传导图页面尚未实现。

从仓库根目录运行：

```powershell
npm run bootstrap
npm run dev:web
```
