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
# "숫자형"이라는 이유로 자동 포함되는 것을 차단.
# v3: SURVEY_PLAN §3 확정 목록. 정의와 인코딩은 survey_encode.py 한 곳에만 둔다
# (두 벌로 나뉘면 "몇 점으로 봤는지"가 조용히 어긋난다).
from survey_encode import FEATURE_COLUMNS  # noqa: E402

MIN_SAMPLES = 10  # 이 미만이면 군집 결과가 통계적으로 무의미


def make_sample_survey(n=300, seed=42) -> pd.DataFrame:
    """[데모 전용] 세 그룹을 의도적으로 심어둔 합성 설문 —
    이 데이터의 군집 결과는 '심어둔 그룹의 복원'이지 고객 발견이 아님.

    v3: 모집 설계(SURVEY_PLAN §1)의 G1/G2/G3를 흉내 낸다.
      g0 = Night Keeper 후보(유자녀·야간사용↑·Pain↑)
      g1 = 떠날 사람 후보(전월세·이사계획·혼수 구매)
      g2 = 대조군(Pain↓·수용도↓)
    """
    rng = np.random.default_rng(seed)
    g = rng.choice([0, 1, 2], size=n, p=[0.4, 0.35, 0.25])

    def pick(a, b, c):
        return np.where(g == 0, a, np.where(g == 1, b, c))

    def scale(mu_a, mu_b, mu_c, sd=0.8):
        return pick(rng.normal(mu_a, sd, n), rng.normal(mu_b, sd, n),
                    rng.normal(mu_c, sd, n)).clip(1, 5).round()

    df = pd.DataFrame({
        "LG가전수": pick(rng.normal(2.6, 0.5, n), rng.normal(1.8, 0.6, n),
                       rng.normal(1.5, 0.6, n)).clip(1, 3).round(),
        "앱사용빈도": pick(rng.normal(3.4, 0.6, n), rng.normal(2.2, 0.8, n),
                       rng.normal(1.6, 0.8, n)).clip(0, 4).round(),
        "연령대": pick(rng.normal(2.4, 0.6, n), rng.normal(2.0, 0.5, n),
                     rng.normal(3.0, 1.0, n)).clip(1, 5).round(),
        "자녀유무": pick(rng.random(n) < 0.85, rng.random(n) < 0.15,
                      rng.random(n) < 0.30).astype(int),
        "점유형태_전월세": pick(rng.random(n) < 0.35, rng.random(n) < 0.90,
                           rng.random(n) < 0.40).astype(float),
        "이사계획": pick(rng.choice([0, 0.5, 1], n, p=[.6, .25, .15]),
                      rng.choice([0, 0.5, 1], n, p=[.1, .2, .7]),
                      rng.choice([0, 0.5, 1], n, p=[.5, .3, .2])),
        "구매계기_혼수": pick(rng.random(n) < 0.30, rng.random(n) < 0.70,
                          rng.random(n) < 0.20).astype(int),
        "P1경험": scale(4.2, 3.0, 2.0),
        "P2경험": scale(4.0, 3.4, 1.9),
        "P3부담": scale(3.6, 3.0, 2.2),
        "워치보유": pick(rng.random(n) < 0.55, rng.random(n) < 0.45,
                      rng.random(n) < 0.35).astype(int),
        "야간사용": scale(4.4, 2.6, 1.8),
        "온바디수용도": scale(4.3, 3.6, 2.1),
        "지불의사": pick(rng.choice([0, 1, 2], n, p=[.2, .4, .4]),
                      rng.choice([0, 1, 2], n, p=[.3, .5, .2]),
                      rng.choice([0, 1, 2], n, p=[.7, .25, .05])),
    })
    return df[FEATURE_COLUMNS]


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
