-- Epic 5 발견 트랙 스키마 (Story 5.1)
-- 설계 근거: docs/meetings/2026-07-22_postgres-portfolio-track.md §8.3
-- 원칙: 게이트 하류 — 검증(gate)을 통과하지 못한 데이터는 이 DB에 존재하지 않는다.

CREATE SCHEMA IF NOT EXISTS ops;
CREATE SCHEMA IF NOT EXISTS mart;

-- C: 실행 이력 — 전 테이블의 FK 부모. DB가 아니면 못 하는 일(시계열·run 간 비교)의 축.
CREATE TABLE ops.runs (
    run_id        text PRIMARY KEY,
    created_at    timestamptz NOT NULL,
    data_mode     text NOT NULL,              -- real / hypothesis
    source_type   text NOT NULL,              -- google_play / synthetic_demo
    gate_status   text NOT NULL CHECK (gate_status = 'passed'),
        -- 적재 계약: 통과한 run만 들어온다. 실패 run을 넣고 거르지 않는다(회의 §8.2).
    agent_results jsonb                       -- A~F 성공/실패 + 사람 판정 로그(§8.1 두 독법)
);

-- B: 분석 결과 -------------------------------------------------------------

CREATE TABLE mart.reviews (
    run_id      text NOT NULL REFERENCES ops.runs(run_id),
    review      text NOT NULL,
    rating      smallint CHECK (rating BETWEEN 1 AND 5),
    review_date date,
    likes       integer,
    source_type text,
    tokens      text
);

CREATE TABLE mart.painpoints (
    run_id            text NOT NULL REFERENCES ops.runs(run_id),
    topic             text NOT NULL,
    freq              integer,
    avg_rating        numeric(3,1),
    mention_all_neg   numeric(5,1),   -- 언급률_전체부정기준(%) — 두 기준 명시(CLAUDE.md v2.2)
    mention_assigned  numeric(5,1),   -- 언급률_배정기준(%)
    rep_review        text
);

CREATE TABLE mart.strengths (
    run_id     text NOT NULL REFERENCES ops.runs(run_id),
    topic      text NOT NULL,
    freq       integer,
    avg_rating numeric(3,1),
    rep_review text
);

CREATE TABLE mart.competitor_reviews (
    run_id      text NOT NULL REFERENCES ops.runs(run_id),
    review      text,
    rating      smallint,
    review_date date,
    app         text NOT NULL DEFAULT 'smartthings'
);

CREATE TABLE mart.segments (
    run_id        text NOT NULL REFERENCES ops.runs(run_id),
    respondent_id integer NOT NULL,
    lg_devices    smallint,
    app_freq      smallint,
    age_band      smallint,
    has_child     smallint,
    is_renter     smallint,
    move_plan     numeric(2,1),
    bought_wedding smallint,
    p1_exp        smallint,
    p2_exp        smallint,
    p3_burden     smallint,
    has_watch     smallint,
    night_use     smallint,
    onbody_intent smallint,
    pay_intent    smallint,
    segment       smallint,
    is_synthetic  boolean NOT NULL
        -- NFR6: seg_members 300행은 합성 패널(synthetic_panel.py)이다.
        -- 실설문 도착 전까지 전부 true — 배너 규약의 자료구조 버전(회의 §8.3 경고).
);

CREATE TABLE mart.naver_testimony (
    run_id    text NOT NULL REFERENCES ops.runs(run_id),
    testimony text NOT NULL
);
