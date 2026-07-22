# -*- coding: utf-8 -*-
"""프로필 기반 명령 전송 회귀 테스트 (Story 2.2).

고정하는 것:
  1. 루틴 → 명령 변환 (AC1) — 기기별 그룹핑·개수·순서, 미등록 참조 거부, 결정적
  2. BLE 청킹 (AC1) — 20B MTU 왕복, 적대적 재조립 거부
  3. 종단 실행 (AC1) — 프로필 → 캐리어 → 루틴 → 시뮬레이터 상태가 의도값과 일치
  4. 클라우드 호출 부재 (AC2) — 동적(호출 감시) + 정적(AST) 양쪽

Epic 1·2.1 교훈 계승: 정확한 값 단언, 예외 금지, 오류에 값 원문 금지,
검사기 자체의 스텁 판별.
"""
import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from appliance_sim.core import SIMULATOR_BANNER, ApplianceState  # noqa: E402
from appliance_sim.transports.loopback import LoopbackTransport  # noqa: E402
from appliance_sim.wire import MAX_COMMAND_BYTES, decode_command  # noqa: E402
from home_profile import MemoryCarrier, serialize  # noqa: E402
from home_profile import routine as rt  # noqa: E402
from home_profile import storage as st  # noqa: E402


@pytest.fixture
def profile():
    """기기 3대·루틴 2개. 루틴 0은 dev000·dev001을 건드린다(기기 2대)."""
    return st.make_sample_profile(3, 2)


# ---------- 1. 루틴 → 명령 변환 (AC1) ----------

def test_routine_groups_actions_by_device(profile):
    """액션이 기기 2대를 건드리면 명령은 2건 — 2.1의 명령 형식이 기기 단일이므로."""
    cmds, errs = rt.routine_to_commands(profile, 0)
    assert errs == []
    refs = [c["device_ref"] for c in cmds]
    assert refs == sorted(set(refs))          # 기기당 정확히 1건, 중복 없음
    actions = profile["routines"][0]["actions"]
    assert len(cmds) == len({a["device_ref"] for a in actions})


def test_command_shape_matches_wire_contract(profile):
    """2.1의 wire 계약을 그대로 따른다 — 새 형식 발명 금지."""
    cmds, errs = rt.routine_to_commands(profile, 0)
    assert errs == []
    for c in cmds:
        assert set(c) == {"v", "device_ref", "set"}
        assert c["v"] == 1
        assert isinstance(c["set"], dict) and c["set"]


def test_all_actions_land_in_commands(profile):
    """액션이 조용히 누락되지 않는다 — 값까지 정확히 옮겨진다."""
    actions = profile["routines"][0]["actions"]
    cmds, errs = rt.routine_to_commands(profile, 0)
    assert errs == []
    merged = {}
    for c in cmds:
        for k, v in c["set"].items():
            merged[(c["device_ref"], k)] = v
    assert merged == {(a["device_ref"], a["setting_key"]): a["value"]
                      for a in actions}


def test_command_order_is_deterministic(profile):
    """같은 루틴은 같은 순서를 낸다 — 발표 재현성이 걸려 있다."""
    first, _ = rt.routine_to_commands(profile, 0)
    for _ in range(5):
        again, _ = rt.routine_to_commands(profile, 0)
        assert again == first


def test_unregistered_device_ref_rejected(profile):
    """와이어를 거친 프로필은 재불신 — 스키마가 이미 막지만 다시 본다."""
    profile["routines"][0]["actions"][0]["device_ref"] = "ghost999"
    cmds, errs = rt.routine_to_commands(profile, 0)
    assert cmds is None and len(errs) == 1


def test_capability_not_on_device_rejected(profile):
    """기기가 선언하지 않은 setting_key는 거부 — 시뮬레이터가 거부할 명령을
    만들어 보내지 않는다."""
    profile["routines"][0]["actions"][0]["setting_key"] = "humidity"
    cmds, errs = rt.routine_to_commands(profile, 0)
    assert cmds is None and len(errs) >= 1


def test_convert_never_raises(profile):
    for bad_profile, bad_idx in (
        (None, 0), ("문자열", 0), (42, 0), ({}, 0), (profile, -1),
        (profile, 99), (profile, "0"), (profile, None),
        ({"routines": "리스트아님"}, 0), ({"routines": [None]}, 0),
        ({"routines": [{"actions": None}]}, 0),
    ):
        cmds, errs = rt.routine_to_commands(bad_profile, bad_idx)
        assert cmds is None
        assert isinstance(errs, list) and len(errs) >= 1


