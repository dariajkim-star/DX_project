# -*- coding: utf-8 -*-
"""
[크롤러 2/3] 네이버 키워드 매트릭스 수집 — 공식 검색 오픈 API
- 소스: 블로그·카페·지식iN (쿼리당 최대 1,100건 = API 상한 start 1000 + display 100)
- 키워드 매트릭스 v2: 제품축 × **4개 테마축**(집이바뀜/사람기기바뀜/경쟁대안/계정거부)
  — 주제 "집이 나를 따라온다"에 기여하는 사건을 캔다 (v1은 장애 현상만 반복 채굴했음)
- 축별 유효율 측정 내장: 시그널 패턴 + 제품어 동시 포함 비율, 기준선 18.8% 미달 시 재설계 판정
- 오염 필터: 옛 스마트폰 ThinQ(G6~G8 등) 글 제거. 협찬 블로그는 유지(팀 결정) 하되 컬럼으로 표시
- 산출: data/crawl_naver.csv + data/crawl_naver_yield.csv + data/crawl_naver_manifest.json
- 인증: 환경변수 NAVER_CLIENT_ID / NAVER_CLIENT_SECRET (https://developers.naver.com)
- 주의: API는 본문 전문이 아니라 제목+요약 스니펫을 반환함 (전문 크롤링은 별도 논의)

실행:
  python crawl_naver.py                          # 4축 매트릭스
  python crawl_naver.py --per-query 300          # 쿼리당 상한 조절
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# ---- 키워드 매트릭스 v2 (2026-07-21 재설계) ---------------------------------
# v1은 전 축이 "장애 현상"(연결 오류·서버 점검)이라 P-1만 반복 채굴했고,
# 그 영역은 이미 리뷰 17,446건이 충분히 커버한다. 주제("집이 나를 따라온다")에
# 기여하는 4개 테마로 재편 — 프로필이 따라다니지 못해 생긴 사건을 캔다.
PRODUCTS = ["씽큐", "ThinQ", "LG 가전", "LG 에어컨", "LG 세탁기"]

AXES = {
    # A. 집이 바뀌는 순간 — 헤드라인 직결
    "A_집이바뀜": ["이사 재설치", "이사 초기화", "이전설치", "공유기 바꾸니 연결",
                "인터넷 이전 연결", "신혼집 설치", "새 아파트 등록"],
    # B. 사람·기기가 바뀌는 순간 — P-2의 미채굴 변종 (프로필 소유권)
    "B_사람기기바뀜": ["폰 바꾸니 다시", "기기변경 재등록", "가족 공유 안됨",
                  "가족 초대", "계정 이전", "부모님 집 원격"],
    # C. 경쟁·대안 탐색 — 처방(온바디·개방 생태계)의 시장 근거
    "C_경쟁대안": ["스마트싱스 비교", "삼성 스마트홈 비교", "홈어시스턴트 연동",
               "구글홈 연동", "애플 홈킷", "워치로 제어"],
    # D. 계정·프라이버시 거부 — P-3 심층 + 온바디 셀링포인트 근거
    "D_계정거부": ["회원가입 없이", "계정 없이 제어", "개인정보 수집", "탈퇴",
               "약관 동의 강제"],
}

# 축별 유효율 판정 패턴 — 기준선 18.8%(v1 매트릭스의 P-2 실수율) 미달 축은 폐기 검토
AXIS_SIGNAL = {
    "A_집이바뀜": r"이사|이전\s*설치|공유기|인터넷\s*이전|신혼집|입주|새\s*집",
    "B_사람기기바뀜": r"폰\s*바꾸|기기\s*변경|기변|가족|공유|초대|계정\s*이전|부모님",
    "C_경쟁대안": r"스마트싱스|SmartThings|삼성|홈어시스턴트|Home\s*Assistant|구글홈|홈킷|워치",
    "D_계정거부": r"회원가입|계정|개인정보|탈퇴|약관",
}

SOURCES = ("blog", "cafearticle", "kin")
PHONE_NOISE = re.compile(r"G[5-9]\s*ThinQ|V[345]0\s*ThinQ|스냅드래곤|스마트폰.{0,10}(사양|스펙|출시)")
SPONSORED = re.compile(r"원고료|협찬|제공받아|체험단")


def api_call(source: str, query: str, start: int, cid: str, csec: str) -> list:
    url = (f"https://openapi.naver.com/v1/search/{source}.json"
           f"?query={urllib.parse.quote(query)}&display=100&start={start}&sort=sim")
    req = urllib.request.Request(url, headers={
        "X-Naver-Client-Id": cid, "X-Naver-Client-Secret": csec})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r).get("items", [])


def crawl(per_query: int) -> pd.DataFrame:
    cid = os.environ.get("NAVER_CLIENT_ID")
    csec = os.environ.get("NAVER_CLIENT_SECRET")
    if not (cid and csec):
        sys.exit("[ERR] NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 환경변수를 설정하세요.")

    rows, n_calls = [], 0
    queries = [(axis, f"{p} {kw}") for axis, kws in AXES.items()
               for p in PRODUCTS for kw in kws]
    print(f"[수집 시작] 4축 매트릭스 — 제품 {len(PRODUCTS)} × 키워드 {sum(len(v) for v in AXES.values())}"
          f" = {len(queries)}쿼리 × {len(SOURCES)}소스")

    for axis, q in queries:
        for src in SOURCES:
            got = 0
            for start in range(1, min(per_query, 1000) + 1, 100):
                try:
                    items = api_call(src, q, start, cid, csec)
                    n_calls += 1
                except Exception as e:
                    print(f"[WARN] {src} '{q}' 실패({type(e).__name__}) — 다음으로")
                    break
                for it in items:
                    text = re.sub(r"<[^>]+>", "", f"{it.get('title', '')} {it.get('description', '')}")
                    rows.append({"review": text, "axis": axis, "query": q,
                                 "origin": f"naver_{src}", "link": it.get("link"),
                                 "sponsored": bool(SPONSORED.search(text))})
                got += len(items)
                if len(items) < 100 or got >= per_query:
                    break
                time.sleep(0.1)  # 쿼터 예의
        print(f"  … [{axis}] '{q}' 누적 {len(rows)}건 (API {n_calls}콜)")

    df = pd.DataFrame(rows)
    if df.empty:
        sys.exit("[ERR] 수집 결과 0건")
    before = len(df)
    df = df.drop_duplicates(subset=["link"]).reset_index(drop=True)
    noise = df["review"].str.contains(PHONE_NOISE, na=False)
    df = df[~noise].reset_index(drop=True)
    print(f"[정제] 중복 {before - len(df) - noise.sum()}건, 스마트폰 오염 {noise.sum()}건 제거")
    return df


# 유효율 판정용 — 앱 자체를 언급해야 우리 도메인. "LG"만으로는 부족하다는 것을
# 눈검수로 확인(인터넷 가입 광고·LG전자 주식 분석이 "LG"에 대량 매칭됨, 2026-07-21).
APP_MENTION = r"씽큐|ThinQ|thinq"
OFF_TOPIC = (r"인터넷\s*(가입|설치|결합|이전)|사은품|현금\s*지원"
             r"|주식|종목|PBR|배당|씽큐베이션|서평|기자|보도자료")


def measure_yield(df: pd.DataFrame) -> pd.DataFrame:
    """축별 유효율 = (축 시그널 ∧ 앱 언급 ∧ ¬오프토픽) 비율.
    기준선 18.8%(v1 매트릭스 P-2 실수율) 미달 축은 키워드 재설계 대상."""
    rows = []
    for axis, pattern in AXIS_SIGNAL.items():
        sub = df[df["axis"] == axis]
        if sub.empty:
            continue
        text = sub["review"].astype(str)
        hit = text.str.contains(pattern, regex=True, na=False)
        app = text.str.contains(APP_MENTION, regex=True, na=False)
        off = text.str.contains(OFF_TOPIC, regex=True, na=False)
        valid = hit & app & ~off
        rows.append({
            "축": axis, "수집": len(sub),
            "시그널포함": int(hit.sum()),
            "앱언급": int(app.sum()),
            "오프토픽": int(off.sum()),
            "유효": int(valid.sum()),
            "유효율(%)": round(valid.mean() * 100, 1),
            "판정": "채택" if valid.mean() * 100 >= 18.8 else "재설계 검토",
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-query", type=int, default=200, help="쿼리·소스당 수집 상한(최대 1000)")
    args = ap.parse_args()

    df = crawl(args.per_query)
    out_csv = DATA_DIR / "crawl_naver.csv"
    df.to_csv(out_csv, index=False, encoding="utf-8-sig")

    # 축별 유효율 측정 — 기준선 18.8% 미달 축은 재설계 검토
    yield_df = measure_yield(df)
    yield_df.to_csv(DATA_DIR / "crawl_naver_yield.csv", index=False, encoding="utf-8-sig")
    print("\n[축별 유효율]")
    print(yield_df.to_string(index=False))

    h = hashlib.sha256(open(out_csv, "rb").read()).hexdigest()
    manifest = {
        "source": "naver_open_api(blog/cafearticle/kin)",
        "collected_at": datetime.now().isoformat(timespec="seconds"),
        "axis_yield": yield_df.to_dict("records"),
        "n_rows": len(df),
        "matrix": {"products": PRODUCTS, "axes": AXES},
        "by_origin": df["origin"].value_counts().to_dict(),
        "sponsored_rows": int(df["sponsored"].sum()),
        "csv_sha256": h,
    }
    with open(DATA_DIR / "crawl_naver_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)

    print(f"[완료] {len(df)}건 → {out_csv.name} (협찬 표시 {manifest['sponsored_rows']}건 포함)")
    print(f"  소스별: {manifest['by_origin']}")
