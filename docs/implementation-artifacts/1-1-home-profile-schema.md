# Story 1.1: 홈 프로필 스키마 정의

Status: ready-for-dev

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

- [ ] **Task 1: 스키마 정의 모듈 작성** (AC: 1, 2, 3)
  - [ ] `home_profile/schema.py` 신설 — 스키마를 **선언적 상수 + 검증 함수**로 정의
        (JSON Schema dict 또는 dataclass. 외부 의존성 추가 금지 — 아래 '라이브러리 제약' 참조)
  - [ ] 최상위 필드 — **근거 문서 유래**: `schema_version`(str, semver), `devices`[],
        `settings`{}, `routines`[], `reserved_wellness`{}
  - [ ] ⚠️ `profile_id`가 필요하다고 판단되면 **반드시 비식별 랜덤값**으로만 두고,
        `docs/PROFILE_SCHEMA.md`에 **"설계 판단(근거 문서 없음)"**으로 표기할 것.
        epics.md AC에 없는 필드다 — 넣는 것도 안 넣는 것도 가능하되, 넣었으면 출처를
        정직하게 '창작'으로 표기한다. 계정·기기 시리얼에서 유도한 값은 AC4 위반
  - [ ] `devices[]`: `device_ref`(로컬 기기 식별자 — 시리얼·계정 아님), `device_type`, `capabilities`[]
  - [ ] `routines[]`: `trigger`{type, params}, `actions`[{device_ref, setting_key, value}]
  - [ ] `reserved_wellness`: **예약 선언만** — 값 스키마는 `{}`(빈 객체)로 고정하고
        읽기·해석·판단 코드를 일절 작성하지 않는다. 주석에 "NFR5: 진단·의료 판단 금지" 명시
- [ ] **Task 2: 버전·마이그레이션 계약** (AC: 3)
  - [ ] `SCHEMA_VERSION = "1.0.0"` 상수, 프로필 생성 시 자동 각인
  - [ ] `is_supported(version)` — 지원 범위를 명시적으로 판정. **모르는 버전은 조용히 통과 금지**
  - [ ] `MIGRATIONS` 레지스트리 뼈대(빈 dict + 등록 규약 주석) — 1.0.0은 마이그레이션 없음
- [ ] **Task 3: 식별자 부재 검증** (AC: 4)
  - [ ] `FORBIDDEN_FIELD_PATTERNS` — name/account/email/phone/user_id/birth 등 금지 패턴 상수
  - [ ] `assert_no_identifiers(profile)` — 중첩 dict/list를 재귀 순회해 금지 키 검출 시 거부
  - [ ] 스키마 자체를 이 함수에 통과시키는 테스트로 "설계상 부재"를 기계 증명
- [ ] **Task 4: 검증 함수** (AC: 1, 2, 3)
  - [ ] `validate_profile(profile) -> list[str]` — 위반 사유 목록 반환(빈 리스트 = 통과).
        예외가 아니라 목록 반환: 여러 위반을 한 번에 보고해야 사람이 판단한다
  - [ ] 미지 최상위 키는 **거부**한다(조용한 확장 금지 — NFR6 정합)
- [ ] **Task 5: pytest 회귀 자산** (프로젝트 필수 규약)
  - [ ] `tests/test_home_profile_schema.py` 신설
  - [ ] 케이스: 유효 프로필 통과 / 식별자 필드 주입 시 거부 / 미지 버전 거부 /
        미지 최상위 키 거부 / `reserved_wellness`에 값 넣어도 해석 로직 부재 확인 /
        루틴 액션이 존재하지 않는 `device_ref` 참조 시 거부
- [ ] **Task 6: 스키마 문서화** (AC: 4)
  - [ ] `docs/PROFILE_SCHEMA.md` 신설 — 필드표 + **"수집하지 않는 것"** 절
        (CX_DEFINITION.md §4 '수집하지 않은 것' 표기 방식을 그대로 승계)
  - [ ] NFR5 예약 필드의 의미와 금지 범위를 문서에 못박음

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

### Debug Log References

### Completion Notes List

### File List
