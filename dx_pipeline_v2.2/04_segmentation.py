# -*- coding: utf-8 -*-
"""
[DX 4단계] 타겟 세그먼트 분석 (설문 정형 데이터) (v2.8)
- K-Means 군집화 (엘보우 + 실루엣으로 최적 k 결정, k 상한을 표본 수에 맞춤)
- PCA 2차원 시각화
- v2.2: 분석 변수 명시적 화이트리스트(FEATURE_COLUMNS) + 스키마 검증
  (숫자형 자동 인식 폐지 — 응답자 ID·코드값이 군집 변수로 섞이는 사고 방지)
- v2.2: RF 변수중요도 → 세그먼트별 표준화 평균(z-score 프로파일)으로 교체
  (군집 라벨을 만든 데이터로 다시 중요도를 재는 순환 논리 제거)
실행: python 04_segmentation.py          (data/survey.csv 필요)
      python 04_segmentation.py --demo   (합성 샘플 300건 — 데모 전용)
출력: out/seg_elbow.png, out/seg_pca.png, out/seg_profile.csv, out/seg_zprofile.csv
"""
import sys
_enc = getattr(sys.stdout, "encoding", None)
if _enc and _enc.lower() != "utf-8" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # Windows cp949 콘솔 대응
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUT_DIR = BASE_DIR / "out"
OUT_DIR.mkdir(exist_ok=True)

