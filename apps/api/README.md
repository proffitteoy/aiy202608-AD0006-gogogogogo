# RiskTrace API

FastAPI 模块化后端。当前实现提供存活/就绪检查、基础设施真实探测、固定场景导入器、
只读事件/证据查询、核心追溯表，以及第一版确定性事件与评分内核。

事件引擎位于 `src/risktrace/events`，包含：

- Rule 2 `DROP / WAIT / ADMIT / ATTACH` 准入规则与低可信高影响候选保护；
- 语义、实体、时间和事件类型复合匹配，以及来源加权的在线聚类中心；
- 与事件匹配分离的精确哈希和 SimHash 近似去重；
- 热度、增长异常、来源熵、动量和显式数据完整度；
- 不使用 Agent 产物的 Rule 3 `raw_score`，以及 Rule 4 后验校准分、置信度和区间；
- 事实/新闻/社交分层的 `confirmation-v2`，传播速度不参与事实确认；
- `candidate → confirmed → active → cooling → closed` 生命周期规则。

Sentence Transformers 通过可选的惰性适配器接入；默认 API 安装不包含其 PyTorch/Transformers
依赖，启用前需执行 `npm run bootstrap:api:embeddings`，并显式提供本地模型路径或可取得的模型名。
仓库不附带模型权重。pgvector 用于保存事件中心和按租户检索候选事件。当前已有固定 seed
导入和服务端固定 Demo tenant 的只读业务 API。`POST /api/v1/ingestion/items` 已提供
Bearer 服务账户写入：服务端决定 tenant 和 provider scope，按来源 ID 幂等保存 `RawDocument`，
每次投递追加 `IngestionReceipt`。首次写入会同步尽力执行确定性 Rule 1/2、Event、Metric 和
Rule 3/4 持久化；该阶段失败会回滚并记录日志，但接入记录仍保留。响应目前固定为
`pending_enrichment`，尚无处理状态查询、可靠重试或后台调度。Agent 1/2 也尚未实现。

Sentence Transformers 的上游实现保存在 `vendor/`，`uv.lock` 使用本地可选路径源；默认安装和
容器构建不会安装该可选依赖。当前没有 Celery worker 或 Agent 1/2 运行调用链，因此 Celery、
Pydantic AI Slim 与 Pydantic Graph 未保留在依赖或 vendor 目录中。安装和容器构建不依赖根目录的
`第三方库`。

从仓库根目录运行：

```powershell
uv sync --project apps/api
uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
npm run dev:api
```

写接口运行前必须配置 `RISKTRACE_INGESTION_API_TOKEN`、`RISKTRACE_INGESTION_TENANT_ID`
和 `RISKTRACE_INGESTION_ALLOWED_PROVIDERS`。请求体不能携带 tenant、event、sentiment、topic
或 risk 等下游权威字段；完整示例见根 `README.md`。
