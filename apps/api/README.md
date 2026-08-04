# RiskTrace API

FastAPI 模块化后端。当前实现提供存活/就绪检查、基础设施真实探测以及第一批核心数据表迁移。

从仓库根目录运行：

```powershell
uv sync --project apps/api
uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
npm run dev:api
```
