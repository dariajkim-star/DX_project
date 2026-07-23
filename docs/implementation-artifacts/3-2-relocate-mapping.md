---
baseline_commit: a6c6deb
---

# Story 3.2: 이사 — 새 기기 집합 매핑

Status: review

## Story

As a **전세 거주 Night Keeper**(가설 H2: 이사 예정자),
I want 이사한 집의 새 기기들에 기존 설정을 옮기기를,
so that 이사 때마다 집을 처음부터 다시 길들이지 않는다.

**에픽 맥락**: 3.1(재설치 복원)이 "같은 집, 폰만 초기화"를 풀었다면, 3.2는
**"다른 집, 다른 기기"**를 푼다 — Epic 3(P-2 반박)의 마지막 조각. 3.1의 복원은
device_ref가 그대로였지만, 이사는 **기기 집합 자체가 바뀐다**(새 device_ref·다른
구성·개수 불일치). 그래서 이건 복원이 아니라 **매핑**이다: 손목의 옛 프로필을
새 집의 기기들에 얹되, 안 맞는 건 버리지 말고 **보류**한다.
[Source: docs/planning-artifacts/epics.md#Story 3.2]

> **발표에서의 위상.** 3.1과 함께 P-2("재설치하니 다 없어짐")를 구조로 반박하는
> 한 쌍이다. 3.2의 핵심 메시지는 **"이사해도 길들인 집이 따라온다"** — 단
> ⚠️ 이건 **처방(설계 결정)**이다. VOC(P-2)가 문제를 줬고, "device_type으로
> 매칭한다"는 해법은 **우리의 선택**이다(Mary 3단 프레임). 매칭 알고리즘의
> 근거를 VOC 수치인 것처럼 말하지 않는다.

## Acceptance Criteria

**AC1 — 매칭 이전 + 손실 없는 보류 (FR5)**
**Given** 기존 프로필과 다른 구성의 새 기기 집합이 있을 때
**When** 프로필을 새 환경에 적용하면
**Then** 매칭되는 기기에는 설정·루틴이 이전되고, 매칭 불가 항목은 **손실 없이 보류**된다

**AC2 — 이전·보류 결과 요약 (조용한 누락 금지)**
**And** 이전·보류 결과가 사용자에게 요약 제시된다(조용한 누락 금지)

**AC3 — H2 가설 정직 표기 (NFR6)**
**Given** H2 가설(전세=이사 예정자 → 온바디 수용도↑)이 미검증일 때
**When** 이 스토리를 발표에서 근거로 쓰면
**Then** "설문 검증 대기 가설"로 표기한다

[Source: docs/planning-artifacts/epics.md#Story 3.2]

## Tasks / Subtasks

- [x] **Task 1: 매핑 함수 — `map_to_new_home`** (AC: 1, 2)
  - [x] ⚠️ **먼저 이게 3.1의 복원이 아님을 이해하라.** 3.1 `restore_from_carrier`는
        device_ref가 보존되는 왕복이다. 3.2는 **device_ref가 바뀐다** — 옛 집의
        `dev000`(에어컨)을 새 집의 `newAC`(에어컨)에 얹는 것. 그래서 `merge_chunks`나
        `restore_from_carrier`를 재사용하는 게 아니라 **새 변환 함수**가 필요하다
  - [x] `home_profile/relocate.py` 신설 — `map_to_new_home(old_profile, new_devices)`
        `-> (new_profile | None, report)`. new_profile은 하드 실패(입력 무효) 시에만
        None. 매칭 성공하되 보류 항목이 있어도 **유효한 new_profile + report**를 낸다
  - [x] **매칭 전략(결정적):** device_type을 매칭 키로 한다. new_devices를
        device_type별로 묶고, old_profile.devices를 **순서대로** 순회하며 같은
        type의 **미사용** new 기기에 1:1 배정. 같은 인자 → 같은 매핑(딕셔너리
        순서·난수 비의존). 옛 기기 N대 vs 새 기기 M대(같은 type)면 min(N,M)만
        매칭되고 나머지는 보류
  - [x] **capability 교집합:** 매칭된 쌍에서 **옛 설정 키 ∩ 새 기기 capabilities**만
        이전한다. 새 기기가 지원 안 하는 설정 키는 **보류**(reason: capability
        미지원). 새 기기가 그 capability를 실제로 가졌는지는 new_devices의
        `capabilities`로 판정
  - [x] **루틴 이전(원자적, 부분 변형 금지):** 루틴의 **모든** 액션이
        (매핑된 기기 + 지원되는 setting_key)로 옮겨질 수 있을 때만 그 루틴을
        새 device_ref로 재작성해 이전한다. 액션 하나라도 못 옮기면 **루틴 통째로
        보류**(reason 기록). 일부만 옮겨 담으면 그게 조용한 변형이다(AC2 위반)
  - [x] ⚠️ **계약 승계(3.1·1.x):** 예외 금지(어떤 입력에도 (None|결과, report)),
        fail-closed, 오류·보류 사유에 페이로드 값 금지(이름·타입·사유 라벨까지만).
        결과 new_profile은 **반드시 `validate_profile()` 통과**(새 refs·지원 키·
        비어있지 않은 actions). 통과 못 하면 (None, report)

- [x] **Task 2: 이전·보류 리포트 — 조용한 누락 금지** (AC: 2)
  - [x] report는 최소 다음을 담는다: `transferred`(옮겨진 기기·설정·루틴 요약),
        `held`(보류 항목 목록, 각 항목에 사유 라벨), `unmatched_new`(설정을 못 받은
        새 기기 — 이것도 침묵하지 않는다). **모든 옛 항목은 transferred 또는 held
        중 정확히 한 곳에 나타난다**(누락 0 불변식)
  - [x] ⚠️ 보류 사유는 열거형 라벨로 고정한다(자유 문자열로 PII 운반 금지):
        예) `no_matching_type`(같은 type 새 기기 없음), `capability_unsupported`
        (설정 키 미지원), `routine_action_unmappable`(루틴 액션 이전 불가).
        사유 라벨 집합을 relocate.py 상단 상수로 둔다
  - [x] **불변식 테스트 대상:** len(old.devices) == len(transferred.devices) +
        len(held.devices), 옛 설정 키 총수 == 이전된 키 + 보류된 키. 이 항등식이
        "손실 없음"의 코드적 정의다

- [x] **Task 3: 이사 데모 — "이사했는데 집이 따라왔다"** (AC: 1, 2, 3)
  - [x] `demo_relocate.py` 신설 — 옛 집 프로필(TYPICAL) → 다른 구성의 새 집 기기
        집합 → `map_to_new_home` → 이전/보류 요약을 화면에. 최소 한 건씩:
        매칭 이전 성공, type 불일치 보류, capability 미지원 보류, 루틴 이전/보류
  - [x] 새 기기 집합은 데모에서 **명시적으로 조립**한다(옛 집과 일부만 겹치게 —
        에어컨 있음/청소기 없음/새 스타일러 추가 식). `home_profile/`은 수정 최소
  - [x] ⚠️ **H2 정직 표기(AC3):** 화면·페르소나에 "전세 거주 Night Keeper"를 쓰되
        **"설문 검증 대기 가설(H2)"** 라벨을 반드시 병기. H2 정의는
        `docs/SURVEY_PLAN.md`(전세·월세·이사계획 × 온바디 수용도, 실측 대기).
        인구통계 날조 금지(2.4 계보 — 기각된 김민수·김영희)
  - [x] 배너 규약(§4-b)·정직 표기 유지. 매핑은 시뮬레이션이며 실기기 아님

- [x] **Task 4: 테스트** (AC: 1, 2, 3)
  - [x] `tests/test_relocate_mapping.py` 신설
  - [x] **결정성:** 같은 (old, new) → 같은 new_profile·같은 report(2회 호출 비교)
  - [x] **매칭 이전(AC1):** 같은 type 매칭 시 설정이 새 device_ref로 이전되고
        결과가 `validate_profile` 통과. 지원되는 키만 이전됨을 **정확한 값**으로 단언
  - [x] **손실 없는 보류(AC1·AC2):** type 불일치 기기·미지원 설정 키·이전 불가
        루틴이 각각 held에 사유와 함께 등장. **누락 0 불변식** 항등식 단언
  - [x] **루틴 원자성:** 액션 일부만 매핑 가능한 루틴은 통째로 held(부분 이전 안 됨)
  - [x] **경계값:** 새 집 기기 0대(전부 보류), 같은 type 여러 대(결정적 1:1),
        옛 프로필 빈 것(빈 이전). 예외 금지(garbage 입력 → (None, report))
  - [x] **H2 문서 회귀:** 페르소나/데모 문서에 "설문 검증 대기" 라벨 존재 +
        인구통계 수치(나이·소득 등) 부재 단언(2.4 `test_night_scenario` 계보)
  - [x] 회귀 기준선: **323 passed**(`a6c6deb`, 3.1 리뷰 반영 후). 신규만큼 증가·회귀 0

- [x] **Task 5: 문서 — 발표 대본·H2 표기**
  - [x] `docs/DEMO_SCRIPT.md`에 이사 매핑 장면(§8) 추가 — 3.1 재설치(§7)와 한 쌍으로
        P-2 반박 완성. 이전/보류 요약을 화면에 보이는 것이 이 장면의 정직성
  - [x] H2 가설 표기를 대본에 명시: "전세 거주자 수용도 가설은 **설문 검증 대기**,
        발표에서 근거로 쓸 때 라벨 병기"(NFR6). SURVEY_PLAN.md 링크

## Dev Notes

### 🚨 이 스토리의 함정 — 먼저 읽을 것

**1. 이건 3.1의 복원이 아니라 매핑이다 — device_ref가 바뀐다.**
3.1은 device_ref 보존 왕복이라 `restore_from_carrier`/`merge_chunks`가 동일성을
지켰다. 3.2는 **옛 dev000(에어컨) → 새 newAC(에어컨)**로 참조를 갈아끼운다.
`merge_chunks`를 재사용하려 하면 이 스토리를 오해한 것이다. 새 변환 함수
`map_to_new_home`이 필요하고, 그 산출물은 **새 device_ref로 재작성된 유효 프로필**이다.

**2. "손실 없이 보류"가 이 스토리의 핵심 — 조용한 누락이 곧 실패다.**
매칭 안 되는 기기, 미지원 설정, 이전 불가 루틴을 **버리면 안 된다.** 전부 held에
사유와 함께 남고, "옛 항목 = transferred + held" 항등식이 코드로 성립해야 한다.
이건 3.1의 `merge_chunks` "반쪽 프로필 금지"와 같은 계보다 — 다만 여기선 거부가
아니라 **명시적 보류**다(이사는 부분 이전이 정상이니까). 침묵이 금지되는 것.

**3. 루틴은 원자적으로 옮긴다 — 부분 이전은 조용한 변형이다.**
루틴의 액션 3개 중 2개만 새 집에 매핑되면, 2개짜리 루틴을 조용히 만들지 마라.
그건 사용자가 정의한 자동화를 말없이 바꾸는 것이다. **전부 매핑되면 이전, 하나라도
안 되면 통째로 보류**(사유 기록). 스키마도 이를 돕는다 — actions는 비어있지 않은
배열이어야 하므로(schema.py `_validate_routines`), 액션이 다 빠진 루틴은 애초에
유효하지 않다.

**4. 결정적이어야 한다 — 발표에서 재현되어야 하니까.**
같은 (옛 프로필, 새 기기 집합) → 항상 같은 매핑·같은 리포트. device_type별 묶기와
**순서 기반 1:1 배정**으로 달성한다. 딕셔너리 순회 순서·set 순서·난수에 기대면
발표 때 다른 결과가 나올 수 있다. 3.1 `merge_chunks`가 `meta.device_refs` 순서를
진실로 삼은 것과 같은 규율.

**5. 이건 처방(설계)이다 — 매칭 알고리즘은 우리의 선택이다.**
P-2(VOC)는 "이사하면 다 없어짐"이라는 **문제**를 줬다. "device_type으로 매칭하고
capability 교집합만 이전한다"는 **해법**은 우리가 정한 것이다. 발표에서 이 알고리즘의
정당성을 VOC 수치로 포장하지 마라(epics.md Requirements Inventory 주석 계보).
다른 매칭 전략(사용자 수동 지정 등)도 가능하며, 우리는 결정적 자동 매칭을 택했다.

**6. H2는 미검증 가설이다 — 2.4의 인구통계 날조 교훈을 반복하지 마라.**
"전세 거주자가 온바디를 더 원한다"(H2)는 다리아의 **가설**이고 설문으로만 검증된다
(`SURVEY_PLAN.md`). 발표 페르소나 "전세 거주 Night Keeper"에 나이·소득·직업을
붙이고 싶어지지만(2.4에서 실제로 저지른 실수), **붙이지 마라.** 유효한 것은
잡("이사해도 길들인 집이 따라오길")과 미검증 라벨뿐이다.

**7. 경계 — home_profile 코어, 새 모듈, 캐리어·스키마 무수정.**
`map_to_new_home`은 profile→profile 순수 변환이라 캐리어를 모른다. `relocate.py`
신설, `home_profile/schema.py`·`carrier.py`·`storage.py`는 무수정 목표(스키마로
검증만). 스키마 변경이 필요해 보이면 함정 1을 놓친 신호.

### 재사용 자산 (신규는 relocate.py와 데모·테스트)

| 자산 | 위치 | 용도 |
|---|---|---|
| `validate_profile` | `home_profile/schema.py:467` | 매핑 결과 유효성 강제 |
| `new_profile` | `home_profile/schema.py:157` | 결과 프로필 뼈대 |
| `make_sample_profile` | `home_profile/storage.py:84` | 옛 집 프로필(결정적) |
| device/settings/routine 형태 | `home_profile/schema.py` `_validate_devices`·`_validate_settings`·`_validate_routines` | 매핑 대상 자료구조 계약 |
| MAX_DEVICES/MAX_ROUTINES 등 | `home_profile/schema.py:115` | 규모 상한(3.1 리뷰서 병합에도 강제됨) |
| 페르소나 정직 표기 규약 | `docs/PERSONA_NIGHT_KEEPER.md`, `CX_DEFINITION §3` | "설문 검증 대기" 라벨 |
| H2 정의 | `docs/SURVEY_PLAN.md:10` | 전세·이사계획 × 온바디 수용도(미검증) |
| 데모 하우스 패턴 | `demo_reinstall.py`·`demo_night.py` | 배너 4경계·정직 표기·in-process 테스트 |
| 리포트 "누락 금지" 계보 | 3.1 `merge_chunks`(반쪽 금지) | held 항등식의 사상적 뿌리 |

### 파일 배치

- 신규: `home_profile/relocate.py`, `demo_relocate.py`, `tests/test_relocate_mapping.py`
- 수정: `home_profile/__init__.py`(신규 공개 심볼 export — 3.1 패턴), `docs/DEMO_SCRIPT.md`
  (§8 이사 장면), 필요 시 `docs/PERSONA_NIGHT_KEEPER.md`에 전세 변주 1절(H2 라벨)
- `home_profile/schema.py`·`carrier.py`·`storage.py` **무수정** 목표

### 테스트 규약

- 정확한 값 단언(이전된 설정값·새 device_ref), '단어 언급' 금지
- "누락 0" 항등식을 명시 단언(transferred + held = old 전체)
- 결정성: 2회 호출 결과 동일
- 예외 금지: garbage 입력 → (None, report), 크래시 없음
- 문서 회귀: H2 미검증 라벨 존재 + 인구통계 수치 부재 **둘 다**
- `pytest.ini` testpaths = tests

### References

- [Source: docs/planning-artifacts/epics.md#Story 3.2] — AC 원문(FR5), H2 표기
- [Source: docs/planning-artifacts/epics.md#Epic 3] — P-2 반박, HMW-2
- [Source: docs/implementation-artifacts/3-1-reinstall-restore.md] — 복원 vs 매핑 구분,
  계약 승계(예외 금지·fail-closed·누락 금지), code-review 교훈(상한·조용한 누락)
- [Source: home_profile/schema.py] — device/settings/routine 형태, validate_profile, MAX_*
- [Source: home_profile/storage.py] — make_sample_profile, split_chunks(참고)
- [Source: docs/SURVEY_PLAN.md] — H2 가설 정의(설문 검증 대기)
- [Source: docs/CX_DEFINITION.md#3] — 페르소나 정직 표기·인구통계 날조 기각
- [Source: docs/DEMO_SCRIPT.md] — 이사 매핑 장면을 추가할 대본(§7 재설치와 한 쌍)

## Dev Agent Record

### Agent Model Used

Claude Fable 5 (claude-fable-5) — 2026-07-23

### Debug Log References

- 설계 확정: `map_to_new_home(old_profile, new_devices) -> (new_profile|None, report)`.
  device_type별 순서 기반 1:1 매칭 → capability 교집합 설정 이전 → 루틴 원자 이전.
- 3.1 리뷰 교훈 선제 반영: 결과 프로필의 settings·devices·routines를 deepcopy로
  격리(aliasing 방지). `test_result_has_no_aliasing_with_inputs`로 회귀 고정.
- GREEN: 14/14 첫 회 통과(데모 in-process 포함). 하드 실패·garbage 입력은 전부
  (None, report) 또는 예외 없이 처리 — 예외 금지 계약 유지.
- 데모 실측: 옛 집(에어컨·청소기·조명) → 새 집(에어컨 fan_speed 미지원·청소기
  없음·스타일러 신규) → 에어컨 power/target_temp 이전, fan_speed 보류(미지원),
  청소기 보류(type 없음), 루틴 이전, styler unmatched_new 표기 → exit 0.

### Completion Notes List

- **Task 1**: `home_profile/relocate.py` `map_to_new_home` — device_type 매칭(순서
  결정적), capability 교집합만 이전, 루틴 원자 이전(액션 하나라도 못 옮기면 통째
  보류), 결과 `validate_profile` 통과 강제. 예외 금지·fail-closed.
- **Task 2**: report = transferred/held/unmatched_new/errors. 보류 사유 3종 열거
  상수(`REASON_NO_MATCHING_TYPE`·`REASON_CAPABILITY_UNSUPPORTED`·
  `REASON_ROUTINE_UNMAPPABLE`). "누락 0" 항등식(old = transferred + held)을
  `_identity_holds` 헬퍼로 3축(기기·설정 키·루틴) 단언. 사유·항목에 값 미노출.
- **Task 3**: `demo_relocate.py` — 옛 집/새 집/이전/보류 4경계 장면. 일부러 어긋난
  새 집으로 보류 4종을 모두 시연. H2 라벨(`H2_LABEL`) 병기. 실기기 아님 표기.
- **Task 4**: `tests/test_relocate_mapping.py` 14개 — 매칭 이전·유효성·결정성·
  보류 항등식·루틴 원자성·경계(빈 새집/빈 옛집/여러 대)·예외 금지·aliasing 격리·
  데모 H2 라벨.
- **Task 5**: `DEMO_SCRIPT.md` §8 이사 장면(§7 재설치와 한 쌍) + H2 설문검증 대기
  표기. PERSONA 문서 변경은 불요(H2 라벨이 데모·대본에 있음).

### File List

- `home_profile/relocate.py` — 신규 (`map_to_new_home` + 보류 사유 상수)
- `home_profile/__init__.py` — 수정 (신규 공개 심볼 4종 export)
- `demo_relocate.py` — 신규 (이사 매핑 데모, 4경계)
- `tests/test_relocate_mapping.py` — 신규 (14 tests)
- `docs/DEMO_SCRIPT.md` — 수정 (시연 순서 8 + §8 이사 장면)
- `docs/implementation-artifacts/3-2-relocate-mapping.md` — 본 파일
- ※ `home_profile/schema.py`·`carrier.py`·`storage.py`·`appliance_sim/` **무수정**

### Change Log

- 2026-07-23: Story 3.2 컨텍스트 생성(bmad-create-story). Epic 3 마지막 스토리 —
  이사 새 기기 집합 매핑(FR5). 핵심 신규 = `map_to_new_home`(device_type 매칭 +
  capability 교집합 + 손실 없는 보류 리포트). 복원(3.1)과 구분되는 매핑.
  H2 미검증 가설 표기. 베이스라인 323 passed. Status: ready-for-dev.
- 2026-07-23: Story 3.2 구현 완료 — map_to_new_home(매칭·보류 항등식·루틴 원자성·
  결정성·aliasing 격리), 데모·테스트 14개, DEMO_SCRIPT §8. Status: ready-for-dev → review.
