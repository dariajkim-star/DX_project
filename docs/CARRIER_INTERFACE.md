# 캐리어 인터페이스 — 온바디 저장·전송 추상화 (Story 1.3)

작성 2026-07-22 · 근거: NFR3(캐리어 중립), NFR6(근거 무결성), AC1~AC4
구현: `home_profile/carrier.py`(코어) · `home_profile/carriers/`(벤더 어댑터)
감시: `tests/test_carrier_neutrality.py`(AST 기반 경계 위반 탐지 + 어댑터 계약 스위트)

캐리어 중립은 성능 요구가 아니라 **전략 제약**이다 — 처방 정의가 "애플·가민·샤오미
대응 가능한 추상화. 삼성 갤럭시워치 폐쇄 진영에 대한 개방 생태계 전략"이다.
벤더 API가 코어에 새면 발표의 주장 한 축이 코드 레벨에서 무너진다.

---

## 1. 캐리어 현황표

발표 자료에 이 표를 그대로 쓸 수 있다 — 상태는 정직하게.

| 캐리어 | 상태 | 실기기 | 비고 |
|---|---|---|---|
| 참조(`MemoryCarrier`) | ✅ 동작 | ❌ **실기기 아님** | 호스트 파이썬 메모리. Epic 2 호스트 측 시연용 |
| 가민(`GarminConnectIQCarrier`) | ⛔ **미구현** | 팀 보유(별개 사실) | 경계 설계·용량 신고만. Monkey C 런타임 필요 — 이 저장소엔 구현체가 없다 |
| 애플 | ⛔ 미구현 | — | 코드 없음(빈 스텁도 없음 — §4 절차만 존재) |
| 샤오미 | ⛔ 미구현 | — | 〃 |

**구조는 중립이고 실증은 가민 하나로만 가능하다** — 이 비대칭을 숨기지 않는 것이
AC4다. "가민에서 됨"으로 읽히는 문장을 어디에도 쓰지 말 것.

## 2. 메서드 계약표

인터페이스는 **불투명 바이트 레코드 맵**을 다룬다. 단일 키/분할 저장, 평문/압축
어느 쪽도 강요하지 않는다 — 1.2의 미결정(A 섹션분할 vs C zlib)을 인터페이스에
못 박지 않기 위해서다. 어댑터는 페이로드를 파싱하지 않는다.

| 메서드 | 시그니처 | 반환 규약 |
|---|---|---|
| `put_records` | `(records: dict[str, bytes]) -> list[str]` | 빈 리스트 = 성공. **원자적** — 한 레코드라도 거부되면 배치 전체 미저장 |
| `get_records` | `(names: list[str]) -> (dict[str, bytes] \| None, list[str])` | 하나라도 없으면 `(None, errors)` — 반쪽 결과 금지 |
| `erase` | `(names: list[str]) -> list[str]` | 없는 이름은 오류 — '지웠다고 생각했는데 남아 있음' 방지 |
| `capabilities` | `() -> CarrierCapabilities` | 항상 성공. 신고한 한계는 실제로 강제되어야 한다 |

세부 규약 (리뷰 P6 — 미정의였던 지점의 명문화):

- **빈 입력**: `put_records({})`는 **오류**("저장할 것이 없다" — 실수 가능성이
  높은 호출), `get_records([])`·`erase([])`는 **성공**(빈 결과/no-op — 집합
  연산의 자연스러운 항등원). 비대칭은 의도다. UNIMPLEMENTED 어댑터는 빈 입력에도
  "미구현" 오류를 낸다(모든 연산 실패가 우선 규약).
- **페이로드 타입**: `bytes`·`bytearray` 수용(내부에 `bytes`로 **복사** 저장 —
  호출자 변조 무영향, 반환은 항상 `bytes`). `memoryview` 등 기타 버퍼는 거부.
- **names 타입**: `list[str]`가 권장 표면이나 문자열 이터러블이면 수용
  (str·bytes 자체는 거부). 중복 이름은 get/erase에서 순서 유지로 중복 제거된다.
- **이름 표시**: 오류 문구의 레코드 이름은 32자까지만 원문 표기, 초과 시
  `<str len=N>` — 이름 채널로 페이로드를 밀수하는 우회 차단(리뷰 P2).

