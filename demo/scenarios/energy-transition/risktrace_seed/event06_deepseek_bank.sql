-- RiskTrace demo seed
-- Target event:
--   d6c8ee46-2ec3-432b-b43c-a6c6cb88370e
--   财联社《爆火仅半年，DeepSeek在银行业已“泯然众模型”？三大障碍成为拦路虎》
--
-- Purpose:
--   为单个事件补充 5 条模拟社交帖子与 5 条观点归因记录，
--   方便团队在本地 demo 中同步同一批展示数据。
--
-- Notes:
--   1. 仅适用于 demo tenant: aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa
--   2. 所有新增记录均显式标注 simulated / manual_demo_seed / internal_demo_only
--   3. 脚本按 source_id 幂等 upsert raw_documents，并重建这批 demo opinion_records
BEGIN;
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM events
        WHERE id = 'd6c8ee46-2ec3-432b-b43c-a6c6cb88370e'::uuid
          AND tenant_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid
    ) THEN
        RAISE EXCEPTION
            'Target event % for tenant % not found',
            'd6c8ee46-2ec3-432b-b43c-a6c6cb88370e',
            'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa';
    END IF;
END $$;
CREATE TEMP TABLE tmp_seed (
    document_id uuid PRIMARY KEY,
    opinion_id uuid NOT NULL,
    platform text NOT NULL,
    source_id text NOT NULL,
    published_at timestamptz NOT NULL,
    collected_at timestamptz NOT NULL,
    author_alias text NOT NULL,
    author_id_hash text NOT NULL,
    title text NOT NULL,
    raw_text text NOT NULL,
    content_hash text NOT NULL,
    likes integer NOT NULL,
    comments integer NOT NULL,
    reposts integer NOT NULL,
    stance text NOT NULL,
    emotion text NOT NULL,
    reason text NOT NULL,
    claim_type text NOT NULL,
    evidence_span text NOT NULL,
    model_confidence double precision NOT NULL,
    input_hash text NOT NULL
) ON COMMIT DROP;
INSERT INTO tmp_seed (
    document_id,
    opinion_id,
    platform,
    source_id,
    published_at,
    collected_at,
    author_alias,
    author_id_hash,
    title,
    raw_text,
    content_hash,
    likes,
    comments,
    reposts,
    stance,
    emotion,
    reason,
    claim_type,
    evidence_span,
    model_confidence,
    input_hash
)
VALUES
(
    'b850df8c-df78-4d43-a871-0c0993813899'::uuid,
    '2141dc5e-9f25-4b64-8869-57ae11357ed5'::uuid,
    'weibo',
    'demo-deepseek-bank-20250804-social-001',
    '2025-08-04T12:15:00Z'::timestamptz,
    '2025-08-04T12:15:00Z'::timestamptz,
    '金融科技从业者',
    'af95b8868589791c57150b4c9c78be36d133d9cf1635f7e8c31c9dfe3e88347c',
    '微博热议：半年就“泯然众模型”说明银行AI应用被严重高估',
    '这篇报道说得太真实了。半年前一堆银行发公告说接入DeepSeek，其实大部分就是部署了个API调一下，离真正的业务落地差十万八千里。金融数据太复杂、容错率太低，通用大模型根本扛不住。热潮退去才知道谁在裸泳。',
    'c79c3820e4c55e4d18eb244c9efe4adc5146208632e819b975631793ea353906',
    423,
    134,
    67,
    'bearish',
    'negative',
    '银行AI应用被严重高估，大部分仅部署API，离业务落地很远',
    'opinion',
    '热潮退去才知道谁在裸泳。',
    0.74,
    '3ad444cb840cf3d0531df9fd268130505523db3906c8df1836f65690f6988248'
),
(
    '561aadde-7535-4bd0-abce-a10c4342df3f'::uuid,
    '30b4cc7d-03e1-49b2-945a-e97d08e304a1'::uuid,
    'xueqiu',
    'demo-deepseek-bank-20250804-social-002',
    '2025-08-04T12:28:00Z'::timestamptz,
    '2025-08-04T12:28:00Z'::timestamptz,
    '银行IT老兵',
    '7579a812b6a1db68c5fb973fe560787b770cfa1213cd157f69de9d3bc3011be2',
    '雪球讨论：三大障碍里“数据复杂性”才是真正的死结',
    '三大障碍说得对但顺序不对。最致命的不是“通用vs专用”的问题，而是银行的数据根本喂不进大模型——信贷数据散在十几个系统里、格式不统一、还有大量非结构化文档。DeepSeek再强，垃圾进垃圾出。先解决数据治理再说AI。',
    '9b3a1b864a31a479c88b074803b7b5a1b2deeab6e6802dff561ccf4753c7c816',
    312,
    89,
    45,
    'bearish',
    'negative',
    '银行数据治理未解决前，大模型无法发挥价值（垃圾进垃圾出）',
    'opinion',
    'DeepSeek再强，垃圾进垃圾出。',
    0.72,
    'e851b9f1c36f2ff95a90594a1c35e5288ce218c1f61a6fde0a85783ff19e2a44'
),
(
    '3354c658-f9b3-4003-b482-a58b8adb74fc'::uuid,
    'd28e8b96-eb9c-41eb-86e9-6c7da0e6eb7c'::uuid,
    'eastmoney_guba',
    'demo-deepseek-bank-20250804-social-003',
    '2025-08-04T12:42:00Z'::timestamptz,
    '2025-08-04T12:42:00Z'::timestamptz,
    '炒概念的小散',
    '9bef892c59512382ce891ac832a293212a45dc126a5f821235b7b71f63c2b9ae',
    '股吧热帖：监管不让大银行宣传DeepSeek=自主研发才是方向',
    '“不得大规模宣传DeepSeek应用，金融大模型要突出自主研发”——这条信息才是核心。监管已经意识到金融AI不能依赖外部开源模型，必须走自主研发路线。这对有自研大模型的银行（工行、招行）是利好，对靠DeepSeek蹭概念的中小银行是利空。',
    '0eae33e611ef801be8a61d2c6582ed121d236b8a108858d0572e58cf6853b51a',
    289,
    76,
    38,
    'bullish',
    'optimistic',
    '监管要求金融大模型自主研发，利好有自研能力的银行',
    'opinion',
    '这对有自研大模型的银行是利好，对靠DeepSeek蹭概念的中小银行是利空。',
    0.7,
    '9a7304931b673e039d5c4be012eb8acdfb54ba6ce84ade7c21b3e65ecede7480'
),
(
    'ef7242e5-9dfa-46a5-aaa5-1d011d27bce3'::uuid,
    '58cd4589-469d-42f0-a287-10af90a89d73'::uuid,
    'weibo',
    'demo-deepseek-bank-20250804-social-004',
    '2025-08-04T12:55:00Z'::timestamptz,
    '2025-08-04T12:55:00Z'::timestamptz,
    '中小银行从业者',
    '0ea1eefc6770e31450a21971bd36386661fb6b667ba51b05e0729c15709e95c9',
    '微博讨论：DeepSeek解决了“有没有”但解决不了“好不好”',
    '杨磊说得对——DeepSeek帮中小银行解决了“有没有”的问题，但“好不好”还差得远。我们行去年接入了DeepSeek，结果AI投顾推荐的基金组合被客户投诉三次，最后下线了。免费的东西确实便宜，但金融业务不能用“便宜”来衡量。',
    'f31c66f61624d6d89e526f2b53d2d580d1132ea7374a36305eb5b69c6c4f9947',
    345,
    112,
    56,
    'bearish',
    'negative',
    'DeepSeek解决“有没有”但未解决“好不好”，金融业务不能用便宜衡量',
    'opinion',
    '免费的东西确实便宜，但金融业务不能用“便宜”来衡量。',
    0.71,
    '0258da6bad08fd122665fd792ed5f31a7f48d6960a2643dccb481c1236e34714'
),
(
    'a16f4e15-5b5b-49df-b8f0-a78e3735718a'::uuid,
    '6215d192-f62d-4f95-97ae-1f88eac90e62'::uuid,
    'xueqiu',
    'demo-deepseek-bank-20250804-social-005',
    '2025-08-04T13:08:00Z'::timestamptz,
    '2025-08-04T13:08:00Z'::timestamptz,
    'AI应用观察者',
    'ad17e0ea6bf262415ed0be1519f8d30436e5b5d976283336e0b51c60a175a08d',
    '雪球讨论：半年结论太早，AI在金融的渗透是3-5年的长周期',
    '说“泯然众模型”太早了。历史上每一轮技术从概念到落地都需要3-5年——云计算从2009年到2014年才真正普及。DeepSeek在银行的探索才半年，就像婴儿刚学走路就评判他能不能跑马拉松。现在的问题不是DeepSeek行不行，而是银行的组织架构和流程还没准备好。',
    '9f4c6354cce9a08ee0c7037807e8a6059c3df7d239ab27530c5109f29de6fbcb',
    267,
    82,
    34,
    'bullish',
    'optimistic',
    'AI在金融的渗透是3-5年长周期，半年评判太早',
    'opinion',
    '现在的问题不是DeepSeek行不行，而是银行的组织架构和流程还没准备好。',
    0.69,
    'e669cff46bf970f08a0f26e2a218505b22981831c98a4bacf558288c7d3b0c38'
);
INSERT INTO raw_documents (
    id,
    tenant_id,
    source_type,
    source_level,
    platform,
    source_id,
    source_url,
    published_at,
    collected_at,
    received_at,
    replay_at,
    author_id_hash,
    title,
    raw_text,
    language,
    engagement,
    is_original,
    collection_method,
    license_scope,
    content_hash,
    raw_payload_ref,
    source_metadata
)
SELECT
    seed.document_id,
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid,
    'social',
    'public_discussion',
    seed.platform,
    seed.source_id,
    NULL,
    seed.published_at,
    seed.collected_at,
    seed.collected_at,
    NULL,
    seed.author_id_hash,
    seed.title,
    seed.raw_text,
    'zh',
    jsonb_build_object(
        'likes', seed.likes,
        'comments', seed.comments,
        'reposts', seed.reposts
    ),
    TRUE,
    'manual_demo_seed',
    'internal_demo_only',
    seed.content_hash,
    NULL,
    jsonb_build_object(
        'simulated', TRUE,
        'seed_batch', 'demo-deepseek-bank-20250804',
        'author_alias', seed.author_alias,
        'note', 'Demo social post seeded for event workspace presentation only'
    )
