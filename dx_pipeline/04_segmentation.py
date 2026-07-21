# -*- coding: utf-8 -*-
"""
[DX 4단계] 타겟 세그먼트 분석 (설문 정형 데이터)
- K-Means 군집화 (엘보우 + 실루엣으로 최적 k 결정)
- PCA 2차원 시각화
- RandomForest로 "어떤 변수가 세그먼트를 가르는가" 해석 → 페르소나 근거
실행: python 04_segmentation.py
입력: data/survey.csv (없으면 샘플 자동 생성)
출력: out/seg_elbow.png, out/seg_pca.png, out/seg_profile.csv
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier

os.makedirs("out", exist_ok=True)
plt.rcParams["font.family"] = ["Malgun Gothic", "AppleGothic", "NanumGothic", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def make_sample_survey(n=300, seed=42) -> pd.DataFrame:
    """설문 샘플: 실제로는 구글폼 응답 CSV를 data/survey.csv 로 저장해서 사용"""
    rng = np.random.default_rng(seed)
    # 세 그룹을 의도적으로 심어둔 가상 데이터
    g = rng.choice([0, 1, 2], size=n, p=[0.4, 0.35, 0.25])
    df = pd.DataFrame({
        "나이": np.where(g == 0, rng.normal(32, 5, n), np.where(g == 1, rng.normal(58, 6, n), rng.normal(41, 7, n))).round(),
        "보유가전수": np.where(g == 0, rng.normal(6, 1.5, n), np.where(g == 1, rng.normal(3, 1, n), rng.normal(8, 2, n))).clip(1).round(),
        "앱사용빈도_주": np.where(g == 0, rng.normal(10, 3, n), np.where(g == 1, rng.normal(2, 1, n), rng.normal(15, 4, n))).clip(0).round(),
        "알림놓침빈도_주": np.where(g == 0, rng.normal(3, 1, n), np.where(g == 1, rng.normal(6, 2, n), rng.normal(1, 0.5, n))).clip(0).round(),
        "불편심각도_5점": np.where(g == 0, rng.normal(3.5, 0.6, n), np.where(g == 1, rng.normal(4.4, 0.4, n), rng.normal(2.2, 0.6, n))).clip(1, 5).round(1),
    })
    return df


def find_best_k(X, k_range=range(2, 8)):
    inertias, silhouettes = [], []
    for k in k_range:
        km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(X)
        inertias.append(km.inertia_)
        silhouettes.append(silhouette_score(X, km.labels_))

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].plot(list(k_range), inertias, "o-"); axes[0].set_title("엘보우 (Inertia)"); axes[0].set_xlabel("k")
    axes[1].plot(list(k_range), silhouettes, "o-", color="orange"); axes[1].set_title("실루엣 점수"); axes[1].set_xlabel("k")
    fig.tight_layout(); fig.savefig("out/seg_elbow.png", dpi=150)

    best_k = list(k_range)[int(np.argmax(silhouettes))]
    print(f"[OK] 실루엣 기준 최적 k = {best_k} (점수 {max(silhouettes):.3f})")
    return best_k


if __name__ == "__main__":
    # 1) 데이터 로드
    if os.path.exists("data/survey.csv"):
        df = pd.read_csv("data/survey.csv")
        print(f"[OK] 실제 설문 로드: {df.shape}")
    else:
        df = make_sample_survey()
        print(f"[WARN] data/survey.csv 없음 → 샘플 설문 생성: {df.shape}")

    num_cols = df.select_dtypes("number").columns.tolist()

    # v2.1: NaN 처리 — 실제 설문엔 무응답이 반드시 존재 (StandardScaler는 NaN에서 에러)
    n_nan = int(df[num_cols].isna().sum().sum())
    if n_nan > 0:
        print(f"[WARN] 결측치 {n_nan}개 → 각 컬럼 중앙값으로 대체")
        df[num_cols] = df[num_cols].fillna(df[num_cols].median())
    df = df.dropna(subset=num_cols).reset_index(drop=True)

    X = StandardScaler().fit_transform(df[num_cols])

    # 2) 최적 k 탐색 → K-Means
    k = find_best_k(X)
    km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(X)
    df["segment"] = km.labels_

    # 3) PCA 2D 시각화
    p = PCA(n_components=2).fit_transform(X)
    plt.figure(figsize=(7, 6))
    for s in sorted(df["segment"].unique()):
        m = df["segment"] == s
        plt.scatter(p[m, 0], p[m, 1], label=f"세그먼트 {s} (n={m.sum()})", alpha=0.7)
    plt.legend(); plt.title("고객 세그먼트 (PCA 2D)"); plt.tight_layout()
    plt.savefig("out/seg_pca.png", dpi=150)

    # 4) 세그먼트 프로파일 (페르소나 근거표)
    profile = df.groupby("segment")[num_cols].mean().round(2)
    profile["비중(%)"] = (df["segment"].value_counts(normalize=True).sort_index() * 100).round(1)
    profile.to_csv("out/seg_profile.csv", encoding="utf-8-sig")
    print("\n[세그먼트 프로파일] → 이 표가 페르소나의 데이터 근거가 됨")
    print(profile)

    # 5) RandomForest 변수 중요도: 무엇이 세그먼트를 가르는가
    rf = RandomForestClassifier(n_estimators=300, random_state=42).fit(X, df["segment"])
    imp = pd.Series(rf.feature_importances_, index=num_cols).sort_values(ascending=False)
    print("\n[세그먼트 구분 변수 중요도]")
    print(imp.round(3))
    print("\n저장 완료: out/seg_elbow.png, out/seg_pca.png, out/seg_profile.csv")
