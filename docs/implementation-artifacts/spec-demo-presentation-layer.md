---
title: '데모 프레젠테이션 층 — UX 계약을 7개 데모 출력에 반영'
type: 'feature'
created: '2026-07-28'
status: 'done'
baseline_commit: '0c92b84f31af5babcda3438a61a215b38e17a1aa'
context:
  - '{project-root}/docs/REVIEW_PLAYBOOK.md'
  - '{project-root}/docs/planning-artifacts/ux-designs/ux-thinq-onme-2026-07-28/EXPERIENCE.md'
  - '{project-root}/docs/planning-artifacts/ux-designs/ux-thinq-onme-2026-07-28/DESIGN.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** UX 계약(final)이 7장면 프레젠테이션 층을 정의했지만 데모 스크립트 7개는
각자 `_emit`을 중복 정의한 무색·비구조 출력이다. 심사위원 가독(전이 1행씩·판정 기호·
정직 표기 슬롯·S7 배지 금지)이 코드에 없다.

**Approach:** 공용 모듈 `demo_ui.py`(순수 stdlib)를 신설해 scene_header /
transition_row / honesty_footer / verdict(✓✗⏸) / held_summary / boundary_table /
evidence_block을 제공하고, 7개 데모의 **출력 계층만** 이를 쓰도록 치환한다.

## Boundaries & Constraints

**Always:**
- 기존 데모 로직·검증·rc 불변 — 출력 계층만 교체. `home_profile/` 수정 금지
- 기존 테스트가 단언하는 문자열 토큰 보존 (거부/보류/이전됨/참조 어댑터/실기기 아님/
  재등록/원격/잠든 뒤에도/seq=/차단 등) + 396 passed 유지
- `dev_`/`seq=` 스트림 라인의 접두·형태 불변 (test_demo_night_banner_rule의 스트림
  검출 규약). 배너 규약 유지: 경계마다 1회, 스트림 라인에 배너 금지
- 판정은 항상 기호+색 병기(색맹 대비). 색은 5 의미역만(fg/dim/success/blocked/held),
  비TTY·NO_COLOR·cp949 위험 시 자동 무색(테스트는 capsys라 무색 경로)
- PLAYBOOK 교훈 1·3: 프레젠테이션 층은 **표시만** 한다 — 값을 만들거나 기본값으로
  채우지 않는다. 실패 경로에서도 실측 결과만 출력
- S7: "완료"류 배지 문자열 출력 금지 — 두 축(복원 시도 결과·잔류 스캔 결과) 실측만
- 확정 마이크로카피 6종(EXPERIENCE.md Voice and Tone) 각 장면에 유지/삽입
- 모든 출력은 console_safe 경유 (cp949 안전)

**Ask First:**
- 기존 테스트 단언 문자열 자체를 바꿔야만 하는 상황이 오면 중단하고 확인
- 새 외부 의존(rich/colorama 등)이 필요해 보이면 중단 (원칙: 무의존)

