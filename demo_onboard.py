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

from appliance_sim.core import SIMULATOR_BANNER, console_safe
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


def _emit(line=""):
    print(console_safe(line))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="demo_onboard",
        description=f"{SIMULATOR_BANNER} — 무계정 로컬 온보딩 (Story 4.1)")
    p.add_argument("--offline", action="store_true",
                   help="오프라인 강제 안에서 온보딩 (계정 생성이 서버를 부를 자리가 없다)")
    args = p.parse_args(argv)

    carrier = MemoryCarrier()                      # 워치 대역 — 실기기 아님

    # 경계 1: 기동 헤더 — 배너 1회
    _emit("=" * 62)
    _emit(f"  {SIMULATOR_BANNER}")
    _emit(f"  무계정 온보딩 — P-3 반박: \"{PAIN}\"")
    _emit("=" * 62)

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

    # 경계 2: 온보딩 결과 — 배너 1회
    _emit()
    _emit(f"--- 온보딩 완료 · {SIMULATOR_BANNER} ---")
    _emit(f"  계정 생성 {int(report['account_created'])}회 · "
          f"로그인 {int(report['login_performed'])}회 · "
          f"클라우드 조회 {report['network_calls']}회")
    _emit(f"  기기 연결 {report['devices_connected']}대 · 프로필 온바디 저장 완료")
    if args.offline:
        _emit("  오프라인 강제 활성 — 계정 생성이 서버를 부를 자리가 없음을 강제 증명")

    # 경계 3: 동의 범위 — 배너 1회. 정직한 최소.
    _emit()
    _emit(f"--- 동의 범위 · {SIMULATOR_BANNER} ---")
    _emit("  요구하는 것 (로컬 동작용):")
    for c in LOCAL_CONSENT_SCOPE:
        _emit(f"    · {c['item']} — {c['purpose']}")
    _emit("  요구하지 않는 것:")
    for c in NOT_REQUIRED:
        _emit(f"    · {c['item']} — {c['why']}")

    # 경계 4: 종료 푸터 — 배너 1회
    _emit()
    _emit("신원을 넘기지 않고 집을 연결했다 — 무계정은 결함이 아니라 셀링포인트 (FR6)")
    _emit("서버가 원본을 갖지 않는다 — 데이터 소재 명시는 4.2(FR7)에서 이어진다")
    _emit(f"[{SIMULATOR_BANNER}] 참조 어댑터 기반 — 실기기(가민) 시연 아님")
    return 0


if __name__ == "__main__":
    sys.exit(main())
