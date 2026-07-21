# -*- coding: utf-8 -*-
"""
[DX 7단계] 워드클라우드 + 감성분석 리포트 (v1)
데이터 출처 (혼동 방지를 위해 명시):
  ① 플레이스토어 ThinQ 앱 리뷰 = "ThinQ 앱 실사용자의 공개 후기" (앱 내부 데이터 아님)
     - data/reviews_raw.csv 재사용 (없으면 01_collect.py 먼저 실행 안내)
     - 분석 대상: 별점 1~3점 (부정·중립 후기)
  ② (옵션) LGE 키워드 검색 수집 — 네이버 오픈 API (블로그·카페·지식iN)
     - 환경변수 NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 설정 시에만 동작
     - 미설정이면 건너뛰고 ①만으로 진행 (실행 로그에 명시)

출력:
  out/wordcloud_neg.png        별점 1~3점 워드클라우드
  out/sentiment_dist.png       감성분석 분포 (딥러닝 모델 or 평점 폴백)
  data/keyword_lge.csv         (옵션 ② 실행 시) LGE 키워드 수집분
  data/wordcloud_freq.csv      워드클라우드 상위 단어 빈도표 (보고서 인용용)

실행: python 07_wordcloud_sentiment.py [--keyword "LGE ThinQ"] [--top 100]
"""
import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

