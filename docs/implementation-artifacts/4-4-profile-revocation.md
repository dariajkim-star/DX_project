---
baseline_commit: 10b344e
---

# Story 4.4: 분실·양도 시 프로필 폐기

Status: done

## Story

As a **워치를 잃어버린 사용자**,
I want 잃어버린 기기의 권한을 끊기를,
so that 내 집이 남의 손목에 남지 않는다.

**에픽 맥락**: Epic 4의 마지막이자 위협 모델의 완결. 4.3(릴레이 방어)이
"근접만으로는 못 연다"였다면, 4.4는 **"손목을 통째로 뺏겼을 때"**를 다룬다 —
4.3이 잔여 한계로 남긴 "손목 탈취 후 즉시 사용"의 답이 여기다. 또한 4.1 파티
리뷰에서 "재설정은 폐기(4.4) 후 다시 온보딩"으로 미뤄둔 경로가 이 스토리에서
완성된다.
[Source: docs/planning-artifacts/epics.md#Story 4.4]

> **발표에서의 위상.** 온바디 구조의 가장 날카로운 반박이 "잃어버리면요?"다.
> 답이 없으면 프라이버시 셀링포인트가 통째로 무너진다. 4.4는 그 답이며,
> **서버 없이도 폐기가 성립**함을 보여 구조 일관성까지 지킨다(서버가 폐기의
> 단일 장애점이 되면 P-1 SPOF를 뒷문으로 다시 들이는 셈).

## Acceptance Criteria

**AC1 — 폐기 후 제어 불가 (NFR2)**
**Given** 프로필이 저장된 워치가 분실·양도되었을 때
**When** 폐기(revocation) 절차를 수행하면
**Then** 해당 기기의 프로필로는 더 이상 가전 제어가 성립하지 않는다

**AC2 — 서버 없는 폐기 경로 최소 1개 (구조 일관성)**
**And** 폐기가 **서버 없이도** 가능한 경로가 최소 1개 존재한다

**AC3 — 폐기 이후 복구 시나리오 정의**
**And** 폐기 이후 복구 시나리오(정상 사용자의 재설정)가 정의된다

## Tasks / Subtasks

- [x] **Task 1: 온바디 폐기 — `revoke_onbody`** (AC: 1, 2)
  - [x] ⚠️ **이름을 모르는 채로 전부 지워야 한다.** Carrier 프로토콜엔 '전체
        나열'이 없다(`capabilities`/`put_records`/`get_records(names)`/`erase(names)`).
        `erase`는 이름을 알아야 지운다. 해법은 3.1 복원과 같은 패턴 — **meta를
        읽어 device_refs·routine_count로 전체 레코드 이름을 재구성**한 뒤 erase
  - [x] `home_profile/revoke.py` 신설 — `revoke_onbody(carrier) -> (ok, report)`.
        meta 조회 → 이름 재구성(meta + device:* + routine:*) → `erase(전체)` →
        **검증**: 폐기 후 `restore_from_carrier`가 실패해야 한다(잔류 0 확인)
  - [x] ⚠️ **"지웠다고 생각했는데 남아 있음"이 최악이다**(carrier.erase docstring).
        폐기는 **결과를 확인**해야 한다 — erase 성공 보고를 믿지 말고 복원 시도가
        실패하는지로 검증. 부분 삭제 잔류가 있으면 폐기 실패로 보고(fail-closed)
  - [x] report: `records_erased`(개수), `restorable_after`(False여야 함),
        `server_required`(False — AC2 구조 증명), `errors`. ⚠️ 측정 안 한 리터럴
        금지(4.1 파티 교훈) — `restorable_after`는 실제 복원 시도 결과여야 한다
  - [x] 계약 승계: 예외 금지, fail-closed, 오류에 레코드 이름 원문 금지

- [x] **Task 2: 폐기 후 제어 불가 증명** (AC: 1)
  - [x] 폐기의 의미는 "레코드가 지워졌다"가 아니라 **"그 프로필로 가전을 못
        연다"**이다. 폐기된 캐리어로 복원→명령 경로를 시도하면 복원 단계에서
        실패해야 하고, 가전 상태가 **불변**임을 확인한다
  - [x] ⚠️ 4.3 게이트와의 합성: 폐기 후에도 공격자가 **이전에 캡처한** 근접
        토큰을 재생할 수 있는가? → 4.3 nonce 1회용이 이미 막는다. 폐기는 프로필
        자체를 없애므로 이중 방어. 이 관계를 THREAT_MODEL에 1줄로 연결
  - [x] ⚠️ **잔여 한계 정직 표기(4.3 계보):** 폐기는 **캐리어에 접근할 수 있을 때**
        성립한다. 이미 남의 손에 있는 워치를 원격으로 지우는 것은 이 구조에
        없다(서버 없는 구조의 대가) — 실기기에선 워치 PIN·자동 잠금이 1차 방어.
        "완전 방어" 주장 금지

- [x] **Task 3: 복구 시나리오 — 폐기 후 재온보딩** (AC: 3)
  - [x] 4.1 파티 결정("재설정은 폐기 후 다시 온보딩")을 **코드로 완성**한다:
        폐기된(비워진) 캐리어는 `onboard_local`이 다시 받아들여야 한다 —
        4.1의 재온보딩 거부는 meta 존재로 판정하므로, 폐기가 meta를 지우면
        재온보딩이 자연히 열린다. **이 흐름을 테스트로 고정**
  - [x] `docs/REVOCATION.md` 신설 — 폐기 절차 + 복구 시나리오 1장. "분실했을 때 /
        양도할 때 / 폐기 후 새로 시작할 때" 3경로. AC3 문서화 요건 충족
  - [x] 서버 없는 폐기가 왜 중요한지 1줄: 서버가 폐기의 단일 장애점이 되면
        P-1(SPOF) 반박이 자기 발등을 찍는다

- [x] **Task 4: 폐기 데모** (AC: 1, 2, 3)
  - [x] `demo_revoke.py` 신설 — ①온보딩된 워치(4.1) → 소재 확인(4.2)으로 온바디에
        데이터 있음 확인 → ②폐기 실행 → ③폐기 후: 복원 실패·제어 불가·소재 0 →
        ④복구: 재온보딩 성공(AC3)
  - [x] `enforce_offline` 안에서 폐기 실행 — **서버 없이 폐기됨**을 강제 증명(AC2)
  - [x] 잔여 한계 표기(캐리어 접근 전제, 원격 소거 아님). 배너·참조 어댑터 표기

- [x] **Task 5: 테스트** (AC: 1, 2, 3)
  - [x] `tests/test_revocation.py` 신설
  - [x] **폐기 후 복원 불가(AC1):** 온보딩 → 폐기 → `restore_from_carrier` 실패.
        `revoke_onbody` report의 `restorable_after is False`(실측)
  - [x] **잔류 0:** 폐기 후 캐리어 내부 저장소가 비어 있음. 부분 잔류가 있으면
        폐기 실패로 보고되는지(fail-closed) — 인위적 잔류 상황 구성
  - [x] **제어 불가(AC1):** 폐기 후 복원→명령 경로 시도 시 가전 상태 불변
  - [x] **서버 없는 폐기(AC2):** `enforce_offline` 안에서 폐기 성공 + monkeypatch 0건
  - [x] **복구(AC3):** 폐기 후 `onboard_local` 재온보딩 성공(4.1 재온보딩 거부가
        폐기로 해제됨을 고정) → 새 프로필로 정상 동작
  - [x] **fail-closed:** 빈 캐리어 폐기·garbage carrier → 예외 없이 보고
  - [x] **문서 회귀:** `REVOCATION.md`에 복구 시나리오 + 잔여 한계(원격 소거 아님) 존재
  - [x] 회귀 기준선: **379 passed**(`10b344e`, 4.3 완료). 신규만큼 증가·회귀 0

- [x] **Task 6: 문서 — 발표 대본·위협 모델 연결**
  - [x] `docs/DEMO_SCRIPT.md`에 폐기 장면(§12) 추가 — "잃어버리면요?"의 답
  - [x] `docs/THREAT_MODEL.md`에 폐기 연결 1절 — 4.3이 잔여 한계로 남긴 "손목
        탈취 후 즉시 사용"에 대한 부분적 답(폐기 + 워치 PIN)과 그 한계

### Review Findings (party code-review 2026-07-23 · Code Review Crew)

- [x] [Review][Patch] **부분 폐기 잔류를 검증이 놓친다** [home_profile/revoke.py]
      — Grumbal 재현·Vex·Boundary 확인. 복원은 meta부터 읽으므로 meta만 지워지고
      device 레코드가 남은 상태에서도 `restorable_after=False`(=성공)가 나온다.
      **개인 데이터가 워치에 남았는데 "폐기 성공"으로 오보** — 4.1 파티가 잡은
      유령 레코드와 같은 병의 재발이며, 4.4의 자랑인 "실측 검증"이 틀린 답을 냈다.
      해법(Yui·Vex): "복원 불가"와 "잔류 0"은 **다른 주장**이므로 축을 분리해
      `residual_records`를 추가하고 **둘 다** 만족해야 폐기 선언. **적용됨**
- [x] [Review][Patch] meta 없는 **고아 잔류**는 이름 재구성 불가로 탐지·삭제 불가
      [home_profile/revoke.py] — Boundary+Grumbal. 근본 원인은 Carrier에 '전체
      나열'이 없다는 것(캐리어 중립 계약이라 불변). 잔류 수를 0이 아니라
      **None(판정 불가)**으로 보고해 세탁하지 않고, REVOCATION.md에 **사용자
      조치(수동 워치 초기화)**를 명시. Grumbal 요구("탐지되면 말은 해줘야지")
      반영. **적용됨**
- 회귀 3건 추가: 부분 폐기 잔류 탐지, 정상 폐기 잔류 0(실측), 고아 잔류 None 보고.

## Dev Notes

### 🚨 이 스토리의 함정 — 먼저 읽을 것

**1. 이름을 모르는 채로 전부 지워야 한다.**
Carrier 프로토콜엔 '전체 나열'이 없고 `erase(names)`는 이름을 요구한다. 파티
리뷰(4.1)에서 이미 확인된 제약이다. 해법은 **meta를 읽어 이름을 재구성**하는 3.1
복원 패턴 — meta의 `device_refs`와 `routine_count`로 `device:*`·`routine:*` 이름을
전부 만들어 erase한다. 새 프로토콜 메서드를 발명하지 마라(캐리어 중립 계약 훼손).

**2. "지웠다"를 믿지 말고 확인하라.**
`carrier.erase` docstring이 직접 말한다 — "지웠다고 생각했는데 남아 있음이 온바디
프라이버시에서 최악의 실패." erase가 `[]`(성공)를 반환해도 그것만으로 폐기를
선언하지 마라. **복원 시도가 실패하는지**로 검증한다. `restorable_after`는 실제
`restore_from_carrier` 결과여야 하고, 측정 안 한 `False` 리터럴이면 그건 4.1 파티가
잡았던 그 병(NFR6 위반)의 재발이다.

**3. 폐기의 의미는 "제어 불가"이지 "레코드 삭제"가 아니다.**
AC1의 문면은 "그 프로필로는 더 이상 가전 제어가 성립하지 않는다"다. 테스트는
레코드 개수가 아니라 **가전 상태가 불변임**까지 확인해야 한다. 3.1·4.2가 "복원
가능"으로 원본 존재를 증명했듯, 4.4는 "복원 불가 → 제어 불가"로 폐기를 증명한다.

**4. 서버 없는 폐기가 구조 일관성이다.**
폐기를 서버가 담당하면 P-1(SPOF) 반박이 자기 발등을 찍는다 — "서버 없이 동작한다"고
해놓고 가장 중요한 보안 동작에 서버를 요구하는 꼴. `enforce_offline` 안에서 폐기가
성공해야 한다(AC2). 이건 3.1 AC3·4.1·4.2와 같은 증명 방식이다.

**5. 잔여 한계를 정직하게 — 원격 소거가 아니다(4.3 계보).**
이 폐기는 **캐리어에 접근할 수 있을 때** 성립한다. 이미 도둑의 손에 있는 워치를
원격으로 지우는 기능은 이 구조에 **없다** — 서버 없는 구조의 대가다. 실기기에선
워치 PIN·자동 잠금이 1차 방어이고, 우리 폐기는 "회수했거나 양도 전"의 경로다.
4.3이 "완전 방어 주장 금지"로 세운 규율을 그대로 승계한다.

**6. 4.1 재온보딩 거부와의 연결이 복구 시나리오다(AC3).**
파티 리뷰에서 재온보딩을 거부하며 "재설정은 폐기 후"라고 미뤘다. 4.4가 meta를
지우면 4.1의 거부 조건(meta 존재)이 해제되어 재온보딩이 열린다 — **이미 맞물려
있다**. 새 코드를 만들지 말고 이 흐름을 테스트로 고정하면 AC3가 완성된다.

**7. 경계 — home_profile 코어, 새 모듈, 캐리어·스키마·storage 무수정.**
`revoke.py` 신설. `carrier.erase`·`restore_from_carrier`를 조립할 뿐 수정하지 않는다.

### 재사용 자산 (신규는 revoke.py·REVOCATION.md·데모·테스트)

| 자산 | 위치 | 용도 |
|---|---|---|
| `carrier.erase(names)` | `home_profile/carrier.py:236` | 원자적 삭제(부분 삭제 없음) |
| `carrier.get_records(["meta"])` | `home_profile/carrier.py:215` | 이름 재구성용 meta 조회 |
| `restore_from_carrier` | `home_profile/storage.py`(3.1) | **폐기 검증**(복원 실패 = 폐기 성공) |
| `onboard_local` | `home_profile/onboard.py`(4.1) | 복구 시나리오(폐기 후 재온보딩) |
| `data_residency` | `home_profile/residency.py`(4.2) | 폐기 전후 온바디 footprint 대비 |
| `ApplianceState` | `appliance_sim/core.py` | 제어 불가(상태 불변) 확인 |
| `enforce_offline` | `offline_guard.py` | 서버 없는 폐기 증명(AC2) |
| 한계 표기 계보 | `THREAT_MODEL.md`(4.3)·`DATA_RESIDENCY.md`(4.2) | 원격 소거 아님 표기 |

### 파일 배치

- 신규: `home_profile/revoke.py`, `demo_revoke.py`, `tests/test_revocation.py`,
  `docs/REVOCATION.md`
- 수정: `home_profile/__init__.py`(export), `docs/DEMO_SCRIPT.md`(§12),
  `docs/THREAT_MODEL.md`(폐기 연결 1절)
- `home_profile/carrier.py`·`schema.py`·`storage.py`·`appliance_sim/` **무수정** 목표

### 테스트 규약

- 정확한 값 단언(복원 실패·상태 불변·잔류 0), '단어 언급' 금지
- `restorable_after`는 실측(리터럴 금지 — 4.1 파티 교훈)
- 서버 없는 폐기는 enforce_offline(강제) + monkeypatch(감시) 둘 다
- 복구는 폐기→재온보딩 성공으로 고정(4.1 거부 해제)
- 문서 회귀: 복구 시나리오 + 잔여 한계(원격 소거 아님) 존재
- `pytest.ini` testpaths = tests

### References

- [Source: docs/planning-artifacts/epics.md#Story 4.4] — AC 원문(NFR2)
- [Source: home_profile/carrier.py:236] — erase 원자성·"지웠는데 남아있음" 경고
- [Source: home_profile/storage.py] — restore_from_carrier(폐기 검증), meta 이름 재구성 패턴
- [Source: docs/implementation-artifacts/4-1-accountless-onboarding.md] — 파티 리뷰: 재온보딩 거부, "재설정은 4.4"
- [Source: docs/implementation-artifacts/4-3-relay-defense.md] — 잔여 한계 표기 규율, "손목 탈취" 미해결 항목
- [Source: docs/THREAT_MODEL.md] — 방어 범위표(폐기 연결 대상)
- [Source: docs/DEMO_SCRIPT.md] — 폐기 장면을 추가할 대본

## Dev Agent Record

### Agent Model Used

Claude Opus 4.8 (claude-opus-4-8) — 2026-07-23

### Debug Log References

- 설계: `revoke_onbody(carrier)` = meta 조회 → 이름 재구성(meta + device:* +
  routine:*) → `carrier.erase(전체)` → **`restore_from_carrier`로 검증**.
  `restorable_after`는 실제 복원 시도 결과(리터럴 아님 — 4.1 파티 교훈).
- **테스트가 실 결함 1건 적발**: `test_revoke_never_raises_on_garbage_carrier`가
  RED. 깨진 캐리어(get_records가 예외)에서 조회 실패를 '빈 캐리어'로 오인해
  `ok=True`("이미 폐기됨")를 반환했다 — **폐기 못 했는데 폐기됐다고 보고**하는
  것은 이 스토리 최악의 실패(carrier.py:238 계보). 조회 실패와 meta 부재를
  구분해 fail-closed 거부로 정정 → GREEN.
- GREEN: 12/12. 데모(`--offline`) exit 0 — 4장면(폐기 전·폐기·폐기 후·복구) 정상.

### Completion Notes List

- **Task 1**: `home_profile/revoke.py` — meta 기반 이름 재구성 후 원자적 erase,
  복원 시도로 검증. 조회 실패 시 fail-closed 거부. 예외 금지.
- **Task 2**: 폐기 = 제어 불가를 테스트로 고정(복원 실패 + 가전 상태 불변).
  4.2 `data_residency`와의 정합도 확인(`restorable_from_onbody=False`).
- **Task 3**: 복구 = 폐기 후 재온보딩. 4.1 파티 결정("재설정은 4.4 경로")이
  **새 코드 없이** 맞물림 — 재온보딩 거부 판정 기준이 meta 존재이고 폐기가
  그것을 지우므로 자연히 열린다. `docs/REVOCATION.md`에 3경로 문서화.
- **Task 4**: `demo_revoke.py` — 4장면 + offline 강제(AC2) + 원격 소거 아님 표기.
- **Task 5**: `tests/test_revocation.py` 12개 — 복원불가·잔류0·제어불가·소재정합·
  서버없는폐기(2겹)·복구·fail-closed(빈/깨진/중복 폐기)·문서회귀·데모.
- **Task 6**: `DEMO_SCRIPT.md` §12(+ "원격 소거 가능"을 금지 문구로 명시),
  `THREAT_MODEL.md`에 4.3↔4.4 연결 절(둘을 합쳐도 완전 방어 아님).

### File List

- `home_profile/revoke.py` — 신규 (revoke_onbody)
- `home_profile/__init__.py` — 수정 (revoke_onbody export)
- `demo_revoke.py` — 신규 (폐기 데모 4장면)
- `tests/test_revocation.py` — 신규 (12 tests)
- `docs/REVOCATION.md` — 신규 (폐기 절차·복구 시나리오·잔여 한계, AC3)
- `docs/DEMO_SCRIPT.md` — 수정 (시연 순서 12 + §12)
- `docs/THREAT_MODEL.md` — 수정 (폐기 연결 절)
- `docs/implementation-artifacts/4-4-profile-revocation.md` — 본 파일
- ※ `home_profile/carrier.py`·`schema.py`·`storage.py`·`appliance_sim/` **무수정**

### Change Log

- 2026-07-23: Story 4.4 컨텍스트 생성. Epic 4 완결 — 분실·양도 폐기(NFR2).
  핵심 신규 = `revoke_onbody`(meta로 이름 재구성 → erase → **복원 시도로 검증**).
  서버 없는 폐기(AC2)·복구=폐기 후 재온보딩(AC3, 4.1 파티 결정 완성).
  잔여 한계: 원격 소거 아님. 베이스라인 379 passed. Status: ready-for-dev.
