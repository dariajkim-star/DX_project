# DX 파이프라인 v2.8 — CX 보고서 데이터 분석 (1~6단계)

## ⚠️ 알려진 잔여 리스크 (수용됨 — 실데이터 운영 시 반드시 인지)

**1. Prompt injection: 완화책이지 결정적 방어가 아님**
리뷰 원문·에이전트 출력은 외부 신뢰 불가 데이터입니다. v2.8은 작업 지시를 system 메시지에,
데이터를 별도 user 메시지의 JSON 값으로 분리해 구분자 탈출(tag breakout)을 막았지만,
**LLM이 데이터 안 지시를 따를 가능성을 완전히 배제하지는 못합니다.**
- 악성 리뷰가 신뢰도 수치·인용문을 오염시킬 수 있으므로, 최종 보고서의 인용문과
  신뢰도는 사람이 원본 대조로 검수해야 합니다
- 에이전트 출력의 어떤 문장도 실행 가능한 명령으로 취급하지 마세요
- 앱 리뷰 소스를 바꾸면 악성 샘플 회귀 테스트를 다시 수행하세요

**2. A·C·D는 검색 도구 없이 생성됨 — 전부 미검증**
시장 규모·경쟁사 기능·트렌드 수치는 `(미검증 — 조사 필요)`로 강등되고 F 신뢰도는
`산출 불가`로 고정됩니다. 이 결과는 **리서치 질문·가설 생성용**으로만 쓰고,
외부 보고서의 사실 근거로 인용하지 마세요.

## v2.8 변경사항 (GPT 7차 교차검증 반영)

- **tag breakout 차단**: 인라인 `<UNTRUSTED_*>` 태그 → 지시(system)/데이터(user JSON) 메시지 분리. 데이터가 닫는 태그를 포함해도 경계를 깰 수 없음
- **`reviews_raw.csv`를 계보 게이트에 포함**: raw 실파일 해시·source_type 컬럼, 그리고 실수집 메타 일관성(app_id 존재, demo warning 부재, n_reviews=raw 행 수) 검증 — "메타는 google_play인데 raw는 synthetic_demo"인 모순 번들 차단
- **strengths 평점을 `sentiment_method`별로 검증**: rating_fallback은 4~5(그 모드에선 평점 3 이하가 pos일 수 없음), deep_learning은 1~5
- 잔여 리스크 문서화(위 절), `_FAILED.md`에 task 해시+payload 키 기록

## v2.7 변경사항 (GPT 6차 교차검증 반영 — orchestrator 중심)

- **Layer 2 격리**: A~D 출력을 `<UNTRUSTED_AGENT_OUTPUT>` 태그로 감싸 E/F에 전달 — B 인용문을 통한 injection 전파 경로 차단 (SYSTEM_PROMPT도 확장)
- **가설 모드 B 본문 분리**: 대표인용·강점 요구 자체를 제거하고 '미보고(실데이터 없음)' 지시 — 지시 충돌로 인한 가짜 인용 방지
- **게이트 검증 확장**: 두 언급률 모두 0~100, 빈도 정수 강제, strengths 행 내용(공백 리뷰·평점 1~5·좋아요 음수) 검증, 빈도 합=negative−noise, 언급률 재계산 일치(±0.1)
- **manifest 내구성**: 실행 시작 시 초기 저장 + try/finally — 중도 예외 시에도 gate_status=crashed·fatal_error 기록
- CLAUDE.md 종합점수 환산식 명시: (0.4E+0.35B)/0.75, F 축 미보고 병기

## v2.6 변경사항 (GPT 5차 교차검증 반영 — orchestrator 중심)

- **대표리뷰 필수 컬럼화**(누락·전부 공백 시 거부), **strengths.csv 필수 번들**(스키마·해시 검증, 0행이면 '강점 미보고' 강등)
- **prompt injection 방어**: system 메시지 분리 + 리뷰 데이터 `<UNTRUSTED_REVIEW_DATA>` 격리 (데이터 안 명령 무시 지시)
- **가설 모드 신뢰도 통제**: 게이트 실패 시 B·E는 '산출 불가(실데이터 없음)' 고정, F는 항상 '산출 불가(미검증 입력)' — CLAUDE.md에 종합점수 산출 규칙 명시
- painpoints 수치 범위(빈도≥1·평점 1~5·언급률 0~100)·메타 카운트 검증, preprocess source_type 일치 검증, None 포함 source_type 안전 처리(TypeError 제거), 폴백 번들 사용 시 경고
- **`run_manifest.json` 영속화**(data_mode·게이트 사유·에이전트별 상태) — Agent G가 별도 세션에서 복원
- import 부작용 제거(main()으로 이동), `_FAILED.md`에 예외 정보 기록(프롬프트는 해시+앞 500자만)

## v2.5 변경사항 (GPT 4차 교차검증 반영)

