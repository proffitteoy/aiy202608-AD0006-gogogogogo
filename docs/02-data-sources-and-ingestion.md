# 开发文档 02｜消息源、数据接入与治理

定义事实源、新闻源、舆情源、行情源的职责与统一数据契约

文档版本：v0.1  |  日期：2026-08-04  |  状态：MVP Engineering Baseline

| 关键决策：消息源不以“网站列表”组织，而以信息职能分层：事实源负责确认发生了什么，新闻源负责专业解释，舆情源负责市场叙事与情绪，行情源负责市场反应。 |
| --- |

## 1. 数据源分层

| 层级 | 回答的问题 | 典型来源 | 在系统中的地位 |
| --- | --- | --- | --- |
| 事实源 | 实际发生了什么？ | 交易所/公司公告、监管政策、政府文件、公司官方声明 | 最高事实权重 |
| 专业新闻源 | 专业媒体如何解释？ | 财经媒体、行业媒体、授权资讯 | 事件发现与背景补充 |
| 舆情源 | 市场参与者在担忧/期待什么？ | 微博、雪球、股吧、评论区、公众号文章 | 观点与情绪样本 |
| 行情源 | 价格和成交如何变化？ | 股票、行业指数、期货等行情 | 用于时间对齐和研究验证，不作为因果证明 |

## 2. MVP 数据源范围

- 事实源：至少一个上市公司/交易所公告源。

- 新闻源：至少一个可稳定、合规获取的财经新闻源；若无实时授权，使用历史事件数据集进行回放。

- 舆情源：微博或雪球二选一作为主舆情源，第二个来源作为扩展，不在 MVP 同时攻克。

- 行情源：日内分钟级或至少 5 分钟级价格/成交量数据，用于事件时间线。

## 3. 合规与接入原则

- 优先使用官方 API、授权数据供应商、公开 RSS/数据接口或已获许可的数据集。

- 不得将绕过登录、验证码、反爬或访问控制作为产品核心能力；采集方式必须记录 collection_method 与 license_scope。

- 原始文本保留时间、展示范围、二次分发能力按来源授权策略配置。

- 用户导出时区分“结构化分析结果”和“受版权限制的原文内容”；必要时只导出引用片段或 source_url。

## 4. 统一原始数据模型

```text
RawDocument {
  id: UUID
  tenant_id: UUID | null
  source_type: "fact" | "news" | "social" | "market"
  platform: string
  source_id: string
  source_url: string | null
  published_at: datetime
  collected_at: datetime
  author_id_hash: string | null
  title: string | null
  raw_text: string | null
  language: string
  engagement: {likes, comments, reposts, views}
  is_original: boolean | null
  collection_method: string
  license_scope: string
  content_hash: string
  raw_payload_ref: string | null
}
```

## 5. 数据处理流水线

```text
采集 Adapter
  → Schema 校验
  → 原始数据不可变落库
  → 文本标准化
  → 精确去重 / 近似去重
  → 垃圾与异常账号过滤
  → 实体初识别
  → 事件候选聚类
  → 写入标准化文档表
  → 触发事件引擎与分析任务
```

## 6. Source Adapter 接口

```text
interface SourceAdapter:
    name: str
    source_type: str

    def fetch(cursor, start_time, end_time) -> FetchBatch
    def normalize(raw_item) -> RawDocument
    def checkpoint(batch) -> Cursor
    def healthcheck() -> SourceHealth
```

- Adapter 只负责“取数 + 解析来源字段”，不得在 Adapter 内进行情绪判断或事件归因。

- 每批数据必须有 cursor/checkpoint，实现幂等重跑。

- 失败重试采用指数退避；连续失败触发 source_health 告警，而不是静默丢数据。

## 7. 去重与传播链

| 阶段 | 方法 | 输出 |
| --- | --- | --- |
| 精确去重 | source_id、canonical_url、content_hash | 重复记录标记 |
| 近似文本去重 | SimHash/MinHash/向量相似度 | duplicate_group_id |
| 转发/引用识别 | 平台元数据 + 文本规则 | parent_document_id |
| 聚合计数 | 同组仅保留代表文本，传播量单独统计 | unique_count / propagation_count |

## 8. 时间语义

- published_at 是分析主时间轴；collected_at 用于衡量采集延迟。

- 所有内部存储统一使用 UTC 时间戳，API 同时返回用户时区显示值；界面默认 Asia/Shanghai。

- 任何事件热度窗口必须基于 published_at，并在数据延迟过高时显示“样本不完整”状态。

## 9. 来源可信度与权重

来源权重只影响确定性聚合计算，不允许 LLM 自行修改。建议分离三种概念：source_reliability（来源历史可靠度）、document_confidence（该条内容真实性/清晰度）、engagement_quality（互动质量）。

```text
weighted_signal_i = semantic_score_i
                  × source_reliability_i
                  × document_confidence_i
                  × engagement_quality_i
```

## 10. 证据链与数据血缘

- 所有 LLM 输出必须引用 input_document_ids 或 knowledge_record_ids。

- 任何聚合指标必须生成 calculation_id，记录输入集合、算法版本、参数版本和计算时间。

- 任何事件摘要必须能回到 cluster_id → document_id → raw_payload_ref。

- 原始数据原则上不可原地修改；纠错通过派生字段和版本记录完成。

## 11. 数据质量监控

| 监控项 | 触发条件示例 | 处理 |
| --- | --- | --- |
| 采集延迟 | P95 > 5 分钟 | 标记源降级并告警 |
| 数据量异常 | 较历史基线下降 > 80% | 检查 Adapter/授权 |
| 重复率异常 | 近似重复 > 90% | 检查转发洪峰或抓取重复 |
| 解析失败 | 单批 > 5% | 隔离 bad records |
| 时钟异常 | published_at 明显晚于 collected_at | 纠正/隔离 |
| 来源健康 | 连续 N 次失败 | 停止下游置信度提升 |

## 12. 数据表建议

| 表 | 主要字段 |
| --- | --- |
| raw_documents | 原始标准化文档 |
| documents_enriched | 语言、实体、重复组、质量标签 |
| events | 事件主表与状态 |
| event_documents | 事件—文档关联及权重 |
| entities | 行业、公司、商品、政策实体 |
| market_bars | 行情时间序列 |
| evidence_links | 结论—证据关系 |
| source_health | 数据源延迟、错误率、状态 |

## 13. MVP 验收标准

1. 四类数据至少覆盖事实/新闻/舆情/行情中的三类，且统一进入 RawDocument。

1. 任一 Adapter 重跑同一时间区间不会制造不可控重复记录。

1. 事件页面展示的原始证据可以还原来源、发布时间和采集时间。

1. 近似重复的转发文本不会按独立观点重复计数。

1. 数据源故障时系统能明确显示“数据不完整/来源降级”，而不是继续输出满置信度结论。
