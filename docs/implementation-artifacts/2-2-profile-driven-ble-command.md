# Story 2.2: 프로필 기반 BLE 명령 전송

Status: ready-for-dev

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

- [ ] **Task 1: 루틴 → 명령 변환기** (AC: 1)
  - [ ] `home_profile/routine.py` 신설 — **프로필 쪽에 둔다.** 루틴 해석은
        프로필의 의미론이지 시뮬레이터의 것이 아니다. `appliance_sim`을
        import하지 않는다(역방향 의존 금지 — 시뮬레이터가 소비자다)
  - [ ] `routine_to_commands(profile, routine_index) -> (commands, errors)`:
        루틴 1개의 `actions[]`를 **기기별 명령으로 묶는다**. 액션 3개가 기기
        2대를 건드리면 명령은 2건이다(기기당 1건) — 2.1의 명령 형식이
        `{"v":1,"device_ref":…,"set":{…}}`로 기기 단일이기 때문
  - [ ] 예외 금지·fail-closed. 미등록 기기 참조·미지 setting_key는 오류 목록
        (스키마가 이미 미등록 참조를 거부하지만 와이어를 거친 프로필은 재불신)
  - [ ] 명령 순서는 **결정적**이어야 한다 — 같은 루틴이 같은 순서를 낸다.
        발표 재현성이 걸려 있고, 테스트가 순서를 단언할 수 있어야 한다

- [ ] **Task 2: BLE 청킹 — 20B MTU 재조립** (AC: 1)
  - [ ] ⚠️ **여기가 2.1이 미룬 지점이다.** Connect IQ BLE 특성은 read/write
        20바이트이며 long write 미지원(포럼발, PROFILE_SCHEMA §5). 명령
        1건(실측 50~72B)이 한 번에 안 들어간다
  - [ ] `chunk(data, mtu) -> list[bytes]` / `reassemble(chunks) -> (bytes|None, errors)`
        — 청크 헤더에 **순번·총개수**를 실어 순서 뒤바뀜·유실·중복을 탐지한다.
        헤더가 페이로드를 먹으므로 유효 페이로드는 20B보다 작다 — 그 수치를 실측해
        문서에 남길 것
  - [ ] 재조립기는 **적대적 입력을 가정**한다: 총개수 위조(메모리 고갈),
        순번 중복·결번, 청크 0개, 재조립 후 크기가 `MAX_COMMAND_BYTES` 초과.
        전부 예외 없이 거부. 2.1 `decode_command`가 크기 상한을 파싱 전에
        건 것과 같은 이유이며, **여기가 그 상한이 실제로 필요해지는 지점**이다
  - [ ] 배치 도중 중단(청크 절반만 도착)은 **부분 적용 금지** — 완전 재조립
        후에만 `decode_command`로 넘긴다

- [ ] **Task 3: 전송자(Central) 측 — 캐리어 어댑터 경유** (AC: 1)
  - [ ] 프로필 조각을 읽는 경로는 **1.3의 캐리어 어댑터**를 쓴다
        (`MemoryCarrier.get_records`). 저장 매체를 직접 만지지 않는다 —
        그게 캐리어 중립(NFR3)이 코드에서 성립하는 방식이다
  - [ ] `execute_routine(carrier, transport, routine_index) -> (applied, errors)`
        — 조각 읽기 → 프로필 복원 → 루틴 변환 → 청킹 → 전송. 각 단계 실패는
        오류 목록으로 전파(예외 금지)
  - [ ] 전송 대상은 **2.1의 전송 인터페이스**(`deliver(bytes) -> errors`)로만
        말한다. 루프백·BLE 어느 쪽이든 같은 코드가 돈다 — 그게 2.3에서
        네트워크를 끊어도 같은 경로임을 보이는 근거다

- [ ] **Task 4: 2.1 이월 건 해소 — applied / unchanged 구별** (AC: 1)
  - [ ] ⚠️ **2.1 파티 리뷰 P4의 이월분.** 지금이 소비자가 생긴 시점이다:
        루틴 실행기가 "몇 대가 실제로 바뀌었나"를 알아야 AC1을 판정하고,
        2.4 야간 모드 데모가 "전환됨"을 화면에 띄운다
  - [ ] `ApplianceState.apply_command`의 반환을 소비자 요구에 맞춰 정한다.
        **지금 3값 열거형을 만들지 말고**, 실행기가 실제로 무엇을 필요로 하는지
        먼저 코드로 드러난 뒤 최소 형태로 고칠 것(1.3 함정 7 유지)
  - [ ] 어느 쪽으로 정하든 2.1의 기존 테스트가 깨지면 **테스트를 고치지 말고
        결정을 재검토**한다 — 2.1 테스트는 계약이다

- [ ] **Task 5: 클라우드 호출 부재 증명** (AC: 2)
  - [ ] "네트워크 호출이 없다"를 **주장이 아니라 테스트로** 고정한다:
        실행 경로 전체를 도는 동안 `socket.socket`·`socket.create_connection`·
        `urllib.request.urlopen`이 **한 번도 호출되지 않음**을 단언
        (monkeypatch로 폭발하는 가짜를 심어 놓고 경로를 돈다)
  - [ ] 정적 증거도 함께: `home_profile/`·`appliance_sim/`(BLE 바인딩 제외)의
        AST에 `socket`·`urllib`·`http`·`requests`·`httpx` import가 없음을 단언
        — 1.3 P3 반영판 검사기 재사용(동적 import 포함)
  - [ ] ⚠️ 이 증거의 **한계를 정직하게 적을 것**: 파이썬 레벨 감시는 프로세스
        밖(OS·드라이버·워치 펌웨어)을 못 본다. 발표에서 "네트워크 캡처로
        확인했다"고 말하지 않는다 — 실제 패킷 캡처는 2.3의 일이다 (NFR6)

- [ ] **Task 6: 종단 데모 — 프로필에서 가전까지** (AC: 1, 2)
  - [ ] `python -m appliance_sim`과 짝이 되는 실행 경로: 프로필 생성 →
        캐리어 저장 → 루틴 실행 → 시뮬레이터 상태 전이 출력
  - [ ] 배너 규약 준수: **경계마다 한 번, 반복 스트림엔 생략**
        (docs/CARRIER_INTERFACE.md §4-b — 2.1 파티 리뷰 Sally 규약)
  - [ ] 청크 수를 화면에 낸다(예: "명령 68B → 20B 청크 4개") — 워치급 제약이
        눈에 보이는 것이 발표에서 이 스토리의 값어치다

- [ ] **Task 7: 테스트** (AC: 1, 2)
  - [ ] `tests/test_routine_execution.py` 신설
  - [ ] 변환기: 액션→명령 묶음 정확성(기기별 그룹핑·개수·순서), 미등록 참조
        거부, 예외 금지, 결정적 순서
  - [ ] 청킹: 왕복 무손실, 경계(정확히 MTU·MTU+1·1바이트·빈 입력), 적대적
        재조립(총개수 위조·결번·중복·순서 뒤바뀜·재조립 후 초과)
  - [ ] 종단: 프로필 → 캐리어 → 루틴 실행 → 시뮬레이터 상태가 **프로필이 의도한
        값과 정확히 일치**(AC1의 문면). 이벤트 로그로도 교차 확인
  - [ ] 네트워크 부재: 동적(호출 감시) + 정적(AST) 양쪽
  - [ ] 회귀 기준선: **225 passed** (`2aad9fd`)

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

### Debug Log References

### Completion Notes List

### File List

### Change Log
