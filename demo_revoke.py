# -*- coding: utf-8 -*-
"""프로필 폐기 데모 (Story 4.4, NFR2).

    python demo_revoke.py            # 폐기 → 복원 불가 → 복구(재온보딩)
    python demo_revoke.py --offline  # 서버 없이 폐기됨을 강제 증명(AC2)

Epic 4의 마지막 장면. 온바디 구조의 가장 날카로운 반박 **"잃어버리면요?"**에
답한다. 폐기의 의미는 '레코드 삭제'가 아니라 **'그 프로필로 가전을 못 연다'** —
지운 뒤 복원을 시도해 실패를 확인한다.

⚠️ **원격 소거가 아니다.** 캐리어에 접근할 수 있을 때 성립한다(회수했거나 양도 전).
   서버 없는 구조의 대가이며, 정직하게 남긴 한계다. 상세: docs/REVOCATION.md
"""
import argparse
import sys

from appliance_sim.core import SIMULATOR_BANNER, console_safe
from home_profile import (
    MemoryCarrier,
    data_residency,
    onboard_local,
    restore_from_carrier,
    revoke_onbody,
)

_DEVICES = [
    {"device_ref": "ac1", "device_type": "air_conditioner",
     "capabilities": ["power", "target_temp"]},
    {"device_ref": "light1", "device_type": "light", "capabilities": ["power"]},
]
_FRESH = [{"device_ref": "newac", "device_type": "air_conditioner",
           "capabilities": ["power"]}]


def _emit(line=""):
    print(console_safe(line))


def _yn(v):
    return "예" if v else "아니오"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="demo_revoke",
        description=f"{SIMULATOR_BANNER} — 프로필 폐기 (Story 4.4)")
    p.add_argument("--offline", action="store_true",
                   help="오프라인 강제 안에서 폐기 (서버 없이 폐기됨)")
    args = p.parse_args(argv)

    carrier = MemoryCarrier()

    # 경계 1: 기동 헤더 — 배너 1회
    _emit("=" * 62)
    _emit(f"  {SIMULATOR_BANNER}")
    _emit("  프로필 폐기 — \"잃어버리면요?\"에 대한 답 (NFR2)")
    _emit("=" * 62)

    # 장면 1: 폐기 전 — 온바디에 프로필이 있고 복원된다
    profile, on_rep = onboard_local(_DEVICES, carrier)
    if profile is None:
        _emit(f"[{SIMULATOR_BANNER}] 온보딩 실패: {on_rep['errors'][0]}")
        return 1
    before = data_residency(profile, carrier)
    _emit()
    _emit(f"--- 장면 1: 폐기 전 · {SIMULATOR_BANNER} ---")
    _emit(f"  온바디 레코드 {before['onbody_record_count']}개 · "
          f"{before['onbody_bytes']:,}B")
    _emit(f"  온바디만으로 복원 가능: {_yn(before['restorable_from_onbody'])}")

    # 장면 2: 폐기 — 서버 없이
    _emit()
    _emit(f"--- 장면 2: 폐기 실행 · {SIMULATOR_BANNER} ---")
    if args.offline:
        import offline_guard
        try:
            with offline_guard.enforce_offline():
                ok, rep = revoke_onbody(carrier)
        except offline_guard.OfflineViolation as v:
            _emit(f"[{SIMULATOR_BANNER}] ⚠️ 폐기가 네트워크를 건드렸다: {v}")
            return 1
        _emit("  오프라인 강제 활성 — 서버 없이 폐기됨을 강제 증명(AC2)")
    else:
        ok, rep = revoke_onbody(carrier)
    if not ok:
        _emit(f"[{SIMULATOR_BANNER}] 폐기 실패: {rep['errors'][0]}")
        return 1
    _emit(f"  레코드 {rep['records_erased']}개 삭제")
    _emit(f"  폐기 후 복원 가능: {_yn(rep['restorable_after'])}  "
          f"← 지웠다는 보고가 아니라 **복원 시도로 검증**")
    residue = rep["residual_records"]
    _emit(f"  잔류 레코드: {'판정 불가' if residue is None else f'{residue}건'}  "
          f"← '복원 불가'와 '잔류 0'은 다른 주장이라 **둘 다** 확인한다")

    # 장면 3: 폐기 후 — 제어 불가
    _emit()
    _emit(f"--- 장면 3: 폐기 후 · {SIMULATOR_BANNER} ---")
    restored, errs = restore_from_carrier(carrier)
    _emit(f"  프로필 복원 시도: {'성공(!)' if restored else '실패'} — "
          f"{'남의 손목에서도 집이 열린다' if restored else '그 프로필로는 가전을 못 연다'}")
    if restored:
        return 1

    # 장면 4: 복구 — 폐기 후 재온보딩(AC3)
    _emit()
    _emit(f"--- 장면 4: 복구(재설정) · {SIMULATOR_BANNER} ---")
    fresh, rep2 = onboard_local(_FRESH, carrier)
    if fresh is None:
        _emit(f"  재온보딩 실패: {rep2['errors'][0]}")
        return 1
    _emit(f"  폐기된 워치에 재온보딩 성공 — 기기 {rep2['devices_connected']}대 연결")
    _emit("  (4.1의 재온보딩 거부는 meta 존재로 판정 — 폐기가 그것을 지워 복구가 열린다)")

    # 경계: 종료 푸터 — 배너 1회. 잔여 한계 정직 표기.
    _emit()
    _emit("잃어버려도 집은 남의 손목에 남지 않는다 — 서버 없이 폐기 (NFR2)")
    _emit("  ※ 잔여 한계: **원격 소거가 아니다** — 캐리어 접근이 전제(회수·양도 전).")
    _emit("     원격 소거는 서버·계정을 요구해 무계정 구조와 충돌한다. 기기 PIN이 1차 방어")
    _emit("  상세: docs/REVOCATION.md · docs/THREAT_MODEL.md")
    _emit(f"[{SIMULATOR_BANNER}] 참조 어댑터 기반 — 실기기(가민) 시연 아님")
    return 0


if __name__ == "__main__":
    sys.exit(main())
