# 아키텍처 흐름도 — 층 구조·코드 연관성·역류

작성 2026-07-23 · 파티 검수(2026-07-22) 요구사항 반영 · 대상 커밋 `acdb984` 기준

이 문서는 **코드가 어떤 층으로 나뉘고, 명령이 어느 경로로 흐르며, 어디에 역류가
남아 있는지**를 한 장으로 보여준다. 발표 서사에서 **힘 줄 곳(🔴)과 뺄 곳(⚪)**을
시각적으로 구분하는 것이 목적이다. 관련 결정은 [DECISIONS.md](DECISIONS.md),
LG 언어 무기화는 [LGE_KEYWORD_MATRIX.md](LGE_KEYWORD_MATRIX.md) 참조.

---

## 1. 층 구조 + 명령 흐름 (Mermaid)

```mermaid
flowchart TB
    %% ── 진입점 (데모·발표 리허설) ──
    subgraph ENTRY["진입점 · 데모"]
        EN1["demo_night.py<br/>야간 모드 (2.4, 발표 클라이맥스)"]
        EN2["demo_routine.py<br/>루틴 실행 (2.2/2.3)"]
        EN3["python -m appliance_sim<br/>가전 셀프 데모 · --transport ble"]
    end

    %% ── 제품 코어 (처방 트랙, Epic 1) ──
    subgraph HP["home_profile/ — 제품 코어 (처방 트랙, Epic 1)"]
        HP_schema["schema.py<br/>validate_profile · new_profile"]
        HP_storage["storage.py<br/>serialize · chunk · split_chunks"]
        HP_routine["routine.py<br/>routine_to_commands · execute_routine<br/>chunk · reassemble ⬅역류 대상"]
        HP_carrier["carrier.py<br/>Carrier · MemoryCarrier"]
        HP_garmin["carriers/garmin.py<br/>온바디 캐리어 (Garmin ConnectIQ)"]
    end

    %% ── 경계 계약 ──
    BYTES(["명령 bytes<br/>— 층 사이 유일 계약 —"])

    %% ── 시뮬레이터 (Epic 2) ──
    subgraph AS["appliance_sim/ — 가전 시뮬레이터 (Epic 2)"]
        AS_loop["transports/loopback.py<br/>deliver · deliver_chunks"]
        AS_ble["transports/ble_bless.py<br/>BleServerBinding · check_available"]
        AS_wire["wire.py<br/>decode_command"]
        AS_core["core.py<br/>ApplianceState · apply_command"]
    end

    %% ── 🔴 힘 줄 곳 (아직 코드 0) ──
    P2["🔴 P-2 이동성 · Epic 3<br/>초기화·기기이동에도 살아남기<br/>실증 차별화(경쟁 2.0배 열위) — 코드·데모 0"]

    %% ── 정방향 흐름 (edge 0~14) ──
    EN1 --> HP_storage
    EN2 --> HP_storage
    HP_schema --> HP_storage
    HP_storage --> HP_carrier
    HP_carrier -.->|온바디 구현체| HP_garmin
    EN1 --> HP_routine
    EN2 --> HP_routine
    HP_carrier -->|get_records| HP_routine
    HP_routine -->|chunk pieces| BYTES
    BYTES -->|deliver_chunks| AS_loop
    EN3 --> AS_loop
    EN3 --> AS_ble
    AS_loop -->|decode_command| AS_wire
    AS_ble -->|on_write| AS_wire
    AS_wire -->|apply_command| AS_core

    %% ── ⛔ 역류 (edge 15, 빨강) ──
    AS_loop ==>|"import reassemble ⛔ 역류 (loopback.py:53)"| HP_routine

    %% ── 🔴 P-2 위치 (edge 16) ──
    HP_garmin -.->|Epic 3에서 실증| P2

    %% ── 스타일 ──
    classDef core   fill:#dbeafe,stroke:#3b82f6,color:#0b2545;
    classDef sim    fill:#e5e7eb,stroke:#6b7280,color:#111827;
    classDef entry  fill:#f3e8ff,stroke:#a855f7,color:#3b0764;
    classDef bytes  fill:#fef9c3,stroke:#ca8a04,color:#713f12;
    classDef p2     fill:#fee2e2,stroke:#e5484d,color:#7f1d1d,stroke-width:2px;
    classDef fade   fill:#f9fafb,stroke:#d1d5db,color:#9ca3af,stroke-dasharray:4 3;

    class HP_schema,HP_storage,HP_routine,HP_carrier,HP_garmin core;
    class AS_loop,AS_wire,AS_core sim;
    class AS_ble fade;
    class EN1,EN2,EN3 entry;
    class BYTES bytes;
    class P2 p2;

    linkStyle 15 stroke:#e5484d,stroke-width:3px,color:#e5484d;
```

> 렌더 안 되는 뷰어라면: **파랑 = 제품 코어(`home_profile`)**, **회색 = 시뮬레이터
> (`appliance_sim`)**, **노랑 = 명령 bytes 경계**, **빨강 굵은 화살표 = 역류 1건**,
> **🔴 = 힘 줄 곳**, **⚪(점선 흐림) = 뺄 곳**.

---

## 2. 정방향 경로 (한 명령이 흐르는 길)

