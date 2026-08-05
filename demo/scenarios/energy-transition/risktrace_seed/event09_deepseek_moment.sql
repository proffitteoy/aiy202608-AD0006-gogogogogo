-- RiskTrace demo seed
-- Target event:
--   8542aadd-38cc-4b0e-9993-05ea4be6d9ee
--   21世纪经济报道《深度 | 金融业迎来“DeepSeek时刻”》
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
        WHERE id = '8542aadd-38cc-4b0e-9993-05ea4be6d9ee'::uuid
          AND tenant_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid
    ) THEN
        RAISE EXCEPTION
            'Target event % for tenant % not found',
            '8542aadd-38cc-4b0e-9993-05ea4be6d9ee',
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
    '798c667d-8523-4894-9e64-b6e99f1c8776'::uuid,
    '91e416fd-09a3-491f-b771-0239cbe05cee'::uuid,
    'weibo',
    'demo-deepseek-moment-20250214-social-001',
    '2025-02-14T18:15:00Z'::timestamptz,
    '2025-02-14T18:15:00Z'::timestamptz,
    '金融科技观察',
    'beae8cd51a61870f5b6761feb27dab148c413d96a857d15e5402216750070d0f',
    '微博热议：中小银行抢跑DeepSeek是营销还是真干？',
    '21经济网这篇报道写得很全面。但有个细节值得玩味——中小银行率先部署，六大行只有邮储官宣。这到底是中小银行更积极，还是大行被监管限制了？我倾向后者。大行数据安全要求更高，不可能像城商行那样随便部署一个API就发公告。',
    'cd3046928c98bd7c24bb5cce38de627ca93c9c3867469048db21d98c80decf8f',
    378,
    112,
    56,
    'wait',
    'neutral',
    '中小银行抢跑DeepSeek可能是营销行为，大行受监管限制更谨慎',
    'opinion',
    '大行数据安全要求更高，不可能像城商行那样随便部署一个API就发公告。',
    0.71,
    'd5f3f5317d14faabf6f28687913f15e7d02b40d140975922a4827d401d183985'
),
(
    'ed1d2f48-92c8-43cc-a3a1-e9127a758a27'::uuid,
    '0d4ad80f-061e-434d-908b-96db8fc4309c'::uuid,
    'xueqiu',
    'demo-deepseek-moment-20250214-social-002',
    '2025-02-14T18:28:00Z'::timestamptz,
    '2025-02-14T18:28:00Z'::timestamptz,
    '银行业研究员',
    '6e036cce4fbdd425f5d0d4f242e5b7322c8183076fdee90151d0e084fed7731f',
    '雪球讨论：苏商银行效率提升20%是唯一硬数据',
    '整篇报道里最有价值的是苏商银行那个数字——信贷材料识别准确率提升至97%，审核效率提升20%。这是目前唯一有量化效果的案例。其他银行说的“90余个应用落地”都是虚的，没有量化指标。真正能说服市场的是效率提升数据，不是应用数量。',
    '8ea6d05a7f5c9f574e212ee8d1011d16ae80e971a393caaf5dc5c0551b253ef8',
    312,
    89,
    45,
    'bullish',
    'optimistic',
    '苏商银行效率提升20%是目前唯一有量化效果的案例，证明AI可提质效',
    'opinion',
    '真正能说服市场的是效率提升数据，不是应用数量。',
    0.73,
    '515085c4b5ecf724b39908c6456259d0d1af09a689cfc8f2747ef5f6155bb593'
),
(
    '1190f2fc-c830-4649-912f-b853436287e2'::uuid,
    '2eb63795-6102-4c51-a0ac-a13113d8ef8b'::uuid,
    'eastmoney_guba',
    'demo-deepseek-moment-20250214-social-003',
    '2025-02-14T18:42:00Z'::timestamptz,
    '2025-02-14T18:42:00Z'::timestamptz,
    '被AI焦虑的金融人',
    '3d8789f89f0f57202d2ecf12e39069284e7e5fe4caef6a5f13e598260f84f364',
    '股吧热帖：经济学家说“达不到这个水平就可以说拜拜了”太扎心',
    '报道里那位经济学家在朋友圈说“让DeepSeek做了两道经济学题目，给出几近完美的答案。作为经济金融领域的研究者，如果达不到这个水平，甚至只是简单的收集新闻，就可以说拜拜了。”我就是做资料收集的，看完这段直接失眠了。但冷静想想——AI能做的是信息整合，不是判断。判断力才是护城河。',
    'b128e0b8f7dd83639bb076f8fb27e25ea3f33db7eb46774e9bf488def7661e07',
    456,
    167,
    89,
    'bearish',
    'negative',
    '经济学家说“达不到水平就可以说拜拜”，引发金融从业者焦虑',
    'opinion',
    '判断力才是护城河。',
    0.7,
    'cf890f97c84688fcc82a8d346a0146fdf8f2e305c2f4afc25323085fb2b97224'
),
(
    '1584e806-b22b-433e-9a7e-066fe855f62c'::uuid,
    'b3c1d792-9183-4a08-b305-55c3e5a57fe3'::uuid,
    'weibo',
    'demo-deepseek-moment-20250214-social-004',
    '2025-02-14T18:55:00Z'::timestamptz,
    '2025-02-14T18:55:00Z'::timestamptz,
    '银行IT部门员工',
    '24715e236887ad1c4cd7029c0eea2481ce69969040bfd5f03e535f26f2ff4a26',
    '微博讨论：张然说“数据安全是核心约束”这句话才是大实话',
    '中信银行张然说的“数据安全和隐私要求这一核心约束依然存在，银行未来仍不会直接放弃自行搭建设施”——这句话才是大实话。银行不可能把客户数据放到外部大模型上跑，这是底线。所以DeepSeek对银行的价值上限就是“内部辅助工具”，不可能成为核心系统。',
    'e9d11e6f70636756c6cf3f41e7f9bae771df42d92dd59c35f64074375fe5aad3',
    289,
    78,
    34,
    'bearish',
    'negative',
    '银行不可能把客户数据放到外部大模型上，DeepSeek价值上限是辅助工具',
    'opinion',
    'DeepSeek对银行的价值上限就是“内部辅助工具”，不可能成为核心系统。',
    0.72,
    'd6be12697d6f99ce57a0af5ae395178eb2ce99c45909e61a9c88a86a102ee4dc'
),
(
    '380d5b6f-c1f9-4054-8d0c-d718ec744c87'::uuid,
    '7543de62-f004-4914-b034-36e4f308b101'::uuid,
    'xueqiu',
    'demo-deepseek-moment-20250214-social-005',
    '2025-02-14T19:08:00Z'::timestamptz,
    '2025-02-14T19:08:00Z'::timestamptz,
    '技术理想主义者',
    'fca81fa03fed9965786f3d3f626517f610cfc2a7e6733cb5304595387640eade',
    '雪球讨论：“像教小孩一样训练AI”这个比喻太精准了',
    '报道里有个比喻特别精准——“AI和孩子是一样的。你教他什么，他的内核是什么，在不在法律和伦理的框架范围内，怎么训练和控制？”这才是AI金融应用的核心命题。不是模型多强，而是谁在训练、怎么训练、训练数据是否合规。DeepSeek只是工具，真正决定成败的是训练它的人。',
    '2e0bd8830b58836e4c98ad0b4c40882095e2feca84ac94ae9492b4ee14abdca6',
    234,
    67,
    28,
    'bullish',
    'optimistic',
    'AI金融应用的核心不是模型强弱而是训练数据和训练方法',
    'opinion',
    'DeepSeek只是工具，真正决定成败的是训练它的人。',
    0.69,
    '10851d3469fe463477fa06515d7dc6695cbec245328e2ec055b946ed176284c6'
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
        'seed_batch', 'demo-deepseek-moment-20250214',
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
    '8542aadd-38cc-4b0e-9993-05ea4be6d9ee'::uuid,
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
WHERE opinion.event_id = '8542aadd-38cc-4b0e-9993-05ea4be6d9ee'::uuid
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
    '8542aadd-38cc-4b0e-9993-05ea4be6d9ee'::uuid,
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
        '2025-02-14T19:08:00Z'::timestamptz
    ),
    evidence_count = (
        SELECT COUNT(*)
        FROM event_documents
        WHERE event_id = event.id
    )
WHERE event.id = '8542aadd-38cc-4b0e-9993-05ea4be6d9ee'::uuid
  AND event.tenant_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid;
COMMIT;
