---
baseline_commit: 636e7f1
---

# Story 4.2: 데이터 소재 명시

Status: done

## Story

As a **개인정보에 민감한 사용자**,
I want 내 집 정보가 어디에 있는지 명확히 보기를,
so that "서버에 없다"는 주장을 확인할 수 있다.

**에픽 맥락**: 4.1(무계정 온보딩, FR6)이 "신원을 안 넘긴다"였다면, 4.2는
**"그럼 내 데이터는 어디 있나"**에 답한다 — 프로필 원본이 온바디(워치)에 있고
서버는 원본을 갖지 않음을 **명시·증명**한다. P-3(서버가 원본 미보유 = 프라이버시
셀링포인트)의 마무리. 4.1과 프라이버시 한 쌍을 완성한다.
[Source: docs/planning-artifacts/epics.md#Story 4.2]

> **발표에서의 위상.** 주장을 말로 하지 않고 **화면으로 증명**한다: 온바디에
> 무엇이 얼마나 있는지(footprint), 온바디만으로 프로필이 복원되는지(원본이 거기
> 있다는 증거, 3.1 재사용), 서버로 가는 항목이 있는지('없음'). "서버에 없다"는
> 주장이 아니라 관찰 가능한 사실이 된다.

## Acceptance Criteria

**AC1 — 원본 위치·서버 미보유 명시 (FR7)**
**Given** 프로필이 온바디에 저장된 상태에서
**When** 데이터 소재 화면·문서를 확인하면
**Then** 프로필 원본의 위치(온바디)와 서버 미보유 사실이 명시된다

**AC2 — 서버 전송 항목 명시 (없으면 '없음')**
**And** 서버로 전송되는 항목이 있다면 그 목록과 목적이 함께 제시된다(없으면 '없음'으로 명시)

## Tasks / Subtasks

- [x] **Task 1: 데이터 소재 리포트 — `data_residency`** (AC: 1, 2)
  - [x] ⚠️ **말이 아니라 관찰로 증명하라.** "서버에 없다"를 문자열로 적는 게 아니라,
        온바디에 실제 무엇이 저장돼 있는지(footprint)와 온바디만으로 복원되는지를
        **값으로** 보인다. 4.1의 report 패턴 계승
  - [x] `home_profile/residency.py` 신설 — `data_residency(profile, carrier) -> report`.
        report는 다음을 담는다:
        · `profile_location` = "온바디 (참조 어댑터 레코드)"
        · `server_holds_original` = False
        · `server_transmitted` = [] (**AC2: 없으면 빈 목록 = '없음'**)
        · `onbody_record_count`·`onbody_bytes`·`onbody_kinds`(meta/device/routine 개수)
        · `restorable_from_onbody` = **온바디만으로 복원 성공 여부**(원본이 거기 있다는 증거)
  - [x] `restorable_from_onbody`는 `restore_from_carrier(carrier)`(3.1)로 복원한 결과가
        입력 profile과 **동일**한지로 판정한다 — 원본이 서버가 아니라 온바디에
        완결돼 있음의 코드적 증거. 다른 저장소가 필요 없음을 보인다
  - [x] ⚠️ **레코드 이름을 원문으로 노출하지 마라.** device_ref는 사용자 통제
        토큰일 수 있다 — footprint는 **종류별 개수·바이트**로 보고하고 원문 키를
        찍지 않는다(carrier `_show_name`·PII 주의 계보). 계약 승계: 예외 금지·fail-closed
  - [x] ⚠️ 이 리포트 경로에 **네트워크 호출이 없다** — "소재 확인"이 서버를 부르면
        자기모순이다. enforce_offline 안에서 리포트 생성이 성공해야 한다(3.1 AC3 계보)

- [x] **Task 2: 데이터 소재 문서 — `docs/DATA_RESIDENCY.md`** (AC: 1, 2)
  - [x] 발표·심사에 그대로 쓸 데이터 소재 1장. "원본 위치: 온바디 / 서버 보유:
        없음 / 서버 전송 항목: 없음 / 온바디만으로 복원: 예". 코드 원천은
        `data_residency`이며 테스트가 문서-코드 정합을 회귀 고정
  - [x] FR7 계보 연결: 스키마의 식별자 0(1.1)·복원 무클라우드(3.1)·무계정(4.1)이
        모여 "서버가 원본을 갖지 않는다"를 이룬다. 이 문서가 그 종합
  - [x] ⚠️ **한계 정직 표기.** 이 증명은 "이 참조 어댑터·이 프로세스에서 서버로
        가는 경로가 없다"까지다. 실제 벤더 워치·실가전 연동 시의 데이터 흐름은
        범위 밖(시뮬레이터 기반)임을 명시(NFR6, 3.1 오프라인 한계 표기 계보)

- [x] **Task 3: 데이터 소재 데모** (AC: 1, 2)
  - [x] `demo_residency.py` 신설 — 온보딩(4.1) → `data_residency` → 화면에
        "원본 위치: 온바디 · 서버 보유: 없음 · 서버 전송: 없음 · 온바디 복원: 가능".
        온바디 footprint(레코드 N개·X바이트)를 보인다
  - [x] `enforce_offline` 안에서 소재 확인 실행 — 소재를 알아내는 데 서버가
        필요 없음을 강제 증명. 배너 규약·참조 어댑터 정직 표기 유지
  - [x] ⚠️ P-3 반박 마무리 — "서버에 없다"를 화면으로 증명하는 것이 이 장면의 핵심

- [x] **Task 4: 테스트** (AC: 1, 2)
  - [x] `tests/test_data_residency.py` 신설
  - [x] **원본 위치·서버 미보유(AC1):** report의 `server_holds_original=False`,
        `profile_location`이 온바디를 명시, `restorable_from_onbody=True`(persist 후)
  - [x] **온바디 복원 증거:** `restore_from_carrier`로 복원한 것이 원본과 동일함을
        residency가 True로 보고. 캐리어가 비면 False(원본이 온바디에 없음)
  - [x] **서버 전송 없음(AC2):** `server_transmitted == []`. '없음'이 빈 목록으로
        명시됨을 단언
  - [x] **footprint 정확성:** onbody_kinds 개수(meta 1·device N·routine M)가
        프로필 구성과 일치. onbody_bytes > 0
  - [x] **네트워크 0:** 소재 확인이 enforce_offline 안에서 성공 + monkeypatch 감시 0건
  - [x] **이름 비노출:** report에 raw device_ref 원문이 실리지 않음을 단언(종류·개수만)
  - [x] **fail-closed:** 무효 프로필 → errors, 예외 없음. garbage 입력 처리
  - [x] **문서 회귀:** `DATA_RESIDENCY.md`에 "서버 보유: 없음"·"서버 전송: 없음" 존재
  - [x] 회귀 기준선: **355 passed**(`636e7f1`, 4.1 완료). 신규만큼 증가·회귀 0

- [x] **Task 5: 문서 — 발표 대본**
  - [x] `docs/DEMO_SCRIPT.md`에 데이터 소재 장면(§10) 추가 — 4.1(§9)과 프라이버시
        한 쌍. `DATA_RESIDENCY.md` 링크. "서버에 없다를 화면으로 증명"이 핵심 메시지

### Review Findings (party code-review 2026-07-23 · Code Review Crew)

- [x] [Review][Patch] `server_holds_original`·`server_transmitted`가 측정 아닌
      **구조적 사실**인데 런타임 수치처럼 읽힘 — Vex 지적, Dana 반론(restorable은
      실관찰). AC2가 요구하는 공개 필드라 유지하되, 코드에 "구조적 사실(전송
      경로 부재), 증거는 restorable_from_onbody + enforce_offline 테스트"로 정직
      라벨. 관찰(footprint·복원)과 구조적 공개를 섞지 않음. **적용됨**
