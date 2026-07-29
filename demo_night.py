# -*- coding: utf-8 -*-
"""Night Keeper 야간 모드 시나리오 데모 (Story 2.4).

    python demo_night.py            # 야간 모드 실행
    python demo_night.py --offline  # 잠들기 전, 네트워크 없이, 손목만으로

Epic 2의 마지막 장면이자 발표 클라이맥스다. 지금까지의 모든 코드가 이 한
장면으로 수렴한다:
  - 프로필·캐리어 (Epic 1)
  - 루틴 실행·청킹 (2.2)
  - 수신 측 재조립 (2.3 R5 해소)
  - 오프라인 강제 (2.3)

⚠️ **새 기능을 만들지 않는다.** 야간 모드는 기존 capability 조합을 담은
**루틴 하나**이며, `routine_to_commands`·`execute_routine`이 그대로 처리한다.
새 실행 경로·새 전송·새 상태 기계가 없다(스토리 함정 1).

⚠️ **`home_profile/`을 수정하지 않는다.** 야간 프로필은 여기서 조립한다 —
시뮬레이터는 프로필의 소비자이지 소유자가 아니다(경계, 1.2 규약).
"""
import argparse
import sys

import demo_ui
from appliance_sim.core import SIMULATOR_BANNER, ApplianceState
from appliance_sim.transports.loopback import LoopbackTransport
from home_profile import MemoryCarrier, execute_routine, serialize
from home_profile import storage as st

RECORD = "profile"
NIGHT_ROUTINE_INDEX = 0

# Job 문장 — 발표 자료·화면·페르소나 문서에서 같은 문구를 쓴다.
JOB = "내가 잠든 뒤에도 집이 아이를 지킨다"

# 야간 모드 = 기존 어휘 조합. 아이를 깨우지 않으려면:
#   - 소음원(로봇청소기·건조기)은 끈다 (power/eco)
#   - 아이 손 닿는 곳은 잠근다 (child_lock)
#   - 에어컨은 조용히 (fan_speed low)
# 각 액션이 Job의 어느 부분을 실현하는지 주석으로 대응시킨다(AC2 근거).
_NIGHT_DEVICES = [
    # (ref, type, capabilities, 초기설정)
    ("dev_ac", "air_conditioner", ["power", "target_temp", "fan_speed"],
     {"power": True, "target_temp": 24, "fan_speed": "high"}),
    ("dev_cleaner", "robot_cleaner", ["power", "mode"],
     {"power": True, "mode": "auto"}),
    ("dev_light", "light", ["power"],
     {"power": True}),
    ("dev_fridge", "refrigerator", ["mode", "child_lock"],
     {"mode": "auto", "child_lock": False}),
]

# 야간 루틴 액션 — 무엇이 어떻게 바뀌는가 + Job 대응
_NIGHT_ACTIONS = [
    ("dev_ac", "fan_speed", "low",     "에어컨 바람 약하게 — 소음↓"),
    ("dev_cleaner", "power", False,    "로봇청소기 끔 — 아이를 깨우지 않게"),
    ("dev_light", "power", False,      "조명 끔 — 밤"),
    ("dev_fridge", "child_lock", True, "냉장고 잠금 — 아이 손 닿는 곳"),
]


def build_night_profile() -> dict:
    """야간 모드 루틴을 담은 프로필. `validate_profile()`을 통과한다.

    기존 어휘만 쓴다(새 capability 없음). 이 함수가 데모·테스트의 단일
    진실 원천이다."""
    p = st.new_profile()
    for ref, dtype, caps, settings in _NIGHT_DEVICES:
        p["devices"].append(
            {"device_ref": ref, "device_type": dtype, "capabilities": caps})
        p["settings"][ref] = dict(settings)
    p["routines"].append({
        "trigger": {"type": "time", "params": {"at": "22:30"}},
        "actions": [{"device_ref": ref, "setting_key": key, "value": val}
                    for ref, key, val, _job in _NIGHT_ACTIONS],
    })
    return p


