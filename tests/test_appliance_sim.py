# -*- coding: utf-8 -*-
"""가전 시뮬레이터 회귀 테스트 (Story 2.1).

고정하는 것:
  1. 상태 기계 (AC1·AC2) — 유효 명령 반영·무효 거부·거부 시 상태 불변·이벤트 정합
  2. 와이어 계약 (AC2) — 왕복 등가, 손상·초과·중복키·버전불일치 거부, 예외 금지
  3. 정직 표기 (AC3) — 배너가 모든 출력 경로에 실제로 실린다
  4. 전송 경계 — core·wire에 BLE 라이브러리 import 없음 (AST, 검사기 스텁 판별 포함)

Epic 1 교훈 계승: '단어 언급' 단언 금지(정확한 값·개수·이름), 예외 금지 계약,
오류 문구에 수신 값 원문 금지, 스텁을 통과시키는 테스트 금지.
"""
import ast
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from appliance_sim import core, wire  # noqa: E402
from appliance_sim.core import ApplianceState, SIMULATOR_BANNER  # noqa: E402
from appliance_sim.transports.loopback import LoopbackTransport  # noqa: E402
from home_profile import storage as st  # noqa: E402


@pytest.fixture
def ac():
    """에어컨 1대 — capability는 storage 어휘에서 고른 것."""
    return ApplianceState(device_ref="dev000", device_type="air_conditioner",
                          capabilities=["power", "target_temp", "mode", "fan_speed"])


# ---------- 1. 어휘 동기 (함정 3) ----------

def test_capability_vocabulary_is_in_sync_with_storage():
    """시뮬레이터 어휘는 storage와 동기여야 한다 — 프로필이 보낼 수 없는 명령을
    받는 가전은 데모에서 거짓이 된다. 비공개 심볼 대조는 테스트에만 격리."""
    assert set(core.KNOWN_CAPABILITIES) == set(st._CAPABILITIES)
    assert set(core.KNOWN_DEVICE_TYPES) == set(st._DEVICE_TYPES)


# ---------- 2. 상태 기계 (AC1·AC2) ----------

def test_initial_state_has_declared_capabilities_only(ac):
    snap = ac.snapshot()
    assert set(snap["state"]) == {"power", "target_temp", "mode", "fan_speed"}
    assert snap["device_ref"] == "dev000"
    assert snap["device_type"] == "air_conditioner"


def test_valid_command_changes_state_exactly(ac):
    applied, errs = ac.apply_command({"device_ref": "dev000",
                                      "set": {"power": True, "target_temp": 24}})
    assert errs == [] and applied is True
    snap = ac.snapshot()
    assert snap["state"]["power"] is True
    assert snap["state"]["target_temp"] == 24
    assert snap["state"]["mode"] is None        # 건드리지 않은 값은 그대로


def test_enum_capability_accepts_only_declared_values(ac):
    assert ac.apply_command({"device_ref": "dev000",
                             "set": {"mode": "cool"}})[1] == []
    applied, errs = ac.apply_command({"device_ref": "dev000",
                                      "set": {"mode": "turbo"}})
    assert applied is False and len(errs) == 1
    assert ac.snapshot()["state"]["mode"] == "cool"      # 거부 후 불변


def test_unknown_capability_rejected(ac):
    applied, errs = ac.apply_command({"device_ref": "dev000",
                                      "set": {"brightness": 50}})
    assert applied is False and len(errs) == 1
    assert "brightness" not in ac.snapshot()["state"]


def test_capability_not_on_this_device_rejected(ac):
    """storage 어휘엔 있지만 이 기기가 선언하지 않은 capability는 거부."""
    applied, errs = ac.apply_command({"device_ref": "dev000",
                                      "set": {"humidity": 40}})
    assert applied is False and len(errs) == 1


def test_wrong_device_ref_rejected(ac):
    applied, errs = ac.apply_command({"device_ref": "dev999",
                                      "set": {"power": True}})
    assert applied is False and len(errs) == 1
    assert ac.snapshot()["state"]["power"] is None