- [x] [Review][Info] 재온보딩 유령 레코드 → residency footprint 축소 보고 문제는
      **4.1 쪽에서 원천 차단**(재온보딩 거부). data_residency는 무수정.
      `test_reonboarding_does_not_leave_ghost_records`가 footprint==실저장량 회귀 고정

## Dev Notes

### 🚨 이 스토리의 함정 — 먼저 읽을 것

**1. 말이 아니라 관찰로 증명한다.**
"서버에 없다"를 문자열로 적는 것은 증명이 아니다. 온바디에 실제 무엇이 있는지
(footprint)와 **온바디만으로 프로필이 복원되는지**(3.1 restore_from_carrier)를
값으로 보인다. 원본이 서버가 아니라 온바디에 완결돼 있음을 코드가 증거한다.
가짜 서버 클라이언트를 만들어 "안 보냈다"를 보이려는 유혹을 거부하라(4.1 함정 1 계보).

**2. 레코드 이름을 원문으로 노출하지 마라.**
device_ref는 사용자 통제 토큰일 수 있다(carrier `_show_name`이 이름을 PII 운반체로
취급하는 이유). 소재 리포트는 **종류별 개수·바이트**로 보고하고 원문 키를 찍지
않는다. "무엇이 얼마나 온바디에 있는가"는 개수·크기로 충분히 증명된다.