_emit = demo_ui.emit


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="demo_night",
        description=f"{SIMULATOR_BANNER} — Night Keeper 야간 모드 (Story 2.4)")
    p.add_argument("--offline", action="store_true",
                   help="오프라인 강제 안에서 실행 (잠들기 전, 네트워크 없이)")
    p.add_argument("--mtu", type=int, default=20, help="BLE 특성 MTU (기본 20)")
    args = p.parse_args(argv)

    # 경계 1: 기동 헤더 — 배너 1회 (S1 scene_header — Job 문장이 화면 상단에)
    demo_ui.title_block(SIMULATOR_BANNER, f"Night Keeper — \"{JOB}\"")

    if args.offline:
        _offline_scene()

    profile = build_night_profile()
    data, errs = serialize(profile)
    if errs:
        _emit(f"[{SIMULATOR_BANNER}] 프로필 직렬화 실패: {errs[0]}")
        return 1
    carrier = MemoryCarrier()
    if carrier.put_records({RECORD: data}):
        _emit(f"[{SIMULATOR_BANNER}] 캐리어 저장 실패")
        return 1

    appliances = {ref: ApplianceState(ref, dtype, caps)
                  for ref, dtype, caps, _s in _NIGHT_DEVICES}
    transports = {ref: LoopbackTransport(a) for ref, a in appliances.items()}
    _emit(f"온바디 저장: {len(data):,}B · 가전 {len(appliances)}대")

    # 경계 2: 야간 모드 블록 — 배너 1회. Job 대응을 함께 보인다 (실행 전 의도 표기)
    demo_ui.scene_header("야간 모드 전환", SIMULATOR_BANNER)
    for _ref, _key, _val, job in _NIGHT_ACTIONS:
        _emit(f"  · {job}")

    if args.offline:
        import offline_guard
        try:
            with offline_guard.enforce_offline():
                result, errs = execute_routine(carrier, transports, RECORD,
                                               NIGHT_ROUTINE_INDEX, mtu=args.mtu)
        except offline_guard.OfflineViolation as v:
            _emit(f"[{SIMULATOR_BANNER}] ⚠️ 오프라인 위반 탐지: {v}")
            return 1
    else:
        result, errs = execute_routine(carrier, transports, RECORD,
                                       NIGHT_ROUTINE_INDEX, mtu=args.mtu)
    if errs:
        _emit(f"[{SIMULATOR_BANNER}] 실행 실패: {errs[0]}")
        return 1

    # 경계 3: 상태 전이 블록 — 배너 1회. 스트림 라인(dev_/seq=)은 형태 그대로,
    # 그 **주변에** 전이 4행(판정+Job 대응)을 입힌다 — 발표자가 행 단위로 말을 얹는다.
    demo_ui.scene_header("가전 상태 전이", SIMULATOR_BANNER)
    for ref in sorted(appliances):
        for ev in appliances[ref].events():
            for ch in ev["changes"]:
                _emit("  %s seq=%d %s: %r -> %r"
                      % (ref, ev["seq"], ch["capability"], ch["old"], ch["new"]))
    _emit()
    for ref, key, val, job in _NIGHT_ACTIONS:
        # 판정은 실측이다: 전이 후 상태가 의도값과 일치하는지 확인한 결과만 표기
        applied = appliances[ref].snapshot()["state"].get(key) == val
        # job 문자열 규약: "라벨 — Job 대응". 구분자가 없으면 중복 출력 대신 통짜 라벨.
        parts = job.split(" — ", 1)
        demo_ui.transition_row(parts[0],
                               "ok" if applied else "blocked",
                               code_kv=f"{key}: {val}",
                               job=parts[1] if len(parts) > 1 else "")

    # 경계 4: 종료 푸터 — 배너 1회
    _emit()
    _emit(f"기기 {result['devices_commanded']}대 전환 · "
          f"재조립 {result['reassembled_by']}")
    if args.offline:
        _emit("오프라인 강제 완료 — 잠들기 전, 네트워크 없이, 손목만으로 성공했다")
        _emit("  SPOF(클라우드 단일 장애점) 제거 — LG 자기약속 'Effortless'의 실현")
    _emit(f"Job 실현: \"{JOB}\"")
    demo_ui.honesty_footer([
        "child_lock은 시뮬레이터 상태 전이 — 안전 기능 아님(NFR5)",
        f"[{SIMULATOR_BANNER}] — 이 산출물은 실가전 데이터가 아니다",
    ])
    return 0


def _offline_scene():
    """차단 시연 (2.3 재사용) — 관찰이지 주장이 아니다. 한계도 같이."""
    import socket

    import offline_guard
    demo_ui.scene_header("오프라인 강제 시연", SIMULATOR_BANNER)
    with offline_guard.enforce_offline():
        try:
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            _emit("  차단 시연 실패 — 소켓이 열렸다(하네스 오작동)")
        except offline_guard.OfflineViolation:
            # ✗는 증거다 — 소켓 열기 실패가 바라던 결과 (DESIGN.md blocked 의미역)
            demo_ui.transition_row("차단 시연: 소켓 열기 시도", "blocked",
                                   code_kv="socket.socket -> OfflineViolation",
                                   job="실패 확인 (하네스 활성)")
    demo_ui.honesty_footer([
        "※ 한계: 이 차단은 '이 파이썬 프로세스가 못 나간다'까지다.",
        "  장비 차단(기내모드)은 사람이 누른다 — docs/DEMO_SCRIPT.md",
    ])


if __name__ == "__main__":
    sys.exit(main())
