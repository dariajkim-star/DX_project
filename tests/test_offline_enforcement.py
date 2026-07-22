# -*- coding: utf-8 -*-
"""오프라인 강제 검증 회귀 테스트 (Story 2.3).

고정하는 것:
  1. R5 해소 (AC1) — 전송 계층이 청크를 받고 **수신 측이** 재조립한다
  2. 차단 하네스 (AC1) — "부르지 않았다"가 아니라 **"부를 수 없다"**.
     하네스 자신의 스텁 판별 포함
  3. 차단 상태 종단 (AC1) — 연결/차단 두 상태의 최종 상태·이벤트가 **동일**
  4. 화면 확인 (AC2) — 차단 사실 표시 + 그 표시의 한계
  5. 대비 자료 (AC3) — ThinQ 칸이 **"미측정"으로 남아 있음**을 고정

Epic 1·2 교훈 계승: 정확한 값 단언, 검사기/하네스의 스텁 판별,
증거와 한계를 같이 적기.
"""
import socket
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import offline_guard  # noqa: E402
from appliance_sim.core import SIMULATOR_BANNER, ApplianceState  # noqa: E402
from appliance_sim.transports.loopback import LoopbackTransport  # noqa: E402
from home_profile import MemoryCarrier, serialize  # noqa: E402
from home_profile import routine as rt  # noqa: E402
from home_profile import storage as st  # noqa: E402


@pytest.fixture
def profile():
    return st.make_sample_profile(3, 2)


def _appliances_for(profile):
    return {d["device_ref"]: ApplianceState(
        d["device_ref"], d["device_type"], d["capabilities"])
        for d in profile["devices"]}


def _loaded_carrier(profile):
    carrier = MemoryCarrier()
    data, errs = serialize(profile)
    assert errs == []
    assert carrier.put_records({"profile": data}) == []
    return carrier


# ---------- 1. R5 해소 — 수신 측 재조립 (AC1) ----------

def test_transport_accepts_chunks(profile):
    """전송 계층이 청크 목록을 받는다 — 무선 구간의 실제 모양."""
    ac = ApplianceState("dev000", "air_conditioner", ["power", "target_temp"])
    t = LoopbackTransport(ac)
    cmd = {"v": 1, "device_ref": "dev000", "set": {"power": True}}
    pieces, errs = rt.chunk(rt._encode(cmd), 20)
    assert errs == [] and len(pieces) >= 2

    errs = t.deliver_chunks(pieces)
    assert errs == []
    assert ac.snapshot()["state"]["power"] is True


def test_receiver_reassembles_not_sender(profile):
    """리뷰 R5 회귀 고정: v1은 `execute_routine`이 쪼갠 것을 **그 자리에서
    다시 붙여** 보냈다 — 무선 구간이 시뮬레이션되지 않았다. 이제 재조립은
    수신 측에서 일어나고, 결과가 어느 경로였는지 말한다."""
    carrier = _loaded_carrier(profile)
    appliances = _appliances_for(profile)
    transports = {ref: LoopbackTransport(a) for ref, a in appliances.items()}
    result, errs = rt.execute_routine(carrier, transports, "profile", 0)
    assert errs == []
    assert result["reassembled_by"] == "receiver"


def test_legacy_deliver_path_preserved(profile):
    """2.1 계약(`deliver(bytes)`)은 삭제하지 않는다. 청크를 못 받는 전송은
    기존 경로로 떨어지되 **어느 쪽을 썼는지 결과에 남긴다**(조용한 분기 금지)."""
    class LegacyTransport:
        """deliver()만 있는 구형 전송 — 2.1 시점의 모양."""
        def __init__(self, appliance):
            self._inner = LoopbackTransport(appliance)

        def deliver(self, data):
            return self._inner.deliver(data)

    carrier = _loaded_carrier(profile)
    appliances = _appliances_for(profile)
    transports = {ref: LegacyTransport(a) for ref, a in appliances.items()}
    result, errs = rt.execute_routine(carrier, transports, "profile", 0)
    assert errs == []
    assert result["reassembled_by"] == "sender"          # 폴백을 숨기지 않는다
    for action in profile["routines"][0]["actions"]:
        state = appliances[action["device_ref"]].snapshot()["state"]
        assert state[action["setting_key"]] == action["value"]


def test_deliver_chunks_never_raises():
    ac = ApplianceState("dev000", "light", ["power"])
    t = LoopbackTransport(ac)
    for bad in (None, "문자열", 42, [], [None], [b""], [b"\x00\x00\x01"]):
        errs = t.deliver_chunks(bad)
        assert isinstance(errs, list) and len(errs) >= 1
    assert ac.events() == []                              # 상태 무손상


