# 홈 프로필 스키마 명세 (v1.0.0)

구현: [`home_profile/schema.py`](../home_profile/schema.py) · 회귀 테스트: [`tests/test_home_profile_schema.py`](../tests/test_home_profile_schema.py)
근거: [epics.md #Story 1.1](planning-artifacts/epics.md) · 작성 2026-07-22

> **이것이 무엇인가.** "집이 나를 따라온다"의 *집* 에 해당하는 자료구조다.
> 기기 등록·설정·루틴을 클라우드 계정이 아니라 사용자의 온바디 디바이스에
> 귀속시키기 위한 표현이며, 서버가 원본을 갖지 않는다는 주장의 근거이기도 하다.

---

## 1. 최상위 구조

```json
{
  "schema_version": "1.0.0",
  "devices": [
    {"device_ref": "d1", "device_type": "air_conditioner",
     "capabilities": ["power", "target_temp"]}
  ],
  "settings": {"d1": {"target_temp": 26}},
  "routines": [
    {"trigger": {"type": "time", "params": {"at": "23:00"}},
     "actions": [{"device_ref": "d1", "setting_key": "target_temp", "value": 26}]}
  ],
  "reserved_wellness": {}
}
```

| 필드 | 필수 | 타입 | 설명 |
|---|---|---|---|
| `schema_version` | ✅ | str (semver) | 지원 목록에 없으면 **거부**. 조용한 통과 없음 |
| `devices` | ✅ | array | 기기 목록. `device_ref` 프로필 내 고유 |
| `settings` | ✅ | object | `{device_ref: {setting_key: value}}` |
| `routines` | ✅ | array | `trigger`(type 필수) + `actions`(1개 이상) |
| `reserved_wellness` | ✅ | object | **예약 전용. 항상 빈 객체.** v2에서 필수로 승격 — 생략은 위반 (§4) |

`devices[]` 원소: `device_ref`(필수), `device_type`(필수), `capabilities`(배열).
`routines[].actions[]` 원소: `device_ref`, `setting_key`, `value` 전부 필수이며
`device_ref`는 반드시 `devices[]`에 등록된 값이어야 한다 — 미등록 기기를 가리키는
루틴은 조용히 통과하지 않고 검증에서 거부된다.

## 2. 식별자 차단 (FR7) — 구조적 방어선

> **이력**: v1 구현은 "존재할 수 없다"·"기계 증명"을 주장했으나 2026-07-22
> Code Review Crew가 실행으로 반증했다(값 PII·한국어 키·호모글리프·`ssid/lat/lon`
> 전부 통과). 같은 날 v2로 재작성해 아래 방어선을 구축하고, 리뷰의 우회 사례
> **14건 전수 재실행으로 차단을 확인**했다. 경위는 스토리 파일의 리뷰 평결 참조.

v2의 접근: 식별자 차단은 단어 목록이 아니라 **구조로** 한다 —
사람이 자유 문자열을 쓸 자리 자체를 없앤다.

| 방어선 | 내용 | 막는 것 |
|---|---|---|
| **키 화이트리스트 (전 레벨)** | `devices[]`·`routines[]`·`trigger`·`actions[]`의 키는 스키마 선언 키만 허용 | `ssid`·`lat`·`lon` 등 임의 키 주입 (v1은 최상위만 막았다) |
| **토큰 형식 강제** | `device_ref`: `^[a-z0-9][a-z0-9_-]{0,31}$` — 생성된 불투명 토큰만 | `"hong@gmail.com"`·`"엄마 방 에어컨"` 같은 자유 문자열 ref |
| **키 이름 형식 강제** | `setting_key`·`device_type`·capability·trigger type: ASCII 소문자 토큰 | 한국어 키(`이름`)·호모글리프 키(`аccount_id`) — 형식 단계에서 전멸 |
| **식별자성 키 조각 (영+한)** | `name`·`account`·… + `이름`·`전화`·`주소`·`주민`·… (NFKC 정규화 후) | 형식은 통과하는 `user_id` 류 |
| **가구 식별·위치 키** | `ssid`·`mac`·`serial`·`imei`·`lat`·`lon`·`geo`·`gps` 정확 일치 거부 | 와이파이 측위 = 집 주소 |
| **값 PII 스캔** | 모든 문자열 값에 이메일·전화(010-…)·주민번호 정규식 + 한국어 식별 문구 | v1의 최대 구멍 — 값에 담긴 PII |
| **스캔 견고성** | 깊이 상한 24 + 순환 감지 — 초과·순환은 **거부**(fail-closed) | 10KB 깊이 폭탄으로 스캔을 죽이는 공격 |

**보증 수준의 정직한 서술**: 위는 **방어선의 총합이지 수학적 증명이 아니다.**
정규식과 조각 목록은 완전할 수 없다. 다만 v1과 달리 ① 자유 문자열이 허용되는
표면 자체가 값 몇 곳으로 좁혀졌고 ② 그 값들은 전부 스캔되며 ③ 검사를 우회하는
크래시 경로가 없다(§아래). 새 필드가 이 검사에 걸리면 **우회할 이름을 찾는 것이
아니라 그 필드가 정말 필요한지 되묻는 것**이 규약이다.

**크래시 = 우회 였던 문제**: v1은 `validate_profile()`이 unhashable ref·깊은
중첩에서 예외를 던졌고, 그 예외가 마지막 줄의 식별자 스캔을 선점했다.
v2는 ① 식별자 스캔을 **먼저** 실행하고 ② 모든 구조 검사를 total function으로
만들고 ③ 남는 내부 오류는 통과가 아니라 거부로 처리한다(fail-closed).
**`validate_profile()`은 어떤 입력에도 예외를 던지지 않는다** — 이 계약은
테스트로 고정되어 있다(unhashable·순환·깊이 1200 전부 위반 목록으로 반환).

## 3. 버전과 마이그레이션

- `SCHEMA_VERSION = "1.0.0"`, `SUPPORTED_VERSIONS = {"1.0.0"}`
- `is_supported(v)` — 문자열이면서 지원 목록에 있을 때만 `True`. (v2: v1의
  semver 파싱 3줄은 어떤 입력에서도 답을 바꾸지 못하는 죽은 코드라 삭제 — 리뷰 Yui)
- **마이그레이션은 미구현·미결정** (v2에서 v1의 빈 `MIGRATIONS` 레지스트리 삭제).
  현재 동작: 지원 목록 밖 버전은 전부 거부. 구버전 프로필을 받아서 변환할지는
  Story 1.2 이후 설계 결정 — 결정 전까지 "마이그레이션 경로가 열려 있다"고
  주장하지 않는다(리뷰 F5 반영)

## 4. `reserved_wellness` — 예약이자 금지 (NFR5)

수면·활동 데이터로의 확장은 [CX_DEFINITION.md §1](CX_DEFINITION.md)의 v2 비전
레이어에 있으나, **체성분·진단은 의료 규제 영역**이라 스키마 예약 필드까지만
허용된다.

따라서 이 필드는 "나중에 쓰려고 비워둔 칸"이 아니라 **"쓰지 않겠다는 선언"** 이다:

- 값을 담으면 `validate_profile()`이 **거부**한다 (빈 객체만 허용)
- 이 모듈에는 웰니스를 해석·판단·평가하는 코드가 **존재하지 않는다**
  (v1의 '함수 이름 5개 hasattr' 테스트는 실패 불가능한 연극이라 삭제 — 리뷰 F4.
  실질 보증은 아래 옆문 봉쇄와 코드 리뷰다)
- "일단 파싱만 해두자"는 AC 위반이다 — 파싱이 곧 해석의 시작점이기 때문

> **v2 보강(리뷰 반영)**: v1은 앞문만 잠갔다 — `settings`로 웰니스 데이터가
> 자유 투입됐고(`sleep_score:82` → 통과), 키를 빼면 검사가 스킵됐다. v2는
> ① `reserved_wellness`를 **필수 키**로 승격(생략 = 위반) ② `settings`의
> 웰니스성 키 조각(`sleep`·`hrv`·`heart`·`blood`·`bp_`·`spo2` 등)을 거부한다.
> 옆문 봉쇄도 조각 목록 기반 방어선이며 완전하지 않다 — 한계는 §2와 동일.

## 5. 전송 제약이 구조를 결정했다

가민 실기기 제약 (2026-07-22 조사):

| 제약 | 값 | 출처 |
|---|---|---|
| Connect IQ `Application.Storage` 총량 | 약 128KB | [Garmin 개발자 포럼](https://forums.garmin.com/developer/connect-iq/f/discussion/2661/storage-available) |
| Storage 키 1개당 | 약 8KB | 〃 |
| BLE 특성 read/write | 약 **20바이트**, long write 미지원 | [Garmin 개발자 포럼](https://forums.garmin.com/developer/connect-iq/f/discussion/196823/bluetooth-low-energy-mtu-size-for-characteristics/1443557) |

프로필 전체를 한 키·한 write로 전송하는 것은 **물리적으로 불가능**하다.
그래서 `devices[]`·`routines[]`의 각 원소가 독립적으로 직렬화·전송 가능하도록
평평하게 유지했고, 값을 스칼라로 제한해 직렬화 불가 프로필이 검증을 통과하는
경로를 막았다(`test_unserializable_values_rejected` 등).

**청크 프로토콜 자체는 이 문서의 범위가 아니다** — Story 1.2(크기 예산 측정)와
Epic 2(BLE 전송)가 이 구조를 상속해 구현한다.

## 6. 설계 판단 (근거 문서 없음 — 정직 표기)

epics.md의 AC에 명시되지 않았으나 구현상 결정한 사항. **요구사항이 아니라
설계 판단**이며, 후속 스토리에서 뒤집힐 수 있다.

| 판단 | 내용 | 이유 |
|---|---|---|
| `profile_id` **미채택** | 프로필 식별자를 두지 않음 | AC에 없고, 잘못 만들면 계정 식별자로 퇴화한다. 필요해지면 그때 비식별 랜덤값으로 도입 |
| `settings`를 `device_ref` 키 맵으로 | 기기별 중첩 구조 | 기기 단위 청크 전송과 이사 매핑(3.2)의 부분 이전에 유리 |
| `device_ref`는 생성된 불투명 토큰 (v2) | `^[a-z0-9][a-z0-9_-]{0,31}$`, 시리얼·MAC 아님 | v1의 '임의 문자열'이 곧 PII 통로였다(리뷰 F1). 표시용 이름은 프로필 밖의 문제 |
| `MIGRATIONS` 삭제 (v2) | 마이그레이션 레지스트리 미도입 | 아무도 읽지 않는 장식이었다(리뷰 F5). 구버전 거부/변환은 미결정 |
| 값은 스칼라만 (v2) | str/int/bool/유한 float | 직렬화 불가 값이 전송 시점에 터지던 결함(리뷰 F6) 봉쇄 |
| 미등록 기기 참조를 **거부** | 검증 실패로 처리 | 3.2의 '손실 없는 보류'는 이사 시나리오의 개념이고, 프로필 자체의 정합성과는 다른 층위 |
| 표준 라이브러리만 사용 | pydantic·jsonschema 미도입 | 이 표현은 워치급 환경(Monkey C)으로 이식된다. Python 전용 라이브러리 종속은 캐리어 중립(NFR3)을 코드 레벨에서 깬다 |

## 7. 사용 예

```python
from home_profile import new_profile, validate_profile

p = new_profile()
p["devices"].append({"device_ref": "d1", "device_type": "light",
                     "capabilities": ["power"]})
p["settings"]["d1"] = {"power": "off"}

errs = validate_profile(p)       # 빈 리스트면 통과
if errs:
    for e in errs:
        print("위반:", e)
```

`validate_profile()`은 예외를 던지지 않고 **위반 목록**을 반환한다.
여러 위반을 한 번에 보여줘야 사람이 판단할 수 있기 때문이다.
