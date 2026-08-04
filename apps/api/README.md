# RiskTrace API

FastAPI 模块化后端。当前实现提供存活/就绪检查、基础设施真实探测、核心追溯表，
以及第一版确定性事件引擎内核。

事件引擎位于 `src/risktrace/events`，包含：

- `DROP / ATTACH / CANDIDATE / CREATE` 准入规则与低可信高影响候选保护；
- 语义、实体、时间和事件类型复合匹配，以及来源加权的在线聚类中心；
- 与事件匹配分离的精确哈希和 SimHash 近似去重；
- 热度、增长异常、来源熵、动量、风险和显式数据完整度；
- `candidate → confirmed → active → cooling → closed` 生命周期规则。

Sentence Transformers 通过惰性适配器接入；必须显式提供本地模型路径或可取得的模型名。
仓库不附带模型权重。pgvector 用于保存事件中心和按租户检索候选事件。当前还没有导入任务、
Celery 调度、业务 API 或页面调用这套内核。

Celery、Sentence Transformers、Pydantic AI Slim 与 Pydantic Graph 的上游实现保存在 `vendor/`，`uv.lock` 使用本地路径源；安装和容器构建不依赖根目录的 `第三方库`。

从仓库根目录运行：

```powershell
uv sync --project apps/api
uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
npm run dev:api
```
