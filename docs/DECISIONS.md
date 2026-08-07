# 의사결정 인덱스

현재 확정 상태는 [CX_DEFINITION.md](CX_DEFINITION.md), 결정의 "왜"는 아래 미팅 기록 참조.
새 미팅 기록은 `meetings/YYYY-MM-DD_slug.md`로 추가하고 여기 한 줄 등록한다.

| 날짜 | 결정 | 기록 |
|---|---|---|
| 2026-07-21 | 주제 확정 "Home Follows You" — 실VOC 기반, Red Team·Pre-mortem 통과 | CX_DEFINITION §1 (검증 과정은 세션 로그) |
| 2026-07-21 | P-2 정규식 정밀화 (오탐 16.1% 적발 → 1.37%로 정정) | [evidence-verification](meetings/2026-07-21_evidence-verification.md) §1 |
| 2026-07-21 | 페르소나 P1 가상 인구통계 삭제 — 설문 검증으로 이관 | [evidence-verification](meetings/2026-07-21_evidence-verification.md) §2 |
| 2026-07-21 | 파일럿(5,000) → 본수집(74,434) 개정, † 수치 재분석 대기 | [evidence-verification](meetings/2026-07-21_evidence-verification.md) §3 |
| 2026-07-21 | 네이버는 토픽 분석 제외 — P-2 심층·정성 증언 전용 | [crawl-strategy](meetings/2026-07-21_crawl-strategy.md) §1.1 |
| 2026-07-21 | 키워드 매트릭스 4축 재설계, 유효율 기준 강화 — C축만 채택(20.9%) | [crawl-strategy](meetings/2026-07-21_crawl-strategy.md) §2 |
| 2026-07-21 | 분석 순서: ThinQ 재분석 → 네이버 정성 → SmartThings 토픽(3순위) | [crawl-strategy](meetings/2026-07-21_crawl-strategy.md) §1.2 |
| 2026-07-22 | PostgreSQL 도입 — **발견 트랙 전용**(B 분석결과 + C 실행이력), Epic 5로 분리해 발표 서사 밖, Docker 호스팅. 처방 트랙은 AST 테스트로 차단 | [postgres-portfolio-track](meetings/2026-07-22_postgres-portfolio-track.md) |
| 2026-07-23 | ble_bless.py **미구현 표기 유지**(삭제 안 함) — 정직 표기 서명·AST 경계 반례·회귀 테스트 4건 자산. Epic 3/가민 실기기 연동 시 재평가 | [ble-bless-retention](meetings/2026-07-23_ble-bless-retention.md) |
| 2026-07-23 | 온보딩 **재온보딩 거부** — 빈 워치 전제. `put_records`가 merge라 유령 레코드가 잔류해 데이터 소재 보고가 어긋난다. 재설정은 **폐기(4.4) → 재온보딩** | [4-1 파티 리뷰](implementation-artifacts/4-1-accountless-onboarding.md#review-findings-party-code-review-2026-07-23--code-review-crew) |
| 2026-07-28 | **기기 별칭 = 로컬 표시층 전용 허용** — 프로필·캐리어·이동 경로 진입 금지, `FORBIDDEN_KEY_FRAGMENTS` 무변경(표시층 자체는 미구현·설계). 근거: PROFILE_SCHEMA v2 "표시용 이름은 프로필 밖" + 리뷰 F1. 별칭 비이전은 FR7의 증거("옮길 것이 없다") | [UX 계약](planning-artifacts/ux-designs/ux-thinq-onme-2026-07-28/EXPERIENCE.md) §손목 1장 |
| 2026-07-28 | **`"owner"` 과잉 차단 유지** — 별칭이 프로필 밖에서 해결되므로 예외 필요성 소멸. "우회할 이름을 찾지 말고 필요성을 되물어라" 규약 존속 | [UX 계약](planning-artifacts/ux-designs/ux-thinq-onme-2026-07-28/EXPERIENCE.md) §손목 1장 |
| 2026-07-28 | **UX 계약 확정** — 주 계약 = 데모 CLI 프레젠테이션 층(대본 §6~§12 7장면 1:1), 제품 UI는 "손목 1장" 스케치만(미구현 표기). 미구현 화면 추가 창작 금지 | [DESIGN.md](planning-artifacts/ux-designs/ux-thinq-onme-2026-07-28/DESIGN.md)·[EXPERIENCE.md](planning-artifacts/ux-designs/ux-thinq-onme-2026-07-28/EXPERIENCE.md) |
| 2026-07-31 | **성숙도 라벨 확정 — "PoC / TRL 3~4"** + 문서 용어 통일(프로토타입→시뮬레이터 PoC). "MVP·파일럿(제품 단계)" 발화 금지. 설문 "파일럿"은 조사방법론 용어로 존치, 과거 기록 미수정 | [MATURITY_POSITION.md](MATURITY_POSITION.md) |
| 2026-08-06 | **설문 트랙 종료 — NDA로 응답 수집·활용 금지** (daria 확인). 대안 A+B 채택: T2 "가설 — 검증 미실행(NDA)" 동결(기각 아님) + 공개 2차 자료로 배경만 보강(`[공개출처]`, 검증 아닌 정황). C(합성패널 hypothesis 모드 발표 활용)는 기각. H3는 VOC 대체 불가 실측 확인(혼수 4·입주 2건/12,585). VOC 74,434건 계보는 무관·유효. TRL 판정 무영향 | [SURVEY_TRACK_CLOSURE.md](SURVEY_TRACK_CLOSURE.md) |
| 2026-08-06 | **발표 서사 뼈대 확정 — 발견→정의→Key Accelerator→증명** (파티, daria 확정). 심사자=채용 담당(인사팀+기술 면접관 **동석**) → 평가 대상은 제품이 아니라 사람. 자료는 나누지 않고 **위아래 3층**(리크루터 한 줄 / 기술 면접관 근거 / 주머니=질문 시 실행). **Key Accelerator = "Pain 3개의 공통 원인을 치는 단일 지렛대"** — CX 보고서와 PRD·MVP 범위 사이 자리(산출물 특강 p.6~7 순서 근거). 단, 이 용어는 산출물 자료 44p·LG 공개자료 어디에도 없음 → **사내 용어 취급, 정의 선언 필수** | [PRESENTATION_SPINE.md](PRESENTATION_SPINE.md) |
| 2026-08-06 | **MVP 동음이의 분리 — 산출물 특강 정의를 정본으로** (daria 확정: "심사 가이드가 우선"). **"MVP 범위"**(최소 완성 핵심 기능 범위, 산출물 특강 p.7) = 정당한 산출물 용어로 **채택**. **"MVP를 만들었다"**(제품 단계 = 실사용자·출시) = **금지 유지**. 파일럿 동음이의 처리(§7.1) 선례 그대로 적용 | [MATURITY_POSITION §7.1](MATURITY_POSITION.md) |
| 2026-08-06 | **ThinQ API 대응 — 주 전송 경로 채택 불가**. LG가 2024-12 ThinQ API 공식 개방(산출물 특강 p.42). 그러나 흐름이 "사용자→**서버**→ThinQ API→가전"이라 **P-1(클라우드 SPOF)을 그대로 재현** — 주 전송으로 쓰면 온바디 논지가 붕괴한다. 예상 질문("공개됐는데 왜 안 썼나") 답변 확정. daria 지시로 **연동은 진행하되 역할은 미확정** — 방 추천은 A(대조군·실증: 실기기를 API로 연결 후 서버를 끊어 죽는 것을 실증, 옆에서 온바디는 생존 → 시뮬레이터 한계를 넘어 TRL 상승 여지) | [PRESENTATION_SPINE §4](PRESENTATION_SPINE.md) |
| 2026-08-06 | **데이터 출처 정본 워딩 확정 — "공개 앱스토어에서 직접 크롤링한 리뷰 74,434건"** (파티, daria 확정). 출처+방법+규모 3요소 필수. **"고객 데이터" 표현 금지** — 사내 데이터로 오해되어 NDA 준수 사실이 정반대로 읽힌다(정직 표기가 아니라 본인 리스크 관리). "크롤링"은 유지 — 출처가 앞에 붙으면 오해가 차단되고, 직접 수집 실행 증거이자 재현 가능성 신호가 된다 | [SURVEY_TRACK_CLOSURE §6.0](SURVEY_TRACK_CLOSURE.md) |
| 2026-08-06 | **Pain 일반화 손실 명시 — 존재/일반화 구분 강제** (파티). 설문 목적 ②가 Pain 3종 일반화 검증이었으므로 함께 소실. Pain **존재**는 유효(계보 분리 확인), **전체 사용자 일반화는 주장 금지**. 선택 편향 질문 대비 방어 3종은 신규 제작 없이 기존 데이터에서 확정 — 대조군 상대비교(2.0배)·11년 시계열·강점 동시수집. 답변 3박자 = 약점 인정 → 그럼에도 한 것 → 못 한 건 못 했다고 끝 | [SURVEY_TRACK_CLOSURE §2.1](SURVEY_TRACK_CLOSURE.md) |
| 2026-08-06 | **B 공개 2차 자료 조사 완료 — 채택 기준 확정**: 원출처 재접속 대조 통과분만 채택하고, ①기준 연도 미상 ②원출처 미확인(인용의 인용) ③기존 실측과 수배 차이 중 하나라도 걸리면 **제외**한다(스마트홈 51.3% 제외 사례). 출처 간 불일치는 유리한 쪽 선택 금지·**병기 강제**(스마트워치 12.9% vs 33%). 민간 조사는 표본 편향 단서 필수 | [PUBLIC_STATS_B.md](PUBLIC_STATS_B.md) |
| 2026-07-28 | **페르소나 등급제(T1/T2/T3) + 타깃 이층 구조** — 근거 타깃 Night Keeper(T1) / 사업 타깃 30대 맞벌이(T2·H3). 무게중심 이동은 설문이 결정. 설문 v4(문4 세분·문7-1/7-2 신설) | [PERSONA_LADDER.md](PERSONA_LADDER.md)·SURVEY_PLAN v4 |

## ❓ 열린 질문 (사람 판단 대기 — 코드 결함 아님)

| 질문 | 배경 | 출처 |
|---|---|---|
| ~~사용자 지정 **기기 별칭** 허용 여부~~ | **닫힘 (2026-07-28)** — 로컬 표시층 전용 허용, 프로필 무변경. 위 결정표 참조 | UX 계약 |
| ~~`"owner"` **과잉 차단** 유지 여부~~ | **닫힘 (2026-07-28)** — 유지. 위 결정표 참조 | UX 계약 |
| **멀티 프로필 충돌·권한 모델** — 한 집에 두 워치·두 프로필이 같은 기기를 두고 선호가 다를 때 누가 이기는가 | Home Starter Couple 시나리오 3("Home Takes Care of Us")이 요구. Epic급 신규 설계 — 발표에선 "다음 단계"로만 발화 | [PERSONA_LADDER.md](PERSONA_LADDER.md) §3 |

## 운영 원칙 (미팅에서 확립)
1. **주제가 수집·분석 스펙을 정한다** — 데이터량은 목표가 아니다.
2. **자동 지표는 눈검수로 교차 확인한다** — P-2 오탐 16.1%, 유효율 40%→10%대 사례.
3. **발견=데이터 / 진단=분석 / 처방=설계**의 경계를 문서에 명시한다.
4. **정정 이력은 숨기지 않는다** — 수치가 바뀐 경위를 미팅 기록으로 남긴다.
5. **페르소나 논의는 계측기 마감 전 소집한다** — 설문·크롤링 스펙이 닫히기 전에
   페르소나 변동 가능성을 먼저 묻는다 (2026-07-28 회고: 변동이 설문 배포 직전
   도착한 것은 운이었다).