`demo_night.py`가 대표 경로다. 루프백이든 BLE든 **같은 코드가 돈다** — 그것이
"네트워크를 끊어도 같은 경로"라는 P-1 논증의 근거다.

1. `build_night_profile()` → 프로필 조립 (시뮬레이터는 **소비자**, `home_profile`을
   수정하지 않는다 — 1.2 경계 규약)
2. `storage.serialize()` → bytes → `MemoryCarrier.put_records()` (온바디 저장)
3. `routine.execute_routine(carrier, transports, …)`:
   - `carrier.get_records()` → `deserialize()` → 프로필
   - `routine_to_commands()` → 명령 목록
   - 명령마다 `chunk(data, mtu=20)` → 청크 조각
   - 전송이 `deliver_chunks`를 가지면 **수신 측 재조립**(`reassembled_by="receiver"`),
     없으면 송신 측 폴백(`"sender"`) — 어느 경로였는지 결과에 남긴다(조용한 분기 금지)
4. `loopback.deliver_chunks()` → `reassemble()` → `deliver()` →
   `wire.decode_command()` → `core.apply_command()` → 상태 전이

경계를 넘는 것은 **오직 명령 bytes**다. 이것이 층을 나누는 계약이며, AST 테스트
(`test_appliance_sim.py`)가 `core·wire·loopback`이 표준 라이브러리만 쓰는지 감시한다.

---

## 3. ⛔ 역류 1건 — 청킹이 잘못된 집에 산다

**`appliance_sim/transports/loopback.py:53`**
```python
from home_profile.routine import reassemble
```

시뮬레이터(수신층)가 제품 코어를 **거꾸로 당긴다.** bytes 경계를 뚫는 유일한 지점이다.

- **왜 생겼나 (R5 이월)**: 2.3에서 재조립을 수신 측으로 옮겼다 — 실기기의 실제
  구조(워치가 쪼개 보내고 수신 측이 붙인다)다. 그런데 `reassemble()`의 **몸은**
  여전히 `home_profile.routine`에 있다. 개념상 수신 측(펌웨어) 관심사가 물리적으로
  제품 코어 패키지에 얹혀 있는 상태 — **"잘못된 집"**.
- **왜 지금 안 옮기나**: Epic 3에서 저장 매체가 바뀔 때 `reassemble`의 **올바른
  집**(수신 측 wire 계층 vs 공유 코덱)이 드러난다. 소비자 없이 지금 옮기면 추측이다.
  지금은 **역류를 문서로 표시**해 두고, 매체 변경이 위치를 정하게 한다.
- **오해 방지**: `execute_routine`이 `transport.deliver_chunks()`를 호출하는 것은
  역류가 아니다 — 전송 **인터페이스 주입**(정방향, duck-typed)이다. 역류는 오직
  `import reassemble` 한 줄.

---

## 4. 🔴 힘 줄 곳 = P-2 이동성 (Epic 3)

발표 서사가 **P-1(오프라인/SPOF)에 과집중**돼 있다. 그러나 유일한 **실증** 차별화는
**P-2(재등록·휘발, 경쟁 2.0배 열위)**인데 **코드·데모가 0**이다. P-2가 진짜
클라이맥스여야 한다.

- 코드상 P-2가 살 곳: `carrier.py` → `carriers/garmin.py` (온바디 캐리어). Epic 3가
  "폰을 초기화해도·기기를 옮겨도 프로필이 몸을 따라온다"를 실증한다.
- LG 언어 무기화([LGE_KEYWORD_MATRIX §3]): **"삼성은 지키는 고객감동을 LG는 못
  지키는 지점"** — 실측 2.0배 열위. **"ThinQ ON을 몸에 새겨(OnMe) 이 지점을 완성한다."**
- 제품명 논증: `ThinQ OnMe`는 LG 공식 `ThinQ ON`의 **정당한 계승이자 미완성(P-2)의
  완성**. 이름 자체가 P-2를 반박한다([LGE_KEYWORD_MATRIX §2]).

---

## 5. ⚪ 뺄 곳 = `ble_bless.py`

발표 서사에서 **비중을 줄일 곳**이다(⚪ = 흐림, 점선). 이 머신에서 bless는 설치
자체가 불가능(상류 패키징 자기모순, 2026-07-22 실측)하고, 실기기에선 **가민 워치가
Central** 역할이라 Python 주변장치 경로가 필요 없을 가능성이 크다.

> ⚠️ **⚪는 "발표에서 시간 쓰지 말 것"이지 "파일 삭제"가 아니다.** `ble_bless.py`는
> `__main__.py`의 `--transport ble` 경로·정직 계약 테스트 4개·AST 경계 정의를
> 떠받치고 있다. **삭제 vs 미구현 표기 유지**는 사람 판단 대상 —
> [DECISIONS.md](DECISIONS.md)와 [meetings/2026-07-23_ble-bless-retention.md](meetings/2026-07-23_ble-bless-retention.md) 참조.

---

## 정직 표기 서명 (1.1~2.4 관통 — 유지)

이 흐름도의 어떤 산출물도 **실가전 데이터가 아니다.** 시뮬레이터·미측정·미검증·
"산출 불가" 표기는 발표 전 구간에서 유지한다. BLE는 "동작한 척 금지 — NFR6".
