# -*- coding: utf-8 -*-
"""Story 4.4 — 분실·양도 시 프로필 폐기 (NFR2).

이 파일이 단언하는 것:
  1. 폐기 후 복원 불가(AC1): restore_from_carrier 실패, restorable_after=False(실측).
  2. 잔류 0 + 제어 불가(AC1): 캐리어 비고, 폐기 후 가전 상태 불변.
  3. 서버 없는 폐기(AC2): enforce_offline 안 성공 + monkeypatch 0건.
  4. 복구(AC3): 폐기 후 재온보딩 성공 — 4.1 재온보딩 거부가 폐기로 해제된다.
  5. fail-closed: 빈 캐리어·garbage carrier → 예외 없이 보고.
  6. 문서 회귀: REVOCATION.md의 복구 시나리오 + 잔여 한계(원격 소거 아님).

⚠️ 폐기의 의미는 '레코드 삭제'가 아니라 **'그 프로필로 가전을 못 연다'**이다.
"""
from appliance_sim.core import ApplianceState
from home_profile import (
    MemoryCarrier,
    data_residency,
    onboard_local,
    restore_from_carrier,
    revoke_onbody,
)


def _dev(ref, dtype, caps):
    return {"device_ref": ref, "device_type": dtype, "capabilities": list(caps)}


def _devices():
    return [_dev("ac1", "air_conditioner", ["power", "target_temp"]),
            _dev("light1", "light", ["power"])]


def _onboarded():
    carrier = MemoryCarrier()
    profile, report = onboard_local(_devices(), carrier)
    assert profile is not None and report["errors"] == []
    return profile, carrier


# ---------- AC1: 폐기 후 복원 불가·제어 불가 ----------

def test_revoke_makes_profile_unrestorable():
    profile, carrier = _onboarded()
    assert restore_from_carrier(carrier)[0] == profile      # 폐기 전엔 복원됨

    ok, report = revoke_onbody(carrier)
    assert ok
    assert report["restorable_after"] is False              # 실측 결과
    restored, errs = restore_from_carrier(carrier)
    assert restored is None and errs                        # 복원 실패


def test_revoke_leaves_no_residue():
    _, carrier = _onboarded()
    ok, report = revoke_onbody(carrier)
    assert ok
    assert carrier._store == {}                             # 잔류 0
    assert report["records_erased"] > 0


def test_after_revoke_appliance_control_does_not_happen():
    """폐기의 의미 = 제어 불가. 복원이 실패하므로 명령 경로가 성립하지 않고
    가전 상태는 불변이다."""
    _, carrier = _onboarded()
    appliance = ApplianceState("ac1", "air_conditioner", ["power"])
    revoke_onbody(carrier)

    restored, errs = restore_from_carrier(carrier)
    assert restored is None and errs                        # 프로필을 못 얻는다
    # 프로필이 없으니 명령을 만들 근거가 없다 — 상태 불변 확인
    assert appliance.snapshot()["state"]["power"] is None


def test_residency_shows_nothing_onbody_after_revoke():
    """4.2 소재 확인과의 정합: 폐기 후엔 온바디에서 복원 불가로 보고된다."""
    profile, carrier = _onboarded()
    revoke_onbody(carrier)
    r = data_residency(profile, carrier)
    assert r["restorable_from_onbody"] is False


# ---------- AC2: 서버 없는 폐기 ----------

def test_revoke_under_offline_enforcement():
    from offline_guard import blocking_installed, enforce_offline

    _, carrier = _onboarded()
    with enforce_offline():
        assert blocking_installed()
        ok, report = revoke_onbody(carrier)
    assert ok
    assert report["restorable_after"] is False


def test_revoke_makes_no_network_calls(monkeypatch):
    import socket
    import urllib.request

    def _fail(*a, **k):                                     # pragma: no cover
        raise AssertionError("폐기가 네트워크를 호출했다 — 서버 없는 폐기 위반")

    for mod, name in ((socket, "socket"), (socket, "create_connection"),
                      (socket, "getaddrinfo"), (urllib.request, "urlopen")):
        monkeypatch.setattr(mod, name, _fail)

    _, carrier = _onboarded()
    ok, _ = revoke_onbody(carrier)
    assert ok


# ---------- AC3: 복구 시나리오 (폐기 후 재온보딩) ----------