**Never:**
- demo_routine.py 마이그레이션 (범위 밖 — deferred-work에 기록)
- 애니메이션·이모지 남용·장식색 추가 (DESIGN.md Don'ts)
- --offline 처리·offline_guard 흐름 변경

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| TTY+VT 지원 | 대화형 실행 | ANSI 5색 + 기호 | N/A |
| capsys/파이프 | 비TTY | 무색, 기호만 — 기존 단언 전부 통과 | N/A |
| NO_COLOR=1 | 환경변수 | 무색 강제 | N/A |
| S3 항등식 | transferred+held ≠ 총계 | 실측값 그대로 출력 + 불일치 경고 행 | 값 조작 금지 |
| S7 부분 폐기 | residual_records > 0 | 잔류 n건 실측 표기, 축2 ✗ | "완료" 미출력 |
| offline 위반 | OfflineViolation | 기존 ⚠️ 경로 유지, rc=1 불변 | 기존과 동일 |

</frozen-after-approval>

## Code Map

- `demo_ui.py` -- 신설. 프레젠테이션 층 단일 출처 (색·기호·컴포넌트 7종)
- `appliance_sim/core.py` -- console_safe·SIMULATOR_BANNER 재사용 (수정 없음)
- `demo_night.py` -- S1: scene_header+transition_row(Job 대응)+honesty_footer. 스트림 라인 불변
- `demo_reinstall.py` -- S2: 3장면 헤더+마이크로카피 "개입할 자리가 없다"
- `demo_relocate.py` -- S3: held_summary(이전+보류=전체, 사유 필수)
- `demo_onboard.py` -- S4: 요구하는 것 vs 않는 것 대비 표+"만들 자리가 없다"
- `demo_residency.py` -- S5: 소재 4행 표+"옮길 것이 없다"
- `demo_relay.py` -- S6: boundary_table(막는/못 막는 동일 무게)
- `demo_revoke.py` -- S7: evidence_block(축1 복원·축2 잔류, 배지 금지)
- `tests/test_demo_ui.py` -- 신설. 컴포넌트 단위 + I/O 매트릭스 케이스
- `tests/test_night_scenario.py` 외 6종 -- 수정 없이 통과해야 함 (회귀 게이트)

## Tasks & Acceptance

**Execution:**
- [x] `demo_ui.py` -- 색 해석(TTY/NO_COLOR/VT enable)·verdict·scene_header·
      transition_row·honesty_footer·held_summary·boundary_table·evidence_block 구현
      -- 단일 출처, 7 스크립트 중복 제거의 기반
- [x] `tests/test_demo_ui.py` -- I/O 매트릭스 6케이스 + evidence_block "완료" 부재
      단언 + 무색 경로 스냅샷 -- 층 자체의 계약 고정
- [x] `demo_night.py` -- S1 치환 (스트림 라인·배너 규약 보존) -- 절정 장면 가독
- [x] `demo_reinstall.py`, `demo_relocate.py` -- S2·S3 치환 -- P-2 쌍
- [x] `demo_onboard.py`, `demo_residency.py` -- S4·S5 치환 -- P-3 쌍
- [x] `demo_relay.py`, `demo_revoke.py` -- S6·S7 치환 -- 보안 쌍
- [x] `docs/implementation-artifacts/deferred-work.md` -- demo_routine.py 이관 항목 추가

**Acceptance Criteria:**
- Given 전체 테스트, when `pytest`, then 396 + 신규 전부 passed, 회귀 0
- Given 비TTY 실행, when 7개 데모 각각 `main([])`(및 --offline 보유 5종 플래그 포함),
  then rc 기존과 동일·기존 단언 토큰 전부 존재
- Given S7 실행(정상 폐기), when 출력 검사, then "완료" 문자열 부재 + 축1·축2 실측
  결과 행 존재
- Given S3 실행, when 출력 검사, then 이전 n·보류 m·전체 N 항등식 행 + 보류 각 행 사유
- Given S6 출력, when 막는/못 막는 블록 비교, then 행 수·서식 동일 무게

## Design Notes

- 색: `\x1b[…m` 직접, Windows는 `os.system('')` 아닌 ctypes VT enable 시도 후 실패 시
  무색 폴백. 판정 기호는 색과 무관하게 항상 출력
- transition_row 형식: `  {장면표기} {기호} ({코드키: 값})  — {Job 대응}` 단,
  demo_night의 기존 `dev_…`/`seq=…` 스트림 라인은 그대로 두고 **주변에** 층을 입힌다
- evidence_block: 축별 `axis(label, measured, ok)` 입력 — 결론 문자열을 층이 합성하지
  않는다 (교훈 1: 호출자가 준 실측만)

## Verification

**Commands:**
- `python -m pytest -q` -- expected: 396+신규 passed, 0 failed
- `python demo_night.py --offline` -- expected: rc 0, Job 문장·차단·전이 4행 가독 출력
- `python demo_revoke.py --offline` -- expected: rc 0, "완료" 부재, 두 축 실측 행

## Suggested Review Order

**프레젠테이션 층 (단일 출처)**

- 색·기호·폴백의 전 규칙이 이 파일 하나에 있다 — 진입점
  [`demo_ui.py:1`](../../demo_ui.py#L1)

- cp949 폴백: 기호가 '?'로 소실되면 판정 정보가 통째로 사라진다 (리뷰 High 수정)
  [`demo_ui.py:95`](../../demo_ui.py#L95)

- VT enable 캐시 + NO_COLOR 존재 판정 (리뷰 Med 수정)
  [`demo_ui.py:53`](../../demo_ui.py#L53)

- evidence_block — "완료" 배지를 구조적으로 낼 수 없는 형태
  [`demo_ui.py:150`](../../demo_ui.py#L150)

**판정 = 실측 (교훈 1)**

- 전이 판정이 스냅샷 실측 대조 — 예고가 아니라 결과
  [`demo_night.py:145`](../../demo_night.py#L145)

- 상수 ok 제거 — 연결 수 실측 대조로 (리뷰 수정)
  [`demo_onboard.py:69`](../../demo_onboard.py#L69)

**실패 경로 진실 (교훈 3)**

- 재생 통과 시 rc 1 — 뚫린 데모를 성공으로 끝내지 않는다 (리뷰 수정)
  [`demo_relay.py:68`](../../demo_relay.py#L68)

- 복원 오류 표기 — 증거 오염을 숨기지 않는다 (리뷰 수정)
  [`demo_revoke.py:91`](../../demo_revoke.py#L91)

**S3 항등식 · S6 동일 무게**

- held_summary — 불일치 시 값 미조작 + 경고 행
  [`demo_ui.py:124`](../../demo_ui.py#L124)

- 미지 kind 크래시 방지 폴백 (리뷰 High 수정)
  [`demo_relocate.py:126`](../../demo_relocate.py#L126)

**주변부**

- 층 계약 고정 테스트 15종 (I/O 매트릭스 + 리뷰 패치 고정)
  [`test_demo_ui.py:1`](../../tests/test_demo_ui.py#L1)

- 이월 2건 (소급 판정 구조·전각 정렬)
  [`deferred-work.md:1`](deferred-work.md#L1)
