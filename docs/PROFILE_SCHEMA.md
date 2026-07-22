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
| `reserved_wellness` | — | object | **예약 전용. 항상 빈 객체** (§4 참조) |

`devices[]` 원소: `device_ref`(필수), `device_type`(필수), `capabilities`(배열).
`routines[].actions[]` 원소: `device_ref`, `setting_key`, `value` 전부 필수이며
`device_ref`는 반드시 `devices[]`에 등록된 값이어야 한다 — 미등록 기기를 가리키는
루틴은 조용히 통과하지 않고 검증에서 거부된다.

## 2. 식별자 차단 — 현재 상태 (⚠️ FR7 미충족)

> **2026-07-22 코드 리뷰 결과 이 절의 기존 서술을 철회한다.**
> 이전 판은 "이 필드들은 존재할 수 없다", "기계 증명"이라고 적었으나 **사실이 아니다.**
> 아래는 실행으로 확인된 실제 능력이다. 이 프로젝트의 서명 —
> *"불확실을 확실로 세탁하지 않는다"* — 에 따라 정정한다.

**현재 구현이 실제로 하는 일**: `assert_no_identifiers()`는 **키 이름**을 소문자화해
아래 12개 **영어 조각**과 부분 일치 검사한다. `validate_profile()`이 이를 내부 호출한다.

`name` `account` `email` `phone` `user_id` `userid` `birth` `address` `contact` `ssn` `gender` `owner`

**실행으로 확인된 통과 사례 (전부 `validate_profile() == []`)**

| 우회 | 예시 |
|---|---|
| **값에 담기** (검사는 키만 본다) | `device_ref = "hong.gildong@gmail.com"`, `device_type = "서울 강남구 123-4 홍길동 침실"` |
| **한국어 키** | `settings["d1"]["이름"] = "홍길동"`, `["전화번호"] = "010-…"` |
| **호모글리프** | `"аccount_id"` (키릴 а, U+0430) — 정규화 없음 |
| **의미상 동의어** | `resident` `alias` `who` `label` `tag` `ssid` `mac` `serial` `lat` `lon` `household` |
| **중첩 미지 키** | 미지 키 거부는 **최상위에서만** 작동. `devices[]`·`settings[ref]`·`routines[]` 내부는 임의 키 자유 |

`ssid="KimFamily_5G"` + `lat`/`lon`은 이 검사가 실제로 잡는 `email` 문자열보다
**강한 가구 식별자**다(와이파이 측위 = 집 주소).

**따라서 현재 보증 수준은 이렇게만 말할 수 있다**:

> 최상위 키는 화이트리스트로 제한된다. 중첩 키 중 **철자에 위 12개 영어 조각이 포함된
> 것**은 거부된다. 그 외에는 아무것도 보증하지 않는다 — **값은 전혀 검사하지 않는다.**

이것은 린트 규칙이지 증명이 아니다. **FR7("식별자 필드가 존재하지 않음")은
현재 미충족**이며, Story 1.1의 AC4도 미충족으로 재판정되었다.

**후속 작업 필요** (Story 1.2 이전에 처리):
값 검사(이메일·전화·주민번호 정규식), 한국어 금지어, 유니코드 NFKC 정규화,
중첩 레벨 미지 키 거부, `device_ref`를 자유 문자열이 아닌 **생성된 불투명 토큰**으로 제약.

## 3. 버전과 마이그레이션

- `SCHEMA_VERSION = "1.0.0"`, `SUPPORTED_VERSIONS = {"1.0.0"}`
- `is_supported(v)` — semver 3자리 숫자 형식이면서 지원 목록에 있을 때만 `True`.
  형식 위반(`"1.0"`, `"v1.0.0"`, `""`)도 전부 `False`
- `MIGRATIONS: dict` — `{"출발버전": callable(profile) -> profile}`.
  함수는 부작용 없이 다음 버전 dict를 반환한다. 1.0.0은 최초 버전이라 **등록분 없음**
  (빈 dict가 정상 상태이며, 테스트가 이를 고정한다)

