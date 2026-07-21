# -*- coding: utf-8 -*-
"""
[분석] ThinQ vs SmartThings 경쟁 대조 — 기간 정합 비교
- Grumbal 지적 반영: 전체 평균 비교는 표본 기간 불일치로 왜곡됨.
  두 앱이 모두 존재하는 구간만 잘라 **월별 추이 오버레이**로 비교한다.
- 산출: out/compare_rating_trend.png, out/compare_summary.csv

실행: python compare_competitor.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

plt.rcParams["font.family"] = ["Malgun Gothic", "AppleGothic", "NanumGothic", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

BASE = Path(__file__).parent
DATA_DIR, OUT_DIR = BASE / "data", BASE / "out"
OUT_DIR.mkdir(exist_ok=True)

# P-2(설정 휘발·재등록) 시그널 — 경쟁 비교의 핵심 축
P2_PATTERN = r"재등록|다시 등록|초기화|설정.{0,8}(사라|날아|다시)|기기.{0,4}등록|제품.{0,4}등록"


def load(name: str, alias: str) -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / f"crawl_playstore_{name}.csv", parse_dates=["date"])
    df["app"] = alias
    return df


if __name__ == "__main__":
    thinq = load("thinq", "LG ThinQ")
    smart = load("smartthings", "SmartThings")

    # 기간 정합 — 양쪽 모두 데이터가 있는 구간으로 절단
    lo = max(thinq["date"].min(), smart["date"].min())
    thinq, smart = thinq[thinq["date"] >= lo], smart[smart["date"] >= lo]
    both = pd.concat([thinq, smart], ignore_index=True)
    print(f"[기간 정합] {lo.date()} ~ (ThinQ {len(thinq):,} / SmartThings {len(smart):,})")

    # 월별 1점 비율 + 리뷰량
    both["월"] = both["date"].dt.to_period("M").dt.to_timestamp()
    trend = both.groupby(["월", "app"]).agg(
        리뷰수=("rating", "size"),
        일점비율=("rating", lambda r: (r == 1).mean() * 100),
        평균평점=("rating", "mean"),
    ).reset_index()

    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    for app, color in [("LG ThinQ", "#c0392b"), ("SmartThings", "#2980b9")]:
        d = trend[trend["app"] == app]
        axes[0].plot(d["월"], d["일점비율"], label=app, color=color, linewidth=1.8)
        axes[1].plot(d["월"], d["리뷰수"], label=app, color=color, linewidth=1.8)
    axes[0].set_title("월별 1점 리뷰 비율 (%) — 기간 정합 비교")
    axes[0].set_ylabel("1점 비율 (%)"); axes[0].legend(); axes[0].grid(alpha=.3)
    axes[1].set_title("월별 리뷰 수 (불만 폭증 시점 탐지)")
    axes[1].set_ylabel("리뷰 수"); axes[1].legend(); axes[1].grid(alpha=.3)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "compare_rating_trend.png", dpi=150)
    plt.close(fig)
    print(f"[OK] 차트 저장: out/compare_rating_trend.png")

    # 요약표 — 전체 + P-2 시그널 비중
    rows = []
    for app, d in both.groupby("app"):
        p2 = d["review"].astype(str).str.contains(P2_PATTERN, regex=True, na=False)
        rows.append({
            "앱": app, "리뷰수": len(d),
            "1점비율(%)": round((d["rating"] == 1).mean() * 100, 1),
            "평균평점": round(d["rating"].mean(), 2),
            "P2_설정휘발_건수": int(p2.sum()),
            "P2_비중(%)": round(p2.mean() * 100, 2),
        })
    summary = pd.DataFrame(rows)
    summary.to_csv(OUT_DIR / "compare_summary.csv", index=False, encoding="utf-8-sig")
    print(summary.to_string(index=False))
