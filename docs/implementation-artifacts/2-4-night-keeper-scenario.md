---
baseline_commit: 763c6ff
---

# Story 2.4: Night Keeper 야간 모드 시나리오

Status: review

## Story

As a **Night Keeper**,
I want 아이를 깨우지 않고 손목에서 집 상태를 확인·전환하기를,
so that 내가 잠든 뒤에도 집이 아이를 지킨다.

**에픽 맥락**: 2.1(받는 쪽)·2.2(보내는 쪽)·2.3(차단 검증)이 경로를 세우고
의심에 답했다. 2.4는 그 위에 **사람의 이야기**를 얹는다 — Epic 2의, 그리고
발표의 마지막 스토리다. 기술이 아니라 **"내가 잠든 뒤에도 집이 아이를 지킨다"**
는 Job이 화면에 서는 순간이며, 지금까지의 모든 코드가 이 한 장면을 위한 것이다.
[Source: docs/planning-artifacts/epics.md#Story 2.4]

> **발표에서의 위상.** 발표 중심 주장은 AI 오케스트레이션(`WORKFLOW.md §5`)이고
> Epic 2는 그 **마지막 증거**다. 2.4는 그 증거에 서사를 입히되, "이 처방은 VOC
> 실측(P-1 43.4%)에서 나왔고 그 분석은 §5 검수를 통과했다"는 연결을 유지한다.
> 야간 모드 장면이 독립된 감동이 아니라 **검증된 처방의 실행**임을 잊지 않는다.

## Acceptance Criteria

**AC1 — 워치 조작만으로 야간 모드 전환 (FR9)**
**Given** 야간 모드 루틴이 포함된 프로필이 있을 때
**When** 워치에서 야간 모드를 실행하면
**Then** 폰을 켜지 않고 워치 조작만으로 시뮬레이터가 야간 상태로 전환된다

**AC2 — 페르소나 Job과의 대응이 발표 자료에 명시**
**And** 시나리오가 페르소나 Job("내가 잠든 뒤에도…")과 대응됨이 발표 자료에 명시된다

**AC3 — 미검증 페르소나의 정직 표기 (NFR6)**
**Given** 페르소나 인구통계가 아직 미검증일 때
**When** 발표 자료에 페르소나를 제시하면
**Then** "행동 프로파일 — 인구통계는 설문 검증 대기" 라벨이 병기된다

[Source: docs/planning-artifacts/epics.md#Story 2.4]

## Tasks / Subtasks

- [x] **Task 1: 야간 모드 어휘 — 프로필이 말할 수 있는 것** (AC: 1)
  - [x] ⚠️ **새 capability를 발명하기 전에 기존 어휘로 되는지 먼저 보라.**
        야간 모드 = "여러 기기를 밤 상태로 한 번에 전환"이다. 이미 있는
        capability(power·mode·target_temp·fan_speed·child_lock 등)의 조합으로
        표현되는지 확인하고, **정말 필요할 때만** `night_mode` 같은 상태를 추가한다
        (1.1 스키마 상한 = 보안 천장. 어휘를 함부로 늘리지 않는다)
  - [x] 야간 모드는 **루틴 하나**로 표현하는 것이 자연스럽다 — 기존 루틴 구조
        (`trigger` + `actions[]`)가 이미 "여러 기기를 한 번에"를 담는다.
        2.2의 `routine_to_commands`가 그대로 처리한다. **새 실행 경로를 만들지 말 것**
  - [x] 샘플 프로필에 야간 모드 루틴을 넣는 방법을 정한다: `make_sample_profile`을
        건드릴지, 데모 전용 프로필 빌더를 둘지. **`home_profile/`은 수정 최소화**가
        기본(1.2 규약) — 데모 쪽에 야간 루틴을 조립하는 것이 경계상 깨끗하다

- [x] **Task 2: child_lock — 아이를 깨우지 않는다는 Job의 코드적 표현** (AC: 1)
  - [x] Job의 문면이 "아이를 깨우지 않고"다. 야간 모드가 **child_lock을 켜고
        소음원(청소기 등)을 끄는** 것을 포함하면, 서사와 코드가 일치한다.
        단 이것은 **시뮬레이터 상태 전이**이지 실제 안전 기능이 아니다 —
        "아이 안전을 보장한다"로 읽히지 않게 표기한다(NFR5 웰니스·안전 배제 계보)
  - [x] 야간 상태의 관찰 가능성: 전환 후 각 기기 상태가 **의도한 야간 값**임을
        이벤트 로그로 확인. 2.1의 관찰 가능성 규약 승계(print가 아니라 자료구조)

- [x] **Task 3: 야간 모드 데모 — "잠들기 전 손목 한 번"** (AC: 1)
  - [x] `demo_night.py` 또는 `demo_routine.py --scenario night` — 야간 모드
        시나리오를 **하나의 장면으로** 실행. 프로필 → 캐리어 → 야간 루틴 →
        여러 기기 동시 전환 → 상태 확인
  - [x] **오프라인 강제 안에서 실행 가능**해야 한다(2.3 재사용). 발표에서
        "잠들기 전, 기내모드에서, 손목만으로"가 한 화면에 서는 것이 이 스토리의
        절정이다. `--offline` 플래그를 지원하거나 시나리오가 그것을 포함
  - [x] 화면에 **Job 문장을 명시**: "내가 잠든 뒤에도 집이 아이를 지킨다"가
        어느 기기 전환에 대응하는지 보인다. 단 배너 규약(§4-b) 유지
  - [x] ⚠️ 폴백: BLE 안 뜨면 루프백. 실기기 못 쓰면 시뮬레이터. **동작한 척 금지**

- [x] **Task 4: 페르소나 정직 표기 — 발표 자료 (AC: 2, 3)**
  - [x] `docs/PERSONA_NIGHT_KEEPER.md` 신설 — 발표에 그대로 쓸 페르소나 1장.
        Job("내가 잠든 뒤에도…"), 겨냥 Pain(P-1 43.4%), 야간 시나리오와의 대응표
  - [x] ⚠️ **인구통계를 쓰지 마라.** `CX_DEFINITION §3`의 규약: MoA E 에이전트가
        만든 인구통계 페르소나 2건(김민수·김영희)은 **날조로 기각**됐다.
        유효한 것은 **잡 기반 Night Keeper뿐이며 인구통계는 미확인**이다.
        문서 전체에 **"행동 프로파일 — 인구통계는 설문 검증 대기"** 라벨을 단다
  - [x] 시나리오 ↔ Job 대응표: 각 기기 전환이 Job의 어느 부분을 실현하는지.
        발표자가 이 표를 그대로 읽을 수 있어야 한다(AC2)
  - [x] 근거 연결: 이 페르소나가 §5 검수를 통과한 분석에서 나왔음을 1줄로 명시 —
        발표 서사(오케스트레이션의 마지막 증거)와의 접점

- [x] **Task 5: 테스트 (AC: 1, 2, 3)**
  - [x] `tests/test_night_scenario.py` 신설
  - [x] 야간 루틴 실행 → 여러 기기가 **의도한 야간 값**으로 전환됨(정확한 값 단언)
  - [x] 오프라인 강제 안에서 동일 결과(2.3 종단 동등성 패턴 재사용)
  - [x] child_lock·소음원 off가 실제로 상태에 반영됨
  - [x] 데모: 시나리오 실행 성공, Job 문장 표시, 배너 규약 준수
  - [x] **문서 회귀**: `PERSONA_NIGHT_KEEPER.md`에 "설문 검증 대기" 라벨이 있고,
        **인구통계 수치(나이·성별·소득 등)가 없음**을 단언한다 — 날조 페르소나가
        슬며시 돌아오는 것을 막는다(1.2 "미측정 빈칸" 회귀 테스트와 같은 계보)
  - [x] 회귀 기준선: **283 passed** (`c4fa328`)

## Dev Notes

### 🚨 이 스토리의 함정 — 먼저 읽을 것

**1. 이건 새 기능이 아니라 기존 부품의 조립이다.**
2.1·2.2·2.3이 이미 다 만들었다 — 프로필, 루틴 실행, 청킹, 오프라인 강제.
야간 모드는 그것들 위에 **하나의 시나리오**를 얹는 것이다. 새 실행 경로·새
전송·새 상태 기계를 만들면 그건 이 스토리를 오해한 것이다. `routine_to_commands`가
야간 루틴을 그대로 처리하고, `execute_routine`이 그대로 실행하고, `enforce_offline`이
그대로 감싼다. **조립이 깨끗하면 이 스토리는 작다.**

**2. 페르소나 인구통계 날조는 이 프로젝트가 실제로 저지른 실수다.**
MoA E 에이전트가 김민수(38세)·김영희(35세) 같은 인구통계를 지어냈고 **날조로
기각**됐다(`CX_DEFINITION §3`). 그 유혹이 이 스토리에서 정확히 재현된다 —
발표 페르소나를 예쁘게 만들려면 나이·직업·소득을 넣고 싶어진다. **넣지 마라.**
유효한 것은 Job("내가 잠든 뒤에도…")과 그것이 겨냥하는 실측 Pain(P-1 43.4%)뿐이다.
"행동 프로파일 — 인구통계는 설문 검증 대기"가 이 프로젝트의 서명이고, 그 라벨이
빠진 페르소나는 발표에서 우리를 반박하는 증거가 된다.

**3. "아이를 지킨다"를 안전 기능으로 과장하지 마라.**
Job의 문면이 감정적이라 위험하다. child_lock을 켜는 것은 **시뮬레이터 상태
전이**이지 실제 아동 안전 보장이 아니다. NFR5(웰니스·의료·안전 판단 배제)의
계보다 — "집이 아이를 지킨다"는 **서사**이고, 코드가 하는 것은 "야간 루틴이
정의한 기기 상태로 전환"까지다. 발표에서 이 선을 넘으면 규제·윤리 반박을 부른다.

**4. 오프라인 + 야간이 한 화면에 서는 것이 절정이다.**
2.3의 `enforce_offline`을 재사용해 "잠들기 전, 네트워크 없이, 손목만으로"를
한 장면에 담는다. 이것이 발표에서 Epic 2 전체가 수렴하는 지점이다. 단 2.3의
한계 표기도 함께 간다 — 프로세스 차단이지 장비 차단이 아니고, 장비 기내모드는
사람이 누른다(`DEMO_SCRIPT.md §3`).

**5. 오늘 확립된 규약 전부 승계 — 재발명 금지.**
- 배너: `CARRIER_INTERFACE.md §4-b` (경계마다 한 번, 스트림엔 생략)
- 관찰 가능성: print가 아니라 이벤트 로그 자료구조 (2.1)
- 정직 표기: 시뮬레이터·미측정·미검증을 라벨로 (전 스토리)
- 반환 규약·예외 금지: 제품 코드 `(결과|None, errors)` (2.2 R1)
- `home_profile/` 수정 최소화, 데모/문서 쪽에 시나리오 조립 (경계)

**6. `ble_bless.py` 존치 결정이 이 스토리 완료 후 올라온다.**
2.1(설치 불가)·2.3(가민 중앙 역할) 근거가 다 모였다. **이 스토리에서 삭제하지
말고**, 2.4 완료 = Epic 2 완료 시점에 `docs/DECISIONS.md`에 올려 사람이 판단한다.

### 재사용 자산 (전부 있음 — 새로 만들 것 거의 없음)

| 자산 | 위치 | 용도 |
|---|---|---|
| `make_sample_profile` | `home_profile/storage.py` | 프로필 뼈대 (야간 루틴은 데모에서 조립) |
| `routine_to_commands`·`execute_routine` | `home_profile/routine.py` | 야간 루틴 실행 — 그대로 |
| `chunk`/`reassemble` | 〃 | 청킹 — 그대로 |
| `LoopbackTransport.deliver_chunks` | `appliance_sim/transports/loopback.py` | 수신 측 재조립 (2.3) |
| `ApplianceState` | `appliance_sim/core.py` | 야간 상태·이벤트 |
| `enforce_offline` | `offline_guard.py` | 오프라인 절정 장면 (2.3) |
| 배너·`console_safe` | `appliance_sim/core.py` | 화면 출력 |
| 페르소나 규약 | `docs/CX_DEFINITION.md §3` | "설문 검증 대기" 라벨 |
| 시연 절차서 | `docs/DEMO_SCRIPT.md` | 야간 장면을 이 대본에 추가 |

### 파일 배치

- 신규: `docs/PERSONA_NIGHT_KEEPER.md`, `tests/test_night_scenario.py`,
  그리고 데모(`demo_night.py` **또는** `demo_routine.py`에 `--scenario night`)
- 수정 최소: `home_profile/`은 되도록 건드리지 않는다. 야간 루틴은 데모/테스트
  쪽에서 조립. `docs/DEMO_SCRIPT.md`에 야간 장면 절 추가
- child_lock이 기존 capability에 없으면 그때 스키마 논의 — **먼저 있는지 확인**

### 페르소나 원문 (CX_DEFINITION §3 — 그대로 인용)

- **"밤에 지키는 사람 (The Night Keeper)"** — 잡 기반, 인구통계 미확인
- 등급: **리뷰 기반 잠정(provisional)** — 플레이스토어 리뷰엔 인구통계가 없다
- MoA E의 인구통계 페르소나 2건(김민수·김영희)은 **날조로 기각**
- 유효한 유일 페르소나이며 발표 시 "설문 검증 대기" 병기 필수

### 테스트 규약

- 정확한 값 단언(야간 상태값), '단어 언급' 금지
- 오프라인 종단 동등성은 2.3 패턴 재사용
- 문서 회귀: 미검증 라벨 존재 + 인구통계 수치 부재를 **둘 다** 단언
- `pytest.ini` testpaths = tests

### References

- [Source: docs/planning-artifacts/epics.md#Story 2.4] — AC 원문 (FR9)
- [Source: docs/planning-artifacts/epics.md#Epic 2] — 발표에서의 위상
- [Source: docs/CX_DEFINITION.md#3] — Night Keeper 페르소나·날조 기각·라벨 규약
- [Source: docs/implementation-artifacts/2-3-offline-enforcement.md]
  — `enforce_offline` 재사용, 종단 동등성 패턴, 한계 표기
- [Source: docs/implementation-artifacts/2-2-profile-driven-ble-command.md]
  — `routine_to_commands`·`execute_routine`, 배너 규약
- [Source: docs/DEMO_SCRIPT.md] — 야간 장면을 추가할 시연 대본
- [Source: docs/CX_DEFINITION.md#1] — P-1(43.4%), 처방의 근거

## Dev Agent Record

### Agent Model Used

Claude Opus 4.8 (claude-opus-4-8) — 2026-07-22

### Debug Log References

- 착수 전 확인: 야간 모드 어휘가 기존 capability로 표현되는지 실측 →
  `_CAPABILITIES`에 power·mode·fan_speed·child_lock·eco_mode 등이 이미 있고
  `night` 토큰은 없음. **새 capability 발명 불필요 확인**(함정 1).
  device_type에 `robot_cleaner`·`light`도 이미 있음.
- RED: `demo_night` 없음 → collection error
- GREEN 1차: 12/13 — 페르소나 문서 회귀 1건 실패. **테스트가 내 문서를 잡음**:
  "소득" 단어를 금지했는데 문서가 "소득이 존재하지 않는다"고 정직하게 설명하는
  부분까지 걸렸다(오늘 OFFLINE_EVIDENCE "모든" 자기참조와 같은 종류).
  → 날조의 서명은 단어가 아니라 **수치**이므로 `연봉/소득 \d`·`\d세`·`\d만원`
  패턴만 금지하도록 정밀화. 이름(김민수·김영희) 금지는 유지.
- GREEN 2차: 13/13
- 데모 실측(`--offline`): 온바디 955B → 가전 4대 → 야간 전환(에어컨 조용히·
  청소기 끔·조명 끔·냉장고 잠금) → `재조립 receiver`(2.3 R5 경로) → exit 0
- 전체 회귀: **296 passed** (283 + 13, 회귀 0)

### Completion Notes List

- **Task 1**: 야간 모드 = 기존 어휘 조합. **새 capability 없음**을 테스트로
  고정(`test_night_routine_uses_only_known_capabilities`). 야간 루틴은
  `routine` 구조 하나로 표현되고 `routine_to_commands`가 그대로 처리 —
  새 실행 경로 없음.
- **Task 2**: `child_lock: true`(냉장고) + `power: false`(로봇청소기·조명)로
  "아이를 깨우지 않는다"를 코드로 표현. 단 **서사이지 안전 기능이 아님**을
  페르소나 문서와 스토리에 명시(NFR5). 전환은 이벤트 로그로 관찰(2.1 규약).
- **Task 3**: `demo_night.py` — `--offline`로 "잠들기 전·네트워크 없이·손목만"이
  한 화면에. 각 전환의 Job 대응을 화면에 표시. 배너 규약(4경계) 준수.
  위반은 우아하게 표시(2.3 R3 계승).
- **Task 4**: `docs/PERSONA_NIGHT_KEEPER.md` — Job·P-1 근거·시나리오 대응표.
  **"행동 프로파일 — 인구통계는 설문 검증 대기" 라벨**(AC3). 시나리오↔Job
  대응이 `demo_night._NIGHT_ACTIONS`와 1:1(코드가 진실 원천). `DEMO_SCRIPT.md`에
  야간 클라이맥스 절 추가.
- **Task 5**: `tests/test_night_scenario.py` 13개 — 어휘 검증, 전환 값 정확성,
  오프라인 종단 동등성, child_lock·소음원, 데모, **페르소나 날조 회귀 방지**
  (기각된 이름 부재 + 인구통계 수치 부재).

### File List

- `demo_night.py` — 신규 (야간 시나리오 데모 + `build_night_profile`)
- `docs/PERSONA_NIGHT_KEEPER.md` — 신규 (발표용 페르소나, 정직 표기)
- `docs/DEMO_SCRIPT.md` — 수정 (야간 클라이맥스 장면 추가)
- `tests/test_night_scenario.py` — 신규 (13 tests)
- `docs/implementation-artifacts/2-4-night-keeper-scenario.md` — 본 파일
- ※ `home_profile/`·`appliance_sim/` **무수정** — 조립만으로 완성(경계 유지)

### Change Log

- 2026-07-22: Story 2.4 구현 완료 — Night Keeper 야간 모드 시나리오.
  기존 어휘 조립(새 capability·새 경로 없음), 오프라인 절정 장면, 페르소나
  정직 표기(인구통계 미검증 라벨 + 날조 회귀 방지). **home_profile 무수정**.
  **296 passed** (신규 13, 회귀 0). **Epic 2 완료.**
  Status: ready-for-dev → review.

### 사람 결정 대기 (Epic 2 완료 — 올릴 시점)

- **`ble_bless.py` 존치** — 2.1(설치 불가 실측)·2.3(가민 중앙 역할)에서 이월된
  근거가 다 모였다. Epic 2가 완료됐으므로 **이제 `docs/DECISIONS.md`에 올려
  사람이 판단할 시점**이다. 요지: 실기기 데모에서 가민 워치가 Central이면
  Python 주변장치(`ble_bless.py`) 경로가 불필요하며, bless는 이 환경에서 설치
  자체가 불가능하다. 삭제 vs 미구현 표기 유지 중 택일.
