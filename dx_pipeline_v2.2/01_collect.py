# -*- coding: utf-8 -*-
"""
[DX 1단계] 데이터 수집 (v2.8)
- 구글 플레이 앱 리뷰 크롤링 (예: LG ThinQ)
- v2.2: 데이터 계보(lineage) 분리 — 샘플 데이터는 --demo 옵션으로만 생성.
  실수집 실패 시 기본 동작은 '중단'(샘플로 위장하지 않음).
  data/metadata.json 에 출처·수집조건·시각 기록.
실행: python 01_collect.py            (실데이터, 실패 시 에러 종료)
      python 01_collect.py --demo     (합성 샘플 45건 — 데모/발표 전용)
출력: data/reviews_raw.csv, data/metadata.json
"""
import sys
_enc = getattr(sys.stdout, "encoding", None)
if _enc and _enc.lower() != "utf-8" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # Windows cp949 콘솔 대응
import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

APP_ID = "com.lgeha.nuts"  # LG ThinQ 앱. 플레이스토어 URL의 id= 값으로 교체
N_REVIEWS = 500


def collect_from_playstore() -> pd.DataFrame:
    from google_play_scraper import Sort, reviews
    result, _ = reviews(APP_ID, lang="ko", country="kr", sort=Sort.NEWEST, count=N_REVIEWS)
    df = pd.DataFrame(result)[["content", "score", "at", "thumbsUpCount"]]
    df.columns = ["review", "rating", "date", "likes"]
    return df


