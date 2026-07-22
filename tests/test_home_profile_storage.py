# -*- coding: utf-8 -*-
"""온바디 저장·크기 예산 회귀 테스트 (Story 1.2).

Story 1.1 리뷰 교훈 적용: '단어 언급' 단언 금지. 왕복은 == 등가로, 리포트는
합산 정합으로, 거부는 정확한 개수·경로로 단언한다.

고정하는 것:
  1. 왕복 무손실 (AC3) — deserialize(serialize(p)) == p, 이후 재검증도 통과
  2. 크기 리포트 정합 (AC1·AC2) — 섹션 합 ≤ 전체, 기여 필드 경로가 실재
  3. 버전 불일치 명시 거부 (AC4) — 사유에 버전 문자열 포함, 조용한 통과 없음
  4. 예외 금지 계약 — 손상·잘림·비UTF8·타입 오류 전부 오류 목록으로
"""
import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from home_profile import (  # noqa: E402
    SCHEMA_VERSION, new_profile, validate_profile,
)
from home_profile import storage as st  # noqa: E402


@pytest.fixture(scope="module")
def small():
    return st.make_sample_profile(*st.SMALL)


@pytest.fixture(scope="module")
def typical():
    return st.make_sample_profile(*st.TYPICAL)


@pytest.fixture(scope="module")
def large():
    return st.make_sample_profile(*st.LARGE)


# ---------- 생성기 계약: 샘플은 스키마를 통과해야 한다 ----------
def test_samples_are_schema_valid(small, typical, large):
    for p in (small, typical, large):
        assert validate_profile(p) == []


def test_sample_shape_matches_request():
    p = st.make_sample_profile(7, 4)
    assert len(p["devices"]) == 7
    assert len(p["routines"]) == 4
    assert len(p["settings"]) == 7          # 기기당 설정 묶음 1개
    assert p["schema_version"] == SCHEMA_VERSION


def test_sample_zero_is_valid_and_empty():
    p = st.make_sample_profile(0, 0)
    assert validate_profile(p) == []
    assert p["devices"] == [] and p["routines"] == []


def test_sample_is_deterministic():
    """같은 인자면 같은 프로필 — 크기 실측이 재현 가능해야 한다"""
    assert st.make_sample_profile(5, 3) == st.make_sample_profile(5, 3)


# ---------- AC3: 왕복 무손실 ----------
def test_roundtrip_equality_all_samples(small, typical, large):
    for p in (small, typical, large, new_profile()):
        blob, errs = st.serialize(p)
        assert errs == []
        assert isinstance(blob, bytes)
        back, berrs = st.deserialize(blob)
        assert berrs == []
        assert back == p


def test_roundtrip_revalidates_clean(typical):
    blob, _ = st.serialize(typical)
    back, _ = st.deserialize(blob)
    assert validate_profile(back) == []


def test_roundtrip_preserves_scalar_types(small):
    p = dict(small)
    p["settings"] = dict(p["settings"])
    ref = p["devices"][0]["device_ref"]
    p["settings"][ref] = {"i": 26, "f": 1.5, "b": True, "s": "on"}
    blob, errs = st.serialize(p)
    assert errs == []
    back, _ = st.deserialize(blob)
    got = back["settings"][ref]
    assert got == {"i": 26, "f": 1.5, "b": True, "s": "on"}
    assert isinstance(got["i"], int) and isinstance(got["b"], bool)
    assert not isinstance(got["i"], bool)


def test_serialize_is_compact_utf8(typical):
    blob, _ = st.serialize(typical)
    assert b", " not in blob and b": " not in blob   # compact separators
    blob.decode("utf-8")                              # 유효 UTF-8


# ---------- 직렬화 게이트: 검증 미통과는 거부 ----------
def test_serialize_rejects_invalid_profile():
    p = new_profile()
    p["settings"]["ghost"] = {"power": "off"}      # 미등록 기기 참조
    blob, errs = st.serialize(p)
    assert blob is None
    assert len(errs) >= 1
    # 2차 리뷰 Vex F6: settings 키는 서수로 지목되고 원문은 재작성된다
    assert any("settings[#0]" in e and "devices에 없음" in e for e in errs)
    assert "ghost" not in " ".join(errs)


