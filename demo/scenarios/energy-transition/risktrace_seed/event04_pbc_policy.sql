-- RiskTrace demo seed
-- Target event:
--   3ea356d1-922f-4182-884c-bb2e0dcffd0a
--   中国人民银行《2024年中国货币政策大事记》——9月24日房地产政策记录
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
        WHERE id = '3ea356d1-922f-4182-884c-bb2e0dcffd0a'::uuid
          AND tenant_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid
    ) THEN
        RAISE EXCEPTION
            'Target event % for tenant % not found',
            '3ea356d1-922f-4182-884c-bb2e0dcffd0a',
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
    '4034ffee-ff78-4d5e-b4cf-6a584f42bba3'::uuid,
    '474a5fb4-5cec-4209-89ff-9297d81643ff'::uuid,
    'weibo',
    'demo-pbc-policy-20250925-social-001',
    '2025-09-25T09:15:00Z'::timestamptz,
    '2025-09-25T09:15:00Z'::timestamptz,
    '央行观察者',
    'f1af9527e81f1bde79f57ab458c1c93c0723f1ccc7acbda70774f0d7fa0e7038',
    '微博热议：924新政是央行有史以来最激进的一次房地产松绑',
    '看了央行官网的大事记，9月24日一天出了三招：首付统一15%、金融16条延到2026年底、存量房贷利率定价机制改革。一天之内三拳齐出，这种力度在央行历史上从来没有过。说明决策层对房地产下行的容忍度已经到极限了。',
    'e45cb6e95a33c49e79fe12624560dac9a7e0c5ee38b4a9b37b233b045d9e8ec6',
    567,
    178,
    93,
    'bullish',
    'optimistic',
    '924新政一天三拳齐出，力度史无前例，说明决策层对下行的容忍已到极限',
    'opinion',
    '这种力度在央行历史上从来没有过。',
    0.76,
    '27518416f61e9ae3385ae0535134fe856866938251f86b3195ca75abf1a95fa1'
),
(
    '253954be-b413-45b9-8c16-45cf2d24ec53'::uuid,
    'b7a3ee7c-ec77-4c25-aedb-91fe4c834c25'::uuid,
    'xueqiu',
    'demo-pbc-policy-20250925-social-002',
    '2025-09-25T09:28:00Z'::timestamptz,
    '2025-09-25T09:28:00Z'::timestamptz,
    '利率交易员小赵',
    '833091aea823c7855aa46bb985b9007b025bfbcecac272630a1275a7c195b5ec',
    '雪球讨论：首付15%是双刃剑——降低门槛也放大了杠杆风险',
    '央行把首付比例统一到15%，意味着杠杆从6.7倍放大到了6.7倍→改为5.9倍→现在接近6.7倍。如果房价再跌15%，首付就归零了——这和2008年美国次贷的逻辑很像。政策出发点是好的，但杠杆风险被低估了。',
    '56d80bd09edd4a039e8fb8972237d361c7a9690b31e33e78156ff9cce4a5cece',
    345,
    112,
    56,
    'bearish',
    'negative',
    '首付15%放大杠杆风险，房价再跌15%首付即归零，类似次贷逻辑',
    'speculation',
    '如果房价再跌15%，首付就归零了——这和2008年美国次贷的逻辑很像。',
    0.68,
    'c67d84f362039c5c7f1814e8c1d481fac226ae9e20b0e31547a5e9b4ef758336'
),
(
    'dea924a9-7a12-4694-a621-22f87f89df0f'::uuid,
    '41b25ce6-d285-4cbf-82c5-a0d5975a9dac'::uuid,
    'eastmoney_guba',
    'demo-pbc-policy-20250925-social-003',
    '2025-09-25T09:42:00Z'::timestamptz,
    '2025-09-25T09:42:00Z'::timestamptz,
    '刚需购房者小李',
    '3de0bb30549124a1d64df20519208e712e5175cc7a321355643f3b656d8be74a',
    '股吧热帖：等了三年终于等到15%首付，但我不敢买',
    '从2022年等到2025年，首付从30%降到15%，利率从5.88%降到3%。政策确实到位了，但房价还在跌——我所在的城市过去两年跌了20%。首付15%加上房价继续跌10%，我的首付就没了。政策给了我入场券，但市场没给我信心。',
    '7286c954bfe1d0980b46791fd9aa75ee4d231ff18e161a90ddbb60ccf40a4ba4',
    478,
    203,
    87,
    'bearish',
    'negative',
    '政策到位但市场信心未恢复，房价继续下跌阻碍刚需入场',
    'opinion',
    '政策给了我入场券，但市场没给我信心。',
    0.73,
    '1bad82f2cc0a7bb4fb62dc579f5b2e958c1255ddff99bc00b17630a0f5d302e9'
),
(
    '63c135c8-babd-400b-9e27-9a5e7b064b8c'::uuid,
    'cbba8afe-01e5-4c5b-988b-396b6155b425'::uuid,
    'weibo',
    'demo-pbc-policy-20250925-social-004',
    '2025-09-25T09:55:00Z'::timestamptz,
    '2025-09-25T09:55:00Z'::timestamptz,
    '银行业内部人士',
    '82c2bb2656f36e9f33943d35a7d9c38b29820de78708878c065b095f5750c386',
    '微博讨论：5月17日那一波才是真正的分水岭',
    '大家都关注924，但回头看5月17日才是真正的分水岭：取消利率下限+公积金降息0.25%+首付15%/25%+保障性住房再贷款。9月24日只是把5月17日的力度进一步加码。真正的政策底在5月17日就已经出现了。',
    'ba01a78c331e01cfe1553dbb787900f38a1ad3457598fe1639e72b5e1d7e30e7',
    289,
    94,
    38,
    'bullish',
    'optimistic',
    '真正的政策底在5月17日已出现，924只是进一步加码',
    'opinion',
    '真正的政策底在5月17日就已经出现了。',
    0.71,
    'f8df5f34d8ffdaa2ffc471990d98e89316ba678b372db2c55b4d1188dcc98221'
),
(
    'd13745eb-4555-4926-982f-552ef4b38e0f'::uuid,
    'fced73c1-d0ba-4fc0-81d0-e31adf7efa35'::uuid,
    'xueqiu',
    'demo-pbc-policy-20250925-social-005',
    '2025-09-25T10:08:00Z'::timestamptz,
    '2025-09-25T10:08:00Z'::timestamptz,
    '地产周期研究者',
    '9fc69027d587b2b41dad7a64f084f63d8003b67b0b34eca004458821d5e87fa7',
    '雪球讨论：6月3日保障性住房再贷款才是去库存的真正武器',
    '924新政抢了所有风头，但6月3日的保障性住房再贷款通知才是真正的结构性工具——让地方国企收购已建成未售商品房。这才是“去库存”的核心抓手，而不是降首付。可惜3000亿再贷款到9月只用了162亿，利用率5.4%——政策设计很好，执行端卡壳了。',
    '4cc3af710ae9211942a677124aabf6b6b34780d0975551d97818cff5c9b259aa',
    312,
    87,
    41,
    'wait',
    'neutral',
    '保障性住房再贷款是去库存核心抓手，但执行端利用率仅5.4%卡壳',
    'opinion',
    '政策设计很好，执行端卡壳了。',
    0.72,
    '1614917c3ad1aa11883dc5558ecb278a963602f520ec58966959170a6526fbe1'
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
        'seed_batch', 'demo-pbc-policy-20250925',
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
    '3ea356d1-922f-4182-884c-bb2e0dcffd0a'::uuid,
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
WHERE opinion.event_id = '3ea356d1-922f-4182-884c-bb2e0dcffd0a'::uuid
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
    '3ea356d1-922f-4182-884c-bb2e0dcffd0a'::uuid,
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
        '2025-09-25T10:08:00Z'::timestamptz
    ),
    evidence_count = (
        SELECT COUNT(*)
        FROM event_documents
        WHERE event_id = event.id
    )
WHERE event.id = '3ea356d1-922f-4182-884c-bb2e0dcffd0a'::uuid
  AND event.tenant_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid;
COMMIT;
