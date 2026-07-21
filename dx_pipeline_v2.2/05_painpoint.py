# -*- coding: utf-8 -*-
"""
[DX 5단계] Pain Point 도출 (감성 분석 + 토픽 모델링) (v2.8)
- 감성: 딥러닝 모델(가능 시) 또는 평점 기반(rating<=3) 폴백 — 사용된 방식을
  sentiment_method 로 기록 (v2.2)
- 토픽: BERTopic(가능 시) 또는 LDA 폴백
- v2.2 주요 수정:
  * 감성 라벨 화이트리스트 검증 (알 수 없는 라벨 → 평점 폴백, 조용한 오분류 방지)
  * 임베딩 사용 전 문서 해시 검증 (emb_meta.json) — 행 수만 같은 다른 데이터 차단
  * 언급률을 이중 표기: 전체 부정 리뷰 기준 / 토픽 배정 리뷰 기준 (+노이즈율)
  * 대표 리뷰 = 토픽 확률 최대 문서(LDA) / get_representative_docs(BERTopic)
  * LDA 토픽 수를 문서 수에 맞게 조정, min_df 동적, 빈 데이터 가드
실행: python 05_painpoint.py
입력: data/reviews_clean.csv (+ data/emb_sbert.npy, data/emb_meta.json 있으면 활용)
출력: data/painpoints.csv, out/topic_freq.png
"""
import sys
_enc = getattr(sys.stdout, "encoding", None)
if _enc and _enc.lower() != "utf-8" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # Windows cp949 콘솔 대응
import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUT_DIR = BASE_DIR / "out"
OUT_DIR.mkdir(exist_ok=True)

