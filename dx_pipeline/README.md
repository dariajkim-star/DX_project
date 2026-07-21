# DX 파이프라인 — CX 보고서 데이터 분석 (1~6단계)

리뷰·설문 데이터로 **타겟 세그먼트**와 **Pain Point**를 정량 도출하는 파이프라인입니다.
모든 스크립트는 실데이터가 없어도 **샘플 데이터로 즉시 실행**되며,
무거운 라이브러리(SBERT, BERTopic 등)가 없으면 **자동으로 가벼운 기법으로 폴백**합니다.

## 설치

```bash
pip install -r requirements.txt
```

최소 실행만 원하면 (딥러닝 제외):
```bash
pip install pandas numpy scikit-learn scipy matplotlib kiwipiepy google-play-scraper
```

## 실행 순서

```bash
python 01_collect.py       # 리뷰 수집 (플레이스토어) → data/reviews_raw.csv
python 02_preprocess.py    # 정제 + Kiwi 형태소 분석 → data/reviews_clean.csv
python 03_embedding.py     # TF-IDF + Ko-SBERT 임베딩 → data/emb_*.npz/npy
python 04_segmentation.py  # K-Means 세그먼트 + PCA + RF 중요도 → out/seg_*.png
python 05_painpoint.py     # 감성분석 + 토픽모델링 → data/painpoints.csv
python 06_visualize.py     # 우선순위 매트릭스 + 레이더 차트 → out/*.png
```

## 실데이터 연결 방법

| 파일 | 교체 방법 |
|------|-----------|
| 01_collect.py | `APP_ID`를 분석할 앱 ID로 변경 (플레이스토어 URL의 `id=` 값) |
| 04_segmentation.py | 구글폼 설문 응답을 `data/survey.csv`로 저장 (숫자형 컬럼 자동 인식) |
| 06_visualize.py | `radar_chart()`의 점수를 팀 평가 점수(1~5)로 교체 |

## CX 보고서 연결

- `out/seg_profile.csv` → 3장 페르소나의 **데이터 근거**
- `data/painpoints.csv` → 6장 Pain Point 표 (언급률·평균평점)
- `out/priority_matrix.png` → 6.2장 우선순위 매트릭스
- `out/radar_cx.png` → 경쟁사 비교 정량 평가
- 보고서 문구 예: *"부정 리뷰 N건을 BERTopic으로 분석한 결과, '알림 미인지'가 언급률 1위(XX%)로 나타남"*

## 자동 폴백 구조

| 단계 | 기본(설치 시) | 폴백(미설치 시) |
|------|---------------|-----------------|
| 02 형태소 | Kiwi | 공백 분리 |
| 03 임베딩 | Ko-SBERT + TF-IDF | TF-IDF만 |
| 05 감성 | KoELECTRA 계열 딥러닝 | 평점 기반 (rating≤3=부정) |
| 05 토픽 | BERTopic | LDA |

## 한글 폰트 참고

윈도우(Malgun Gothic)·맥(AppleGothic)은 자동 적용됩니다.
리눅스/코랩은 `sudo apt install fonts-nanum` 후 matplotlib 캐시 삭제.
