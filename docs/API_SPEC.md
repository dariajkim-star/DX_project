# API 명세서 — DX 파이프라인 v2.8 + MoA 오케스트레이터

이 프로젝트의 "API"는 HTTP 엔드포인트가 아니라 **① CLI 스크립트 계약 ② 파일(데이터·메타) 계약 ③ 파이썬 함수 계약** 세 층입니다. 단계 간 결합은 전부 파일로 이루어지므로, 파일 계약이 사실상의 인터페이스입니다.

---

## 1. CLI 스크립트 계약

모든 스크립트는 `dx_pipeline_v2.2/`에서 실행하며, 성공 시 exit 0, 계약 위반 시 예외와 함께 exit ≠ 0.

| 스크립트 | 옵션 | 입력 | 출력 | 실패 조건(주요) |
|---|---|---|---|---|
| `01_collect.py` | `--demo` | (플레이스토어 API) | `data/reviews_raw.csv`, `data/metadata.json` | 실수집 실패 시 중단 + `metadata.status=collect_failed` 기록 |
| `02_preprocess.py` | — | reviews_raw.csv, metadata.json | `data/reviews_clean.csv`, `data/preprocess_meta.json` | metadata 부재/손상/`status≠ok`/raw 해시 불일치, 정제·토큰화 후 문서 <3건 |
| `03_embedding.py` | — | reviews_clean.csv | `data/emb_tfidf.npz`, `emb_tfidf_vocab.json`, `emb_sbert.npy`(선택), `emb_meta.json` | 문서 <3건. SBERT 실패는 폴백(기존 npy 삭제) |
| `04_segmentation.py` | `--demo` | `data/survey.csv` | `out/seg_elbow.png`, `seg_pca.png`, `seg_profile.csv`, `seg_zprofile.csv` | survey 부재(비데모), FEATURE_COLUMNS 누락, 표본 <10, 고유 응답 <2 |
| `05_painpoint.py` | — | reviews_clean.csv + 메타 체인 | `data/painpoints.csv`, `strengths.csv`, `painpoints_meta.json`, `out/topic_freq.png` | 계보 검증 실패(run_id/해시/status/source_type), 부정 리뷰 <5건, 전량 노이즈 |
| `06_visualize.py` | `--demo` | painpoints.csv, `data/cx_scores.csv`(선택) | `out/priority_matrix.png`, `radar_cx.png` | painpoints 수치 범위 위반, cx_scores 스키마/1~5 범위 위반. **실패 시 해당 PNG 삭제** |
| `moa_orchestrator.py` | — | data/ 번들 전체 | `out_moa/<ts>/A~F.md`, `*_FAILED.md`, `*_SKIPPED.md`, `run_manifest.json` | `OPENAI_API_KEY` 부재. 게이트 실패는 중단이 아니라 **가설 모드 강등** |
| `07_wordcloud_sentiment.py` | `--keyword`, `--top` | reviews_raw.csv (+네이버 API 키 시 키워드 수집) | `out/wordcloud_neg.png`, `sentiment_dist.png`, `data/wordcloud_freq.csv`, `keyword_lge.csv` | reviews_raw 부재 |
| `crawl_playstore.py` | `--app-id`, `--alias`, `--max` | (플레이스토어 공개 API) | `data/crawl_playstore_<별칭>.csv` + `_manifest.json` (SHA-256 포함), 2,000건마다 체크포인트 | — (토큰 소진 시 조기 종료 = 전량) |
| `crawl_naver.py` | `--per-query` | (네이버 검색 오픈 API) | `data/crawl_naver.csv`, `crawl_naver_yield.csv`(축별 유효율), `crawl_naver_manifest.json` | `NAVER_CLIENT_ID/SECRET` 환경변수 부재 |
| `crawl_smartthings.py` | `--max` | crawl_playstore.run() 재사용 | `data/crawl_playstore_smartthings.csv` + `_manifest.json` | — |
| `compare_competitor.py` | — | crawl_playstore_thinq.csv + _smartthings.csv | `out/compare_rating_trend.png`, `compare_summary.csv` | 두 crawl CSV 부재 |

`--demo` 공통 의미: 합성 데이터 사용을 **명시적으로** 허용. 산출물에 synthetic 표기가 남는다(계보·컬럼·워터마크).

---

## 2. 파일 계약

### 2.1 데이터 파일

**`data/reviews_raw.csv`** — 01 출력
| 컬럼 | 타입 | 설명 |
|---|---|---|
| review | str | 리뷰 원문 |
| rating | int 1~5 | 평점 |
| date | datetime | 작성일 |
| likes | int ≥0 | 좋아요 수 |
| source_type | `google_play` \| `synthetic_demo` | 데이터 출처 (전 행 동일) |

**`data/reviews_clean.csv`** — 02 출력. raw 컬럼 + `tokens`(str, 공백 구분 형태소). RangeIndex 확정 상태(임베딩 행 매칭 기준).

**`data/painpoints.csv`** — 05 출력 (orchestrator 게이트의 필수 스키마)
| 컬럼 | 타입/범위 | 비고 |
|---|---|---|
| PainPoint(토픽) | str | LDA는 `T{i}_` 접두어로 고유성 보장 |
| 빈도 | int ≥1 | 정수 강제 |
| 평균평점 | float 1~5 | |
| 언급률_전체부정기준(%) | float 0~100 | = 빈도/negative_count×100 (±0.1 재계산 검증) |
| 언급률_배정기준(%) | float 0~100 | 노이즈 제외 분모 |
| 대표리뷰 | str, 공백 금지 | 해당 토픽 배정 문서 중 확률 최대 (≤100자) |

