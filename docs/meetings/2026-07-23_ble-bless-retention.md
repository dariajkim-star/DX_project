# ble_bless.py 존치 결정 브리프 (2026-07-23)

핸드오프 3번 안건. Epic 2 완료로 근거가 다 모였다. **삭제 vs 미구현 표기 유지** —
사람 판단 대상(daria). 이 문서는 판단 근거를 모으고 권고를 제시한다. 확정 시
[DECISIONS.md](../DECISIONS.md) 인덱스에 한 줄 등록한다.

## 안건
`appliance_sim/transports/ble_bless.py` (BLE GATT 주변장치 바인딩, Story 2.1).
이 환경에서 `bless`는 설치 자체가 불가능(상류 패키징 자기모순, 2026-07-22 실측)하고,
실기기 데모에선 **가민 워치가 Central** 역할이라 Python 주변장치 경로가 필요 없을
가능성이 크다. 그렇다면 파일을 지울 것인가?

## 사실 관계 (실측·코드 확인)
- **죽은 코드가 아니다.** 세 곳이 물려 있다:
  - `appliance_sim/__main__.py:16,98` — `--transport ble` 경로(`_run_ble`)가 import·사용
  - 정직 계약 테스트 **4개** (`tests/test_appliance_sim.py`):
    `test_ble_uuids_are_actually_valid_uuids`(Paige 회귀 고정),
    `test_ble_module_is_exempt_and_exists`,
    `test_ble_module_reports_error_when_bless_missing`,
    `test_ble_distinguishes_missing_from_broken_deps`(거짓 "미설치" 문구 회귀 고정)
  - `transports/__init__.py`·`appliance_sim/__init__.py` 경계 문서가 이 파일을 경계 정의로 명시
- **AST 경계가 이 파일에 의존한다.** `test_ble_module_is_exempt_and_exists`는 파일이
  존재하고 **동시에** stdlib-only 규칙을 위반함(`_transport_violations(...) != set()`)을
  단언한다. 즉 `core·wire·loopback`이 "깨끗하다"는 증명은 **ble_bless가 격리소라는 사실에
  대비되어** 성립한다. 파일을 지우면 경계의 반례(정의)가 사라진다.
- **테스트는 하드웨어 없이 도는 정직 계약이다.** UUID 형식 검증, "미설치 vs 설치했는데
  깨짐" 구분, 예외 대신 오류 보고 — 전부 하드웨어 없이 고정 가능한 계약이고, 실제 리뷰
  발견(v1 UUID 오류, 거짓 오류 문구)을 회귀 고정한다.

## 권고: **미구현 표기 유지 (삭제하지 않음)** — 재평가 시점 = Epic 3 / 가민 실기기 연동

### 유지 근거
1. **정직 표기 서명의 최강 구현체.** ble_bless는 "동작한 척 금지 — NFR6"를 가장 강하게
   체현한다. `python -m appliance_sim --transport ble`는 **안 되는 이유를 출력하고
   비정상 종료**한다(조용한 루프백 대체 금지). 이건 부끄러운 사족이 아니라 **엔지니어링
   정직성의 실물 증거** — AX 심사에서 통하는 자산이다.
2. **경계 증명이 무너진다.** AST 테스트가 ble_bless의 존재를 반례로 써서 clean 경계를
   정의한다. 삭제하면 이 정의를 다시 짜야 한다.
3. **회귀 고정 4건 소실.** 하드웨어 없이 검증되는 정직 계약 테스트가 사라진다.
4. **"필요 없을 가능성"은 "지금 삭제"가 아니다.** 가민 Central 구조는 **재평가 대상**
   (파일 주석 line 29)이지 확정이 아니다. `reassemble` 역류가 풀리는 곳과 **같은 지점
   (Epic 3, 저장 매체·수신 구조 재결정)**에서 이 경로의 운명도 드러난다. 그 전에 지우면 추측.
5. **삭제 비용.** `__main__.py`(`--transport ble`·`_run_ble` 제거)·경계 문서 2개·테스트
   4개를 건드려야 한다. 자산을 없애는 비자명한 표면 변경.

### 삭제 근거 (기각하되 기록)
- 이 환경에서 server 경로는 영영 못 돈다(상류 패키징) → 그러나 **못 도는 이유를 정직하게
  보고하는 것 자체가 데모 자산**이라 오히려 유지 논거가 된다.
- 가민 Central이면 주변장치 불필요 → 재평가 대상일 뿐 확정 아님(위 4).
- 안 도는 코드 유지의 유지보수 신호 → 미구현 표기·테스트로 이미 정직하게 관리됨.

### ⚪와의 관계 (오해 방지)
[ARCHITECTURE_FLOW.md](../ARCHITECTURE_FLOW.md)의 ⚪(뺄 곳)는 **발표 서사 비중을
줄이라**는 뜻이지 **코드 삭제**가 아니다. 발표에선 ble_bless에 시간을 쓰지 말고
🔴 P-2로 힘을 옮긴다 — 파일은 미구현 표기로 존치.

## 결정
> **대기 — daria 비준 필요.** 권고는 "미구현 표기 유지, Epic 3에서 재평가".
> 비준되면 이 절과 DECISIONS.md 인덱스를 확정으로 갱신한다.
