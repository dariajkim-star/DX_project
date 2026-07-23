# -*- coding: utf-8 -*-
"""Story 4.2 — 데이터 소재 명시 (FR7).

이 파일이 단언하는 것:
  1. 원본 위치·서버 미보유(AC1): server_holds_original=False, 온바디 명시,
     restorable_from_onbody=True(persist 후).
  2. 온바디 복원 증거: 캐리어만으로 복원 == 원본 → True. 빈 캐리어 → False.
  3. 서버 전송 없음(AC2): server_transmitted == [] ('없음').
  4. footprint 정확성 + 이름 비노출.
  5. 네트워크 0: enforce_offline + monkeypatch 둘 다.
  6. fail-closed.
"""
from home_profile import MemoryCarrier, data_residency, onboard_local
from home_profile.schema import new_profile


def _dev(ref, dtype, caps):
    return {"device_ref": ref, "device_type": dtype, "capabilities": list(caps)}


def _onboarded():
    """온보딩(4.1)으로 온바디에 저장된 프로필 + 캐리어."""
    carrier = MemoryCarrier()
    devices = [_dev("ac1", "air_conditioner", ["power", "target_temp"]),
               _dev("light1", "light", ["power"]),
               _dev("light2", "light", ["power"])]
    profile, report = onboard_local(devices, carrier)
    assert profile is not None and report["errors"] == []
    return profile, carrier


# ---------- AC1: 원본 위치·서버 미보유 ----------

def test_server_holds_no_original():
    profile, carrier = _onboarded()
    r = data_residency(profile, carrier)
    assert r["server_holds_original"] is False
    assert "온바디" in r["profile_location"]
    assert r["errors"] == []


def test_restorable_from_onbody_is_proof_original_is_there():
    """원본이 온바디에 있음의 증거 — 캐리어만으로 복원 == 원본."""
    profile, carrier = _onboarded()
    r = data_residency(profile, carrier)
    assert r["restorable_from_onbody"] is True


def test_empty_carrier_is_not_restorable():
    """캐리어가 비면(원본이 온바디에 없음) restorable=False로 정직 보고."""
    profile, _ = _onboarded()
    r = data_residency(profile, MemoryCarrier())      # 빈 캐리어
    assert r["restorable_from_onbody"] is False


# ---------- AC2: 서버 전송 없음 ----------

def test_server_transmitted_is_empty():
    profile, carrier = _onboarded()
    r = data_residency(profile, carrier)
    assert r["server_transmitted"] == []              # '없음'을 빈 목록으로 명시


# ---------- footprint 정확성 + 이름 비노출 ----------

def test_onbody_footprint_counts():
    profile, carrier = _onboarded()
    r = data_residency(profile, carrier)
    # meta 1 + device 3 + routine 0
    assert r["onbody_kinds"]["meta"] == 1
    assert r["onbody_kinds"]["device"] == 3
    assert r["onbody_kinds"]["routine"] == 0
    assert r["onbody_record_count"] == 4
    assert r["onbody_bytes"] > 0


def test_report_does_not_leak_raw_device_refs():
    """이름 비노출(함정 2): report 어디에도 raw device_ref 원문이 없다."""
    profile, carrier = _onboarded()
    r = data_residency(profile, carrier)
    blob = repr(r)
    for ref in ("ac1", "light1", "light2"):
        assert ref not in blob


# ---------- 네트워크 0 (두 겹) ----------

def test_residency_makes_no_network_calls(monkeypatch):
    import socket
    import urllib.request

    def _fail(*a, **k):                               # pragma: no cover
        raise AssertionError("소재 확인이 네트워크를 호출했다 — 자기모순")

    for mod, name in ((socket, "socket"), (socket, "create_connection"),
                      (socket, "getaddrinfo"), (urllib.request, "urlopen")):
        monkeypatch.setattr(mod, name, _fail)

    profile, carrier = _onboarded()
    r = data_residency(profile, carrier)
    assert r["restorable_from_onbody"] is True


def test_residency_under_offline_enforcement():
    from offline_guard import blocking_installed, enforce_offline

    profile, carrier = _onboarded()
    with enforce_offline():
        assert blocking_installed()
        r = data_residency(profile, carrier)
    assert r["errors"] == []
    assert r["server_holds_original"] is False


# ---------- fail-closed ----------

def test_invalid_profile_reports_error_without_raising():
    r = data_residency({"not": "a profile"}, MemoryCarrier())
    assert r["errors"]
    assert r["server_holds_original"] is False        # 기본값 유지


def test_never_raises_on_garbage():
    for bad in (None, 42, "profile", []):
        r = data_residency(bad, MemoryCarrier())
        assert isinstance(r, dict)
        assert r["errors"]


def test_empty_profile_residency():
    profile = new_profile()
    carrier = MemoryCarrier()
    from home_profile import persist_to_carrier
    assert persist_to_carrier(profile, carrier) == []
    r = data_residency(profile, carrier)
    assert r["server_holds_original"] is False
    assert r["restorable_from_onbody"] is True


# ---------- 데모 ----------

def test_demo_residency_output(capsys):
    import demo_residency

    assert demo_residency.main([]) == 0
    out = capsys.readouterr().out
    assert "서버" in out                              # 서버 미보유 표기
    assert "온바디" in out                            # 원본 위치
    assert "없음" in out                              # 서버 전송 없음(AC2)
