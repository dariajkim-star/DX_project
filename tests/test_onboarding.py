# -*- coding: utf-8 -*-
"""Story 4.1 — 무계정 로컬 전용 온보딩 (FR6).

이 파일이 단언하는 것:
  1. 무계정 완결(AC1): onboard_local이 계정/로그인 인자 없이 프로필 생성 +
     기기 연결 + 온바디 저장을 완료. 결과가 validate_profile 통과.
  2. 식별자 0(FR7 정합): 결과 profile에 find_identifier_violations 빈 목록.
  3. 네트워크 0(AC1 구조 증명): enforce_offline 강제 + monkeypatch 감시 둘 다.
  4. 동의 정직성(AC2): consent_scope 비어있지 않고 금지 문구 부재.
  5. fail-closed: 식별자 키 삽입·garbage → (None, report), 예외 없음.

P-3(6.2%) 반박: 무계정은 결함이 아니라 셀링포인트.
"""
from home_profile import (
    LOCAL_CONSENT_SCOPE,
    MemoryCarrier,
    NOT_REQUIRED,
    consent_scope_violations,
    find_identifier_violations,
    onboard_local,
    restore_from_carrier,
)
from home_profile.schema import validate_profile


def _dev(ref, dtype, caps):
    return {"device_ref": ref, "device_type": dtype, "capabilities": list(caps)}


def _devices():
    return [
        _dev("ac1", "air_conditioner", ["power", "target_temp"]),
        _dev("light1", "light", ["power"]),
    ]


# ---------- AC1: 무계정 완결 ----------

def test_onboarding_completes_without_account():
    carrier = MemoryCarrier()
    profile, report = onboard_local(_devices(), carrier)
    assert profile is not None
    assert validate_profile(profile) == []
    assert report["devices_connected"] == 2
    # 무계정은 '측정 안 한 리터럴'로 주장하지 않는다(코드리뷰 Vex+Yui) —
    # report는 관찰한 것(연결 수·동의 범위)만 담고, 계정 부재는 not_required로 명시.
    assert "account_created" not in report
    assert "network_calls" not in report


def test_onboarding_persists_to_carrier():
    """기기 연결 = 온바디 저장. 복원으로 왕복 확인(3.1 재사용)."""
    carrier = MemoryCarrier()
    profile, report = onboard_local(_devices(), carrier)
    assert report["errors"] == []
    restored, errs = restore_from_carrier(carrier)
    assert errs == []
    assert restored == profile


def test_onboard_signature_has_no_credential_params():
    """구조 증명: onboard_local 시그니처에 username/password/token 인자가 없다."""
    import inspect
    params = set(inspect.signature(onboard_local).parameters)
    assert params == {"devices", "carrier"}
    for forbidden in ("username", "password", "token", "email", "account", "login"):
        assert forbidden not in params


# ---------- AC1 정합: 식별자 0 (FR7) ----------

def test_onboarded_profile_has_zero_identifiers():
    carrier = MemoryCarrier()
    profile, _ = onboard_local(_devices(), carrier)
    assert find_identifier_violations(profile) == []


def test_onboarding_rejects_identifier_injection():
    """기기 정의에 식별자 키를 심으면 온보딩이 거부(조용히 떨궈 우회하지 않음)."""
    carrier = MemoryCarrier()
    bad = [{"device_ref": "ac1", "device_type": "air_conditioner",
            "capabilities": ["power"], "owner_name": "kim"}]
    profile, report = onboard_local(bad, carrier)
    assert profile is None
    assert report["errors"]


# ---------- AC1 구조 증명: 네트워크 0 (두 겹) ----------

def test_onboarding_makes_no_network_calls(monkeypatch):
    """겹 ① 감시(2.2 패턴): 온보딩 경로가 네트워크를 부르면 즉시 실패."""
    import socket
    import urllib.request

    def _fail(*a, **k):                           # pragma: no cover
        raise AssertionError("온보딩이 네트워크를 호출했다 — 무계정 구조 위반")

    for mod, name in ((socket, "socket"), (socket, "create_connection"),
                      (socket, "getaddrinfo"), (urllib.request, "urlopen")):
        monkeypatch.setattr(mod, name, _fail)

    carrier = MemoryCarrier()
    profile, report = onboard_local(_devices(), carrier)
    assert profile is not None
    assert report["errors"] == []          # 네트워크 안 부름 = monkeypatch가 증명(리터럴 아님)


