# -*- coding: utf-8 -*-
"""홈 프로필 스키마 회귀 테스트 (Story 1.1, 리뷰 반영 v2).

v1 테스트의 결함(2026-07-22 Code Review Crew 적발): 단언 대부분이
'단어가 에러 메시지에 언급됐는지'만 봐서 **검증 로직 0줄짜리 스텁이 23/23 통과**했다.
v2 원칙:
  - 유효 프로필은 정확히 0건, 단일 결함 프로필은 **정확히 그 결함만** 보고돼야 한다
    (표류 방지: 위반 수까지 고정)
  - 계약 고정: validate_profile은 어떤 입력에도 **예외를 던지지 않는다**
    (unhashable·순환·깊은 중첩 전부 위반 목록으로)
  - 우회 케이스를 직접 재현: 값 PII·한국어 키·호모글리프·중첩 미지 키·null 스킵
"""
import importlib.util
import json
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def hp():
    spec = importlib.util.spec_from_file_location(
        "hp_schema", ROOT / "home_profile" / "schema.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _make_profile(hp):
    """유효한 최소 프로필 — 케이스마다 이걸 변조해서 쓴다."""
    return {
        "schema_version": hp.SCHEMA_VERSION,
        "devices": [
            {"device_ref": "d1", "device_type": "air_conditioner",
             "capabilities": ["power", "target_temp"]},
            {"device_ref": "d2", "device_type": "light", "capabilities": ["power"]},
        ],
        "settings": {"d1": {"target_temp": 26}, "d2": {"power": "off"}},
        "routines": [
            {"trigger": {"type": "time", "params": {"at": "23:00"}},
             "actions": [{"device_ref": "d1", "setting_key": "target_temp", "value": 26},
                         {"device_ref": "d2", "setting_key": "power", "value": "off"}]},
        ],
        "reserved_wellness": {},
    }


def _errs(hp, p):
    out = hp.validate_profile(p)
    assert isinstance(out, list)
    return out


# ---------- 계약: 유효 프로필 = 정확히 0건 ----------
def test_valid_profile_exactly_zero_violations(hp):
    assert _errs(hp, _make_profile(hp)) == []


def test_new_profile_is_valid_and_fresh(hp):
    a, b = hp.new_profile(), hp.new_profile()
    assert _errs(hp, a) == []
    a["devices"].append({"device_ref": "x1", "device_type": "light"})
    assert b["devices"] == []  # 컨테이너 공유 금지


# ---------- 계약: 어떤 입력에도 예외 금지 ----------
def test_never_raises_on_unhashable_ref(hp):
    """v1 결함: device_ref가 list/dict면 TypeError로 크래시했다"""
    for bad in (["a"], {"a": 1}):
        p = _make_profile(hp)
        p["devices"][0]["device_ref"] = bad
        errs = _errs(hp, p)  # 예외가 아니라 목록
        assert errs, f"{type(bad).__name__} ref가 무보고 통과"


def test_never_raises_on_deep_nesting(hp):
    """v1 결함: 깊이 1000 중첩(~10KB)이 RecursionError로 검증기를 죽였다"""
    d = 1200
    payload = json.loads('{"n":' * d + '{}' + '}' * d)
    p = _make_profile(hp)
    p["settings"]["d1"] = payload
    errs = _errs(hp, p)
    assert any("깊이" in e for e in errs)


def test_never_raises_on_circular_reference(hp):
    """v1 결함: 순환 참조가 무조건 크래시했다"""
    p = _make_profile(hp)
    p["settings"]["d1"] = {}
    p["settings"]["d1"]["loop"] = p
    errs = _errs(hp, p)
    assert any("순환" in e for e in errs)


# ---------- v1 결함: null이 검증을 통째로 껐다 ----------
def test_null_section_is_a_violation_not_a_skip(hp):
    """devices:null이면 구조·참조 검사 전체가 스킵돼 유령 참조가 통과했다"""
    p = _make_profile(hp)
    p["devices"] = None
    errs = _errs(hp, p)
    assert any("devices" in e for e in errs)
    # null 뒤에 숨은 유령 참조도 함께 보고돼야 한다 — settings의 d1/d2가 미확인
    for key in ("settings", "routines"):
        p2 = _make_profile(hp)
        p2[key] = None
        assert any(key in e for e in _errs(hp, p2)), f"{key}:null 무보고 통과"


def test_null_device_ref_is_a_violation(hp):
    """v1 결함: ref:null이 중복 검사·유령 참조 검사를 동시에 껐다"""
    p = _make_profile(hp)
    p["devices"][0]["device_ref"] = None
    assert any("device_ref" in e for e in _errs(hp, p))


def test_null_trigger_and_empty_actions_rejected(hp):
    p = _make_profile(hp)
    p["routines"][0]["trigger"] = None
    assert any("trigger" in e for e in _errs(hp, p))
    p2 = _make_profile(hp)
    p2["routines"][0]["actions"] = []
    assert any("actions" in e for e in _errs(hp, p2))


# ---------- AC1: 필수 필드·참조 정합 ----------
def test_each_missing_required_key_reported_exactly_once(hp):
    for key in ("schema_version", "devices", "settings", "routines",
                "reserved_wellness"):
        p = _make_profile(hp)
        del p[key]
        errs = _errs(hp, p)
        hits = [e for e in errs if key in e and "누락" in e]
        assert len(hits) == 1, f"{key}: {errs}"


def test_ghost_reference_reported(hp):
    p = _make_profile(hp)
    p["routines"][0]["actions"][0]["device_ref"] = "ghost9"
    errs = _errs(hp, p)
    assert len([e for e in errs if "ghost9" in e]) == 1


def test_duplicate_device_ref_reported(hp):
    p = _make_profile(hp)
    p["devices"][1]["device_ref"] = "d1"
    errs = _errs(hp, p)
    hits = [e for e in errs if "중복" in e and "devices[1]" in e]
    assert len(hits) == 1, errs
    # 2차 리뷰 Vex F3: 메시지에 값 원문이 들어가면 안 된다 — 위치와 재작성만
    assert "'d1'" not in hits[0] and "<str len=2" in hits[0]


def test_settings_ghost_device_reported(hp):
    p = _make_profile(hp)
    p["settings"]["ghost7"] = {"power": "on"}
    errs = _errs(hp, p)
    # settings 키는 사용자 통제 문자열 — 서수로 지목하고 원문은 재작성한다(Vex F6)
    hits = [e for e in errs if "settings[#2]" in e and "devices에 없음" in e]
    assert len(hits) == 1, errs
    assert "ghost7" not in " ".join(errs)


def test_numeric_device_ref_rejected(hp):
    """숫자 ref는 JSON 객체 키(항상 문자열)에서 영구 참조 불가 — 토큰 형식 강제"""
    p = _make_profile(hp)
    p["devices"][0]["device_ref"] = 1
    p["settings"] = {"d2": {"power": "off"}}
    assert any("device_ref" in e for e in _errs(hp, p))


# ---------- NFR6: 미지 키 거부 — 이제 전 레벨 ----------
def test_unknown_key_rejected_at_every_level(hp):
    cases = [
        lambda p: p.update({"cloud_account": 1}),
        lambda p: p["devices"][0].update({"ssid": "KimFamily_5G"}),
        lambda p: p["routines"][0].update({"extra": 1}),
        lambda p: p["routines"][0]["trigger"].update({"geo": [37.49, 127.03]}),
        lambda p: p["routines"][0]["actions"][0].update({"lat": 37.49}),
    ]
    for i, mutate in enumerate(cases):
        p = _make_profile(hp)
        mutate(p)
        errs = _errs(hp, p)
        assert any("미지" in e for e in errs), f"case{i}: {errs}"


def test_exactly_one_violation_for_single_unknown_key(hp):
    """스텁 방지: 위반 '수'까지 고정한다"""
    p = _make_profile(hp)
    p["surprise"] = 1
    assert len(_errs(hp, p)) == 1


# ---------- AC4/FR7: 식별자 차단 — 키와 **값** ----------
def test_pii_in_values_detected(hp):
    """v1 결함: 검사가 키만 봐서 값 PII가 전부 통과했다"""
    cases = [
        ("email값", lambda p: p["settings"]["d1"].update(
            {"memo": "hong.gildong@gmail.com"})),
        ("전화값", lambda p: p["settings"]["d1"].update({"memo": "010-1234-5678"})),
        ("주민번호값", lambda p: p["settings"]["d1"].update(
            {"memo": "900101-1234567"})),
        ("한국어PII값", lambda p: p["routines"][0]["trigger"]["params"].update(
            {"at": "홍길동 이름으로 예약"})),
    ]
    for label, mutate in cases:
        p = _make_profile(hp)
        mutate(p)
        errs = _errs(hp, p)
        assert errs, f"{label} 무보고 통과"


def test_pii_as_settings_key_rejected(hp):
    """이메일이 dict 키로 들어와도 잡힌다 (v1: 'gmail'≠'email'이라 통과)"""
    p = _make_profile(hp)
    p["devices"].append({"device_ref": "hong.gildong@gmail.com",
                         "device_type": "light"})
    assert _errs(hp, p)  # 토큰 형식 위반으로 거부


def test_korean_identifier_keys_rejected(hp):
    """v1 결함: 금지어가 영어뿐이라 '이름'·'전화번호' 키가 통과했다"""
    for bad in ("이름", "전화번호", "주소록"):
        p = _make_profile(hp)
        p["settings"]["d1"][bad] = "x"
        assert _errs(hp, p), f"{bad} 무보고 통과"


def test_homoglyph_key_rejected(hp):
    """v1 결함: 키릴 а가 섞인 'аccount_id'가 통과했다 — 비ASCII 키 자체를 거부"""
    p = _make_profile(hp)
    p["settings"]["d1"]["аccount_id"] = "x"
    assert _errs(hp, p)


def test_english_identifier_keys_still_rejected(hp):
    for bad in ("user_name", "account_id", "email", "phone", "birth_date"):
        p = _make_profile(hp)
        p["settings"]["d1"][bad] = "x"
        assert _errs(hp, p), f"{bad} 무보고 통과"


def test_location_and_hardware_ids_rejected(hp):
    """ssid+좌표는 이메일보다 강한 가구 식별자다 (Vex)"""
    for bad in ("ssid", "mac", "serial", "imei", "lat", "lon", "latitude"):
        p = _make_profile(hp)
        p["settings"]["d1"][bad] = "v"
        assert _errs(hp, p), f"{bad} 무보고 통과"


def test_find_identifier_violations_reports_path(hp):
    p = _make_profile(hp)
    p["settings"]["d1"]["email"] = "a@b.c"
    found = hp.find_identifier_violations(p)
    assert len(found) >= 1
    assert any("email" in f for f in found)


def test_identifier_scan_runs_even_when_structure_broken(hp):
    """v1 결함: 구조 검사 크래시가 PII 스캔을 선점했다 — 이제 둘 다 보고된다"""
    p = _make_profile(hp)
    p["devices"][0]["device_ref"] = ["unhashable"]
    p["settings"]["d1"]["email"] = "a@b.c"
    errs = _errs(hp, p)
    assert any("email" in e for e in errs)


# ---------- 2차 리뷰: 제로폭 은닉 / 메시지 유출 / 정수 우회 ----------
_HIDDEN = [
    "hong" + chr(0xFEFF) + "@gmail.com",
    "hong" + chr(0x200B) + "@gmail.com",
    "010-1234" + chr(0x200B) + "-5678",
    "a" + chr(0x00AD) + "b" + chr(0x2060) + "c",
]


def test_zero_width_hidden_pii_rejected(hp):
    """제로폭 한 글자로 PII 정규식이 무력화되던 통로 (Vex F1)"""
    for hidden in _HIDDEN:
        p = _make_profile(hp)
        p["settings"]["d1"]["memo"] = hidden
        assert _errs(hp, p), f"{hidden!r} 무보고 통과"


def test_surrogate_in_value_rejected(hp):
    """UTF-8 인코딩 불가 — 통과 후 저장·측정이 깨지던 경로 (Boundary F2)"""
    p = _make_profile(hp)
    p["settings"]["d1"]["memo"] = chr(0xD800)
    assert _errs(hp, p)


def test_violation_messages_never_echo_untrusted_values(hp):
    """거부 사유가 PII 운반체가 되면 안 된다 (Vex F3) — 게이트가 막은 걸 로그가 흘린다"""
    secrets = ("hong.gildong@gmail.com", "010-1234-5678", "900101-1234567")
    cases = [
        lambda p, s: p["devices"][0].update({"device_type": s}),
        lambda p, s: p["settings"].update({s: {"power": "off"}}),
        lambda p, s: p["settings"]["d1"].update({s: 1}),
        lambda p, s: p["routines"][0]["actions"][0].update({"setting_key": s}),
        lambda p, s: p.update({"reserved_wellness": {s: 1}}),
        lambda p, s: p.update({"schema_version": s}),
    ]
    for secret in secrets:
        for i, mutate in enumerate(cases):
            p = _make_profile(hp)
            mutate(p, secret)
            errs = _errs(hp, p)
            assert errs, f"case{i} 무보고 통과"
            blob = " ".join(errs)
            assert secret not in blob, f"case{i}가 원문 유출: {blob[:120]}"


def test_version_message_is_length_bounded(hp):
    """5MB 페이로드가 500만자 에러 문자열을 만들던 증폭 (Vex F4)"""
    p = _make_profile(hp)
    p["schema_version"] = "9" * 100_000
    errs = _errs(hp, p)
    assert errs
    assert max(len(e) for e in errs) < 500


def test_huge_integer_value_rejected(hp):
    """_MAX_STR이 정수로 우회되던 구멍 (Boundary F4)"""
    p = _make_profile(hp)
    p["settings"]["d1"]["target_temp"] = int("9" * 4000)
    assert _errs(hp, p)
    p2 = _make_profile(hp)
    p2["settings"]["d1"]["target_temp"] = 26        # 정상값은 통과
    assert _errs(hp, p2) == []


# ---------- AC2/NFR5: 웰니스 봉쇄 — 앞문과 옆문 ----------
def test_reserved_wellness_must_exist_and_stay_empty(hp):
    p = _make_profile(hp)
    p["reserved_wellness"] = {"sleep_score": 82}
    assert any("reserved_wellness" in e for e in _errs(hp, p))
    p2 = _make_profile(hp)
    del p2["reserved_wellness"]  # v1 결함: 키를 빼면 검사가 스킵됐다
    assert any("reserved_wellness" in e for e in _errs(hp, p2))


def test_wellness_data_in_settings_rejected(hp):
    """v1 결함: 옆문 — settings에 웰니스 데이터가 자유 투입됐다"""
    for bad in ("sleep_score", "hrv", "body_fat_pct", "bp_systolic",
                "heart_rate", "spo2"):
        p = _make_profile(hp)
        p["settings"]["d1"][bad] = 82
        assert _errs(hp, p), f"{bad} 무보고 통과"


# ---------- AC3: 버전 ----------
def test_unknown_and_malformed_versions_rejected(hp):
    assert hp.is_supported(hp.SCHEMA_VERSION) is True
    for bad in ("99.0.0", "1.0", "v1.0.0", "", "abc", None, 1.0):
        assert hp.is_supported(bad) is False, bad
    p = _make_profile(hp)
    p["schema_version"] = "99.0.0"
    errs = _errs(hp, p)
    assert len([e for e in errs if "99.0.0" in e]) == 1


# ---------- 직렬화 가능성 (Story 1.2 계약) ----------
def test_unserializable_values_rejected(hp):
    """v1 결함: set 값이 검증을 통과하고 json.dumps에서 터졌다"""
    p = _make_profile(hp)
    p["settings"]["d1"]["target_temp"] = {1, 2}
    assert _errs(hp, p)


def test_nonfinite_float_rejected(hp):
    p = _make_profile(hp)
    p["settings"]["d1"]["target_temp"] = math.nan
    assert _errs(hp, p)


def test_valid_profile_roundtrips_json(hp):
    p = _make_profile(hp)
    assert json.loads(json.dumps(p, ensure_ascii=False)) == p
    assert _errs(hp, json.loads(json.dumps(p, ensure_ascii=False))) == []


# ---------- 다중 위반 전수 보고 ----------
def test_multiple_violations_all_reported(hp):
    p = _make_profile(hp)
    del p["devices"]
    p["schema_version"] = "99.0.0"
    p["surprise"] = 1
    errs = _errs(hp, p)
    assert any("devices" in e for e in errs)
    assert any("99.0.0" in e for e in errs)
    assert any("surprise" in e for e in errs)


def test_non_dict_profile_rejected(hp):
    for bad in (None, [], "profile", 42):
        assert _errs(hp, bad)


# ---------- 패키지 표면 (v1: import home_profile이 0회 실행됐다) ----------
def test_package_imports_and_all_is_consistent():
    import sys
    sys.path.insert(0, str(ROOT))
    try:
        import home_profile
        for nm in home_profile.__all__:
            assert hasattr(home_profile, nm), nm
        assert "MIGRATIONS" not in home_profile.__all__  # 죽은 상수는 표면에서 제거됨
        assert "SUPPORTED_VERSIONS" in home_profile.__all__
    finally:
        sys.path.remove(str(ROOT))