**`data/strengths.csv`** — 05 출력. `대표리뷰`(공백 금지) / `평점`(sentiment_method별: rating_fallback→4~5, deep_learning→1~5) / `좋아요`(int ≥0). 0행 허용(→ 강점 미보고).

**`data/survey.csv`** — 사용자 제공. `FEATURE_COLUMNS`(04 상단 정의)의 숫자형 컬럼 필수.

**`data/cx_scores.csv`** — 사용자 제공. 첫 컬럼 이름 + 평가 축 정확히 5개, 값 1~5.

### 2.2 메타(계보) 파일 — lineage 체인

```
metadata.json ──run_id, raw_csv_hash──▶ preprocess_meta.json ──run_id, clean_csv_hash──▶ painpoints_meta.json
```

**`metadata.json`** (01)
```json
{
  "status": "ok | collect_failed",
  "run_id": "YYYYMMDD_HHMMSS_ffffff",
  "raw_csv_hash": "sha256(reviews_raw.csv 바이트)",
  "source_type": "google_play | synthetic_demo",
  "app_id": "실수집 시 필수, 데모는 null",
  "collected_at": "ISO8601", "n_reviews": 45,
  "warning": "데모일 때만 존재, 실수집은 null"
}
```

**`preprocess_meta.json`** (02): `run_id`, `source_type`, `raw_csv_hash`(승계), `clean_csv_hash`

**`painpoints_meta.json`** (05): `run_id`, `source_type`, `clean_csv_hash`(승계), `painpoints_csv_hash`, `strengths_csv_hash`, `sentiment_method`(`deep_learning|rating_fallback`), `topic_method`(`bertopic|lda`), `negative_count`(≥1), `noise_count`(0≤n≤negative)

**`emb_meta.json`** (03): `document_hash`(review 컬럼 SHA-256), `row_count`, `sbert_model`, `sbert_available` — 05가 임베딩 사용 전 검증. 체인과 별도의 로컬 계약.

**`out_moa/<ts>/run_manifest.json`** (orchestrator) — Agent G의 실행 상태 복원 기준
```json
{
  "data_mode": "real | hypothesis | null",
  "data_dir": "...", "source_type": "...", "run_id": "...",
  "gate_status": "running | passed | failed | crashed",
  "gate_failures": ["거부 사유..."],
  "fatal_error": {"type": "...", "message": "..."},
  "agents": {"A": "success | failed | skipped | not_run", "...": "..."},
  "created_at": "ISO8601"
}
```

### 2.3 orchestrator 계보 게이트 (`_validate_bundle`)

`data/` 번들이 **전부** 통과해야 실데이터 모드. 하나라도 실패 시 사유와 함께 가설 모드.

1. 필수 7파일 존재: reviews_raw/clean, painpoints, strengths, metadata, preprocess_meta, painpoints_meta
2. 메타 3종: 유효 JSON + 최상위 객체 + `run_id` 3자 존재·일치
3. `metadata.status == ok`, `source_type == google_play` (메타 3종 일치)
4. 실수집 일관성: `app_id` 존재, `warning` 부재, `n_reviews` == raw 행 수
5. 파일 해시: raw·clean·painpoints·strengths 실파일 SHA-256 == 메타 기록
6. 데이터 컬럼: raw·clean의 `source_type` 전 행 `google_play`
7. painpoints 스키마·수치 범위·`대표리뷰` 비공백, strengths 행 내용
8. 의미 정합성: Σ빈도 == negative−noise, 언급률 재계산 일치(±0.1)

---

## 3. 파이썬 함수 계약 (moa_orchestrator)

```python
load_dx_data() -> dict
# {"data_mode": "real"|"hypothesis", "instructions": str, "payload": dict|None,
#  "gate_failures": [str], "data_dir": str|None, "run_id": str|None, "source_type": str|None}
# 예외를 던지지 않음 — 모든 실패는 hypothesis 모드로 강등

build_layer1(dx) -> {"A"|"B"|"C"|"D": (task: str, payload: dict|None)}
build_layer2(r: {agent: str}, dx) -> {"E"|"F": (task, payload)}   # 입력 결측 시 해당 키 없음

build_messages(task, payload) -> [{"role": "system", ...}, {"role": "user", ...}]
# 보안 규칙+작업 지시는 system, 외부 데이터는 user의 JSON 문자열.
# payload는 json.dumps로 직렬화 — 데이터 내 태그/구분자가 지시 영역으로 탈출 불가

call_gpt(name, task, payload=None) -> str
# 재시도(지수 백오프, 마지막 시도 후 대기 없음). 성공: RUN_DIR/{name}.md 저장 후 본문 반환.
# 최종 실패: {name}_FAILED.md(예외 정보+task 해시) 기록 후 "" 반환 — 예외 전파 없음

main()  # 유일한 부작용 진입점: API 키 검사, client·RUN_DIR 초기화, manifest 저장
```

`lineage.py`: `file_sha256(path)`, `load_json/save_json`, `require_meta(path, what)`(부재/손상 시 raise), `verify_hash(file, expected, what)`(불일치 시 raise).

---

## 4. 환경 계약

- Python 3.10+ (개발·검증: 3.12, Windows)
- `OPENAI_API_KEY` 환경변수 — orchestrator 전용, 코드·파일에 저장 금지
- 의존성: `dx_pipeline_v2.2/requirements.txt` (딥러닝 스택은 선택 — 부재 시 자동 폴백)
- 콘솔 인코딩: cp949에서도 동작 (stdout reconfigure, `reconfigure` 부재 환경 안전)
