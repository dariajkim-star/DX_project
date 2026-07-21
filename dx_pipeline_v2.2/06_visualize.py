# -*- coding: utf-8 -*-
"""
[DX 6단계] 정량화·시각화 (보고서 삽입용) (v2.8)
- Pain Point 우선순위 매트릭스 (언급률 x 심각도)
- 레이더 차트 (자사 vs 경쟁사 CX 5각형 평가)
- v2.2 주요 수정:
  * 레이더 차트: 하드코딩 점수 제거 → data/cx_scores.csv 필수 입력.
    없으면 생성하지 않음 (가짜 점수가 보고서 산출물로 위장되는 사고 방지).
    --demo 로 예시 점수 차트 생성 가능하나 이미지에 워터마크 삽입.
  * 빈 데이터 가드, 심각도 스케일 주석 정정(0~4), 우선순위 점수를
    '휴리스틱 점수'로 명명, pathlib 경로, plt.close
실행: python 06_visualize.py            (cx_scores.csv 없으면 레이더 생략)
      python 06_visualize.py --demo     (예시 점수 레이더 — 워터마크 포함)
입력: data/painpoints.csv (5단계 출력), data/cx_scores.csv (팀 평가 점수)
출력: out/priority_matrix.png, out/radar_cx.png
"""
import sys
_enc = getattr(sys.stdout, "encoding", None)
if _enc and _enc.lower() != "utf-8" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # Windows cp949 콘솔 대응
import argparse
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

MENTION_COL = "언급률_전체부정기준(%)"  # 05단계 v2.2 출력 컬럼


# ---------- (1) 우선순위 매트릭스 ----------
def priority_matrix():
    try:
        pp = pd.read_csv(DATA_DIR / "painpoints.csv")
    except pd.errors.EmptyDataError as e:
        raise ValueError("painpoints.csv가 0바이트 또는 헤더 없는 빈 파일입니다 — "
                         "05_painpoint.py를 다시 실행하세요.") from e
    if len(pp) == 0:
        raise ValueError("painpoints.csv가 비어 있음 — 05_painpoint.py 결과를 확인하세요.")
    if MENTION_COL not in pp.columns:  # v2.1 이전 산출물 호환
        raise ValueError(f"'{MENTION_COL}' 컬럼 없음 — v2.2 05_painpoint.py로 재생성하세요.")

    # v2.5: 수치 범위 검증 — 변조/오염된 CSV가 그럴듯한 차트로 위장되는 것 방지
    num_checks = {
        "빈도": (pp["빈도"], 1, None),
        "평균평점": (pp["평균평점"], 1, 5),
        MENTION_COL: (pp[MENTION_COL], 0, 100),
    }
    for name, (col, lo, hi) in num_checks.items():
        vals = pd.to_numeric(col, errors="coerce")
        if vals.isna().any() or not np.isfinite(vals).all():
            raise ValueError(f"painpoints.csv '{name}'에 비숫자/NaN/Inf 존재")
        if (vals < lo).any() or (hi is not None and (vals > hi).any()):
            raise ValueError(f"painpoints.csv '{name}' 값이 유효 범위({lo}~{hi}) 밖")

    # 심각도 = 5 - 평균평점 (평점 1~5 → 심각도 0~4; 평점이 낮을수록 심각)
    pp["심각도"] = (5 - pp["평균평점"]).round(2)

    fig, ax = plt.subplots(figsize=(8, 6))
    x, y = pp[MENTION_COL], pp["심각도"]
    # 버블 크기 정규화 — 최소 100, 최대 600
    sizes = 100 + 500 * (pp["빈도"] / pp["빈도"].max())
    ax.scatter(x, y, s=sizes, alpha=0.6, color="steelblue")
    for _, row in pp.iterrows():
        ax.annotate(str(row.iloc[0])[:14], (row[MENTION_COL], row["심각도"]),
                    fontsize=9, xytext=(5, 5), textcoords="offset points")
    ax.axvline(x.median(), color="gray", ls="--", lw=0.8)
    ax.axhline(y.median(), color="gray", ls="--", lw=0.8)
    ax.set_xlabel("언급률 (%, 전체 부정 리뷰 기준)  → 빈도")
    ax.set_ylabel("심각도 (5-평균평점, 0~4)")
    ax.set_title("Pain Point 우선순위 매트릭스\n(우상단 = 1순위 해결 대상)")
    fig.tight_layout(); fig.savefig(OUT_DIR / "priority_matrix.png", dpi=150)
    plt.close(fig)

    # 휴리스틱 점수 — 언급률×심각도는 임의 공식이므로 '최종 순위'가 아닌 참고용
    pp["휴리스틱_우선순위점수"] = (pp[MENTION_COL] * pp["심각도"]).round(1)
    top = pp.sort_values("휴리스틱_우선순위점수", ascending=False)
    print("[Pain Point 휴리스틱 우선순위]  ← 언급률 x 심각도 (참고용, 팀 검토 필요)")
    print(top[[top.columns[0], MENTION_COL, "심각도", "휴리스틱_우선순위점수"]].to_string(index=False))
    return top