def test_reonboarding_allowed_after_revoke():
    """4.1 파티 결정 완성: 재온보딩 거부는 meta 존재로 판정되므로, 폐기가
    meta를 지우면 재온보딩이 열린다 — 이것이 정의된 복구 경로다."""
    _, carrier = _onboarded()

    # 폐기 전: 재온보딩 거부(4.1)
    blocked, rep1 = onboard_local([_dev("new1", "styler", ["power"])], carrier)
    assert blocked is None and rep1["errors"]

    ok, _ = revoke_onbody(carrier)
    assert ok

    # 폐기 후: 재온보딩 성공(복구)
    fresh, rep2 = onboard_local([_dev("new1", "styler", ["power"])], carrier)
    assert fresh is not None and rep2["errors"] == []
    restored, errs = restore_from_carrier(carrier)
    assert errs == [] and restored == fresh                 # 새 프로필로 정상 동작


# ---------- fail-closed ----------

def test_revoke_empty_carrier_reports_without_raising():
    ok, report = revoke_onbody(MemoryCarrier())
    assert isinstance(report, dict)
    assert report["restorable_after"] is False              # 복원 불가 상태
    assert ok                                               # 지울 게 없음 = 이미 폐기


def test_revoke_never_raises_on_garbage_carrier():
    class Broken:
        def get_records(self, names):
            raise RuntimeError("boom")

    ok, report = revoke_onbody(Broken())
    assert ok is False
    assert report["errors"]


def test_revoke_twice_is_safe():
    _, carrier = _onboarded()
    ok1, _ = revoke_onbody(carrier)
    ok2, report2 = revoke_onbody(carrier)
    assert ok1 and ok2
    assert report2["restorable_after"] is False


# ---------- 파티 리뷰 회귀: 부분 폐기 잔류 ----------

class _PartialEraseCarrier(MemoryCarrier):
    """erase가 meta만 지우고 나머지를 남기는 캐리어 — 부분 폐기 재현."""

    def erase(self, names):
        self._store = {k: v for k, v in self._store.items() if k != "meta"}
        return ["부분 삭제 실패"]


def test_partial_erase_residue_is_detected():
    """파티 리뷰(Grumbal 재현): 복원은 meta부터 읽으므로 meta만 지워지면
    restorable_after=False가 나온다 — 그런데 device 레코드는 워치에 남아 있다.
    '복원 불가'와 '잔류 0'은 다른 주장이며, 폐기는 **둘 다** 만족해야 한다."""
    carrier = _PartialEraseCarrier()
    profile, rep = onboard_local(_devices(), carrier)
    assert profile is not None and rep["errors"] == []

    ok, report = revoke_onbody(carrier)
    assert ok is False                                   # 폐기 실패로 보고
    assert report["restorable_after"] is False           # 복원은 실제로 불가
    assert report["residual_records"] == len(_devices())  # 그러나 잔류가 남았다
    assert carrier._store                                # 실제로 남아 있음


def test_clean_revoke_reports_zero_residue():
    _, carrier = _onboarded()
    ok, report = revoke_onbody(carrier)
    assert ok
    assert report["residual_records"] == 0               # 실측 0


def test_orphan_residue_without_meta_is_not_laundered_to_zero():
    """Boundary 지적: meta 없이 device만 남으면 이름을 재구성할 수 없어
    탐지도 삭제도 불가 — 그 사실을 0으로 세탁하지 않고 None(판정 불가)로 남긴다."""
    carrier = _PartialEraseCarrier()
    onboard_local(_devices(), carrier)
    revoke_onbody(carrier)                               # meta만 삭제, 고아 잔류 발생
    ok, report = revoke_onbody(carrier)                  # 다시 폐기 시도
    assert report["residual_records"] is None            # 0이 아니라 '판정 불가'
    assert any("판정 불가" in e for e in report["errors"])


# ---------- 문서 회귀 ----------

def test_revocation_doc_defines_recovery_and_limits():
    import pathlib
    doc = pathlib.Path("docs/REVOCATION.md").read_text(encoding="utf-8")
    assert "복구" in doc                                    # AC3 복구 시나리오
    assert "재온보딩" in doc or "다시 온보딩" in doc
    # 잔여 한계: 원격 소거가 아님을 명시
    assert "원격" in doc
    assert "잔여 한계" in doc or "한계" in doc


# ---------- 데모 ----------

def test_demo_revoke_output(capsys):
    import demo_revoke

    assert demo_revoke.main([]) == 0
    out = capsys.readouterr().out
    assert "폐기" in out
    assert "복원" in out
    assert "원격" in out                                    # 잔여 한계 표기
