# -*- coding: utf-8 -*-
"""
[DX 5단계] Pain Point 도출 (감성 분석 + 토픽 모델링)
- 감성: 딥러닝 모델(가능 시) 또는 평점 기반(rating<=3) 폴백
- 토픽: BERTopic(가능 시) 또는 LDA 폴백
실행: python 05_painpoint.py
입력: data/reviews_clean.csv (+ data/emb_sbert.npy 있으면 활용)
출력: data/painpoints.csv, out/topic_freq.png
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

os.makedirs("out", exist_ok=True)
plt.rcParams["font.family"] = ["Malgun Gothic", "AppleGothic", "NanumGothic", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


# ---------- (1) 부정 리뷰 필터링 ----------
def filter_negative(df: pd.DataFrame) -> pd.DataFrame:
    """딥러닝 감성분석 시도 → 실패 시 평점 기반 폴백"""
    try:
        from transformers import pipeline
        clf = pipeline("sentiment-analysis",
                       model="matthewburke/korean_sentiment", truncation=True)
        preds = clf(df["review"].tolist(), batch_size=32)
        # LABEL_0=부정, LABEL_1=긍정 (matthewburke/korean_sentiment 기준)
        # v2.1 주의: 다른 모델로 교체 시 라벨 방향이 반대일 수 있음 → 아래 샘플 출력으로 반드시 확인
        df["sentiment"] = ["neg" if p["label"] == "LABEL_0" else "pos" for p in preds]
        print("[OK] 딥러닝 감성 분석 사용")
        print("[검증용 샘플] 아래 매핑이 상식과 맞는지 확인하세요:")
        for i in range(min(3, len(df))):
            print(f"  ({df['sentiment'].iloc[i]}) {df['review'].iloc[i][:30]}")
    except Exception as e:
        print(f"[WARN] 감성 모델 사용 불가({type(e).__name__}) → 평점 기반 폴백 (rating<=3 = 부정)")
        df["sentiment"] = np.where(df["rating"] <= 3, "neg", "pos")

    neg = df[df["sentiment"] == "neg"].copy()
    print(f"부정 리뷰: {len(neg)}건 / 전체 {len(df)}건 ({len(neg)/len(df)*100:.1f}%)")
    return neg


# ---------- (2) 토픽 모델링 ----------
def topics_bertopic(neg: pd.DataFrame):
    from bertopic import BERTopic
    embeddings = None
    if os.path.exists("data/emb_sbert.npy"):
        all_emb = np.load("data/emb_sbert.npy")
        # v2.1: 정합성 검증 — 02 재실행 후 03을 안 돌리면 임베딩이 다른 리뷰와 매칭됨
        if len(all_emb) == N_TOTAL_DOCS:
            embeddings = all_emb[neg.index.values]  # 부정 리뷰 위치의 임베딩만
        else:
            print(f"[WARN] 임베딩 수({len(all_emb)}) != 문서 수({N_TOTAL_DOCS}) → "
                  f"03_embedding.py를 재실행하세요. 이번엔 임베딩 없이 진행합니다.")
    tm = BERTopic(language="multilingual", min_topic_size=5, verbose=False)
    topics, _ = tm.fit_transform(neg["review"].tolist(), embeddings)
    neg["topic"] = topics
    info = tm.get_topic_info()
    labels = {row["Topic"]: row["Name"] for _, row in info.iterrows()}
    neg["topic_label"] = neg["topic"].map(labels)
    print("[OK] BERTopic 사용")
    return neg


def topics_lda(neg: pd.DataFrame, n_topics=5):
    """BERTopic 불가 시 폴백: TF-IDF + LDA"""
    from sklearn.feature_extraction.text import CountVectorizer
    from sklearn.decomposition import LatentDirichletAllocation
    vec = CountVectorizer(max_features=1000, min_df=2)
    X = vec.fit_transform(neg["tokens"].fillna(""))
    lda = LatentDirichletAllocation(n_components=n_topics, random_state=42).fit(X)
    neg["topic"] = lda.transform(X).argmax(axis=1)
    vocab = np.array(vec.get_feature_names_out())
    labels = {}
    print("[OK] LDA 폴백 사용 — 토픽별 대표 키워드:")
    print("[주의] 토픽 간 키워드가 많이 겹치면 데이터가 부족하다는 신호 → n_topics를 줄이거나 데이터 확충")
    for i, comp in enumerate(lda.components_):
        top_words = vocab[np.argsort(comp)[::-1][:4]]
        # v2.1: T{i}_ 접두어로 라벨 고유성 보장 — 데이터가 작으면 토픽 간 키워드가
        # 겹쳐 라벨이 동일해지고 groupby에서 서로 다른 토픽이 조용히 합쳐지는 버그 방지
        labels[i] = f"T{i}_" + "_".join(top_words)
        print(f"  토픽 {i}: {', '.join(top_words)}")
    neg["topic_label"] = neg["topic"].map(labels)
    return neg


if __name__ == "__main__":
    df = pd.read_csv("data/reviews_clean.csv")
    N_TOTAL_DOCS = len(df)  # v2.1: 임베딩 정합성 검증용

    neg = filter_negative(df)

    try:
        neg = topics_bertopic(neg)
    except Exception as e:
        print(f"[WARN] BERTopic 사용 불가({type(e).__name__}) → LDA 폴백")
        neg = topics_lda(neg)

    # ---------- (3) Pain Point 정량화 ----------
    neg = neg[neg["topic"] != -1]  # BERTopic 노이즈(-1) 제외
    pp = (neg.groupby("topic_label")
              .agg(빈도=("review", "size"), 평균평점=("rating", "mean"))
              .sort_values("빈도", ascending=False))
    pp["언급률(%)"] = (pp["빈도"] / len(neg) * 100).round(1)
    pp["평균평점"] = pp["평균평점"].round(2)
    pp.index.name = "PainPoint(토픽)"
    pp.to_csv("data/painpoints.csv", encoding="utf-8-sig")

    print("\n[Pain Point 순위] → CX 보고서 6장 표에 그대로 사용")
    print(pp)

    # 시각화
    pp.head(8)["언급률(%)"].iloc[::-1].plot(kind="barh", figsize=(8, 5), color="tomato")
    plt.title("부정 리뷰 토픽별 언급률 (%)"); plt.tight_layout()
    plt.savefig("out/topic_freq.png", dpi=150)

    # 토픽별 대표 리뷰 (보고서 인용용)
    print("\n[토픽별 대표 리뷰 예시]")
    for label, grp in neg.groupby("topic_label"):
        print(f"- {label}: \"{grp['review'].iloc[0][:50]}...\"")
    print("\n저장 완료: data/painpoints.csv, out/topic_freq.png")
