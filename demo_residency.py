# -*- coding: utf-8 -*-
"""데이터 소재 명시 데모 (Story 4.2, FR7).

    python demo_residency.py            # 데이터 소재 확인
    python demo_residency.py --offline  # 소재 확인에 서버가 필요 없음을 강제 증명

Epic 4의 마무리 축. 4.1(무계정)에 이어 **"그럼 내 데이터는 어디"**에 답한다 —
프로필 원본이 온바디에 있고 서버는 원본을 갖지 않음을 **관찰로 증명**한다.
"서버에 없다"를 말이 아니라 화면으로 보인다(P-3 반박 마무리).

⚠️ **한계 정직 표기.** 이 증명은 이 참조 어댑터·이 프로세스에서 서버로 가는
경로가 없음까지다. 실기기·실가전 연동 데이터 흐름은 범위 밖(시뮬레이터 기반).
"""
import argparse
import sys

from appliance_sim.core import SIMULATOR_BANNER, console_safe
from home_profile import MemoryCarrier, data_residency, onboard_local

_DEVICES = [
    {"device_ref": "ac1", "device_type": "air_conditioner",
     "capabilities": ["power", "target_temp"]},
    {"device_ref": "light1", "device_type": "light", "capabilities": ["power"]},
    {"device_ref": "fridge1", "device_type": "refrigerator",
     "capabilities": ["child_lock"]},
]


def _emit(line=""):
    print(console_safe(line))


def _yn(v):
    return "예" if v else "아니오"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="demo_residency",
        description=f"{SIMULATOR_BANNER} — 데이터 소재 명시 (Story 4.2)")
    p.add_argument("--offline", action="store_true",
                   help="오프라인 강제 안에서 소재 확인 (서버가 필요 없음)")
    args = p.parse_args(argv)

    carrier = MemoryCarrier()

    # 경계 1: 기동 헤더 — 배너 1회
    _emit("=" * 62)
    _emit(f"  {SIMULATOR_BANNER}")
    _emit("  데이터 소재 명시 — \"서버에 없다\"를 화면으로 증명 (FR7)")
    _emit("=" * 62)

    profile, on_report = onboard_local(_DEVICES, carrier)   # 4.1 온보딩
    if profile is None:
        _emit(f"[{SIMULATOR_BANNER}] 온보딩 실패: {on_report['errors'][0]}")
        return 1

    if args.offline:
        import offline_guard
        try:
            with offline_guard.enforce_offline():
                r = data_residency(profile, carrier)
        except offline_guard.OfflineViolation as v:
            _emit(f"[{SIMULATOR_BANNER}] ⚠️ 소재 확인이 네트워크를 건드렸다: {v}")
            return 1
    else:
        r = data_residency(profile, carrier)
    if r["errors"]:
        _emit(f"[{SIMULATOR_BANNER}] 소재 확인 실패: {r['errors'][0]}")
        return 1

    # 경계 2: 데이터 소재 — 배너 1회
    _emit()
    _emit(f"--- 데이터 소재 · {SIMULATOR_BANNER} ---")
    _emit(f"  원본 위치: {r['profile_location']}")
    _emit(f"  서버 원본 보유: {_yn(r['server_holds_original'])}")
    _emit(f"  서버로 전송되는 항목: "
          f"{'없음' if not r['server_transmitted'] else ', '.join(r['server_transmitted'])}")
    _emit(f"  온바디만으로 복원 가능: {_yn(r['restorable_from_onbody'])}  "
          f"← 원본이 온바디에 있다는 증거")

    # 경계 3: 온바디 footprint — 배너 1회. 종류·개수·바이트(이름 비노출).
    _emit()
    _emit(f"--- 온바디 footprint · {SIMULATOR_BANNER} ---")
    k = r["onbody_kinds"]
    _emit(f"  레코드 {r['onbody_record_count']}개 "
          f"(meta {k['meta']}·기기 {k['device']}·루틴 {k['routine']}) · "
          f"{r['onbody_bytes']:,}B")
    if args.offline:
        _emit("  오프라인 강제 활성 — 소재를 알아내는 데 서버가 필요 없음을 강제 증명")

    # 경계 4: 종료 푸터 — 배너 1회
    _emit()
    _emit("서버에 없다 — 말이 아니라 관찰로 증명했다 (FR7, P-3 반박 마무리)")
    _emit("  ※ 한계: 이 참조 어댑터·이 프로세스 범위. 실기기 데이터 흐름은 범위 밖")
    _emit(f"[{SIMULATOR_BANNER}] 참조 어댑터 기반 — 실기기(가민) 시연 아님")
    return 0


if __name__ == "__main__":
    sys.exit(main())
