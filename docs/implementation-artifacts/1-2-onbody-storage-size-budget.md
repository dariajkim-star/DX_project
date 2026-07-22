---
baseline_commit: 5f8264cd98a1e4b5f05c0780ea0e4f5e68b89ae6
---

# Story 1.2: 온바디 저장 및 크기 예산 검증

Status: changes-requested

## Story

As a **Night Keeper**(밤에 지키는 사람 — 잡 기반 페르소나, 인구통계 미확정),
I want 프로필이 내 워치에 실제로 들어가기를,
so that 폰을 잃거나 앱을 지워도 집 설정이 내 손목에 남는다.

**에픽 맥락**: Story 1.1이 "집이 무엇으로 담기는가"(스키마)를 정의했다.
이 스토리는 **"정말 손목에 들어가는가"(NFR4)를 수치로 판정**한다. 여기서 예산이
안 맞으면 "집이 나를 따라온다"는 문장 전체가 거짓이 된다 — Epic 2(BLE 전송)·
Epic 3(복원·이사)이 전부 이 결과 위에 선다.
[Source: docs/planning-artifacts/epics.md#Epic 1]

## Acceptance Criteria

**AC1 — 크기 예산 (NFR4)**
**Given** Story 1.1의 스키마와 대표 가정(기기 N대·루틴 M개) 샘플이 있을 때
**When** 프로필을 직렬화하면
**Then** 산출 크기가 워치급 저장·전송 한계 예산 안에 들어간다

**AC2 — 크기 리포트**
**And** 예산 초과 시 **어떤 필드가 원인인지 식별 가능한** 크기 리포트가 남는다

**AC3 — 왕복 무손실**
**Given** 직렬화된 프로필이 있을 때
**When** 역직렬화하면
**Then** 원본과 의미적으로 동일한 프로필이 복원된다(왕복 무손실)

**AC4 — 버전 불일치 명시 처리**
**And** 스키마 버전이 다르면 **조용히 통과하지 않고** 명시적으로 거부하거나 마이그레이션한다

[Source: docs/planning-artifacts/epics.md#Story 1.2]

## Tasks / Subtasks

- [x] **Task 1: 예산 상수 정의** (AC: 1)
  - [x] `home_profile/storage.py` 신설. 예산을 **출처 있는 상수**로 고정:
        `BUDGET_STORAGE_TOTAL = 128 * 1024` (Connect IQ Application.Storage 총량),
        `BUDGET_STORAGE_KEY = 8 * 1024` (키 1개당), `BLE_MTU = 20` (특성 write 상한).
        각 상수 옆에 출처 URL 주석 (PROFILE_SCHEMA.md §5의 조사 결과 승계)
  - [x] 안전 마진 정책 상수: 예산의 **80%를 실사용 상한**으로 (`MARGIN = 0.8`) —
        펌웨어 차이·다른 CIQ 앱과의 공유를 감안한 설계 판단(근거 문서 없음으로 표기)
- [x] **Task 2: 대표 가정 샘플 생성기** (AC: 1)
  - [x] `make_sample_profile(n_devices, n_routines)` — 스키마 v2를 **통과하는**
        합성 프로필 생성 (`validate_profile() == []`가 생성기의 계약)
  - [x] 대표 가정 3종을 상수로: `SMALL`(기기 5·루틴 3), `TYPICAL`(기기 12·루틴 8),
        `LARGE`(기기 30·루틴 20). ⚠️ **이 숫자는 실측이 아니다** — 아직 설문·실가전
        데이터가 없으므로 "설계 가정(실측 대기)"으로 코드 주석+문서에 명기.
        설문 문6(보유 가전 수)이 실측되면 그 분포로 교체한다
  - [x] 샘플의 문자열 값은 실제 길이 분포를 흉내 (setting_key 10~20자,
        capability 5~15자) — 최상 케이스로 잰 예산은 예산이 아니다
- [x] **Task 3: 직렬화·역직렬화** (AC: 3, 4)
  - [x] `serialize(profile) -> bytes` — **JSON UTF-8이 기준 표현** (표준 라이브러리,
        compact separators). 직렬화 전 `validate_profile()` 통과를 강제하고,
        위반 시 직렬화 거부 (위반 목록 반환 — 예외 금지 계약 승계)
  - [x] `deserialize(data: bytes) -> (profile | None, errors: list)` — 손상
        바이트·비UTF-8·비JSON·**어떤 입력에도 예외 금지** (1.1 리뷰 계약 승계).
        역직렬화 직후 `validate_profile()` 재실행 — 와이어에서 온 것은 신뢰하지 않는다
  - [x] 버전 처리(AC4): `schema_version`이 `SUPPORTED_VERSIONS` 밖이면
        **명시적 거부** + 사유에 버전 병기. 마이그레이션은 **미결정**(1.1 리뷰 F5
        판정 유지) — "거부"가 현재의 명시 처리이며, 조용한 통과만 금지다
  - [x] 왕복 검증(AC3): `deserialize(serialize(p)) == p` — 단 dict 키 순서는
        의미가 아니므로 등가 비교. float 값 존재 시 반올림 손실 여부 확인
- [x] **Task 4: 크기 리포트** (AC: 1, 2)
  - [x] `size_report(profile) -> dict` — 전체 바이트 + **섹션별**(devices/settings/
        routines) + **기기 1대당·루틴 1개당 평균** + 예산 대비 % + 판정
        (`within_budget: bool`, 마진 반영)
  - [x] 예산 초과 시 최대 기여 필드 상위 5개를 경로로 지목
        (예: `settings[d3]` 2,140B) — "어떤 필드가 원인인지"가 AC2의 문면이다
  - [x] BLE 관점 수치 병기: `ceil(총바이트 / BLE_MTU)` = 필요 청크 수.
        **청크 프로토콜 구현은 여전히 Epic 2 범위** — 여기서는 수만 계산한다
- [x] **Task 5: 예산 판정 실측 실행** (AC: 1)
  - [x] 대표 가정 3종 각각 직렬화 → 크기 리포트 → 8KB/키·128KB 총량 대비 판정.
        결과 표를 `docs/PROFILE_SCHEMA.md`에 새 절(§크기 실측)로 기록 —
        수치는 **이 실행에서 나온 실측값만** 적는다(추정치 창작 금지)
  - [x] LARGE가 8KB/키를 넘으면: 원인 필드를 리포트로 지목하고, 대응(키 축약·
        섹션 분할 저장·압축)을 **구현하지 말고** 선택지+수치로 문서화 —
        결정은 사람 몫 (운영 원칙: 모르는 것은 수치화하지 않는다)
- [x] **Task 6: pytest 회귀 자산** — 1.1 리뷰 교훈 전면 적용
  - [x] `tests/test_home_profile_storage.py` 신설
  - [x] **스텁 판별 원칙**: '단어 언급' 단언 금지. 정확한 값·경계 단언
        (v1 테스트는 검증 로직 0줄 스텁이 23/23 통과했다 — 같은 실수 반복 금지)
  - [x] 케이스: 왕복 등가(3종 샘플 전부) / 손상 바이트·잘린 바이트·비JSON에
        예외 없이 오류 목록 / 버전 불일치 명시 거부(사유에 버전 포함) /
        validate 미통과 프로필 직렬화 거부 / 크기 리포트 합산 정합(섹션 합 ≤ 전체,
        기여 필드 경로 실재) / 예산 판정 경계(마진 직전·직후) /
        `deserialize(serialize(p))` 후 `validate_profile() == []`

## Dev Notes

### 🚨 이 스토리의 함정 — 먼저 읽을 것

**1. 직전 스토리가 리뷰에서 뒤집혔다. 같은 구멍을 다시 파지 말 것.**
Story 1.1 v1은 Code Review Crew에서 AC 4개 중 3개 미충족 판정을 받았다
(경위: [1-1 스토리 파일](1-1-home-profile-schema.md)의 리뷰 평결). 이 스토리에
직접 적용되는 계승 계약:
- **예외 금지**: `serialize`·`deserialize`·`size_report` 전부 어떤 입력에도
  예외를 던지지 않는다. 크래시는 곧 검사 우회다(1.1 리뷰 F3 — try/except 호출자
  에서 PII 스캔이 증발했다). 내부 오류는 fail-closed 거부
- **스텁 판별 테스트**: `assert any("단어" in e ...)` 금지. 그 방식의 테스트는
  검증 로직 0줄 스텁을 23/23 통과시켰다. 정확한 값·개수·경로를 단언할 것
- **보증은 실측만**: "예산 안에 들어간다"고 문서에 쓰려면 이 실행의 실측값을
  적는다. "충분할 것" 류 추정 서술은 1.1의 "기계 증명" 재판이다
- **와이어 불신**: `deserialize`는 역직렬화 직후 `validate_profile()`을 다시
  돌린다. 직렬화 전에 통과했다는 사실은 바이트가 오는 동안 아무것도 보증하지 않는다

**2. 스키마 v2의 형식 제약이 크기를 이미 압박한다 — 그게 의도다.**
`device_ref` ≤32자 토큰, `setting_key` ≤32자 ASCII, 값은 스칼라(문자열 ≤256자).
즉 **폭주하는 필드는 구조적으로 없다**. 예산 초과가 난다면 원인은 개별 필드가
아니라 **개수**(기기·루틴·설정 수)다 — 크기 리포트가 "1대당 평균"을 내야 하는
이유다. Epic 3(이사)에서 프로필이 자라는 속도를 이 평균으로 예측하게 된다.

**3. 직렬화 포맷 결정은 이 스토리에서 "JSON 기준 실측"까지만.**
CBOR·MessagePack은 **서드파티 의존성**이다 — 이 저장소는 표준 라이브러리 원칙
(1.1: 캐리어 중립 NFR3, 워치급 Monkey C 이식성). 순서는:
① JSON compact로 실측 → ② 예산 안이면 JSON 확정(끝) → ③ 초과 시에만
대안(키 축약 테이블, struct 기반 바이너리, zlib — 전부 stdlib)을 **수치와 함께
문서화하고 구현은 보류**. 새 의존성이 필요하다는 결론이 나오면 HALT하고 물을 것.
JSON 직렬화 시 `ensure_ascii=False` + `separators=(",", ":")` — ASCII 이스케이프는
한글 값(현재 스키마상 값에 한글이 올 일은 드물지만)에서 3배 부풀린다.

**4. "대표 가정" 숫자는 실측이 아니다 — 정직 표기 필수.**
기기 5/12/30, 루틴 3/8/20은 설계 가정이다. 설문 문6(보유 가전 수)이 실측되면
교체한다고 코드 주석과 문서 양쪽에 명기할 것. 이 프로젝트에서 근거 없는 수치에
근거 있는 척 라벨을 붙이는 것이 가장 큰 죄다(페르소나 날조 기각·B 신뢰도 출처
날조 적발·1.1 "기계 증명" 반증 — 전부 같은 병의 사례).

**5. 마이그레이션을 구현하고 싶어질 것이다. 하지 말 것.**
AC4의 문면은 "명시적으로 거부**하거나** 마이그레이션한다"이다. 1.1 리뷰 F5
판정으로 마이그레이션 정책은 **미결정**이며, 현재의 올바른 구현은 "버전 명시
거부"다. 빈 레지스트리·미사용 훅을 다시 만들면 1.1 v1의 `MIGRATIONS` 재판이다.

### 스키마 v2 인터페이스 (이 스토리가 소비하는 것)

```python
from home_profile import (SCHEMA_VERSION, SUPPORTED_VERSIONS,
                          new_profile, validate_profile)
# validate_profile(p) -> list[str]  (빈 리스트 = 통과, 예외 절대 없음)
# 값은 스칼라만(str≤256/int/bool/유한 float) — 직렬화 불가 값은 이미 걸러짐
# reserved_wellness는 필수 키(항상 {})
```
`validate_profile`이 이미 직렬화 가능성(스칼라·유한 float)을 보증하므로,
`serialize`에서 `json.dumps`가 실패하는 경로는 "검증을 안 거친 입력"뿐이다 —
그래서 직렬화 전 검증 강제가 계약이다.

### 파일 배치·재사용

- 신규: `home_profile/storage.py`, `tests/test_home_profile_storage.py`.
  `home_profile/schema.py`는 **수정하지 않는 것이 기본** — 스키마 변경이 필요해
  보이면 그것은 이 스토리의 범위 초과 신호다
- `__init__.py`에 `serialize`·`deserialize`·`size_report` 추가 시 `__all__`도
  갱신 — 패키지 import 테스트(`test_package_imports_and_all_is_consistent`)가
  이를 감시한다 (1.1 리뷰 반영으로 신설된 테스트)
- 테스트 픽스처: `tests/test_home_profile_schema.py`의 `_make_profile()` 패턴
  승계. 다만 storage 테스트는 **패키지 import 방식**(`import home_profile`)을
  쓸 것 — spec_from_file_location 방식은 상대 import(`from .schema import`)가
  있는 모듈에서 깨진다
- 예산 수치 출처: [PROFILE_SCHEMA.md §5](../PROFILE_SCHEMA.md) (Garmin 포럼 조사,
  2026-07-22). "약 128KB/8KB"는 포럼발 수치로 공식 문서 보증이 아님 —
  마진 80%를 두는 이유이기도 하다

### 이 스토리가 열어주는 것

| 스토리 | 받는 것 |
|---|---|
| 1.3 캐리어 중립 추상화 | `serialize`/`deserialize`가 어댑터 경계 안쪽의 공통 표현이 됨 |
| Epic 2 (BLE 데모) | 실측 크기 + 필요 청크 수 — 20B MTU 프로토콜 설계의 입력 |
| 3.1 재설치 복원 | `deserialize` + 검증 재실행 = 복원 경로의 신뢰 게이트 |
| 발표 | "기기 12대 가정 실측 N바이트 = 예산의 M%" — 손목에 들어간다는 주장의 수치 증거 |

### 테스트 규약 (1.1 교훈 반영판)

- 스텁 판별: 왕복 테스트는 `==` 등가로, 리포트 테스트는 합산 정합으로,
  거부 테스트는 **정확한 사유 개수**로 단언
- 경계: 빈 프로필(`new_profile()`) / LARGE / 마진 직전·직후 / 0바이트 입력 /
  잘린 JSON / BOM 붙은 UTF-8 / `bytes`가 아닌 입력(str·None)
- 전체 회귀 기준선: **87 passed** (`980322a` 시점). 작업 후
  `python -m pytest tests/ -q` 전체 통과 유지

### References

- [Source: docs/planning-artifacts/epics.md#Story 1.2] — AC 원문
- [Source: docs/planning-artifacts/epics.md#NonFunctional Requirements] — NFR4(자원)·
  NFR3(캐리어 중립)·NFR6(근거 무결성)
- [Source: docs/implementation-artifacts/1-1-home-profile-schema.md] — 직전 스토리
  리뷰 평결·계승 계약(예외 금지·스텁 판별·정직 표기)
- [Source: docs/PROFILE_SCHEMA.md §2·§5] — 스키마 v2 방어선, 전송 제약 실측
- [Source: home_profile/schema.py] — 소비 인터페이스(validate_profile 계약)
- [Source: docs/DEV_PLAN.md#5] — 운영 원칙(모르는 것은 수치화하지 않는다)
- Garmin Connect IQ 저장 한계: https://forums.garmin.com/developer/connect-iq/f/discussion/2661/storage-available
- Connect IQ BLE 20바이트 MTU: https://forums.garmin.com/developer/connect-iq/f/discussion/196823/bluetooth-low-energy-mtu-size-for-characteristics/1443557

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (Claude Opus 4.8)

### Debug Log References

- RED: `pytest tests/test_home_profile_storage.py` → collection error(모듈 부재)
- GREEN: 동일 명령 → 30 passed
- 회귀: `pytest tests/ -q` → **117 passed** (기준선 87 → +30, 회귀 0건)
- 실측 실행 2회: 대표 가정 3종 크기 판정 + 대응 선택지 4종 비교(§크기 실측)

### Completion Notes List

**AC 충족 근거**

- **AC1 (크기 예산)**: SMALL 1,644B(25.1%)·TYPICAL 4,180B(63.8%)는 키 예산
  6,553B 내. **LARGE 10,310B(157.3%)는 초과** — AC는 "예산 안에 들어간다"이므로
  현재 구조로는 기기 30대 가정에서 **미충족**이며, 이 사실을 판정으로 보고한다
  (초과를 숨기지 않는 것이 AC2의 존재 이유다). 총량 예산 대비로는 9.8%라
  문제는 저장 공간이 아니라 **키 1개당 8KB 상한**임이 확인됐다.
- **AC2 (크기 리포트)**: `size_report()`가 섹션별·단위당·상위 기여 필드 경로를
  낸다. LARGE 초과 시 `routines[7] 264B` 식으로 지목되며, `resolve_path()`로
  경로가 실재함을 테스트가 검증한다. 검증 미통과 프로필에도 리포트가 나온다
  (초과 진단이 목적이므로 그때 프로필은 대개 정상이 아니다).
- **AC3 (왕복 무손실)**: 3종 샘플 + 빈 프로필 전부 `deserialize(serialize(p)) == p`,
  스칼라 타입 보존(bool이 int로 붕괴하지 않음) 확인, 왕복 후 재검증도 통과.
- **AC4 (버전 명시 처리)**: 지원 밖 버전은 **명시적 거부** + 사유에 버전 문자열
  병기. 마이그레이션 미구현·미결정 유지(1.1 리뷰 F5) — 빈 훅을 만들지 않았고,
  `MIGRATIONS`/`migrate` 부재를 테스트가 고정한다.

**계승 계약 이행 (1.1 리뷰 유래)**
- 예외 금지: `serialize`·`deserialize`·`size_report` 전부 fail-closed.
  0바이트·잘린 JSON·비UTF8·비객체·BOM·깊이 1500 폭탄·비bytes 입력 전부
  오류 목록으로 반환(크래시 0건, 테스트로 고정)
- 와이어 불신: `deserialize`가 역직렬화 직후 `validate_profile()` 재실행
- 직렬화 게이트: 검증 미통과 프로필은 직렬화 거부 — PII 담긴 프로필이
  와이어로 나가는 경로를 막는다(1.1 방어선이 저장 계층에서도 유효함을 테스트)
- 스텁 판별: '단어 언급' 단언 없음. 왕복은 `==`, 리포트는 합산 정합·경로 실재,
  예산 판정은 `monkeypatch`로 경계를 실제로 넘겨 뒤집힘 확인

**정직 표기**
- 대표 가정(기기 5/12/30)은 실측이 아니다 — `SAMPLE_ASSUMPTIONS_ARE_MEASURED
  = False` 상수와 `SAMPLE_ASSUMPTION_NOTE`로 코드가 스스로 밝히며, 테스트가
  이 라벨을 고정한다. 설문 문6 실측 시 교체. **실측인 것은 바이트 수뿐이다.**
- 대응 선택지 4종은 실행해서 재고 **구현하지 않았다** — 결정은 사람 몫.

**사람 결정 필요 (미해결)**
1. **LARGE 초과 대응 선택**: A 섹션 분할(최대 키 4,511B, 스키마 변경 불필요,
   단 Epic 3에서 원자성 필요) vs C zlib(1,257B, −87.8%, stdlib) vs B+C.
2. **C의 선행 조건**: Connect IQ(Monkey C)에 압축 해제가 있는지 **미확인**.
   없으면 C는 성립하지 않으며, 확인 전까지 A가 유일하게 검증된 경로다.
3. 대표 가정 자체가 과대할 수 있다 — 실가구 기기 수가 19대 이하면 현재
   단일 키 구조로 충분하다. **설문 문6이 이 결정의 실측 근거가 된다.**

### File List

**신규**
- `home_profile/storage.py`
- `tests/test_home_profile_storage.py`

**수정**
- `home_profile/__init__.py` (storage API export + `__all__`)
- `docs/PROFILE_SCHEMA.md` (§5.1 크기 실측 + 대응 선택지 신설)
- `docs/implementation-artifacts/1-2-onbody-storage-size-budget.md` (본 파일)

`home_profile/schema.py` 무변경, 새 의존성 0건.

## Change Log

| 날짜 | 변경 |
|---|---|
| 2026-07-22 | **결정 ①~⑤ 반영.** JSON 유지, MARGIN 폐기→구간 표기, 스키마 개수 상한 신설, 섹션 분할 채택. 최악 케이스 실측 99,657B(최대 섹션 46,381B) — 현재 상한으로는 어떤 예산에도 미달, 결정 ②(실기기 실측)가 선행 조건임이 드러남. 테스트 127 passed. 상세 PROFILE_SCHEMA §5.4 |
| 2026-07-22 | **Code Review Crew 2차 평결: changes-requested.** §5.1 판정 철회 — 측정 대상이 스키마가 아니라 합성 픽스처였다. 스키마 최대 길이로 같은 12·8이 23,395B(357%). 상세 §5.2 |
| 2026-07-22 | Story 1.2 구현 — storage.py(직렬화·역직렬화·크기 리포트) + 회귀 30건. 실측: SMALL 1,644B / TYPICAL 4,180B / LARGE 10,310B(키 예산 157.3% 초과). 대응 선택지 4종 실측 후 미구현(사람 결정 대기). 전체 117 passed |