def test_convert_errors_never_contain_values(profile):
    marker = "PII-CANARY-daria@example.com"
    profile["routines"][0]["actions"][0]["device_ref"] = marker
    _, errs = rt.routine_to_commands(profile, 0)
    assert errs
    for e in errs:
        assert marker not in e


def test_show_rule_matches_appliance_sim():
    """리뷰 회귀 고정: 같은 방어를 두 곳에 **다르게** 구현했었다.
    `appliance_sim`을 import할 수 없어 복사한 것이 드리프트로 이어졌으므로
    (역방향 의존 금지의 대가), 동기를 테스트가 감시한다."""
    from appliance_sim import core as ac
    assert rt._SAFE_SHOW_RE.pattern == ac._SAFE_SHOW_RE.pattern

    # v1에서 두 구현이 갈렸던 실제 입력들 — 이제 판정이 일치한다
    for s in ("dev000", "a_b", "A_B", "9dev", "___", "", "한글",
              "x" * 33, "hong@gmail.com"):
        assert rt._show(s) == ac._show(s), s


# ---------- 2. BLE 청킹 (AC1) ----------

MTU = 20


def test_chunk_respects_mtu(profile):
    cmds, _ = rt.routine_to_commands(profile, 0)
    from appliance_sim.wire import encode_command
    data, _ = encode_command(cmds[0])
    chunks, errs = rt.chunk(data, MTU)
    assert errs == []
    assert len(chunks) >= 2                       # 명령은 실측 50B+ 라 무조건 분할
    assert all(len(c) <= MTU for c in chunks)


def test_chunk_reassemble_roundtrip():
    for size in (1, 19, 20, 21, 100, MAX_COMMAND_BYTES):
        pieces, errs = rt.chunk(bytes(i % 256 for i in range(size)), MTU)
        assert errs == [], size
        back, errs = rt.reassemble(pieces)
        assert errs == [], size
        assert back == bytes(i % 256 for i in range(size)), size


def test_effective_payload_is_smaller_than_mtu():
    """헤더가 MTU를 먹는다 — 유효 페이로드가 20B보다 작음을 수치로 고정."""
    assert 0 < rt.PAYLOAD_PER_CHUNK < MTU
    pieces, errs = rt.chunk(b"x" * (rt.PAYLOAD_PER_CHUNK + 1), MTU)
    assert errs == [] and len(pieces) == 2


def test_chunk_returns_tuple_with_distinct_reasons():
    """리뷰 회귀 고정: v1은 실패를 **빈 목록**으로 냈다 — 저장소 유일한 예외였고
    실패 사유 4종이 호출자에서 하나로 뭉개졌다. 이제 사유가 구별된다."""
    cases = {
        "bytes": (None, MTU),                     # 비bytes
        "정수": (b"x", "20"),                      # MTU 비정수
        "페이로드": (b"x", 2),                      # MTU가 헤더 이하
        "상한": (b"x" * 100_000, MTU),             # 청크 수 초과
    }
    seen = set()
    for expect, (data, mtu) in cases.items():
        pieces, errs = rt.chunk(data, mtu)
        assert pieces is None and len(errs) == 1, expect
        assert expect in errs[0], (expect, errs[0])
        seen.add(errs[0])
    assert len(seen) == 4                         # 네 사유가 서로 다른 문구


def test_chunk_never_raises():
    for data, mtu in ((None, MTU), ("문자열", MTU), (42, MTU), ([], MTU),
                      (b"x", 0), (b"x", -5), (b"x", True), (b"x", None)):
        pieces, errs = rt.chunk(data, mtu)
        assert pieces is None
        assert isinstance(errs, list) and len(errs) >= 1


def test_reassemble_rejects_forged_total():
    """총개수 위조 = 메모리 고갈 공격. 청크 1개가 '총 60000개'라고 주장."""
    data = b"hello"
    chunks, _ = rt.chunk(data, MTU)
    forged = bytearray(chunks[0])
    forged[1] = 0xFF                              # total 바이트 조작
    back, errs = rt.reassemble([bytes(forged)])
    assert back is None and len(errs) >= 1