plt.rcParams["font.family"] = ["Malgun Gothic", "AppleGothic", "NanumGothic", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# v2.2: 군집에 사용할 변수를 명시적으로 지정 — 설문의 ID/코드/타임스탬프가
# "숫자형"이라는 이유로 자동 포함되는 것을 차단. 설문 문항에 맞게 수정할 것.
FEATURE_COLUMNS = [
    "나이",
    "보유가전수",
    "앱사용빈도_주",
    "알림놓침빈도_주",
    "불편심각도_5점",
]

MIN_SAMPLES = 10  # 이 미만이면 군집 결과가 통계적으로 무의미


def make_sample_survey(n=300, seed=42) -> pd.DataFrame:
    """[데모 전용] 세 그룹을 의도적으로 심어둔 합성 설문 —
    이 데이터의 군집 결과는 '심어둔 그룹의 복원'이지 고객 발견이 아님."""
    rng = np.random.default_rng(seed)
    g = rng.choice([0, 1, 2], size=n, p=[0.4, 0.35, 0.25])
    df = pd.DataFrame({
        "나이": np.where(g == 0, rng.normal(32, 5, n), np.where(g == 1, rng.normal(58, 6, n), rng.normal(41, 7, n))).round(),
        "보유가전수": np.where(g == 0, rng.normal(6, 1.5, n), np.where(g == 1, rng.normal(3, 1, n), rng.normal(8, 2, n))).clip(1).round(),
        "앱사용빈도_주": np.where(g == 0, rng.normal(10, 3, n), np.where(g == 1, rng.normal(2, 1, n), rng.normal(15, 4, n))).clip(0).round(),
        "알림놓침빈도_주": np.where(g == 0, rng.normal(3, 1, n), np.where(g == 1, rng.normal(6, 2, n), rng.normal(1, 0.5, n))).clip(0).round(),
        "불편심각도_5점": np.where(g == 0, rng.normal(3.5, 0.6, n), np.where(g == 1, rng.normal(4.4, 0.4, n), rng.normal(2.2, 0.6, n))).clip(1, 5).round(1),
    })
    return df


def find_best_k(X, k_max=7):
    # v2.2: k 상한을 표본 수에 맞춤 (실루엣 계산에는 k <= n-1 필요)
    # v2.3: 고유 벡터 수도 반영 — 동일 응답뿐이면 실루엣 계산 자체가 불가
    n_unique = np.unique(X, axis=0).shape[0]
    if n_unique < 2:
        raise ValueError("서로 다른 응답 패턴이 2개 미만이라 군집화할 수 없습니다.")
    k_max = min(k_max, len(X) - 1, n_unique)
    if k_max < 2:
        raise ValueError(f"표본 {len(X)}건 — 군집화에 필요한 최소 표본이 부족합니다.")
    k_range = range(2, k_max + 1)

    inertias, silhouettes = [], []
    valid_ks = []
    for k in k_range:
        km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(X)
        n_labels = np.unique(km.labels_).size
        if n_labels < 2 or n_labels >= len(X):  # 실제 생성 군집 수 확인 (v2.3)
            continue
        valid_ks.append(k)
        inertias.append(km.inertia_)
        silhouettes.append(silhouette_score(X, km.labels_))
    if not valid_ks:
        raise ValueError("유효한 군집 수(k)를 찾지 못했습니다 — 데이터 다양성이 부족합니다.")
    k_range = valid_ks

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].plot(list(k_range), inertias, "o-"); axes[0].set_title("엘보우 (Inertia)"); axes[0].set_xlabel("k")
    axes[1].plot(list(k_range), silhouettes, "o-", color="orange"); axes[1].set_title("실루엣 점수"); axes[1].set_xlabel("k")
    fig.tight_layout(); fig.savefig(OUT_DIR / "seg_elbow.png", dpi=150)
    plt.close(fig)

    best_k = list(k_range)[int(np.argmax(silhouettes))]
    print(f"[OK] 실루엣 기준 최적 k = {best_k} (점수 {max(silhouettes):.3f})")
    return best_k


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true", help="합성 샘플 설문 사용 (데모 전용)")
    args = parser.parse_args()

    # 1) 데이터 로드
    survey_path = DATA_DIR / "survey.csv"
    if args.demo:
        df = make_sample_survey()
        print(f"[DEMO] 합성 설문 사용: {df.shape} — 군집 결과는 파이프라인 검증용")
    elif survey_path.exists():
        df = pd.read_csv(survey_path)
        print(f"[OK] 실제 설문 로드: {df.shape}")
    else:
        raise FileNotFoundError(
            "data/survey.csv 없음. 구글폼 응답을 저장하거나, 데모는 --demo 로 실행하세요.")

    # 2) 스키마 검증 (v2.2)
    missing = set(FEATURE_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"필수 컬럼 누락: {sorted(missing)} — FEATURE_COLUMNS를 설문에 맞게 수정하세요.")

    # NaN 처리 — 실제 설문엔 무응답이 반드시 존재 (StandardScaler는 NaN에서 에러)
    n_nan = int(df[FEATURE_COLUMNS].isna().sum().sum())
    if n_nan > 0:
        print(f"[WARN] 결측치 {n_nan}개 → 각 컬럼 중앙값으로 대체")
        df[FEATURE_COLUMNS] = df[FEATURE_COLUMNS].fillna(df[FEATURE_COLUMNS].median())
    df = df.reset_index(drop=True)

    if len(df) < MIN_SAMPLES:
        raise ValueError(f"응답 {len(df)}건 — 군집 분석 최소 {MIN_SAMPLES}건 미만.")

    scaler = StandardScaler()
    X = scaler.fit_transform(df[FEATURE_COLUMNS])

    # 3) 최적 k 탐색 → K-Means
    k = find_best_k(X)
    km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(X)
    df["segment"] = km.labels_

    # 4) PCA 2D 시각화
    p = PCA(n_components=2).fit_transform(X)
    plt.figure(figsize=(7, 6))
    for s in sorted(df["segment"].unique()):
        m = df["segment"] == s
        plt.scatter(p[m, 0], p[m, 1], label=f"세그먼트 {s} (n={m.sum()})", alpha=0.7)
    title = "고객 세그먼트 (PCA 2D)" + (" — DEMO 합성 데이터" if args.demo else "")
    plt.legend(); plt.title(title); plt.tight_layout()
    plt.savefig(OUT_DIR / "seg_pca.png", dpi=150)
    plt.close()

    # 5) 세그먼트 프로파일 (페르소나 근거표)
    profile = df.groupby("segment")[FEATURE_COLUMNS].mean().round(2)
    profile["비중(%)"] = (df["segment"].value_counts(normalize=True).sort_index() * 100).round(1)
    # v2.5: 산출물 자체에 데이터 출처 표기 (콘솔 경고만으로는 파일 단독 유통 시 위험)
    profile["데이터출처"] = "synthetic_demo" if args.demo else "survey"
    profile.to_csv(OUT_DIR / "seg_profile.csv", encoding="utf-8-sig")
    print("\n[세그먼트 프로파일(원 단위 평균)] → 이 표가 페르소나의 데이터 근거가 됨")
    print(profile)

    # 6) v2.2: 세그먼트별 표준화 평균(z-score) — "무엇이 이 세그먼트를 특징짓는가"
    #    (K-Means 라벨을 같은 X로 RF에 다시 학습시키는 순환 논리 대신, 직접 비교)
    z_df = pd.DataFrame(X, columns=FEATURE_COLUMNS)
    z_df["segment"] = df["segment"]
    z_profile = z_df.groupby("segment").mean().round(2)
    z_profile["데이터출처"] = "synthetic_demo" if args.demo else "survey"
    z_profile.to_csv(OUT_DIR / "seg_zprofile.csv", encoding="utf-8-sig")
    print("\n[세그먼트 z-score 프로파일] (|값|이 클수록 그 세그먼트의 구별 특징)")
    print(z_profile)

    print("\n저장 완료: out/seg_elbow.png, out/seg_pca.png, out/seg_profile.csv, out/seg_zprofile.csv")