## 4. `reserved_wellness` — 예약이자 금지 (NFR5) ⚠️ 현재 우회 가능

수면·활동 데이터로의 확장은 [CX_DEFINITION.md §1](CX_DEFINITION.md)의 v2 비전
레이어에 있으나, **체성분·진단은 의료 규제 영역**이라 스키마 예약 필드까지만
허용된다.

따라서 이 필드는 "나중에 쓰려고 비워둔 칸"이 아니라 **"쓰지 않겠다는 선언"** 이다:

- 값을 담으면 `validate_profile()`이 **거부**한다 (빈 객체만 허용)
- 이 모듈에는 웰니스를 해석·판단·평가하는 함수가 **존재하지 않는다**.
  `wellness_score`·`interpret_wellness`·`diagnose`·`assess_health`·
  `evaluate_wellness` 부재를 테스트가 고정한다
- "일단 파싱만 해두자"는 AC 위반이다 — 파싱이 곧 해석의 시작점이기 때문

> ⚠️ **2026-07-22 리뷰 정정 — 이 봉쇄는 앞문만 잠근다.**
> `settings`는 임의 키·값을 받으므로 웰니스 데이터가 옆문으로 자유롭게 들어온다.
> 실행 확인: `settings["d1"] = {"sleep_score":82, "hrv":41, "body_fat_pct":18.2,
> "bp_systolic":139}` → `validate_profile() == []`.
> 또한 `reserved_wellness`는 `REQUIRED_TOP_LEVEL_KEYS`에 없어 **키를 아예 빼면
> 검사 자체가 건너뛰어진다**. **NFR5 노출은 이 스토리로 줄어들지 않았다.**

## 5. 전송 제약이 구조를 결정했다

가민 실기기 제약 (2026-07-22 조사):

| 제약 | 값 | 출처 |
|---|---|---|
| Connect IQ `Application.Storage` 총량 | 약 128KB | [Garmin 개발자 포럼](https://forums.garmin.com/developer/connect-iq/f/discussion/2661/storage-available) |
| Storage 키 1개당 | 약 8KB | 〃 |
| BLE 특성 read/write | 약 **20바이트**, long write 미지원 | [Garmin 개발자 포럼](https://forums.garmin.com/developer/connect-iq/f/discussion/196823/bluetooth-low-energy-mtu-size-for-characteristics/1443557) |

프로필 전체를 한 키·한 write로 전송하는 것은 **물리적으로 불가능**하다.
그래서 `devices[]`·`routines[]`의 각 원소가 독립적으로 직렬화·전송 가능하도록
평평하게 유지했고, 이를 테스트로 고정했다
(`test_profile_is_chunkable_by_top_level_lists`).

**청크 프로토콜 자체는 이 문서의 범위가 아니다** — Story 1.2(크기 예산 측정)와
Epic 2(BLE 전송)가 이 구조를 상속해 구현한다.

## 6. 설계 판단 (근거 문서 없음 — 정직 표기)

epics.md의 AC에 명시되지 않았으나 구현상 결정한 사항. **요구사항이 아니라
설계 판단**이며, 후속 스토리에서 뒤집힐 수 있다.

| 판단 | 내용 | 이유 |
|---|---|---|
| `profile_id` **미채택** | 프로필 식별자를 두지 않음 | AC에 없고, 잘못 만들면 계정 식별자로 퇴화한다. 필요해지면 그때 비식별 랜덤값으로 도입 |
| `settings`를 `device_ref` 키 맵으로 | 기기별 중첩 구조 | 기기 단위 청크 전송과 이사 매핑(3.2)의 부분 이전에 유리 |
| `device_ref`는 로컬 임의 문자열 | 시리얼·MAC 아님 | 하드웨어 식별자는 추적 가능한 준식별자다 |
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
