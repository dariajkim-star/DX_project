-- Epic 5 Story 5.3 — 서사 질의 세트
-- 실행: docker compose -f db/compose.yml exec -T db psql -U analyst -d discovery -f - < db/queries.sql
-- 원칙: 모든 질의는 게이트 통과 run만 본다 — WHERE 절이 계보 서사를 그대로 싣는다.

-- ── Q1. 최신 게이트 통과 run의 Pain Point 우선순위 (두 언급률 기준 병기 — v2.2 규약)
SELECT p.topic,
       p.freq,
       p.mention_all_neg  AS "언급률_전체부정(%)",
       p.mention_assigned AS "언급률_배정(%)",
       p.avg_rating
FROM mart.painpoints p
WHERE p.run_id = (SELECT max(run_id) FROM ops.runs WHERE gate_status = 'passed')
ORDER BY p.mention_all_neg DESC
LIMIT 5;

-- ── Q2. H2 크로스탭 — 이사계획 × 온바디 수용도 (⚠️ 합성 패널 여부 항상 표기)
SELECT s.move_plan          AS "이사계획",
       s.is_renter          AS "전월세",
       round(avg(s.onbody_intent), 2) AS "평균 온바디 수용도",
       count(*)             AS n,
       bool_and(s.is_synthetic) AS "전부_합성인가"   -- NFR6: 실측인 척 금지
FROM mart.segments s
WHERE s.run_id = (SELECT max(run_id) FROM ops.runs WHERE gate_status = 'passed')
GROUP BY s.move_plan, s.is_renter
ORDER BY s.move_plan DESC, s.is_renter DESC;

-- ── Q3. ThinQ vs SmartThings 월별 평점 추이 (P-2 경쟁 2.0배 열위의 시계열 무대)
SELECT date_trunc('month', r.review_date)::date AS month,
       'thinq'  AS app, round(avg(r.rating), 2) AS avg_rating, count(*) AS n
FROM mart.reviews r
WHERE r.run_id = (SELECT max(run_id) FROM ops.runs WHERE gate_status = 'passed')
  AND r.review_date IS NOT NULL
GROUP BY 1
UNION ALL
SELECT date_trunc('month', c.review_date)::date,
       c.app, round(avg(c.rating), 2), count(*)
FROM mart.competitor_reviews c
WHERE c.run_id = (SELECT max(run_id) FROM ops.runs WHERE gate_status = 'passed')
  AND c.review_date IS NOT NULL
GROUP BY 1, c.app
ORDER BY month, app;

-- ── Q4. run 간 P-1 언급률 변동 — CSV로는 불가능한 질문 ("재현성을 데이터로 다룬다")
SELECT r.run_id,
       r.created_at,
       p.mention_all_neg AS "P-1 언급률(%)"
FROM ops.runs r
JOIN mart.painpoints p ON p.run_id = r.run_id
WHERE p.topic LIKE '0\_%'          -- P-1 = 0번 토픽(연결·서버)
ORDER BY r.created_at;

-- ── Q5. 실행 이력 자체 — "AI가 낸 것을 사람이 어떻게 판정했나" (§8.1 두 독법)
SELECT run_id, created_at, data_mode, source_type,
       jsonb_object_keys(agent_results) AS agent
FROM ops.runs
ORDER BY created_at DESC;