def test_type_violations_rejected(ac):
    for bad in ({"power": 1}, {"power": "on"}, {"target_temp": "24"},
                {"target_temp": True}, {"target_temp": 3.5}, {"mode": 3}):
        applied, errs = ac.apply_command({"device_ref": "dev000", "set": bad})
        assert applied is False and len(errs) == 1, bad


def test_every_int_range_declares_its_source():
    """리뷰(Mary) 회귀 고정: 범위값은 판정을 하는 숫자다 — 출처가 값과 함께
    다니지 않으면 '결정된 척'이다. 1.3의 CapabilityValue(value, source)와
    같은 규약을 여기에도 적용한다(같은 병을 한쪽만 고치지 않는다)."""
    assert core.INT_CAPABILITIES                       # 비어 있지 않고
    for cap, spec in core.INT_CAPABILITIES.items():
        assert isinstance(spec, core.RangeSpec), cap
        assert isinstance(spec.source, str) and spec.source.strip(), cap
        assert spec.lo < spec.hi, cap


def test_simulator_is_not_stricter_than_real_appliances():
    """시뮬레이터가 실가전보다 엄격하면 프로필이 이식 불가가 된다 —
    실가전이 거부할 명령을 승인하는 것보다, 판정을 실가전에 넘기는 쪽이 낫다.
    LG 에어컨 하한(18도로 알려짐)보다 낮은 값도 시뮬레이터는 통과시킨다."""
    spec = core.INT_CAPABILITIES["target_temp"]
    assert spec.lo <= 18 and spec.hi >= 30
    assert "미확인" in spec.source                     # 정직 표기 유지


def test_int_range_enforced(ac):
    assert ac.apply_command({"device_ref": "dev000",
                             "set": {"target_temp": 16}})[1] == []
    applied, errs = ac.apply_command({"device_ref": "dev000",
                                      "set": {"target_temp": 999}})
    assert applied is False and len(errs) == 1
    assert ac.snapshot()["state"]["target_temp"] == 16


def test_partial_batch_is_atomic(ac):
    """한 항목이라도 거부되면 배치 전체 미반영 (1.3 P1 계보)."""
    applied, errs = ac.apply_command(
        {"device_ref": "dev000", "set": {"power": True, "mode": "turbo"}})
    assert applied is False and len(errs) == 1
    assert ac.snapshot()["state"]["power"] is None      # power도 반영 안 됨


def test_apply_never_raises(ac):
    for bad in (None, "문자열", 42, [], {"set": None}, {"device_ref": "dev000"},
                {"device_ref": None, "set": {}}, {"device_ref": "dev000", "set": []},
                {"device_ref": "dev000", "set": {"power": None}}):
        applied, errs = ac.apply_command(bad)
        assert applied is False
        assert isinstance(errs, list) and len(errs) >= 1


def test_errors_never_contain_received_values(ac):
    """오류 문구에 수신 값 원문 금지 (1.1 F-PII·1.3 P2 계승)."""
    marker = "PII-CANARY-daria@example.com"
    for cmd in ({"device_ref": marker, "set": {"power": True}},
                {"device_ref": "dev000", "set": {"mode": marker}},
                {"device_ref": "dev000", "set": {marker: 1}}):
        _, errs = ac.apply_command(cmd)
        assert errs
        for e in errs:
            assert marker not in e


# ---------- 3. 이벤트 로그 (AC2 "관찰 가능") ----------

def test_events_record_exact_transitions(ac):
    ac.apply_command({"device_ref": "dev000", "set": {"power": True}})
    ac.apply_command({"device_ref": "dev000", "set": {"target_temp": 22}})
    evs = ac.events()
    assert len(evs) == 2
    assert [e["seq"] for e in evs] == [1, 2]             # 단조 증가
    assert evs[0]["changes"] == [{"capability": "power", "old": None, "new": True}]
    assert evs[1]["changes"] == [
        {"capability": "target_temp", "old": None, "new": 22}]


