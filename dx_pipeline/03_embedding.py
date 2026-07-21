# -*- coding: utf-8 -*-
"""
[DX 3단계] 벡터화 (임베딩)
- 방법 A: TF-IDF (가볍고 빠름, 해석 쉬움)
- 방법 B: Ko-SBERT 딥러닝 임베딩 (의미 기반, BERTopic/군집에 유리)
실행: python 03_embedding.py
입력: data/reviews_clean.csv
출력: data/emb_tfidf.npz, data/emb_sbert.npy
"""
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer


def tfidf_embed(tokens_list):
    vec = TfidfVectorizer(max_features=2000, min_df=2, ngram_range=(1, 2))
    X = vec.fit_transform(tokens_list)
    print(f"[OK] TF-IDF: {X.shape} (문서 x 단어)")
    # 상위 키워드 미리보기
    scores = np.asarray(X.sum(axis=0)).ravel()
    top = np.argsort(scores)[::-1][:15]
    vocab = np.array(vec.get_feature_names_out())
    print("전체 상위 키워드:", ", ".join(vocab[top]))
    return X, vec


def sbert_embed(sentences):
    """Ko-SBERT. 최초 실행 시 모델(~400MB) 자동 다운로드."""
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("jhgan/ko-sroberta-multitask")
        emb = model.encode(sentences, show_progress_bar=True, batch_size=64)
        print(f"[OK] Ko-SBERT: {emb.shape} (문서 x 768차원)")
        return emb
    except ImportError:
        print("[WARN] sentence-transformers 미설치 → SBERT 생략 (TF-IDF만 사용)")
        return None


if __name__ == "__main__":
    df = pd.read_csv("data/reviews_clean.csv")

    # A) TF-IDF (tokens 기반)
    X_tfidf, _ = tfidf_embed(df["tokens"].fillna(""))
    sparse.save_npz("data/emb_tfidf.npz", X_tfidf)

    # B) Ko-SBERT (원문 기반 — 형태소 분석 없이 문장 의미를 그대로 인코딩)
    emb = sbert_embed(df["review"].tolist())
    if emb is not None:
        np.save("data/emb_sbert.npy", emb)

    print("\n저장 완료: data/emb_tfidf.npz" + (", data/emb_sbert.npy" if emb is not None else ""))