def test_serialize_rejects_pii_bearing_profile():
    """1.1 방어선이 직렬화 경로에서도 유효한지 — 와이어로 나가기 전 마지막 게이트"""
    p = st.make_sample_profile(2, 1)
    ref = p["devices"][0]["device_ref"]
    p["settings"][ref]["memo"] = "010-1234-5678"
    blob, errs = st.serialize(p)
    assert blob is None and errs


def test_serialize_never_raises_on_bad_input():
    for bad in (None, [], "profile", 42, {"schema_version": SCHEMA_VERSION}):
        blob, errs = st.serialize(bad)
        assert blob is None
        assert isinstance(errs, list) and errs


# ---------- AC4: 버전 불일치 명시 거부 ----------
def test_deserialize_rejects_unknown_version_with_version_in_reason():
    p = st.make_sample_profile(2, 1)
    raw = json.loads(json.dumps(p))
    raw["schema_version"] = "0.9.0"
    blob = json.dumps(raw, ensure_ascii=False).encode("utf-8")
    prof, errs = st.deserialize(blob)
    assert prof is None
    assert len([e for e in errs if "0.9.0" in e]) >= 1


def test_deserialize_rejects_missing_version():
    raw = json.loads(json.dumps(st.make_sample_profile(2, 1)))
    del raw["schema_version"]
    prof, errs = st.deserialize(json.dumps(raw).encode("utf-8"))
    assert prof is None and errs


def test_no_migration_hook_exists():
    """1.1 리뷰 F5: 아무도 읽지 않는 빈 레지스트리 재발 금지"""
    assert not hasattr(st, "MIGRATIONS")
    assert not hasattr(st, "migrate")