def test_rejected_command_records_no_event(ac):
    ac.apply_command({"device_ref": "dev000", "set": {"mode": "turbo"}})
    assert ac.events() == []


def test_no_op_command_records_no_event(ac):
    ac.apply_command({"device_ref": "dev000", "set": {"power": True}})
    ac.apply_command({"device_ref": "dev000", "set": {"power": True}})   # 같은 값
    assert len(ac.events()) == 1


def test_events_returns_copy_not_internal_list(ac):
    ac.apply_command({"device_ref": "dev000", "set": {"power": True}})
    ac.events().clear()
    assert len(ac.events()) == 1


# ---------- 4. 정직 표기 (AC3) ----------

def test_banner_constant_is_exact():
    assert SIMULATOR_BANNER == "시뮬레이터 — 실가전 아님"


def test_banner_in_snapshot(ac):
    assert ac.snapshot()["banner"] == SIMULATOR_BANNER


def test_banner_in_every_event(ac):
    ac.apply_command({"device_ref": "dev000", "set": {"power": True}})
    for e in ac.events():
        assert e["banner"] == SIMULATOR_BANNER


def test_banner_in_startup_lines(ac):
    lines = ac.startup_lines()
    assert any(SIMULATOR_BANNER in ln for ln in lines)


def test_advertised_name_carries_marker(ac):
    """BLE 광고명에도 표기 — 스캐너 화면 캡처가 '실가전'으로 읽히지 않게."""
    name = ac.advertised_name()
    assert name.startswith("SIM-NOT-REAL-")
    assert "dev000" in name


def test_console_safe_survives_cp949(monkeypatch):
    """Windows cp949 콘솔 규약: 배너의 em dash는 cp949로 인코딩되지 않는다.
    배너 문자열 자체는 AC3 문면이라 바꾸지 않고 **출력 경로에서** 안전화한다 —
    인코딩 때문에 표기가 통째로 사라지는 것이 최악이다(표기 누락 = NFR6 위반)."""
    class _CP949Stdout:
        encoding = "cp949"

    monkeypatch.setattr(sys, "stdout", _CP949Stdout())
    for ln in ac_startup_lines():
        safe = core.console_safe(ln)
        safe.encode("cp949")                 # 실패하면 예외로 테스트 실패
        assert "실가전 아님" in core.console_safe(SIMULATOR_BANNER)


def ac_startup_lines():
    a = ApplianceState("dev000", "air_conditioner", ["power", "mode"])
    return a.startup_lines()


def test_console_safe_is_identity_on_utf8(monkeypatch):
    class _Utf8Stdout:
        encoding = "utf-8"

    monkeypatch.setattr(sys, "stdout", _Utf8Stdout())
    assert core.console_safe(SIMULATOR_BANNER) == SIMULATOR_BANNER


# ---------- 5. 와이어 계약 (AC2) ----------

def test_command_roundtrip_equal():
    cmd = {"v": 1, "device_ref": "dev000", "set": {"power": True, "target_temp": 24}}
    data, errs = wire.encode_command(cmd)
    assert errs == [] and isinstance(data, bytes)
    back, errs = wire.decode_command(data)
    assert errs == [] and back == cmd


def test_encode_uses_compact_utf8_json():
    """기준 표현은 프로필과 동일한 JSON UTF-8 compact — 새 포맷 발명 금지."""
    cmd = {"v": 1, "device_ref": "dev000", "set": {"power": True}}
    data, _ = wire.encode_command(cmd)
    assert data == json.dumps(cmd, ensure_ascii=False,
                              separators=(",", ":")).encode("utf-8")
    assert b", " not in data and b'": ' not in data


def test_decode_rejects_oversize_before_parsing():
    """명령 상한은 프로필 상한(128KB)이 아니다 — 20B MTU 재조립 DoS 창구 차단."""
    assert wire.MAX_COMMAND_BYTES < st.MAX_WIRE_BYTES
    payload = b"x" * (wire.MAX_COMMAND_BYTES + 1)
    cmd, errs = wire.decode_command(payload)
    assert cmd is None and len(errs) == 1


