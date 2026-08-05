-- RiskTrace demo seed
-- Target event:
--   bcc8d804-3281-43b3-9ed3-0c54bb2b5595
--   连平《房地产市场有望缓跌走稳》
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
        WHERE id = 'bcc8d804-3281-43b3-9ed3-0c54bb2b5595'::uuid
          AND tenant_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid
    ) THEN
        RAISE EXCEPTION
            'Target event % for tenant % not found',
            'bcc8d804-3281-43b3-9ed3-0c54bb2b5595',
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
    '566b84ad-5d24-4a83-854d-c497862ea5ed'::uuid,
    '8cbdd30a-669c-4aff-aa52-46d60c7a5be6'::uuid,
    'weibo',
    'demo-realestate-outlook-20250307-social-001',
    '2025-03-07T11:15:00Z'::timestamptz,
    '2025-03-07T11:15:00Z'::timestamptz,
    '宏观经济观察',
    '62bc657b038d34ea7d1c19d7943d3333f6041f06005bcb448abbb2125003567e',
    '微博热议：房企投资回报率首次转负意味着行业逻辑彻底变了',
    '连平这篇报告里最触目惊心的数字不是销售面积跌12.9%，而是房企平均投入资本回报率首次转负（-0.95%）。这意味着整个行业的商业模式已经不成立了——不是流动性问题，是商业模式问题。政策能解决流动性，但解决不了商业模式。',
    '15cea9ed9f5b4c597ff6e9539f0eee639dbf741ae8fb021195d73780e7a8ac19',
    456,
    134,
    78,
    'bearish',
    'negative',
    '房企投资回报率首次转负，行业商业模式已不成立，政策无法解决',
    'opinion',
    '不是流动性问题，是商业模式问题。',
    0.76,
    '0eb2e0510fd31047fc49f05ba1cd1efca6c5906a50166278cd60f0e9ab9912f5'
),
(
    'fe480295-a352-428c-96fa-09de4a09053c'::uuid,
    'f30be2aa-927b-4b0f-804a-bbbea00aca0c'::uuid,
    'xueqiu',
    'demo-realestate-outlook-20250307-social-002',
    '2025-03-07T11:28:00Z'::timestamptz,
    '2025-03-07T11:28:00Z'::timestamptz,
    '地产研究达人',
    '71440b6ddf897e9b549a8b02a592ece9a33b7b8b466af2f07f55f49ca25ba963',
    '雪球讨论：3000亿再贷款只用了162亿=收储价格谈不拢',
    '连平报告揭示了一个被忽视的数据：央行3000亿保障性住房再贷款，截至9月只用了162亿，利用率5.4%。为什么？因为收储价格谈不拢——房企不愿亏本卖，地方政府没钱补差价。政策给了子弹但没人开枪，因为找不到靶心。',
    '84d9da6c9b3aa8fa12cbd9c2b934cd2a6dd2879a8fb0588f3c12ebf7d5cab735',
    378,
    102,
    56,
    'bearish',
    'negative',
    '3000亿再贷款利用率仅5.4%，收储价格谈不拢是核心障碍',
    'opinion',
    '政策给了子弹但没人开枪，因为找不到靶心。',
    0.73,
    '319d6fd0a6bece1be1433ca4660d31f49d4939de398280138dca982c1fed5493'
),
(
    'c5df173b-e19e-4027-b69e-b997315f304b'::uuid,
    '64e1fc72-2940-436a-b5ba-4c3917744c7f'::uuid,
    'eastmoney_guba',
    'demo-realestate-outlook-20250307-social-003',
    '2025-03-07T11:42:00Z'::timestamptz,
    '2025-03-07T11:42:00Z'::timestamptz,
    '被套的地产股投资者',
    'b2a1b2f8660f8f2be084db75dc1a2081fc087b9855972f61ffdb54216d699b0f',
    '股吧热帖：房地产拖累GDP 1.36个百分点，我持有的地产股还能回本吗',
    '连平说房地产投资拖累名义GDP增速1.36个百分点，从业人员减少10-15万、产业链近100万。这种级别的行业收缩不是一两年能逆转的。我持有的万科、保利全被深套，现在的问题是该割还是继续扛？感觉无论怎么选都是错。',
    '73f6257867e250965c1500e7ace512d935e323b74ee8aebf48dc9132ceb955be',
    423,
    178,
    89,
    'bearish',
    'negative',
    '房地产拖累GDP 1.36个百分点，行业收缩非一两年能逆转',
    'opinion',
    '无论怎么选都是错。',
    0.71,
    '7e4256bfe5ae05c53894bb98cd1db04101313ff5dfe77568c2e33dde553c1b73'
),
(
    'b549f5bf-4551-4263-a009-76c5492fefd6'::uuid,
    'd799c00a-59ef-4cef-84e0-2f14775cfd49'::uuid,
    'weibo',
    'demo-realestate-outlook-20250307-social-004',
    '2025-03-07T11:55:00Z'::timestamptz,
    '2025-03-07T11:55:00Z'::timestamptz,
    '就业市场观察员',
    '6746d97d987a4183d529b183822257c478432b12d94a00f6d199ee4d0d2adb5c',
    '微博讨论：房地产减少100万就业才是真正的社会风险',
    '连平测算2024年房地产产业链减少近100万就业。这100万人里大部分是中年男性农民工，再就业能力有限。他们失业意味着家庭消费断崖式下降——一个人失业影响一个家庭的消费，100万人就是100万个家庭的消费萎缩。这才是房地产下行最大的社会成本。',
    'f64d8d7c1b5eeaebf6c2f05d5bf6998fc327c0a8741662b9f091d8fc44343a60',
    345,
    98,
    52,
    'bearish',
    'negative',
    '产业链减少100万就业，家庭消费断崖式下降是最大社会成本',
    'opinion',
    '100万人就是100万个家庭的消费萎缩。',
    0.72,
    'e7b4614e45985d70f716ae60c974ee03f68289e8a9b2beea6a316534deecbb00'
),
(
    'efb23c33-1e82-440c-b81b-82ea554e0e59'::uuid,
    'fcf3bf78-0f1e-4f88-b4e5-e9e0b40a26cb'::uuid,
    'xueqiu',
    'demo-realestate-outlook-20250307-social-005',
    '2025-03-07T12:08:00Z'::timestamptz,
    '2025-03-07T12:08:00Z'::timestamptz,
    '逆向布局者',
    '07843ec77f9c9e06360d31502b251a9e07f22f0b466a11d2b6a6fa826dec2bb7',
    '雪球讨论：一线城市房价可能涨2.5%是全篇最有价值的预测',
    '连平预测2025年一线城市新房价格同比上涨2.5%，二手房止跌。如果这个判断成立，意味着一线城市已经触底。回顾历史——2015年也是一线城市率先止跌后向二三线扩散。先布局一线城市土储多的房企可能是当前最优策略。',
    '1ef85d23538db817e365fd26451d0dc4ba873f4c0577a1ccd210e2944de2add9',
    289,
    76,
    38,
    'bullish',
    'optimistic',
    '一线城市房价可能涨2.5%，参照2015年先一线后二三线扩散规律',
    'speculation',
    '先布局一线城市土储多的房企可能是当前最优策略。',
    0.69,
    'e4a9a4de0b7d0bca0a30276b780a6a5b642a0f3c3cbc9b57803bfd1b30bdb196'
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
        'seed_batch', 'demo-realestate-outlook-20250307',
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
    'bcc8d804-3281-43b3-9ed3-0c54bb2b5595'::uuid,
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
WHERE opinion.event_id = 'bcc8d804-3281-43b3-9ed3-0c54bb2b5595'::uuid
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
    'bcc8d804-3281-43b3-9ed3-0c54bb2b5595'::uuid,
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
        '2025-03-07T12:08:00Z'::timestamptz
    ),
    evidence_count = (
        SELECT COUNT(*)
        FROM event_documents
        WHERE event_id = event.id
    )
WHERE event.id = 'bcc8d804-3281-43b3-9ed3-0c54bb2b5595'::uuid
  AND event.tenant_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid;
COMMIT;
