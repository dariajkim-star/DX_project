---
baseline_commit: 2faf85f
---

# Story 2.1: 가전 시뮬레이터 (BLE 주변장치)

Status: done

## Story

As a **발표자**,
I want 실가전 없이도 가전 역할을 하는 시뮬레이터가 있기를,
so that 실기기 조달 없이 구조를 실증할 수 있다.

**에픽 맥락**: Epic 2는 "서버 없는 야간 모드 전환"을 실기기로 실증하는 **주장의 실증
단계**이며, 발표 중심 주장(AI 오케스트레이션)의 **마지막 증거**다. 2.1은 그 무대의
바닥이다 — 명령을 받아줄 가전이 없으면 2.2(명령 전송)·2.3(오프라인 강제)·2.4(야간
시나리오)가 전부 공중에 뜬다. Epic 1이 "무엇을 보낼 것인가"(프로필·조각·어댑터)를
완성했고, 2.1은 "받는 쪽"을 세운다.
[Source: docs/planning-artifacts/epics.md#Epic 2] [Source: docs/PROTO_KICKOFF.md]

## Acceptance Criteria

**AC1 — BLE 주변장치로서의 가전 상태 (FR8)**
**Given** BLE 주변장치로 동작하는 시뮬레이터가 필요할 때
**When** 시뮬레이터를 실행하면
**Then** 가전 상태(예: 전원·모드·온도)를 보유하고 BLE 특성으로 노출한다

**AC2 — 명령 수신·반영 관찰 가능 (FR8)**
**And** 수신한 명령에 따라 상태가 변하고 그 변화가 관찰 가능하다

**AC3 — 시뮬레이터 정직 표기 (NFR6)**
**Given** 시뮬레이터가 산출물을 남길 때
**When** 로그·화면을 확인하면
**Then** **"시뮬레이터 — 실가전 아님"** 표기가 항상 함께 노출된다

[Source: docs/planning-artifacts/epics.md#Story 2.1]

## Tasks / Subtasks

- [x] **Task 1: 가전 상태 코어 — 전송 무관 상태 기계** (AC: 1, 2)
  - [x] `appliance_sim/core.py` 신설 — **표준 라이브러리만**(1.1~1.3 원칙 승계).
        BLE·bless import 금지 — 코어는 전송을 모른다(캐리어 경계와 동일 계보)
  - [x] `ApplianceState` — 기기 1대의 상태. **키·값 어휘는 발명하지 않는다**:
        `home_profile.storage`의 `_CAPABILITIES`·`_DEVICE_TYPES`가 쓰는
        capability 토큰(power/mode/target_temp/fan_speed/…)과 값 타입 규약
        (스칼라만: str≤64/int/bool)을 **그대로** 따른다. 프로필이 보낼 수 없는
        상태는 시뮬레이터에 있을 이유가 없다
  - [x] `apply_command(cmd) -> (applied: bool, errors: list[str])` — **예외 금지
        fail-closed** (1.1 리뷰 F3 계승: 크래시는 곧 검사 우회). 와이어 불신:
        수신 명령은 화이트리스트(capability 토큰·값 타입·범위) 검증 후 반영,
        위반은 목록 반환. 오류 문구에 **수신 값 원문 금지**(1.3 P2 계승 —
        타입명·크기·키 이름 32자 절단까지만)
  - [x] 상태 변화 이벤트 로그 — `events() -> list`(단조 seq·시각·무엇이 어떻게
        바뀌었나). AC2의 "관찰 가능"은 print가 아니라 **조회 가능한 자료**여야
        테스트가 스텁을 판별한다

- [x] **Task 2: 명령 와이어 계약** (AC: 2)
  - [x] `appliance_sim/wire.py` — 명령 인코딩/디코딩. **JSON UTF-8 compact**
        (프로필 기준 표현과 동일 — 새 포맷 발명 금지). 형식:
        `{"v": 1, "device_ref": …, "set": {cap: value, …}}`
  - [x] `decode_command(data: bytes) -> (cmd | None, errors)` — deserialize와
        같은 계보: 크기 상한 먼저, BOM 허용, 중복 키 거부, 예외 금지.
        **버전 불일치는 명시 거부**(조용한 통과 금지)
  - [x] ⚠️ **크기 상한은 `storage.MAX_WIRE_BYTES`(131,072B)를 쓰지 말 것.**
        그건 **프로필 전체**의 상한이다. 명령 1건은 기기 참조 + 설정 몇 개라
        수백 바이트 규모이며, 20B MTU로 재조립되는 입력에 128KB를 허용하면
        BLE 경로에 6,500청크짜리 메모리 고갈 창구를 여는 것이다(2차 리뷰 Vex F5가
        막았던 바로 그 병의 재판). `MAX_COMMAND_BYTES`를 **시뮬레이터 쪽에 별도
        선언**하고(권고: 1,024B — 최악 명령 실측 후 조정) 근거를 주석에 남긴다.
        실측: capability 10종 전부 + 최대 길이 값으로 최악 명령 크기를 재고,
        그 수치를 상한 근거로 적을 것
  - [x] ⚠️ BLE 청킹(20B MTU 재조립)은 **이 스토리 밖**이다 — 그건 2.2(전송자)와
        전송 바인딩의 일이다. wire는 "완성된 bytes 1개"만 다룬다

- [x] **Task 3: 전송 바인딩 경계 — 루프백(기본) + BLE(옵션)** (AC: 1)
  - [x] `appliance_sim/transports/loopback.py` — 함수 호출로 bytes를 전달하는
        참조 전송. **표준 라이브러리만.** 자기 표기: `is_radio=False`,
        라벨 `"루프백 — BLE 아님"`. 테스트·CI·BLE 불가 환경 데모 폴백의 유일한 경로
  - [x] `appliance_sim/transports/ble_bless.py` — **bless 사용 승인됨(이 모듈
        한정)**. GATT 서비스 1개 + 특성: 명령 수신(write)·상태 노출(read/notify).
        import 실패·어댑터 부재 시 **예외가 아니라** "BLE 사용 불가(사유)" 오류
        목록으로 보고하고 루프백 폴백을 **명시 로그**와 함께 안내
  - [x] 경계 테스트: `appliance_sim/core.py`·`wire.py`에 bless·bluetooth 계열
        import가 없음을 AST로 단언 — `tests/test_carrier_neutrality.py`의
        `_imported_modules`/`_vendor_violations` 패턴 재사용(P3 반영판:
        동적 import·부분일치 포함). 전송 토큰: `bless`, `bleak`, `bluez`,
        `winrt`, `bluetooth`
  - [x] ⚠️ **이 개발 머신에 BLE 주변장치 가능 어댑터가 있는지 미확인**이다.
        BLE 실동작은 "확인 필요"로 남기고, 실행 성공/실패 사실만 기록한다.
        실패해도 스토리는 완료다 — AC1의 실증은 실기기 준비(Epic 2 후속) 시점에
        가민 실기기와 함께 검증한다. **동작한 척 금지**(NFR6)

- [x] **Task 4: 정직 표기 상시 노출** (AC: 3)
  - [x] 배너 상수 `SIMULATOR_BANNER = "시뮬레이터 — 실가전 아님"` — 모든 출력
        경로(기동 로그·이벤트 로그의 각 스냅샷·상태 조회 응답·BLE 기기명/
        서비스 설명)에 포함. **읽히지 않는 상수 금지**(1.1 MIGRATIONS 교훈):
        배너를 실제로 싣는 코드 경로가 각각 존재해야 한다
  - [x] BLE 광고 이름에도 표기가 실린다(예: `SIM-NOT-REAL-<ref>`) — 화면 캡처
        어디에도 "실가전"으로 읽힐 여지를 남기지 않는다
  - [x] 테스트: 기동 로그·이벤트·상태 응답 각각에서 배너 문자열을 정확 단언

- [x] **Task 5: 실행 진입점** (AC: 1, 2, 3)
  - [x] `python -m appliance_sim` — 인자: `--transport loopback|ble`(기본
        loopback), `--device-ref`, `--device-type`. cp949 콘솔 안전(이모지 금지,
        `sys.stdout.reconfigure` 또는 ASCII 폴백 — DEV_PLAN Windows 규약)
  - [x] 루프백 모드 셀프 데모: 내장 샘플 명령 2~3개를 순서대로 주입해 상태 전이를
        보여주고 종료 — 발표 리허설·스크린샷용. 주입 명령도 "루프백 셀프 데모"
        라벨과 함께 로그
  - [x] BLE 모드: 기동 시 어댑터 검사 → 불가면 사유 출력 후 비정상 종료 코드
        (조용한 루프백 대체 금지 — 사용자가 명시한 전송이 안 되면 정직하게 실패)

- [x] **Task 6: 테스트 (pytest 영구 자산)** (AC: 1, 2, 3)
  - [x] `tests/test_appliance_sim.py` 신설 — testpaths 규약 준수
  - [x] 상태 기계: 유효 명령 반영(정확한 값 단언), 무효 명령 거부(미지 capability·
        타입 위반·범위 위반·미지 device_ref), 거부 시 상태 불변(원자성),
        이벤트 로그 정합(seq 단조·변경 내용 일치)
  - [x] wire: 왕복 등가, 손상 bytes·크기 초과·중복 키·버전 불일치 거부, 예외 금지
        (BAD_INPUTS 스타일 — 1.3 계약 스위트 패턴 재사용)
  - [x] 루프백 종단: encode → 루프백 전달 → decode → apply → 상태·이벤트 확인
  - [x] 경계: core·wire의 전송 라이브러리 import 부재(AST) + 검사기 자체가 가짜
        소스에서 실패함을 확인(스텁 판별 — 1.1 교훈·1.3 P4 계승)
  - [x] ⚠️ BLE 바인딩은 단위 테스트 **면제**(하드웨어 의존) — 대신 "bless 부재
        환경에서 import 시도 시 예외 없이 오류 보고" 딱 하나는 가짜 환경으로 고정
  - [x] 회귀 기준선: **176 passed** (`2faf85f`). 전체 스위트 통과 유지

## Dev Notes

### 🚨 이 스토리의 함정 — 먼저 읽을 것

**1. BLE가 이 스토리의 본체가 아니다 — 상태 기계가 본체다.**
발표에서 무너지면 안 되는 것은 "명령을 받으면 상태가 바뀌고 그게 보인다"이지
전파가 아니다. BLE는 전송 바인딩 1개일 뿐이고, Windows에서 Python BLE 주변장치는
동작 보증이 약하다(아래 기술 현황). 그래서 **코어는 전송 무관**으로 짓고 루프백으로
전 기능을 실증한다. BLE가 이 머신에서 안 떠도 스토리는 완료다 — 단, "안 떴다"를
기록한다. 뜬 척은 NFR6 위반이다.

**2. 새 의존성 규약 — bless는 ble_bless.py 한정 승인, 코어는 표준 라이브러리만.**
dev-story의 "추가 의존성은 사용자 승인 필요" 규칙에 대해: 이 스토리는
**`bless`를 `appliance_sim/transports/ble_bless.py` 안에서만** 쓰도록 사전
승인한다(스토리 작성 시점 결정). 코어·wire·테스트에 새면 캐리어 중립과 같은
원리로 경계 위반이며, Task 3의 AST 테스트가 이를 감시한다. bless 외 다른 BLE
라이브러리로 바꿀 필요가 생기면 HALT하고 물어볼 것.

**3. 어휘 발명 금지 — 프로필이 말할 수 있는 것만 가전이 알아듣는다.**
capability 토큰·값 타입은 `home_profile.storage._CAPABILITIES` 계열과 동일해야
한다. 시뮬레이터에 프로필이 보낼 수 없는 명령(예: `brightness`)을 넣으면 2.2에서
"보낼 수 없는 것을 받는 가전"이 되고, 반대로 빠뜨리면 데모 루틴이 죽는다.
단 `_CAPABILITIES`는 비공개 심볼이다(`__all__` 미포함) — **제품 코드에서 직접
import하지 말고** 토큰 목록을 시뮬레이터 쪽에 명시 선언하고, **테스트에서만**
`storage._CAPABILITIES`와 대조해 드리프트를 감시한다(1.3 P8의 절연 원리 —
비공개 심볼 의존은 테스트에 격리, 단 여기선 동기 자체가 계약이라 단언으로 고정).

값 검증 범위는 `storage._sample_value`가 만드는 값의 도메인을 참고하되
**복사가 아니라 판단**이다: bool 계열(power/child_lock/eco_mode), 정수 계열
(target_temp/humidity/timer_min), 열거 계열(fan_speed: low/mid/high,
mode: cool/heat/dry/auto). 명시 선언하고 근거를 주석에 남길 것.

**4. 예외 금지·와이어 불신·오류에 값 금지 — 전부 그대로 상속.**
`apply_command`·`decode_command`는 어떤 입력에도 예외를 던지지 않는다.
BLE write로 들어오는 bytes는 적대적 입력이다(deserialize와 동일 지위):
크기 상한 먼저, 파싱은 그 다음, 반영은 검증 후. 거부 메시지에 수신 값 원문을
싣지 않는다 — 1.3 P2에서 이름 채널까지 막았던 것과 같은 기준(`_show_name` 계보).

**5. "관찰 가능"을 print로 때우지 말 것.**
AC2의 관찰 가능성은 조회 가능한 이벤트 로그(자료구조)가 근거고, 화면 출력은 그
투영이다. print만 있으면 테스트가 캡처 문자열 grep으로 전락한다 — 1.1 "단어 언급
단언 금지" 교훈. 이벤트는 정확한 값(seq·capability·old→new)으로 단언한다.

**6. 범위 통제 — 2.2~2.4를 미리 짓지 말 것.**
루틴 실행기(프로필→명령 변환)는 2.2다. 오프라인 증명은 2.3이다. 야간 모드
시나리오는 2.4다. 여기서는 **명령 bytes를 받아 상태를 바꾸는 가전 1대**만 짓는다.
멀티 기기 오케스트레이션·페어링·인증도 전부 밖이다(인증은 Epic 4).
1.3 함정 7(투기적 프레임워크 금지)과 같은 원리.

**7. 시뮬레이터 표기는 장식이 아니라 계보다.**
`--demo` 플래그·합성 패널 워터마크와 같은 원칙(NFR6): 이 산출물이 실데이터/실기기
로 인용되는 순간 프로젝트 전체의 신뢰 서사가 무너진다. 배너는 모든 출력 경로에
실리고, 각 경로마다 테스트가 있다. BLE 광고명까지 포함하는 이유다.

### 기술 현황 — Python BLE 주변장치 (조사 2026-07-22)

- [bless](https://github.com/kevincar/bless): 크로스플랫폼 Python GATT **서버**
  라이브러리(주변장치 역할). bleak(중앙 역할)의 자매 격. Windows는 WinRT 경유로
  지원 표방하나 **이 머신에서의 동작은 미확인** — 어댑터가 주변장치 모드를
  지원해야 하며 데스크톱 BLE 동글/내장 카드 편차가 크다.
- 검증 순서 권고: ① 루프백으로 전 기능 완성 ② `--transport ble` 기동 시도
  ③ 성공 시 폰 BLE 스캐너 앱으로 광고명 확인까지만(가민 연동은 2.2)
- 실패 대비 폴백이 데모 서사에 이미 있다: 발표 범위는 "가민 실기기 → BLE →
  시뮬레이터"이고, 호스트 루프백은 리허설·구조 설명용으로 정직 표기 후 사용
  [Source: docs/PROTO_KICKOFF.md — 데모 목표]

### 재사용 자산 (Epic 1 산출물 — 새로 만들지 말 것)

| 자산 | 용도 |
|---|---|
| JSON UTF-8 compact 기준 표현 (`storage` docstring §포맷) | wire 인코딩 — 새 포맷 발명 금지 |
| `home_profile.storage._CAPABILITIES` 어휘 (동기 테스트로 감시) | 명령 화이트리스트 |
| `tests/test_carrier_neutrality.py`의 AST 검사기 패턴 (P3 반영판) | 전송 경계 감시 |
| 1.3 계약 스위트의 BAD_INPUTS·카나리아 패턴 | apply/decode 견고성 테스트 |
| `MemoryCarrier` (1.3) | 2.2에서 프로필 조각 공급원 — 이 스토리에선 미사용 |

### 파일 배치

- 신규: `appliance_sim/__init__.py`, `appliance_sim/core.py`,
  `appliance_sim/wire.py`, `appliance_sim/transports/__init__.py`,
  `appliance_sim/transports/loopback.py`, `appliance_sim/transports/ble_bless.py`,
  `appliance_sim/__main__.py`, `tests/test_appliance_sim.py`
- `home_profile/`은 **수정하지 않는 것이 기본**(1.2 규약 승계). 시뮬레이터는
  소비자이지 소유자가 아니다
- 분석 파이프라인(`dx_pipeline*`)과 계보 무관 — import 금지(기존 원칙)

### 테스트 규약

- 정확한 값·개수·이름 단언. '단어 언급' 단언 금지 (배너 존재 단언은 AC3 문면이
  표기 규약 자체이므로 예외 — 1.3과 동일 논리)
- 경계: 빈 bytes·크기 초과 직전/직후·미지 capability·타입 위반·seq 연속성·
  거부 후 상태 불변
- BLE 하드웨어 의존 테스트 금지 — CI·타 머신 재현성이 우선

### References

- [Source: docs/planning-artifacts/epics.md#Story 2.1] — AC 원문 (FR8, NFR6)
- [Source: docs/planning-artifacts/epics.md#Epic 2] — 에픽 목적·발표에서의 위상
- [Source: docs/PROTO_KICKOFF.md] — 데모 목표(워치 2대 캐리어 중립·가전은 시뮬레이터)
- [Source: docs/implementation-artifacts/1-3-carrier-neutral-abstraction.md#Review Findings]
  — P2(이름 채널)·P3(AST 검사기)·P4(스텁 판별) 계승 지점
- [Source: docs/PROFILE_SCHEMA.md#5] — BLE MTU 20B·long write 미지원(포럼발) —
  청킹이 2.2로 미뤄진 근거
- [Source: docs/DEV_PLAN.md#5] — 운영 원칙(정직 표기·cp949·pytest 영구화)
- bless (BLE GATT 서버, 크로스플랫폼): https://github.com/kevincar/bless — Windows
  동작은 이 머신에서 **미확인**

## Dev Agent Record

### Agent Model Used

Claude Opus 4.8 (claude-opus-4-8) — 2026-07-22

### Debug Log References

- RED: `ModuleNotFoundError: appliance_sim` (구현 전 실패 확인)
- GREEN 1차: 37/39 — **자기 테스트에 2건 적발**(둘 다 진짜 결함):
  1. `test_errors_never_contain_received_values`: `_show()`가 32자 이하 문자열을
     원문 표시해서 28자 PII 카나리아가 오류 문구로 샜다. 1.3 P2의 "길이 절단"만으로는
     부족 — **형식 검증**이 필요했다. 스키마의 device_ref 토큰 형식
     (`^[a-z0-9][a-z0-9_-]{0,31}$`)을 통과한 문자열만 원문 표시하도록 교체
     (storage._VERSION_SHOW_RE와 같은 방어 계보, 1.2 Vex F4).
  2. `test_startup_lines_are_cp949_safe`: **배너 자체의 em dash(—)가 cp949로
     인코딩 불가**. 배너 문자열은 AC3의 문면이라 바꿀 수 없으므로 출력 경로에
     `console_safe()` 도입 — 인코딩 때문에 표기가 통째로 사라지는 것이 최악
     (표기 누락 = NFR6 위반). 테스트도 출력 경로 대상으로 재작성.
- **BLE 실측(정직 기록)**: `python -m appliance_sim --transport ble` →
  `bless` 미설치(`ModuleNotFoundError`)로 **기동 실패, exit 2**.
  조용한 루프백 대체 없이 사유 출력 후 종료됨을 육안·테스트 양쪽으로 확인.
  **이 머신에서 BLE 주변장치 실동작은 여전히 미확인**이며, 실증은 실기기 준비
  시점(가민 연동)으로 남는다. 설치하지 않은 이유: 스토리 함정 1의 판단
  (BLE는 본체가 아니며, 안 뜨는 사실을 기록하는 것이 뜬 척보다 낫다).
- 루프백 셀프 데모 실측: 명령 3건 50B/68B/72B, 상태 전이 5건, exit 0.
- 최종: `python -m pytest tests/ -q` → **219 passed** (기존 176 + 신규 43, 회귀 0)

### Completion Notes List

- **Task 1**: `appliance_sim/core.py` — `ApplianceState`(상태·이벤트·배너),
  표준 라이브러리만. `apply_command`는 예외 금지·**원자적**(한 항목 거부 시
  배치 전체 미반영)·화이트리스트 검증(capability 존재/기기 선언 여부/타입/범위).
  bool이 int 서브클래스인 점을 명시 배제(`{"target_temp": True}` 통과 방지).
  `events()`는 깊은 복사본 반환 — 호출자가 내부 로그를 지울 수 없다.
- **Task 2**: `wire.py` — JSON UTF-8 compact(프로필 기준 표현 동일).
  **`MAX_COMMAND_BYTES = 1024`**를 별도 선언(스토리 지시대로 `MAX_WIRE_BYTES`
  128KB 미사용 — 20B MTU 재조립 DoS 창구 차단). 최악 명령 실측을 테스트로 고정
  (`test_max_command_bytes_covers_worst_case`). BOM 허용·중복 키 거부·버전
  명시 거부·예외 금지 전부 deserialize 계보.
- **Task 3**: `transports/loopback.py`(is_radio=False, "루프백 — BLE 아님") +
  `transports/ble_bless.py`(bless 의존은 여기만, `check_available()`이 예외 대신
  오류 보고). AST 경계 테스트가 core·wire·loopback에 전송 라이브러리 import
  부재를 단언하고, **검사기 자체가 가짜 소스에서 실패함**도 고정(1.3 P3·P4 계승).
- **Task 4**: `SIMULATOR_BANNER`가 snapshot·이벤트 각 건·기동 로그·상태 조회
  페이로드·BLE 광고명(`SIM-NOT-REAL-<ref>`)에 실린다 — 경로마다 테스트 1개씩.
- **Task 5**: `python -m appliance_sim` — 루프백 셀프 데모(명령 3건 주입 →
  상태 전이 출력), `--transport ble`은 **조용한 대체 없이** 사유 출력 후 exit 2.
  `console_safe()`로 cp949 콘솔 안전.
- **Task 6**: `tests/test_appliance_sim.py` 43개 — 어휘 동기, 상태 기계(정확값·
  원자성·이벤트 정합), 예외 금지 9종 입력, PII 카나리아 3경로, 와이어 계약
  (왕복·초과·중복키·버전·BOM), 루프백 종단, 진입점 3종, AST 경계 + 스텁 판별.

### File List

- `appliance_sim/__init__.py` — 신규 (공개 표면)
- `appliance_sim/core.py` — 신규 (상태 기계·배너·console_safe)
- `appliance_sim/wire.py` — 신규 (명령 인코딩/디코딩·MAX_COMMAND_BYTES)
- `appliance_sim/__main__.py` — 신규 (실행 진입점)
- `appliance_sim/transports/__init__.py` — 신규 (전송 경계 디렉터리)
- `appliance_sim/transports/loopback.py` — 신규 (참조 전송, BLE 아님)
- `appliance_sim/transports/ble_bless.py` — 신규 (BLE 바인딩, 동작 미확인)
- `tests/test_appliance_sim.py` — 신규 (43 tests)
- `docs/implementation-artifacts/2-1-appliance-simulator-ble-peripheral.md` — 본 파일

### Change Log

- 2026-07-22: Story 2.1 구현 완료 — 가전 시뮬레이터(상태 기계·와이어 계약·
  루프백/BLE 전송 경계·정직 표기·실행 진입점). 219 passed (신규 43, 회귀 0).
  BLE 실동작은 bless 미설치로 **미확인 유지**(정직 기록).
  Status: ready-for-dev → review.

### 파티 리뷰 (2026-07-22) — Mary·Winston·Amelia·John·Sally·Paige

라운드테이블 결과 4건 도출, 3건 즉시 반영 + 1건 2.2 이월. **225 passed**(신규 6).

- [x] **P1 (Paige) BLE UUID가 UUID가 아니었다** — `a1b2c3d4-...-thinqonme001`은
      16진수가 아니고 마지막 그룹도 12자리가 아니다. `uuid.UUID()` 파싱 실패.
      BLE 실행 불가라 한 번도 검증되지 않았고 테스트는 "하드웨어 의존"으로 통째
      면제돼 있었다 — **형식 검증은 하드웨어 없이도 된다. 면제 범위가 너무 넓었다.**
      → `uuid5(NAMESPACE_DNS, …)` 결정적 생성으로 교체 + 형식·상호구별 테스트.
- [x] **P2 (Mary) 범위값 3개가 출처 없이 판정하고 있었다** — 주석에 "근거 없음"을
      적는 것으로는 부족하다. 값이 판정을 하는데 출처가 값과 함께 다니지 않으면
      그건 미결정이 아니라 **결정된 척**이다. 1.3에서 `CapabilityValue(value,
      source)`로 어댑터 한계값에 출처를 강제해놓고 여기만 안 붙인 것은
      **같은 병을 한쪽만 고친 것**(Winston). → `RangeSpec(lo, hi, source)` 도입.
      추가로 `target_temp` 하한 16이 실제 LG 에어컨 하한(18)보다 낮아 **실가전이
      거부할 명령을 승인**할 수 있었다 → 0~40으로 넓혀 판정 책임을 실가전에 넘김
      (시뮬레이터가 실가전보다 엄격하면 프로필이 이식 불가가 된다).
- [x] **P3 (Sally) 배너가 12줄 중 9줄 — 표기가 작동하지 않았다** — 반복 문구는
      시각적 노이즈가 되어 필터링된다. 아홉 번 붙이면 아홉 번 안 읽힌다.
      테스트는 `count >= 6`으로 통과했지만 그건 문자열 개수를 잰 것이지 표기가
      읽히는지를 잰 것이 아니다 — **1.1 '단어 언급 단언 금지'의 표기 영역 재발.**
      → 규약 "경계마다 한 번, 스트림 안엔 생략" 수립, 화면 4경계로 축소,
      자료구조·BLE 광고명은 유지(맥락이 다르다), 회귀 테스트 재작성,
      `docs/CARRIER_INTERFACE.md §4-b`에 규약 문서화(Paige).
- [ ] **P4 (Amelia) applied=True인데 이벤트가 없는 경로 — 2.2로 이월**
      같은 값 재설정 시 `(True, [])`를 반환하는데 이벤트가 없어 "성공"과
      "무변화"가 구별되지 않는다. 2.4 야간 모드 데모에서 "전환됨"을 판정할 근거가
      사라진다. **Winston 판단으로 이월**: 반환값을 소비하는 코드가 2.2에 있는데
      아직 안 짰다 — 지금 3값(applied/unchanged/rejected)을 정하면 소비자가 뭘
      필요로 하는지 모른 채 인터페이스를 못 박는 것이다(1.3 함정 7 "투기적
      프레임워크 금지"). Mary의 반문("그럼 범위값도 미루자는 거냐")에 대한 구분:
      **범위값은 이미 코드에 박혀 판정 중이라 '결정된 척'이고, 3값 반환은 아직
      아무도 안 쓴다. 박힌 거짓말이 안 박힌 미완성보다 급하다.**

### bless 설치 실측 (사용자 지시로 실행 — 결과: 설치 불가)

리뷰 중 실제 설치를 시도했고, **이 환경에서 bless는 설치 자체가 불가능**함을
확인했다(Python 3.12 + Windows):

1. `pip install bless` → **0.2.6** 설치됨. import 시
   `ModuleNotFoundError: No module named 'bleak_winrt'`.
   0.2.6의 WinRT 백엔드는 구 bleak(<0.22)의 `bleak_winrt` 모듈을 요구하는데
   최신 bleak(3.x)는 그것을 제공하지 않는다(`winrt-*` 네임스페이스로 이전).
2. `pip install bless==0.3.0` → **ResolutionImpossible**. 0.3.0 메타데이터가
   자기모순이다:
   `bleak>=1.1.1`(→ winrt-runtime ≥3.x) 와
   `winrt-Windows.*==2.0.0b1`(→ winrt-runtime ==2.0.0-beta.1)을 **동시에** 요구.
3. **결론: 상류 패키징 문제이며 이 저장소에서 해결할 수 없다.**
   설치 시도로 들어온 패키지 9개는 전부 제거해 환경을 원복했다.

**코드 반영**: v1의 오류 문구 "bless 미설치이거나 어댑터 미지원"이 실측으로
**거짓**임이 드러났다(설치는 됐는데 backend가 깨진 상태였다). 사유를
`NOTICE_NOT_INSTALLED` / `NOTICE_BROKEN_DEPS` / `NOTICE_NOT_IMPLEMENTED`로
구분해 보고하도록 교체 — 두 사유는 사용자가 취할 행동이 완전히 다르다.
회귀 테스트로 고정(`test_ble_distinguishes_missing_from_broken_deps`).

**후속 재평가 대상**: 실기기 데모에서는 **가민 워치가 중앙(Central) 역할**이므로
Python 주변장치 경로 자체가 필요 없을 가능성이 크다. Epic 2 후속에서 이 모듈의
존치 여부를 다시 판단할 것.

### 사람 결정 대기 (2건 → 1건 해소, 1건 잔존)

1. ~~**bless 설치 여부**~~ — **해소.** 사용자 지시로 설치 시도했고 상류 패키징
   문제로 **설치 불가**임을 실측 확인(위 절). 환경 원복 완료.
2. **`target_temp` 실제 범위** — 잔존. 리뷰에서 0~40으로 넓혀 판정 책임을
   실가전에 넘겼고 `source="미확인(설계 판단 …)"`으로 정직 표기했으나,
   **실가전 스펙 확인은 여전히 미완**이다. 설문 문6(보유 가전) 결과나 LG 공개
   스펙으로 교체 대상. `humidity`·`timer_min`은 물리 정의라 근거 확정됨.
