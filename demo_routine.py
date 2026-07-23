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
    p.add_argument("--offline", action="store_true",
                   help="오프라인 강제 하네스 안에서 실행 (Story 2.3)")
    args = p.parse_args(argv)

    # 경계 1: 기동 헤더 — 배너 1회
    _emit("=" * 62)
    _emit(f"  {SIMULATOR_BANNER}")
    _emit("  프로필 -> 캐리어 -> 루틴 -> BLE 청킹 -> 가전")
    _emit("=" * 62)

    if args.offline:
        _offline_preamble()

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

    # 오프라인 모드면 하네스 안에서 실행한다 — "부르지 않았다"가 아니라
    # "부를 수 없다"(2.3). 위반은 OfflineViolation(BaseException)으로 터진다.
    if args.offline:
        import offline_guard
        with offline_guard.enforce_offline():
            result, errs = execute_routine(carrier, transports, RECORD,
                                           args.routine, mtu=args.mtu)
    else:
        result, errs = execute_routine(carrier, transports, RECORD,
                                       args.routine, mtu=args.mtu)
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
          f"{result['mtu']}B 청크 {result['chunks_sent']}개")
    # 2.3에서 R5가 풀렸다: 수신 측 재조립이면 청크가 실제로 전송 계층을 거친다.
    # 정직 표기를 경로에 따라 조건부로 낸다(Sally·Winston 규약 유지).
    if result["reassembled_by"] == "receiver":
        _emit("  청크가 전송 계층을 거쳐 수신 측에서 재조립됨(무선 구간 구조 반영)")
    else:
        _emit("  ※ 청크 수는 계산값 — 송신 측 재조립본 전송(구형 전송 폴백)")
    if args.offline:
        _emit("오프라인 강제 완료 — 차단 상태에서 위 실행이 성공했다")
    else:
        _emit("네트워크 호출 0건 (증거와 한계: docs/OFFLINE_EVIDENCE.md)")
    _emit(f"[{SIMULATOR_BANNER}] — 이 산출물은 실가전 데이터가 아니다")
    return 0


def _offline_preamble():
    """차단 사실을 화면에 표시한다(AC2). **관찰이지 주장이 아니다** —
    차단이 실제로 작동함을 그 자리에서 시연(일부러 연결 시도 → 실패 확인)한다.

    ⚠️ 한계도 같이 적는다: 코드가 아는 것은 '이 파이썬 프로세스가 못 나간다'
    까지다. 기내모드는 사람이 눌러야 하고 코드는 그것을 관측하지 못한다."""
    import socket

    import offline_guard
    _emit()
    _emit(f"--- 오프라인 강제 시연 · {SIMULATOR_BANNER} ---")
    with offline_guard.enforce_offline():
        try:
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            _emit("  차단 시연 실패 — 소켓이 열렸다(하네스 오작동)")
        except offline_guard.OfflineViolation:
            _emit("  차단 시연: 소켓 열기 시도 -> 실패 확인 (하네스 활성)")
    _emit("  ※ 한계: 이 차단은 '이 파이썬 프로세스가 못 나간다'까지다.")
    _emit("    장비 차단(기내모드)은 사람이 누르는 것이며 코드가 증명하지 못한다.")
    _emit("    발표 시연 절차: docs/DEMO_SCRIPT.md")


if __name__ == "__main__":
    sys.exit(main())