def test_reassemble_rejects_missing_chunk():
    data = b"x" * 100
    chunks, _ = rt.chunk(data, MTU)
    back, errs = rt.reassemble(chunks[:-1])       # 결번
    assert back is None and len(errs) >= 1


def test_reassemble_rejects_duplicate_seq():
    data = b"x" * 100
    chunks, _ = rt.chunk(data, MTU)
    back, errs = rt.reassemble(chunks + [chunks[0]])
    assert back is None and len(errs) >= 1


def test_reassemble_tolerates_shuffled_order():
    """순서가 뒤바뀌어도 헤더의 순번으로 복원한다 — BLE는 순서를 보장하지 않는다."""
    data = b"".join(bytes([i]) * 7 for i in range(20))
    chunks, _ = rt.chunk(data, MTU)
    back, errs = rt.reassemble(list(reversed(chunks)))
    assert errs == [] and back == data


def test_reassemble_rejects_empty_and_oversize():
    assert rt.reassemble([])[0] is None
    assert rt.reassemble(None)[0] is None
    big = b"x" * (MAX_COMMAND_BYTES + 1)
    pieces, _ = rt.chunk(big, MTU)
    back, errs = rt.reassemble(pieces)
    assert back is None and len(errs) >= 1        # 재조립 후 상한 초과 거부


def test_reassemble_never_raises():
    for bad in (None, "문자열", 42, [None], [b""], [b"\x00"], ["문자열"],
                [b"\x00\x00\x01"],                      # total=0
                [b"\x05\x02\x01", b"\x01\x02\x02"],     # seq 범위 밖
                [b"\x00\x02\x01", b"\x01\x03\x02"]):    # total 불일치
        back, errs = rt.reassemble(bad)
        assert back is None, bad
        assert isinstance(errs, list) and len(errs) >= 1


def test_reassemble_accepts_minimal_valid_pair():
    """대조군: 위 불량 케이스들이 '아무거나 거부'라서 통과하는 게 아님을 보인다
    — 형식이 맞으면 실제로 재조립된다(검사기 스텁 판별과 같은 원리)."""
    back, errs = rt.reassemble([b"\x00\x02\x01", b"\x01\x02\x02"])
    assert errs == [] and back == b"\x01\x02"


def test_reassembled_bytes_decode_as_command(profile):
    """청킹→재조립을 거친 바이트가 2.1의 decode_command를 그대로 통과한다."""
    cmds, _ = rt.routine_to_commands(profile, 0)
    from appliance_sim.wire import encode_command
    data, _ = encode_command(cmds[0])
    pieces, errs = rt.chunk(data, MTU)
    assert errs == []
    back, errs = rt.reassemble(pieces)
    assert errs == []
    decoded, errs = decode_command(back)
    assert errs == [] and decoded == cmds[0]


# ---------- 3. 종단 실행 (AC1) ----------

def _appliances_for(profile):
    return {d["device_ref"]: ApplianceState(
        d["device_ref"], d["device_type"], d["capabilities"])
        for d in profile["devices"]}


def test_execute_routine_end_to_end(profile):
    """프로필 → 캐리어 → 루틴 → 청킹 → 시뮬레이터. 상태가 의도값과 정확히 일치."""
    carrier = MemoryCarrier()
    data, errs = serialize(profile)
    assert errs == []
    assert carrier.put_records({"profile": data}) == []

    appliances = _appliances_for(profile)
    transports = {ref: LoopbackTransport(a) for ref, a in appliances.items()}
    result, errs = rt.execute_routine(carrier, transports, "profile", 0)
    assert errs == []

    # 프로필이 의도한 값과 시뮬레이터 상태가 일치 (AC1의 문면)
    for action in profile["routines"][0]["actions"]:
        state = appliances[action["device_ref"]].snapshot()["state"]
        assert state[action["setting_key"]] == action["value"]
    assert result["devices_commanded"] == len(
        {a["device_ref"] for a in profile["routines"][0]["actions"]})
    assert result["chunks_sent"] >= result["commands"] * 2   # 전부 분할됐다


