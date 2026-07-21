# -*- coding: utf-8 -*-
"""
[크롤러 1/3] 플레이스토어 리뷰 전량 수집 — continuation token 페이지네이션
- 대상: LG ThinQ 앱 (기본). --app-id 로 다른 앱도 수집 가능
- 01_collect.py(단발 5,000건)와 달리 토큰을 이어가며 상한까지 전량 수집
- 산출: data/crawl_playstore_<앱별칭>.csv + 동일 이름 _manifest.json (계보용 해시 포함)

실행:
  python crawl_playstore.py                      # ThinQ 30,000건 상한
  python crawl_playstore.py --max 50000
  python crawl_playstore.py --app-id com.other.app --alias otherapp
"""
import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

DEFAULT_APP_ID = "com.lgeha.nuts"  # LG ThinQ
BATCH = 200  # google-play-scraper 권장 페이지 크기


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def crawl(app_id: str, max_reviews: int) -> pd.DataFrame:
    from google_play_scraper import Sort, reviews

    all_rows, token = [], None
    while len(all_rows) < max_reviews:
        count = min(BATCH, max_reviews - len(all_rows))
        result, token = reviews(app_id, lang="ko", country="kr",
                                sort=Sort.NEWEST, count=count,
                                continuation_token=token)
        if not result:
            break
        all_rows.extend(result)
        if len(all_rows) % 2000 < BATCH:
            print(f"  … {len(all_rows)}건 (최고 {all_rows[-1]['at']:%Y-%m-%d}까지 도달)")
        if token is None:  # 더 이상 페이지 없음 = 전량 도달
            break

    df = pd.DataFrame(all_rows)[["content", "score", "at", "thumbsUpCount"]]
    df.columns = ["review", "rating", "date", "likes"]
    df = df.drop_duplicates(subset=["review", "date"]).reset_index(drop=True)
    return df


def run(app_id: str, alias: str, max_reviews: int) -> Path:
    """수집→저장→manifest 기록. crawl_smartthings.py도 이 함수를 재사용한다."""
    print(f"[수집 시작] {app_id} (상한 {max_reviews}건)")
    df = crawl(app_id, max_reviews)

    out_csv = DATA_DIR / f"crawl_playstore_{alias}.csv"
    df.to_csv(out_csv, index=False, encoding="utf-8-sig")

    manifest = {
        "source": "google_play_public_reviews",
        "app_id": app_id,
        "collected_at": datetime.now().isoformat(timespec="seconds"),
        "n_reviews": len(df),
        "date_range": [str(df["date"].min()), str(df["date"].max())],
        "rating_dist": df["rating"].value_counts().sort_index().to_dict(),
        "csv_sha256": file_sha256(out_csv),
    }
    with open(DATA_DIR / f"crawl_playstore_{alias}_manifest.json", "w",
              encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)

    print(f"[완료] {len(df)}건 → {out_csv.name}")
    print(f"  기간: {manifest['date_range'][0]} ~ {manifest['date_range'][1]}")
    print(f"  평점 분포: {manifest['rating_dist']}")
    return out_csv


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--app-id", default=DEFAULT_APP_ID)
    ap.add_argument("--alias", default="thinq", help="산출 파일명에 쓸 앱 별칭")
    ap.add_argument("--max", type=int, default=30000, help="수집 상한")
    args = ap.parse_args()
    run(args.app_id, args.alias, args.max)