def test_deliver_chunks_rejects_adversarial_reassembly():
    """수신 측이 재조립하므로 **적대적 청크를 받는 것도 수신 측**이다."""
    ac = ApplianceState("dev000", "light", ["power"])
    t = LoopbackTransport(ac)
    cmd = {"v": 1, "device_ref": "dev000", "set": {"power": True}}
    pieces, _ = rt.chunk(rt._encode(cmd), 20)

    forged = bytearray(pieces[0])
    forged[1] = 0xFF                                      # 총개수 위조
    assert t.deliver_chunks([bytes(forged)]) != []
    assert t.deliver_chunks(pieces[:-1]) != []            # 결번
    assert ac.events() == []                              # 아무것도 반영 안 됨


# ---------- 2. 차단 하네스 (AC1) ----------

def test_guard_blocks_socket():
    """'부르지 않았다'가 아니라 **'부를 수 없다'**."""
    with pytest.raises(offline_guard.OfflineViolation):
        with offline_guard.enforce_offline():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)


def test_guard_blocks_dns_and_socketpair():
    """2.2 리뷰(Paige)가 구멍으로 지적한 경로들 — 이제 막힌다."""
    with pytest.raises(offline_guard.OfflineViolation):
        with offline_guard.enforce_offline():
            socket.getaddrinfo("example.com", 80)
    with pytest.raises(offline_guard.OfflineViolation):
        with offline_guard.enforce_offline():
            socket.socketpair()


def test_guard_blocks_urllib_and_subprocess():
    import subprocess
    import urllib.request
    with pytest.raises(offline_guard.OfflineViolation):
        with offline_guard.enforce_offline():
            urllib.request.urlopen("http://example.com")
    with pytest.raises(offline_guard.OfflineViolation):
        with offline_guard.enforce_offline():
            subprocess.run(["curl", "http://example.com"])


def test_guard_restores_on_exit():
    original = socket.socket
    with offline_guard.enforce_offline():
        assert socket.socket is not original
    assert socket.socket is original


def test_guard_restores_after_violation():
    """위반으로 빠져나가도 원상복구된다 — 뒤따르는 테스트를 오염시키지 않는다."""
    original = socket.socket
    with pytest.raises(offline_guard.OfflineViolation):
        with offline_guard.enforce_offline():
            socket.socket()
    assert socket.socket is original


def test_guard_nests_safely():
    original = socket.socket
    with offline_guard.enforce_offline():
        with offline_guard.enforce_offline():
            assert offline_guard.is_active()
        assert offline_guard.is_active()          # 안쪽이 끝나도 바깥은 유효
    assert not offline_guard.is_active()
    assert socket.socket is original


def test_guard_is_not_a_stub():
    """⚠️ 하네스 자신의 스텁 판별 — **네 번째 적용**.
    1.1의 스텁 23/23 통과, 1.3 P4(항상 실패하는 어댑터), 2.2 AST 검사기에
    이어 같은 병이 여기서도 가능하다: **아무것도 안 막는 하네스도 '위반 없음'을
    낸다.** 막힌 상태에서 일부러 열어 보고 실제로 터지는지 고정한다."""
    # 비활성 상태에서는 소켓 생성이 정상 동작한다(대조군)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.close()
    assert not offline_guard.is_active()

    # 활성 상태에서는 같은 호출이 반드시 터진다
    blocked = 0
    with pytest.raises(offline_guard.OfflineViolation):
        with offline_guard.enforce_offline():
            assert offline_guard.is_active()
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            blocked = 1                            # 여기 도달하면 안 막힌 것
    assert blocked == 0


def test_violation_not_swallowed_by_product_code(profile):
    """제품 코드의 `except Exception`이 위반을 흡수하면 이 스토리가 무의미하다.
    fail-closed가 여기서는 함정이 된다 — 위반은 반드시 밖으로 나와야 한다."""
    def sneaky_deliver(_data):
        socket.socket(socket.AF_INET, socket.SOCK_STREAM)   # 위반 시도
        return []

    class SneakyTransport:
        deliver = staticmethod(sneaky_deliver)

    carrier = _loaded_carrier(profile)
    transports = {d["device_ref"]: SneakyTransport()
                  for d in profile["devices"]}
    with pytest.raises(offline_guard.OfflineViolation):
        with offline_guard.enforce_offline():
            rt.execute_routine(carrier, transports, "profile", 0)


# ---------- 3. 차단 상태 종단 (AC1) ----------