plt.rcParams["font.family"] = ["Malgun Gothic", "AppleGothic", "NanumGothic", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# v2.8: 모델·라벨 설정은 model_config 단일 소스에서
from model_config import LABEL_MAP, SENTIMENT_MODEL, SBERT_MODEL as EXPECTED_SBERT_MODEL


def hash_documents(reviews) -> str:
    import hashlib
    joined = "\n".join(str(r) for r in reviews)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


# ---------- (1) 부정 리뷰 필터링 ----------
def filter_negative(df: pd.DataFrame) -> pd.DataFrame:
    """딥러닝 감성분석 시도 → 실패/라벨 불일치 시 평점 기반 폴백.
    사용된 방식을 sentiment_method 컬럼에 기록."""
    method = "rating_fallback"
    try:
        from transformers import pipeline
        clf = pipeline("sentiment-analysis",
                       model=SENTIMENT_MODEL, truncation=True)
        preds = clf(df["review"].astype(str).tolist(), batch_size=32)
        unknown = {p["label"] for p in preds} - set(LABEL_MAP)
        if unknown:
            raise ValueError(f"알 수 없는 감성 라벨 {unknown} — LABEL_MAP을 확인하세요")
        df["sentiment"] = [LABEL_MAP[p["label"]] for p in preds]
        method = "deep_learning"
        print("[OK] 딥러닝 감성 분석 사용")
        print("[검증용 샘플] 아래 매핑이 상식과 맞는지 확인하세요:")
        for i in range(min(3, len(df))):
            print(f"  ({df['sentiment'].iloc[i]}) {df['review'].iloc[i][:30]}")
    except Exception as e:
        print(f"[WARN] 감성 모델 사용 불가({type(e).__name__}: {e}) "
              f"→ 평점 기반 폴백 (rating<=3 = 부정)")
        df["sentiment"] = np.where(df["rating"] <= 3, "neg", "pos")

    df["sentiment_method"] = method
    neg = df[df["sentiment"] == "neg"].copy()
    print(f"부정 리뷰: {len(neg)}건 / 전체 {len(df)}건 "
          f"({len(neg)/len(df)*100:.1f}%, 방식={method})")
    return neg


# ---------- (2) 토픽 모델링 ----------
def load_valid_embeddings(df: pd.DataFrame):
    """v2.2: 문서 해시가 일치할 때만 임베딩 사용 — 행 수만 같은 과거 임베딩 차단.
    v2.3: 손상 파일은 폴백(전체 중단 아님), 모델명·row_count·배열 무결성도 검증."""
    emb_path, meta_path = DATA_DIR / "emb_sbert.npy", DATA_DIR / "emb_meta.json"
    if not (emb_path.exists() and meta_path.exists()):
        return None
    try:
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
        all_emb = np.load(emb_path, allow_pickle=False)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print(f"[WARN] 임베딩 산출물 손상({type(e).__name__}) → 임베딩 없이 진행")
        return None
    if meta.get("sbert_available") is not True:
        return None
    if meta.get("sbert_model") != EXPECTED_SBERT_MODEL:
        print(f"[WARN] SBERT 모델 불일치({meta.get('sbert_model')}) → 임베딩 없이 진행")
        return None
    if meta.get("document_hash") != hash_documents(df["review"]):
        print("[WARN] 임베딩과 현재 리뷰 데이터 불일치(해시) → 03_embedding.py를 재실행하세요. "
              "이번엔 임베딩 없이 진행합니다.")
        return None
    if meta.get("row_count") != len(df) or len(all_emb) != len(df):
        print(f"[WARN] 임베딩/메타 행 수 불일치 → 임베딩 없이 진행")
        return None
    if all_emb.ndim != 2 or not np.isfinite(all_emb).all():
        print("[WARN] 임베딩 배열 형식 오류(차원/NaN/Inf) → 임베딩 없이 진행")
        return None
    return all_emb


def topics_bertopic(neg: pd.DataFrame, all_emb):
    from bertopic import BERTopic
    embeddings = all_emb[neg.index.values] if all_emb is not None else None
    # 대형 코퍼스에서 min_topic_size만 키우면 HDBSCAN이 90%짜리 거대 클러스터로
    # 뭉치는 것을 스윕으로 확인(2026-07-21: ms=10/15/20 모두 토픽 2개, 최대 점유 90%).
    # 대신 잘게 쪼갠 뒤(ms=5) 계층 병합(nr_topics)으로 상한을 두는 전략 채택 —
    # 3천건 기준 nr=16이 토픽 15개·최대 점유 25%·노이즈 33%로 최량이었음.
    nr = 16 if len(neg) > 1000 else None
    tm = BERTopic(language="multilingual", min_topic_size=5, nr_topics=nr, verbose=False)
    print(f"[OK] min_topic_size=5, nr_topics={nr} (부정 리뷰 {len(neg)}건 기준)")
    topics, _ = tm.fit_transform(neg["review"].tolist(), embeddings)
    neg["topic"] = topics
    info = tm.get_topic_info()
    labels = {row["Topic"]: row["Name"] for _, row in info.iterrows()}
    neg["topic_label"] = neg["topic"].map(labels)
    # v2.2: 대표 문서 = BERTopic이 뽑은 대표 문서 (등장 순서 아님)
    rep_docs = {t: docs[0] for t, docs in tm.get_representative_docs().items() if docs}
    neg.attrs["rep_docs"] = {labels.get(t, t): d for t, d in rep_docs.items()}
    print("[OK] BERTopic 사용")
    return neg


def topics_lda(neg: pd.DataFrame, requested_topics=5):
    """BERTopic 불가 시 폴백: CountVectorizer + LDA"""
    from sklearn.feature_extraction.text import CountVectorizer
    from sklearn.decomposition import LatentDirichletAllocation

    # v2.2: 토픽 수·min_df 를 데이터 크기에 맞게 조정
    n_topics = min(requested_topics, max(2, len(neg) // 10))
    min_df = 1 if len(neg) < 20 else 2
    vec = CountVectorizer(max_features=1000, min_df=min_df)
    X = vec.fit_transform(neg["tokens"].fillna(""))
    lda = LatentDirichletAllocation(n_components=n_topics, random_state=42).fit(X)
    doc_topic = lda.transform(X)
    neg["topic"] = doc_topic.argmax(axis=1)
    vocab = np.array(vec.get_feature_names_out())
    labels = {}
    print(f"[OK] LDA 폴백 사용 (n_topics={n_topics}, min_df={min_df}) — 토픽별 대표 키워드:")
    print("[주의] 토픽 간 키워드가 많이 겹치면 데이터가 부족하다는 신호 → n_topics를 줄이거나 데이터 확충")
    for i, comp in enumerate(lda.components_):
        top_words = vocab[np.argsort(comp)[::-1][:4]]
        # T{i}_ 접두어로 라벨 고유성 보장 (v2.4)
        labels[i] = f"T{i}_" + "_".join(top_words)
        print(f"  토픽 {i}: {', '.join(top_words)}")
    neg["topic_label"] = neg["topic"].map(labels)
    # v2.3: 대표 리뷰 = 해당 토픽에 '배정된' 문서 중 토픽 확률 최대 문서
    # (전체 문서에서 argmax를 하면 다른 토픽에 배정된 문서가 대표로 뽑힐 수 있음)
    rep_docs = {}
    topic_arr = neg["topic"].to_numpy()
    for i, label in labels.items():
        positions = np.flatnonzero(topic_arr == i)
        if len(positions) == 0:
            continue
        local_idx = positions[np.argmax(doc_topic[positions, i])]
        rep_docs[label] = neg["review"].iloc[local_idx]
    neg.attrs["rep_docs"] = rep_docs
    return neg


if __name__ == "__main__":
    # v2.4: 계보 체인 검증 — reviews_clean이 현재 metadata의 실행에서 나온 것인지 확인.
    # (과거 clean 잔존 + 새 01만 실행 → 새 run_id가 과거 데이터에 붙는 사고 차단)
    from lineage import require_meta, verify_hash, file_sha256, save_json
    collect_meta = require_meta(DATA_DIR / "metadata.json", "수집 데이터")
    prep_meta = require_meta(DATA_DIR / "preprocess_meta.json", "reviews_clean.csv")
    if collect_meta.get("status") != "ok":
        raise RuntimeError(f"수집 상태 비정상(status={collect_meta.get('status')}) — "
                           f"01_collect.py를 다시 실행하세요.")
    if collect_meta.get("run_id") != prep_meta.get("run_id"):
        raise ValueError(
            f"run_id 불일치(metadata={collect_meta.get('run_id')}, "
            f"preprocess={prep_meta.get('run_id')}) — reviews_clean.csv는 다른 실행의 "
            f"잔존물입니다. 02_preprocess.py를 다시 실행하세요.")
    # v2.5: raw→clean 계보 연결과 source_type 일치도 생산 시점에 검증
    if collect_meta.get("raw_csv_hash") != prep_meta.get("raw_csv_hash"):
        raise ValueError("raw_csv_hash 계보 불일치 — 02_preprocess.py를 다시 실행하세요.")
    if collect_meta.get("source_type") != prep_meta.get("source_type"):
        raise ValueError("source_type 계보 불일치 — 02_preprocess.py를 다시 실행하세요.")
    verify_hash(DATA_DIR / "reviews_clean.csv", prep_meta.get("clean_csv_hash"),
                "02 전처리 이후 파일이 변경/교체됨")

    df = pd.read_csv(DATA_DIR / "reviews_clean.csv")
    if len(df) < 3:
        raise ValueError(f"문서 {len(df)}건 — 분석 최소 3건 미만.")

    neg = filter_negative(df)
    # v2.3: 토픽 모델링 최소 문서 수 — 1~4건으로 토픽 2개를 억지로 만드는 것 방지
    if len(neg) < 5:
        raise ValueError(f"부정 리뷰 {len(neg)}건 — 토픽 모델링 최소 5건 미만. "
                         "감성 분류 방식과 데이터를 확인하세요.")

    all_emb = load_valid_embeddings(df)
    topic_method = "bertopic"
    try:
        neg = topics_bertopic(neg, all_emb)
    except Exception as e:
        print(f"[WARN] BERTopic 사용 불가({type(e).__name__}) → LDA 폴백")
        neg = topics_lda(neg)
        topic_method = "lda"

    # ---------- (3) Pain Point 정량화 ----------
    n_neg_total = len(neg)
    rep_docs = neg.attrs.get("rep_docs", {})
    assigned = neg[neg["topic"] != -1]  # BERTopic 노이즈(-1) 제외
    n_noise = n_neg_total - len(assigned)
    if len(assigned) == 0:
        raise ValueError("모든 부정 리뷰가 노이즈로 분류됨 — 데이터 확충 필요.")

    pp = (assigned.groupby("topic_label")
              .agg(빈도=("review", "size"), 평균평점=("rating", "mean"))
              .sort_values("빈도", ascending=False))
    # v2.2: 언급률 이중 표기 — 노이즈 제거로 비율이 부풀어 보이는 문제 방지
    pp["언급률_전체부정기준(%)"] = (pp["빈도"] / n_neg_total * 100).round(1)
    pp["언급률_배정기준(%)"] = (pp["빈도"] / len(assigned) * 100).round(1)
    pp["평균평점"] = pp["평균평점"].round(2)
    # v2.5: 대표 리뷰를 CSV에 포함 — Agent B가 '대표인용'을 지어내지 않도록 실데이터 전달
    pp["대표리뷰"] = [str(rep_docs.get(label, ""))[:100] for label in pp.index]
    pp.index.name = "PainPoint(토픽)"
    pp.to_csv(DATA_DIR / "painpoints.csv", encoding="utf-8-sig")

    # v2.5: 긍정 강점 산출물 — Agent B의 '지켜야 할 강점' 근거 데이터
    pos = df[df["sentiment"] == "pos"].copy()
    strengths = (pos.sort_values(["rating", "likes"], ascending=False)
                    .head(10)[["review", "rating", "likes"]])
    strengths.columns = ["대표리뷰", "평점", "좋아요"]
    strengths.to_csv(DATA_DIR / "strengths.csv", index=False, encoding="utf-8-sig")

    # v2.4: 계보 메타 — 입력(clean)과 출력(painpoints) 파일 해시를 모두 기록.
    # orchestrator는 run_id 3자 일치 + clean/painpoints 실파일 해시 일치까지 검증한다.
    save_json(DATA_DIR / "painpoints_meta.json", {
        "run_id": prep_meta["run_id"],
        "source_type": collect_meta.get("source_type"),
        "clean_csv_hash": prep_meta["clean_csv_hash"],
        "painpoints_csv_hash": file_sha256(DATA_DIR / "painpoints.csv"),
        "strengths_csv_hash": file_sha256(DATA_DIR / "strengths.csv"),
        "sentiment_method": neg["sentiment_method"].iloc[0],
        "topic_method": topic_method,
        "negative_count": int(n_neg_total),
        "noise_count": int(n_noise),
    })

    print(f"\n[Pain Point 순위] (노이즈 {n_noise}건/{n_neg_total}건 = "
          f"{n_noise/n_neg_total*100:.1f}% 제외) → CX 보고서 6장 표에 사용")
    print(pp)

    # 시각화 (전체 부정 리뷰 기준 비율 사용)
    pp.head(8)["언급률_전체부정기준(%)"].iloc[::-1].plot(kind="barh", figsize=(8, 5), color="tomato")
    plt.title("부정 리뷰 토픽별 언급률 (%, 전체 부정 리뷰 기준)"); plt.tight_layout()
    plt.savefig(OUT_DIR / "topic_freq.png", dpi=150)
    plt.close()

    # 토픽별 대표 리뷰 (보고서 인용용) — v2.2: 토픽 확률/대표문서 기준
    print("\n[토픽별 대표 리뷰] (토픽 대표성 기준 선정)")
    for label in pp.index:
        doc = rep_docs.get(label, "")
        print(f"- {label}: \"{str(doc)[:50]}...\"")
    print("\n저장 완료: data/painpoints.csv, out/topic_freq.png")
