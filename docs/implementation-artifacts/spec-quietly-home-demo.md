---
title: 'Quietly Home 데모 — 부부 2프로필 × 이사: 설정은 한 번, 집은 계속 바뀌어도'
type: 'feature'
created: '2026-07-28'
status: 'done'
baseline_commit: '42e0b57'
context:
  - '{project-root}/docs/REVIEW_PLAYBOOK.md'
  - '{project-root}/docs/PERSONA_LADDER.md'
---

<frozen-after-approval reason="human-owned intent — daria 재프레임(LTV·락인) 파티 합의 2026-07-28">

## Intent

**Problem:** Home Starter Couple(T2)·H2×H3에 실물 데모가 없다. Quietly Home의 핵심은
"한 번의 밤"이 아니라 **"한 번의 설정이 이사를 건너 생존한다"**(daria 재프레임 —
이사=이탈 순간, 설정 자산=전환 비용, LTV).

**Approach:** `demo_quietly.py` 신설 — 부부 2프로필(각자 캐리어=각자 워치, 선호값
상이) × 이사 1회, 4장면. 기존 조립만: onboard/persist/execute_routine/map_to_new_home
+ demo_ui. `home_profile/` 수정 금지.

## Boundaries & Constraints

**Always:** 어휘 확장 없음(KNOWN_* 그대로) · 트리거=원터치(감지·상태공유·서버 금지,
교훈 9: "알아서" 문구 금지) · 판정=실측(스냅샷·리포트 대조, 교훈 1) · 보류는 사유와
함께(held_summary) · T2 가설 라벨 병기 · 멀티프로필 충돌 안 건드림(각자 자기 프로필
실행 — "충돌 해소는 다음 단계" 명시) · 마이크로카피 "설정은 한 번, 집은 계속 바뀌어도"
· 411 passed 회귀 0

**Ask First:** 기존 데모·테스트 파일을 수정해야 하는 상황

**Never:** TV·밝기·무음 등 없는 어휘 연출 · 발표 대본(7장면) 변경 — 이 데모는 발표 밖,
H3 참이면 승격 (파티 합의)

</frozen-after-approval>

## Code Map

- `demo_quietly.py` -- 신설. 4장면: ①옛 집 두 프로필(한 번 새김) ②원터치(옛 집 실증)
  ③이사 — 각자 map_to_new_home + held_summary ④새 집 재실행(재설정 0회·선호값 생존)
- `tests/test_quietly_home.py` -- 신설. rc 0·토큰·"알아서" 부재·선호값 26/24 생존
- `home_profile/*`·`demo_ui.py` -- 재사용, 수정 없음

## Tasks & Acceptance

**Execution:**
- [x] `demo_quietly.py` -- 4장면 구현
- [x] `tests/test_quietly_home.py` -- 계약 고정

**Acceptance Criteria:**
- Given pytest, when 전체 실행, then 411+신규 passed 회귀 0
- Given 데모 실행, when 출력 검사, then 두 선호값(26·24)이 이사 후에도 각자 생존 실측
  + 보류 사유 행 + "설정은 한 번" + "알아서" 부재 + T2 가설 라벨

## Spec Change Log