def sample_data() -> pd.DataFrame:
    """데모 전용 합성 샘플 45건. 토픽(알림 미인지/안전/연동/지연/UI)이 의도적으로
    심어진 데이터이므로, 이 데이터의 분석 결과는 '파이프라인 동작 검증'이지
    실제 고객 인사이트가 아님."""
    rows = [
        # 알림 미인지 (청각)
        ("세탁 끝난 알림을 못 들어서 빨래를 몇 시간씩 방치하게 돼요", 2),
        ("알림이 소리로만 와서 청각장애인인 저는 확인이 불가능합니다", 1),
        ("건조기 완료음을 듣지 못해 옷이 구겨진 채로 방치됩니다", 2),
        ("초인종 소리를 못 들어서 택배를 계속 놓칩니다", 1),
        ("알림 소리를 못 듣는 사람을 위한 화면 점멸 기능이 필요합니다", 2),
        ("세탁기 완료 알림을 진동 기기로 받고 싶은데 방법이 없네요", 2),
        ("전자레인지 조리 완료를 알 방법이 없어 음식이 식어버려요", 2),
        ("집안일 하다 보면 스마트폰 알림도 놓치기 일쑤입니다", 3),
        # 안전 불안
        ("화재경보가 울려도 진동으로 알려주는 기능이 없어서 불안해요", 1),
        ("가스 경고를 소리로만 알려줘서 위험한 상황이 걱정됩니다", 1),
        ("혼자 있을 때 위험 상황을 인지할 수단이 없어 무섭습니다", 1),
        ("긴급 상황에 보호자에게 자동으로 연락되는 기능이 있으면 좋겠어요", 3),
        ("야간에 경보가 울려도 자고 있으면 전혀 알 수가 없어요", 1),
        # 연동/안정성
        ("연동이 자꾸 끊겨서 다시 등록해야 해요", 2),
        ("와이파이 바꾸면 기기 등록을 처음부터 다시 해야 하나요", 2),
        ("허브 연결이 하루에도 몇 번씩 끊깁니다", 1),
        ("기기 추가할 때마다 오류가 나서 서너 번씩 시도합니다", 2),
        ("업데이트 후 등록된 가전이 전부 사라졌어요", 1),
        # 알림 지연/품질
        ("앱 연동은 좋은데 알림이 너무 늦게 와요", 3),
        ("알림이 실시간이 아니라 십 분 뒤에 도착합니다", 2),
        ("어떤 날은 알림이 아예 안 오는 날도 있어요", 2),
        # UI/사용성
        ("알림 설정 메뉴가 너무 복잡하고 깊숙이 숨어있어요", 2),
        ("글씨가 작아서 부모님이 보기 힘들어하세요", 3),
        ("메뉴 구조가 복잡해서 원하는 기능 찾기가 어렵습니다", 2),
        ("음성 명령이 인식이 잘 안 됩니다", 2),
        ("음성 안내만 있고 자막이 없어서 내용을 알 수 없습니다", 2),
        # 긍정 (강점 유지 포인트)
        ("가전 상태를 앱에서 확인할 수 있어 편리해요", 5),
        ("부모님 댁 가전 상태를 원격으로 볼 수 있어 안심돼요", 5),
        ("에어컨 예약 기능은 정말 만족합니다", 5),
        ("UI가 직관적이라 부모님도 쉽게 쓰세요", 4),
        ("외출 중에 세탁기를 돌릴 수 있어 시간이 절약됩니다", 5),
        ("전기 사용량을 한눈에 보여줘서 좋아요", 4),
        ("여러 브랜드 기기를 한 앱에서 관리하니 편합니다", 4),
        ("위젯으로 바로 제어할 수 있는 점이 마음에 들어요", 4),
        ("고객센터 응대가 빨라서 만족스러웠습니다", 4),
        # 기타 요구
        ("스마트워치와 연동해서 진동 알림을 받고 싶어요", 3),
        ("수어 안내 영상이 있으면 이해가 훨씬 쉬울 것 같아요", 3),
        ("알림 우선순위를 위험도별로 나눠주면 좋겠습니다", 3),
        ("가족 구성원별로 알림을 다르게 설정하고 싶어요", 3),
        ("조명 깜빡임으로 알림을 대신할 수 있게 해주세요", 2),
        ("TV 화면에 알림 배너를 띄워주는 기능이 필요해요", 3),
        ("문 열림 감지 알림이 너무 자주 와서 피로합니다", 3),
        ("앱 실행 속도가 느려서 급할 때 답답합니다", 2),
        ("위험 알림만큼은 무조건 진동과 화면으로 왔으면 합니다", 2),
        ("청각장애인 모드를 공식 기능으로 만들어 주세요", 2),
    ]
    df = pd.DataFrame(rows, columns=["review", "rating"])
    df["date"] = pd.Timestamp("2026-07-01")
    df["likes"] = 0
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true",
                        help="합성 샘플 데이터 사용 (데모/발표 전용, 실데이터 아님)")
    args = parser.parse_args()

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")  # v2.5: 동시 실행 충돌 방지

    if args.demo:
        df = sample_data()
        source_type = "synthetic_demo"
        print("[DEMO] 합성 샘플 데이터 사용 — 분석 결과는 실제 고객 인사이트가 아닙니다.")
    else:
        try:
            df = collect_from_playstore()
            source_type = "google_play"
            print(f"[OK] 플레이스토어에서 {len(df)}건 수집")
        except Exception as e:
            # v2.3: 실패 사실을 metadata에 기록 — 과거 산출물(reviews_raw.csv 등)이
            # data/에 남아 있어도 02단계가 status를 보고 재사용을 거부하게 함
            with open(DATA_DIR / "metadata.json", "w", encoding="utf-8") as f:
                json.dump({"status": "collect_failed", "run_id": run_id,
                           "failed_at": datetime.now().isoformat(timespec="seconds"),
                           "error": f"{type(e).__name__}: {e}"},
                          f, ensure_ascii=False, indent=2)
            raise RuntimeError(
                f"실데이터 수집 실패({type(e).__name__}: {e}).\n"
                f"  기존 data/ 산출물은 무효 처리되었습니다(metadata.status=collect_failed).\n"
                f"  데모 데이터로 진행하려면 명시적으로: python 01_collect.py --demo"
            ) from e

    df["source_type"] = source_type
    df.to_csv(DATA_DIR / "reviews_raw.csv", index=False, encoding="utf-8-sig")

    from lineage import file_sha256
    metadata = {
        "status": "ok",
        "run_id": run_id,
        "raw_csv_hash": file_sha256(DATA_DIR / "reviews_raw.csv"),  # v2.4 계보 체인 시작
        "source_type": source_type,
        "app_id": APP_ID if source_type == "google_play" else None,
        "collected_at": datetime.now().isoformat(timespec="seconds"),
        "n_reviews": len(df),
        "warning": None if source_type == "google_play" else
                   "합성 데모 데이터 — 보고서에 실데이터 분석 결과로 인용 금지",
    }
    with open(DATA_DIR / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(df.head())
    print(f"\n저장 완료: data/reviews_raw.csv ({len(df)}건, source={source_type})")
    print(f"메타데이터: data/metadata.json")
    print(f"평점 분포:\n{df['rating'].value_counts().sort_index()}")
