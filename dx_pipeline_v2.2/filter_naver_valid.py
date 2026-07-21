# -*- coding: utf-8 -*-
"""
[분석] 네이버 4축 수집분 유효 필터링 — 정성 증언 후보 추출
- 결정 근거: 2026-07-21 크롤 전략 미팅 — A·B·D축 재수집 대신 기존 수집분의
  유효분만 추려 정성 증언·P-2 심층·경쟁 담론 재료로 사용 (토픽 분석 제외)
- 유효 기준(엄격): 축 시그널 ∧ 앱 언급(씽큐|ThinQ) ∧ ¬오프토픽 — crawl_naver.measure_yield와 동일
- 산출:
    data/naver_valid.csv          유효분 전체 (axis·sponsored 컬럼 유지)
    data/naver_testimony.csv      정성 증언 후보 — 1인칭·경험 서술이 있는 것 우선 정렬

실행: python filter_naver_valid.py
"""
import re
from pathlib import Path

import pandas as pd

from crawl_naver import APP_MENTION, AXIS_SIGNAL, OFF_TOPIC

DATA_DIR = Path(__file__).parent / "data"

# 경험 서술 신호 — 협찬·가이드가 아닌 1인칭 증언을 앞세우기 위한 우선순위 점수
EXPERIENCE = re.compile(
    r"저도|제가|우리\s*집|저희\s*집|했더니|하니까|당했|겪|짜증|화가|스트레스|포기|결국")
GUIDE_TONE = re.compile(r"해결법|꿀팁|총정리|방법\s*안내|가이드|STEP|정리해\s*드")


if __name__ == "__main__":
    df = pd.read_csv(DATA_DIR / "crawl_naver.csv")
    text = df["review"].astype(str)

    app = text.str.contains(APP_MENTION, regex=True, na=False)
    off = text.str.contains(OFF_TOPIC, regex=True, na=False)
    axis_hit = pd.Series(False, index=df.index)
    for axis, pattern in AXIS_SIGNAL.items():
        axis_hit |= (df["axis"] == axis) & text.str.contains(pattern, regex=True, na=False)

    valid = df[axis_hit & app & ~off].copy()
    valid.to_csv(DATA_DIR / "naver_valid.csv", index=False, encoding="utf-8-sig")
    print(f"[OK] 유효분 {len(valid)}건 / {len(df)}건 → data/naver_valid.csv")
    print(valid["axis"].value_counts().to_string())

    # 정성 증언 후보: 경험 서술 있음 > 가이드 톤 아님 > 비협찬 순으로 정렬
    vt = valid["review"].astype(str)
    valid["경험서술"] = vt.str.contains(EXPERIENCE, regex=True, na=False)
    valid["가이드톤"] = vt.str.contains(GUIDE_TONE, regex=True, na=False)
    testimony = valid.sort_values(
        by=["경험서술", "가이드톤", "sponsored"],
        ascending=[False, True, True]).reset_index(drop=True)
    testimony.to_csv(DATA_DIR / "naver_testimony.csv", index=False, encoding="utf-8-sig")

    n_exp = int(valid["경험서술"].sum())
    print(f"\n[OK] 증언 후보 정렬 → data/naver_testimony.csv (경험 서술 {n_exp}건 상위 배치)")
    print("\n[상위 증언 후보 미리보기]")
    for _, r in testimony.head(5).iterrows():
        print(f"  [{r['axis']}] {str(r['review'])[:80]}")