FROM tmp_seed AS seed
ON CONFLICT ON CONSTRAINT uq_raw_documents_tenant_platform_source
DO UPDATE SET
    published_at = EXCLUDED.published_at,
    collected_at = EXCLUDED.collected_at,
    received_at = EXCLUDED.received_at,
    replay_at = EXCLUDED.replay_at,
    author_id_hash = EXCLUDED.author_id_hash,
    title = EXCLUDED.title,
    raw_text = EXCLUDED.raw_text,
    language = EXCLUDED.language,
    engagement = EXCLUDED.engagement,
    is_original = EXCLUDED.is_original,
    collection_method = EXCLUDED.collection_method,
    license_scope = EXCLUDED.license_scope,
    content_hash = EXCLUDED.content_hash,
    raw_payload_ref = EXCLUDED.raw_payload_ref,
    source_metadata = EXCLUDED.source_metadata
;
INSERT INTO event_documents (
    event_id,
    document_id,
    weight,
    similarity,
    source_weight,
    novelty,
    is_duplicate,
    duplicate_of_document_id
)
SELECT
    'd6c8ee46-2ec3-432b-b43c-a6c6cb88370e'::uuid,
    doc.id,
    0.92,
    0.86,
    0.88,
    0.42,
    FALSE,
    NULL
