# -*- coding: utf-8 -*-
"""
[DX 6단계] 정량화·시각화 (보고서 삽입용)
- Pain Point 우선순위 매트릭스 (언급률 x 심각도)
- 레이더 차트 (자사 vs 경쟁사 CX 5각형 평가 — 강의 자료 방식)
실행: python 06_visualize.py
입력: data/painpoints.csv (5단계 출력)
출력: out/priority_matrix.png, out/radar_cx.png
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


# ---------- (1) 우선순위 매트릭스 ----------
def priority_matrix():
    pp = pd.read_csv("data/painpoints.csv")
    # 심각도 = 5 - 평균평점 (평점이 낮을수록 심각) → 1~4 스케일
    pp["심각도"] = (5 - pp["평균평점"]).round(2)

    fig, ax = plt.subplots(figsize=(8, 6))
    x, y = pp["언급률(%)"], pp["심각도"]
    # v2.1: 버블 크기 정규화 — 리뷰 수천 건에서도 차트가 안 덮이게 최대 600으로 상한
    sizes = 100 + 500 * (pp["빈도"] / pp["빈도"].max())
    ax.scatter(x, y, s=sizes, alpha=0.6, color="steelblue")
    for _, row in pp.iterrows():
        ax.annotate(str(row.iloc[0])[:14], (row["언급률(%)"], row["심각도"]),
                    fontsize=9, xytext=(5, 5), textcoords="offset points")
    ax.axvline(x.median(), color="gray", ls="--", lw=0.8)
    ax.axhline(y.median(), color="gray", ls="--", lw=0.8)
    ax.set_xlabel("언급률 (%)  → 빈도"); ax.set_ylabel("심각도 (5-평균평점)")
    ax.set_title("Pain Point 우선순위 매트릭스\n(우상단 = 1순위 해결 대상)")
    fig.tight_layout(); fig.savefig("out/priority_matrix.png", dpi=150)

    pp["우선순위점수"] = (pp["언급률(%)"] * pp["심각도"]).round(1)
    top = pp.sort_values("우선순위점수", ascending=False)
    print("[Pain Point 최종 우선순위]  ← 언급률 x 심각도")
    print(top[[top.columns[0], "언급률(%)", "심각도", "우선순위점수"]].to_string(index=False))
    return top


# ---------- (2) CX 5각형 레이더 차트 (자사 vs 경쟁사) ----------
def radar_chart():
    # 강의 자료의 5개 평가축. 팀 평가 점수(1~5)로 교체해서 사용
    axes_labels = ["CI/BI 일관성", "아이콘", "색상활용", "인터렉션", "Layout"]
    scores = {
        "자사(우리 서비스)": [3, 4, 3, 2, 3],
        "경쟁사 A":        [4, 5, 4, 4, 4],
    }

    n = len(axes_labels)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    angles += angles[:1]  # 닫기

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
    for name, vals in scores.items():
        v = vals + vals[:1]
        ax.plot(angles, v, "o-", linewidth=2, label=name)
        ax.fill(angles, v, alpha=0.15)
    ax.set_xticks(angles[:-1]); ax.set_xticklabels(axes_labels, fontsize=11)
    ax.set_ylim(0, 5); ax.set_yticks([1, 2, 3, 4, 5])
    ax.set_title("CX 정량 평가 — 자사 vs 경쟁사", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1))
    fig.tight_layout(); fig.savefig("out/radar_cx.png", dpi=150)
    print("\n[OK] 레이더 차트 저장 → 점수는 팀 휴리스틱 평가로 교체하세요")


if __name__ == "__main__":
    if os.path.exists("data/painpoints.csv"):
        priority_matrix()
    else:
        print("[WARN] data/painpoints.csv 없음 → 05_painpoint.py 먼저 실행")
    radar_chart()
    print("\n저장 완료: out/priority_matrix.png, out/radar_cx.png")
