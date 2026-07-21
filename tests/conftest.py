# -*- coding: utf-8 -*-
"""공용 픽스처 — orchestrator 모듈 로드 + 정합적인 실수집 번들 생성기.

7차 교차검증에서 쓰인 변조 시나리오들을 영구 회귀 테스트로 만든 것.
번들은 매 테스트마다 tmp_path에 새로 만들어지므로 저장소의 data/를 건드리지 않는다.
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PIPELINE_DIR = ROOT / "dx_pipeline_v2.2"


@pytest.fixture(scope="session")
def moa():
    """moa_orchestrator 모듈 (import 부작용 없음이 전제 — L1 회귀 겸용)"""
    spec = importlib.util.spec_from_file_location("moa", ROOT / "moa_orchestrator.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert m.client is None and m.RUN_DIR is None, "import 부작용 회귀!"
    return m


def _w(path: Path, text: str):
    path.write_text(text, encoding="utf-8-sig")


@pytest.fixture
def bundle(tmp_path, moa):
    """계보 체인이 완전한 '실수집(google_play)' 번들.
    수치는 의미 정합성(Σ빈도=negative-noise, 언급률 재계산)까지 맞춰져 있다."""
    d = tmp_path / "data"
    d.mkdir()

    neg_rows = [(f"리뷰 {i} 알림이 안 와서 불편해요", 2) for i in range(36)]
    pos_rows = [(f"리뷰 {i} 편리하고 좋아요", 5) for i in range(36, 45)]
    rows = neg_rows + pos_rows

    _w(d / "reviews_raw.csv",
       "review,rating,date,likes,source_type\n"
       + "".join(f"{r},{s},2026-07-01,0,google_play\n" for r, s in rows))
    _w(d / "reviews_clean.csv",
       "review,rating,date,likes,source_type,tokens\n"
       + "".join(f"{r},{s},2026-07-01,0,google_play,{r}\n" for r, s in rows))
    # 빈도 합 36 = negative_count(36) - noise_count(0), 언급률 = 빈도/36*100 (1자리 반올림)
    _w(d / "painpoints.csv",
       "PainPoint(토픽),빈도,평균평점,언급률_전체부정기준(%),언급률_배정기준(%),대표리뷰\n"
       "T0_알림,16,2.0,44.4,44.4,대표 리뷰 영\n"
       "T1_연동,11,2.1,30.6,30.6,대표 리뷰 일\n"
       "T2_지연,9,2.2,25.0,25.0,대표 리뷰 이\n")
    _w(d / "strengths.csv",
       "대표리뷰,평점,좋아요\n원격 제어가 편리해요,5,3\n전기 사용량 확인 좋아요,4,0\n")

    f = moa._file_sha256
    meta = {"status": "ok", "run_id": "20260721_000000_000000",
            "raw_csv_hash": f(d / "reviews_raw.csv"), "source_type": "google_play",
            "app_id": "com.example.app", "collected_at": "2026-07-21T00:00:00",
            "n_reviews": 45, "warning": None}
    prep = {"run_id": meta["run_id"], "source_type": "google_play",
            "raw_csv_hash": meta["raw_csv_hash"],
            "clean_csv_hash": f(d / "reviews_clean.csv")}
    ppm = {"run_id": meta["run_id"], "source_type": "google_play",
           "clean_csv_hash": prep["clean_csv_hash"],
           "painpoints_csv_hash": f(d / "painpoints.csv"),
           "strengths_csv_hash": f(d / "strengths.csv"),
           "sentiment_method": "rating_fallback", "topic_method": "lda",
           "negative_count": 36, "noise_count": 0}
    for name, obj in (("metadata.json", meta), ("preprocess_meta.json", prep),
                      ("painpoints_meta.json", ppm)):
        (d / name).write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    return d


def edit_json(d: Path, name: str, **updates):
    p = d / name
    obj = json.loads(p.read_text(encoding="utf-8"))
    obj.update(updates)
    p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def rehash(d: Path, moa):
    """파일을 고의로 바꾼 뒤 해시 체인을 다시 정합하게 만들 때 사용
    (해시는 맞지만 내용이 비정상인 공격 시나리오 재현용)"""
    f = moa._file_sha256
    edit_json(d, "metadata.json", raw_csv_hash=f(d / "reviews_raw.csv"))
    edit_json(d, "preprocess_meta.json",
              raw_csv_hash=f(d / "reviews_raw.csv"),
              clean_csv_hash=f(d / "reviews_clean.csv"))
    edit_json(d, "painpoints_meta.json",
              clean_csv_hash=f(d / "reviews_clean.csv"),
              painpoints_csv_hash=f(d / "painpoints.csv"),
              strengths_csv_hash=f(d / "strengths.csv"))