- **painpoints.csv에 `대표리뷰` 컬럼 추가 + `strengths.csv`(긍정 상위 10건) 신설** — Agent B가 대표 인용·강점을 지어내지 않도록 실데이터 전달 (해시 계보 포함)
- **orchestrator 게이트 보강**: painpoints.csv 스키마·데이터 행 존재 검사(0바이트/헤더-only 차단), run_id 필수값 검증(전부 None인 fail-open 봉인), metadata↔preprocess raw_csv_hash 연결 검증, 메타 JSON 최상위 객체 타입 검사
- **05 생산 시점 계보 검사 확대**: metadata.status·raw_csv_hash·source_type 불일치 시 산출물 생산 자체를 중단
- **06: 검증 실패 시 기존 priority_matrix/radar PNG 삭제**(잘못된 CX CSV에서도 잔존물 방지) + painpoints 수치 범위 검증(평점 1~5, 빈도≥1, 언급률 0~100, NaN/Inf)
- **A·C·D 프롬프트에 미검증 명시** — 검색 도구 없이 호출되므로 수치·기능 주장을 사실로 단정하지 않고 '조사 필요 항목' 목록화
- E/F 스킵 시 `E_SKIPPED.md`/`F_SKIPPED.md` 기록, run_id·실행 폴더 마이크로초 단위(동시 실행 충돌 방지), 04 데모 산출물에 `데이터출처` 컬럼·차트 표기, 최종 재시도 후 불필요한 대기 제거

## v2.4 변경사항 (GPT 3차 교차검증 반영)

- **계보 해시를 파일 바이트 전체 SHA-256으로 교체** — review 컬럼만 해싱하던 구멍(rating·tokens·source_type·출력 CSV 변조 미탐지) 봉인. 공통 유틸 `lineage.py`
- **체인 연결**: `metadata.json`(run_id·raw_csv_hash) → `preprocess_meta.json`(+clean_csv_hash) → `painpoints_meta.json`(+painpoints_csv_hash). 02·05는 이전 단계 메타의 run_id·해시를 검증한 뒤에만 진행 (과거 clean에 새 run_id가 붙는 사고 차단)
- **orchestrator 게이트 확장**: run_id 3자 일치 + clean/painpoints 실파일 해시 일치 + painpoints_meta·metadata source_type 일치. 경로 폴백은 완전한 번들(필수 5개 파일+계보 검증)만 채택. CSV 절단을 `csv.reader` 논리 행 기준으로 교체
- **02: metadata 부재/손상 시 중단** (계보 없는 raw는 신뢰하지 않음)
- **requirements에 `openai` 추가**, 문서 버전 동기화

## v2.3 변경사항 (GPT 2차 교차검증 반영)

- **실행 계보 end-to-end 연결**: `metadata.json`에 `run_id`·`status`, 05가 `painpoints_meta.json`(run_id·입력 문서 해시·감성/토픽 방식) 기록. orchestrator는 source_type + run_id 일치 + 입력 해시 일치의 3중 게이트를 통과할 때만 실데이터로 주입
- **수집 실패 시 잔존물 무효화**: 01 실패 시 `metadata.status=collect_failed` 기록 → 02가 과거 산출물 재사용 거부
- **레이더 스킵 시 기존 `radar_cx.png` 삭제** (잔존 데모 차트 방지) + CX 점수 스키마·1~5 범위 검증
- **임베딩 무결성 강화**: 손상 npy/json은 폴백(중단 아님), 모델명·row_count·차원·NaN/Inf 검증
- **LDA 대표 리뷰를 해당 토픽 배정 문서 내에서 선정** (타 토픽 문서가 대표로 뽑히는 버그 수정)
- **가드 보강**: 토큰화 후 최소 문서 수 재검사(+원자적 저장), 부정 리뷰 5건 미만 시 토픽 모델링 중단, 동일 응답 데이터 군집화 가드, 0바이트 painpoints.csv 명확한 에러, stdout reconfigure 안전화

리뷰·설문 데이터로 **타겟 세그먼트**와 **Pain Point**를 정량 도출하는 파이프라인입니다.

> ⚠️ **데이터 계보 원칙 (v2.2)**
> 샘플/합성 데이터 실행은 `--demo` 옵션으로만 가능하며, 그 산출물은
> **파이프라인 동작 검증용**입니다. 실제 고객·시장 분석 결과로 인용하지 마세요.
> 산출물 출처는 `data/metadata.json`(source_type)으로 확인할 수 있습니다.

## v2.2 변경사항 (v2.1 코드 리뷰 + GPT 교차검증 반영)

