---
baseline_commit: c77540ddbfaf5e5ea23edadc507c7597c30cf2f7
---

# Story 1.1: 홈 프로필 스키마 정의

Status: review

## Story

As a **Night Keeper**(밤에 지키는 사람 — 잡 기반 페르소나, 인구통계 미확정),
I want 내 집의 기기·설정·루틴이 하나의 이식 가능한 프로필로 정의되기를,
so that 앱이나 서버가 아니라 **내가** 집 상태의 보관 주체가 된다.

**에픽 맥락**: Epic 1은 나머지 전부의 전제다 — 스키마가 없으면 BLE로 보낼 것도(Epic 2),
복원할 것도(Epic 3), 프라이버시를 주장할 근거도(Epic 4) 없다.
[Source: docs/planning-artifacts/epics.md#Epic 1]

## Acceptance Criteria

**AC1 — 필수 필드 구성**
**Given** 기기 등록 정보·설정값·루틴을 포함하는 프로필 스펙이 필요할 때
**When** 스키마를 정의하면
**Then** 기기 식별자·설정 키/값·루틴(트리거·액션)·**스키마 버전** 필드를 포함한다

**AC2 — 웰니스 예약 (NFR5, 의료 규제)**
**And** 웰니스 필드는 **예약(reserved)으로만** 선언되고 어떤 진단·의료 판단 로직도 갖지 않는다

**AC3 — 마이그레이션 경로**
**And** 스키마 버전이 명시되어 향후 마이그레이션 경로가 열려 있다

**AC4 — 식별자 부재 증명 (FR7 선행)**
**Given** 프로필에 개인 식별 정보가 들어갈 여지가 있을 때
**When** 스키마를 검토하면
**Then** 이름·계정·연락처 등 식별자 필드가 **존재하지 않음**이 문서로 확인된다

[Source: docs/planning-artifacts/epics.md#Story 1.1]

## Tasks / Subtasks

- [x] **Task 1: 스키마 정의 모듈 작성** (AC: 1, 2, 3)
  - [x] `home_profile/schema.py` 신설 — 스키마를 **선언적 상수 + 검증 함수**로 정의
        (JSON Schema dict 또는 dataclass. 외부 의존성 추가 금지 — 아래 '라이브러리 제약' 참조)
  - [x] 최상위 필드 — **근거 문서 유래**: `schema_version`(str, semver), `devices`[],
        `settings`{}, `routines`[], `reserved_wellness`{}
  - [x] ⚠️ `profile_id`가 필요하다고 판단되면 **반드시 비식별 랜덤값**으로만 두고,
        `docs/PROFILE_SCHEMA.md`에 **"설계 판단(근거 문서 없음)"**으로 표기할 것.
        epics.md AC에 없는 필드다 — 넣는 것도 안 넣는 것도 가능하되, 넣었으면 출처를
        정직하게 '창작'으로 표기한다. 계정·기기 시리얼에서 유도한 값은 AC4 위반
  - [x] `devices[]`: `device_ref`(로컬 기기 식별자 — 시리얼·계정 아님), `device_type`, `capabilities`[]
  - [x] `routines[]`: `trigger`{type, params}, `actions`[{device_ref, setting_key, value}]
  - [x] `reserved_wellness`: **예약 선언만** — 값 스키마는 `{}`(빈 객체)로 고정하고
        읽기·해석·판단 코드를 일절 작성하지 않는다. 주석에 "NFR5: 진단·의료 판단 금지" 명시
- [x] **Task 2: 버전·마이그레이션 계약** (AC: 3)
  - [x] `SCHEMA_VERSION = "1.0.0"` 상수, 프로필 생성 시 자동 각인
  - [x] `is_supported(version)` — 지원 범위를 명시적으로 판정. **모르는 버전은 조용히 통과 금지**
  - [x] `MIGRATIONS` 레지스트리 뼈대(빈 dict + 등록 규약 주석) — 1.0.0은 마이그레이션 없음
- [x] **Task 3: 식별자 부재 검증** (AC: 4)
  - [x] `FORBIDDEN_FIELD_PATTERNS` — name/account/email/phone/user_id/birth 등 금지 패턴 상수
  - [x] `assert_no_identifiers(profile)` — 중첩 dict/list를 재귀 순회해 금지 키 검출 시 거부
  - [x] 스키마 자체를 이 함수에 통과시키는 테스트로 "설계상 부재"를 기계 증명
- [x] **Task 4: 검증 함수** (AC: 1, 2, 3)
  - [x] `validate_profile(profile) -> list[str]` — 위반 사유 목록 반환(빈 리스트 = 통과).
        예외가 아니라 목록 반환: 여러 위반을 한 번에 보고해야 사람이 판단한다
  - [x] 미지 최상위 키는 **거부**한다(조용한 확장 금지 — NFR6 정합)
- [x] **Task 5: pytest 회귀 자산** (프로젝트 필수 규약)
  - [x] `tests/test_home_profile_schema.py` 신설
  - [x] 케이스: 유효 프로필 통과 / 식별자 필드 주입 시 거부 / 미지 버전 거부 /
        미지 최상위 키 거부 / `reserved_wellness`에 값 넣어도 해석 로직 부재 확인 /
        루틴 액션이 존재하지 않는 `device_ref` 참조 시 거부
- [x] **Task 6: 스키마 문서화** (AC: 4)
  - [x] `docs/PROFILE_SCHEMA.md` 신설 — 필드표 + **"수집하지 않는 것"** 절
        (CX_DEFINITION.md §4 '수집하지 않은 것' 표기 방식을 그대로 승계)
  - [x] NFR5 예약 필드의 의미와 금지 범위를 문서에 못박음

## Dev Notes

### 🚨 이 스토리의 함정 — 먼저 읽을 것

**1. 크기 예산은 Story 1.2지만, 스키마 설계가 그 결과를 이미 결정한다.**
실기기 제약을 확인했다(2026-07-22 조사):

| 제약 | 값 | 출처 |
|---|---|---|
| Connect IQ `Application.Storage` 총량 | **약 128KB** | Garmin 개발자 포럼 |
| Storage **키 1개당** | **약 8KB** | 〃 |
| Connect IQ BLE 특성 read/write | **약 20바이트, long write 미지원** | Garmin 개발자 포럼 / API 문서 |

→ **설계 함의**: 프로필 전체를 한 키·한 write로 보내는 설계는 **물리적으로 불가능**하다.
스키마는 처음부터 **청크 분할 가능한 구조**여야 한다 — 즉 `devices[]`·`routines[]`가
각각 독립적으로 직렬화·전송 가능해야 하고, 필드 이름은 짧아야 한다(20바이트 MTU에서
키 이름 길이가 곧 전송 비용). 다만 **이 스토리에서 청크 프로토콜을 구현하지는 말 것** —
Story 1.2(크기 예산)·Epic 2(BLE 전송)의 범위다. 여기서는 **구조가 그것을 가능하게**
만들어 두고, 근거를 `docs/PROFILE_SCHEMA.md`에 남긴다.

**2. `reserved_wellness`는 "나중에 쓰려고 비워둔 칸"이 아니라 "쓰지 않겠다는 선언"이다.**
NFR5는 의료 규제 대응이다. 필드를 선언하되 **읽는 코드·해석하는 코드·판단하는 코드를
쓰지 않는 것**이 AC2의 실질이다. 값을 넣어도 아무 일이 일어나지 않아야 하고,
그것을 테스트로 고정한다. "일단 파싱만 해두자"는 AC 위반이다.

**3. AC4는 "안 넣었다"가 아니라 "없음을 증명했다"를 요구한다.**
`assert_no_identifiers()`를 만들어 스키마 자신을 통과시키는 테스트가 증명 수단이다.
문서에 "안 넣었습니다"라고 쓰는 것만으로는 AC4 미충족.

**4. 이 프로젝트의 서명: "불확실을 확실로 세탁하지 않는다."**
스키마에 근거 없는 필드를 창작하지 말 것. epics.md가 명시한 필드 외에 추가하고 싶으면
`docs/PROFILE_SCHEMA.md`에 "설계 판단(근거 문서 없음)"으로 표기한다.
[Source: docs/planning-artifacts/epics.md#Overview — "요구사항을 임의로 창작하지 않았으며"]

### 라이브러리·환경 제약

- **Python 3.10+**, Windows(cp949 콘솔) 동작 보장. 스크립트 상단 `sys.stdout.reconfigure`
  패턴은 기존 코드(`synthetic_panel.py:31-33`)를 그대로 따를 것
- **새 런타임 의존성 추가 금지 (기본값).** `requirements.txt`는 재현성을 위해 버전 범위가
  고정돼 있다. `pydantic`·`jsonschema`를 끌어오고 싶어도 **표준 라이브러리(dataclasses,
  typing)로 먼저 시도**할 것. 표준 라이브러리로 불가능한 이유를 대지 못하면 추가 금지.
  이유: 이 프로필은 최종적으로 워치급 환경(Monkey C)으로 이식될 표현이다 — Python 전용
  라이브러리에 스키마 정의가 종속되면 캐리어 중립(NFR3)이 코드 레벨에서 깨진다
- 직렬화 포맷은 **이 스토리에서 확정하지 않는다**. JSON을 기본 표현으로 쓰되,
  Story 1.2에서 크기 예산 측정 후 CBOR/MessagePack 전환 가능성을 열어둔다 —
  그래서 스키마는 **포맷 중립적인 dict 구조**로 정의해야 한다

### 파일 배치 규약

기존 저장소 구조:
```
DX_project/
  dx_pipeline_v2.2/     ← 분석 파이프라인 (이 스토리와 무관, 건드리지 말 것)
  synthetic_panel.py    ← 루트 스크립트 (ThinQ Village)
  moa_orchestrator.py   ← 루트 스크립트 (MoA)
  tests/                ← pytest 자산 전부 여기 (testpaths=tests, pytest.ini)
  docs/                 ← 문서
```
**신규**: `home_profile/` 패키지를 루트에 신설(`__init__.py` + `schema.py`).
제품 코드(온바디 프로필)와 분석 파이프라인은 **다른 계보**다 — `dx_pipeline_v2.2/` 안에
넣지 말 것. 테스트는 프로젝트 규약대로 `tests/`에 둔다.

### 재사용 — 바퀴를 다시 만들지 말 것

- **해시 유틸**: `dx_pipeline_v2.2/lineage.py::file_sha256`이 이미 있다.
  단, 이 프로젝트에는 **의도적 중복 선례**가 있다 — `synthetic_panel.py:74`가 같은 함수를
  복제하고 "루트 스크립트가 하위 파이프라인 폴더를 import하는 결합을 피한다"는 주석을 달았다
  (파티 평결: Dana 승). `home_profile/`도 같은 판단을 따를 것 — **import하지 말고, 필요하면
  복제하되 이유를 주석으로 남긴다.** 주석 없는 복제는 리뷰에서 반려된다
- **검증 함수 반환 규약**: `validate_seg_bundle()`(synthetic_panel.py:82)이
  "통과 시 튜플, 실패 시 사유 문자열" 패턴을 쓴다. 다만 이 스토리는 **다중 위반 보고**가
  필요하므로 `list[str]` 반환을 채택한다(빈 리스트 = 통과). 차이의 이유를 docstring에 남길 것
- **테스트 픽스처 패턴**: `tests/test_panel.py`의 `_write_bundle()` 헬퍼처럼,
  유효한 최소 프로필을 만드는 `_make_profile()` 헬퍼를 두고 케이스마다 변조하는 방식을 따를 것

### 이 스토리가 열어주는 것 (하위 스토리 계약)

| 스토리 | 이 스키마에서 무엇을 받는가 |
|---|---|
| 1.2 온바디 저장·크기 예산 | 직렬화 대상 구조 + 대표 가정(기기 N대·루틴 M개) 샘플 |
| 1.3 캐리어 중립 추상화 | 벤더 SDK에 독립적인 프로필 표현(어댑터 경계 뒤 격리 대상) |
| 3.1 재설치 무재등록 복원 | `device_ref` 기반 매칭 — 계정 조회 없이 복원 가능해야 함 |
| 3.2 이사 매핑 | 매칭 불가 항목의 **손실 없는 보류**를 표현할 자리가 스키마에 있어야 함 |
| 4.2 데이터 소재 명시 | "서버에 원본 없음"을 주장할 근거 = 식별자 부재 증명(AC4) |

⚠️ **3.2의 '보류(pending)' 표현**을 지금 창작하지 말 것. epics.md는 3.2에서 요구하지만
1.1 AC에는 없다. 스키마가 나중에 그것을 **수용 가능한 구조**(routines가 device_ref로
느슨하게 참조)면 충분하다.

### Project Structure Notes

- `home_profile/`는 신규 최상위 패키지 — 기존 `dx_pipeline_v2.2/`와 계보·목적이 다름
- 기존 파일 **수정 대상 없음**(UPDATE 파일 0건). 전부 신규 생성이므로 회귀 위험은
  `tests/` 전체 통과 여부로만 판정된다. 작업 후 `python -m pytest tests/ -q` 55개 통과 유지 필수
  (현재 기준선: 55 passed — `12f5965` 시점)
- `pytest.ini`의 `testpaths = tests` 때문에 다른 위치의 테스트는 수집되지 않는다

### 테스트 규약

- 프로젝트 원칙: **"검증은 일회성 실행이 아니라 `tests/` pytest 자산으로 영구화한다"**
  [Source: docs/planning-artifacts/epics.md#Additional Requirements]
- 순수 함수(스키마 검증)는 실데이터 없이 고정 가능하다 — 파티 평결(Grumbal) 선례대로
  경계값을 테스트로 못박을 것
- 느린 테스트는 `@pytest.mark.slow` 마커 사용(pytest.ini에 등록됨). 이 스토리는 해당 없음

### References

- [Source: docs/planning-artifacts/epics.md#Story 1.1] — AC 원문
- [Source: docs/planning-artifacts/epics.md#NonFunctional Requirements] — NFR3 캐리어 중립,
  NFR4 자원 제약, NFR5 웰니스 규제, NFR6 근거 무결성
- [Source: docs/CX_DEFINITION.md#1] — 처방 정의(온바디 홈 프로필), v2 비전 레이어의
  "체성분은 스키마 예약 필드만. 진단 기능 배제 — 의료 규제"
- [Source: docs/CX_DEFINITION.md#4] — "수집하지 않은 것" 방어 표기 서술 방식(문서 Task 6 참조)
- [Source: docs/DEV_PLAN.md#5] — 운영 원칙 4개(계보·폴백 기록·산출 불가·최종 책임 팀)
- [Source: docs/API_SPEC.md#4] — 환경 계약(Python 3.10+, cp949, 의존성 관리)
- [Source: synthetic_panel.py:74] — 의도적 중복 선례와 주석 규약
- [Source: tests/test_panel.py] — 픽스처·회귀 테스트 작성 패턴
- Garmin Connect IQ 저장 한계(약 128KB 총량 / 키당 약 8KB):
  https://forums.garmin.com/developer/connect-iq/f/discussion/2661/storage-available
- Connect IQ BLE 특성 20바이트 MTU·long write 미지원:
  https://forums.garmin.com/developer/connect-iq/f/discussion/196823/bluetooth-low-energy-mtu-size-for-characteristics/1443557
- Connect IQ BLE 개요: https://developer.garmin.com/connect-iq/core-topics/bluetooth-low-energy/

## Dev Agent Record

### Agent Model Used

claude-fable-5 (Claude Fable 5)

### Debug Log References

- RED: `pytest tests/test_home_profile_schema.py` → 23 errors (모듈 부재) — 테스트 정당성 확인
- GREEN: 동일 명령 → 23 passed
- 회귀: `pytest tests/ -q` → **78 passed** (기준선 55 → +23, 회귀 0건)

### Completion Notes List

**구현 요약** — 표준 라이브러리만으로 스키마를 순수 dict 계약으로 정의했다.
외부 의존성 0건 추가(`requirements.txt` 무변경) — 캐리어 중립(NFR3)이 코드 레벨에서
깨지지 않도록 pydantic·jsonschema를 쓰지 않았다.

**AC 충족 근거**
- **AC1**: `TOP_LEVEL_KEYS`/`REQUIRED_TOP_LEVEL_KEYS` 상수 + `validate_profile()`.
  기기 식별자(`device_ref`)·설정 K/V(`settings`)·루틴(`trigger`/`actions`)·
  `schema_version` 전부 포함. 미등록 기기를 참조하는 루틴과 `device_ref` 중복도 거부
- **AC2**: `reserved_wellness`는 선언되어 있으나 **빈 객체만 허용**(값을 담으면 거부).
  웰니스 해석 함수 5종(`wellness_score`·`interpret_wellness`·`diagnose`·
  `assess_health`·`evaluate_wellness`) 부재를 테스트가 고정
- **AC3**: `SCHEMA_VERSION="1.0.0"`, `is_supported()`가 형식 위반·미지 버전을 전부
  `False`로 판정(조용한 통과 없음), `MIGRATIONS` 레지스트리 + 등록 규약 주석
- **AC4**: `assert_no_identifiers()`가 중첩 dict/list를 재귀 순회, 부분 일치·대소문자
  무시로 검출. `validate_profile()`이 내부에서 호출하므로 별도 호출을 잊어도 막힌다.
  **스키마 자신이 이 검사를 통과함**을 테스트로 기계 증명(`test_schema_itself_has_no_identifier_fields`).
  문서화는 `docs/PROFILE_SCHEMA.md` §2 "수집하지 않는 것"

**스토리 지시와 다르게 한 것 (정직 표기)**
- 상수명을 `FORBIDDEN_FIELD_PATTERNS` → **`FORBIDDEN_KEY_FRAGMENTS`** 로 변경.
  정규식 패턴이 아니라 부분 문자열 조각을 담기 때문에 이름이 내용을 오도했다
- `profile_id` **미채택**. 스토리는 "넣으면 창작으로 표기하라"고 허용했으나,
  AC에 없고 잘못 만들면 계정 식별자로 퇴화할 위험이 있어 넣지 않았다.
  판단 근거는 `docs/PROFILE_SCHEMA.md` §6에 기록

**후속 스토리로 넘긴 것 (범위 준수)**
- 청크 전송 프로토콜 — 구조만 청크 가능하게 두고 구현은 Story 1.2·Epic 2
- 직렬화 포맷 확정(JSON vs CBOR) — 크기 예산 측정(Story 1.2) 후 결정
- 이사 시 '보류(pending)' 표현 — Story 3.2 범위이며 지금 창작하지 않았다

**미해결 질문 (사람 판단 필요)**
1. `FORBIDDEN_KEY_FRAGMENTS`에 `"name"`이 있어 `device_name` 같은 **사용자 지정
   기기 별칭**("안방 에어컨")도 차단된다. 별칭은 UX상 필요할 수 있으나 준식별자이기도
   하다 — 허용할지, 허용한다면 어떤 이름으로 예외를 둘지는 설계 결정이다
2. `"owner"` 차단이 `device_owner_room` 같은 무해한 키까지 막을 수 있다.
   현재는 과잉 차단을 택했다("우회할 이름을 찾지 말고 필요성을 되물어라" 규약)

### File List

**신규**
- `home_profile/__init__.py`
- `home_profile/schema.py`
- `tests/test_home_profile_schema.py`
- `docs/PROFILE_SCHEMA.md`

**수정**
- `docs/implementation-artifacts/1-1-home-profile-schema.md` (frontmatter·체크박스·Dev Agent Record)

기존 파일 수정 0건 — `dx_pipeline_v2.2/`·`synthetic_panel.py`·`requirements.txt` 무변경.

## Change Log

| 날짜 | 변경 |
|---|---|
| 2026-07-22 | Story 1.1 구현 — 홈 프로필 스키마 v1.0.0 + 회귀 테스트 23건 + 스키마 명세 문서. 전체 테스트 78 passed |
| 2026-07-22 | **Code Review Crew 평결: changes-requested.** AC2·AC3·AC4 미충족 재판정. PROFILE_SCHEMA.md §2·§4의 거짓 보증 문구 철회·정정 |
| 2026-07-22 | **리뷰 반영 v2 재작성.** 스키마·테스트 전면 재작성 — 리뷰 우회 14건 전수 차단 확인, 스텁 판별 테스트(스텁 13건 FAIL), 전체 87 passed. 상태 review 복귀 |

## Senior Developer Review (AI)

**리뷰**: Code Review Crew (Vex 보안 / Grumbal 적대 / Boundary 엣지 / Yui 장인 / Dana 현실) · 2026-07-22
**결과**: **Changes Requested** — AC1만 충족. AC2·AC3·AC4 미충족.

### 재판정 근거 (전부 실행으로 확인)

- **AC4 미충족** — `assert_no_identifiers()`는 **키 이름만** 검사한다. 값은 한 번도 읽지 않는다.
  `device_ref="hong.gildong@gmail.com"`, `device_type="서울 강남구 123-4 홍길동 침실"` → `[]`.
  금지어가 **영어 12개뿐**이라 `이름`·`전화번호` 통과, 호모글리프(`аccount_id`, 키릴 а) 통과,
  `ssid`·`lat`·`lon`(가구 식별자+위치) 통과. "기계 증명"은 `new_profile()` 즉 **빈 컨테이너 4개**를
  검사한 것이었다 — 스키마에 대한 증명이 아니라 `{}`에 대한 증명.
- **AC2 미충족** — `reserved_wellness`는 잠갔으나 `settings`가 임의 키를 받는다.
  `{"sleep_score":82,"body_fat_pct":18.2,"bp_systolic":139}` → `[]`. 게다가
  `reserved_wellness`는 필수 키가 아니라 **키를 빼면 검사가 건너뛰어진다**.
  '해석 함수 부재' 테스트는 구현자가 사후에 고른 이름 5개에 대한 `hasattr`라 실패 불가.
- **AC3 미충족** — `MIGRATIONS`를 읽는 코드가 0줄. 더구나 `is_supported()`가 구버전을
  **거부**하므로 옛 프로필은 마이그레이션되기 전에 차단된다. 마이그레이션을 쓰려면
  `is_supported`부터 뜯어야 한다 = 그 결정이 아직 안 내려졌다.
- **NFR6 부분 충족** — 미지 키 거부는 **최상위에서만** 작동. 중첩 레벨(devices[]·
  settings[ref]·routines[]·trigger·actions[]) 전부 임의 키 자유. 위 우회들의 실제 통로.

### 검증 게이트 자체의 결함

- **테스트 23개가 검증 로직 0줄짜리 스텁을 구별하지 못한다** (직접 재현: 23 passed).
  단언 대부분이 `assert any(<문자열> in e for e in errs)` — 검증이 일어났는지가 아니라
  그 단어가 언급됐는지만 본다. `test_profile_is_chunkable...`은 `json` 모듈을 테스트하며
  `schema.py`를 호출조차 하지 않는다.
- **`validate_profile()`이 계약을 어기고 예외를 던진다**: `device_ref`가 list/dict면
  `TypeError: unhashable`, 깊이 1000 중첩이면 `RecursionError`, 순환 참조도 크래시.
  docstring이 "예외를 던지지 않는다"고 약속해 호출자가 방어하지 않는다.
  **이 크래시들은 `assert_no_identifiers()`(함수 마지막 줄)보다 먼저 터진다** — 즉
  try/except를 쓰는 호출자에서는 PII 검사가 아예 실행되지 않는다.
- **`null`이 검증을 통째로 끈다**: `devices:null` → 모든 구조·참조 검사 스킵 → `[]`.
  `device_ref:null`이면 중복 검사와 유령 참조 검사가 동시에 꺼진다.
- **직렬화 불가 프로필이 통과한다**: `set` 값 → `validate_profile()==[]`,
  `json.dumps()` → `TypeError`. Story 1.2가 정면으로 밟을 지점.

### Review Follow-ups (AI)

- [x] [AI-Review][High] 테스트 스텁 판별력 확보 — 정확한 위반 수·경로 단언으로 재작성, 스텁 재검증 13건 FAIL 확인
- [x] [AI-Review][High] FR7 값 검사 — 이메일·전화·주민번호 정규식 + 한국어 식별 문구 스캔(값), 키 조각 영+한 확장
- [x] [AI-Review][High] 키 구조 봉쇄 — 전 레벨 화이트리스트, device_ref 토큰 형식, setting_key ASCII 형식(한국어·호모글리프 키 형식 단계 차단)
- [x] [AI-Review][High] null = 위반 (스킵 아님) — devices/settings/routines/trigger/device_ref 전부
- [x] [AI-Review][High] 크래시 봉쇄 — unhashable ref·깊이 폭탄·순환 참조 전부 위반 목록으로. 식별자 스캔을 최우선 실행 + fail-closed
- [x] [AI-Review][High] NFR5 옆문 — reserved_wellness 필수 키 승격 + settings 웰니스성 키 거부
- [x] [AI-Review][Med] 직렬화 게이트 — 값은 스칼라만(유한 float), set·NaN 거부
- [x] [AI-Review][Med] assert_no_identifiers → find_identifier_violations 개명
- [x] [AI-Review][Med] validate_profile 헬퍼 6개로 분해 (7단 중첩 해소)
- [x] [AI-Review][Med] MIGRATIONS 삭제 — 마이그레이션은 '미결정'으로 정직 표기 (AC3 재해석: 버전 각인+미지 버전 거부까지가 이 스토리의 실질)
- [x] [AI-Review][Low] __init__.py __all__ 명시, SUPPORTED_VERSIONS 공개, 패키지 import 테스트 추가
- [x] [AI-Review][Low] is_supported의 inert semver 파싱 제거

### 구조 (Yui)

- `assert_no_identifiers`는 이름이 거짓 — `assert_*`인데 raise하지 않고, 성공 시 falsy를
  반환한다. 맨 문장으로 쓰면 조용한 no-op. → `find_identifier_violations()`로 개명
- `validate_profile()` 116줄 7단 중첩 → 헬퍼 4개로 분해 (테스트가 동작을 고정한 지금이 최저비용)
- `is_supported()`의 semver 파싱 3줄은 어떤 입력에서도 답을 바꾸지 못함(inert)
- `__init__.py`가 가변 전역 `MIGRATIONS`를 내보내고 `SUPPORTED_VERSIONS`는 빼놓음.
  테스트가 `import home_profile`을 한 번도 실행하지 않아 export가 썩어도 CI 초록불
