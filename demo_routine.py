# -*- coding: utf-8 -*-
"""종단 데모 — 프로필에서 가전까지 (Story 2.2, Task 6).

    python demo_routine.py                 # 루틴 0 실행
    python demo_routine.py --routine 1

`python -m appliance_sim`(2.1, 받는 쪽 단독)과 짝이 되는 실행 경로다.
여기서는 **보내는 쪽**이 붙는다: 프로필 생성 → 캐리어 저장 → 루틴 실행 →
청킹 → 시뮬레이터 상태 전이.

표기 규약(docs/CARRIER_INTERFACE.md §4-b, 2.1 파티 리뷰 Sally): 배너는
**경계마다 한 번, 반복 스트림 안에서는 생략**한다.
"""
import argparse
import sys

from appliance_sim.core import SIMULATOR_BANNER, ApplianceState, console_safe
from appliance_sim.transports.loopback import LoopbackTransport
from home_profile import MemoryCarrier, execute_routine, serialize
from home_profile import routine as rt
from home_profile import storage as st

RECORD = "profile"


def _emit(line=""):
    print(console_safe(line))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="demo_routine",
        description=f"{SIMULATOR_BANNER} — 프로필 기반 루틴 실행 (Story 2.2)")
    p.add_argument("--routine", type=int, default=0, help="실행할 루틴 인덱스")
    p.add_argument("--devices", type=int, default=3, help="샘플 기기 수")
    p.add_argument("--routines", type=int, default=2, help="샘플 루틴 수")
    p.add_argument("--mtu", type=int, default=20, help="BLE 특성 MTU (기본 20)")
    args = p.parse_args(argv)

    # 경계 1: 기동 헤더 — 배너 1회
    _emit("=" * 62)
    _emit(f"  {SIMULATOR_BANNER}")
    _emit("  프로필 -> 캐리어 -> 루틴 -> BLE 청킹 -> 가전")
    _emit("=" * 62)

    profile = st.make_sample_profile(args.devices, args.routines)
    data, errs = serialize(profile)
    if errs:
        _emit(f"[{SIMULATOR_BANNER}] 프로필 직렬화 실패: {errs[0]}")
        return 1

    carrier = MemoryCarrier()
    errs = carrier.put_records({RECORD: data})
    if errs:
        _emit(f"[{SIMULATOR_BANNER}] 캐리어 저장 실패: {errs[0]}")
        return 1
    _emit(f"온바디 저장: {len(data):,}B -> {carrier.label}")

    appliances = {d["device_ref"]: ApplianceState(
        d["device_ref"], d["device_type"], d["capabilities"])
        for d in profile["devices"]}
    transports = {ref: LoopbackTransport(a) for ref, a in appliances.items()}
    _emit(f"가전 시뮬레이터 {len(appliances)}대 · 전송: "
          f"{next(iter(transports.values())).label}")

    # 경계 2: 블록 헤더 — 배너 1회. 이하 반복 줄에는 붙이지 않는다
    _emit()
    _emit(f"--- 루틴 {args.routine} 실행 · {SIMULATOR_BANNER} ---")
    commands, errs = rt.routine_to_commands(profile, args.routine)
    if errs:
        _emit(f"[{SIMULATOR_BANNER}] 루틴 변환 실패: {errs[0]}")
        return 1
    for c in commands:
        body = rt._encode(c)
        pieces, errs = rt.chunk(body, args.mtu)
        if errs:
            _emit(f"[{SIMULATOR_BANNER}] 청킹 실패: {errs[0]}")
            return 1
        _emit(f"  {c['device_ref']}: 명령 {len(body)}B -> "
              f"{args.mtu}B 청크 {len(pieces)}개로 분할 가능")

    result, errs = execute_routine(carrier, transports, RECORD, args.routine,
                                   mtu=args.mtu)
    if errs:
        _emit(f"[{SIMULATOR_BANNER}] 실행 실패: {errs[0]}")
        return 1

    # 경계 3: 블록 헤더 — 배너 1회
    _emit()
    _emit(f"--- 가전 상태 전이 · {SIMULATOR_BANNER} ---")
    for ref in sorted(appliances):
        for ev in appliances[ref].events():
            for ch in ev["changes"]:
                _emit("  %s seq=%d %s: %r -> %r"
                      % (ref, ev["seq"], ch["capability"], ch["old"], ch["new"]))

    # 경계 4: 종료 푸터 — 배너 1회
    _emit()
    _emit(f"명령 {result['commands']}건 · 기기 {result['devices_commanded']}대 · "
          f"{result['mtu']}B 청크 {result['chunks_sent']}개 분량")
    # ⚠️ 정직 표기(리뷰 2026-07-22, Sally·Winston): 청크 수는 실제로 계산한
    # 값이지만, 이 실행 경로는 쪼갠 것을 그 자리에서 재조립해 전송한다 —
    # 즉 **무선 구간이 시뮬레이션되지 않았다.** "3개로 쪼개서 보냈다"로 읽히면
    # 사실이 아니다. 실제 분할 전송은 2.3(실기기 무선 구간)의 일이다.
    _emit("  ※ 청크 수는 계산값 — 이 경로는 재조립본을 전송한다(무선 구간 미시뮬레이션)")
    _emit("네트워크 호출 0건 (증거와 한계: docs/OFFLINE_EVIDENCE.md)")
    _emit(f"[{SIMULATOR_BANNER}] — 이 산출물은 실가전 데이터가 아니다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
