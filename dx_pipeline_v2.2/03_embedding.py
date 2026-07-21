# -*- coding: utf-8 -*-
"""
[DX 3단계] 벡터화 (임베딩) (v2.8)
- 방법 A: TF-IDF (가볍고 빠름, 해석 쉬움) — 키워드 분석용 독립 산출물
  ※ 05단계 LDA 폴백은 이 파일을 사용하지 않고 자체 CountVectorizer를 씀 (M1 명시)
- 방법 B: Ko-SBERT 딥러닝 임베딩 (의미 기반, BERTopic/군집에 유리)
- v2.2: 문서 해시 + 모델명을 emb_meta.json 에 기록 → 05단계에서 정합성 검증.
  SBERT 실패 시 기존 emb_sbert.npy 를 삭제해 오래된 임베딩 오사용 방지.
  min_df 를 문서 수에 따라 동적 조정 (작은 데이터 empty-vocabulary 방지).
실행: python 03_embedding.py
입력: data/reviews_clean.csv
출력: data/emb_tfidf.npz, data/emb_tfidf_vocab.json, data/emb_sbert.npy, data/emb_meta.json
"""
import sys
_enc = getattr(sys.stdout, "encoding", None)
if _enc and _enc.lower() != "utf-8" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # Windows cp949 콘솔 대응
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

from model_config import SBERT_MODEL  # v2.8: 모델 설정 단일 소스


def hash_documents(reviews) -> str:
    """리뷰 원문 전체의 SHA-256 — 임베딩과 리뷰 데이터의 정합성 검증용"""
    joined = "\n".join(str(r) for r in reviews)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def tfidf_embed(tokens_list):
    n_docs = len(tokens_list)
    min_df = 1 if n_docs < 20 else 2  # v2.2: 작은 데이터에서 empty vocabulary 방지
    vec = TfidfVectorizer(max_features=2000, min_df=min_df, ngram_range=(1, 2))
    X = vec.fit_transform(tokens_list)
    print(f"[OK] TF-IDF: {X.shape} (문서 x 단어, min_df={min_df})")
    scores = np.asarray(X.sum(axis=0)).ravel()
    top = np.argsort(scores)[::-1][:15]
    vocab = np.array(vec.get_feature_names_out())
    print("전체 상위 키워드:", ", ".join(vocab[top]))
    return X, vec


def sbert_embed(sentences):
    """Ko-SBERT. 최초 실행 시 모델(~400MB) 자동 다운로드.
    v2.2: ImportError 외 다운로드/네트워크 실패도 폴백 처리."""
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(SBERT_MODEL)
        emb = model.encode(sentences, show_progress_bar=True, batch_size=64)
        print(f"[OK] Ko-SBERT: {emb.shape} (문서 x 768차원)")
        return emb
    except ImportError:
        print("[WARN] sentence-transformers 미설치 → SBERT 생략 (TF-IDF만 사용)")
        return None
    except Exception as e:
        print(f"[WARN] SBERT 생성 실패({type(e).__name__}: {e}) → SBERT 생략")
        return None


if __name__ == "__main__":
    df = pd.read_csv(DATA_DIR / "reviews_clean.csv")
    if len(df) < 3:
        raise ValueError(f"문서 {len(df)}건 — 임베딩/분석에 필요한 최소 3건 미만.")

    doc_hash = hash_documents(df["review"])

    # A) TF-IDF (tokens 기반) — vocabulary 도 함께 저장해 재사용/해석 가능하게
    X_tfidf, vec = tfidf_embed(df["tokens"].fillna(""))
    sparse.save_npz(DATA_DIR / "emb_tfidf.npz", X_tfidf)
    with open(DATA_DIR / "emb_tfidf_vocab.json", "w", encoding="utf-8") as f:
        json.dump(vec.get_feature_names_out().tolist(), f, ensure_ascii=False)

    # B) Ko-SBERT (원문 기반 — 형태소 분석 없이 문장 의미를 그대로 인코딩)
    emb = sbert_embed(df["review"].tolist())
    sbert_path = DATA_DIR / "emb_sbert.npy"
    if emb is not None:
        np.save(sbert_path, emb)
    elif sbert_path.exists():
        # v2.2: 이번 실행에서 못 만들었으면 과거 임베딩은 무효 — 다른 리뷰와
        # 조용히 매칭되는 사고 방지를 위해 삭제
        sbert_path.unlink()
        print("[WARN] 기존 emb_sbert.npy 삭제 (현재 리뷰와의 정합성 보장 불가)")

    meta = {
        "document_hash": doc_hash,
        "row_count": len(df),
        "sbert_model": SBERT_MODEL if emb is not None else None,
        "sbert_available": emb is not None,
    }
    with open(DATA_DIR / "emb_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print("\n저장 완료: data/emb_tfidf.npz, data/emb_meta.json"
          + (", data/emb_sbert.npy" if emb is not None else ""))
