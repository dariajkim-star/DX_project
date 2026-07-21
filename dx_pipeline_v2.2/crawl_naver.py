# -*- coding: utf-8 -*-
"""
[크롤러 2/3] 네이버 키워드 매트릭스 수집 — 공식 검색 오픈 API
- 소스: 블로그·카페·지식iN (쿼리당 최대 1,100건 = API 상한 start 1000 + display 100)
- 키워드 매트릭스: 제품축 × Pain축 — 주제(P-2 설정 휘발) 집중 기본값 내장
- 오염 필터: 옛 스마트폰 ThinQ(G6~G8 등) 글 제거. 협찬 블로그는 유지(팀 결정) 하되 컬럼으로 표시
- 산출: data/crawl_naver.csv + data/crawl_naver_manifest.json
- 인증: 환경변수 NAVER_CLIENT_ID / NAVER_CLIENT_SECRET (https://developers.naver.com)
- 주의: API는 본문 전문이 아니라 제목+요약 스니펫을 반환함 (전문 크롤링은 별도 논의)

실행:
  python crawl_naver.py                          # 기본 매트릭스 (P-2 집중)
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

# ---- 키워드 매트릭스 (주제 기여 기준으로 설계) -------------------------------
# 제품축: ThinQ 연동 주력 제품
PRODUCTS = ["씽큐", "ThinQ", "LG 에어컨 앱", "LG 세탁기 앱", "LG 로봇청소기 앱"]
# Pain축: P-2(설정 휘발·재등록) 집중 + P-1/P-3 보조 — 실측 워드클라우드에서 역산
PAINS = ["재등록", "초기화", "기기 등록 안됨", "이사", "설정 사라짐",
         "연결 오류", "서버 점검", "로그인 안됨"]

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
    queries = [f"{p} {pain}" for p in PRODUCTS for pain in PAINS]
    print(f"[수집 시작] 매트릭스 {len(PRODUCTS)}제품 × {len(PAINS)}Pain = {len(queries)}쿼리 × {len(SOURCES)}소스")

    for q in queries:
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
                    rows.append({"review": text, "query": q, "origin": f"naver_{src}",
                                 "link": it.get("link"),
                                 "sponsored": bool(SPONSORED.search(text))})
                got += len(items)
                if len(items) < 100 or got >= per_query:
                    break
                time.sleep(0.1)  # 쿼터 예의
        print(f"  … '{q}' 누적 {len(rows)}건 (API {n_calls}콜)")

    df = pd.DataFrame(rows)
    if df.empty:
        sys.exit("[ERR] 수집 결과 0건")
    before = len(df)
    df = df.drop_duplicates(subset=["link"]).reset_index(drop=True)
    noise = df["review"].str.contains(PHONE_NOISE, na=False)
    df = df[~noise].reset_index(drop=True)
    print(f"[정제] 중복 {before - len(df) - noise.sum()}건, 스마트폰 오염 {noise.sum()}건 제거")
    return df


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-query", type=int, default=200, help="쿼리·소스당 수집 상한(최대 1000)")
    args = ap.parse_args()

    df = crawl(args.per_query)
    out_csv = DATA_DIR / "crawl_naver.csv"
    df.to_csv(out_csv, index=False, encoding="utf-8-sig")

    h = hashlib.sha256(open(out_csv, "rb").read()).hexdigest()
    manifest = {
        "source": "naver_open_api(blog/cafearticle/kin)",
        "collected_at": datetime.now().isoformat(timespec="seconds"),
        "n_rows": len(df),
        "matrix": {"products": PRODUCTS, "pains": PAINS},
        "by_origin": df["origin"].value_counts().to_dict(),
        "sponsored_rows": int(df["sponsored"].sum()),
        "csv_sha256": h,
    }
    with open(DATA_DIR / "crawl_naver_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)

    print(f"[완료] {len(df)}건 → {out_csv.name} (협찬 표시 {manifest['sponsored_rows']}건 포함)")
    print(f"  소스별: {manifest['by_origin']}")