def _run_once(profile):
    carrier = _loaded_carrier(profile)
    appliances = _appliances_for(profile)
    transports = {ref: LoopbackTransport(a) for ref, a in appliances.items()}
    result, errs = rt.execute_routine(carrier, transports, "profile", 0)
    snapshots = {ref: a.snapshot()["state"] for ref, a in appliances.items()}
    events = {ref: [(e["seq"], tuple(sorted(
        (c["capability"], repr(c["old"]), repr(c["new"])) for c in e["changes"])))
        for e in a.events()] for ref, a in appliances.items()}
    return result, errs, snapshots, events


def test_offline_result_identical_to_online(profile):
    """AC1의 문면은 '차단 상태에서도 **동일하게** 성공'이다.
    '둘 다 성공'은 약한 단언 — 최종 상태·이벤트가 같은지 본다."""
    online = _run_once(profile)
    with offline_guard.enforce_offline():
        assert offline_guard.is_active()          # 하네스가 실제로 활성인지 확인
        offline = _run_once(profile)

    on_result, on_errs, on_snap, on_ev = online
    off_result, off_errs, off_snap, off_ev = offline
    assert on_errs == [] and off_errs == []
    assert on_snap == off_snap                     # 최종 상태 동일
    assert on_ev == off_ev                         # 이벤트 로그 동일
    assert on_result["commands"] == off_result["commands"]
    assert on_result["chunks_sent"] == off_result["chunks_sent"]
    assert off_result["reassembled_by"] == "receiver"


def test_offline_test_would_fail_without_guard(profile):
    """⚠️ 이 검증이 하네스 없이도 통과하면 의미가 없다.
    하네스가 실제로 활성이었음을 테스트가 스스로 확인한다."""
    assert not offline_guard.is_active()
    with offline_guard.enforce_offline():
        assert offline_guard.is_active()
    assert not offline_guard.is_active()


# ---------- 4. 화면 확인 (AC2) ----------

def test_demo_offline_flag_shows_blocking(capsys):
    from demo_routine import main
    rc = main(["--offline"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "차단" in out
    assert "실패 확인" in out or "차단 시연" in out     # 관찰이지 주장이 아니다


def test_demo_offline_states_its_limit(capsys):
    """화면 표시의 한계 — 코드가 아는 것은 '이 프로세스가 못 나간다'까지다.
    기내모드는 사람이 누르는 것이고 우리는 그것을 관측하지 못한다."""
    from demo_routine import main
    main(["--offline"])
    out = capsys.readouterr().out
    assert "프로세스" in out
    assert "기내모드" in out


def test_demo_banner_rule_holds_with_offline(capsys):
    """배너 규약(§4-b)은 새 출력이 생겨도 유지된다 — 재발명 금지."""
    from demo_routine import main
    main(["--offline"])
    lines = [ln for ln in capsys.readouterr().out.splitlines() if ln.strip()]
    stream = [ln for ln in lines if ln.startswith("  dev")]
    assert len(stream) >= 4
    assert all(SIMULATOR_BANNER not in ln for ln in stream)


# ---------- 5. 대비 자료 (AC3) ----------

def test_comparison_doc_leaves_thinq_unmeasured():
    """⚠️ AC3은 코드로 완결되지 않는다. ThinQ 앱을 기내모드에서 돌리는 것은
    사람의 일이므로, 우리는 **틀만** 만들고 빈칸을 남긴다.
    이 테스트는 그 빈칸이 나중에 **추정치로 채워지는 것**을 막는다
    (1.2의 '산출 불가 > 그럴듯한 숫자'와 같은 계보)."""
    doc = (ROOT / "docs" / "OFFLINE_COMPARISON.md").read_text(encoding="utf-8")
    assert "미측정" in doc
    # ThinQ 행에 결과가 적히면 실패한다 — 측정 없이 채우지 않는다
    thinq_rows = [ln for ln in doc.splitlines()
                  if ln.startswith("|") and "ThinQ 앱" in ln]
    assert thinq_rows, "대비표에 ThinQ 행이 없다"
    assert all("미측정" in r for r in thinq_rows), thinq_rows
    # 측정 절차와 기록 항목이 정의돼 있다
    for token in ("측정 절차", "앱 버전", "캡처"):
        assert token in doc, token


def test_demo_script_exists_with_fallback_and_limits():
    doc = (ROOT / "docs" / "DEMO_SCRIPT.md").read_text(encoding="utf-8")
    for token in ("기내모드", "폴백", "예상 질문", "발견", "처방"):
        assert token in doc, token
    # 발표 중 즉흥 과장을 막는 장치 — 말해도 되는 것/안 되는 것 표
    assert "말하면 안 되는" in doc or "말해도 되는" in doc
