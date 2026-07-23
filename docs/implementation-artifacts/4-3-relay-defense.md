---
baseline_commit: 6da83a0
---

# Story 4.3: 릴레이 공격 방어

Status: ready-for-dev

## Story

As a **보안 검토자**,
I want 근접성이 위조된 원격 명령이 거부되기를,
so that "손목에 있으면 열린다"가 공격 표면이 되지 않는다.

**에픽 맥락**: Epic 4의 위협 모델 진입. 4.1·4.2(프라이버시 쌍)가 "신원을 안
넘긴다·서버에 없다"였다면, 4.3·4.4는 **보안**이다. 온바디 프로필이 로컬에서
가전을 여는 구조는 편리하지만, 근접성이 인증이 되는 순간 **릴레이 공격**이
표면이 된다 — 공격자가 근접 명령을 중계해 원거리에서 문을 연다. 4.3은 이를
막되, **완전 방어를 주장하지 않고 잔여 한계를 정직하게 문서화**한다(NFR1 AC2).
[Source: docs/planning-artifacts/epics.md#Story 4.3]

> **발표에서의 위상.** 보안 스토리의 핵심은 **정직**이다. "우리는 릴레이를 완전히
> 막았다"는 거짓이고, 심사에서 반증되면 신뢰 전체가 무너진다. 우리가 막는 것
> (replay: 캡처한 명령의 재사용)과 막지 못하는 것(실시간 relay: 신선도 창 안의
> 실시간 중계 — 거리 바운딩 하드웨어 필요, 시뮬레이터 밖)을 **선명히 구분**한다.
> 3.1 오프라인 한계 표기("프로세스 차단이지 장비 차단 아님")와 같은 규율.

## Acceptance Criteria

**AC1 — 릴레이/재생 명령 거부 (NFR1)**
**Given** 정상 근접 명령이 성공하는 상태에서
**When** 릴레이(중계) 시나리오로 원거리 명령을 재현하면
**Then** 명령이 거부된다

**AC2 — 방어 기법·잔여 한계 문서화 (완전 방어 주장 금지)**
**And** 방어 기법과 **잔여 한계**가 위협 모델 문서 1장에 기록된다

## Tasks / Subtasks

- [ ] **Task 1: 근접 게이트 — `ProximityGuard`** (AC: 1)
  - [ ] ⚠️ **기존 명령 계약을 깨지 마라.** `ApplianceState.apply_command`는 2.x부터
        토큰 없이 동작한다 — 여기에 토큰을 강제하면 기존 테스트가 전부 깨진다.
        근접 방어는 apply_command **앞단의 합성 가능한 게이트**로 얹는다(수정 아님)
  - [ ] `home_profile/proximity.py` 신설 — 챌린지-응답 신선도(freshness) 기반
        재생 방어:
        · `issue_challenge()` → 신선한 nonce 발급(가전 측). 근접한 워치만 이 값을
          제때 받는다
        · `make_proximity_token(nonce)` → 근접 워치가 만드는 토큰(현재 nonce 바인딩)
        · `ProximityGuard.verify(token)` → 토큰 nonce가 **현재 챌린지와 일치 +
          미소비**여야 통과. 통과 시 nonce 소비(1회용) → 같은 토큰 재생은 거부
  - [ ] 반환은 계약 승계: `(ok: bool, reason)` 또는 `(None, errors)`. **예외 금지**,
        fail-closed(의심스러우면 거부). 거부 사유에 토큰 원문·페이로드 금지
  - [ ] ⚠️ **막는 것과 못 막는 것을 코드 주석·docstring에 선명히.** 막는 것=replay
        (캡처 명령 재사용). 못 막는 것=실시간 relay(신선도 창 안 실시간 중계 —
        거리 바운딩 RTT 하드웨어 필요, 시뮬레이터 밖). 이 구분이 이 스토리의 정직성

- [ ] **Task 2: 위협 모델 문서 — `docs/THREAT_MODEL.md`** (AC: 2)
  - [ ] 릴레이 공격 위협 모델 1장. 구조: 위협(릴레이/재생) → 방어(챌린지-응답
        신선도) → **잔여 한계**(실시간 relay는 거리 바운딩 필요, 미구현). 완전
        방어 주장을 **명시적으로 부인**한다
  - [ ] 방어 범위표: "막는다"(replay·stale nonce·wrong nonce) / "못 막는다"
        (실시간 relay·물리적 근접 위조·손목 탈취 후 즉시 사용). `DEMO_SCRIPT §6`
        "말해도 되는 것/안 되는 것"과 같은 계보
  - [ ] NFR1 계보: 이 방어는 "손목에 있으면 무조건 열린다"를 "손목에 있고 +
        신선한 챌린지에 실시간 응답해야 열린다"로 좁힌다. 완전 제거가 아니라 표면 축소

- [ ] **Task 3: 릴레이 시나리오 데모** (AC: 1, 2)
  - [ ] `demo_relay.py` 신설 — ①정상 근접 명령(현재 nonce 응답) → 성공 →
        가전 상태 전이. ②릴레이/재생(캡처한 명령을 nonce 회전 후 재현) → **거부**.
        두 결과를 나란히 화면에
  - [ ] 화면에 **막는 것/못 막는 것**을 함께 표기 — 데모가 "완전 방어"로 읽히지
        않게(AC2 정직성). `THREAT_MODEL.md` 링크
  - [ ] 배너 규약·참조 어댑터 정직 표기 유지. 실기기 아님

- [ ] **Task 4: 테스트** (AC: 1, 2)
  - [ ] `tests/test_relay_defense.py` 신설
  - [ ] **정상 근접 성공(AC1 전제):** 현재 nonce에 바인딩된 토큰 → verify 통과 →
        apply_command 성공(가전 상태 전이 정확한 값)
  - [ ] **재생 거부(AC1):** 소비된 nonce의 토큰을 재사용 → verify 거부. apply까지
        가지 않음(원자성 — 거부되면 상태 불변)
  - [ ] **wrong nonce 거부(AC1):** 다른/옛 nonce 토큰 → 거부
  - [ ] **신선도:** 챌린지 재발급 후 옛 토큰 → 거부(1회용 nonce 소비)
  - [ ] **fail-closed:** garbage 토큰·None·형식 위반 → 거부, 예외 없음
  - [ ] **잔여 한계 문서 회귀:** `THREAT_MODEL.md`에 "못 막는다/잔여 한계/실시간
        relay/거리 바운딩" 취지 문구 존재 + "완전 방어" 무조건 주장 **부재** 단언
  - [ ] 회귀 기준선: **369 passed**(`6da83a0`, 4.2 파티 리뷰 후). 신규만큼 증가·회귀 0

- [ ] **Task 5: 문서 — 발표 대본**
  - [ ] `docs/DEMO_SCRIPT.md`에 릴레이 방어 장면(§11) 추가. `THREAT_MODEL.md` 링크.
        "막는 것/못 막는 것" 구분이 이 장면의 핵심(과장 방지)

## Dev Notes

### 🚨 이 스토리의 함정 — 먼저 읽을 것

**1. 완전 방어를 주장하면 이 스토리는 실패다.**
보안에서 "완전히 막았다"는 거의 항상 거짓이고, 심사에서 반증되면 신뢰 전체가
무너진다. 우리가 막는 것(replay)과 못 막는 것(실시간 relay)을 선명히 구분하는 것이
**이 스토리의 목표**다. AC2가 "잔여 한계 문서화"를 요구하는 이유 — 방어 자체보다
정직한 경계 설정이 평가 대상이다(3.1 오프라인 한계 표기 계보).

**2. 기존 apply_command 계약을 깨지 마라.**
`ApplianceState.apply_command`는 2.x부터 토큰 없이 동작하고 수십 개 테스트가 그에
의존한다. 토큰을 필수 인자로 넣으면 전부 깨진다. 근접 방어는 **앞단 게이트**로
합성한다 — verify 통과 후 기존 apply_command를 그대로 호출. apply_command 무수정이
회귀 0의 조건이다(ApplianceState docstring이 "인증은 Epic 4"라 예고한 그 지점).

**3. replay와 relay는 다르다 — 용어를 정확히.**
- **replay(재생)**: 공격자가 유효한 명령을 캡처해 **나중에** 재사용. 신선도(nonce
  1회용)로 **막는다**.
- **relay(중계)**: 공격자가 신선한 챌린지와 응답을 **실시간으로** 중계. 신선도로는
  **못 막는다** — 거리 바운딩(왕복 시간 측정)이 필요한데 하드웨어가 없다.
문서·데모·주석에서 이 둘을 섞으면 정직성이 무너진다. "릴레이 방어"라는 제목 아래
실제로 막는 건 replay이며, 진짜 relay의 잔여 한계를 명시한다.

**4. 결정적이되 신선해야 한다.**
nonce는 실행마다 신선해야(재생 방어의 본질) 하지만, 테스트는 결정적이어야 한다.
해법: 테스트가 `issue_challenge()`가 반환한 nonce를 받아 토큰을 만든다 — nonce
값의 무작위성에 의존하지 않고 "발급된 것에 응답"하는 흐름만 검증. 재생은 "소비된
nonce 재사용"으로 결정적으로 재현된다.

**5. 경계 — home_profile 코어, 새 모듈, appliance_sim·schema·carrier 무수정.**
`ProximityGuard`는 자족적 보안 primitive다. `proximity.py` 신설, appliance_sim은
수정하지 않고 데모/테스트에서 게이트+apply_command를 **합성**한다.

### 재사용 자산 (신규는 proximity.py·THREAT_MODEL.md·데모·테스트)

| 자산 | 위치 | 용도 |
|---|---|---|
| `ApplianceState.apply_command` | `appliance_sim/core.py:185` | 게이트 통과 후 명령 반영(무수정) |
| `ApplianceState` | `appliance_sim/core.py` | 가전 상태·이벤트(정상 명령 성공 확인) |
| 데모 하우스 패턴 | `demo_onboard.py`·`demo_reinstall.py` | 배너 4경계·정직 표기·in-process |
| 한계 정직 표기 계보 | `DATA_RESIDENCY.md`·3.1 오프라인 한계 | "막는 것/못 막는 것" 표기 |
| `_show`(값 비노출) | `appliance_sim/core.py` | 거부 사유에 토큰 원문 금지 |
| `secrets` (표준 라이브러리) | stdlib | nonce 발급(캐리어 중립·서드파티 금지 규약과 정합) |

### 파일 배치

- 신규: `home_profile/proximity.py`, `demo_relay.py`,
  `tests/test_relay_defense.py`, `docs/THREAT_MODEL.md`
- 수정: `home_profile/__init__.py`(export), `docs/DEMO_SCRIPT.md`(§11)
- `appliance_sim/`·`home_profile/schema.py`·`carrier.py` **무수정** 목표

### 테스트 규약

- 정확한 값 단언(거부/성공, 상태 전이), '단어 언급' 금지
- 재생 거부는 "소비된 nonce 재사용"으로 결정적 재현
- fail-closed: garbage 토큰 → 거부, 예외 없음
- 문서 회귀: "잔여 한계"·"못 막는다" 존재 + "완전 방어" 무조건 주장 부재
- `pytest.ini` testpaths = tests

### References

- [Source: docs/planning-artifacts/epics.md#Story 4.3] — AC 원문(NFR1)
- [Source: docs/planning-artifacts/epics.md#Epic 4] — 위협 모델
- [Source: appliance_sim/core.py:136] — ApplianceState, apply_command(무수정 대상), "인증은 Epic 4" 예고
- [Source: docs/implementation-artifacts/3-1-reinstall-restore.md] — 오프라인 한계 표기(정직 경계 계보)
- [Source: docs/DATA_RESIDENCY.md] — 구조적 사실 vs 관찰, 한계 표기
- [Source: docs/DEMO_SCRIPT.md] — 릴레이 방어 장면을 추가할 대본

## Dev Agent Record

### Agent Model Used

_(dev-story 실행 시 기록)_

### Debug Log References

### Completion Notes List

### File List

### Change Log

- 2026-07-23: Story 4.3 컨텍스트 생성. Epic 4 위협 모델 — 릴레이 공격 방어(NFR1).
  핵심 신규 = `ProximityGuard`(챌린지-응답 신선도로 replay 방어) + 잔여 한계
  문서화(실시간 relay는 거리 바운딩 필요, 미구현). 완전 방어 주장 금지가 핵심.
  베이스라인 369 passed. Status: ready-for-dev.
