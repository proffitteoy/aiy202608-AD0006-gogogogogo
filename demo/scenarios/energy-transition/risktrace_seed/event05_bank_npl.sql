-- RiskTrace demo seed
-- Target event:
--   7c6199a0-2a2c-434c-892a-45f4ca3d67bd
--   中国房地产报/中房网《起底银行坏账！地产与个贷仍是高发区》
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
        WHERE id = '7c6199a0-2a2c-434c-892a-45f4ca3d67bd'::uuid
          AND tenant_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid
    ) THEN
        RAISE EXCEPTION
            'Target event % for tenant % not found',
            '7c6199a0-2a2c-434c-892a-45f4ca3d67bd',
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
    'a8a1e48b-3eb5-42ce-9103-7e72b26c55c6'::uuid,
    '9ab1d8bb-b4c7-4137-9300-fba1592d3fd2'::uuid,
    'weibo',
    'demo-bank-npl-20250910-social-001',
    '2025-09-10T09:15:00Z'::timestamptz,
    '2025-09-10T09:15:00Z'::timestamptz,
    '银行股持有者',
    'bd6d9c0629fb4eacb6dac45569c1cab784d0210774ae23074eb35e2399251a5d',
    '微博热议：六大行房贷不良率全线上涨，银行股还撑得住吗',
    '工行从0.73%涨到0.86%，交行从0.58%涨到0.75%——六大行个人房贷不良率全部上升。虽然绝对值不高，但趋势方向比绝对水平更可怕。银行股的估值修复前提是资产质量稳定，如果房贷不良继续上升，PB修复逻辑就不成立。',
    'be1a5d44d166f11c51bbe5dc7440bf522049e04e81e2f97bc6164bcc80d3b9f4',
    434,
    145,
    72,
    'bearish',
    'negative',
    '六大行房贷不良率全线上涨，趋势方向比绝对水平更可怕，PB修复逻辑不成立',
    'opinion',
    '趋势方向比绝对水平更可怕。',
    0.74,
    '9f4e4f157a00d449a8b77dcd59b9389d133444e4a38917c11bf6b2c9977757cc'
),
(
    '03406261-3faf-499f-9a88-1b72a223db1e'::uuid,
    '9bdd30f9-051f-493d-bfee-85fa9da9343d'::uuid,
    'xueqiu',
    'demo-bank-npl-20250910-social-002',
    '2025-09-10T09:28:00Z'::timestamptz,
    '2025-09-10T09:28:00Z'::timestamptz,
    '风控老兵',
    '9f8f1e13cdf23d235622e942e54f55e469c7fee334f5f0b83445b40faf0f1866',
    '雪球讨论：青农商行房地产不良率21.32%才是真正的雷',
    '大家关注六大行，但真正危险的是中小银行。青农商行房地产不良率从7%飙到21.32%，意味着每放100块房贷有21块收不回来。这种级别的坏账，拨备覆盖率再高也扛不住。城商行农商行的房地产风险敞口远未被市场定价。',
    'ab8c59e0717bc2966302526f4a9ae1ba1d01a4b62e2677f4c687c7cc5ce47a06',
    367,
    98,
    56,
    'bearish',
    'negative',
    '中小银行房地产不良率飙升（青农商行21.32%），城商行风险敞口未被市场定价',
    'opinion',
    '城商行农商行的房地产风险敞口远未被市场定价。',
    0.72,
    '21eda3ac73b404c5bf0125fff1893197664d3aaa59cf5892575b91761486fa80'
),
(
    'a6012c6e-8ceb-4e6e-8a25-00a36e6ef140'::uuid,
    '96bffdff-cc82-4d24-8327-b09288aa6ada'::uuid,
    'eastmoney_guba',
    'demo-bank-npl-20250910-social-003',
    '2025-09-10T09:42:00Z'::timestamptz,
    '2025-09-10T09:42:00Z'::timestamptz,
    '断供的苦命人',
    '935da1ed792a6a5d577ddbf3f6d4f082976ac2b181dca0e65c079e07050ecd68',
    '股吧热帖：银行组建催收团队来收我的房贷了',
    '报道说国有大行总行组建直属催收团队，我已经体验到了——上个月接到工行催收电话，态度比以前硬多了。我2021年高位买的房跌了30%，月供1万2还着，真的还不动了。不是不想还，是真的还不起。',
    '061d13bcaf2323451c22ba66e39dec9fb157f2669cb25d1a61a65f3ad8cd31b6',
    567,
    234,
    112,
    'bearish',
    'negative',
    '银行组建直属催收团队，借款人实际还款压力加剧',
    'opinion',
    '不是不想还，是真的还不起。',
    0.7,
    'f2457fa3429bfff032bf70e7c14b26f9b32b3dc5a7be8f4f55dde78142c287d9'
),
(
    '44acb73f-f363-4e60-8a55-e835835efc12'::uuid,
    '44e7c480-c23a-4e99-8e8e-73635d1a047a'::uuid,
    'weibo',
    'demo-bank-npl-20250910-social-004',
    '2025-09-10T09:55:00Z'::timestamptz,
    '2025-09-10T09:55:00Z'::timestamptz,
    '金融分析师小陈',
    '4b6b7b522cf27efef9e1fbfbd2b931f6d2e8042317fe68e4067ee125789b9cad',
    '微博讨论：银行“放松审核标准”才是不良率上升的真正原因',
    '报道分析了三个原因：收入放缓、房价下跌、银行放松审核。第三个原因被忽视了——2020-2021年房贷狂飙时期，很多银行为了冲规模放宽了收入证明审核。现在这些“水分贷款”开始暴露了。不是市场的问题，是银行自己的问题。',
    '2367ab82d40da9cdf1fc3788a6dd4f9cc838458d234a82779573ba3646dd6925',
    289,
    87,
    34,
    'bearish',
    'negative',
    '2020-2021年房贷狂飙期银行放松审核，“水分贷款”开始暴露',
    'opinion',
    '不是市场的问题，是银行自己的问题。',
    0.69,
    '67149f4cd32c7abb2976db65b6e54d5ac66d86f082b376e84772dccf62dd2461'
),
(
    '7a741069-ae3b-4e82-84fd-2a63e42187af'::uuid,
    '3671c9ec-473e-406d-928f-a54219117da0'::uuid,
    'xueqiu',
    'demo-bank-npl-20250910-social-005',
    '2025-09-10T10:08:00Z'::timestamptz,
    '2025-09-10T10:08:00Z'::timestamptz,
    '逆向投资者',
    '7f2bd3b1bc3ae2ba30f35e5d8b0e94af4548f49bc06f6d4a651a23cdad68a119',
    '雪球讨论：中国银行房地产不良率5.38%反而说明风险在出清',
    '中行房地产不良率5.38%看似很高，但“实质新增同比已经出现下降趋势”——武剑这句话才是关键。不良率上升有两种：一种是新不良在加速生成，一种是旧不良在集中暴露。现在是后者，是风险出清的信号而不是恶化信号。',
    '79a1c58551c8861ba9f7c7c25ea0a91429e47984041f711546bbe2145029a44e',
    234,
    76,
    29,
    'bullish',
    'optimistic',
    '不良率上升是旧不良集中暴露而非新不良加速，属于风险出清信号',
    'opinion',
    '是风险出清的信号而不是恶化信号。',
    0.67,
    '529955da6bce695a56ea7dac11267c7f3555f7cd074095501b1fb635d5e98462'
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
        'seed_batch', 'demo-bank-npl-20250910',
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
    '7c6199a0-2a2c-434c-892a-45f4ca3d67bd'::uuid,
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
WHERE opinion.event_id = '7c6199a0-2a2c-434c-892a-45f4ca3d67bd'::uuid
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
    '7c6199a0-2a2c-434c-892a-45f4ca3d67bd'::uuid,
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
        '2025-09-10T10:08:00Z'::timestamptz
    ),
    evidence_count = (
        SELECT COUNT(*)
        FROM event_documents
        WHERE event_id = event.id
    )
WHERE event.id = '7c6199a0-2a2c-434c-892a-45f4ca3d67bd'::uuid
  AND event.tenant_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid;
COMMIT;