def test_result_counts_commanded_not_changed(profile):
    """리뷰 P4 계승: 결과 필드는 **보낸 기기 수**이지 바뀐 기기 수가 아니다.
    같은 값을 두 번 보내면 전송은 두 번 성공하지만 상태 변화는 한 번뿐 —
    필드 이름이 그 차이를 속이지 않는지 고정한다."""
    carrier = MemoryCarrier()
    data, _ = serialize(profile)
    carrier.put_records({"profile": data})
    appliances = _appliances_for(profile)
    transports = {ref: LoopbackTransport(a) for ref, a in appliances.items()}

    first, errs = rt.execute_routine(carrier, transports, "profile", 0)
    assert errs == []
    second, errs = rt.execute_routine(carrier, transports, "profile", 0)
    assert errs == []

    # 두 번째도 같은 수를 "보냈다"고 보고한다
    assert second["devices_commanded"] == first["devices_commanded"]
    # 그러나 실제 상태 변화 이벤트는 첫 실행 것뿐이다 (no-op은 이벤트 없음)
    touched = {a["device_ref"] for a in profile["routines"][0]["actions"]}
    for ref in touched:
        assert len(appliances[ref].events()) == 1
    assert "devices_changed" not in second          # 없는 것을 있는 척하지 않는다


def test_execute_records_events_in_simulator(profile):
    """이벤트 로그로도 교차 확인 — 상태만 보면 우연히 맞을 수 있다."""
    carrier = MemoryCarrier()
    data, _ = serialize(profile)
    carrier.put_records({"profile": data})
    appliances = _appliances_for(profile)
    transports = {ref: LoopbackTransport(a) for ref, a in appliances.items()}
    rt.execute_routine(carrier, transports, "profile", 0)

    touched = {a["device_ref"] for a in profile["routines"][0]["actions"]}
    for ref in touched:
        assert len(appliances[ref].events()) == 1


def test_execute_never_raises(profile):
    carrier = MemoryCarrier()
    for args in ((None, None, "profile", 0), (carrier, None, "profile", 0),
                 (carrier, {}, "없는레코드", 0), (carrier, {}, "profile", 0)):
        result, errs = rt.execute_routine(*args)
        assert result is None
        assert isinstance(errs, list) and len(errs) >= 1


def test_execute_reads_through_carrier_not_raw_dict(profile):
    """캐리어를 우회하면 1.3의 캐리어 중립이 이 스토리에서 무효화된다.
    캐리어가 거부하면 실행도 실패해야 한다(우회 경로가 없다는 증거)."""
    carrier = MemoryCarrier()          # 아무것도 저장하지 않음
    transports = {ref: LoopbackTransport(ApplianceState(ref, "light", ["power"]))
                  for ref in ("dev000",)}
    result, errs = rt.execute_routine(carrier, transports, "profile", 0)
    assert result is None and len(errs) >= 1


# ---------- 3b. 종단 데모 (Task 6) ----------

def test_demo_runs_and_shows_chunking(capsys):
    from demo_routine import main
    rc = main([])
    out = capsys.readouterr().out
    assert rc == 0
    assert "청크" in out                              # 워치급 제약이 화면에 보인다
    assert "seq=1" in out                             # 상태 전이가 실제로 보인다
    assert "OFFLINE_EVIDENCE" in out                  # 증거 한계로 안내


def test_demo_banner_follows_boundary_rule(capsys):
    """2.1 파티 리뷰(Sally) 규약 승계 — 경계마다 한 번, 스트림 안엔 생략."""
    from demo_routine import main
    main([])
    lines = [ln for ln in capsys.readouterr().out.splitlines() if ln.strip()]
    banner_lines = [ln for ln in lines if SIMULATOR_BANNER in ln]
    assert len(banner_lines) == 4, banner_lines
    # 반복 스트림 = 기기별 명령 줄·상태 전이 줄 ("  dev0xx ...")
    stream = [ln for ln in lines if ln.startswith("  dev")]
    assert len(stream) >= 4, stream
    assert all(SIMULATOR_BANNER not in ln for ln in stream)


# ---------- 4. 클라우드 호출 부재 (AC2) ----------

