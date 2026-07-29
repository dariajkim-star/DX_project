# 이월 작업 (Deferred Work)

code-review에서 실재하나 지금 조치하지 않기로 한 항목. 후속 스토리·리팩터에서 재검토.

## Deferred from: code review of 3-1-reinstall-restore (2026-07-23)

- **`merge_chunks` 반환이 입력 조각을 참조로 물고 나온다(aliasing)** —
  `home_profile/storage.py` `merge_chunks`. 반환 프로필의 중첩 객체(routines·
  settings)가 입력 `chunks`(및 `split_chunks` 경로에선 원본 프로필)와 참조를
  공유한다. 캐리어 복원(주 경로)은 JSON 재역직렬화로 신선한 객체를 만들어
  무해하고, `split_chunks` 자체도 이미 동일한 얕은 복사 특성을 가진다.
  직접 `merge_chunks(split_chunks(x))` 반환값을 "독립 소유물"로 다루며 중첩을
  변형하는 호출자만 영향. 수정 시 반환 직전 deepcopy(비용 발생)로 격리 가능.
  값 동등(`==`) 테스트로는 드러나지 않음. blind 리뷰 Med.

## Deferred from: spec-demo-presentation-layer (2026-07-28)

- **`demo_routine.py`의 demo_ui 이관** — 7개 발표 장면(demo_night 외 6종)은
  `demo_ui.py` 프레젠테이션 층으로 치환됐으나 `demo_routine.py`는 스펙 범위 밖
  (frozen Boundaries의 Never 항목)으로 로컬 `_emit` 출력이 남아 있다.
  후속 작업에서 동일한 방식(출력 계층만 교체·로직/rc 불변·기존 테스트 토큰 보존)
  으로 이관할 것.

## Deferred from: code review of spec-demo-presentation-layer (2026-07-28)

- **demo_night 전이 판정의 소급 구조** — `_NIGHT_ACTIONS`에 같은 (ref, key) 쌍이
  두 번 들어가면 앞선 액션이 실제 적용됐어도 최종 스냅샷 비교로 거짓 blocked가
  뜬다. 현 데이터(4액션, 중복 없음)에선 무해. 액션별 즉시 판정으로 바꾸려면
  execute_routine 이벤트 스트림과의 대조가 필요. blind 리뷰 Med.
- **전각/반각 혼합 폭 정렬** — boundary_table 라벨 패딩·title_block 62열 괘선이
  한글 전각 폭에서 어긋날 수 있음. 프로젝터 리허설(폰트 실측)과 함께 조정.
  blind 리뷰 Low.

## Epic 5 Docker 실증 — 재부팅 대기 (2026-07-28)

- 코드는 완성(0b36e67): compose·schema·load_mart·queries·경계 테스트 5 passed
- Docker Desktop 4.79.0 기동 실패 — **좀비 유닉스 소켓 병리**: 앱이 만드는 소켓
  파일(dockerInference·engine.sock)이 생성 직후 삭제 불가(`?????????` 속성)가 되어
  다음 기동의 remove 단계에서 사망. `run`·`docker-secrets-engine` 디렉터리를
  `*_stale`로 격리해도 새 소켓이 즉시 재감염 — 시스템 수준.
- **처방: Windows 재부팅**(좀비 AF_UNIX 엔트리는 재부팅으로 소멸) 후
  `ONME_DB_PASSWORD=<로컬비번> docker compose -f db/compose.yml up -d` →
  `python db/load_mart.py` → `db/queries.sql` 실증.
- WSL2 자체는 정상(docker-desktop 배포판 등록 확인). 회의록의 "WSL2 미확인"
  리스크는 해소 — 병은 다른 곳에 있었다.
- 격리 디렉터리 2개(`Docker/run_stale`·`docker-secrets-engine_stale`)는 재부팅 후
  삭제 가능해지면 정리.
