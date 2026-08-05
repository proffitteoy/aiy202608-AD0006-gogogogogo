-- RiskTrace demo seed
-- Target event:
--   4a897de9-f136-4e25-bc87-06c2920473c8
--   中国能源产业发展网/36氪《四个关键词解码+引爆A股涨停潮》
--
-- Purpose:
--   为单个能源事件补充 5 条模拟社交帖子与 5 条观点归因记录，
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
        WHERE id = '4a897de9-f136-4e25-bc87-06c2920473c8'::uuid
          AND tenant_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid
    ) THEN
        RAISE EXCEPTION
            'Target event % for tenant % not found',
            '4a897de9-f136-4e25-bc87-06c2920473c8',
            'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa';
    END IF;
END $$;

CREATE TEMP TABLE tmp_energy_rally_seed (
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

INSERT INTO tmp_energy_rally_seed (
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
    '45ff444b-34b0-48d3-8316-3937f5902626'::uuid,
    '09d0181a-53ae-46c2-af4f-5390b219e727'::uuid,
    'weibo',
    'demo-energy-rally-social-001',
    '2026-07-22T16:08:00Z'::timestamptz,
    '2026-07-22T16:10:00Z'::timestamptz,
    '新能源老纪',
    '05debf3517b16854aea82abbb54692ba832d3d0f617df06a4b23f1c8b4775880',
    '微博热议：新能源链被“四个关键词”再次点火',
    '刚看完这篇对“扩量提质、可靠替代、制氢、制度创新”的拆解，今天A股的电网设备、储能、特高压一起拉升不是偶然。市场现在在交易的不只是情绪，而是后续招标和并网节奏可能同步改善。',
    '0f15dbda263a6a271c0dca8f38b98155db3c254fca8604bc446b54ba5efccc6c',
    286,
    74,
    51,
    'bullish',
    'optimistic',
    '市场把规划关键词解读成新能源链景气扩散信号',
    'opinion',
    '电网设备、储能、特高压一起拉升不是偶然，后续招标和并网节奏可能同步改善。',
    0.74,
    'e58426e35fad7f7c2e18e4ce3af1f6a14427ffe33bbb3105f126a40376514b40'
),
(
    '8329dbc4-64cb-4479-bbf1-c31941695396'::uuid,
    '4c0f37dc-ea22-49c1-9754-a337291bee2f'::uuid,
    'xueqiu',
    'demo-energy-rally-social-002',
    '2026-07-22T16:19:00Z'::timestamptz,
    '2026-07-22T16:21:00Z'::timestamptz,
    '左侧看景气',
    'bd0ec278a7140c7efd95a16bbb1aae5021895abce30bd9057c84f3dfc675a2ee',
    '雪球讨论：先看电网设备，再看储能兑现',
    '这条消息最值得盯的不是口号，而是“可靠替代”第一次被放到这么高的位置。真要兑现，先受益的可能是电网设备和储能，光伏组件更像第二阶段受益，短期节奏上还是先看订单。',
    'e6dbe2dbd1fe49a009012809b6385a529d519adef09062b4d030ab3f6f60d1bd',
    193,
    41,
    18,
    'bullish',
    'optimistic',
    '讨论焦点开始从概念炒作转向电网设备和储能订单兑现',
    'speculation',
    '先受益的可能是电网设备和储能，光伏组件更像第二阶段受益。',
    0.69,
    '900c63848fb43107caa4685e417eb337e1f831adf72d7910748fe6472cde7ad0'
),
(
    '1f4faeb2-94c0-44f4-9ec3-eedd2d4aeab2'::uuid,
    'd8e7ecde-cd19-4cda-a0c9-277a1ae2f1ae'::uuid,
    'xueqiu',
    'demo-energy-rally-social-003',
    '2026-07-22T16:34:00Z'::timestamptz,
    '2026-07-22T16:36:00Z'::timestamptz,
    '逆风做研究',
    'f67f5a91b0ae73a75d78e61aff17efbdd0f783ae62bbbedf49c776d89d7449c6',
    '跟帖分歧：涨停潮之后更要防止高位追涨',
    '今天涨停潮很猛，但里面有不少是情绪先跑、业绩后验证。政策方向当然偏正面，不过如果后续没有更细的配套细则，短线追高很容易从“预期差”变成“兑现差”。',
    '609198123129610412d2502c3e46014d4ef44dc5f1a47bd5753025b8cac0db67',
    158,
    57,
    12,
    'bearish',
    'negative',
    '部分资金担心涨停潮透支预期，短线追高风险上升',
    'opinion',
    '如果后续没有更细的配套细则，短线追高很容易从“预期差”变成“兑现差”。',
    0.63,
    'ba5b733eb58d6f3d5960c40af2eb440e9e2c90a2654d5344cc9ea62f972f0795'
),
(
    '30bcb7ac-8fa5-4903-8f68-dce936b77181'::uuid,
    '4a6119d6-bf00-4fa8-8073-39be8669e505'::uuid,
    'eastmoney_guba',
    'demo-energy-rally-social-004',
    '2026-07-22T16:47:00Z'::timestamptz,
    '2026-07-22T16:49:00Z'::timestamptz,
    '题材跟踪员',
    'b2f1fa6618906523240307d1295a11a8c591153267aa60dc8580847f68e9f460',
    '股吧热帖：绿氢和储能是这轮扩散里最容易被低估的支线',
    '很多人只盯着光伏，其实这篇里面最有弹性的还是制氢和储能。只要“非电利用”这条线被市场继续强化，绿氢装备、长时储能、电解槽这些方向的弹性未必比主线差。',
    '3611286a47f31874aa6dc4fcbb6c87679c8ed1b2a30a1eb22c5f952663fcbf34',
    247,
    88,
    21,
    'bullish',
    'optimistic',
    '社交讨论开始把制氢和储能视为主线外的弹性方向',
    'speculation',
    '只要“非电利用”这条线被市场继续强化，绿氢装备、长时储能的弹性未必比主线差。',
    0.71,
    '4122ca9f11aec92f44928720ff392f51e1714fe7f03761e2263bc798fbe785ab'
),
(
    'c682d3ea-2311-430e-ad4f-08c1f2da4ff0'::uuid,
    '31fe15d9-45ce-4a57-a348-11dde3bf3091'::uuid,
    'weibo',
    'demo-energy-rally-social-005',
    '2026-07-22T17:11:00Z'::timestamptz,
    '2026-07-22T17:13:00Z'::timestamptz,
    '盘中看板客',
    'bcee1871116c6dd6a0781d05232981ae4d1c9476dbe58bbdac13b2d1ceb4148d',
    '微博复盘：政策强度确认了，但分化也会更快到来',
    '今天盘面已经确认政策强度够硬，问题只剩谁是真受益、谁是情绪搭车。看板块内部，电网设备和特高压的持续性比纯概念票更强，后面应该会从普涨转成细分龙头分化。',
    '97d44f01681c83cadb1e5e46a2d1cc8f640e88ae441608637308017dae6e0997',
    321,
    93,
    37,
    'wait',
    'neutral',
    '情绪从全面看多切到细分龙头筛选，市场进入分化观察阶段',
    'opinion',
    '后面应该会从普涨转成细分龙头分化。',
    0.66,
    '53476e25098dde65f34cc43ec9a59499fec3b23e8db6cf450753c89b2334acbe'
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
        'seed_batch', 'demo-energy-a-share-rally-20260805',
        'author_alias', seed.author_alias,
        'note', 'Demo social post seeded for event workspace presentation only'
    )
FROM tmp_energy_rally_seed AS seed
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
    source_metadata = EXCLUDED.source_metadata;

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
    '4a897de9-f136-4e25-bc87-06c2920473c8'::uuid,
    doc.id,
    0.92,
    0.86,
    0.88,
    0.42,
    FALSE,
    NULL
FROM tmp_energy_rally_seed AS seed
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
    duplicate_of_document_id = EXCLUDED.duplicate_of_document_id;

DELETE FROM opinion_records AS opinion
USING raw_documents AS doc
JOIN tmp_energy_rally_seed AS seed
  ON seed.platform = doc.platform
 AND seed.source_id = doc.source_id
WHERE opinion.event_id = '4a897de9-f136-4e25-bc87-06c2920473c8'::uuid
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
    '4a897de9-f136-4e25-bc87-06c2920473c8'::uuid,
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
FROM tmp_energy_rally_seed AS seed
JOIN raw_documents AS doc
  ON doc.tenant_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid
 AND doc.platform = seed.platform
 AND doc.source_id = seed.source_id;

UPDATE events AS event
SET
    last_seen_at = GREATEST(
        event.last_seen_at,
        '2026-07-22T17:11:00Z'::timestamptz
    ),
    evidence_count = (
        SELECT COUNT(*)
        FROM event_documents
        WHERE event_id = event.id
    )
WHERE event.id = '4a897de9-f136-4e25-bc87-06c2920473c8'::uuid
  AND event.tenant_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid;

COMMIT;
