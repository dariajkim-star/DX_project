# -*- coding: utf-8 -*-
"""홈 프로필 스키마 회귀 테스트 (Story 1.1).

고정하는 것:
  1. 필수 필드 구성 — 기기·설정·루틴·스키마 버전 (AC1)
  2. 웰니스 예약 — 값을 넣어도 해석 로직이 없다 (AC2, NFR5 의료 규제)
  3. 버전 계약 — 모르는 버전은 조용히 통과하지 않는다 (AC3)
  4. 식별자 부재 — 이름·계정·연락처 필드는 설계상 존재할 수 없다 (AC4, FR7 선행)

테스트 픽스처는 tests/test_panel.py의 _write_bundle 패턴을 따른다:
유효한 최소 프로필을 만드는 헬퍼를 두고 케이스마다 변조한다.
"""
import importlib.util
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


# ---------- AC1: 필수 필드 구성 ----------
def test_valid_profile_passes(hp):
    assert hp.validate_profile(_make_profile(hp)) == []


def test_required_top_level_fields(hp):
    """최상위 필수 키가 빠지면 각각 위반으로 보고된다"""
    for key in ("schema_version", "devices", "settings", "routines"):
        p = _make_profile(hp)
        del p[key]
        errs = hp.validate_profile(p)
        assert any(key in e for e in errs), f"{key} 누락이 보고되지 않음: {errs}"


def test_device_requires_ref_and_type(hp):
    p = _make_profile(hp)
    del p["devices"][0]["device_ref"]
    assert any("device_ref" in e for e in hp.validate_profile(p))


def test_routine_requires_trigger_and_actions(hp):
    p = _make_profile(hp)
    del p["routines"][0]["trigger"]
    assert any("trigger" in e for e in hp.validate_profile(p))


def test_routine_action_must_reference_known_device(hp):
    """존재하지 않는 기기를 가리키는 루틴은 조용히 통과하면 안 된다"""
    p = _make_profile(hp)
    p["routines"][0]["actions"][0]["device_ref"] = "ghost"
    errs = hp.validate_profile(p)
    assert any("ghost" in e for e in errs), errs


def test_duplicate_device_ref_rejected(hp):
    """device_ref는 프로필 내 매칭 키 — 중복이면 복원(3.1)이 비결정적이 된다"""
    p = _make_profile(hp)
    p["devices"][1]["device_ref"] = "d1"
    assert any("d1" in e for e in hp.validate_profile(p))


def test_unknown_top_level_key_rejected(hp):
    """조용한 확장 금지 (NFR6) — 미지 키는 거부"""
    p = _make_profile(hp)
    p["cloud_account"] = {"id": "x"}
    assert any("cloud_account" in e for e in hp.validate_profile(p))


# ---------- AC2: 웰니스 예약 (NFR5) ----------
def test_reserved_wellness_is_declared(hp):
    """예약 필드는 스키마에 선언되어 있다"""
    assert "reserved_wellness" in hp.TOP_LEVEL_KEYS


def test_reserved_wellness_must_stay_empty(hp):
    """값을 넣으면 거부한다 — '일단 파싱만 해두자'가 곧 규제 위반의 시작"""
    p = _make_profile(hp)
    p["reserved_wellness"] = {"sleep_score": 82}
    errs = hp.validate_profile(p)
    assert any("reserved_wellness" in e for e in errs), errs


def test_no_wellness_interpretation_functions(hp):
    """모듈에 웰니스를 해석·판단하는 공개 함수가 존재하지 않는다 (NFR5)"""
    banned = ("wellness_score", "interpret_wellness", "diagnose",
              "assess_health", "evaluate_wellness")
    for name in banned:
        assert not hasattr(hp, name), f"NFR5 위반: {name} 존재"


# ---------- AC3: 버전·마이그레이션 ----------
def test_schema_version_is_semver(hp):
    parts = hp.SCHEMA_VERSION.split(".")
    assert len(parts) == 3 and all(x.isdigit() for x in parts)


def test_new_profile_stamps_version(hp):
    assert hp.new_profile()["schema_version"] == hp.SCHEMA_VERSION


def test_unknown_version_rejected(hp):
    """모르는 버전은 조용히 통과 금지"""
    assert hp.is_supported(hp.SCHEMA_VERSION) is True
    assert hp.is_supported("99.0.0") is False
    p = _make_profile(hp)
    p["schema_version"] = "99.0.0"
    assert any("99.0.0" in e for e in hp.validate_profile(p))


def test_malformed_version_rejected(hp):
    for bad in ("1.0", "v1.0.0", "", "abc"):
        assert hp.is_supported(bad) is False


def test_migrations_registry_exists(hp):
    """마이그레이션 경로가 열려 있다 — 1.0.0은 등록분 없음"""
    assert isinstance(hp.MIGRATIONS, dict)
    assert hp.SCHEMA_VERSION not in hp.MIGRATIONS


# ---------- AC4: 식별자 부재 증명 (FR7 선행) ----------
def test_schema_itself_has_no_identifier_fields(hp):
    """스키마 자신을 통과시켜 '설계상 부재'를 기계 증명한다"""
    assert hp.assert_no_identifiers(hp.new_profile()) == []


def test_identifier_injection_detected(hp):
    for bad_key in ("name", "user_name", "account_id", "email",
                    "phone", "birth_date", "user_id"):
        p = _make_profile(hp)
        p["settings"]["d1"][bad_key] = "홍길동"
        found = hp.assert_no_identifiers(p)
        assert found, f"{bad_key} 미검출"
        assert any(bad_key in f for f in found)


def test_identifier_detected_in_nested_list(hp):
    """중첩 리스트 안에 숨겨도 재귀 순회로 잡는다"""
    p = _make_profile(hp)
    p["routines"][0]["actions"][0]["owner_email"] = "a@b.c"
    assert hp.assert_no_identifiers(p)


def test_validate_profile_rejects_identifiers(hp):
    """검증 함수가 식별자 검사를 포함한다 — 별도로 부르는 걸 잊어도 막힌다"""
    p = _make_profile(hp)
    p["devices"][0]["account_id"] = "acc-1"
    assert any("account_id" in e for e in hp.validate_profile(p))


def test_identifier_check_is_case_insensitive(hp):
    p = _make_profile(hp)
    p["settings"]["d1"]["Email"] = "a@b.c"
    assert hp.assert_no_identifiers(p)


# ---------- 구조 계약 (BLE 20바이트 MTU 대응) ----------
def test_profile_is_chunkable_by_top_level_lists(hp):
    """devices/routines가 각각 독립 직렬화 가능해야 한다 (20바이트 MTU → 청크 전송).
    프로토콜 구현은 Story 1.2·Epic 2 범위 — 여기서는 구조만 고정한다."""
    import json
    p = _make_profile(hp)
    for d in p["devices"]:
        json.loads(json.dumps(d, ensure_ascii=False))
    for r in p["routines"]:
        json.loads(json.dumps(r, ensure_ascii=False))


def test_validate_profile_returns_all_violations(hp):
    """여러 위반을 한 번에 보고한다 — 사람이 판단하려면 목록이어야 한다"""
    p = _make_profile(hp)
    del p["devices"]
    p["schema_version"] = "99.0.0"
    p["surprise"] = 1
    assert len(hp.validate_profile(p)) >= 3


def test_non_dict_profile_rejected(hp):
    for bad in (None, [], "profile", 42):
        assert hp.validate_profile(bad)
