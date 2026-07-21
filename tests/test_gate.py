# -*- coding: utf-8 -*-
"""orchestrator 계보 게이트(_validate_bundle) 회귀 테스트.
GPT 교차검증 3~7차에서 실제로 뚫렸거나 시도된 변조 시나리오를 고정한다.
각 테스트는 '해시까지 정합하게 위조'한 뒤에도 게이트가 잡는지를 본다."""
import json

from conftest import edit_json, rehash


def ok(moa, d):
    return isinstance(moa._validate_bundle(d), tuple)


def reason(moa, d):
    v = moa._validate_bundle(d)
    assert not isinstance(v, tuple), "거부됐어야 하는데 통과함"
    return v


# ---------- 정상 경로 ----------

def test_valid_bundle_passes(moa, bundle):
    v = moa._validate_bundle(bundle)
    assert isinstance(v, tuple)
    meta, ppm, n_strengths = v
    assert meta["source_type"] == "google_play"
    assert n_strengths == 2


# ---------- source_type / 실수집 일관성 (7차 H2) ----------

def test_reject_synthetic_metadata(moa, bundle):
    edit_json(bundle, "metadata.json", source_type="synthetic_demo")
    assert "실데이터 아님" in reason(moa, bundle)


def test_reject_raw_column_synthetic(moa, bundle):
    raw = (bundle / "reviews_raw.csv").read_text(encoding="utf-8-sig")
    (bundle / "reviews_raw.csv").write_text(
        raw.replace("google_play", "synthetic_demo"), encoding="utf-8-sig")
    rehash(bundle, moa)
    assert "reviews_raw.csv의 source_type" in reason(moa, bundle)


def test_reject_clean_column_synthetic(moa, bundle):
    clean = (bundle / "reviews_clean.csv").read_text(encoding="utf-8-sig")
    (bundle / "reviews_clean.csv").write_text(
        clean.replace("google_play", "synthetic_demo"), encoding="utf-8-sig")
    rehash(bundle, moa)
    assert "reviews_clean.csv의 source_type" in reason(moa, bundle)


def test_reject_demo_warning_present(moa, bundle):
    edit_json(bundle, "metadata.json", warning="합성 데모 데이터")
    assert "warning" in reason(moa, bundle)


def test_reject_missing_app_id(moa, bundle):
    edit_json(bundle, "metadata.json", app_id=None)
    assert "app_id" in reason(moa, bundle)


def test_reject_n_reviews_mismatch(moa, bundle):
    edit_json(bundle, "metadata.json", n_reviews=999)
    assert "n_reviews" in reason(moa, bundle)


def test_reject_preprocess_source_mismatch(moa, bundle):
    edit_json(bundle, "preprocess_meta.json", source_type="synthetic_demo")
    assert "preprocess_meta" in reason(moa, bundle)


# ---------- run_id / 해시 체인 (4~5차) ----------

def test_reject_run_id_all_missing(moa, bundle):
    for name in ("metadata.json", "preprocess_meta.json", "painpoints_meta.json"):
        edit_json(bundle, name, run_id=None)
    assert "run_id 누락" in reason(moa, bundle)


def test_reject_run_id_mismatch(moa, bundle):
    edit_json(bundle, "painpoints_meta.json", run_id="99999999_999999_000000")
    assert "run_id 불일치" in reason(moa, bundle)


def test_reject_raw_hash_link_broken(moa, bundle):
    edit_json(bundle, "preprocess_meta.json", raw_csv_hash="RAW-B")
    assert "raw_csv_hash" in reason(moa, bundle)


def test_reject_tampered_painpoints_without_rehash(moa, bundle):
    pp = (bundle / "painpoints.csv").read_text(encoding="utf-8-sig")
    (bundle / "painpoints.csv").write_text(pp.replace(",16,", ",999,"),
                                           encoding="utf-8-sig")
    assert "painpoints.csv 실파일 해시" in reason(moa, bundle)


def test_reject_metadata_json_list(moa, bundle):
    (bundle / "metadata.json").write_text("[]", encoding="utf-8")
    assert "객체가 아님" in reason(moa, bundle)  # AttributeError 크래시 회귀 방지


# ---------- painpoints 내용 검증 (5~6차) ----------

def test_reject_empty_painpoints_even_with_valid_hash(moa, bundle):
    (bundle / "painpoints.csv").write_text(
        "PainPoint(토픽),빈도,평균평점,언급률_전체부정기준(%),언급률_배정기준(%),대표리뷰\n",
        encoding="utf-8-sig")
    rehash(bundle, moa)
    assert "데이터 행 없음" in reason(moa, bundle)


def test_reject_noninteger_freq(moa, bundle):
    pp = (bundle / "painpoints.csv").read_text(encoding="utf-8-sig")
    (bundle / "painpoints.csv").write_text(pp.replace(",16,", ",16.5,"),
                                           encoding="utf-8-sig")
    rehash(bundle, moa)
    assert "빈도 비정상" in reason(moa, bundle)


def test_reject_assigned_mention_out_of_range(moa, bundle):
    pp = (bundle / "painpoints.csv").read_text(encoding="utf-8-sig")
    (bundle / "painpoints.csv").write_text(pp.replace(",44.4,대표", ",999,대표"),
                                           encoding="utf-8-sig")
    rehash(bundle, moa)
    assert "언급률(배정) 비정상" in reason(moa, bundle)


def test_reject_blank_rep_review(moa, bundle):
    pp = (bundle / "painpoints.csv").read_text(encoding="utf-8-sig")
    (bundle / "painpoints.csv").write_text(pp.replace("대표 리뷰 영", ""),
                                           encoding="utf-8-sig")
    rehash(bundle, moa)
    assert "대표리뷰 공백" in reason(moa, bundle)


def test_reject_freq_sum_vs_meta_counts(moa, bundle):
    edit_json(bundle, "painpoints_meta.json", negative_count=100)
    assert "빈도 합" in reason(moa, bundle)


def test_reject_recomputed_mention_mismatch(moa, bundle):
    pp = (bundle / "painpoints.csv").read_text(encoding="utf-8-sig")
    (bundle / "painpoints.csv").write_text(pp.replace("16,2.0,44.4", "16,2.0,40.0"),
                                           encoding="utf-8-sig")
    rehash(bundle, moa)
    assert "재계산값" in reason(moa, bundle)


# ---------- strengths (7차: sentiment_method별 평점 정책) ----------

def test_strengths_rating_policy_by_method(moa, bundle):
    s = (bundle / "strengths.csv").read_text(encoding="utf-8-sig")
    (bundle / "strengths.csv").write_text(s.replace(",5,3", ",1,3"),
                                          encoding="utf-8-sig")
    rehash(bundle, moa)
    # rating_fallback 모드에선 평점 1 강점은 모순 → 거부
    assert "4~5" in reason(moa, bundle)
    # deep_learning 모드에선 저평점 긍정 가능 → 허용
    edit_json(bundle, "painpoints_meta.json", sentiment_method="deep_learning")
    assert ok(moa, bundle)


def test_strengths_zero_rows_downgrades_not_rejects(moa, bundle):
    (bundle / "strengths.csv").write_text("대표리뷰,평점,좋아요\n", encoding="utf-8-sig")
    rehash(bundle, moa)
    v = moa._validate_bundle(bundle)
    assert isinstance(v, tuple) and v[2] == 0


def test_reject_zero_byte_strengths(moa, bundle):
    (bundle / "strengths.csv").write_bytes(b"")
    rehash(bundle, moa)
    assert "strengths.csv" in reason(moa, bundle)
