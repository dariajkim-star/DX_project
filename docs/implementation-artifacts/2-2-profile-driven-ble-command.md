---
baseline_commit: d7e09da
---

# Story 2.2: 프로필 기반 BLE 명령 전송

Status: done

## Story

As a **Night Keeper**,
I want 손목의 프로필이 가전에 직접 명령을 보내기를,
so that 앱·서버를 경유하지 않고 집이 반응한다.

**에픽 맥락**: 2.1이 "받는 쪽"(가전 시뮬레이터)을 세웠다. 2.2는 **"보내는 쪽"**이다.
Epic 1의 프로필(스키마·조각·어댑터)과 2.1의 가전 사이를 잇는 마지막 배선이며,
이것이 붙는 순간 **"온바디 프로필이 서버 없이 집을 움직인다"**가 코드로 성립한다.
2.3(오프라인 강제)과 2.4(야간 시나리오)는 이 경로 위에서 조건만 바꾼 것이다.
[Source: docs/planning-artifacts/epics.md#Epic 2]

## Acceptance Criteria

**AC1 — 루틴 실행이 시뮬레이터 상태를 바꾼다 (FR2)**
**Given** 온바디 프로필과 페어링된 시뮬레이터가 있을 때
**When** 프로필의 루틴을 실행하면
**Then** BLE로 명령이 전달되고 시뮬레이터 상태가 프로필이 의도한 값으로 바뀐다

**AC2 — 클라우드 호출 부재의 증명**
**And** 명령 경로에 클라우드 호출이 **하나도 없음**이 네트워크 관찰로 확인된다

[Source: docs/planning-artifacts/epics.md#Story 2.2]

## Tasks / Subtasks

- [x] **Task 1: 루틴 → 명령 변환기** (AC: 1)
  - [x] `home_profile/routine.py` 신설 — **프로필 쪽에 둔다.** 루틴 해석은
        프로필의 의미론이지 시뮬레이터의 것이 아니다. `appliance_sim`을
        import하지 않는다(역방향 의존 금지 — 시뮬레이터가 소비자다)
  - [x] `routine_to_commands(profile, routine_index) -> (commands, errors)`:
        루틴 1개의 `actions[]`를 **기기별 명령으로 묶는다**. 액션 3개가 기기
        2대를 건드리면 명령은 2건이다(기기당 1건) — 2.1의 명령 형식이
        `{"v":1,"device_ref":…,"set":{…}}`로 기기 단일이기 때문
  - [x] 예외 금지·fail-closed. 미등록 기기 참조·미지 setting_key는 오류 목록
        (스키마가 이미 미등록 참조를 거부하지만 와이어를 거친 프로필은 재불신)
  - [x] 명령 순서는 **결정적**이어야 한다 — 같은 루틴이 같은 순서를 낸다.
        발표 재현성이 걸려 있고, 테스트가 순서를 단언할 수 있어야 한다

- [x] **Task 2: BLE 청킹 — 20B MTU 재조립** (AC: 1)
  - [x] ⚠️ **여기가 2.1이 미룬 지점이다.** Connect IQ BLE 특성은 read/write
        20바이트이며 long write 미지원(포럼발, PROFILE_SCHEMA §5). 명령
        1건(실측 50~72B)이 한 번에 안 들어간다
  - [x] `chunk(data, mtu) -> list[bytes]` / `reassemble(chunks) -> (bytes|None, errors)`
        — 청크 헤더에 **순번·총개수**를 실어 순서 뒤바뀜·유실·중복을 탐지한다.
        헤더가 페이로드를 먹으므로 유효 페이로드는 20B보다 작다 — 그 수치를 실측해
        문서에 남길 것
  - [x] 재조립기는 **적대적 입력을 가정**한다: 총개수 위조(메모리 고갈),
        순번 중복·결번, 청크 0개, 재조립 후 크기가 `MAX_COMMAND_BYTES` 초과.
        전부 예외 없이 거부. 2.1 `decode_command`가 크기 상한을 파싱 전에
        건 것과 같은 이유이며, **여기가 그 상한이 실제로 필요해지는 지점**이다
  - [x] 배치 도중 중단(청크 절반만 도착)은 **부분 적용 금지** — 완전 재조립
        후에만 `decode_command`로 넘긴다

- [x] **Task 3: 전송자(Central) 측 — 캐리어 어댑터 경유** (AC: 1)
  - [x] 프로필 조각을 읽는 경로는 **1.3의 캐리어 어댑터**를 쓴다
        (`MemoryCarrier.get_records`). 저장 매체를 직접 만지지 않는다 —
        그게 캐리어 중립(NFR3)이 코드에서 성립하는 방식이다
  - [x] `execute_routine(carrier, transport, routine_index) -> (applied, errors)`
        — 조각 읽기 → 프로필 복원 → 루틴 변환 → 청킹 → 전송. 각 단계 실패는
        오류 목록으로 전파(예외 금지)
  - [x] 전송 대상은 **2.1의 전송 인터페이스**(`deliver(bytes) -> errors`)로만
        말한다. 루프백·BLE 어느 쪽이든 같은 코드가 돈다 — 그게 2.3에서
        네트워크를 끊어도 같은 경로임을 보이는 근거다

- [x] **Task 4: 2.1 이월 건 해소 — applied / unchanged 구별** (AC: 1)
  - [x] ⚠️ **2.1 파티 리뷰 P4의 이월분.** 지금이 소비자가 생긴 시점이다:
        루틴 실행기가 "몇 대가 실제로 바뀌었나"를 알아야 AC1을 판정하고,
        2.4 야간 모드 데모가 "전환됨"을 화면에 띄운다
  - [x] `ApplianceState.apply_command`의 반환을 소비자 요구에 맞춰 정한다.
        **지금 3값 열거형을 만들지 말고**, 실행기가 실제로 무엇을 필요로 하는지
        먼저 코드로 드러난 뒤 최소 형태로 고칠 것(1.3 함정 7 유지)
  - [x] 어느 쪽으로 정하든 2.1의 기존 테스트가 깨지면 **테스트를 고치지 말고
        결정을 재검토**한다 — 2.1 테스트는 계약이다

- [x] **Task 5: 클라우드 호출 부재 증명** (AC: 2)
  - [x] "네트워크 호출이 없다"를 **주장이 아니라 테스트로** 고정한다:
        실행 경로 전체를 도는 동안 `socket.socket`·`socket.create_connection`·
        `urllib.request.urlopen`이 **한 번도 호출되지 않음**을 단언
        (monkeypatch로 폭발하는 가짜를 심어 놓고 경로를 돈다)
  - [x] 정적 증거도 함께: `home_profile/`·`appliance_sim/`(BLE 바인딩 제외)의
        AST에 `socket`·`urllib`·`http`·`requests`·`httpx` import가 없음을 단언
        — 1.3 P3 반영판 검사기 재사용(동적 import 포함)
  - [x] ⚠️ 이 증거의 **한계를 정직하게 적을 것**: 파이썬 레벨 감시는 프로세스
        밖(OS·드라이버·워치 펌웨어)을 못 본다. 발표에서 "네트워크 캡처로
        확인했다"고 말하지 않는다 — 실제 패킷 캡처는 2.3의 일이다 (NFR6)

- [x] **Task 6: 종단 데모 — 프로필에서 가전까지** (AC: 1, 2)
  - [x] `python -m appliance_sim`과 짝이 되는 실행 경로: 프로필 생성 →
        캐리어 저장 → 루틴 실행 → 시뮬레이터 상태 전이 출력
  - [x] 배너 규약 준수: **경계마다 한 번, 반복 스트림엔 생략**
        (docs/CARRIER_INTERFACE.md §4-b — 2.1 파티 리뷰 Sally 규약)
  - [x] 청크 수를 화면에 낸다(예: "명령 68B → 20B 청크 4개") — 워치급 제약이
        눈에 보이는 것이 발표에서 이 스토리의 값어치다

- [x] **Task 7: 테스트** (AC: 1, 2)
  - [x] `tests/test_routine_execution.py` 신설
  - [x] 변환기: 액션→명령 묶음 정확성(기기별 그룹핑·개수·순서), 미등록 참조
        거부, 예외 금지, 결정적 순서
  - [x] 청킹: 왕복 무손실, 경계(정확히 MTU·MTU+1·1바이트·빈 입력), 적대적
        재조립(총개수 위조·결번·중복·순서 뒤바뀜·재조립 후 초과)
  - [x] 종단: 프로필 → 캐리어 → 루틴 실행 → 시뮬레이터 상태가 **프로필이 의도한
        값과 정확히 일치**(AC1의 문면). 이벤트 로그로도 교차 확인
  - [x] 네트워크 부재: 동적(호출 감시) + 정적(AST) 양쪽
  - [x] 회귀 기준선: **225 passed** (`2aad9fd`)

## Dev Notes

### 🚨 이 스토리의 함정 — 먼저 읽을 것

**1. 20B MTU가 이 스토리의 진짜 난이도다.**
2.1은 "완성된 bytes 1개"만 다뤘다. 여기서 그 가정이 깨진다 — 실측 명령이
50~72B이므로 **모든 명령이 청킹된다**. 청킹은 단순해 보이지만 재조립기가
공격 표면이다: 총개수 위조 하나로 워치 메모리를 고갈시킬 수 있다. 1.2에서
`MAX_WIRE_BYTES`가, 2.1에서 `MAX_COMMAND_BYTES`가 각각 파싱 전 상한을 건 이유가
**여기서 현실이 된다.** 재조립 버퍼에도 상한을 걸어라.

**2. 역방향 의존 금지 — 루틴 해석은 프로필의 일이다.**
`home_profile`이 `appliance_sim`을 import하면 제품 코드가 시뮬레이터에
의존하게 되고, 실가전으로 갈 때 통째로 뜯어야 한다. 방향은 항상
**프로필 → (명령 bytes) → 가전**이다. 명령 형식은 양쪽이 공유하는 계약이므로
어디에 둘지 판단이 필요하다 — 지금은 `appliance_sim/wire.py`에 있고, 2.2가
그것을 읽어야 한다면 **계약을 공용 위치로 올리는 것**도 선택지다. 올릴 때
`home_profile`이 `appliance_sim`을 import하는 모양이 되지 않게 할 것.

**3. 2.1 이월 건(P4)은 지금 풀되, 지금도 최소로 풀어라.**
Winston의 판단이 "소비자가 생기면 그때"였고 지금이 그때다. 하지만 여전히
**2.4가 뭘 필요로 하는지는 모른다.** 실행기가 실제로 쓰는 것만 만들고,
"나중에 쓸 것 같은" 상태값을 추가하지 마라. 1.3 함정 7은 계속 유효하다.

**4. "클라우드 없음"은 주장이 아니라 증거여야 한다 — 그리고 그 증거의 한계도.**
파이썬 레벨 감시(monkeypatch + AST)는 강력하지만 **프로세스 밖을 못 본다.**
발표에서 "네트워크를 관찰해 확인했다"는 문장을 쓰려면 2.3의 실제 차단 실험이
근거여야 한다. 이 스토리의 증거는 "우리 코드에 네트워크 경로가 없다"까지다.
그 구분을 문서와 발표 자료에 유지할 것 (NFR6).

**5. 배너·정직 표기 규약은 2.1에서 확립됐다 — 재발명 금지.**
`docs/CARRIER_INTERFACE.md §4-b`가 규약이다. 경계마다 한 번, 스트림엔 생략,
자료구조엔 유지, 광고명엔 유지. 새 출력 경로를 만들면 이 규약을 적용하고,
회귀 테스트도 "개수"가 아니라 "경계마다/스트림엔 없음"으로 단언한다.

**6. 캐리어를 우회하지 마라.**
프로필 조각을 읽을 때 `MemoryCarrier`를 거치는 것이 번거로워 보이겠지만,
직접 dict를 만지면 1.3이 만든 캐리어 중립이 **이 스토리에서 무효화**된다.
Epic 3(재설치 복원)이 저장 매체를 바꿀 때 이 경로가 그대로 살아야 한다.

### 2.1이 넘겨준 자산 (재사용 — 새로 만들지 말 것)

| 자산 | 위치 | 용도 |
|---|---|---|
| 명령 형식·인코딩 | `appliance_sim/wire.py` | `{"v":1,"device_ref":…,"set":{…}}` |
| `MAX_COMMAND_BYTES` = 1,024 | 〃 | 재조립 후 크기 상한 |
| 전송 인터페이스 `deliver(bytes)` | `appliance_sim/transports/loopback.py` | 루프백·BLE 공통 |
| 상태·이벤트 조회 | `appliance_sim/core.py` | AC1 판정 근거 |
| `RangeSpec`·capability 어휘 | 〃 | 명령이 통과할 값의 범위 |
| 배너 규약 | `docs/CARRIER_INTERFACE.md §4-b` | 출력 경로 표기 |
| `MemoryCarrier` | `home_profile/carrier.py` | 프로필 조각 읽기 |
| `split_chunks`·`deserialize` | `home_profile/storage.py` | 조각 ↔ 프로필 |

### 미해결 (이 스토리가 건드리지 않는 것)

- **실제 BLE 무전** — `bless`가 이 환경에서 설치 불가임이 2.1에서 실측됐다
  (상류 패키징 문제). 2.2의 BLE는 **청킹 계약**까지이며 무전은 실기기 시점.
  실기기에서는 가민 워치가 **중앙 역할**이라 Python 주변장치 경로 자체가
  불필요할 수 있다 — 그때 `ble_bless.py` 존치를 재평가한다
- **페어링·인증** — Epic 4(NFR1 릴레이 방어). 여기서는 신뢰된 채널을 가정
- **실제 네트워크 차단 실험** — 2.3
- **야간 모드 시나리오·페르소나 연결** — 2.4

### References

- [Source: docs/planning-artifacts/epics.md#Story 2.2] — AC 원문 (FR2)
- [Source: docs/implementation-artifacts/2-1-appliance-simulator-ble-peripheral.md]
  — 넘겨받는 자산, 파티 리뷰 P4 이월 사유, bless 설치 불가 실측
- [Source: docs/CARRIER_INTERFACE.md#4-b] — 시뮬레이터 표기 규약
- [Source: docs/PROFILE_SCHEMA.md#5] — BLE 20B MTU·long write 미지원(포럼발)
- [Source: docs/implementation-artifacts/1-3-carrier-neutral-abstraction.md]
  — 캐리어 경유 원칙, 함정 7(투기적 프레임워크 금지)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.8 (claude-opus-4-8) — 2026-07-22

### Debug Log References

- RED: `ModuleNotFoundError: home_profile.routine` (구현 전 실패 확인)
- GREEN 1차: 25/27 — 2건 실패, **하나는 테스트가 틀렸다**:
  1. `test_reassemble_never_raises`의 `[b"\x00\x02\x01", b"\x01\x02\x02"]`는
     실제로 **정상 청크 2개**(seq0/total2 + seq1/total2)라 재조립이 맞다.
     테스트를 진짜 불량 케이스(total=0 / seq 범위 밖 / total 불일치)로 교체하고,
     **대조군**(`test_reassemble_accepts_minimal_valid_pair`)을 추가해
     "아무거나 거부해서 통과하는 게 아님"을 고정했다(검사기 스텁 판별과 같은 원리)
  2. `docs/OFFLINE_EVIDENCE.md` 부재 — Task 5가 요구한 한계 문서를 작성
- GREEN 2차: 배너 규약 테스트 실패 — 헤더 박스의 배너 줄도 `"  "`로 시작해
  스트림 필터에 걸렸다. 스트림 정의를 `"  dev"`(기기별 반복 줄)로 정밀화
- **자체 발견(P4 재발)**: `execute_routine` 결과 필드를 `devices_changed`로
  이름 붙였으나 **실제로는 "명령을 보낸 기기 수"**다. 같은 값 재설정(no-op)이면
  전송은 성공하고 상태는 안 바뀌는데도 세어진다 — 2.1 파티 리뷰 P4가 이름만
  바뀐 채 살아 있었다. `devices_commanded`로 정정하고 회귀 테스트 추가
  (`test_result_counts_commanded_not_changed`)
- 종단 데모 실측: 프로필 1,095B → 캐리어 → 명령 2건(51B·54B) → 20B 청크 6개
  → 상태 전이 2건, exit 0
- 최종: **255 passed** (기존 225 + 신규 31 — 개발 중 1개 추가, 회귀 0)

### Completion Notes List

- **Task 1**: `home_profile/routine.py` — `routine_to_commands()`가 액션을
  기기별로 묶어 2.1 명령 형식으로 변환. **순서는 `device_ref` 정렬로 결정적**.
  와이어 불신(스키마가 이미 막지만 미등록 참조·미선언 capability를 재검증),
  원자성(하나라도 틀리면 명령을 만들지 않음), 오류에 값 원문 금지.
  **`appliance_sim`을 import하지 않는다** — 명령 형식 상수를 재선언하고
  동기는 테스트가 감시(2.1의 capability 어휘 동기 감시와 같은 방식).
- **Task 2**: `chunk()` / `reassemble()` — 헤더 2B(`[seq][total]`),
  **유효 페이로드 18B**(20B MTU 기준, 실측 상수 `PAYLOAD_PER_CHUNK`).
  재조립기는 적대적 입력 가정: **총개수 위조 즉시 거부**(선언된 total ≠ 수신
  청크 수이면 버퍼를 잡아두지 않고 반환 — 메모리 고갈 차단), 순번 결번·중복·
  범위 밖, 재조립 후 `MAX_COMMAND_BYTES` 초과 전부 거부.
  **순서 뒤바뀜은 허용**(BLE는 순서를 보장하지 않으므로 헤더 순번으로 복원).
- **Task 3**: `execute_routine()` — 프로필은 **캐리어를 통해서만** 읽는다.
  전송은 `deliver(bytes) -> errors` 인터페이스로만 말하므로 루프백·BLE 어느
  쪽이든 같은 코드가 돈다(2.3의 근거). 전송 대상 부재를 **먼저** 확인해
  절반만 보내는 경로를 차단.
- **Task 4**: 소비자가 실제로 필요로 한 것은 "보냈는가"까지였고, 3값 열거형은
  만들지 않았다(1.3 함정 7 · Winston 판단 유지). 대신 **필드 이름이 사실과
  다른 것을 발견해 정정** — 위 Debug Log 참조. 진짜 변경 수가 필요해지는 것은
  2.4(야간 모드 "전환됨" 표시)이며 그때 전송 계층 반환값이 결정된다.
- **Task 5**: 동적 증거(`socket.socket`·`create_connection`·`urlopen`에
  폭발하는 가짜를 심고 경로 주행) + 정적 증거(7개 모듈 AST에 네트워크 토큰
  9종 import 부재, 1.3 P3 반영판 검사기 재사용) + **검사기 자체의 스텁 판별**.
  ⚠️ **한계를 `docs/OFFLINE_EVIDENCE.md`에 명문화** — 파이썬 레벨 감시는
  프로세스 밖(OS·드라이버·펌웨어)을 못 본다. "네트워크 캡처로 확인했다"는
  말하지 않으며 실제 차단 실험은 2.3이다. 그 문서 존재를 테스트가 단언.
- **Task 6**: `demo_routine.py` — `python -m appliance_sim`(받는 쪽)과 짝이 되는
  보내는 쪽. 청크 수를 화면에 내어 워치급 제약이 눈에 보인다. 배너 규약
  (경계 4회, 스트림 생략) 준수 및 회귀 테스트.
- **Task 7**: `tests/test_routine_execution.py` 31개 — 변환(그룹핑·순서·거부·
  예외 금지·PII 카나리아), 청킹(왕복·경계·적대적 재조립 6종·대조군), 종단
  (상태 일치 + 이벤트 교차 확인 + 캐리어 우회 불가), 데모, 네트워크 부재 양면.

### File List

- `home_profile/routine.py` — 신규 (변환·청킹·재조립·종단 실행)
- `home_profile/__init__.py` — 수정 (routine 심볼 4종 공개 + `__all__`)
- `demo_routine.py` — 신규 (종단 데모 진입점)
- `docs/OFFLINE_EVIDENCE.md` — 신규 (증거와 그 한계)
- `tests/test_routine_execution.py` — 신규 (31 tests)
- `docs/implementation-artifacts/2-2-profile-driven-ble-command.md` — 본 파일

### Change Log

- 2026-07-22: Story 2.2 구현 완료 — 루틴→명령 변환, 20B MTU 청킹·적대적
  재조립, 캐리어 경유 종단 실행, 클라우드 부재 증거(동적+정적)와 그 한계 문서,
  종단 데모. **256 passed** (신규 31, 회귀 0).
  Status: ready-for-dev → review.
- 2026-07-22: 파티 코드리뷰 5건 중 4건 반영 — `chunk()` 반환 규약 통일(R1),
  데모 화면 정직 표기(R2), 증거 문서 과장 정정 + `subprocess` 우회 차단(R3),
  `_show()` 드리프트 제거 + 동기 감시(R4). R5(청킹 무효)는 2.3 이월.
  **258 passed**. Status: review → done.

### 파티 리뷰 (2026-07-22) — Amelia·Winston·Sally·Paige·Mary·John

5건 도출, **4건 즉시 반영 + 1건 2.3 이월**. 258 passed (신규 2).

- [x] **R1 (Amelia) `chunk()` 반환 규약이 저장소 유일한 예외** — 실패를 빈 목록으로
      반환해 사유 4종(비bytes·MTU 비정수·MTU가 헤더 이하·청크 수 초과)이
      `execute_routine`에서 하나로 뭉개졌다. **2.1에서 BLE 오류를 셋으로 쪼갠 것과
      같은 병을 몇 시간 만에 새로 만든 것.** → `(chunks|None, errors)` 튜플로 통일,
      네 사유가 서로 다른 문구임을 테스트로 고정
      (`test_chunk_returns_tuple_with_distinct_reasons`)
- [x] **R2 (Sally·Winston) 데모 화면이 거짓 인상을 만든다** — 청크 수는 실제
      계산값이지만 이 경로는 재조립본을 보내므로 "3개로 쪼개서 보냈다"로 읽히면
      사실이 아니다. **틀린 게 아니라 오해를 부르는 것**(Mary) — 오전 배너 논의와
      같은 종류의 결함. → "분할 가능"·"분량"·"※ 청크 수는 계산값, 무선 구간
      미시뮬레이션"으로 문구 정정. **코드 구조는 건드리지 않음**(R5 참조)
- [x] **R3 (Paige) `OFFLINE_EVIDENCE.md`가 자기 앞장에서 과장** — 감시 표가
      `socket.socket`을 "모든 TCP/UDP 연결의 출발점"이라 적었는데
      `socketpair`·`getaddrinfo`·C 확장 syscall은 지나간다. §1의 "모든"과 §2의
      한계가 **같은 문서 안에서 모순**이었다. **한계를 적는 문서가 앞장에서
      과장하면 그 문서의 신뢰가 먼저 죽는다.** → 문구 정정 + 정정 경위 명시.
      추가로 **`subprocess` 우회(curl 실행)가 동적 감시·AST 토큰 양쪽에 누락**돼
      있던 것을 발견 → 둘 다 추가
- [x] **R4 (Mary) `_show()`가 2.1과 다른 규칙** — 2.1은 정규식
      `[a-z0-9][a-z0-9_-]{0,31}`, 2.2는 "ascii + 영숫자"라 `"A_B"`·`"9dev"`의
      판정이 갈렸다. `appliance_sim`을 import할 수 없어 복사한 것이 드리프트로
      이어진 것(**역방향 의존 금지의 대가** — Winston). → 패턴 일치 + 두 구현의
      판정이 같음을 감시하는 테스트(`test_show_rule_matches_appliance_sim`)
- [ ] **R5 (Winston) 청킹이 실행 경로에서 무효 — 2.3 이월**
      `execute_routine`이 쪼갠 것을 **그 자리에서 재조립해** 전송한다. 즉
      무선 구간이 시뮬레이션되지 않으며, 청킹은 이 경로에서 장식이다
      (단위 테스트가 증명하는 것과 별개). 더 큰 문제는 전송 인터페이스
      `deliver(bytes)`가 **완성된 bytes를 받는 모양**이라, 실기기를 붙이면
      2.1 계약을 깨야 한다는 것.
      **이월 사유**(Winston): 올바른 수정 형태 — 전송 인터페이스가 청크를 받을지,
      전송 계층 안에서 쪼갤지 — 는 **2.3에서 실제 무선 구간을 붙일 때** 드러난다.
      지금 고치면 또 소비자 없이 인터페이스를 못 박는 것이다(1.3 함정 7).
      거짓 인상만 R2로 걷어내고 구조는 2.3에 넘긴다.

### 사람 결정 대기 (1건)

- **`ble_bless.py` 존치 여부** — 2.1에서 bless 설치 불가가 실측됐고, 실기기
  데모에서는 **가민 워치가 중앙(Central) 역할**이므로 Python 주변장치 경로 자체가
  불필요할 가능성이 크다. 2.3 또는 실기기 준비 시점에 재평가 대상.
