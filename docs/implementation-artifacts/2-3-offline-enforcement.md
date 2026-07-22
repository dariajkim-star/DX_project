---
baseline_commit: e081729
---

# Story 2.3: 오프라인 강제 검증

Status: in-progress

## Story

As a **심사위원**,
I want "정말 서버가 없어도 되는지" 의심을 검증받기를,
so that 데모가 연출이 아니라 구조임을 믿을 수 있다.

**에픽 맥락**: 2.1이 받는 쪽, 2.2가 보내는 쪽을 세워 경로가 이어졌다. 2.3은
그 경로에 **의심을 들이대는** 스토리다 — `As a 심사위원`이라는 주체가 Epic 2에서
유일하게 여기만 나온다는 점이 이 스토리의 성격을 말한다. 우리가 만든 것을
우리가 검증하는 게 아니라, **믿지 않는 사람이 검증할 수 있게 만드는 것**이다.
[Source: docs/planning-artifacts/epics.md#Story 2.3]

## Acceptance Criteria

**AC1 — 차단 상태에서도 동일하게 성공 (FR3)**
**Given** 시연 장비가 네트워크에 연결된 상태에서
**When** 기내모드 전환 등으로 네트워크를 물리적으로 차단하면
**Then** 프로필 기반 제어가 **차단 상태에서도 동일하게** 성공한다

**AC2 — 차단 사실이 화면에서 확인 가능 (연출 의심 차단)**
**And** 차단 사실이 화면에서 확인 가능하다

**AC3 — 기존 앱 경로와의 대비 기록**
**Given** 네트워크 차단 상태에서
**When** 기존 ThinQ 앱 경로를 동일 조건에서 시도하면
**Then** 두 경로의 결과 차이가 기록되어 대비 자료로 남는다

[Source: docs/planning-artifacts/epics.md#Story 2.3]

## Tasks / Subtasks

- [ ] **Task 1: R5 해소 — 전송 계층이 청크를 받는다** (AC: 1)
  - [ ] ⚠️ **2.2 파티 리뷰 R5의 이월분이며 이 스토리의 선행 조건이다.**
        현재 `execute_routine`은 쪼갠 것을 **그 자리에서 재조립해** 넘긴다
        (`routine.py`의 `restored, errs = reassemble(pieces)` → `deliver(restored)`).
        즉 무선 구간이 시뮬레이션되지 않았고, 그 상태로는 "차단해도 된다"를
        증명해도 **증명 대상이 실물이 아니다**
  - [ ] 전송 인터페이스에 **`deliver_chunks(chunks: list[bytes]) -> errors`** 추가.
        기존 `deliver(bytes)`는 **삭제하지 않는다** — 2.1 계약이고 그 테스트가
        지키고 있다. 새 메서드를 가진 전송은 그것을 쓰고, 없으면 기존 경로로
        떨어지되 **어느 쪽을 썼는지 결과에 남긴다**(조용한 분기 금지)
  - [ ] 재조립 책임이 **수신 측으로 이동**한다: `LoopbackTransport.deliver_chunks`가
        `reassemble()`을 호출한다. 이것이 실기기의 실제 구조다(워치가 쪼개 보내고
        가전/펌웨어가 붙인다). `execute_routine`은 이제 붙이지 않는다
  - [ ] `execute_routine` 결과에 `reassembled_by`(`"sender"` | `"receiver"`)를
        실어 어느 경로였는지 기록. 데모 화면도 이 값을 그대로 쓴다 —
        2.2 R2에서 넣은 "무선 구간 미시뮬레이션" 문구를 **조건부로** 바꾼다
  - [ ] ⚠️ **최소로 풀 것**: 청크 유실·재전송·순서 보장 프로토콜을 만들지 마라.
        `reassemble()`이 이미 순서 뒤바뀜을 감내하고 결번을 거부한다. 재전송은
        실기기에서 BLE 스택이 하는 일이고, 여기서 지어내면 투기적 프레임워크다
        (1.3 함정 7 — 이 프로젝트에서 네 번째 적용)

- [ ] **Task 2: 오프라인 강제 하네스 — 실행 중 네트워크를 실제로 막는다** (AC: 1)
  - [ ] `offline_guard.py` 신설 — 컨텍스트 매니저로 **프로세스 내 네트워크를
        실제 차단**한다. 2.2가 만든 것은 *"부르지 않았다"* 를 관찰하는 감시였고,
        이것은 *"부를 수 없게 만든다"* 이다. 차이가 중요하다: 감시는 통과했지만
        실은 부를 수 있었던 코드와, 막힌 상태에서 통과한 코드는 강도가 다르다
  - [ ] 차단 대상은 2.2의 감시 목록을 승계·확장:
        `socket.socket`·`create_connection`·**`getaddrinfo`(DNS)**·`socketpair`·
        `urllib.request.urlopen`·`subprocess.Popen`/`run`.
        `getaddrinfo`와 `socketpair`는 **2.2 리뷰(Paige)가 구멍으로 지적**한 것들이다
  - [ ] 차단 시 `OfflineViolation` 예외를 던진다 — 여기서는 **예외가 옳다.**
        이 프로젝트의 예외 금지는 *제품 코드의 계약*이고, 하네스는 시험 장비다.
        위반이 조용히 오류 목록으로 흡수되면 그게 바로 이 스토리가 잡으려는 것
  - [ ] 하네스 자신의 스텁 판별: **막힌 상태에서 일부러 소켓을 열어 보고
        실제로 터지는지** 테스트로 고정한다. 아무것도 안 막는 하네스도
        "위반 없음"을 낸다(1.1 교훈 · 1.3 P4 · 2.1·2.2에서 반복 적용)

- [ ] **Task 3: 차단 상태 종단 실행 — 같은 코드가 같은 결과를 낸다** (AC: 1)
  - [ ] 연결 상태와 차단 상태에서 **동일한 실행 경로**를 돌려 결과를 비교한다.
        비교 대상은 "성공했다"가 아니라 **시뮬레이터 최종 상태·이벤트 로그가
        바이트 단위로 같은가**여야 한다 — "둘 다 성공"은 약한 단언이다
  - [ ] 차단 상태에서 `execute_routine`이 **오류 없이** 완료되고,
        `deliver_chunks` 경로를 탔음이 결과에 남는다
  - [ ] ⚠️ 이 테스트가 **하네스 없이도 통과하면 의미가 없다** — Task 2의
        하네스가 실제로 활성인 상태에서 도는지 테스트가 스스로 확인할 것

- [ ] **Task 4: 차단 사실의 화면 확인** (AC: 2)
  - [ ] 데모 실행 중 **차단 상태를 화면에 표시**한다. "연출 의심 차단"이
        AC의 문면이므로, 표시는 **우리 주장이 아니라 관찰**이어야 한다:
        차단 하네스가 활성인지, 그리고 **차단이 실제로 작동함을 그 자리에서
        시연**(일부러 연결 시도 → 실패 확인)
  - [ ] ⚠️ **화면 표시의 한계도 같이 적을 것**: 프로세스 내 차단은
        "이 파이썬 프로세스가 못 나간다"이지 "장비가 네트워크에서 끊겼다"가
        아니다. **기내모드는 사람이 눌러야 하고 그건 코드가 증명할 수 없다.**
        발표 시연 절차는 문서로 남기고(Task 6), 화면에는 코드가 아는 것만 적는다
  - [ ] 배너 규약 준수 — `docs/CARRIER_INTERFACE.md §4-b`
        (경계마다 한 번, 반복 스트림엔 생략). 새 출력이 생겨도 재발명 금지

- [ ] **Task 5: 대비 자료 — 기존 앱 경로** (AC: 3)
  - [ ] ⚠️ **이 AC는 코드로 완결되지 않는다.** 실제 ThinQ 앱을 기내모드에서
        돌리는 것은 **사람이 폰으로 하는 일**이다. 우리가 만들 수 있는 것은
        **기록의 틀**이지 결과가 아니다
  - [ ] `docs/OFFLINE_COMPARISON.md` 신설 — 두 경로 대비표의 **틀**과
        측정 절차를 정의하고, 우리 경로의 결과는 실측으로 채운다.
        **ThinQ 앱 쪽은 빈칸 + "미측정"으로 남긴다.** 추정치를 적지 않는다(NFR6)
  - [ ] 근거 연결: P-1(43.4%) 인용과 이 대비가 같은 주장의 두 면임을 명시.
        VOC가 "서버 죽으면 아무것도 안 됨"을 말했고, 이 표가 그 구조를 보인다
  - [ ] ⚠️ 앱 측정을 하게 되면 **캡처·날짜·기기·앱 버전**을 함께 기록할 것.
        기록 없는 비교는 발표에서 반박당한다

- [ ] **Task 6: 발표 시연 절차서** (AC: 2, 3)
  - [ ] `docs/DEMO_SCRIPT.md` 신설 — 발표장에서 **무엇을 어떤 순서로 보이는가**.
        Epic 2가 발표의 마지막 증거이므로 이 문서가 그 실행 대본이다
  - [ ] 포함할 것: 사전 준비(기기·프로필 적재), 시연 순서, **기내모드 전환 시점**,
        화면에서 심사위원이 볼 것, 예상 질문과 답(특히 *"서버 없다면서 DB는?"* —
        발견/처방 트랙 구분), **실패 시 폴백**(BLE 안 뜨면 루프백으로, 단 정직 표기)
  - [ ] 말해도 되는 것 / 안 되는 것 표를 `docs/OFFLINE_EVIDENCE.md §2`에서
        가져와 대본에 박아둔다 — 발표 중 즉흥으로 과장하는 것을 막는 장치

- [ ] **Task 7: 테스트** (AC: 1, 2, 3)
  - [ ] `tests/test_offline_enforcement.py` 신설
  - [ ] R5: `deliver_chunks` 왕복, 수신 측 재조립, 기존 `deliver` 경로 보존,
        `reassembled_by` 값 정확성, 2.1·2.2 테스트 무손상
  - [ ] 하네스: 차단 활성 시 소켓·DNS·subprocess가 **실제로 터진다**(스텁 판별),
        컨텍스트 종료 후 원상복구, 중첩 사용, 예외 발생 시에도 복구
  - [ ] 종단: 연결/차단 두 상태의 **최종 상태·이벤트가 동일**
  - [ ] 문서: `OFFLINE_COMPARISON.md`의 ThinQ 칸이 **"미측정"으로 남아 있음**을
        단언한다 — 나중에 추정치로 채워지는 것을 막는 회귀 테스트
  - [ ] 회귀 기준선: **258 passed** (`66b3a87`)

## Dev Notes

### 🚨 이 스토리의 함정 — 먼저 읽을 것

**1. R5를 안 풀면 이 스토리 전체가 헛것이다.**
현재 청킹은 실행 경로에서 장식이다(2.2 리뷰 Winston). 그 상태로 "차단해도
성공한다"를 보이면, 증명한 대상이 **실제 전송 구조가 아니다.** Task 1이
선행 조건인 이유이며, 순서를 바꾸지 마라.

**2. "부르지 않았다" ≠ "부를 수 없다".**
2.2는 monkeypatch로 **감시**했다. 통과했지만 그건 "이번 실행에서 안 불렀다"이다.
2.3은 **막는다.** 막힌 상태에서 통과해야 심사위원의 의심에 답이 된다.
그래서 하네스는 예외를 던지고, 그 예외가 제품 코드의 `except Exception`에
흡수되면 **테스트가 그것을 잡아야 한다** — fail-closed가 여기서는 함정이 된다.
`OfflineViolation`을 `BaseException` 계열로 두는 것도 검토할 것(단, 그 판단과
이유를 코드 주석에 남길 것).

**3. 화면 표시는 코드가 아는 것만 말한다.**
"네트워크 차단됨"이라고 띄우고 싶겠지만, 코드가 아는 것은
**"이 프로세스의 파이썬 네트워크 API가 막혀 있다"**까지다. 기내모드는 사람이
누르는 것이고 우리는 그것을 관측하지 못한다. AC2의 "차단 사실이 화면에서 확인
가능"은 **하네스 활성 + 실패 시연**으로 만족시키고, 장비 차단은 시연 절차서에
맡긴다. 오늘(2026-07-22) 세 스토리에서 반복된 원칙이다 — **증거와 한계를 같이 적는다.**

**4. AC3은 코드로 완결되지 않는다 — 틀만 만들고 빈칸을 남겨라.**
ThinQ 앱을 기내모드에서 돌리는 건 사람의 일이다. 여기서 "아마 실패할 것"이라고
적으면 그게 바로 NFR6 위반이고, 발표에서 반박당하는 지점이다.
**빈칸 + "미측정"**이 정답이며, 그 빈칸이 나중에 추정치로 채워지지 않도록
테스트로 고정한다(1.2의 "산출 불가 > 그럴듯한 숫자"와 같은 계보).

**5. 하네스 자신이 스텁이면 모든 게 무너진다.**
아무것도 안 막는 하네스도 "위반 없음"을 낸다. 1.1의 스텁 23/23 통과, 1.3의 P4
(항상 실패하는 어댑터가 계약 스위트 통과), 2.2의 AST 검사기 — **같은 병이
네 번째다.** 막힌 상태에서 일부러 소켓을 열어 터지는 것을 반드시 고정하라.

**6. 오늘 확립된 규약을 재발명하지 마라.**
- 배너: `docs/CARRIER_INTERFACE.md §4-b` (경계마다 한 번, 스트림엔 생략)
- 오류 문구: 값 원문 금지, `_show()` 사용 — **두 곳에 복사하면 드리프트한다**
  (2.2 R4). 새 모듈이 필요하면 동기 감시 테스트를 같이 만들 것
- 반환 규약: `(결과|None, errors)` — 제품 코드는 예외 금지 (2.2 R1이 이 규약의
  유일한 예외를 없앴다). **단 하네스는 시험 장비라 예외가 옳다**(함정 2)
- 실패 사유는 **구별해서** 보고 (2.1 BLE 3분할, 2.2 chunk 4분할)

**7. `ble_bless.py` 존치 재평가가 여기서 걸릴 수 있다.**
실기기 데모에서 **가민 워치가 중앙(Central) 역할**이면 Python 주변장치 경로가
불필요하다. Task 1에서 전송 인터페이스를 건드리므로 그 판단이 자연스럽게 올라올
것이다 — **이 스토리에서 삭제 결정을 내리지 말고**, 근거가 모이면
`docs/DECISIONS.md`에 올려 사람이 판단하게 하라.

### 2.2가 넘겨준 상태 (현재 코드)

```python
# home_profile/routine.py — execute_routine 내부
pieces, errs = chunk(data, mtu)          # 쪼개고
restored, errs = reassemble(pieces)      # ← 그 자리에서 다시 붙이고 (R5)
errs = transports[ref].deliver(restored) # 완성본을 넘긴다

# appliance_sim/transports/loopback.py
def deliver(self, data) -> list:         # 2.1 계약 — 완성된 bytes 1개
```

바꿀 것: 재조립을 **수신 측으로**. 남길 것: `deliver()`와 그 테스트.

### 재사용 자산 (새로 만들지 말 것)

| 자산 | 위치 | 용도 |
|---|---|---|
| `chunk` / `reassemble` | `home_profile/routine.py` | 그대로 사용, 호출 위치만 이동 |
| `execute_routine` | 〃 | 재조립 제거 + `reassembled_by` 추가 |
| `deliver` 인터페이스 | `appliance_sim/transports/loopback.py` | 보존 대상 |
| 네트워크 감시 목록 | `tests/test_routine_execution.py` | 하네스 차단 목록의 출발점 |
| 배너 규약 | `docs/CARRIER_INTERFACE.md §4-b` | 새 화면 출력 |
| 증거 한계 표 | `docs/OFFLINE_EVIDENCE.md §2` | 시연 대본에 인용 |
| `_show()` | `routine.py` / `appliance_sim/core.py` | 오류 문구 (동기 유지) |

### 파일 배치

- 신규: `offline_guard.py`(저장소 루트 — 시험 장비이지 제품 코드가 아니다),
  `docs/OFFLINE_COMPARISON.md`, `docs/DEMO_SCRIPT.md`,
  `tests/test_offline_enforcement.py`
- 수정: `home_profile/routine.py`(재조립 이동), `appliance_sim/transports/loopback.py`
  (`deliver_chunks` 추가), `demo_routine.py`(차단 표시·문구 조건부화),
  `docs/OFFLINE_EVIDENCE.md`(2.3 결과 반영 — "실제 차단 실험은 2.3" 문장 갱신)
- `appliance_sim/transports/ble_bless.py`도 `deliver_chunks`를 갖게 되지만
  **미구현 정직 표기 유지** — 동작하는 척 금지(2.1 AC4)

### 테스트 규약

- 정확한 값·개수·이름 단언. '단어 언급' 단언 금지
- 하네스·검사기는 **자기 스텁 판별 테스트를 반드시 동반**
- 두 상태 비교는 "둘 다 성공"이 아니라 **상태·이벤트 동등성**으로
- `pytest.ini`의 `testpaths = tests`

### References

- [Source: docs/planning-artifacts/epics.md#Story 2.3] — AC 원문 (FR3)
- [Source: docs/implementation-artifacts/2-2-profile-driven-ble-command.md#파티 리뷰]
  — R5 이월 사유와 정확한 형태
- [Source: docs/OFFLINE_EVIDENCE.md] — 2.2가 확보한 증거와 그 한계, 2.3의 역할
- [Source: docs/CARRIER_INTERFACE.md#4-b] — 배너 규약
- [Source: docs/planning-artifacts/epics.md#FR Coverage Map] — FR3 → Epic 2 / 2.3
- [Source: docs/CX_DEFINITION.md] — P-1(43.4%) 인용, 대비 자료의 근거
- [Source: docs/implementation-artifacts/1-3-carrier-neutral-abstraction.md]
  — 함정 7(투기적 프레임워크 금지), P4(스텁 판별)

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List

### Change Log