# ---------- 예외 금지 계약 ----------
def test_deserialize_never_raises(typical):
    good, _ = st.serialize(typical)
    cases = [
        b"",                                   # 0바이트
        b"{",                                  # 잘린 JSON
        good[: len(good) // 2],                # 중간 절단
        b"\xff\xfe\x00garbage",                # 비UTF-8
        b"[1,2,3]",                            # JSON이지만 객체 아님
        b'"just a string"',
        b"null",
        json.dumps({"a": 1}).encode(),         # 스키마 밖 객체
        b"\xef\xbb\xbf" + good,                # BOM 접두
    ]
    for data in cases:
        prof, errs = st.deserialize(data)
        assert isinstance(errs, list)
        if prof is None:
            assert errs, f"거부인데 사유 없음: {data[:20]!r}"


def test_deserialize_rejects_non_bytes():
    for bad in (None, 42, ["x"], {"a": 1}):
        prof, errs = st.deserialize(bad)
        assert prof is None and errs


def test_deserialize_accepts_str_only_if_documented(typical):
    """str 입력은 bytes가 아니므로 거부 — 계약을 흐리지 않는다"""
    blob, _ = st.serialize(typical)
    prof, errs = st.deserialize(blob.decode("utf-8"))
    assert prof is None and errs


def test_deep_nesting_payload_rejected_without_crash():
    """1.1의 깊이 폭탄이 저장 계층에서도 크래시가 아닌 거부여야 한다"""
    d = 1500
    blob = ('{"schema_version":"1.0.0","devices":[],"settings":{"a":'
            + '{"n":' * d + '{}' + '}' * d
            + '},"routines":[],"reserved_wellness":{}}').encode("utf-8")
    prof, errs = st.deserialize(blob)
    assert prof is None
    assert isinstance(errs, list) and errs


# ---------- AC1·AC2: 크기 리포트 ----------
def test_size_report_total_matches_serialized_length(typical):
    blob, _ = st.serialize(typical)
    rep, errs = st.size_report(typical)
    assert errs == []
    assert rep["total_bytes"] == len(blob)


def test_size_report_sections_do_not_exceed_total(small, typical, large):
    for p in (small, typical, large):
        rep, errs = st.size_report(p)
        assert errs == []
        assert sum(rep["sections"].values()) <= rep["total_bytes"]
        assert set(rep["sections"]) == {"devices", "settings", "routines"}


def test_size_report_per_unit_averages(typical):
    rep, _ = st.size_report(typical)
    n_dev = len(typical["devices"])
    assert rep["bytes_per_device"] == pytest.approx(
        rep["sections"]["devices"] / n_dev, rel=1e-6)
    assert rep["bytes_per_routine"] == pytest.approx(
        rep["sections"]["routines"] / len(typical["routines"]), rel=1e-6)


def test_size_report_zero_units_no_division_error():
    rep, errs = st.size_report(new_profile())
    assert errs == []
    assert rep["bytes_per_device"] is None
    assert rep["bytes_per_routine"] is None
    assert rep["total_bytes"] > 0


def test_top_contributors_are_real_paths(large):
    rep, _ = st.size_report(large)
    tops = rep["top_contributors"]
    assert 1 <= len(tops) <= 5
    prev = math.inf
    for entry in tops:
        assert entry["bytes"] <= prev            # 내림차순
        prev = entry["bytes"]
        # 2차 리뷰 Vex F6: 경로에 키 원문을 넣지 않는다 — 섹션+서수로 지목
        node = large[entry["section"]]
        seq = node if isinstance(node, list) else list(node.values())
        assert 0 <= entry["index"] < len(seq)
        assert len(st._dumps(seq[entry["index"]])) == entry["bytes"]


def test_budget_verdicts_are_reported_as_a_range(typical):
    """결정 ③ C: 단일 판정 금지 — 참조 예산 3종 각각에 single/split 병기"""
    rep, _ = st.size_report(typical)
    assert set(rep["budget_verdicts"]) == {"보수", "포럼", "공식"}
    for label, budget in st.BUDGET_REFERENCES:
        v = rep["budget_verdicts"][label]
        assert v["budget_bytes"] == budget
        assert v["single"] is (rep["total_bytes"] <= budget)
        assert v["split"] is (rep["max_section_bytes"] <= budget)
    # 근거 없는 MARGIN 단일 판정은 제거됐다 (2차 리뷰 Grumbal F4)
    assert not hasattr(st, "MARGIN")
    assert "within_key_budget" not in rep and "pct_of_key_budget" not in rep


def test_budget_verdict_flips_at_boundary(monkeypatch):
    """경계를 실제로 넘겨 판정이 뒤집히는지 — 스텁 방지"""
    p = st.make_sample_profile(3, 2)
    total = st.size_report(p)[0]["total_bytes"]
    monkeypatch.setattr(st, "BUDGET_REFERENCES", (("t", total + 1),))
    assert st.size_report(p)[0]["budget_verdicts"]["t"]["single"] is True
    monkeypatch.setattr(st, "BUDGET_REFERENCES", (("t", total - 1),))
    assert st.size_report(p)[0]["budget_verdicts"]["t"]["single"] is False


def test_max_section_is_the_largest_measured(typical):
    """결정 ⑤ A: 섹션 분할 판정의 기준은 가장 큰 섹션이다"""
    rep, _ = st.size_report(typical)
    assert rep["max_section"] in st.SECTION_KEYS
    assert rep["max_section_bytes"] == max(rep["sections"].values())
    assert rep["max_section_bytes"] <= rep["total_bytes"]


def test_ble_chunk_count(typical):
    rep, _ = st.size_report(typical)
    assert rep["ble_chunks"] == math.ceil(rep["total_bytes"] / st.BLE_MTU)
    assert st.BLE_MTU == 20


def test_size_report_never_raises_on_invalid():
    """검증 미통과 프로필에도 리포트는 나와야 한다 — 초과 원인 진단이 목적이므로"""
    for bad in (None, {"schema_version": "x"}, {"devices": None}):
        rep, errs = st.size_report(bad)
        assert isinstance(rep, dict) and isinstance(errs, list)
        assert "total_bytes" in rep
    # 직렬화 불가 값: v1은 total_bytes=0 -> 예산 내로 보고했다(fail-open)
    bad = st.make_sample_profile(3, 2)
    bad["devices"][0]["capabilities"] = {1, 2}
    rep, errs = st.size_report(bad)
    assert rep["total_bytes"] is None
    for v in rep["budget_verdicts"].values():
        assert v["single"] is None               # True가 아니다
    assert errs


def test_report_grows_monotonically_with_size(small, typical, large):
    a = st.size_report(small)[0]["total_bytes"]
    b = st.size_report(typical)[0]["total_bytes"]
    c = st.size_report(large)[0]["total_bytes"]
    assert a < b < c


# ---------- 대표 가정은 실측이 아님을 코드가 스스로 밝힌다 ----------
def test_assumption_constants_are_named_as_assumptions():
    """이름이 경험적 주장을 하지 않아야 한다 (2차 리뷰 Yui F5).
    죽은 불리언 상수 대신 이름 자체가 가정임을 말한다."""
    assert st.ASSUMED_TYPICAL == st.TYPICAL
    assert not hasattr(st, "SAMPLE_ASSUMPTIONS_ARE_MEASURED")
    assert not hasattr(st, "resolve_path")
    assert not hasattr(st, "format_report")


def test_package_exports_storage_api():
    import home_profile
    for name in ("serialize", "deserialize", "size_report"):
        assert name in home_profile.__all__
        assert hasattr(home_profile, name)
    # 샘플 생성기는 제품 표면이 아니다 (2차 리뷰 Yui F7)
    assert "make_sample_profile" not in home_profile.__all__


# ---------- 2차 리뷰 회귀 ----------
def test_oversized_wire_input_rejected_before_parsing():
    """기기 20만대·15.6MB가 통과하던 폭 제한 부재 (Vex F5)"""
    blob = b'{"x":"' + b"a" * (st.MAX_WIRE_BYTES + 10) + b'"}'
    prof, errs = st.deserialize(blob)
    assert prof is None
    assert len(errs) == 1 and "상한" in errs[0]


def test_duplicate_json_keys_rejected():
    """검증은 깨끗한 사본을 보고 통과시키는데 원본 바이트엔 PII가 남던 경로 (Vex F2)"""
    raw = (b'{"schema_version":"1.0.0",'
           b'"settings":{"dev000":{"memo":"hong@gmail.com"}},'
           b'"settings":{},'
           b'"devices":[],"routines":[],"reserved_wellness":{}}')
    prof, errs = st.deserialize(raw)
    assert prof is None
    assert any("중복 키" in e for e in errs)
    assert "hong@gmail.com" not in " ".join(errs)


def test_version_mismatch_message_is_bounded_and_redacted():
    """버전 메시지가 PII 스캔을 안 거친 채 무제한 에코되던 증폭 (Vex F4)"""
    raw = ('{"schema_version":"010-1234-5678","devices":[],"settings":{},'
           '"routines":[],"reserved_wellness":{}}').encode()
    prof, errs = st.deserialize(raw)
    assert prof is None
    assert "010-1234-5678" not in " ".join(errs)
    big = ('{"schema_version":"' + "9" * 200_000 + '","devices":[]}').encode()
    prof, errs = st.deserialize(big)
    assert prof is None
    assert max(len(e) for e in errs) < 500


def test_surrogate_payload_rejected_at_wire():
    """통과 후 저장·측정이 깨지던 고아 서로게이트 (Boundary F2)"""
    raw = ('{"schema_version":"1.0.0","devices":[{"device_ref":"a",'
           '"device_type":"x","capabilities":["p"]}],'
           '"settings":{"a":{"p":"\\ud800"}},"routines":[],'
           '"reserved_wellness":{}}').encode()
    prof, errs = st.deserialize(raw)
    assert prof is None and errs
