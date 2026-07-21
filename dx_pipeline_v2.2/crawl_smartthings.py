# -*- coding: utf-8 -*-
"""
[크롤러 3/3] 삼성 SmartThings 리뷰 수집 — 경쟁 대조군
- 목적: P-2(설정 휘발) 경쟁 비교 실증 — "삼성 껀 그대로인데" 인용의 규모 확인,
  프로필 보존·연결 안정성에서 ThinQ 대비 우위/열위 정량화
- 방식: crawl_playstore.run() 재사용 (1주제 1파일 — 이 파일은 대조군 담당)
- 산출: data/crawl_playstore_smartthings.csv + _manifest.json

실행:
  python crawl_smartthings.py            # 10,000건 상한 (대조군은 본군보다 작게)
  python crawl_smartthings.py --max 30000
"""
import argparse

from crawl_playstore import run

SMARTTHINGS_APP_ID = "com.samsung.android.oneconnect"

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=10000, help="수집 상한")
    args = ap.parse_args()
    run(SMARTTHINGS_APP_ID, "smartthings", args.max)
