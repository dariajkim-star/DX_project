---
baseline_commit: 26a6de31048a113a926fe0bb8f63ccf658877b2c
---

# Story 1.3: 캐리어 중립 추상화

Status: done

## Story

As a **제품 전략 담당**,
I want 프로필 저장·전송이 특정 워치 벤더 API에 묶이지 않기를,
so that 애플·가민·샤오미 어디서도 같은 서사가 성립한다 (삼성 폐쇄 진영 대비 개방 전략).

**에픽 맥락**: 1.1이 "집이 무엇으로 담기는가"(스키마), 1.2가 "정말 손목에 들어가는가"
(크기 예산)를 정했다. 1.3은 **"그 손목이 누구 손목이어도 되는가"**를 코드 구조로
보증한다. 캐리어 중립은 성능 요구가 아니라 **전략 제약(NFR3)**이다 — 처방 자체가
"삼성 갤럭시워치 폐쇄 진영에 대한 개방 생태계 전략"으로 정의돼 있고, 여기서 벤더
API가 코어에 새면 발표의 주장 한 축이 코드 레벨에서 무너진다.
[Source: docs/CX_DEFINITION.md#1] [Source: docs/planning-artifacts/epics.md#Epic 1]

## Acceptance Criteria

**AC1 — 어댑터 경계 (NFR3)**
**Given** 온바디 저장·전송 기능을 구현할 때
**When** 벤더 SDK를 사용하면
**Then** 벤더 의존 코드가 **어댑터 경계 뒤에만** 존재한다

**AC2 — 코어의 SDK 비의존**
**And** 코어 로직은 벤더 SDK를 직접 import하지 않는다

**AC3 — 어댑터 추가만으로 확장 가능함을 문서로 제시**
**Given** 가민 어댑터가 구현된 상태에서
**When** 다른 캐리어 추가를 가정하면
**Then** 코어 변경 없이 어댑터 추가만으로 가능함이 인터페이스 문서로 제시된다

**AC4 — 미구현 캐리어의 정직 표기 (NFR6)**
**And** 미구현 캐리어는 **"미구현"으로 표기**되며 동작하는 것처럼 시연되지 않는다

[Source: docs/planning-artifacts/epics.md#Story 1.3]

## Tasks / Subtasks

- [x] **Task 1: 캐리어 인터페이스 정의** (AC: 1, 3)
  - [x] `home_profile/carrier.py` 신설 — 표준 라이브러리만(1.1·1.2 의존성 원칙 승계).
        `typing.Protocol` 또는 순수 클래스로 정의하되 **런타임 의존성 0건**
  - [x] 인터페이스는 **불투명 바이트 레코드 맵**을 다룬다:
        `put_records(records: dict[str, bytes]) -> list[str]`,
        `get_records(names) -> (dict[str, bytes] | None, list[str])`,
        `erase(names) -> list[str]`.
        ⚠️ **단일 키/섹션 분할 중 어느 쪽도 인터페이스가 강요하지 않는다** —
        레코드 1개면 단일 키, 4개면 섹션 분할이다. 페이로드가 압축본인지 평문인지도
        어댑터가 알 필요 없다 (아래 함정 6 참조)
  - [x] `CarrierCapabilities` — 어댑터가 **자기 한계를 스스로 신고**하는 값 객체:
        `max_record_bytes`, `max_total_bytes`, `transfer_mtu`,
        각 값의 `source`(측정/벤더문서/포럼/미확인) 라벨 포함.
        1.2의 `BUDGET_*` 상수는 **가민 값**이다 — 코어 상수가 아니라 가민 어댑터가
        신고하는 값으로 옮겨야 캐리어 중립이 성립한다 (아래 함정 4)
  - [x] `CarrierStatus` — `SUPPORTED` / `UNIMPLEMENTED` 2값. 3값 이상으로 늘리지 말 것
        (상태를 늘리면 "부분 동작"이라는 회색지대가 생기고 그게 AC4가 막는 것이다)

- [x] **Task 2: 참조 어댑터 1개 — 실제로 도는 것** (AC: 1, 3)
  - [x] `MemoryCarrier`(또는 `LocalFileCarrier`) **1종만** 구현. 이것이 "어댑터 모양이
        실재한다"는 유일한 증거이며, Epic 2에서 호스트 측 시연에도 쓰인다
  - [x] 자기 표기: 이 어댑터는 **워치가 아니다**. `is_device=False` + 라벨
        `"참조 어댑터 — 실기기 아님"`. 1.2의 시뮬레이터 표기 규약(NFR6)과 동일 계보
  - [x] 용량 한계를 **실제로 강제**한다 — `max_record_bytes` 초과 시 거부.
        한계를 신고만 하고 통과시키면 어댑터가 거짓말을 하는 것이고,
        가민에서만 터지는 코드가 테스트를 통과한다

- [x] **Task 3: 가민 어댑터 — 미구현 정직 표기** (AC: 4)
  - [x] `GarminConnectIQCarrier` — `status = UNIMPLEMENTED`.
        모든 연산은 **예외 없이** `["미구현: Garmin Connect IQ 어댑터는 Monkey C
        런타임을 요구하며 이 저장소에 구현체가 없다"]`를 반환한다
  - [x] ⚠️ **이 저장소에 벤더 SDK가 없고 설치할 수도 없다** — Connect IQ SDK는
        Monkey C이며 Python 패키지가 아니다. 그러므로 이 어댑터는 **경계 설계와
        용량 신고까지만** 담당한다. "곧 되는 것처럼" 보이는 코드를 쓰지 말 것
  - [x] `capabilities()`는 신고하되 **출처 라벨을 반드시 포럼/미확인으로** 남긴다
        (128KB·8KB·20B는 공식 문서 보증이 아니다 — PROFILE_SCHEMA.md §5)
  - [x] `zlib` 해제 지원 여부는 **미확인**으로 신고한다(`supports_decompression=None`).
        `False`도 `True`도 아니다 — 모르는 것을 아는 것으로 세탁하지 않는다

- [x] **Task 4: 애플·샤오미는 만들지 말 것** (AC: 3, 4)
  - [x] 빈 어댑터·빈 레지스트리를 **생성하지 않는다**. AC3이 요구하는 것은
        "코어 변경 없이 추가 가능함이 **인터페이스 문서로** 제시"이지 스텁 클래스가
        아니다. 1.1에서 빈 `MIGRATIONS` 레지스트리가 삭제됐다 — 같은 실수 금지
  - [x] 대신 `docs/CARRIER_INTERFACE.md`에 **"새 캐리어를 추가하려면"** 절을 쓴다:
        구현해야 할 메서드 목록, 신고해야 할 capabilities, 코어를 **한 줄도** 고치지
        않는다는 서술, 그리고 애플·샤오미 현재 상태 = **미구현**임을 표로 명시

- [x] **Task 5: 경계 위반 탐지 테스트** (AC: 2)
  - [x] `tests/test_carrier_neutrality.py` 신설
  - [x] **코어 모듈 소스를 실제로 읽어** 벤더 import가 없음을 단언한다:
        `home_profile/schema.py`, `home_profile/storage.py`, `home_profile/__init__.py`
        의 AST를 파싱해 import 이름을 수집하고, 벤더 토큰(`garmin`, `connectiq`,
        `monkeyc`, `toybox`, `apple`, `healthkit`, `watchconnectivity`, `xiaomi`,
        `mifit`, `zepp`, `samsung`, `tizen`, `wearable`) 교집합이 공집합임을 단언
  - [x] 문자열 grep이 아니라 **AST 기반**일 것 — 주석·docstring의 "Garmin" 언급은
        위반이 아니다(1.1·1.2 docstring에 이미 등장한다). grep으로 짜면 지금 당장
        빨간불이고, 그걸 피하려 docstring을 지우는 건 문서를 태워 테스트를 맞추는 짓이다
  - [x] 어댑터 모듈은 이 검사에서 **면제 대상**임을 테스트가 명시(그게 경계의 정의)
  - [x] 코어에 벤더 import를 **주입한 가짜 소스**로 검사기가 실제로 실패함을 확인
        (검사기 자체의 스텁 판별 — 아래 함정 2)

- [x] **Task 6: 어댑터 계약 테스트 (공통 스위트)** (AC: 1, 3, 4)
  - [x] 어떤 어댑터든 통과해야 하는 계약 테스트를 **한 벌** 작성해
        참조 어댑터·가민 어댑터에 각각 적용:
        · 어떤 입력에도 예외 없음(None·비bytes·거대 레코드·빈 이름·중복 이름)
        · `UNIMPLEMENTED` 어댑터는 **모든 연산이 실패**하고 오류 문구에 "미구현" 포함
        · `UNIMPLEMENTED` 어댑터가 실수로 데이터를 반환하는 경로가 없음
          (`get_records`가 절대 `(dict, [])`를 내지 않음)
        · `capabilities()`의 미확인 값이 `None`이며 `False`로 붕괴하지 않음
  - [x] 왕복: 참조 어댑터에 `serialize()` 결과를 넣고 꺼내 `deserialize()` →
        `validate_profile() == []` (1.2 자산 재사용, 새 직렬화 경로 만들지 말 것)
  - [x] 오류 문구에 **레코드 페이로드 값을 넣지 않는다** — 크기·이름·개수만.
        1.1 리뷰에서 거부 메시지가 PII 값을 그대로 흘린 것이 지적됐다

- [x] **Task 7: 인터페이스 문서** (AC: 3, 4)
  - [x] `docs/CARRIER_INTERFACE.md` 신설 — 메서드 계약표, 반환 규약(예외 금지),
        capabilities 필드와 출처 라벨 규칙, "새 캐리어 추가 절차", **캐리어 현황표**
  - [x] 캐리어 현황표는 상태를 정직하게: 참조 = 동작(실기기 아님),
        가민 = **미구현(경계·용량 신고만)**, 애플 = 미구현, 샤오미 = 미구현.
        발표 자료에 이 표를 그대로 쓸 수 있어야 한다
  - [x] `docs/PROFILE_SCHEMA.md` §6 표에 이번 설계 판단(예: 예산 상수의 어댑터 이관)
        을 1행 추가 — 근거 문서 없는 판단은 그 표가 있는 곳에 적는다

### Review Findings

리뷰 2026-07-22 · 레이어 3종(Blind Hunter / Edge Case Hunter / Acceptance Auditor) · 원 발견 24건 → 병합 10건 + 노이즈 1건 기각

- [x] [Review][Patch] **P1(H) erase 비원자성 — 중복 이름·루프 중 예외 시 부분 삭제 후 "거부" 허위 보고** [home_profile/carrier.py:249-256] — `erase(["a","a"])`: 존재 검사는 통과, 첫 del 후 둘째 del이 KeyError → "거부" 반환하는데 a는 이미 삭제됨. put처럼 단일 재바인딩으로 원자화 + 이름 dedup + 중복 이름 테스트 추가 (blind+edge+auditor)
- [x] [Review][Patch] **P2(M) 오류 문구의 레코드 이름 채널로 페이로드 밀수 가능** [carrier.py:205,233,251] — 이름 길이 무제한이라 PII를 이름에 담으면 `{name!r}`로 로그에 그대로 샘. 이름 표시를 길이 제한(예: 32자 절단+길이 병기)하고 이름 채널 카나리아 테스트 추가 (edge+blind)
- [x] [Review][Patch] **P3(M) AST 경계 검사기 회피 경로 — 동적 import·부분일치 미탐지, 심볼명 오탐 위험** [tests/test_carrier_neutrality.py:_imported_names] — `importlib.import_module("garmin")`·`__import__` 미탐지, `import garminconnect` 류 부분일치 미탐지, 역으로 `from mylib import apple` 오탐. 호출 노드 탐지 + 모듈명 부분일치 + 심볼명 대조 완화 (blind+edge)
- [x] [Review][Patch] **P4(M) 공통 계약 스위트가 '항상 실패하는 스텁'을 통과시킴 + 경계 케이스 공백** [tests 섹션4] — SUPPORTED 어댑터의 성공 경로(왕복)가 공통 스위트에 없음. 상태 분기 왕복 추가 + 0바이트 레코드 + get/erase 중복 이름 + capabilities 필드 단언(None/True) + total-limit 테스트의 나눗셈 가정 제거 (edge+auditor+blind)
- [x] [Review][Patch] **P5(M) capabilities()의 예외 금지 계약이 코드로 미보장** [carrier.py:175, carriers/garmin.py:44] — 지연 `from . import storage`가 try 밖. 모듈 상단 import로 이동(순환 없음 확인) 또는 가드 (blind)
- [x] [Review][Patch] **P6(L) 미정의 규약의 문서화 — 빈 입력 비대칭·수용 타입** [docs/CARRIER_INTERFACE.md §2] — `put({})`=오류 vs `get([])`/`erase([])`=성공, bytearray 수용(복사)·memoryview 거부, names는 이터러블 수용. 현행 동작을 계약표에 명시 (blind+edge)
- [x] [Review][Patch] **P7(L) 총 예산에 이름 바이트 미산입** [carrier.py:212] — 실기기 Storage는 키도 공간 차지. `len(name.encode)+len(payload)` 합산으로 보수화 (edge)
- [x] [Review][Patch] **P8(L) 테스트가 비공개 `st._dumps` 의존** [tests:test_split_chunks_roundtrip] — 테스트 로컬 compact-JSON 헬퍼로 교체 (blind+auditor)
- [x] [Review][Patch] **P9(L) 명명된 인터페이스 심볼 부재 (Task 1 문면)** [carrier.py] — `Carrier` Protocol(runtime_checkable) 추가, 계약 스위트가 isinstance로 참조해 죽은 코드 아님을 보장 (auditor)
- [x] [Review][Patch] **P10(L) 회귀 기준선 기록 불일치 117↔129** [본 파일 Dev Notes] — 스토리 작성 시점(996d7c1)=117, 착수 시점(26a6de3)=129 (1.2 리뷰 2회전 반영分). Debug Log에 1줄 해명 (auditor)

기각 1건: carriers/__init__.py docstring의 현황표 중복 기재 — 원본이 CARRIER_INTERFACE.md임을 이미 명시, 드리프트 리스크 경미 (auditor)

## Dev Notes

### 🚨 이 스토리의 함정 — 먼저 읽을 것

**1. 예외 금지(fail-closed)는 이 스토리에도 그대로 상속된다.**
`put_records`·`get_records`·`erase`·`capabilities` 전부 **어떤 입력에도 예외를
던지지 않는다.** 1.1 리뷰의 F3 판정: `validate_profile()`이 계약을 어기고
`TypeError`/`RecursionError`를 던졌고, try/except를 쓰는 호출자에서는 **PII 스캔이
아예 실행되지 않았다.** 크래시는 곧 검사 우회다. 내부 오류는 `except Exception`으로
받아 오류 목록으로 되돌린다(`storage.py:135`, `storage.py:177` 패턴 그대로).
[Source: docs/implementation-artifacts/1-1-home-profile-schema.md#Senior Developer Review]

**2. 테스트가 "로직 0줄 스텁"을 구별하지 못하면 그 테스트는 자산이 아니다.**
1.1의 테스트 23개는 **검증 로직 0줄짜리 스텁을 23/23 통과**시켰다. 원인은
`assert any("단어" in e for e in errs)` 식 단언 — 검증이 일어났는지가 아니라 그 단어가
언급됐는지만 봤다. 이 스토리에서 특히 위험한 지점은 **Task 5의 경계 검사기 자신**이다:
아무것도 안 하는 검사기도 "위반 없음"을 낸다. 그래서 **벤더 import를 주입한 가짜
소스에서 검사기가 실패하는 것**을 반드시 테스트로 고정한다. 정확한 값·개수·이름을
단언하고, '언급 여부' 단언은 쓰지 않는다.

**3. 정직 표기 — "불확실을 확실로 세탁하지 않는다"가 이 프로젝트의 서명이다.**
- 가민 어댑터는 **미구현**이다. 그럴듯한 스텁 로직으로 "거의 다 됨"처럼 보이게
  만들지 말 것. AC4의 문면이 "동작하는 것처럼 시연되지 않는다"이다
- Connect IQ 한계값(128KB/8KB/20B)은 **포럼발**이며 공식 문서 보증이 아니다.
  capabilities에 실을 때 `source="garmin_forum_2026-07-22"` 같은 라벨을 함께 싣는다
- Monkey C의 압축 해제 지원 여부는 **미확인**이다(1.2 미해결 2번). `None`으로
  신고하라 — `False`로 적으면 "확인해서 없더라"가 되고, 그건 하지 않은 조사를 한 척하는 것
- 참조 어댑터는 워치가 아니다. 로그·문서·발표 어디서도 "가민에서 됨"으로 읽히면 안 된다
[Source: docs/implementation-artifacts/1-2-onbody-storage-size-budget.md#Completion Notes List]

**4. 죽은 코드 금지 — 문서가 가리킬 대상으로 존재하는 심볼을 만들지 말 것.**
1.1 v1의 `MIGRATIONS`는 **아무도 읽지 않는 빈 레지스트리**여서 삭제됐다(리뷰 F5).
1.2에서도 읽히지 않는 불리언 상수(`SAMPLE_ASSUMPTIONS_ARE_MEASURED`)가 같은 냄새로
다시 지적됐다 — 테스트가 라벨을 고정한다는 방어가 붙어 살아남았을 뿐이다.
이 스토리의 최대 유혹은 **`CARRIERS = {"apple": AppleStub, "xiaomi": XiaomiStub}`**
같은 레지스트리다. 하지 마라. 어댑터 레지스트리를 만들려면 **호출자가 실제로 그것을
읽어 분기하는 코드가 이 스토리 안에 있어야** 한다. 없으면 문서(Task 7)로 충분하다.
AC3은 "인터페이스 **문서**로 제시"라고 문면이 명시돼 있다.

**5. 에러 메시지에 신뢰 불가 값을 담지 말 것.**
1.1 리뷰에서 거부 메시지가 입력값(이메일·주소 문자열)을 그대로 되뱉는 경로가
발견됐다. 어댑터 오류는 **레코드 이름·바이트 수·한계값**까지만 말한다.
`f"레코드 'devices' 4,511B > 한계 4,096B"`는 좋고,
`f"거부된 페이로드: {payload!r}"`는 금지다. 로그로 새는 순간 온바디 프라이버시
주장(FR7)이 자기 코드에서 반증된다.

**6. 1.2의 미결정을 인터페이스에 못 박지 말 것.**
1.2는 LARGE(기기 30)에서 **키 예산 157.3% 초과**를 실측했고, 대응은
**A 섹션 분할** vs **C zlib**(vs B+C)로 **미결정** 상태다. 사람 결정 대기 중이다.
따라서 캐리어 인터페이스는:
- 레코드를 **1개로 가정하지 않는다**(A를 배제하면 안 됨)
- 페이로드를 **평문 JSON으로 가정하지 않는다**(C를 배제하면 안 됨) — 어댑터는
  바이트를 불투명하게 다루고 내용을 파싱하지 않는다
- `compress=True` 같은 플래그를 인터페이스에 넣지 않는다 — 그건 C를 선택한 것이다
어느 쪽으로 결정되든 어댑터 구현이 바뀌지 않는 모양이 정답이다.
[Source: docs/PROFILE_SCHEMA.md#5.1]

**7. 투기적 멀티캐리어 프레임워크를 짓지 말 것.**
캐리어가 3개일 때 예쁜 추상화를 지금 상상해서 만들면, 실제 두 번째 캐리어가 왔을 때
전부 틀린 채로 발견된다. **실재하는 어댑터 모양 1개 + 문서화된 인터페이스 1벌**이
정직한 범위다. 플러그인 로더·엔트리포인트·동적 import·설정 기반 캐리어 선택 —
전부 이 스토리 밖이다.

### 왜 이것이 전략 제약인가 (범위를 줄이고 싶어질 때 읽을 것)

처방 자체가 "**캐리어 중립**(애플·가민·샤오미 — 삼성 갤럭시워치 폐쇄 진영에 대한
개방 생태계 전략) 온바디 홈 프로필"로 정의돼 있다. P-2 대표 인용에는
"핸드폰 초기화하고 재설치하니 제품이 전부 없어짐. **삼성 껀 그대로인데**"가 있다 —
경쟁 열위 2.0배의 실증 인용이 곧 이 스토리가 존재하는 이유다. 동시에 팀이 실제로
보유한 기기는 **가민**이며 Epic 2 데모가 그 위에서 돈다. 즉 구조는 중립이어야 하고
실증은 가민 하나로만 가능하다 — **그 비대칭을 숨기지 않고 표기하는 것**이 AC4다.
[Source: docs/CX_DEFINITION.md#1] [Source: docs/CX_DEFINITION.md#2.1]

### 이 스토리가 감싸는 코드 (현재 상태)

```python
# home_profile/storage.py — 1.2 산출물
serialize(profile)   -> (bytes | None, errors: list[str])   # 예외 없음
deserialize(data)    -> (profile | None, errors: list[str]) # 와이어 불신: 재검증
size_report(profile) -> dict                                # 예외 없음
BUDGET_STORAGE_TOTAL = 128*1024   # ← 가민 값. 어댑터로 이관 대상
BUDGET_STORAGE_KEY   = 8*1024     # ← 가민 값
BLE_MTU              = 20         # ← 가민 값
MARGIN = 0.8                      # 설계 판단(근거 문서 없음)
```

- **코어가 이미 벤더 중립적인 지점**: JSON UTF-8 compact 기준 표현, 표준 라이브러리
  전용(pydantic·jsonschema 미도입 — 이유가 명시적으로 NFR3다), 값 스칼라 제한
- **코어가 아직 벤더에 물든 지점**: 위 3개 예산 상수. 이름·값·주석 전부 가민이다.
  이관 방식(어댑터가 신고 → 호출자가 판정)은 설계 결정이며, **기존 상수를 갑자기
  삭제하면 1.2 테스트가 깨진다** — 호환 유지 방법과 그 이유를 주석·문서에 남길 것.
  `home_profile/schema.py`는 **수정하지 않는 것이 기본**이다(1.2 규약 승계)

### 파일 배치·재사용

- 신규: `home_profile/carrier.py`, `tests/test_carrier_neutrality.py`,
  `docs/CARRIER_INTERFACE.md`
- 벤더 어댑터를 파일로 분리할 경우 `home_profile/carriers/` 하위에 둔다 —
  **경계가 디렉터리로도 보이는 것**이 리뷰에서 설명 비용을 줄인다
- `__init__.py`에 공개 심볼을 추가하면 `__all__`도 갱신 —
  `test_package_imports_and_all_is_consistent`가 이를 감시한다(1.1 리뷰 산물)
- 테스트는 `import home_profile` 패키지 방식으로 쓸 것.
  `spec_from_file_location`은 상대 import가 있는 모듈에서 깨진다(1.2 기록)
- 회귀 기준선: **117 passed** (`996d7c1` 시점). 작업 후 `python -m pytest tests/ -q`
  전체 통과 유지

### 이 스토리가 열어주는 것

| 스토리 | 받는 것 |
|---|---|
| Epic 2 (BLE 데모) | 호스트 측에서 실제로 도는 참조 어댑터 + 전송 한계 신고 값 |
| 3.1 재설치 복원 | 저장 매체 교체 가능성 — 복원 경로가 벤더에 묶이지 않음 |
| 4.2 데이터 소재 명시 | "원본이 어디에 있는가"를 어댑터 단위로 답할 수 있는 구조 |
| 발표 | 캐리어 현황표(동작/미구현) — 개방 전략 주장의 정직한 증빙 |

### 테스트 규약

- 프로젝트 원칙: **"검증은 일회성 실행이 아니라 `tests/` pytest 자산으로 영구화한다"**
- 스텁 판별: 정확한 값·개수·이름 단언. '단어 언급' 단언 금지
- 경계: `None`·비bytes·0바이트 레코드·한계 직전/직후 크기·중복 레코드 이름·
  존재하지 않는 레코드 조회·`UNIMPLEMENTED` 어댑터의 전 연산
- `pytest.ini`의 `testpaths = tests` — 다른 위치의 테스트는 수집되지 않는다

### References

- [Source: docs/planning-artifacts/epics.md#Story 1.3] — AC 원문
- [Source: docs/planning-artifacts/epics.md#NonFunctional Requirements] —
  NFR3(캐리어 중립: "애플·가민·샤오미 대응 가능한 추상화. 삼성 폐쇄 진영에 대한
  개방 생태계 전략"), NFR6(근거 무결성: "모르는 것은 수치화하지 않는다")
- [Source: docs/planning-artifacts/epics.md#FR Coverage Map] — NFR3 → Epic 1 / Story 1.3
- [Source: docs/implementation-artifacts/1-1-home-profile-schema.md#Senior Developer Review] —
  예외 금지·스텁 판별·죽은 코드(MIGRATIONS) 삭제·거부 메시지 PII 누출
- [Source: docs/implementation-artifacts/1-2-onbody-storage-size-budget.md#Completion Notes List] —
  계승 계약 이행 사례, 정직 표기(실측인 것은 바이트 수뿐), 사람 결정 대기 3건
- [Source: docs/PROFILE_SCHEMA.md#5.1] — 크기 실측과 대응 선택지(A 섹션분할 / C zlib, 미결정)
- [Source: docs/PROFILE_SCHEMA.md#6] — 설계 판단 정직 표기 표(표준 라이브러리 전용 근거 = NFR3)
- [Source: home_profile/storage.py] — 감싸는 대상(예산 상수·직렬화 계약)
- [Source: home_profile/schema.py] — 수정 금지 기본 원칙
- [Source: docs/CX_DEFINITION.md#1] — 처방 정의(캐리어 중립 = 개방 생태계 전략, 가민 실기기 보유)
- [Source: docs/DEV_PLAN.md#5] — 운영 원칙('산출 불가' > 그럴듯한 숫자)
- Garmin Connect IQ 저장 한계(포럼발, 공식 문서 아님):
  https://forums.garmin.com/developer/connect-iq/f/discussion/2661/storage-available
- Connect IQ BLE 20바이트 MTU·long write 미지원:
  https://forums.garmin.com/developer/connect-iq/f/discussion/196823/bluetooth-low-energy-mtu-size-for-characteristics/1443557
- Connect IQ 개요(언어 = Monkey C, Python SDK 부재의 근거):
  https://developer.garmin.com/connect-iq/overview/

## Dev Agent Record

### Agent Model Used

Claude Opus 4.8 (claude-opus-4-8) — 2026-07-22

### Debug Log References

- 기준선 해명(리뷰 P10): Dev Notes의 "117 passed"는 스토리 작성 시점(`996d7c1`)
  수치. 착수 시점(`26a6de3`)은 **129** — 사이의 +12는 1.2 리뷰 2회전 반영분
  (config.yaml 전환 이력 "Epic 1 스토리 1.1·1.2 완료(리뷰 2회전 반영)" 참조).
  본 스토리의 회귀 기준선은 129가 맞다.
- RED: `ModuleNotFoundError: home_profile.carrier` (구현 전 실패 확인)
- GREEN 1차: 32/33 — `test_serialize_roundtrip_through_carrier` 실패:
  TYPICAL 전체 4,180B > 키당 한계 4,096B. **한계 강제가 실작동한다는 증거**라
  테스트를 수정: 단일 레코드 왕복은 SMALL로, 초과 사실은
  `test_typical_profile_needs_chunking`으로 별도 고정.
- 최종: `python -m pytest tests/ -q` → **162 passed** (기존 129 + 신규 33, 회귀 0)

### Completion Notes List

- **Task 1**: `home_profile/carrier.py` — `CarrierStatus`(2값 Enum),
  `CapabilityValue`(값+출처 라벨, frozen dataclass), `CarrierCapabilities`
  (`supports_decompression: Optional[bool]`, None=미확인). 표준 라이브러리만
  (enum·dataclasses·typing). 인터페이스는 불투명 바이트 레코드 맵 —
  분할/압축 어느 쪽도 강요하지 않음(1.2 미결정 보존).
- **Task 2**: `MemoryCarrier` — `is_device=False`, 라벨 "참조 어댑터 — 실기기
  아님". 키당·총량 한계를 실제 강제(초과 시 거부, 실측 테스트로 고정).
  put은 **원자적**(한 건이라도 거부 시 배치 전체 미저장), get은 반쪽 결과 금지.
  한계값은 코어 보수 예산과 동일 수치, source="설계값(측정 아님)".
- **Task 3**: `home_profile/carriers/garmin.py` — `GarminConnectIQCarrier`,
  `UNIMPLEMENTED`. 전 연산이 예외 없이 "미구현: … Monkey C 런타임을 요구하며
  이 저장소에 구현체가 없다" 반환. capabilities 출처는 전부 포럼발/설계보수값
  라벨, `supports_decompression=None`(미확인 유지).
- **Task 4**: 애플·샤오미 코드 0줄 — 파일도 스텁도 레지스트리도 안 만듦.
  테스트가 carriers/ 디렉터리에 apple.py·xiaomi.py **부재를 단언**한다.
  문서(CARRIER_INTERFACE.md §4)로만 추가 절차 제시.
- **Task 5**: AST 기반 경계 검사 — Import/ImportFrom 노드에서 이름 수집,
  벤더 토큰 13종 교집합 공집합 단언. 코어 4개 모듈(schema·storage·carrier·
  `__init__`) 대상. **가짜 벤더 import 소스로 검사기 실패를 고정**(스텁 판별),
  docstring 벤더 언급이 비위반임도 고정. 어댑터 디렉터리 면제 명시.
- **Task 6**: 공통 계약 스위트 — `any_carrier` 파라미터 픽스처(memory·garmin)로
  두 어댑터에 동일 적용: 악성 입력 9종 예외 금지, 1MB 레코드, PII 카나리아가
  오류 문구에 안 나옴, UNIMPLEMENTED의 전 연산 실패·데이터 무반환.
  왕복: serialize→put→get→deserialize→validate==[] (1.2 자산 재사용).
- **Task 7**: `docs/CARRIER_INTERFACE.md` — 캐리어 현황표(발표용), 메서드
  계약표, 출처 라벨 규칙, 새 캐리어 추가 절차(코어 0줄 수정).
  PROFILE_SCHEMA §6에 "예산 상수의 어댑터 이관" 판단 1행 추가 —
  storage.py 상수는 1.2 테스트 호환 위해 유지, 어댑터가 참조·신고.

### File List

- `home_profile/carrier.py` — 신규 (인터페이스·값 객체·MemoryCarrier)
- `home_profile/carriers/__init__.py` — 신규 (벤더 경계 디렉터리)
- `home_profile/carriers/garmin.py` — 신규 (미구현 정직 표기 어댑터)
- `home_profile/__init__.py` — 수정 (carrier 공개 심볼 4종 + `__all__` 갱신)
- `tests/test_carrier_neutrality.py` — 신규 (33 tests)
- `docs/CARRIER_INTERFACE.md` — 신규
- `docs/PROFILE_SCHEMA.md` — 수정 (§6 표 1행 추가)
- `docs/implementation-artifacts/1-3-carrier-neutral-abstraction.md` — 본 파일

### Change Log

- 2026-07-22: Story 1.3 구현 완료 — 캐리어 중립 추상화(인터페이스·참조 어댑터·
  가민 미구현 어댑터·AST 경계 검사·계약 스위트·인터페이스 문서). 162 passed.
  Status: ready-for-dev → review.
- 2026-07-22: 코드리뷰(3레이어 24건 → 10 patch) 전건 반영 — erase 원자화(P1),
  이름 채널 밀수 차단(P2), AST 검사기 회피 3종 봉쇄(P3), 계약 스위트 스텁
  판별력 강화(P4), capabilities 예외 보장(P5), 규약 문서화(P6), 총 예산 이름
  바이트 산입(P7), _dumps 절연(P8), Carrier Protocol(P9), 기준선 해명(P10).
  **176 passed** (기존 129 + 신규 47). Status: review → done.