**전 메서드 예외 금지(fail-closed).** 어떤 입력(None·비bytes·거대 레코드·빈
이름·비이터러블)에도 예외를 던지지 않는다 — 크래시는 곧 검사 우회다(1.1 리뷰 F3).
내부 오류는 `except Exception`으로 받아 오류 목록으로 되돌린다.

**오류 문구에 페이로드 값 금지.** 레코드 이름·바이트 수·한계값까지만.
`"레코드 'devices' 4,511B > 한계 4,096B"` ← 좋음 / `"거부된 페이로드: …"` ← 금지.
페이로드가 로그로 새면 온바디 프라이버시 주장(FR7)이 자기 코드에서 반증된다.

## 3. Capabilities — 자기 한계의 정직한 신고

```python
CapabilityValue(value: int, source: str)      # 값 + 출처 라벨
CarrierCapabilities(
    max_record_bytes: CapabilityValue,        # 저장 키 1개당 상한
    max_total_bytes: CapabilityValue,         # 총 저장량 상한
    transfer_mtu: CapabilityValue,            # 전송 단위 상한
    supports_decompression: bool | None,      # None = 미확인
)
```

출처 라벨 규칙(NFR6):
- `source`는 값의 계보를 말한다: `측정` / `벤더문서` / `garmin_forum_2026-07-22` /
  `설계값` / `미확인`. **포럼발 수치에 '측정'·'벤더문서'를 붙이는 순간 거짓말이다.**
- 모르는 boolean은 `None`이다. `False`로 적으면 "확인해서 없더라"가 되고,
  그건 하지 않은 조사를 한 척하는 것이다(가민 zlib 해제 여부가 현재 이 상태).
- 가민 어댑터가 신고하는 값은 `storage.py`의 가민 유래 상수(`BUDGET_PER_KEY`
  4,096B·`BUDGET_STORAGE_TOTAL` 128KB·`BLE_MTU` 20B)와 일치한다. 상수의 단일
  출처는 storage.py에 유지(1.2 테스트 호환)하되, "이건 가민 값"이라는 의미
  부여는 어댑터의 일이다 — PROFILE_SCHEMA §6 참조.

## 4. 새 캐리어를 추가하려면

**코어(`schema.py`·`storage.py`·`carrier.py`)는 한 줄도 고치지 않는다.**
이것이 AC3의 정의이며, 위반하면 `test_carrier_neutrality.py`가 알려준다.

1. `home_profile/carriers/<vendor>.py` 생성 — 벤더 의존은 이 파일 안에만.
2. §2의 메서드 4개를 계약대로 구현: 예외 금지, 원자적 put, 반쪽 결과 금지,
   오류에 페이로드 금지, 신고한 한계의 실제 강제.
3. `capabilities()`에 자기 한계를 신고 — 각 값에 출처 라벨(§3). 모르면 미확인.
4. `status`·`is_device`·`label`을 정직하게: 동작하지 않으면
   `CarrierStatus.UNIMPLEMENTED`(모든 연산이 "미구현" 오류를 반환해야 한다),
   실기기가 아니면 `is_device=False`.
5. `tests/test_carrier_neutrality.py`의 공통 계약 스위트(`any_carrier` 픽스처)에
   어댑터를 등록 — 어떤 어댑터든 같은 계약 테스트를 통과해야 한다.

레지스트리(`CARRIERS = {...}`)는 만들지 않았다 — 호출자가 읽어 분기하는 코드가
생기기 전까지는 죽은 장식이다(1.1 `MIGRATIONS` 삭제와 같은 원칙). 호출자는
어댑터를 직접 import해 주입한다.

### 애플·샤오미 추가 시 예상 매핑 (참고 — 조사 전, 전부 미확인)

| 항목 | 애플(watchOS) | 샤오미 |
|---|---|---|
| 저장 API | 미조사 | 미조사 |
| 전송 경로 | 미조사 | 미조사 |
| 한계값 | **미확인** — 조사 없이 수치를 적지 않는다 | 〃 |

## 5. 상태 모델

`CarrierStatus`는 `SUPPORTED` / `UNIMPLEMENTED` **2값뿐**이다. "부분 동작" 같은
제3의 상태를 추가하지 말 것 — 회색지대가 생기는 순간 "동작하는 것처럼 시연되지
않는다"(AC4)가 무너진다. 부분적으로만 동작하는 어댑터는 UNIMPLEMENTED다.
