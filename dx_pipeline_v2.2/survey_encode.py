# -*- coding: utf-8 -*-
"""[DX 4단계 전처리] 구글폼 응답 → FEATURE_COLUMNS 인코딩 (v3)

구글폼이 내보내는 CSV는 컬럼명이 문항 제목 전체이고 값은 한글 텍스트다.
K-Means에 넣으려면 서열 숫자로 바꿔야 하는데, 그 매핑을 코드 밖에 두면
"어떤 보기를 몇 점으로 봤는지"가 사라진다 — 이 파일이 그 계약서다.

문항 정의: docs/SURVEY_PLAN.md §2 (v3) / 인코딩 규약: 같은 문서 §3

실행:
  python survey_encode.py                      # data/survey_raw.csv → data/survey.csv
  python survey_encode.py --in a.csv --out b.csv
"""
import sys

_enc = getattr(sys.stdout, "encoding", None)
if _enc and _enc.lower() != "utf-8" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # Windows cp949 콘솔 대응

import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# 문항 번호 → 인코딩 결과 컬럼명. 구글폼 CSV의 헤더는 문항 제목 전체라
# "1." 같은 접두사로 찾는다 ("13."은 "1."로 시작하지 않으므로 충돌 없음).
Q_PREFIX = {
    "q1": "1.", "q2": "2.", "q3": "3.", "q4": "4.", "q5": "5.", "q6": "6.",
    "q7": "7.", "q8": "8.", "q9": "9.", "q10": "10.",
    "q11_1": "11-1.", "q11_2": "11-2.", "q11_3": "11-3.",
    "q12": "12.", "q13": "13.", "q13_1": "13-1.", "q13_2": "13-2.",
    "q15": "15.",
}

MAP_Q1 = {"0대 (없음)": 0, "1대": 1, "2~3대": 2, "4대 이상": 3}
MAP_Q2 = {"사용해본 적 없음": 0, "설치만 해둠": 1, "월 1회 이하": 2, "주 1~2회": 3, "거의 매일": 4}
MAP_Q3 = {"20대 이하": 1, "30대": 2, "40대": 3, "50대": 4, "60대 이상": 5}
MAP_Q6 = {"있다": 1.0, "없다": 0.0, "아직 모르겠다": 0.5}
# v3: 금액이 아니라 성향 서열 (SURVEY_PLAN §2 v2→v3 변경 결정)
MAP_Q13 = {
    "무료가 아니면 쓰지 않겠다": 0,
    "무료로 써보고 괜찮으면 유료도 고려하겠다": 1,
    "유료라도 쓸 의향이 있다": 2,
}
# 자가/전월세 이진 밖은 결측 — H2 분석에서 제외된다 (SURVEY_PLAN §2)
# v3.1: 문5의 '기타'가 자유기입으로 바뀌어 임의 문자열이 들어온다. 결과는 어차피
#       결측이지만, **얼마나·무엇 때문에 잃는지 세는 것**이 자유기입을 켠 이유다.
MAP_Q5_TENURE = {"자가": 0.0, "전세": 1.0, "월세": 1.0}

FEATURE_COLUMNS = [
    "LG가전수",        # 문1: 1/2/3 서열 (0대는 스크리닝 아웃이라 분석 대상 아님)
    "앱사용빈도",      # 문2: 0~4
    "연령대",          # 문3: 1~5
    "자녀유무",        # 문4 파생: 0/1
    "점유형태_전월세",  # 문5 파생: 자가0/전월세1, 기타는 결측  ← H2
    "이사계획",        # 문6: 있다1/없다0/모름0.5              ← H2
    "구매계기_혼수",    # 문7 파생: 0/1
    "P1경험",          # 문8: 1~5
    "P2경험",          # 문9: 1~5
    "P3부담",          # 문10: 1~5
    "워치보유",        # 문11-1 파생: 0/1 (복수 선택 — '없음' 외 1개 이상이면 1)
    "야간사용",        # 문11-2: 1~5
    "온바디수용도",    # 문12: 1~5
    "지불의사",        # 문13: 0/1/2 성향 서열 (v3)
]


def find_col(df: pd.DataFrame, prefix: str) -> str:
    """문항 번호 접두사로 구글폼 컬럼을 찾는다."""
    hits = [c for c in df.columns if str(c).strip().startswith(prefix)]
    if not hits:
        raise KeyError(f"'{prefix}' 로 시작하는 컬럼을 찾을 수 없습니다. 헤더: {list(df.columns)[:5]}...")
    if len(hits) > 1:
        raise KeyError(f"'{prefix}' 접두사에 {len(hits)}개 컬럼이 걸립니다: {hits}")
    return hits[0]


def leading_int(s):
    """'4 자주 있다' → 4. 척도 문항은 라벨 앞 숫자가 곧 점수다."""
    if pd.isna(s):
        return np.nan
    m = re.match(r"\s*([1-5])", str(s))
    return int(m.group(1)) if m else np.nan


def map_strict(series: pd.Series, table: dict, qname: str) -> pd.Series:
    """매핑에 없는 값은 결측으로 두되 반드시 경고 — 조용한 누락이 제일 위험하다."""
    known = series.isna() | series.isin(table.keys())
    if not known.all():
        bad = sorted(set(series[~known].dropna()))
        print(f"[WARN] {qname}: 매핑에 없는 응답 {bad} → 결측 처리 "
              f"(문항이 바뀌었다면 survey_encode.py의 매핑을 갱신할 것)")
    return series.map(table)


