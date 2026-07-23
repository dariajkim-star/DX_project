---
baseline_commit: 853710f
---

# Story 4.1: 무계정 로컬 전용 온보딩

Status: review

## Story

As a **개인정보에 민감한 사용자**,
I want 회원가입 없이 집을 연결하기를,
so that 가전을 쓰려고 신원을 넘기지 않아도 된다.

**에픽 맥락**: Epic 4는 P-3(6.2%: *"내 집에 있는 제품들 연결해서 쓰는 건데 굳이
회원가입을 강요하는 이유가 뭡니까"*)를 겨냥한다 — 서버가 원본을 갖지 않는 구조를
**결함이 아니라 셀링포인트**로 만든다. 4.1은 그 입구다: 계정·로그인 없이 온보딩이
**완결**됨을 보이고, 필수 동의가 로컬 동작 범위로 한정됨을 문서화한다.
[Source: docs/planning-artifacts/epics.md#Story 4.1]

> **발표에서의 위상.** 4.1(무계정 온보딩, FR6)과 4.2(데이터 소재 명시, FR7)는
> 프라이버시 한 쌍이다. Epic 1의 스키마가 이미 식별자·계정 키를 거부하므로(FR7
> 선행), 4.1의 "무계정"은 새 방어를 발명하는 게 아니라 **기존 구조가 계정을 요구할
> 자리가 없음을 온보딩 흐름으로 실증**하는 것이다. AC3(3.1)의 "클라우드 조회 없음"과
> 같은 계보 — 참는 게 아니라 개입할 자리가 없다.

## Acceptance Criteria

**AC1 — 계정·로그인 없이 온보딩 완결 (FR6)**
**Given** 최초 설치 상태에서
**When** 온보딩을 진행하면
**Then** 계정 생성·로그인 **없이** 프로필 생성과 기기 연결이 완료된다

**AC2 — 동의 범위가 로컬 동작으로 한정됨 문서화**
**And** 필수 동의 항목이 로컬 동작에 필요한 범위로 한정됨이 문서화된다

## Tasks / Subtasks

- [x] **Task 1: 온보딩 함수 — `onboard_local`** (AC: 1)
  - [x] ⚠️ **가짜 계정 시스템을 만들어 "안 쓴다"를 보이지 마라.** 무계정은
        구조적이다 — 온보딩 API에 username/password/token 같은 **인자가 없고**,
        경로에 네트워크 호출이 없다(AC3/3.1 계보). "계정을 만들 수 있는데 참았다"가
        아니라 "계정을 만들 자리가 없다"
  - [x] `home_profile/onboard.py` 신설 — `onboard_local(devices, carrier) ->`
        `(profile | None, report)`. new_profile()로 빈 프로필을 만들고, 주어진
        기기들을 등록(설정은 기본값 또는 비움), `persist_to_carrier`(3.1)로 온바디에
        새긴다. **계정·로그인·서버 등록 단계가 경로에 없다**
  - [x] 반환 report는 무계정을 **증거로** 담는다: `account_created=False`,
        `login_performed=False`, `network_calls=0`(오프라인 강제로 증명 가능),
        `consent_scope`(아래 Task 2). 리포트가 "계정 안 만듦"을 말이 아니라 값으로 보인다
  - [x] ⚠️ **계약 승계(3.1·1.x):** 예외 금지(어떤 입력에도 (None|결과, report)),
        fail-closed, 결과 profile은 `validate_profile()` 통과 **및**
        `find_identifier_violations()` 빈 목록(식별자 0 — FR7 정합). 오류에 페이로드 금지

- [x] **Task 2: 동의 범위 매니페스트 — 정직한 최소 (AC: 2)**
  - [x] ⚠️ **빈 목록으로 "동의가 필요 없다"를 위장하지 마라.** 로컬 동작에도 필요한
        동의가 있다(BLE 페어링 권한 등). 정직함은 **최소이되 명시**다 — 무엇이
        필요한지 열거하고, 계정·이메일·마케팅·위치·식별자 항목이 **없음**을 보인다
  - [x] `LOCAL_CONSENT_SCOPE`를 onboard.py 상단 상수로 둔다 — 각 항목에 목적 라벨.
        예) BLE 근접 페어링(가전 로컬 제어), 온바디 저장(프로필을 워치에). **금지
        항목**(계정·로그인·이메일·전화·위치·마케팅·클라우드 백업)은 이 목록에 없다
  - [x] 매니페스트 정직성 검사: 스키마의 `FORBIDDEN_KEY_FRAGMENTS`·
        `FORBIDDEN_EXACT_KEYS`에 걸리는 문구가 consent_scope에 **없음**을 코드로
        단언(스키마 방어와 같은 어휘로 온보딩 동의를 감시)
  - [x] `docs/CONSENT_SCOPE.md` 신설 — 발표·심사에 그대로 쓸 동의 범위 1장.
        "로컬 동작에 필요한 것 / 요구하지 않는 것" 두 열. AC2 문서화 요건 충족

- [x] **Task 3: 무계정 온보딩 데모** (AC: 1, 2)
  - [x] `demo_onboard.py` 신설 — 최초 설치 → `onboard_local` → 화면에
        "계정 0 · 로그인 0 · 클라우드 조회 0 · 동의 N개(전부 로컬 동작용)".
        기기 연결 완료와 프로필 온바디 저장을 보인다
  - [x] **오프라인 강제 안에서 온보딩 실행**(offline_guard 재사용, 3.1 AC3 패턴) —
        "계정 생성이 서버를 부를 자리가 없다"를 강제로 증명. `--offline` 또는 기본 포함
  - [x] 동의 범위를 화면에 요약(요구 항목 / 요구하지 않는 항목). 정직 표기·배너 규약 유지
  - [x] ⚠️ 이건 P-3 반박이다 — "무계정 = 결함"이 아니라 셀링포인트로 제시

- [x] **Task 4: 테스트** (AC: 1, 2)
  - [x] `tests/test_onboarding.py` 신설
  - [x] **무계정 완결(AC1):** onboard_local이 계정/로그인 인자 없이 프로필 생성 +
        기기 연결 + 온바디 저장을 완료. 결과 profile이 `validate_profile` 통과
  - [x] **식별자 0(FR7 정합):** 결과 profile에 `find_identifier_violations`가 빈 목록.
        온보딩이 식별자 삽입 우회를 만들지 않음을 단언
  - [x] **네트워크 0(AC1 구조 증명):** 온보딩 경로가 `enforce_offline` 안에서
        성공(3.1 종단 동등성 패턴) + monkeypatch 감시 0건
  - [x] **동의 정직성(AC2):** consent_scope가 비어있지 않고(최소이되 명시),
        금지 문구(account·login·email·위치·마케팅)가 **하나도 없음**을 단언
  - [x] **fail-closed:** 기기 정의에 식별자 키(owner_name 등)를 심으면 온보딩 거부
        (schema 방어 승계). garbage 입력 → (None, report), 예외 없음
  - [x] **문서 회귀:** `CONSENT_SCOPE.md`에 "요구하지 않는 것" 절 존재 + 계정·로그인
        문구가 "요구 항목"이 아니라 "요구하지 않음"에 있음을 단언
  - [x] 회귀 기준선: **341 passed**(`853710f`, Epic 3 완료). 신규만큼 증가·회귀 0

- [x] **Task 5: 문서 — 발표 대본·프라이버시 셀링포인트**
  - [x] `docs/DEMO_SCRIPT.md`에 무계정 온보딩 장면(§9) 추가 — P-3 반박 위치.
        "계정 0·로그인 0"을 화면에 보이는 것이 이 장면의 핵심
  - [x] P-3 인용은 `CX_DEFINITION §2` 대표리뷰 대조 후에만(CLAUDE.md 오염 방지).
        원문: "굳이 회원가입을 강요하는 이유가 뭡니까"
  - [x] AC2 문서(`CONSENT_SCOPE.md`)를 대본에서 링크 — 동의 범위를 심사위원이 열람 가능하게

## Dev Notes

### 🚨 이 스토리의 함정 — 먼저 읽을 것

**1. 무계정은 구조다 — 가짜 계정 시스템을 만들지 마라.**
"계정을 만들 수 있는데 안 만든다"를 보이려고 로그인 흐름을 만들면 이 스토리를
오해한 것이다. `onboard_local`에는 username/password/token **인자 자체가 없고**,
경로에 네트워크 호출이 없다. 3.1 AC3("복원에 클라우드 조회 없음")와 정확히 같은
논리 — 참는 게 아니라 개입할 자리가 없다. `enforce_offline` 안에서 온보딩이
성공하는 것이 그 증명이다.

**2. 동의 매니페스트는 정직해야 한다 — 빈 목록은 거짓말이다.**
"아무 동의도 필요 없다"는 사실이 아니다. BLE 페어링엔 권한이 필요하고, 온바디
저장에도 사용자 인지가 필요하다. 정직함은 **최소이되 명시**다: 필요한 것을 열거하고,
계정·이메일·마케팅·위치는 그 목록에 **없음**을 대비로 보인다. 심사위원이 "그럼
아무것도 동의 안 받나요?"라고 물으면 답이 있어야 한다.

**3. 스키마가 이미 계정·식별자 키를 거부한다 — 우회를 만들지 마라.**
`FORBIDDEN_KEY_FRAGMENTS`(account·email·owner…)·`FORBIDDEN_EXACT_KEYS`(mac·serial…)가
이미 프로필에서 식별자를 막는다(FR7 선행, Story 1.1). 온보딩은 이 방어를 **재사용**할
뿐 새 경로로 우회하면 안 된다. 결과 profile은 `validate_profile` + `find_identifier_violations`
둘 다 통과해야 한다. 온보딩이 식별자 삽입 뒷문이 되면 그게 이 스토리의 반증이다.

**4. 이건 P-3 반박이다 — 무계정을 셀링포인트로.**
발표 서사에서 "무계정 = 기능 부족"이 아니라 **"신원을 넘기지 않아도 되는 구조"**로
제시한다. LG를 공격하지 않고 LG 언어(고객 신뢰·개인정보 보호)로 미완성을 잇는다.
P-3 수치(6.2%)는 겨냥 Pain의 크기이지 FR의 근거가 아니다(epics.md 주석 계보).

**5. 경계 — home_profile 코어, 새 모듈, 스키마·캐리어 무수정.**
`onboard_local`은 new_profile + persist_to_carrier(3.1)를 조립한다. `onboard.py`
신설, `home_profile/schema.py`·`carrier.py`·`storage.py` 무수정 목표. 스키마 변경이
필요해 보이면 함정 3을 놓친 신호.

### 재사용 자산 (신규는 onboard.py·CONSENT_SCOPE.md·데모·테스트)

| 자산 | 위치 | 용도 |
|---|---|---|
| `new_profile` | `home_profile/schema.py:157` | 빈 프로필 뼈대 |
| `persist_to_carrier` | `home_profile/storage.py`(3.1) | 온바디 저장(기기 연결 완결) |
| `MemoryCarrier` | `home_profile/carrier.py` | 워치 대역 저장소(참조 어댑터) |
| `validate_profile`·`find_identifier_violations` | `home_profile/schema.py` | 식별자 0·유효성 강제 |
| `FORBIDDEN_KEY_FRAGMENTS`·`FORBIDDEN_EXACT_KEYS` | `home_profile/schema.py:72,80` | 동의 매니페스트 정직성 감시 |
| `enforce_offline` | `offline_guard.py` | 네트워크 0 구조 증명(3.1 AC3) |
| 데모 하우스 패턴 | `demo_reinstall.py`·`demo_relocate.py` | 배너 4경계·정직 표기·in-process 테스트 |
| P-3 근거·인용 | `docs/CX_DEFINITION.md §2` | 회원가입 거부 대표리뷰(대조 후 인용) |

### 파일 배치

- 신규: `home_profile/onboard.py`, `demo_onboard.py`, `tests/test_onboarding.py`,
  `docs/CONSENT_SCOPE.md`
- 수정: `home_profile/__init__.py`(신규 심볼 export), `docs/DEMO_SCRIPT.md`(§9)
- `home_profile/schema.py`·`carrier.py`·`storage.py` **무수정** 목표

### 테스트 규약

- 정확한 값 단언(계정 0·로그인 0·식별자 0), '단어 언급' 금지
- 네트워크 0은 enforce_offline(강제) + monkeypatch(감시) 둘 다(3.1 두 겹 계보)
- 동의 정직성: 비어있지 않음 + 금지 문구 부재를 **둘 다** 단언
- 문서 회귀: "요구하지 않는 것"에 계정·로그인이 있음을 단언
- `pytest.ini` testpaths = tests

### References

- [Source: docs/planning-artifacts/epics.md#Story 4.1] — AC 원문(FR6)
- [Source: docs/planning-artifacts/epics.md#Epic 4] — 프라이버시·위협 모델, HMW-3
- [Source: docs/CX_DEFINITION.md#2] — P-3(6.2%), 회원가입 거부 대표리뷰
- [Source: home_profile/schema.py] — FORBIDDEN_KEY_FRAGMENTS/EXACT_KEYS, find_identifier_violations
- [Source: home_profile/storage.py] — persist_to_carrier(3.1) 재사용
- [Source: offline_guard.py] — enforce_offline(네트워크 0 증명)
- [Source: docs/implementation-artifacts/3-1-reinstall-restore.md] — AC3 "클라우드 없음" 계보
- [Source: docs/DEMO_SCRIPT.md] — 무계정 온보딩 장면을 추가할 대본

## Dev Agent Record

### Agent Model Used

Claude Fable 5 (claude-fable-5) — 2026-07-23

### Debug Log References

- 설계: `onboard_local(devices, carrier) -> (profile|None, report)`. 시그니처에
  자격증명 인자 없음(구조적 무계정) — `test_onboard_signature_has_no_credential_params`로
  고정. new_profile + 기기 등록(deepcopy) + persist_to_carrier(3.1) 조립.
- 무계정 증명 3겹: ① report 값(account_created/login_performed=False, network_calls=0)
  ② enforce_offline 안 성공(부를 수 없다) ③ monkeypatch 네트워크 감시 0건.
- 식별자 뒷문 차단: 결과 profile을 validate_profile + find_identifier_violations
  둘 다 통과. 기기에 owner_name 주입 시 거부(조용히 떨구지 않음).
- 동의 정직성: `consent_scope_violations`가 스키마 FORBIDDEN 어휘 + 온보딩 특유
  항목(login/marketing/cloud/token)으로 계정성 slip-in 감시. 빈 목록도 위반.
- GREEN: 14/14 첫 회 통과. 데모(`--offline`) exit 0.

### Completion Notes List

- **Task 1**: `home_profile/onboard.py` `onboard_local` — 자격증명 인자 부재,
  네트워크 없음, 결과 식별자 0. 예외 금지·fail-closed. 온바디 저장은
  persist_to_carrier 재사용.
- **Task 2**: `LOCAL_CONSENT_SCOPE`(ble_pairing·onbody_storage, 목적 라벨) +
  `NOT_REQUIRED`(account·login·email·phone·location·marketing·cloud_backup).
  `consent_scope_violations` 정직성 감시. `docs/CONSENT_SCOPE.md`(요구/불요 두 열).
- **Task 3**: `demo_onboard.py` — 계정0·로그인0·클라우드0 화면, 동의 대비, offline
  강제. 참조 어댑터·실기기 아님 표기.
- **Task 4**: `tests/test_onboarding.py` 14개 — 무계정 완결·왕복·시그니처·식별자0·
  네트워크0(2겹)·동의 정직성·fail-closed·데모.
- **Task 5**: `DEMO_SCRIPT.md` §9 무계정 온보딩(P-3 반박) + CONSENT_SCOPE 링크.

### File List

- `home_profile/onboard.py` — 신규 (onboard_local + 동의 매니페스트 + 감시)
- `home_profile/__init__.py` — 수정 (신규 심볼 4종 export)
- `demo_onboard.py` — 신규 (무계정 온보딩 데모)
- `tests/test_onboarding.py` — 신규 (14 tests)
- `docs/CONSENT_SCOPE.md` — 신규 (동의 범위 문서, AC2)
- `docs/DEMO_SCRIPT.md` — 수정 (시연 순서 9 + §9)
- `docs/implementation-artifacts/4-1-accountless-onboarding.md` — 본 파일
- ※ `home_profile/schema.py`·`carrier.py`·`storage.py`·`appliance_sim/` **무수정**

### Change Log

- 2026-07-23: Story 4.1 컨텍스트 생성(bmad-create-story). Epic 4 착수 — 무계정 로컬
  온보딩(FR6). 핵심 신규 = `onboard_local`(new_profile+persist_to_carrier 조립,
  계정/로그인 인자 부재) + `LOCAL_CONSENT_SCOPE` 정직 매니페스트. 무계정은
  구조적(네트워크 0·식별자 0)으로 증명. 베이스라인 341 passed. Status: ready-for-dev.
- 2026-07-23: Story 4.1 구현 완료 — onboard_local(무계정 구조·식별자0·네트워크0),
  동의 매니페스트·CONSENT_SCOPE.md, 데모·테스트 14개, DEMO_SCRIPT §9.
  Status: ready-for-dev → review.