def test_max_command_bytes_covers_worst_case():
    """상한이 최악 명령을 실제로 수용하는지 실측으로 확인 — 상한이 근거 없는
    숫자가 되지 않게 한다."""
    worst = {"v": 1, "device_ref": "d" * 32,
             "set": {c: ("x" * 64 if c in core.ENUM_CAPABILITIES else 999999)
                     for c in core.KNOWN_CAPABILITIES}}
    data, errs = wire.encode_command(worst)
    assert errs == []
    assert len(data) <= wire.MAX_COMMAND_BYTES


def test_decode_rejects_version_mismatch():
    data = json.dumps({"v": 2, "device_ref": "dev000", "set": {}},
                      separators=(",", ":")).encode("utf-8")
    cmd, errs = wire.decode_command(data)
    assert cmd is None and len(errs) == 1


def test_decode_rejects_duplicate_keys():
    data = b'{"v":1,"device_ref":"a","device_ref":"b","set":{}}'
    cmd, errs = wire.decode_command(data)
    assert cmd is None and len(errs) == 1


def test_decode_accepts_bom():
    cmd = {"v": 1, "device_ref": "dev000", "set": {"power": True}}
    data, _ = wire.encode_command(cmd)
    back, errs = wire.decode_command(b"\xef\xbb\xbf" + data)
    assert errs == [] and back == cmd


def test_decode_never_raises():
    for bad in (None, "문자열", 42, b"", b"\xff\xfe", b"{", b"[]", b"null",
                b'{"v":1}', b'{"device_ref":"a","set":{}}', [1, 2]):
        cmd, errs = wire.decode_command(bad)
        assert cmd is None
        assert isinstance(errs, list) and len(errs) >= 1


def test_encode_never_raises():
    for bad in (None, "x", 42, {"v": 1, "set": {"k": object()}}):
        data, errs = wire.encode_command(bad)
        assert data is None
        assert isinstance(errs, list) and len(errs) >= 1


def test_decode_errors_never_contain_payload():
    marker = "PII-CANARY-daria@example.com"
    data = json.dumps({"v": 9, "device_ref": marker, "set": {}},
                      separators=(",", ":")).encode("utf-8")
    _, errs = wire.decode_command(data)
    assert errs
    for e in errs:
        assert marker not in e


# ---------- 6. 루프백 종단 (AC1·AC2) ----------

def test_loopback_end_to_end(ac):
    t = LoopbackTransport(ac)
    assert t.is_radio is False
    assert t.label == "루프백 — BLE 아님"
    cmd = {"v": 1, "device_ref": "dev000",
           "set": {"power": True, "target_temp": 26, "mode": "cool"}}
    data, _ = wire.encode_command(cmd)
    errs = t.deliver(data)                      # bytes가 전송을 건너 들어온다
    assert errs == []
    snap = ac.snapshot()
    assert snap["state"]["power"] is True
    assert snap["state"]["target_temp"] == 26
    assert snap["state"]["mode"] == "cool"
    assert len(ac.events()) == 1
    assert len(ac.events()[0]["changes"]) == 3


def test_loopback_reports_errors_without_raising(ac):
    t = LoopbackTransport(ac)
    for bad in (None, b"", b"garbage", 42):
        errs = t.deliver(bad)
        assert isinstance(errs, list) and len(errs) >= 1
    assert ac.events() == []


def test_loopback_read_state_carries_banner(ac):
    t = LoopbackTransport(ac)
    payload, errs = t.read_state()
    assert errs == []
    obj = json.loads(payload.decode("utf-8"))
    assert obj["banner"] == SIMULATOR_BANNER


# ---------- 6b. 실행 진입점 (Task 5) ----------