| # | 수정 | 대상 |
|---|------|------|
| 1 | 샘플/실데이터 계보 분리: `--demo` 명시적 옵션, 실수집 실패 시 중단, `metadata.json`·`source_type` 기록 | 01 |
| 2 | 임베딩 문서 해시(`emb_meta.json`) 검증 — 행 수만 같은 과거 임베딩 오사용 차단, SBERT 실패 시 기존 npy 삭제 | 03·05 |
| 3 | 레이더 차트 하드코딩 점수 제거 → `data/cx_scores.csv` 입력제, `--demo`는 워터마크 | 06 |
| 4 | 작은/빈 데이터 가드: 최소 문서 수, 동적 `min_df`, `k ≤ n-1`, 부정 0건·전량 노이즈 중단 | 02~06 |
| 5 | 설문 군집 변수 화이트리스트(`FEATURE_COLUMNS`) + 스키마 검증 (숫자형 자동 인식 폐지) | 04 |
| 6 | 감성 라벨 화이트리스트(`LABEL_MAP`) + `sentiment_method` 기록 | 05 |
| 7 | RF 변수중요도(순환 논리) → 세그먼트 z-score 프로파일로 교체 | 04 |
| 8 | 언급률 이중 표기(전체 부정 기준/배정 기준) + 노이즈율 출력, 대표 리뷰를 토픽 대표성 기준으로 선정 | 05 |
| 9 | LDA 토픽 수 데이터 크기 연동, pathlib 경로 고정, 버전 핀(scipy 명시), `plt.close`, '휴리스틱 우선순위' 명명 | 전체 |

## 설치

```bash
pip install -r requirements.txt
```

최소 실행만 원하면 (딥러닝 제외 — 자동 폴백으로 동작):
```bash
pip install pandas numpy scikit-learn scipy matplotlib kiwipiepy google-play-scraper
```

## 실행 순서

```bash
python 01_collect.py       # 리뷰 수집 (실패 시 중단; 데모는 --demo) → data/reviews_raw.csv
python 02_preprocess.py    # 정제 + Kiwi 형태소 분석 → data/reviews_clean.csv
python 03_embedding.py     # TF-IDF + Ko-SBERT 임베딩 + 해시 메타 → data/emb_*, emb_meta.json
python 04_segmentation.py  # K-Means 세그먼트 + PCA + z-프로파일 (데모는 --demo) → out/seg_*
python 05_painpoint.py     # 감성분석 + 토픽모델링 → data/painpoints.csv
python 06_visualize.py     # 우선순위 매트릭스 + 레이더(cx_scores.csv 필요) → out/*.png
```

**중요**: 02를 재실행했으면 03도 반드시 재실행하세요. (05가 해시로 검증해 불일치 시 임베딩을 무시합니다.)

## 실데이터 연결 방법

| 파일 | 교체 방법 |
|------|-----------|
| 01_collect.py | `APP_ID`를 분석할 앱 ID로 변경 (플레이스토어 URL의 `id=` 값) |
| 04_segmentation.py | 구글폼 응답을 `data/survey.csv`로 저장 + `FEATURE_COLUMNS`를 설문 문항에 맞게 수정 |
| 06_visualize.py | 팀 평가 점수를 `data/cx_scores.csv`로 저장 (형식은 06 파일 docstring 참고) |

## CX 보고서 연결

- `out/seg_profile.csv` / `out/seg_zprofile.csv` → 3장 페르소나의 **데이터 근거**
- `data/painpoints.csv` → 6장 Pain Point 표 (언급률 2종·평균평점)
- `out/priority_matrix.png` → 6.2장 우선순위 매트릭스
- `out/radar_cx.png` → 경쟁사 비교 정량 평가 (팀 평가 점수 입력 시에만 생성)
- 보고서 문구 예: *"부정 리뷰 N건을 BERTopic으로 분석한 결과, '알림 미인지'가 전체 부정 리뷰 기준 언급률 1위(XX%)로 나타남 (노이즈 제외율 YY%)"*
- **데모 산출물 사용 시 문서 상단에 반드시 명시**: *"본 산출물은 합성 샘플 데이터 기반 파이프라인 동작 검증 결과이며, 실제 고객·시장 분석 결과가 아님"*

## MoA 연동 주의 (moa_orchestrator v2.4)

`data/painpoints.csv`가 Agent B 프롬프트에 "실데이터"로 주입됩니다.
orchestrator는 다음 **전체 해시 체인**을 통과할 때만 주입합니다 (하나라도 실패 시 가설 모드 + 사유 출력):

1. `metadata.status == ok` && `source_type == google_play`
2. `painpoints_meta.source_type == metadata.source_type`
3. `metadata.run_id == preprocess_meta.run_id == painpoints_meta.run_id`
4. `reviews_clean.csv` 실파일 해시 == preprocess_meta·painpoints_meta의 `clean_csv_hash`
5. `painpoints.csv` 실파일 해시 == painpoints_meta의 `painpoints_csv_hash`

## 자동 폴백 구조

| 단계 | 기본(설치 시) | 폴백(미설치/실패 시) | 기록 |
|------|---------------|---------------------|------|
| 02 형태소 | Kiwi | 공백 분리 (품질 저하 경고) | 콘솔 |
| 03 임베딩 | Ko-SBERT + TF-IDF | TF-IDF만 (기존 npy 삭제) | emb_meta.json |
| 05 감성 | 딥러닝 (라벨 검증) | 평점 기반 (rating≤3=부정) | sentiment_method 컬럼 |
| 05 토픽 | BERTopic | LDA (토픽 수 자동 조정) | 콘솔 |

## 한글 폰트 참고

윈도우(Malgun Gothic)·맥(AppleGothic)은 자동 적용됩니다.
리눅스/코랩은 `sudo apt install fonts-nanum` 후 matplotlib 캐시 삭제.
