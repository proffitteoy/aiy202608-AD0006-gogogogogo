# RiskTrace API

FastAPI 模块化后端。当前实现提供存活/就绪检查、基础设施真实探测以及第一批核心数据表迁移。

Celery、Sentence Transformers、Pydantic AI Slim 与 Pydantic Graph 的上游实现保存在 `vendor/`，`uv.lock` 使用本地路径源；安装和容器构建不依赖根目录的 `第三方库`。

从仓库根目录运行：

```powershell
uv sync --project apps/api
uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
npm run dev:api
```
