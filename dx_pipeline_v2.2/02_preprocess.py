# -*- coding: utf-8 -*-
"""
[DX 2단계] 전처리 + 형태소 분석 (v2.8)
- 중복/짧은 리뷰 제거, 특수문자 정리
- Kiwi 형태소 분석 → 명사/동사/형용사만 추출 (불용어 제거)
- v2.2: pathlib 경로 고정, 최소 문서 수 가드, source_type 컬럼 유지
실행: python 02_preprocess.py
입력: data/reviews_raw.csv
출력: data/reviews_clean.csv  (tokens 컬럼 추가)
"""
import sys
_enc = getattr(sys.stdout, "encoding", None)
if _enc and _enc.lower() != "utf-8" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # Windows cp949 콘솔 대응
import re
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

MIN_DOCS = 3  # 이 미만이면 이후 단계(벡터화·군집)가 의미 없음

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
    """Kiwi 형태소 분석. 미설치 시 공백 분리로 폴백.
    [주의] 폴백 시 조사·어미가 토큰에 남아 TF-IDF/토픽 품질이 떨어짐."""
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
        print("[WARN] kiwipiepy 미설치 → 공백 분리로 폴백 (품질 저하, pip install kiwipiepy 권장)")
        return [" ".join(w for w in t.split() if w not in STOPWORDS) for t in texts]


if __name__ == "__main__":
    # v2.4: 계보 체인 검증 — metadata 부재/손상/실패 상태/raw 해시 불일치 모두 중단
    from lineage import require_meta, verify_hash, file_sha256, save_json
    meta = require_meta(DATA_DIR / "metadata.json", "reviews_raw.csv")
    if meta.get("status") != "ok":
        raise RuntimeError(
            f"직전 수집 상태가 정상이 아님(status={meta.get('status')}) — "
            f"data/의 산출물은 이전 실행 잔존물일 수 있습니다. 01_collect.py를 다시 실행하세요.")
    verify_hash(DATA_DIR / "reviews_raw.csv", meta.get("raw_csv_hash"),
                "01 수집 이후 파일이 변경/교체됨")
    df = pd.read_csv(DATA_DIR / "reviews_raw.csv")
    n0 = len(df)

    # 1) 기본 정제
    df["review"] = df["review"].astype(str).map(clean_text)
    df = df[df["review"].str.len() >= 5]        # 너무 짧은 리뷰 제거
    df = df.drop_duplicates(subset="review")     # 중복 제거
    print(f"정제: {n0}건 → {len(df)}건")

    if len(df) < MIN_DOCS:
        raise ValueError(f"정제 후 문서 {len(df)}건 — 분석에 필요한 최소 {MIN_DOCS}건 미만. "
                         f"데이터를 확충하세요.")

    # 2) 형태소 분석
    df["tokens"] = tokenize_all(df["review"].tolist())
    df = df[df["tokens"].str.len() > 0]
    # 이후 단계(임베딩 행 순서 매칭)의 기준이 되는 인덱스를 여기서 확정
    df = df.reset_index(drop=True)

    # v2.3: 토큰화 후 재검사 — 전부 불용어면 0건인데 성공 코드로 끝나는 문제 방지
    if len(df) < MIN_DOCS:
        raise ValueError(
            f"형태소 분석 후 유효 문서 {len(df)}건 — 최소 {MIN_DOCS}건 미만. "
            f"불용어·품사 조건 또는 원본 데이터를 확인하세요.")

    # v2.3: 원자적 저장 — 실패 시 이전 reviews_clean.csv가 반쯤 덮이는 것 방지
    tmp = DATA_DIR / "reviews_clean.csv.tmp"
    df.to_csv(tmp, index=False, encoding="utf-8-sig")
    tmp.replace(DATA_DIR / "reviews_clean.csv")

    # v2.4: 계보 승계 — 이 clean 파일이 '어느 01 실행'에서 나왔는지 기록
    save_json(DATA_DIR / "preprocess_meta.json", {
        "run_id": meta["run_id"],
        "source_type": meta.get("source_type"),
        "raw_csv_hash": meta["raw_csv_hash"],
        "clean_csv_hash": file_sha256(DATA_DIR / "reviews_clean.csv"),
    })
    print(df[["review", "tokens", "rating"]].head())
    print(f"\n저장 완료: data/reviews_clean.csv ({len(df)}건)")