FROM tmp_seed AS seed
JOIN raw_documents AS doc
  ON doc.tenant_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid
 AND doc.platform = seed.platform
 AND doc.source_id = seed.source_id
ON CONFLICT ON CONSTRAINT uq_event_documents_pair
DO UPDATE SET
    weight = EXCLUDED.weight,
    similarity = EXCLUDED.similarity,
    source_weight = EXCLUDED.source_weight,
    novelty = EXCLUDED.novelty,
    is_duplicate = EXCLUDED.is_duplicate,
    duplicate_of_document_id = EXCLUDED.duplicate_of_document_id
;
DELETE FROM opinion_records AS opinion
USING raw_documents AS doc
JOIN tmp_seed AS seed
  ON seed.platform = doc.platform
 AND seed.source_id = doc.source_id
WHERE opinion.event_id = 'd6c8ee46-2ec3-432b-b43c-a6c6cb88370e'::uuid
  AND opinion.document_id = doc.id
  AND opinion.model_version = 'demo-manual-v1'
  AND opinion.prompt_version = 'seed-20260805';
INSERT INTO opinion_records (
    id,
    tenant_id,
    event_id,
    document_id,
    target_entity_id,
    stance,
    emotion,
    reason,
    claim_type,
    evidence_span,
    model_confidence,
    model_version,
    prompt_version,
    input_hash
)
SELECT
    seed.opinion_id,
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid,
    'd6c8ee46-2ec3-432b-b43c-a6c6cb88370e'::uuid,
    doc.id,
    NULL,
    seed.stance,
    seed.emotion,
    seed.reason,
    seed.claim_type,
    seed.evidence_span,
    seed.model_confidence,
    'demo-manual-v1',
    'seed-20260805',
    seed.input_hash
FROM tmp_seed AS seed
JOIN raw_documents AS doc
  ON doc.tenant_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid
 AND doc.platform = seed.platform
 AND doc.source_id = seed.source_id;
UPDATE events AS event
SET
    last_seen_at = GREATEST(
        event.last_seen_at,
        '2025-08-04T13:08:00Z'::timestamptz
    ),
    evidence_count = (
        SELECT COUNT(*)
        FROM event_documents
        WHERE event_id = event.id
    )
WHERE event.id = 'd6c8ee46-2ec3-432b-b43c-a6c6cb88370e'::uuid
  AND event.tenant_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid;
COMMIT;
