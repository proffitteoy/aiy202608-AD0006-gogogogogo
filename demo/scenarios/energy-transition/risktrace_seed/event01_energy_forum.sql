-- RiskTrace demo seed
-- Target event:
--   59ca0f47-482d-4087-93ac-1d53b421caec
--   证券时报《共话“十五五”新能源产业：光储氢如何实现高质量发展？》
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
        WHERE id = '59ca0f47-482d-4087-93ac-1d53b421caec'::uuid
          AND tenant_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid
    ) THEN
        RAISE EXCEPTION
            'Target event % for tenant % not found',
            '59ca0f47-482d-4087-93ac-1d53b421caec',
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
    '22a38262-520e-4965-ba3e-5b4327f31202'::uuid,
    'd07253df-114c-4c47-81e1-2b5a2dc6b57e'::uuid,
    'weibo',
    'demo-energy-forum-20251125-social-001',
    '2025-11-25T10:15:00Z'::timestamptz,
    '2025-11-25T10:15:00Z'::timestamptz,
    '光储氢观察员',
    'd073be347969a1d66687312ab72cdc60dd69967f4d54cfc537a350fa96c6a73a',
    '微博热议：光储氢三条线里储能最被低估',
    '刚看完这篇论坛报道，通威邱艾松说行业焦虑核心是规则问题不是技术问题，这点我非常认同。但市场还没充分定价的是储能——刘勇说“同工同酬”如果真的落地，储能独立电站的IRR模型要重算。',
    '5ef39f632de9298045c2d7bdb21c3a3d99353701733390c6689f399064bce9f8',
    312,
    89,
    43,
    'bullish',
    'optimistic',
    '储能“同工同酬”政策若落地将重算IRR模型，市场未充分定价',
    'opinion',
    '储能独立电站的IRR模型要重算。',
    0.72,
    'e2a96ecbb3d11146d6e057ce8cfdca64eced1c6b54c9e3cb96bdfdea46f21987'
),
(
    'e1501ead-4e2a-48b1-b21d-16605c6bf094'::uuid,
    '6b46bf93-5f1c-4874-9d89-90f21d59d9d0'::uuid,
    'xueqiu',
    'demo-energy-forum-20251125-social-002',
    '2025-11-25T10:28:00Z'::timestamptz,
    '2025-11-25T10:28:00Z'::timestamptz,
    '新能源赛道选手',
    '5d5431f41cc8320213a27e2e15b0c2ebfaf57249aed328e3431143bd0a61dcc9',
    '雪球讨论：光伏TOPCon产能过剩不代表行业没机会',
    '沈文忠说TOPCon市场已饱和、未来1-2年产能闲置，但重点在后面——无银化、贱金属化是真正的技术拐点。谁先跑通铜电镀工艺，谁就能在下一轮成本战中赢。短期看产能出清是利空，长期看是龙头集中度提升的利好。',
    'f65f5c38890efb64307312bf2b2bb136b7b3bc1d769ad70c828fb0a29f805522',
    198,
    56,
    22,
    'bullish',
    'optimistic',
    '光伏短期产能过剩但长期利好龙头集中度提升，无银化是技术拐点',
    'speculation',
    '谁先跑通铜电镀工艺，谁就能在下一轮成本战中赢。',
    0.68,
    '29dce464014044e5c1106fdafc175a87905baa790dbabe4582ffe028c677aaca'
),
(
    'c634071f-66a8-493e-b568-697ab2c6728a'::uuid,
    'aa7ca772-4d1b-4784-9204-a5934945e1d8'::uuid,
    'xueqiu',
    'demo-energy-forum-20251125-social-003',
    '2025-11-25T10:47:00Z'::timestamptz,
    '2025-11-25T10:47:00Z'::timestamptz,
    '研究不易的散户',
    'eae342da49598692d1bf3285c8c83d65f73313e3ae2b1776c55eb2a52e5ac714',
    '跟帖分歧：专家说“高质量”但市场在交易“低预期”',
    '孙海波说核心是“高质量”，但说实话二级市场现在交易的不是高质量，是低预期修复。光伏板块跌了两年，PE已经到历史底部，只要政策不进一步恶化就是利好。专家谈的“又快又好”是产业逻辑，和投资节奏是两码事。',
    'ed5e4da4812c94e45ada5cf0863b1a6b8b72078f39ac827ddf9b0ee338d56b74',
    167,
    71,
    15,
    'wait',
    'neutral',
    '产业逻辑（高质量）与投资节奏（低预期修复）不同步，追高需谨慎',
    'opinion',
    '专家谈的“又快又好”是产业逻辑，和投资节奏是两码事。',
    0.65,
    '97383b5ac0e4dbb73c8f19f13d775ef5ebb8eb1b951c1917b87bf4488bb26cd8'
),
(
    '0536b15c-7850-49fb-8066-19f3b01b809e'::uuid,
    '76f29ab5-93a0-4c08-b9c8-0034710039c4'::uuid,
    'eastmoney_guba',
    'demo-energy-forum-20251125-social-004',
    '2025-11-25T11:03:00Z'::timestamptz,
    '2025-11-25T11:03:00Z'::timestamptz,
    '题材挖掘机',
    '2555f61898d37d876d6448c4271b93530efb99acc36779a58d9f9cc010cd4d45',
    '股吧热帖：氢能才是十五五最被忽视的万亿赛道',
    '整篇报道里最有价值的是张焰峰那句话——“氢不再是能不能，而是用在何处的问题”。绿氢2030年200万吨的目标，对应的电解槽市场是千亿级。现在市场给了储能足够关注，但氢能板块的估值还在地上。',
    'b7f388b46bf01f24bc4fe044ee53b5cf2bd1220cc4bb73b605162f5fa6aaeea5',
    276,
    94,
    31,
    'bullish',
    'optimistic',
    '氢能是十五五最被低估的万亿赛道，电解槽市场千亿级',
    'speculation',
    '现在市场给了储能足够关注，但氢能板块的估值还在地上。',
    0.7,
    '63e1f3ff3dc511ca3b10bce42141a90e1911cbaa7c2979cd7059514b3c1a9597'
),
(
    '7fd29b73-0688-4462-bb42-329650e1d5e1'::uuid,
    'ef863e0e-08c8-43c3-8fcb-f3300ee46d7f'::uuid,
    'weibo',
    'demo-energy-forum-20251125-social-005',
    '2025-11-25T11:22:00Z'::timestamptz,
    '2025-11-25T11:22:00Z'::timestamptz,
    '持仓过夜有点慌',
    '7bfba6bb731b74ecc4cddd486cb7ba97c3d9ea6fbc60bc3de1141c923a28c8b2',
    '微博复盘：专家观点虽好但别急着追高',
    '专家们说得都很有道理，但每次这种行业论坛开完，第二天相关板块都会高开低走。核心问题还是需求端没看到实质性改善——136号文的冲击还没消化完，现在追光储氢等于在左侧接飞刀。建议等明年Q1装机数据出来再定方向。',
    '238a55c5ebe447b21b2d8f1301010b5eb0b5199aadcc196eeefdb88c3e5b1271',
    234,
    82,
    28,
    'bearish',
    'negative',
    '行业论坛后通常高开低走，需求端未见实质性改善，追高风险大',
    'opinion',
    '现在追光储氢等于在左侧接飞刀。',
    0.67,
    '4248af9e3013299cab44cef879704d2915c0ef602b37b7991f699fcbfc678b3c'
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
        'seed_batch', 'demo-energy-forum-20251125',
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
    '59ca0f47-482d-4087-93ac-1d53b421caec'::uuid,
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
WHERE opinion.event_id = '59ca0f47-482d-4087-93ac-1d53b421caec'::uuid
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
    '59ca0f47-482d-4087-93ac-1d53b421caec'::uuid,
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
        '2025-11-25T11:22:00Z'::timestamptz
    ),
    evidence_count = (
        SELECT COUNT(*)
        FROM event_documents
        WHERE event_id = event.id
    )
WHERE event.id = '59ca0f47-482d-4087-93ac-1d53b421caec'::uuid
  AND event.tenant_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid;
COMMIT;