**3. 소재 확인 경로에 네트워크가 없어야 한다.**
데이터 소재를 알아내려고 서버를 부르면 자기모순이다("서버에 없다는 걸 서버에
물어봤다"). 리포트 생성은 온바디(캐리어)만 읽는다. enforce_offline 안에서 성공하는
것이 그 증명(3.1 AC3, 4.1 계보).

**4. 한계를 정직하게 표기한다.**
이 증명은 "이 참조 어댑터·이 프로세스에서 서버로 가는 경로가 없다"까지다. 실제
벤더 워치·실가전 연동의 데이터 흐름은 범위 밖(시뮬레이터 기반)이다. 3.1의 오프라인
한계 표기("프로세스 차단이지 장비 차단 아님")와 같은 규율 — 과장하지 않는다(NFR6).

**5. 경계 — home_profile 코어, 새 모듈, 스키마·캐리어·storage 무수정.**
`data_residency`는 split_chunks(footprint)·restore_from_carrier(복원 증거)를
조립한다. `residency.py` 신설, schema·carrier·storage 무수정 목표.

### 재사용 자산 (신규는 residency.py·DATA_RESIDENCY.md·데모·테스트)

| 자산 | 위치 | 용도 |
|---|---|---|
| `split_chunks`·`_dumps` | `home_profile/storage.py` | 온바디 footprint(레코드·바이트) 산출 |
| `restore_from_carrier` | `home_profile/storage.py`(3.1) | 온바디만으로 복원 = 원본 증거 |
| `onboard_local` | `home_profile/onboard.py`(4.1) | 데모에서 온보딩 후 소재 확인 |
| `MemoryCarrier` | `home_profile/carrier.py` | 온바디 저장소(참조 어댑터) |
| `validate_profile` | `home_profile/schema.py` | 입력 유효성 |
| `enforce_offline` | `offline_guard.py` | 소재 확인 네트워크 0 증명 |
| carrier `_show_name` 계보 | `home_profile/carrier.py` | 이름 비노출 규약 |
| 데모 하우스 패턴 | `demo_onboard.py`·`demo_reinstall.py` | 배너 4경계·정직 표기·in-process |
| P-3 근거 | `docs/CX_DEFINITION.md §2` | 서버 원본 미보유 = 셀링포인트 |

### 파일 배치

- 신규: `home_profile/residency.py`, `demo_residency.py`,
  `tests/test_data_residency.py`, `docs/DATA_RESIDENCY.md`
- 수정: `home_profile/__init__.py`(export), `docs/DEMO_SCRIPT.md`(§10)
- `home_profile/schema.py`·`carrier.py`·`storage.py` **무수정** 목표

### 테스트 규약

- 정확한 값 단언(server_holds_original=False·server_transmitted=[]·footprint 개수)
- 온바디 복원 증거는 restore_from_carrier == 원본으로(3.1 패턴)
- 네트워크 0은 enforce_offline(강제) + monkeypatch(감시) 둘 다
- 이름 비노출: report에 raw device_ref 부재를 단언
- 문서 회귀: "서버 보유: 없음"·"서버 전송: 없음" 존재
- `pytest.ini` testpaths = tests

### References

- [Source: docs/planning-artifacts/epics.md#Story 4.2] — AC 원문(FR7)
- [Source: docs/planning-artifacts/epics.md#Epic 4] — 프라이버시, HMW-3
- [Source: docs/CX_DEFINITION.md#2] — P-3, 서버 원본 미보유
- [Source: home_profile/storage.py] — split_chunks·restore_from_carrier·_dumps
- [Source: home_profile/onboard.py] — onboard_local(4.1) 재사용
- [Source: offline_guard.py] — enforce_offline(네트워크 0 증명)
- [Source: docs/implementation-artifacts/3-1-reinstall-restore.md] — 복원=원본 증거, 오프라인 한계 표기
- [Source: docs/implementation-artifacts/4-1-accountless-onboarding.md] — 프라이버시 한 쌍, report 패턴
- [Source: docs/DEMO_SCRIPT.md] — 데이터 소재 장면을 추가할 대본

## Dev Agent Record

### Agent Model Used

Claude Fable 5 (claude-fable-5) — 2026-07-23

### Debug Log References

- 설계: `data_residency(profile, carrier) -> report`. footprint는 split_chunks로
  종류별 개수·바이트(이름 원문 비노출). restorable_from_onbody는
  restore_from_carrier == 원본으로 판정(원본이 온바디에 있다는 증거).
- 이름 비노출 검증: `test_report_does_not_leak_raw_device_refs`가 report repr에
  raw device_ref(ac1·light1·light2) 부재를 단언.
- 네트워크 0: enforce_offline 성공 + monkeypatch 감시(소재 확인이 서버를 부르면
  자기모순 — 온바디만 읽는다).
- GREEN: 12/12 첫 회 통과. 데모(`--offline`) exit 0.

### Completion Notes List

- **Task 1**: `home_profile/residency.py` `data_residency` — server_holds_original=False,
  server_transmitted=[]('없음'), onbody footprint(종류·개수·바이트), restorable_from_onbody
  (복원 증거). 예외 금지·fail-closed. 이름 비노출.
- **Task 2**: `docs/DATA_RESIDENCY.md` — 소재 요약표 + 증명 방식(관찰) + FR7 계보
  (1.1 식별자0·3.1 무클라우드·4.1 무계정·4.2 소재) + 한계 정직 표기.
- **Task 3**: `demo_residency.py` — 온보딩→소재 확인, 원본위치·서버미보유·전송없음·
  복원가능·footprint 화면. offline 강제. 참조 어댑터 표기.
- **Task 4**: `tests/test_data_residency.py` 12개 — 서버미보유·복원증거·전송없음·
  footprint·네트워크0(2겹)·이름비노출·fail-closed·데모.
- **Task 5**: `DEMO_SCRIPT.md` §10 데이터 소재(4.1과 한 쌍) + DATA_RESIDENCY 링크.

### File List

- `home_profile/residency.py` — 신규 (data_residency)
- `home_profile/__init__.py` — 수정 (data_residency export)
- `demo_residency.py` — 신규 (데이터 소재 데모)
- `tests/test_data_residency.py` — 신규 (12 tests)
- `docs/DATA_RESIDENCY.md` — 신규 (데이터 소재 문서, AC1/AC2)
- `docs/DEMO_SCRIPT.md` — 수정 (시연 순서 10 + §10)
- `docs/implementation-artifacts/4-2-data-residency.md` — 본 파일
- ※ `home_profile/schema.py`·`carrier.py`·`storage.py`·`appliance_sim/` **무수정**

### Change Log

- 2026-07-23: Story 4.2 컨텍스트 생성. Epic 4 — 데이터 소재 명시(FR7). 핵심 신규 =
  `data_residency`(온바디 footprint + restore_from_carrier 복원 증거 + 서버 전송
  '없음'). 말이 아니라 관찰로 "서버에 없다"를 증명. 베이스라인 355 passed.
  Status: ready-for-dev.
- 2026-07-23: Story 4.2 구현 완료 — data_residency(footprint·복원증거·전송없음·
  이름비노출·네트워크0), DATA_RESIDENCY.md, 데모·테스트 12개, DEMO_SCRIPT §10.
  Status: ready-for-dev → review.
