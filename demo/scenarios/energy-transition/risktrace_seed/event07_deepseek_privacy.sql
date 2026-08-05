-- RiskTrace demo seed
-- Target event:
--   e2f2e0ba-bd6d-4cf0-b41a-6e1ca6444fbf
--   安全内参《DeepSeek火爆背后：个人隐私“陷阱”与应对策略》
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
        WHERE id = 'e2f2e0ba-bd6d-4cf0-b41a-6e1ca6444fbf'::uuid
          AND tenant_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid
    ) THEN
        RAISE EXCEPTION
            'Target event % for tenant % not found',
            'e2f2e0ba-bd6d-4cf0-b41a-6e1ca6444fbf',
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
    '1cf876b7-eeec-420b-af60-ce84ecf66767'::uuid,
    '3c93a38c-ee62-48a4-8c3a-3df62bfde289'::uuid,
    'weibo',
    'demo-deepseek-privacy-20250416-social-001',
    '2025-04-16T10:15:00Z'::timestamptz,
    '2025-04-16T10:15:00Z'::timestamptz,
    '网络安全研究员',
    '084cbee07772a81c230a614b5a13c3bb27c67c98e72d980ca76388c974700210',
    '微博热议：88.9%大模型服务器“裸奔”这个数字太触目惊心',
    '安全内参这篇文章揭露的问题比媒体报道的DeepSeek热潮严重得多。88.9%的大模型服务器无需认证即可访问——这意味着你的对话记录、API密钥、甚至企业内部数据都可能被随意读取。大家都在追AI概念股，没人关心安全基础设施。',
    '2a324603a17a28ee95e42ddc00ae1483cbcbe1ec2540c350282e3d616ecbe34b',
    389,
    112,
    78,
    'bearish',
    'negative',
    '88.9%大模型服务器“裸奔”，安全基础设施严重缺失',
    'opinion',
    '大家都在追AI概念股，没人关心安全基础设施。',
    0.75,
    '5ef330c4d87452dcf0c82f6ccdf1e470f3cb1865083cf4cb12717bbbf89b7162'
),
(
    'defbc1a1-0596-4661-ad24-af548a5de97b'::uuid,
    'd48c11f2-b5b0-406c-997a-321fc1ccb9f4'::uuid,
    'xueqiu',
    'demo-deepseek-privacy-20250416-social-002',
    '2025-04-16T10:28:00Z'::timestamptz,
    '2025-04-16T10:28:00Z'::timestamptz,
    '银行风控经理',
    'c7fd7daaaf6ce755954d0fcaffbc8a837a3452e1564235721d2a6ebcd85bd633',
    '雪球讨论：算法黑箱+语料来源不清=金融AI的合规定时炸弹',
    '文章提到五个安全问题，对金融业来说最致命的是前两个：算法黑箱和语料来源。银行如果用DeepSeek做信贷审批，出了问题怎么解释？监管问“为什么拒绝这笔贷款”，你回答“AI说的”——这能过合规审查吗？',
    'bafd050534fb18731926141bcfde18f68988bf3bc5684d4322b457649d783870',
    312,
    89,
    45,
    'bearish',
    'negative',
    '算法黑箱+语料来源不清导致金融AI无法通过合规审查',
    'opinion',
    '监管问“为什么拒绝这笔贷款”，你回答“AI说的”——这能过合规审查吗？',
    0.73,
    '51181429027d67378c77e0407e6ec10684d069ca95e936ff8e92753b787946ae'
),
(
    '417c9616-4f30-4275-ba88-36cbffe77b31'::uuid,
    '693e9311-3955-4f00-aa3e-0c6f3615bf3f'::uuid,
    'eastmoney_guba',
    'demo-deepseek-privacy-20250416-social-003',
    '2025-04-16T10:42:00Z'::timestamptz,
    '2025-04-16T10:42:00Z'::timestamptz,
    '被DeepSeek坑过的散户',
    '1ced3a188bb9a4bcba06f090c32cbda387681a6f369c6cc246cc8845f2552fed',
    '股吧热帖：恶意依赖包事件说明开源不等于安全',
    '1月份有人上传了“deepseeek”恶意包，大量用户凭据泄露。这就是开源的风险——任何人都可以发布名字相似的包，下载的时候根本分不清真假。银行如果在本地部署时不做供应链审查，等于给黑客留了后门。',
    '5414368fa1f41ad34770fe28f8e2ca1041cf66535103e84a892050332b41a7a1',
    256,
    78,
    34,
    'bearish',
    'negative',
    '开源生态存在恶意包风险，银行本地部署需供应链安全审查',
    'opinion',
    '银行如果在本地部署时不做供应链审查，等于给黑客留了后门。',
    0.71,
    'c38916136adda9c0e7767bb5ad8201b71991b72130b604fd88ec58d5fb89cc2b'
),
(
    'bb87c858-7c40-4465-9f1e-bf4486a180fa'::uuid,
    '93cca6b8-e488-458f-99ce-35eec5c79db9'::uuid,
    'weibo',
    'demo-deepseek-privacy-20250416-social-004',
    '2025-04-16T10:55:00Z'::timestamptz,
    '2025-04-16T10:55:00Z'::timestamptz,
    '数据隐私律师',
    '6b3e3faef977d578a7afd8c8187b88ea8c7ea08f356d33b4ca17c9860f8186ae',
    '微博讨论：模型“记忆效应”违反个人信息保护法',
    '文章说的“记忆效应”——用户输入的个人信息被模型存储并用于后续生成——这直接违反《个人信息保护法》第47条（删除权）。银行如果用DeepSeek处理客户信息，必须建立数据隔离和擦除机制。目前大部分银行没做到这一点。',
    '3a766fd75cef225a4581ff99d9196c052edbf195a21385b9dfab7418bae813fd',
    234,
    67,
    29,
    'bearish',
    'negative',
    '模型“记忆效应”违反《个人信息保护法》删除权，银行需建数据隔离机制',
    'opinion',
    '目前大部分银行没做到这一点。',
    0.72,
    'e48ee93cbd794f85c9fb088b5132e14edcde5d8dec6458edc03857ce5867fa9f'
),
(
    '49fdd641-ef7c-4534-b398-311ed97bbe61'::uuid,
    '1a0415fd-aaf1-4c96-ba03-8a63514134b3'::uuid,
    'xueqiu',
    'demo-deepseek-privacy-20250416-social-005',
    '2025-04-16T11:08:00Z'::timestamptz,
    '2025-04-16T11:08:00Z'::timestamptz,
    '科技股投资者',
    'dbce88dce1f959597d2e5f59ddf34431a004808b8ca196fd96358620f85a4268',
    '雪球讨论：安全问题是AI概念股最大的下行风险',
    '大家都在炒DeepSeek概念股，但没人关注安全合规风险。一旦监管出手——比如要求所有大模型服务器必须通过安全认证——一批蹭概念的公司会直接暴雷。安全内参这篇文章是给市场敲警钟，但没人听。',
    '73d3fd58432b0b8cb533d23b8ef1e3560f8bae972087382e01bcfe4c56818831',
    289,
    82,
    41,
    'bearish',
    'negative',
    '安全合规风险是AI概念股最大下行风险，监管出手将导致暴雷',
    'speculation',
    '一旦监管出手，一批蹭概念的公司会直接暴雷。',
    0.68,
    '33d96d98cfcdc673806e64246d0eae4a020a789980dc49868f2ce632f08968e0'
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
        'seed_batch', 'demo-deepseek-privacy-20250416',
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
    'e2f2e0ba-bd6d-4cf0-b41a-6e1ca6444fbf'::uuid,
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
WHERE opinion.event_id = 'e2f2e0ba-bd6d-4cf0-b41a-6e1ca6444fbf'::uuid
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
    'e2f2e0ba-bd6d-4cf0-b41a-6e1ca6444fbf'::uuid,
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
        '2025-04-16T11:08:00Z'::timestamptz
    ),
    evidence_count = (
        SELECT COUNT(*)
        FROM event_documents
        WHERE event_id = event.id
    )
WHERE event.id = 'e2f2e0ba-bd6d-4cf0-b41a-6e1ca6444fbf'::uuid
  AND event.tenant_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid;
COMMIT;
