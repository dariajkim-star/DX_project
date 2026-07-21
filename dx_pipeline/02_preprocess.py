# -*- coding: utf-8 -*-
"""
[DX 2단계] 전처리 + 형태소 분석
- 중복/짧은 리뷰 제거, 특수문자 정리
- Kiwi 형태소 분석 → 명사/동사/형용사만 추출 (불용어 제거)
실행: python 02_preprocess.py
입력: data/reviews_raw.csv
출력: data/reviews_clean.csv  (tokens 컬럼 추가)
"""
import re
import pandas as pd

# 도메인에 맞게 계속 추가하는 것을 권장
STOPWORDS = {
    "하다", "되다", "있다", "없다", "같다", "이다", "보다", "주다", "받다",
    "너무", "정말", "진짜", "그냥", "계속", "다시", "때문", "경우", "부분",
    "사용", "기능", "어플", "앱",  # 모든 리뷰에 나와서 변별력 없는 단어
}


def clean_text(text: str) -> str:
    text = re.sub(r"[^가-힣a-zA-Z0-9\s]", " ", str(text))  # 특수문자 제거
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize_all(texts):
    """Kiwi 형태소 분석. 미설치 시 공백 분리로 폴백."""
    try:
        from kiwipiepy import Kiwi
        kiwi = Kiwi()
        keep_tags = {"NNG", "NNP", "VV", "VA"}  # 일반명사/고유명사/동사/형용사
        results = []
        for t in texts:
            tokens = [
                tok.form for tok in kiwi.tokenize(t)
                if tok.tag in keep_tags and len(tok.form) > 1 and tok.form not in STOPWORDS
            ]
            results.append(" ".join(tokens))
        print("[OK] Kiwi 형태소 분석 사용")
        return results
    except ImportError:
        print("[WARN] kiwipiepy 미설치 → 공백 분리로 폴백 (pip install kiwipiepy 권장)")
        return [" ".join(w for w in t.split() if w not in STOPWORDS) for t in texts]


if __name__ == "__main__":
    df = pd.read_csv("data/reviews_raw.csv")
    n0 = len(df)

    # 1) 기본 정제
    df["review"] = df["review"].astype(str).map(clean_text)
    df = df[df["review"].str.len() >= 5]        # 너무 짧은 리뷰 제거
    df = df.drop_duplicates(subset="review")     # 중복 제거
    print(f"정제: {n0}건 → {len(df)}건")

    # 2) 형태소 분석
    df["tokens"] = tokenize_all(df["review"].tolist())
    df = df[df["tokens"].str.len() > 0]

    df.to_csv("data/reviews_clean.csv", index=False, encoding="utf-8-sig")
    print(df[["review", "tokens", "rating"]].head())
    print(f"\n저장 완료: data/reviews_clean.csv ({len(df)}건)")