def encode_tenure(series: pd.Series) -> pd.Series:
    """문5 → 자가0 / 전월세1 / 그 외 결측.

    v3.1에서 '기타'가 자유기입이 되어 임의 문자열이 들어온다. map_strict의
    '매핑을 갱신하라' 경고는 여기선 오해를 부른다 — 자유기입은 정상 입력이고,
    이진 밖이라 결측인 것뿐이다. 대신 **H2 표본을 얼마나 잃는지 집계해 보고**한다.
    """
    mapped = series.map(MAP_Q5_TENURE)
    lost = series[mapped.isna() & series.notna()]
    if len(lost):
        counts = lost.astype(str).str.strip().value_counts()
        pct = len(lost) / len(series) * 100
        print(f"[H2] 문5 이진 밖 응답 {len(lost)}/{len(series)}건 ({pct:.1f}%) → 결측 처리")
        for val, n in counts.items():
            print(f"      · {val}: {n}건")
        if pct >= 20:
            print("      ⚠️ 20% 이상이 이진 밖 — H2 검정력이 크게 깎인다. "
                  "보기 재설계를 검토할 것 (SURVEY_PLAN §2)")
    return mapped


def encode_survey(raw: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=raw.index)

    q1 = map_strict(raw[find_col(raw, Q_PREFIX["q1"])], MAP_Q1, "문1")
    out["LG가전수"] = q1
    out["앱사용빈도"] = map_strict(raw[find_col(raw, Q_PREFIX["q2"])], MAP_Q2, "문2")
    out["연령대"] = map_strict(raw[find_col(raw, Q_PREFIX["q3"])], MAP_Q3, "문3")

    q4 = raw[find_col(raw, Q_PREFIX["q4"])].fillna("")
    out["자녀유무"] = q4.str.contains("자녀 있음").astype(int)

    out["점유형태_전월세"] = encode_tenure(raw[find_col(raw, Q_PREFIX["q5"])])
    out["이사계획"] = map_strict(raw[find_col(raw, Q_PREFIX["q6"])], MAP_Q6, "문6")

    q7 = raw[find_col(raw, Q_PREFIX["q7"])].fillna("")
    out["구매계기_혼수"] = q7.str.contains("혼수").astype(int)

    out["P1경험"] = raw[find_col(raw, Q_PREFIX["q8"])].map(leading_int)
    out["P2경험"] = raw[find_col(raw, Q_PREFIX["q9"])].map(leading_int)
    out["P3부담"] = raw[find_col(raw, Q_PREFIX["q10"])].map(leading_int)

    # 체크박스 — 구글폼은 "애플워치, 가민"처럼 쉼표로 이어 붙인다.
    # '없음'만 고른 경우가 0, 하나라도 실제 기기가 있으면 1.
    q111 = raw[find_col(raw, Q_PREFIX["q11_1"])].fillna("")
    owns = q111.apply(
        lambda s: int(any(t.strip() and t.strip() != "없음" for t in str(s).split(","))))
    out["워치보유"] = owns

    out["야간사용"] = raw[find_col(raw, Q_PREFIX["q11_2"])].map(leading_int)
    out["온바디수용도"] = raw[find_col(raw, Q_PREFIX["q12"])].map(leading_int)
    out["지불의사"] = map_strict(raw[find_col(raw, Q_PREFIX["q13"])], MAP_Q13, "문13")

    # 군집 변수는 아니지만 교차 분석에 필요해 원문 그대로 실어 보낸다
    # 문5 원문도 실어 보낸다 — '기타' 자유기입 내용이 보기 재설계의 1차 근거다 (v3.1)
    for key, name in (("q5", "점유형태_원문"), ("q11_3", "상황선택_원문"),
                      ("q13_1", "걱정_원문"), ("q13_2", "과금형태_원문"),
                      ("q15", "유입채널")):
        try:
            out[name] = raw[find_col(raw, Q_PREFIX[key])]
        except KeyError:
            print(f"[WARN] {name}({Q_PREFIX[key]}) 컬럼 없음 — 건너뜀")

    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", default=str(DATA_DIR / "survey_raw.csv"),
                    help="구글폼에서 받은 원본 CSV")
    ap.add_argument("--out", dest="dst", default=str(DATA_DIR / "survey.csv"),
                    help="인코딩 결과 (04_segmentation.py 입력)")
    args = ap.parse_args()

    src = Path(args.src)
    if not src.exists():
        raise FileNotFoundError(
            f"{src} 없음 — 구글폼 응답 시트를 CSV로 내려받아 이 경로에 두세요.")

    raw = pd.read_csv(src)
    print(f"[OK] 원본 로드: {raw.shape}")

    # 스크리닝 아웃(0대)은 문2 이후가 통째로 비어 있어 군집에 넣을 수 없다
    q1col = find_col(raw, Q_PREFIX["q1"])
    n_before = len(raw)
    raw = raw[raw[q1col] != "0대 (없음)"].reset_index(drop=True)
    if n_before != len(raw):
        print(f"[OK] 스크리닝 아웃 {n_before - len(raw)}건 제외 → {len(raw)}건")

    enc = encode_survey(raw)

    n_nan = int(enc[FEATURE_COLUMNS].isna().sum().sum())
    print(f"[INFO] 군집 변수 결측 {n_nan}개")
    tenure_na = int(enc["점유형태_전월세"].isna().sum())
    if tenure_na:
        pct = tenure_na / len(enc) * 100
        print(f"[WARN] 점유형태 '기타' {tenure_na}건({pct:.0f}%) — H2 검증 표본에서 빠집니다")

    Path(args.dst).parent.mkdir(parents=True, exist_ok=True)
    enc.to_csv(args.dst, index=False, encoding="utf-8-sig")
    print(f"[OK] 저장: {args.dst} {enc.shape}")


if __name__ == "__main__":
    main()