plt.rcParams["font.family"] = ["Malgun Gothic", "AppleGothic", "NanumGothic", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

from model_config import LABEL_MAP, SENTIMENT_MODEL

BASE = Path(__file__).parent
DATA_DIR = BASE / "data"
OUT_DIR = BASE / "out"
OUT_DIR.mkdir(exist_ok=True)

# 워드클라우드용 한글 폰트 — malgun.ttf는 wordcloud의 글리프 높이 계산이 어긋나
# 캔버스 가장자리 단어가 잘리는 문제가 있어 나눔고딕 사용
FONT_PATH = r"C:\Windows\Fonts\NanumGothic.ttf"

# 05와 동일 계열의 도메인 불용어 + 워드클라우드 전용 (조사·범용어는 Kiwi 품사로 걸러짐)
STOPWORDS = {
    "앱", "어플", "사용", "때문", "진짜", "정말", "그냥", "계속", "다시", "너무",
    "이거", "저거", "그거", "지금", "오늘", "요즘", "please", "lg", "엘지",
    "씽큐", "띵큐", "thinq", "하다", "되다", "있다", "없다", "같다", "보다",
}


def load_playstore_negative() -> pd.DataFrame:
    """① 플레이스토어 ThinQ 리뷰 중 별점 1~3점 로드."""
    raw = DATA_DIR / "reviews_raw.csv"
    if not raw.exists():
        sys.exit("[ERR] data/reviews_raw.csv 없음 — 먼저 python 01_collect.py 를 실행하세요.")
    df = pd.read_csv(raw)
    meta = json.load(open(DATA_DIR / "metadata.json", encoding="utf-8"))
    neg = df[df["rating"] <= 3].copy()
    neg["origin"] = "playstore_review"
    print(f"[OK] 플레이스토어 리뷰 로드: 전체 {len(df)}건 중 별점 1~3점 {len(neg)}건 "
          f"(source={meta['source_type']}, run_id={meta['run_id']})")
    return neg


def crawl_naver_keyword(keyword: str, per_source: int = 100) -> pd.DataFrame:
    """② 네이버 오픈 API로 LGE 키워드 검색 수집 (블로그·카페·지식iN).
    NAVER_CLIENT_ID/SECRET 미설정이면 빈 DataFrame 반환."""
    cid = os.environ.get("NAVER_CLIENT_ID")
    csec = os.environ.get("NAVER_CLIENT_SECRET")
    if not (cid and csec):
        print("[SKIP] NAVER_CLIENT_ID/SECRET 미설정 — LGE 키워드 수집 건너뜀 "
              "(https://developers.naver.com 에서 발급 후 환경변수 설정)")
        return pd.DataFrame()

    import re
    import urllib.parse
    import urllib.request

    rows = []
    for api in ("blog", "cafearticle", "kin"):
        got = 0
        for start in range(1, per_source + 1, 100):
            url = (f"https://openapi.naver.com/v1/search/{api}.json"
                   f"?query={urllib.parse.quote(keyword)}&display=100&start={start}")
            req = urllib.request.Request(url, headers={
                "X-Naver-Client-Id": cid, "X-Naver-Client-Secret": csec})
            try:
                with urllib.request.urlopen(req, timeout=10) as r:
                    items = json.load(r).get("items", [])
            except Exception as e:
                print(f"[WARN] {api} 수집 실패({type(e).__name__}) — 건너뜀")
                break
            for it in items:
                text = re.sub(r"<[^>]+>", "", it.get("title", "") + " " + it.get("description", ""))
                rows.append({"review": text, "rating": None,
                             "origin": f"naver_{api}", "link": it.get("link")})
            got += len(items)
            if len(items) < 100:
                break
        print(f"[OK] 네이버 {api}: {got}건")
    df = pd.DataFrame(rows)
    if not df.empty:
        # 키워드 오염 필터 — 'ThinQ' 검색에 걸리는 옛 스마트폰(G6~G8, V40 등) 글 제거
        phone_noise = df["review"].str.contains(
            r"G[5-9]\s*ThinQ|V[345]0\s*ThinQ|스냅드래곤|스마트폰.{0,10}(사양|스펙|출시)",
            regex=True, na=False)
        if phone_noise.any():
            print(f"[OK] 키워드 오염 필터: 스마트폰 ThinQ 관련 {phone_noise.sum()}건 제거")
            df = df[~phone_noise].reset_index(drop=True)
        df.to_csv(DATA_DIR / "keyword_lge.csv", index=False, encoding="utf-8-sig")
        print(f"저장: data/keyword_lge.csv ({len(df)}건) — 키워드='{keyword}'")
    return df


def tokenize(texts: list[str]) -> Counter:
    """Kiwi 형태소 분석 → 명사·형용사·동사 어근만 추출 (2글자 이상)."""
    from kiwipiepy import Kiwi
    kiwi = Kiwi()
    counter = Counter()
    for t in texts:
        for tok in kiwi.tokenize(str(t)):
            if tok.tag in ("NNG", "NNP", "VA", "VV") and len(tok.form) >= 2 \
                    and tok.form.lower() not in STOPWORDS:
                counter[tok.form] += 1
    return counter


def draw_wordcloud(freq: Counter, path: Path, top: int):
    import random as _random

    from wordcloud import WordCloud

    def _red_palette(word, **kw):
        # colormap='Reds' 하위 톤이 배경에 묻혀서 진한 적색 계열만 사용
        palette = ["#7f1d1d", "#b91c1c", "#dc2626", "#ef4444", "#c2410c", "#9a3412"]
        return palette[int(_random.Random(word).uniform(0, 1) * len(palette))]

    # max_font_size 제한 + margin — 최상위 단어가 캔버스 밖으로 잘리는 문제 방지
    # prefer_horizontal=1.0 — 세로 단어 제거 (한글 가독성)
    wc = WordCloud(font_path=FONT_PATH, width=1200, height=700,
                   background_color="white", max_words=top,
                   max_font_size=180, margin=10, prefer_horizontal=1.0,
                   random_state=42,
                   color_func=_red_palette).generate_from_frequencies(dict(freq.most_common(top)))
    wc.to_file(str(path))
    print(f"[OK] 워드클라우드 저장: {path}")


def run_sentiment(df: pd.DataFrame) -> pd.DataFrame:
    """딥러닝 감성 모델(가능 시) — 실패하면 평점 기반 폴백 (05와 동일 정책)."""
    try:
        from transformers import pipeline
        clf = pipeline("sentiment-analysis", model=SENTIMENT_MODEL, truncation=True)
        preds = clf(df["review"].astype(str).str[:512].tolist(), batch_size=32)
        unknown = {p["label"] for p in preds} - set(LABEL_MAP)
        if unknown:
            raise ValueError(f"알 수 없는 라벨 {unknown}")
        df["sentiment"] = [LABEL_MAP[p["label"]] for p in preds]
        df["sentiment_method"] = "deep_learning"
        print(f"[OK] 딥러닝 감성분석 사용 ({SENTIMENT_MODEL})")
    except Exception as e:
        print(f"[WARN] 딥러닝 불가({type(e).__name__}) → 평점 폴백 (rating<=3 = neg)")
        df["sentiment"] = df["rating"].map(lambda r: "neg" if (pd.notna(r) and r <= 3) else "pos")
        df["sentiment_method"] = "rating_fallback"
    return df


def plot_sentiment(df: pd.DataFrame, path: Path):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    df["sentiment"].value_counts().plot.bar(ax=axes[0], color=["#c0392b", "#27ae60"])
    axes[0].set_title(f"감성 분포 (method={df['sentiment_method'].iloc[0]})")
    axes[0].tick_params(rotation=0)
    if df["rating"].notna().any():
        pd.crosstab(df["rating"], df["sentiment"]).plot.bar(
            stacked=True, ax=axes[1], color=["#c0392b", "#27ae60"])
        axes[1].set_title("별점 × 감성 교차 (모델 검증용)")
        axes[1].tick_params(rotation=0)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"[OK] 감성 분포 차트 저장: {path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--keyword", default="LGE ThinQ",
                    help="네이버 검색 키워드 (API 키 설정 시에만 사용)")
    ap.add_argument("--top", type=int, default=100, help="워드클라우드 최대 단어 수")
    args = ap.parse_args()

    # ① 플레이스토어 별점 1~3점 후기
    neg = load_playstore_negative()
    # ② (옵션) LGE 키워드 검색
    kw = crawl_naver_keyword(args.keyword)
    corpus = pd.concat([neg, kw], ignore_index=True) if not kw.empty else neg
    print(f"[OK] 분석 코퍼스: {len(corpus)}건 "
          f"(플레이스토어 {len(neg)} + 키워드 {len(kw) if not kw.empty else 0})")

    # 워드클라우드 + 빈도표
    freq = tokenize(corpus["review"].tolist())
    draw_wordcloud(freq, OUT_DIR / "wordcloud_neg.png", args.top)
    freq_df = pd.DataFrame(freq.most_common(args.top), columns=["단어", "빈도"])
    freq_df.to_csv(DATA_DIR / "wordcloud_freq.csv", index=False, encoding="utf-8-sig")
    print(f"[OK] 빈도표 저장: data/wordcloud_freq.csv (상위 {args.top}개)")

    # 감성분석
    corpus = run_sentiment(corpus)
    plot_sentiment(corpus, OUT_DIR / "sentiment_dist.png")
    print("\n감성 분포:")
    print(corpus.groupby("origin")["sentiment"].value_counts().to_string())
