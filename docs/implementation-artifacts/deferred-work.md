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

## Epic 5 Docker 실증 — ✅ 완료 (2026-07-29 재부팅 후)

- **실증 완료**: 재부팅(07-29 14:45) → engine 29.5.3 기동 → DB healthy →
  `load_mart.py` 6/6 테이블 적재(reviews 12,585 / painpoints 15 / strengths 10 /
  competitor 24,805 / segments 300 / naver_testimony 3,923) → `queries.sql`
  Q1~Q5 전부 실행 성공. 테스트 426 passed.
- **병리 최종 기록 (사후 부검)**: 재부팅만으로는 불충분했다 — 좀비 소켓
  `run/dockerInference`(`?????????` 속성, Error 1920)는 **재부팅을 살아넘었고**
  첫 기동이 같은 remove 단계에서 재사망. 실제 치료는 **재부팅 + 감염 `run` 폴더
  재격리(`run_stale2`)의 조합**: 재부팅으로 커널 상태가 리셋된 뒤에는 새로 만든
  소켓이 재감염되지 않았다(07-28에는 격리 즉시 재감염 — 이 차이가 진단 근거).
- 수정 1건: `load_mart.py`가 seg_members.csv의 pandas 유래 "1.0" 문자열을
  smallint로 캐스팅하도록 `_i()` 헬퍼 추가 (경계 테스트 회귀 0).
- DB 비밀번호는 세션 로컬 랜덤값 — `%LOCALAPPDATA%/Temp/onme_db_pw.txt`에만 존재,
  저장소 미기록(회의 §7-3). `down -v` 후 재기동 시 새로 정하면 된다.
- **잔여**: 격리 폴더 3개(`Docker/run_stale`·`run_stale2`·
  `docker-secrets-engine_stale`)는 좀비 소켓 파일 때문에 재부팅 후에도 삭제 불가
  (수 KB, 무해). 다음 재부팅 직후(Docker 시작 전) 삭제 재시도 — 그때도 안 되면
  방치 확정.
