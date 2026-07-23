# -*- coding: utf-8 -*-
"""Story 4.3 — 릴레이 공격 방어 (NFR1).

이 파일이 단언하는 것:
  1. 정상 근접 성공(AC1 전제): 현재 nonce 응답 → verify 통과 → apply 성공.
  2. 재생 거부(AC1): 소비된 nonce 재사용 → 거부. 상태 불변.
  3. wrong/옛 nonce 거부, 신선도(1회용) 거부.
  4. fail-closed: garbage 토큰 → 거부, 예외 없음.
  5. 문서 회귀: THREAT_MODEL.md에 잔여 한계 + 완전방어 무조건주장 부재.

⚠️ 용어: 막는 것 = replay(캡처 명령 재사용). 못 막는 것 = 실시간 relay
(거리 바운딩 필요, 미구현) — THREAT_MODEL.md의 잔여 한계.
"""
from home_profile import ProximityGuard, make_proximity_token
from appliance_sim.core import ApplianceState


def _appliance():
    return ApplianceState("ac1", "air_conditioner", ["power", "target_temp"])


def _cmd():
    return {"device_ref": "ac1", "set": {"power": True}}


# ---------- AC1 전제: 정상 근접 명령 성공 ----------

def test_valid_proximity_command_succeeds():
    guard = ProximityGuard()
    appliance = _appliance()
    nonce = guard.issue_challenge()
    token = make_proximity_token(nonce)      # 근접 워치가 신선한 nonce에 응답
    ok, _ = guard.verify(token)
    assert ok
    applied, errs = appliance.apply_command(_cmd())
    assert applied and errs == []
    assert appliance.snapshot()["state"]["power"] is True


# ---------- AC1: 재생(replay) 거부 ----------

def test_replay_rejected_and_state_unchanged():
    """캡처한 명령을 nonce 회전 후 재현 → 거부. apply까지 가지 않아 상태 불변."""
    guard = ProximityGuard()
    appliance = _appliance()

    nonce1 = guard.issue_challenge()
    captured = make_proximity_token(nonce1)  # 공격자가 캡처
    ok, _ = guard.verify(captured)           # 정상 사용 1회 — nonce 소비
    assert ok

    guard.issue_challenge()                  # 가전이 새 챌린지로 회전
    ok, reason = guard.verify(captured)      # 공격자가 캡처본 재생
    assert ok is False
    assert reason                            # 소비된 nonce로 거부
    # 게이트가 막았으니 apply를 부르지 않는 것이 올바른 합성 — 상태 불변 확인
    assert appliance.snapshot()["state"]["power"] is None


def test_stale_nonce_after_rechallenge_rejected():
    """챌린지 재발급 후 옛 토큰 → 거부(1회용·현재 챌린지 불일치)."""
    guard = ProximityGuard()
    nonce1 = guard.issue_challenge()
    old_token = make_proximity_token(nonce1)
    guard.issue_challenge()                  # 재발급 — nonce1은 더 이상 현재가 아님
    ok, reason = guard.verify(old_token)
    assert ok is False
    assert reason


def test_wrong_nonce_rejected():
    guard = ProximityGuard()
    guard.issue_challenge()
    forged = make_proximity_token("deadbeef" * 4)   # 위조 nonce
    ok, reason = guard.verify(forged)
    assert ok is False
    assert reason


def test_no_challenge_issued_rejects():
    guard = ProximityGuard()
    ok, reason = guard.verify(make_proximity_token("x" * 32))
    assert ok is False
    assert reason


def test_double_use_of_same_challenge_rejected():
    """같은 챌린지에 두 번 응답 → 두 번째 거부(1회용)."""
    guard = ProximityGuard()
    nonce = guard.issue_challenge()
    token = make_proximity_token(nonce)
    ok1, _ = guard.verify(token)
    ok2, _ = guard.verify(token)
    assert ok1 is True
    assert ok2 is False


# ---------- fail-closed ----------

def test_verify_never_raises_on_garbage():
    guard = ProximityGuard()
    guard.issue_challenge()
    for bad in (None, 42, "token", [], {}, {"nonce": 123}, {"nonce": None}):
        ok, reason = guard.verify(bad)
        assert ok is False
        assert isinstance(reason, str)


# ---------- AC2: 잔여 한계 문서 회귀 ----------

def test_threat_model_documents_residual_limit():
    import pathlib
    doc = pathlib.Path("docs/THREAT_MODEL.md").read_text(encoding="utf-8")
    # 잔여 한계·못 막는 것이 명시돼 있다
    assert "잔여 한계" in doc
    assert "못 막" in doc or "막지 못" in doc
    assert "거리 바운딩" in doc or "distance bound" in doc.lower()
    # replay와 relay를 구분한다
    assert "relay" in doc.lower() or "중계" in doc
    assert "replay" in doc.lower() or "재생" in doc


def test_threat_model_does_not_claim_complete_defense():
    import pathlib
    doc = pathlib.Path("docs/THREAT_MODEL.md").read_text(encoding="utf-8")
    # "완전 방어"·"완전히 막"을 무조건형 주장으로 쓰지 않는다 —
    # 등장한다면 반드시 '주장하지 않는다/부인' 맥락이어야 한다(정직성).
    for phrase in ("완전 방어", "완전히 막"):
        idx = doc.find(phrase)
        if idx != -1:
            window = doc[max(0, idx - 20):idx + 40]
            assert ("않" in window or "부인" in window or "못" in window), \
                f"'{phrase}'가 무조건형 주장으로 쓰임 — 정직성 위반"


# ---------- 데모 ----------

def test_demo_relay_output(capsys):
    import demo_relay

    assert demo_relay.main([]) == 0
    out = capsys.readouterr().out
    assert "거부" in out                     # 재생 거부가 화면에
    assert "막지 못" in out or "못 막" in out  # 잔여 한계 표기(AC2)
    assert "실기기 아님" in out or "참조 어댑터" in out or "SIM" in out
