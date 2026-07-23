---
baseline_commit: d4d4465
---

# Story 3.1: 재설치 후 무재등록 복원

Status: review

## Story

As a **Night Keeper**,
I want 앱을 지우고 다시 깔아도 내 집 설정이 그대로이기를,
so that 기기를 하나하나 다시 등록하는 노동이 사라진다.

**에픽 맥락**: Epic 3은 경쟁 대비 **2.0배 열위**가 실측된 유일한 지점(P-2 1.37%)을
정면으로 반박한다. 대표 리뷰: *"핸드폰 초기화하고 재설치하니 제품이 전부 없어짐.
삼성 껀 그대로인데."* 3.1은 그 문장을 **구조적으로 무효화**한다 — 프로필 원본이
클라우드가 아니라 온바디(캐리어 레코드)에 있으므로, 폰이 잊어도 손목이 기억한다.
Epic 1이 세운 온바디 저장(1.2)·캐리어 추상화(1.3) 위에 **복원 경로**를 얹는 스토리다.
[Source: docs/planning-artifacts/epics.md#Story 3.1]

> **발표에서의 위상.** 발표 중심 주장은 AI 오케스트레이션(`WORKFLOW.md §5`)이고,
> Epic 2가 "서버 없이 동작"의 마지막 증거였다면 Epic 3은 **"서버가 없어서 오히려
> 강하다"**를 보인다 — P-2는 우리가 LG를 공격하는 곳이 아니라 **LG의 미완성을 LG
> 언어로 잇는** 곳이다. 재등록 노동의 소멸은 고객감동·Effortless의 코드적 실현이다.
> ⚠️ P-2 수치(1.37%)를 인용할 때 "경쟁 2.0배 열위"는 유지하되, 이 스토리가 겨냥하는
> Pain의 실측 크기이지 FR의 근거가 아니다(epics.md Requirements Inventory 주석).

## Acceptance Criteria

**AC1 — 재등록 절차 없이 프로필 복원 (FR4)**
**Given** 온바디 프로필이 저장된 워치(참조 어댑터)와 등록 완료 상태의 앱이 있을 때
**When** 앱을 삭제하고 재설치한 뒤 워치를 연결하면
**Then** **기기 재등록 절차 없이** 프로필이 복원된다

**AC2 — 복원 일치 검증**
**And** 복원된 설정이 삭제 전과 일치함이 비교로 확인된다(왕복 무손실)

**AC3 — 복원에 클라우드 조회 없음 (FR7 정합)**
**Given** 복원 과정에서
**When** 서버 통신을 관찰하면
**Then** 프로필 복원에 클라우드 조회가 사용되지 않는다

[Source: docs/planning-artifacts/epics.md#Story 3.1]

## Tasks / Subtasks

- [x] **Task 1: `merge_chunks` — `split_chunks`의 정확한 역함수** (AC: 1, 2)
  - [x] ⚠️ **새 저장 표현을 발명하지 마라.** 저장 조각 형식은 이미 `split_chunks`
        (`home_profile/storage.py:229`)가 정한다: `meta`(schema_version·
        reserved_wellness·device_refs·routine_count) + `device:<ref>`(기기 정의 +
        `_settings` 키에 접힌 그 기기 설정) + `routine:<i>`. 복원은 이 형식을
        **되돌리는 것**이지 새로 정의하는 게 아니다
  - [x] `merge_chunks(chunks: dict) -> (profile | None, errors: list)`를
        `home_profile/storage.py`에 추가. `split_chunks`가 접은 것을 편다:
        `device:<ref>` 조각에서 `_settings`를 떼어내 top-level `settings[ref]`로
        복원하고, 나머지 필드로 `devices[]` 엔트리를 만든다. `routine:<i>`는
        인덱스 순서대로 `routines[]`에 담는다. `meta`에서 schema_version과
        reserved_wellness를 얹는다
  - [x] **meta를 유실 탐지에 쓴다(조용한 누락 금지, FR5 계보).** `meta.device_refs`에
        있는데 `device:<ref>` 조각이 없으면 **거부**(반쪽 프로필 금지). `routine_count`와
        실제 `routine:*` 조각 수가 다르면 거부. 순서는 `meta.device_refs`가 진실 —
        dict 키 순서에 기대지 않는다
  - [x] **계약 승계(1.2 storage.py docstring):** 예외 금지(어떤 조각 입력에도
        `(None, errors)`), 와이어 불신(병합 직후 `validate_profile()` 재실행 —
        조각이 개별로 유효해도 합쳐서 유효하란 법 없다), fail-closed
  - [x] ⚠️ `reassemble`(routine.py:181)과 **혼동 금지**. 그건 BLE 전송용 바이트
        청크(20B MTU) 재조립이고, 이건 **저장 키 조각**(meta/device/routine) 병합이다.
        관심사가 다르다 — 이름·경로를 재사용하지 말 것

- [x] **Task 2: 온바디 영속화 왕복 — 캐리어를 통한 저장·복원** (AC: 1, 2, 3)
  - [x] ⚠️ **경계 확인 먼저.** `split_chunks`는 조각을 **파이썬 객체**로 낸다.
        캐리어(`put_records`/`get_records`)는 **bytes**만 다룬다(carrier.py 계약 2:
        불투명 바이트). 그 사이 조각별 직렬화가 필요하다 — 조각 하나하나에
        `storage._dumps`(또는 조각 단위 serialize)를 적용해 `{키: bytes}` 레코드 맵을
        만든다. **새 포맷 금지**: JSON UTF-8 compact가 기준(storage.py docstring)
  - [x] `persist_to_carrier(profile, carrier) -> errors` 와
        `restore_from_carrier(carrier) -> (profile | None, errors)`를 얇게 추가한다.
        배치는 어디 두는가 = 경계 결정: `home_profile/`은 코어이고 캐리어를 안다
        (carrier.py가 이미 `home_profile` 안). storage↔carrier를 잇는 얇은 오케스트레이션은
        **storage에 두되 carrier를 인자로 받는다**(storage가 carrier를 import하면
        1.3 AST 경계와 충돌하는지 먼저 확인 — `test_carrier_neutrality.py`가 감시).
        충돌하면 데모/신규 얇은 모듈에 두고 storage는 순수 profile↔chunks만 유지
  - [x] restore = `carrier.get_records(meta 먼저 읽어 device_refs·routine_count 파악)` →
        필요한 모든 키를 `get_records` → 조각별 역직렬화 → `merge_chunks` →
        `validate_profile`. **get_records가 하나라도 없으면 (None, errors)**
        (carrier 계약: 반쪽 결과 없음) — 이 경우 복원 실패를 정직하게 보고
  - [x] ⚠️ **"재등록 절차"가 코드에 없음을 구조로 보인다.** 복원은 캐리어 레코드만
        읽는다 — 기기를 새로 등록하거나 device_ref를 새로 발급하는 경로가
        **존재하지 않는다**. 복원된 device_ref 집합 == 원본과 동일해야 한다(AC1)

- [x] **Task 3: 재설치 데모 — "폰을 지웠는데 손목이 기억한다"** (AC: 1, 2, 3)
  - [x] `demo_reinstall.py` 신설 — 한 장면: 프로필 생성 → `persist_to_carrier`
        (=워치에 새김) → **"앱 삭제·재설치" 시뮬레이션**(앱/폰 측 상태를 통째로 버리고
        캐리어만 남긴다) → `restore_from_carrier` → 복원 == 원본 비교 표시
  - [x] ⚠️ **재설치를 정직하게 모델링하라.** "앱 삭제"는 폰 로컬 상태 소실이다.
        캐리어(참조 어댑터)는 워치를 대신하므로 **살아남는다**. 새 `MemoryCarrier`를
        만들면 그건 워치까지 교체한 것(=다른 시나리오). 같은 캐리어 인스턴스를
        유지하되 앱 측 변수만 버리는 것이 "재설치"의 정확한 표현이다
  - [x] **AC3 절정: `enforce_offline` 안에서 복원 실행**(offline_guard.py 재사용,
        2.3 패턴). "네트워크 없이, 클라우드 조회 없이 복원됨"이 한 화면에 선다.
        차단 상태에서 성공해야 "부를 수 없다"가 증명된다(2.3의 "부르지 않았다"보다 강함)
  - [x] 배너 규약(`CARRIER_INTERFACE.md §4-b`)·참조 어댑터 정직 표기 유지 —
        화면 어디서도 "가민에서 됨"으로 읽히면 안 된다(NFR6, MemoryCarrier docstring)
  - [x] ⚠️ 폴백 규약 승계: 동작한 척 금지. 복원 실패는 우아하게 표시하고 비정상 종료

- [x] **Task 4: 테스트** (AC: 1, 2, 3)
  - [x] `tests/test_reinstall_restore.py` 신설
  - [x] **왕복 무손실(AC2):** `merge_chunks(split_chunks(p))` == p(의미적 동일)를
        대표 샘플 여러 크기(SMALL/TYPICAL/LARGE)에 대해 단언. settings 접힘/펴짐이
        정확히 역이고, device_ref 순서·루틴 순서가 보존됨을 **정확한 값**으로 단언
  - [x] **재설치 복원(AC1):** persist → 앱 상태 폐기 → restore == 원본. 복원된
        device_ref 집합이 원본과 동일(재등록으로 새 ref가 생기지 않음)
  - [x] **클라우드 조회 없음(AC3) — 두 겹:** ① 2.2 패턴 monkeypatch로 복원 경로에
        네트워크 호출 0건 감시(부르지 않았다) ② `enforce_offline` 안에서 restore가
        동일 성공(부를 수 없다). 종단 동등성은 2.3 패턴 재사용
  - [x] **fail-closed 회귀:** meta에 있는 device 조각 결손 → `(None, errors)`(예외 아님);
        routine_count 불일치 → 거부; 조각 bytes 손상(비UTF8·JSON 깨짐) → 거부.
        **부분 복원 금지**를 단언(반쪽 프로필이 통과하지 않음)
  - [x] 회귀 기준선: **296 passed**(`d4d4465`, Epic 2 완료 시점). 신규 테스트만큼
        증가하고 기존 회귀 0

- [x] **Task 5: 문서 — 발표 대본·데이터 소재 접점**
  - [x] `docs/DEMO_SCRIPT.md`에 재설치 복원 장면 절 추가(P-2 반박 위치). 대표 리뷰
        인용은 `data/painpoints.csv` 대조 후에만(CLAUDE.md 오염 방지 규칙)
  - [x] ⚠️ **H2 가설 표기 불필요, 그러나 P-2 실측 라벨 유지.** 3.1은 재설치(관찰된
        행동)라 H2(이사=온바디 수용도↑, 3.2에서 다룸)와 무관하다. 단 P-2 수치는
        "경쟁 2.0배 열위" 맥락과 함께 인용한다(NFR6)
  - [x] AC3와 FR7의 정합을 1줄로 명시: 복원이 클라우드를 안 쓰는 것은 곧
        "프로필 원본이 서버에 없다"(Epic 4 FR7)의 예고편 — 서사 연결 유지

## Dev Notes

### 🚨 이 스토리의 함정 — 먼저 읽을 것

**1. 복원의 핵심 부품은 없다 — `merge_chunks`가 이 스토리의 실제 신규 코드다.**
`split_chunks`(profile → 저장 조각)는 1.2에 있는데 **역함수가 없다**. 3.1의 무게
중심은 그 역함수를 정확히 만드는 것이다. 특히 `split_chunks`가 기기 설정을
`device:<ref>` 조각 안에 `_settings` 키로 **접어 넣는다**(storage.py:255) — 병합은
이걸 떼어 top-level `settings[ref]`로 **펴야** 한다. 접힘/펴짐이 역이 아니면 왕복이
깨지고 AC2가 실패한다.

**2. "클라우드 조회 없음"은 만들어서 안 부르는 게 아니라 구조적으로 없는 것이다.**
복원 경로에 서버·네트워크 코드를 **넣지 않는다**. AC3는 "우리가 서버를 부를 수도
있는데 참았다"가 아니라 "복원에 서버가 개입할 자리가 없다"이다 — `enforce_offline`
안에서 성공하는 것이 그 증명이다(2.3 계보). 가짜 클라우드 클라이언트를 만들어
"안 불렀다"를 보이려는 유혹을 거부하라. 그건 서사를 약화시킨다.

**3. "재설치"를 잘못 모델링하면 스토리가 거짓이 된다.**
재설치 = **폰/앱 로컬 상태 소실**이지 **워치 소실이 아니다.** 데모·테스트에서
캐리어(참조 어댑터=워치 대역) 인스턴스는 **유지**하고 앱 측 변수만 버려야 "재설치"의
정확한 표현이다. 새 `MemoryCarrier()`를 만들면 워치까지 교체한 다른 시나리오가 되고,
그러면 복원이 성립할 리 없다(빈 저장소). 이 구분이 P-2 반박의 정확성이다.

**4. `reassemble`(BLE 바이트 청크)과 `merge_chunks`(저장 키 조각)는 다른 것이다.**
routine.py:181 `reassemble`은 20B BLE MTU 전송 청크를 바이트로 재조립한다(적대적
입력·총개수 위조 방어). 3.1의 `merge_chunks`는 `meta`/`device:*`/`routine:*` **저장
키 조각**을 프로필로 병합한다. 이름·시그니처를 재사용하지 말고, References의 경로를
정확히 구분해서 읽어라.

**5. 계약 4종 전부 승계 — 재발명 금지.**
- 예외 금지·fail-closed: `merge_chunks`·`restore_from_carrier`는 어떤 입력에도
  `(None|결과, errors)`. 예외를 던지면 검사 우회다(1.1 리뷰 F3 계보)
- 와이어 불신: 병합/복원 직후 `validate_profile()` 재실행(storage.py 계약 2)
- 반쪽 결과 없음: `get_records`가 하나라도 없으면 (None, errors), 부분 복원 금지
  (carrier.py `get_records` 계약)
- 오류에 페이로드 금지: 오류 문구는 이름·타입·크기까지(carrier 계약 4, PII 누출 방지)

**6. 경계: storage가 carrier를 import해도 되는가 — 먼저 확인.**
`test_carrier_neutrality.py`가 AST로 코어의 벤더 SDK import를 감시한다. `MemoryCarrier`는
`home_profile.carrier`(코어 안)라 벤더가 아니지만, storage→carrier 방향 의존을
추가하기 전에 이 테스트의 감시 범위를 확인하라. 순수 profile↔chunks(`merge_chunks`)는
storage에 두고, carrier를 인자로 받는 얇은 오케스트레이션(`restore_from_carrier`)은
경계가 깨끗한 위치에 둔다(storage에 carrier 인자로 주입 vs 데모 측 조립).

### 재사용 자산 (대부분 있음 — 신규는 `merge_chunks`와 얇은 복원 오케스트레이션)

| 자산 | 위치 | 용도 |
|---|---|---|
| `split_chunks` | `home_profile/storage.py:229` | 저장 조각 형식의 진실 원천 — `merge_chunks`가 되돌릴 대상 |
| `_dumps`·`deserialize` | `home_profile/storage.py:151,171` | 조각↔bytes (캐리어 경계) |
| `validate_profile` | `home_profile/schema.py:467` | 병합/복원 직후 재검증 |
| `new_profile` | `home_profile/schema.py:157` | 프로필 뼈대 |
| `make_sample_profile` | `home_profile/storage.py:84` | 테스트·데모 샘플(결정적) |
| `MemoryCarrier`(put/get/erase) | `home_profile/carrier.py:154` | 워치 대역 저장소(참조 어댑터) |
| `enforce_offline` | `offline_guard.py` | AC3 "클라우드 없음" 절정 장면(2.3) |
| 배너·정직 표기 규약 | `CARRIER_INTERFACE.md §4-b`, MemoryCarrier docstring | 참조 어댑터 표기 |
| 2.2 네트워크 감시 패턴 | `tests/`(test_no_network_calls…) | AC3 monkeypatch 겹 |
| 2.3 종단 동등성 패턴 | `tests/test_offline_enforcement.py` | 오프라인/온라인 결과 동일 |

### 파일 배치

- 신규: `demo_reinstall.py`, `tests/test_reinstall_restore.py`
- 수정: `home_profile/storage.py`(`merge_chunks` 추가, 그리고 경계가 허락하면
  `restore_from_carrier`/`persist_to_carrier`), `docs/DEMO_SCRIPT.md`(재설치 장면),
  `home_profile/__init__.py`(신규 공개 심볼 export — 기존 패턴 따름)
- `home_profile/schema.py`는 **무수정** 목표(복원은 기존 스키마로 검증만). 스키마
  변경이 필요해 보이면 그건 함정 1을 놓친 신호

### 테스트 규약

- 정확한 값 단언(복원 프로필 == 원본), '단어 언급' 금지(1.1 계보)
- 왕복은 여러 크기(SMALL/TYPICAL/LARGE)로 — 최상 케이스만 재면 예산이 예산이 아니듯,
  한 크기만 재면 왕복이 왕복이 아니다
- AC3는 monkeypatch(감시) + enforce_offline(강제) **둘 다**
- fail-closed 회귀: 결손 조각·불일치 카운트·손상 bytes가 예외 아니라 거부로 처리됨
- `pytest.ini` testpaths = tests

### References

- [Source: docs/planning-artifacts/epics.md#Story 3.1] — AC 원문(FR4), P-2 반박 대표 리뷰
- [Source: docs/planning-artifacts/epics.md#Epic 3] — 경쟁 2.0배 열위, HMW-2
- [Source: home_profile/storage.py] — `split_chunks`(역함수 대상), 계약 4종, `_dumps`/`deserialize`
- [Source: home_profile/carrier.py] — `MemoryCarrier` put/get/erase, 참조 어댑터 정직 표기, 불투명 바이트 계약
- [Source: offline_guard.py] — `enforce_offline` 재사용(AC3 강제 증명)
- [Source: docs/implementation-artifacts/1-2-onbody-storage-size-budget.md] — 저장 조각 전략의 근거
- [Source: docs/implementation-artifacts/1-3-carrier-neutral-abstraction.md] — 캐리어 경계·AST 감시
- [Source: docs/implementation-artifacts/2-3-offline-enforcement.md] — 오프라인 종단 동등성 패턴, 한계 표기
- [Source: home_profile/routine.py:181] — `reassemble`(혼동 금지 대상 — BLE 바이트 청크)
- [Source: docs/DECISIONS.md] — P-2 정밀화(1.37%), 정정 이력 규약
- [Source: docs/DEMO_SCRIPT.md] — 재설치 복원 장면을 추가할 대본

## Dev Agent Record

### Agent Model Used

Claude Fable 5 (claude-fable-5) — 2026-07-23

### Debug Log References

- RED: `merge_chunks` 미존재 → ImportError (collection error) 확인
- GREEN 1차: 20/20 (데모 테스트 제외) — merge/persist/restore 전부 첫 회 통과
- 데모 테스트 1차 실패: subprocess 호출이 cp949 콘솔 인코딩에 걸림 →
  하우스 패턴(2.4 `test_night_scenario`: in-process `main()` + capsys)으로 정정
- P-2 인용 대조(CLAUDE.md 오염 방지 규칙): epics.md의 인용을
  `crawl_playstore_thinq.csv` 원문과 대조 — 원문은 "핸드폰 초기화 하고 재설치
  하니... 제품이 전부 없어짐 삼성껀 그대로 인데"(2025-08-28, 평점 2)로 실재.
  데모·대본의 인용을 원문 표기 그대로 정정
- 데모 실측(`--offline`): 기기 12대·루틴 8개 → 온바디 4,300B(21개 레코드) →
  앱 상태 폐기 → 오프라인 강제 안 복원 → 삭제 전과 일치 → exit 0
- 전체 회귀: **317 passed** (296 + 21, 회귀 0)

### Completion Notes List

- **Task 1**: `merge_chunks` — `split_chunks`의 정확한 역함수. `_settings`
  접힘/펴짐, meta.device_refs 순서 복원, 결손·카운트 불일치·미지 조각 전부
  거부(반쪽 프로필 금지). 병합 직후 `validate_profile` 재실행(와이어 불신).
  예외 금지·fail-closed 계약 승계.
- **Task 2**: `persist_to_carrier`/`restore_from_carrier` — storage에 두되
  캐리어는 **인자 주입**(storage는 어떤 캐리어 구현도 import하지 않음 —
  1.3 AST 경계와 무충돌, `test_carrier_neutrality` 통과로 확인). 조각별
  JSON UTF-8 직렬화(`_load_chunk`는 deserialize와 같은 불신 계보: 상한·중복
  키·비UTF8 거부). 복원 경로에 기기 등록·ref 발급 코드 부재(FR4를 구조로).
- **Task 3**: `demo_reinstall.py` — 3장면(등록→재설치→복원). 재설치의 정직한
  모델링: 캐리어 인스턴스 유지 + 앱 상태만 폐기(함정 3). `--offline`으로
  AC3 절정. 배너 4경계·참조 어댑터 표기·P-2 원문 인용.
- **Task 4**: `tests/test_reinstall_restore.py` 21개 — 왕복 무손실(3크기),
  재설치 무재등록, AC3 두 겹(monkeypatch 감시 + enforce_offline 강제 +
  종단 동등성), fail-closed 회귀(결손·카운트·손상·빈 캐리어·부분 소실).
- **Task 5**: `DEMO_SCRIPT.md` §7 재설치 장면 — P-2 반박 위치, 원문 대조
  완료 인용만, FR7 예고편 1줄, 실기기 아님 표기. H2 표기는 3.2로 유보.

### File List

- `home_profile/storage.py` — 수정 (`merge_chunks`·`persist_to_carrier`·
  `restore_from_carrier`·`_load_chunk` 추가)
- `home_profile/__init__.py` — 수정 (신규 공개 심볼 3종 export)
- `demo_reinstall.py` — 신규 (재설치 복원 데모, 3장면)
- `tests/test_reinstall_restore.py` — 신규 (21 tests)
- `docs/DEMO_SCRIPT.md` — 수정 (시연 순서 7 + §7 재설치 장면)
- `docs/implementation-artifacts/3-1-reinstall-restore.md` — 본 파일
- ※ `home_profile/schema.py`·`appliance_sim/` **무수정** — 기존 스키마·경계 유지

### Change Log

- 2026-07-23: Story 3.1 컨텍스트 생성(bmad-create-story). Epic 3 착수 — 재설치
  후 무재등록 복원(FR4). 핵심 신규 = `merge_chunks`(`split_chunks` 역함수) +
  캐리어를 통한 복원 왕복. AC3는 `enforce_offline`으로 구조적 증명. 베이스라인
  296 passed. Status: ready-for-dev.
- 2026-07-23: Story 3.1 구현 완료 — merge_chunks 왕복 무손실, 캐리어 복원
  (재등록 경로 구조적 부재), 데모·테스트 21개, P-2 인용 원문 대조.
  **317 passed** (신규 21, 회귀 0). Status: ready-for-dev → review.