# ---------- (2) CX 5각형 레이더 차트 (자사 vs 경쟁사) ----------
def radar_chart(demo: bool):
    """v2.2: 점수는 data/cx_scores.csv 에서 입력.
    형식 — 첫 컬럼 '이름', 이후 5개 축 컬럼(1~5점):
      이름,CI/BI 일관성,아이콘,색상활용,인터랙션,Layout
      자사(우리 서비스),3,4,3,2,3
      경쟁사 A,4,5,4,4,4
    """
    score_path = DATA_DIR / "cx_scores.csv"
    radar_path = OUT_DIR / "radar_cx.png"
    if score_path.exists():
        sc = pd.read_csv(score_path)
        # v2.3: 스키마·범위 검증 — 잘못된 입력이 그럴듯한 차트로 위장되는 것 방지
        if sc.empty:
            raise ValueError("cx_scores.csv에 평가 대상 행이 없습니다.")
        if sc.shape[1] != 6:
            raise ValueError(f"cx_scores.csv는 '이름 컬럼 + 평가 축 5개'여야 합니다 "
                             f"(현재 {sc.shape[1]}개 컬럼).")
        numeric = sc.iloc[:, 1:].apply(pd.to_numeric, errors="coerce")
        if numeric.isna().any().any():
            raise ValueError("CX 점수에 숫자가 아닌 값 또는 결측치가 있습니다.")
        if not numeric.stack().between(1, 5).all():
            raise ValueError("CX 점수는 모두 1~5 범위여야 합니다.")
        axes_labels = sc.columns[1:].tolist()
        scores = {row.iloc[0]: row.iloc[1:].astype(float).tolist() for _, row in sc.iterrows()}
        watermark = None
        print(f"[OK] 팀 평가 점수 로드: {score_path}")
    elif demo:
        axes_labels = ["CI/BI 일관성", "아이콘", "색상활용", "인터랙션", "Layout"]
        scores = {"자사(우리 서비스)": [3, 4, 3, 2, 3], "경쟁사 A": [4, 5, 4, 4, 4]}
        watermark = "DEMO / 예시 점수 — 보고서 사용 금지"
        print("[DEMO] 예시 점수로 레이더 차트 생성 (워터마크 포함)")
    else:
        # v2.3: 과거 데모 차트가 최신 산출물처럼 남는 것 방지 — 스킵 시 기존 파일 제거
        if radar_path.exists():
            radar_path.unlink()
            print("[SKIP] cx_scores.csv 없음 → 기존 radar_cx.png도 제거 (잔존 데모 차트 방지)")
        else:
            print("[SKIP] data/cx_scores.csv 없음 → 레이더 차트 생성 안 함.")
        print("  팀 평가 점수(1~5)를 CSV로 저장하거나, 예시가 필요하면 --demo 로 실행하세요.")
        return

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
    if watermark:
        fig.text(0.5, 0.5, watermark, fontsize=22, color="red", alpha=0.35,
                 ha="center", va="center", rotation=25)
    fig.tight_layout(); fig.savefig(OUT_DIR / "radar_cx.png", dpi=150)
    plt.close(fig)
    print("[OK] 레이더 차트 저장: out/radar_cx.png")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true",
                        help="cx_scores.csv 없이 예시 점수 레이더 생성 (워터마크 포함)")
    args = parser.parse_args()

    # v2.5: 검증 실패 시 이전 실행의 이미지가 최신 결과처럼 남지 않도록
    # 예외 발생 시 해당 산출물을 삭제하고 에러를 그대로 올림
    if (DATA_DIR / "painpoints.csv").exists():
        try:
            priority_matrix()
        except Exception:
            (OUT_DIR / "priority_matrix.png").unlink(missing_ok=True)
            raise
    else:
        print("[WARN] data/painpoints.csv 없음 → 05_painpoint.py 먼저 실행")
    try:
        radar_chart(demo=args.demo)
    except Exception:
        (OUT_DIR / "radar_cx.png").unlink(missing_ok=True)
        raise
    print("\n완료: out/ 폴더를 확인하세요")
