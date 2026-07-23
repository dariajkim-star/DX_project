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

## 운영 원칙 (미팅에서 확립)
1. **주제가 수집·분석 스펙을 정한다** — 데이터량은 목표가 아니다.
2. **자동 지표는 눈검수로 교차 확인한다** — P-2 오탐 16.1%, 유효율 40%→10%대 사례.
3. **발견=데이터 / 진단=분석 / 처방=설계**의 경계를 문서에 명시한다.
4. **정정 이력은 숨기지 않는다** — 수치가 바뀐 경위를 미팅 기록으로 남긴다.