def test_main_loopback_demo_succeeds(capsys):
    from appliance_sim.__main__ import main
    rc = main(["--transport", "loopback"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "루프백 셀프 데모" in out
    assert "seq=1" in out and "seq=3" in out          # 상태 전이가 실제로 보인다


def test_banner_appears_at_every_boundary_not_every_line(capsys):
    """리뷰(Sally) 회귀 고정: 표기 규약 = **경계마다 한 번, 스트림 안엔 생략.**

    v1은 12줄 중 9줄에 배너를 붙였고 테스트는 `count >= 6`으로 통과했다 —
    그 단언은 문자열 개수를 잰 것이지 표기가 읽히는지를 잰 것이 아니다.
    반복 문구는 시각적 노이즈가 되어 필터링된다: 아홉 번 붙이면 아홉 번 안 읽힌다.
    """
    from appliance_sim.__main__ import main
    main(["--transport", "loopback"])
    lines = [ln for ln in capsys.readouterr().out.splitlines() if ln.strip()]

    banner_lines = [ln for ln in lines if SIMULATOR_BANNER in ln]
    # 경계 4곳(기동 헤더·데모 블록·전이 블록·종료 푸터)에 정확히 실린다
    assert len(banner_lines) == 4, banner_lines

    # 반복 스트림(명령 반영·상태 전이 줄)에는 배너가 없다
    stream = [ln for ln in lines
              if ln.lstrip().startswith(("명령 ", "seq="))]
    assert len(stream) >= 6                       # 스트림이 실제로 존재하고
    assert all(SIMULATOR_BANNER not in ln for ln in stream)   # 거기엔 없다


def test_machine_readable_paths_keep_banner(ac):
    """화면에서 걷어낸 것이지 자료구조에서 뺀 게 아니다 — 기계가 읽는 경로는
    노이즈 문제가 없으므로 배너를 유지한다(Sally 규약의 나머지 절반)."""
    ac.apply_command({"device_ref": "dev000", "set": {"power": True}})
    assert ac.snapshot()["banner"] == SIMULATOR_BANNER
    assert all(e["banner"] == SIMULATOR_BANNER for e in ac.events())


def test_main_ble_does_not_silently_fall_back(capsys):
    """--transport ble이 안 되면 사유를 말하고 비정상 종료 — 조용한 루프백
    대체는 '동작한 척'이며 NFR6 위반이다."""
    from appliance_sim.__main__ import main
    rc = main(["--transport", "ble"])
    out = capsys.readouterr().out
    assert rc != 0                                    # 정직한 실패
    assert "루프백 셀프 데모" not in out               # 몰래 돌지 않았다
    assert "SIM-NOT-REAL-" in out                     # 광고명 표기는 남는다


def test_main_respects_device_arguments(capsys):
    from appliance_sim.__main__ import main
    rc = main(["--device-ref", "dev042", "--device-type", "washer"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "dev042" in out and "washer" in out


# ---------- 7. 전송 경계 (AST — 1.3 P3 반영판 재사용) ----------

TRANSPORT_TOKENS = frozenset({"bless", "bleak", "bluez", "winrt",
                              "bluetooth", "dbus"})
CORE_MODULES = (
    ROOT / "appliance_sim" / "core.py",
    ROOT / "appliance_sim" / "wire.py",
    ROOT / "appliance_sim" / "transports" / "loopback.py",
)


def _imported_modules(source: str) -> set:
    """1.3 리뷰 P3 반영판: 동적 import 포함, 심볼명은 대조하지 않는다."""
    segments = set()

    def _add(path: str):
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


def _transport_violations(source: str) -> set:
    hits = set()
    for seg in _imported_modules(source):
        for tok in TRANSPORT_TOKENS:
            if tok in seg:
                hits.add(tok)
    return hits


def test_core_modules_have_no_transport_imports():
    for path in CORE_MODULES:
        assert path.exists(), f"모듈 실종: {path.name}"
        violations = _transport_violations(path.read_text(encoding="utf-8"))
        assert violations == set(), f"{path.name}: 전송 라이브러리 import {violations}"


def test_transport_checker_detects_injected_imports():
    """검사기 스텁 판별 — 아무것도 안 하는 검사기도 '위반 없음'을 낸다."""
    assert _transport_violations("import bless\n") == {"bless"}
    assert _transport_violations("from bleak import BleakClient\n") == {"bleak"}
    assert "bless" in _transport_violations('__import__("bless")\n')
    assert "bluetooth" in _transport_violations("import pybluetooth\n")
    assert _transport_violations("import json\nfrom pathlib import Path\n") == set()


def test_ble_uuids_are_actually_valid_uuids():
    """리뷰(Paige) 회귀 고정: v1의 상수는 UUID가 아니었다
    ('thinqonme001' — 16진수 아님, 마지막 그룹 12자리 아님). BLE 실행이 불가능해
    한 번도 검증되지 않았고, 테스트는 '하드웨어 의존'으로 통째 면제돼 있었다.
    **형식 검증은 하드웨어가 없어도 된다** — 면제 범위가 너무 넓었다."""
    import uuid as _uuid
    from appliance_sim.transports import ble_bless as bb

    for name in ("SERVICE_UUID", "CHAR_COMMAND_UUID", "CHAR_STATE_UUID"):
        value = getattr(bb, name)
        parsed = _uuid.UUID(value)                 # 실패하면 예외로 테스트 실패
        assert str(parsed) == value, name
    # 세 UUID가 서로 달라야 한다 (복붙 실수 방지)
    assert len({bb.SERVICE_UUID, bb.CHAR_COMMAND_UUID, bb.CHAR_STATE_UUID}) == 3


def test_ble_module_is_exempt_and_exists():
    """BLE 바인딩은 검사 면제 — 벤더 의존이 거기에만 있는 것이 경계의 정의."""
    ble = ROOT / "appliance_sim" / "transports" / "ble_bless.py"
    assert ble.exists()
    assert _transport_violations(ble.read_text(encoding="utf-8")) != set()


def test_ble_module_reports_error_when_bless_missing(monkeypatch):
    """bless 부재 환경에서 예외가 아니라 오류 보고 — 하드웨어 없이 고정 가능한
    유일한 BLE 계약(나머지는 하드웨어 의존이라 단위 테스트 면제)."""
    import builtins
    from appliance_sim.transports import ble_bless

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("bless"):
            raise ImportError("no bless here")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    available, errs = ble_bless.check_available()
    assert available is False
    assert isinstance(errs, list) and len(errs) >= 1


def test_ble_distinguishes_missing_from_broken_deps(monkeypatch):
    """리뷰 실측(2026-07-22): bless를 실제로 설치해보니 v1의 오류 문구
    "bless 미설치이거나 어댑터 미지원"이 **거짓**이 됐다 — 설치는 됐는데
    backend 의존성(bleak_winrt)이 깨진 상태였다. 두 사유는 사용자의 대응이
    완전히 다르므로 구분해 보고한다."""
    import builtins
    from appliance_sim.transports import ble_bless

    real_import = builtins.__import__

    def make_fake(missing_name):
        def fake_import(name, *args, **kwargs):
            if name.startswith("bless"):
                raise ImportError(f"No module named {missing_name!r}",
                                  name=missing_name)
            return real_import(name, *args, **kwargs)
        return fake_import

    # 사유 A: bless 자체가 없다
    monkeypatch.setattr(builtins, "__import__", make_fake("bless"))
    _, errs = ble_bless.check_available()
    assert len(errs) == 1 and "미설치" in errs[0]

    # 사유 B: bless는 있는데 backend 의존성이 깨졌다 (실측된 상황)
    monkeypatch.setattr(builtins, "__import__", make_fake("bleak_winrt"))
    _, errs = ble_bless.check_available()
    assert len(errs) == 1 and "의존성" in errs[0]
    assert "미설치" not in errs[0]          # 거짓 사유를 대지 않는다
