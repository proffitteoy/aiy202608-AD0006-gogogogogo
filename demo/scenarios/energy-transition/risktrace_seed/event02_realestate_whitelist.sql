-- RiskTrace demo seed
-- Target event:
--   17c948f5-7aef-474e-9bb2-1a7ef2e45d72
--   证券时报《半年增加一万亿元 全国房地产“白名单”项目融资稳步推进》
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
        WHERE id = '17c948f5-7aef-474e-9bb2-1a7ef2e45d72'::uuid
          AND tenant_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid
    ) THEN
        RAISE EXCEPTION
            'Target event % for tenant % not found',
            '17c948f5-7aef-474e-9bb2-1a7ef2e45d72',
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
    '2e988fe0-030a-4d63-8aed-e6f3d91d35bc'::uuid,
    'ff046141-5099-4ebc-ae88-3e0764165015'::uuid,
    'weibo',
    'demo-realestate-whitelist-20251105-social-001',
    '2025-11-05T21:15:00Z'::timestamptz,
    '2025-11-05T21:15:00Z'::timestamptz,
    '地产观察哨',
    '2a164a8eaa20338ad7c97291b571831420907abcac4ac447daa115b02a11f049',
    '微博热议：7万亿审批但实际放款率才30%',
    '标题写得很漂亮“稳步推进”，但仔细看数据：审批7万亿，实际放款才1.64万亿，放款率不到30%。银行嘴上说支持，身体很诚实——没有明确的风险分担机制，谁敢大额放款给房企？',
    'b7d8ed31fdcbb298af25758ca75548b9d741e6a330ba72da1d2ce3647cd72899',
    456,
    132,
    78,
    'bearish',
    'negative',
    '审批7万亿但实际放款率不到30%，银行风险厌恶态度明显',
    'opinion',
    '银行嘴上说支持，身体很诚实——没有明确的风险分担机制，谁敢大额放款给房企？',
    0.75,
    '53ae7e05f5c0393e9ac92b3b7b28cd94807f326a4b92de14d7c6adfb5d090473'
),
(
    '9259c204-2b84-436d-a061-b009a71677e3'::uuid,
    'c3eedaab-44ae-4a9a-9e47-181e41756fc1'::uuid,
    'xueqiu',
    'demo-realestate-whitelist-20251105-social-002',
    '2025-11-05T21:28:00Z'::timestamptz,
    '2025-11-05T21:28:00Z'::timestamptz,
    '价值投资者老王',
    '9df9a2f30779e46bb3668fa067f5f30bd1edb85d7976e30e24e1bd282c66b55a',
    '雪球讨论：保交楼基本完成是真正的系统性利好',
    '刘水说“保交楼已从应急性攻坚转入常态化平稳运行”，这句话的分量比7万亿这个数字更大。保交楼完成意味着期房信用修复——购房者敢买期房了，销售端才有可能真正回暖。这是房地产企稳的第一块多米诺骨牌。',
    '86dec4e880566aee2108525dacea0e543cc3cda68f7682e3939867427fc320ef',
    289,
    87,
    45,
    'bullish',
    'optimistic',
    '保交楼完成意味着期房信用修复，是房地产企稳的第一块多米诺骨牌',
    'opinion',
    '保交楼完成意味着期房信用修复——购房者敢买期房了，销售端才有可能真正回暖。',
    0.73,
    'b1ac76129092269d9468b968957b9e77c9667014ddd1daf6f1ec7e0555a83389'
),
(
    '2cd514d0-24eb-482f-85a0-27f55c6f178b'::uuid,
    '68e43653-6c2e-4068-af7d-b2934e8ddb77'::uuid,
    'eastmoney_guba',
    'demo-realestate-whitelist-20251105-social-003',
    '2025-11-05T21:42:00Z'::timestamptz,
    '2025-11-05T21:42:00Z'::timestamptz,
    '不追高的韭菜',
    '9de024ed10fc27214f5fb2ae43431ea53b71ef35e68c77d6ae6de26806b5e8b7',
    '股吧热帖：750万套交付背后是无数供应商的血泪',
    '报道说全国750多万套已售难交付住房实现交付，但这背后是多少建筑商、材料商垫资扛着？白名单只保了购房者和银行，产业链上下游的欠款谁来管？房地产的风险传导远没结束。',
    '9d3dd15ad65d172e91db07f3ddcaae70ebf5faa182473f1a4fa1184886307834',
    367,
    118,
    52,
    'bearish',
    'negative',
    '白名单只保购房者和银行，产业链上下游欠款风险未解决',
    'opinion',
    '白名单只保了购房者和银行，产业链上下游的欠款谁来管？',
    0.69,
    'c825bedc3b7a8fe06974ddbb332a59c20e75c19fd35426d86bbdd1b7aefd1fc4'
),
(
    '249e32fa-019a-463b-a944-9dd59f36f762'::uuid,
    '1a5ed97e-7c0c-4deb-afda-e9baf1eec46a'::uuid,
    'xueqiu',
    'demo-realestate-whitelist-20251105-social-004',
    '2025-11-05T21:55:00Z'::timestamptz,
    '2025-11-05T21:55:00Z'::timestamptz,
    '银行股研究员',
    '16175436a1511335ff23f2bc78e2907d712a168d94dcacf25b7856bc7bf6325d',
    '雪球讨论：白名单对银行是双刃剑——放多了怕不良，放少了被约谈',
    '从银行角度看白名单：放款多了，万一项目还是烂尾，不良率直接上升；放款少了，监管约谈。两难之间银行选择了“审批多、放款少”的策略。30%的放款率其实反映了银行的真实态度——风险厌恶。',
    'e5d1e94adc7a081e5d027ce341f83e0dd5fb267146990257a991b56458a15425',
    234,
    76,
    29,
    'wait',
    'neutral',
    '银行选择“审批多放款少”策略，30%放款率反映真实风险厌恶',
    'opinion',
    '30%的放款率其实反映了银行的真实态度——风险厌恶。',
    0.71,
    '299ca1827544ddf58fba57de62800121cd7e2e385058e2ea976664c20d1b0a87'
),
(
    '9fa3524f-a47b-437f-8441-1510e1b5f028'::uuid,
    'b5108c6c-d17e-4ead-b2cf-c0f408803684'::uuid,
    'weibo',
    'demo-realestate-whitelist-20251105-social-005',
    '2025-11-05T22:08:00Z'::timestamptz,
    '2025-11-05T22:08:00Z'::timestamptz,
    '财经评论员张三',
    'a9e81ca74c04e3af269a9b2a724de77a0d745014d96e89e7091c25e498d49b92',
    '微博复盘：白名单制度最大的价值不是钱而是信心',
    '半年增加1万亿确实在加速，但最大的价值不是钱本身，而是向市场传递“政府不会让项目烂尾”的信号。750万套交付意味着购房者的恐惧心理在消退。等这个信心完全修复了，市场自然就回暖了——只是时间问题。',
    'caaec69976d471d40ada7753ff2bf8f9864446634e8259a05b0fbbf386193287',
    298,
    91,
    37,
    'bullish',
    'optimistic',
    '白名单最大价值是传递信心信号，购房者恐惧心理消退',
    'opinion',
    '等这个信心完全修复了，市场自然就回暖了——只是时间问题。',
    0.68,
    '4033351c964e7c7cd7bd60473c3decef7dbb687bfc304f749a785a5631d2da62'
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
        'seed_batch', 'demo-realestate-whitelist-20251105',
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
    '17c948f5-7aef-474e-9bb2-1a7ef2e45d72'::uuid,
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
WHERE opinion.event_id = '17c948f5-7aef-474e-9bb2-1a7ef2e45d72'::uuid
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
    '17c948f5-7aef-474e-9bb2-1a7ef2e45d72'::uuid,
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
        '2025-11-05T22:08:00Z'::timestamptz
    ),
    evidence_count = (
        SELECT COUNT(*)
        FROM event_documents
        WHERE event_id = event.id
    )
WHERE event.id = '17c948f5-7aef-474e-9bb2-1a7ef2e45d72'::uuid
  AND event.tenant_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid;
COMMIT;
