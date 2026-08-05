# RiskTrace 历史回放数据源

本目录实现历史资料的来源侧转换与回放，不包含第二套事件分析逻辑。DOCX 资料被转换成统一
`SourceRecord`，再由 `DemoReplayProvider` 按发布时间顺序投递到统一 ingestion API；事件归类、
准入、评分和后续分析仍由 RiskTrace 主链路负责。

## 当前边界

| 能力 | 状态 | 说明 |
| --- | --- | --- |
| DOCX 转换 | 已实现 | 使用 Python 标准库读取 OOXML，不依赖 Office 或 `python-docx` |
| SourceRecord JSONL | 已实现 | 稳定 ID、UTC 时间、内容哈希、来源层级和原始段落血缘 |
| 不合格记录隔离 | 已实现 | 写入 `rejected.jsonl`，不静默补造发布时间 |
| 固定间隔回放 | 已实现 | 支持 start/pause/resume/stop/reset/seek/set_speed |
| checkpoint | 已实现 | 成功投递后才推进 cursor；运行状态写入根 `runtime/demo/` |
| HTTP 投递 | 已实现 | URL 可配置并发送 Bearer token；2xx 的 `outcome=duplicate` 为幂等成功，409 内容冲突会停止回放 |
| 统一 ingestion API | 后端源码已实现 | `/api/v1/ingestion/items` 已挂载；本次尚未完成真实数据库回放联调 |
| 事件/评分/Agent | 不在本目录实现 | 必须复用后端统一流水线 |

## 数据结构

```text
demo/data/*.docx
  -> manifest.json + DOCX converter
  -> records.jsonl / rejected.jsonl
  -> DemoReplayProvider
  -> configurable HTTP sink
  -> Unified Ingestion API
```

场景目录：

```text
demo/scenarios/
├── deepseek-r1/
├── energy-transition/
└── real-estate-policy/
```

三份源文档共有 24 条候选记录。当前转换接受 22 条，隔离 2 条缺失发布时间的记录：DeepSeek
GitHub 仓库页和能源场景知乎文章。全部场景均明确标记 `market=unavailable`、互动量不可用、
舆情样本稀疏；不得据此生成价格曲线或统计性市场情绪结论。

所有资料的许可凭证均未随 DOCX 提供，因此 `license_scope` 固定为
`unknown_internal_demo_only`。生成数据只适用于内部演示和接入联调，不能据此认定原文允许二次分发。

## 命令

从仓库根目录执行：

```powershell
npm run demo:list
npm run demo:convert
npm run lint:demo
npm run test:demo
```

不连接后端、以 JSONL 检查实际投递载荷：

```powershell
uv run --project demo python demo/src/risktrace_demo_cli.py replay deepseek-r1 `
  --dry-run --interval-ms 1 --no-checkpoint
```

真实投递前配置与后端一致的 token，并确保 provider 在后端允许列表中：

```powershell
$env:RISKTRACE_INGESTION_API_TOKEN = "<本地接入 token>"
uv run --project demo python demo/src/risktrace_demo_cli.py replay deepseek-r1 `
  --endpoint http://127.0.0.1:8000/api/v1/ingestion/items --interval-ms 1000 --reset
```

HTTP 客户端已与当前路由契约对齐；在迁移、数据库和 API 实际启动并完成回放前，不能把端到端
接入标记为已验证。

`npm run demo:list` 会列出每个场景实际使用的 provider；启动 API 前，应把目标场景的这些值加入
`RISKTRACE_INGESTION_ALLOWED_PROVIDERS`。不应使用 `*` 绕过服务账号的来源范围。

`convert --strict` 在存在 rejected 记录时返回退出码 2，适合数据质量门禁；普通 `convert` 会保留
rejected 明细并继续产出其余合法记录。

## 时间与幂等语义

- `published_at`：原来源发布时间，作为排序和分析主时间轴。
- `collected_at`：DOCX 汇编记录的采集日期；只有日期精度，原值和精度保留在 metadata。
- `received_at`：统一 ingestion 服务真正接收请求的时间，由服务端生成，Demo 不传入。
- `replay_at`：Demo 释放该记录的时间，由回放端随 SourceRecord 传入。

日期统一按 Asia/Shanghai 解读后转换为 UTC。仅日期的记录规范到本地当日 00:00，同时保留
`published_at_precision=date`；人工审核过的推断日期额外标记 `published_at_inferred=true` 和依据。

`external_id` 由承载平台和规范来源 URL 稳定派生；HTTP 请求同时发送 `Idempotency-Key`。
checkpoint 只记录下一条 cursor，不删除或修改已被后端接收的原始数据，因此 reset/replay 依赖统一
ingestion API 的幂等约束。

## 投递契约

投递载荷只包含来源事实：`external_id`、`source`、发布时间/采集时间/回放时间、标题、正文、URL
和采集元数据。`received_at` 由服务端生成，不属于客户端载荷。
不得加入 `tenant_id`、`event_id`、`sentiment`、`risk` 或 `topic`。固定 Demo tenant 由服务端上下文
决定；事件和评分由统一规则链生成。

生成的 `records.jsonl` 与 `apps/api/src/risktrace/ingestion/schemas.py` 中的 `SourceRecord` 字段对齐；
HTTP 发送时只在 `SourceRecord.to_ingestion_payload()` 增加当前 `replay_at` 和回放序号。正式路由仍应
复用该 schema，不能让 Demo 改写转换或分析逻辑。
