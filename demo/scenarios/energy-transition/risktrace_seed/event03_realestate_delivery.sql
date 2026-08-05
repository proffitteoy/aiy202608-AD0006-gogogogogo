-- RiskTrace demo seed
-- Target event:
--   d45648f1-b09b-4119-aeb3-932534c79752
--   财联社《“保交楼”成绩单亮眼！7万亿贷款托底2000万套住房交付》
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
        WHERE id = 'd45648f1-b09b-4119-aeb3-932534c79752'::uuid
          AND tenant_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid
    ) THEN
        RAISE EXCEPTION
            'Target event % for tenant % not found',
            'd45648f1-b09b-4119-aeb3-932534c79752',
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
    '21c1cfbe-f68c-4f11-87cf-be49501c8ca8'::uuid,
    'd9526081-e207-4f5d-9b02-a3646389f0c2'::uuid,
    'weibo',
    'demo-realestate-delivery-20250923-social-001',
    '2025-09-23T00:15:00Z'::timestamptz,
    '2025-09-23T00:15:00Z'::timestamptz,
    '楼市老兵',
    'd4f93398998c42628aa4becb12b9338f4014975f89fbcd8970cabe900ab4db44',
    '微博热议：7万亿托底2000万套，但别忘了每年减息3000亿才是真金白银',
    '李云泽说7万亿支持2000万套交付，数字很震撼。但潘功胜说的存量房贷利率下调每年减5000万户家庭3000亿利息支出，这个对消费的刺激可能比7万亿更直接——3000亿直接进了老百姓口袋。',
    '13a3c3e6df9d88749bf8db2d7cf7e9b4a616eb4c3b05fde51791fa1edc70bebe',
    423,
    115,
    67,
    'bullish',
    'optimistic',
    '存量房贷利率下调每年减3000亿利息支出，对消费刺激比7万亿更直接',
    'opinion',
    '3000亿直接进了老百姓口袋。',
    0.74,
    '77acb651afc279a73d151c870686e5aee2c3137703bd4764a220225d676732c8'
),
(
    '50a533d7-0a1f-4a4b-8f69-f8533f46b402'::uuid,
    'faeb2ecb-128f-4907-a46c-99306e8e9646'::uuid,
    'xueqiu',
    'demo-realestate-delivery-20250923-social-002',
    '2025-09-23T00:28:00Z'::timestamptz,
    '2025-09-23T00:28:00Z'::timestamptz,
    '宏观交易员',
    'ae9904fa0b46d3fcb8c3c4a45fac51eaf24d6660244d113e5ce2a794ebb69e01',
    '雪球讨论：融资平台数量降60%才是被忽视的大新闻',
    '大家都在讨论7万亿白名单，但潘功胜还说了句——融资平台数量较2023年3月下降超60%，金融债务规模下降超50%。这意味着城投债务风险在快速收敛，这对银行股估值修复的支撑比房地产政策更大。',
    '721328aa3850ab5fd118ab0677b4209c1405d34fd07a05aa0420562267236265',
    312,
    89,
    41,
    'bullish',
    'optimistic',
    '融资平台数量降60%、债务规模降50%，城投风险收敛利好银行估值',
    'opinion',
    '这对银行股估值修复的支撑比房地产政策更大。',
    0.72,
    '19bf4a0218f3540954264eee2ee6e8b8914c3029d8c68f3ea595c3d44fa4f30f'
),
(
    '4b5a8943-b978-4651-879a-d9d1389a02e4'::uuid,
    'a1c852ed-6e80-4e4e-8eb0-9b3671108957'::uuid,
    'eastmoney_guba',
    'demo-realestate-delivery-20250923-social-003',
    '2025-09-23T00:42:00Z'::timestamptz,
    '2025-09-23T00:42:00Z'::timestamptz,
    '被套的房奴',
    '089fbb05c6784fca546d67b82c363cda67b10e3fb4c77014ab6a045911163fbd',
    '股吧热帖：LPR降了8次合计1.15个百分点，但我的月供没怎么降',
    '央行说2022年以来降5年期LPR共8次合计1.15个百分点至3.5%。但我是2021年高位买的房，利率5.88%，即使存量利率调整后还是4.2%左右。降是降了，但和历史低位比差远了。真正的刚需购房者还在还高息贷款。',
    '0cb8b419105abc4a476670106f06fdd3662bc4c835c9f2146dc23d46421bd605',
    389,
    156,
    72,
    'bearish',
    'negative',
    'LPR虽降8次但存量房贷利率仍偏高，刚需购房者负担未实质性减轻',
    'opinion',
    '降是降了，但和历史低位比差远了。',
    0.7,
    '9447837119c7b2d6ba9478fe9fa00d92131c1fcbe82756652ac0d28e2de7ab56'
),
(
    '5c40be64-dea5-4e55-bc0f-198fc43019bd'::uuid,
    '54e3e009-df1c-434d-8ad0-0b98fe41db68'::uuid,
    'weibo',
    'demo-realestate-delivery-20250923-social-004',
    '2025-09-23T00:55:00Z'::timestamptz,
    '2025-09-23T00:55:00Z'::timestamptz,
    '基建投资分析',
    '0a114d01286a23db194245cbf3f70d99072ecc4d34929e7831c123452a24f615',
    '微博讨论：保障性住房1.6万亿+租赁贷款增52%才是新增长极',
    '7万亿白名单是“止血”，但1.6万亿三大工程+租赁贷款年均增52%才是“造血”。房地产的新模式不是回到高周转老路，而是转向保障+租赁。这意味着建材、施工的增量需求会从商品房转向保障房——结构变了。',
    '4a14694c6dd4210dd9197cea8938006031613f80d6290aa4ee45a2525b46cbe4',
    256,
    78,
    33,
    'bullish',
    'optimistic',
    '保障房1.6万亿+租赁贷款增52%是“造血”，房地产转向新模式',
    'speculation',
    '房地产的新模式不是回到高周转老路，而是转向保障+租赁。',
    0.69,
    '017354056733ad313b6c4037784a9a433575eb883854e25f89997b96bb3619c2'
),
(
    '2f9f2d2e-6dd7-47fb-b37d-6a86ccd4349a'::uuid,
    '91b7b306-9fcc-4cc5-8172-963ed7ae0195'::uuid,
    'xueqiu',
    'demo-realestate-delivery-20250923-social-005',
    '2025-09-23T01:08:00Z'::timestamptz,
    '2025-09-23T01:08:00Z'::timestamptz,
    '看多中国的长期主义者',
    '1a78a1aa692742e83e849c604ededc4e82cb168a5fce8fe7f269dc69a7ce1774',
    '雪球讨论：2000万套交付=2000万个家庭信用修复',
    '看了很多评论都在挑毛病，但换个角度想——2000万套住房交付意味着2000万个家庭的资产负债表得到修复。这些家庭从“钱交了房没拿到”的恐惧中解脱出来，消费信心和再投资意愿会逐步恢复。这是底层的信用修复，比任何政策刺激都管用。',
    '262f41aebdbb3933137031fa8a79fdda7215bd7565526fb61715b94b1df7a782',
    198,
    62,
    25,
    'bullish',
    'optimistic',
    '2000万套交付=2000万个家庭信用修复，底层信用修复比政策刺激更管用',
    'opinion',
    '这是底层的信用修复，比任何政策刺激都管用。',
    0.73,
    '5c845229f716ddc0f3dbf371c39bf09dba8bc14ad2c39750c38c9d50cfa4988e'
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
        'seed_batch', 'demo-realestate-delivery-20250923',
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
    'd45648f1-b09b-4119-aeb3-932534c79752'::uuid,
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
WHERE opinion.event_id = 'd45648f1-b09b-4119-aeb3-932534c79752'::uuid
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
    'd45648f1-b09b-4119-aeb3-932534c79752'::uuid,
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
        '2025-09-23T01:08:00Z'::timestamptz
    ),
    evidence_count = (
        SELECT COUNT(*)
        FROM event_documents
        WHERE event_id = event.id
    )
WHERE event.id = 'd45648f1-b09b-4119-aeb3-932534c79752'::uuid
  AND event.tenant_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid;
COMMIT;