def test_onboarding_succeeds_under_offline_enforcement():
    """겹 ② 강제(2.3 패턴): 차단 상태에서 성공해야 '서버를 부를 수 없다'가 증명된다."""
    from offline_guard import blocking_installed, enforce_offline

    carrier = MemoryCarrier()
    with enforce_offline():
        assert blocking_installed()
        profile, report = onboard_local(_devices(), carrier)
    assert profile is not None
    assert report["errors"] == []


# ---------- AC2: 동의 정직성 ----------

def test_consent_scope_is_nonempty_and_honest():
    """최소이되 명시 — 비어있지 않고, 계정·로그인성 항목이 없다."""
    assert LOCAL_CONSENT_SCOPE                     # 빈 목록 위장 금지
    assert consent_scope_violations() == []


def test_consent_scope_excludes_account_items():
    items = {c["item"] for c in LOCAL_CONSENT_SCOPE}
    for forbidden in ("account", "login", "email", "phone", "location",
                      "marketing", "cloud_backup"):
        assert forbidden not in items


def test_not_required_lists_account_and_login():
    """요구하지 않는 것 목록에 계정·로그인이 명시된다(대비 증거)."""
    items = {c["item"] for c in NOT_REQUIRED}
    assert "account" in items
    assert "login" in items


def test_consent_scope_violations_detects_bad_item():
    """감시가 실제로 계정성 항목을 잡는지 — 회귀 방지."""
    bad_scope = [{"item": "account_link", "purpose": "..."}]
    assert consent_scope_violations(bad_scope)
    empty_scope = []
    assert consent_scope_violations(empty_scope)   # 빈 목록도 위반


# ---------- fail-closed / 예외 금지 ----------

def test_onboarding_never_raises_on_garbage():
    carrier = MemoryCarrier()
    for bad in (None, 42, "devices", [None], [{"device_ref": 1}], [{"x": "y"}]):
        profile, report = onboard_local(bad, carrier)
        assert isinstance(report, dict)
        if profile is None:
            assert report["errors"]


def test_reonboarding_rejected():
    """코드리뷰 파티(#3): 이미 온보딩된 캐리어에 재온보딩은 거부된다 —
    put_records merge로 유령 레코드가 잔류하면 data_residency footprint가 실제
    온바디 저장량을 축소 보고(4.2 자기반증). 재설정은 폐기 후 별도 흐름."""
    carrier = MemoryCarrier()
    p1, r1 = onboard_local(_devices(), carrier)
    assert p1 is not None and r1["errors"] == []
    # 같은 캐리어에 다른 구성으로 재온보딩 시도
    p2, r2 = onboard_local([_dev("newdev", "styler", ["power"])], carrier)
    assert p2 is None
    assert r2["errors"]


def test_reonboarding_does_not_leave_ghost_records():
    """거부가 실제로 유령 레코드를 막는지 — 재온보딩 후에도 첫 프로필만 온바디에
    있고 residency footprint가 실제 저장량과 일치."""
    from home_profile import data_residency, restore_from_carrier
    carrier = MemoryCarrier()
    p1, _ = onboard_local(_devices(), carrier)
    onboard_local([_dev("newdev", "styler", ["power"])], carrier)   # 거부됨
    restored, errs = restore_from_carrier(carrier)
    assert errs == [] and restored == p1                # 첫 프로필 그대로
    r = data_residency(p1, carrier)
    # footprint(현재 프로필)가 실제 온바디 저장량과 일치(유령 없음)
    actual_onbody = sum(len(k.encode("utf-8")) + len(v)
                        for k, v in carrier._store.items())
    assert r["onbody_bytes"] == actual_onbody


def test_empty_devices_onboards_empty_profile():
    """기기 0대 온보딩 — 빈 프로필도 무계정으로 완결(유효)."""
    carrier = MemoryCarrier()
    profile, report = onboard_local([], carrier)
    assert profile is not None
    assert report["devices_connected"] == 0
    assert validate_profile(profile) == []


# ---------- 데모 (Task 3 계약 최소 고정) ----------

def test_demo_onboard_output(capsys):
    import demo_onboard

    assert demo_onboard.main([]) == 0
    out = capsys.readouterr().out
    assert "계정" in out                           # 계정 0 표기
    assert "요구하지 않" in out or "요구 안" in out  # 동의 대비 표기(AC2)
    assert "실기기 아님" in out or "참조 어댑터" in out  # 정직 표기(NFR6)