def test_no_network_calls_during_execution(profile, monkeypatch):
    """동적 증거: 실행 경로 전체에서 소켓·HTTP·외부 프로세스가 열리지 않는다.

    ⚠️ 이 감시가 **모든** 연결을 막는 것은 아니다(getaddrinfo·socketpair·
    C 확장 syscall은 지나간다). 한계는 docs/OFFLINE_EVIDENCE.md §2 참조.
    """
    import socket
    import subprocess
    import urllib.request

    def explode(*a, **k):
        raise AssertionError("실행 경로에서 네트워크 호출이 발생했다")

    monkeypatch.setattr(socket, "socket", explode)
    monkeypatch.setattr(socket, "create_connection", explode)
    monkeypatch.setattr(urllib.request, "urlopen", explode)
    monkeypatch.setattr(subprocess, "Popen", explode)   # curl 우회 차단
    monkeypatch.setattr(subprocess, "run", explode)

    carrier = MemoryCarrier()
    data, _ = serialize(profile)
    carrier.put_records({"profile": data})
    appliances = _appliances_for(profile)
    transports = {ref: LoopbackTransport(a) for ref, a in appliances.items()}
    result, errs = rt.execute_routine(carrier, transports, "profile", 0)
    assert errs == [] and result is not None


NETWORK_TOKENS = frozenset({"socket", "urllib", "http", "requests", "httpx",
                            "aiohttp", "ftplib", "telnetlib", "smtplib",
                            # 리뷰(Paige): 외부 프로세스로 curl을 부르는 우회가
                            # 감시·정적 검사 어디에도 없었다
                            "subprocess"})
OFFLINE_MODULES = (
    ROOT / "home_profile" / "schema.py",
    ROOT / "home_profile" / "storage.py",
    ROOT / "home_profile" / "carrier.py",
    ROOT / "home_profile" / "routine.py",
    ROOT / "appliance_sim" / "core.py",
    ROOT / "appliance_sim" / "wire.py",
    ROOT / "appliance_sim" / "transports" / "loopback.py",
)


def _imported_modules(source: str) -> set:
    """1.3 P3 반영판 — 동적 import 포함, 심볼명은 대조하지 않는다."""
    segments = set()

    def _add(path):
        segments.update(path.lower().split("."))

    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                _add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                _add(node.module)
        elif isinstance(node, ast.Call):
            fn = node.func
            if ((isinstance(fn, ast.Name) and fn.id in ("__import__", "import_module"))
                    or (isinstance(fn, ast.Attribute) and fn.attr == "import_module")):
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        _add(arg.value)
    return segments


def test_no_network_imports_static():
    """정적 증거: 실행 경로 모듈에 네트워크 라이브러리 import가 없다."""
    for path in OFFLINE_MODULES:
        assert path.exists(), path.name
        hits = _imported_modules(path.read_text(encoding="utf-8")) & NETWORK_TOKENS
        assert hits == set(), f"{path.name}: 네트워크 import {hits}"


def test_network_checker_detects_injected_import():
    """검사기 스텁 판별 — 아무것도 안 하는 검사기도 '위반 없음'을 낸다."""
    assert _imported_modules("import socket\n") & NETWORK_TOKENS == {"socket"}
    assert _imported_modules("from urllib.request import urlopen\n") & NETWORK_TOKENS \
        == {"urllib"}
    assert "requests" in _imported_modules('__import__("requests")\n')
    assert _imported_modules("import json\n") & NETWORK_TOKENS == set()


def test_evidence_limits_are_documented():
    """⚠️ 이 증거의 한계: 파이썬 레벨 감시는 프로세스 밖(OS·드라이버·펌웨어)을
    못 본다. 실제 패킷 차단 실험은 2.3의 일이며, 발표에서 '네트워크 캡처로
    확인했다'고 말하지 않는다(NFR6). 그 한계가 문서에 적혀 있음을 고정한다."""
    doc = (ROOT / "docs" / "OFFLINE_EVIDENCE.md").read_text(encoding="utf-8")
    assert "프로세스 밖" in doc
    assert "2.3" in doc
    # 리뷰(Paige): 한계 문서가 자기 앞장에서 과장하면 그 문서의 신뢰가 먼저 죽는다.
    # v1의 감시 표는 socket.socket을 "모든 TCP/UDP 연결의 출발점"이라 적었다.
    # (정정 경위를 서술한 인용문에는 그 구절이 남아 있으므로 **표 행만** 본다)
    table_rows = [ln for ln in doc.splitlines()
                  if ln.startswith("| `socket.socket`")]
    assert table_rows, "감시 대상 표가 사라졌다"
    assert all("모든" not in r for r in table_rows), table_rows
    assert "subprocess" in doc                    # 우회 경로도 감시 목록에 명시
