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
