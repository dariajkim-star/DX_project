# -*- coding: utf-8 -*-
"""무계정 로컬 온보딩 데모 (Story 4.1, FR6).

    python demo_onboard.py            # 무계정 온보딩
    python demo_onboard.py --offline  # 서버가 개입할 자리가 없음을 강제 증명

Epic 4의 첫 장면. P-3("굳이 회원가입을 강요하는 이유가 뭡니까", 6.2%)를 구조로
반박한다: 계정·로그인 **없이** 온보딩이 완결된다. 무계정은 결함이 아니라
**신원을 넘기지 않아도 되는 셀링포인트**다.

⚠️ **무계정은 구조다.** onboard_local에는 자격증명 인자가 없고 경로에 네트워크
호출이 없다(3.1 AC3 계보). `--offline`에서 성공하는 것이 그 증명이다.
"""
import argparse
import sys

import demo_ui
from appliance_sim.core import SIMULATOR_BANNER
from home_profile import (
    LOCAL_CONSENT_SCOPE,
    MemoryCarrier,
    NOT_REQUIRED,
    onboard_local,
)

# P-3 대표 리뷰 — CX_DEFINITION §2 대조 완료.
PAIN = "굳이 회원가입을 강요하는 이유가 뭡니까"

_DEVICES = [
    {"device_ref": "ac1", "device_type": "air_conditioner",
     "capabilities": ["power", "target_temp"]},
    {"device_ref": "light1", "device_type": "light", "capabilities": ["power"]},
]


_emit = demo_ui.emit


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="demo_onboard",
        description=f"{SIMULATOR_BANNER} — 무계정 로컬 온보딩 (Story 4.1)")
    p.add_argument("--offline", action="store_true",
                   help="오프라인 강제 안에서 온보딩 (계정 생성이 서버를 부를 자리가 없다)")
    args = p.parse_args(argv)

    carrier = MemoryCarrier()                      # 워치 대역 — 실기기 아님

    # 경계 1: 기동 헤더 — 배너 1회
    demo_ui.title_block(SIMULATOR_BANNER, f"무계정 온보딩 — P-3 반박: \"{PAIN}\"")

    # 온보딩 — 계정·로그인 없이
    if args.offline:
        import offline_guard
        try:
            with offline_guard.enforce_offline():
                profile, report = onboard_local(_DEVICES, carrier)
        except offline_guard.OfflineViolation as v:
            _emit(f"[{SIMULATOR_BANNER}] ⚠️ 온보딩이 네트워크를 건드렸다: {v}")
            return 1
    else:
        profile, report = onboard_local(_DEVICES, carrier)
    if profile is None:
        _emit(f"[{SIMULATOR_BANNER}] 온보딩 실패: {report['errors'][0]}")
        return 1

    # 경계 2: 온보딩 결과 — 배너 1회. 관찰한 것만 보고한다(측정 안 한 카운트 금지).
    demo_ui.scene_header("온보딩 완료", SIMULATOR_BANNER)
    # 판정은 실측이다: 연결 수가 요청 기기 수와 일치할 때만 ✓ (상수 ok 금지 — 교훈 1)
    demo_ui.transition_row(
        "기기 연결",
        "ok" if report["devices_connected"] == len(_DEVICES) else "blocked",
        code_kv=f"devices_connected: {report['devices_connected']}",
        job="프로필 온바디 저장 완료")
    _emit("  계정·로그인 요구: 없음 (아래 '요구하지 않는 것' 참조)")
    if args.offline:
        _emit("  오프라인 강제 안에서 완료 — 서버 조회가 불가한 상태에서 성공(구조 증명)")

    # 경계 3: 동의 범위 — 배너 1회. 정직한 최소.
    # 요구하는 것 vs 않는 것 대비 표 — 같은 서식, 같은 무게 (S4 대비 패턴)
    demo_ui.scene_header("동의 범위 — 요구하는 것 vs 요구하지 않는 것",
                         SIMULATOR_BANNER)
    _emit("  요구하는 것 (로컬 동작용):")
    for c in LOCAL_CONSENT_SCOPE:
        _emit(f"    · {c['item']} — {c['purpose']}")
    _emit("  요구하지 않는 것:")
    for c in NOT_REQUIRED:
        _emit(f"    · {c['item']} — {c['why']}")

    # 경계 4: 종료 푸터 — 배너 1회. 확정 마이크로카피(S4) 유지.
    _emit()
    _emit("신원을 넘기지 않고 집을 연결했다 — 무계정은 결함이 아니라 셀링포인트 (FR6)")
    _emit("계정을 참는 게 아니라 만들 자리가 없다 — 서버가 원본을 갖지 않는다. "
          "데이터 소재 명시는 4.2(FR7)에서 이어진다")
    demo_ui.honesty_footer(
        [f"[{SIMULATOR_BANNER}] 참조 어댑터 기반 — 실기기(가민) 시연 아님"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
