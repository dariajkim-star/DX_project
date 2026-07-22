# -*- coding: utf-8 -*-
"""가전 시뮬레이터 실행 진입점 (Story 2.1, Task 5).

    python -m appliance_sim                          # 루프백 셀프 데모(기본)
    python -m appliance_sim --transport ble          # BLE 기동 시도
    python -m appliance_sim --device-ref dev001 --device-type washer

**조용한 루프백 대체 금지**: `--transport ble`이 안 되면 사유를 출력하고
비정상 종료한다. 사용자가 명시한 전송이 안 되는데 몰래 다른 걸로 도는 것은
"동작한 척"이며 NFR6 위반이다.
"""
import argparse
import sys

from .core import SIMULATOR_BANNER, ApplianceState, console_safe
from .transports.ble_bless import BleServerBinding
from .transports.loopback import LoopbackTransport
from .wire import encode_command

# 루프백 셀프 데모용 명령 — 발표 리허설·스크린샷용 상태 전이 3단
_SELF_DEMO_COMMANDS = (
    {"power": True},
    {"mode": "cool", "target_temp": 26},
    {"target_temp": 22, "fan_speed": "low"},      # 야간 모드 흉내(2.4의 예고)
)


def _emit(line: str):
    print(console_safe(line))


def _banner_rule_note() -> str:
    """표기 규약(리뷰 2026-07-22, Sally): **경계마다 한 번, 스트림 안에선 생략.**

    v1은 출력 12줄 중 9줄에 배너를 붙였다. 반복 문구는 몇 초 만에 시각적
    노이즈가 되어 뇌가 필터링한다 — 아홉 번 붙이면 아홉 번 안 읽힌다.
    테스트는 통과했지만(`out.count(BANNER) >= 6`) 그건 문자열 개수를 잰 것이지
    **표기가 읽히는지**를 잰 것이 아니다(1.1 '단어 언급 단언 금지'의 변종).
    표기를 빼자는 것이 아니라 표기가 **작동하게** 하자는 것이다.

    적용:
      - 화면: 기동 헤더 1회 + 각 블록 헤더 + 종료 푸터. 반복 줄에는 없음
      - 자료구조(이벤트·상태 페이로드): 배너 유지 — 기계가 읽는 것이라 노이즈 무관
      - BLE 광고명: 유지 — 스캐너에선 한 번만 보이므로 맥락이 다르다
    """
    return f"[{SIMULATOR_BANNER}]"


def _run_self_demo(appliance) -> int:
    transport = LoopbackTransport(appliance)
    # 경계 1: 기동 헤더 — 배너 1회
    _emit("=" * 60)
    _emit(f"  {SIMULATOR_BANNER}")
    _emit(f"  전송: {transport.label}")
    _emit("=" * 60)
    # startup_lines()는 자체적으로 배너를 싣는다(다른 호출자를 위한 독립 API).
    # 여기서는 바로 위 헤더가 이미 경계를 표시했으므로 **인접 중복만** 걷어낸다
    # — 같은 경계에 두 번 붙는 것도 Sally 규약 위반이다.
    for line in appliance.startup_lines():
        if line.strip() != f"[{SIMULATOR_BANNER}]":
            _emit(line)

    # 경계 2: 블록 헤더 — 배너 1회. 이하 반복 줄에는 붙이지 않는다
    _emit("")
    _emit(f"--- 루프백 셀프 데모 · {SIMULATOR_BANNER} "
          f"(주입 {len(_SELF_DEMO_COMMANDS)}건) ---")
    for i, sets in enumerate(_SELF_DEMO_COMMANDS, 1):
        cmd = {"v": 1, "device_ref": appliance.device_ref, "set": sets}
        data, errs = encode_command(cmd)
        if errs:
            _emit(f"{_banner_rule_note()} 명령 {i} 인코딩 실패: {errs[0]}")
            return 1
        errs = transport.deliver(data)
        if errs:
            # 실패는 예외적 사건이라 배너를 붙인다 — 노이즈가 아니라 신호다
            _emit(f"{_banner_rule_note()} 명령 {i} 거부: {errs[0]}")
            return 1
        _emit(f"  명령 {i} 반영 ({len(data)}B)")

    # 경계 3: 블록 헤더 — 배너 1회
    _emit("")
    _emit(f"--- 상태 전이 · {SIMULATOR_BANNER} "
          f"({len(appliance.events())}건) ---")
    for ev in appliance.events():
        for ch in ev["changes"]:
            _emit("  seq=%d %s: %r -> %r"
                  % (ev["seq"], ch["capability"], ch["old"], ch["new"]))

    # 경계 4: 종료 푸터 — 배너 1회
    snap = appliance.snapshot()
    _emit("")
    _emit(f"최종 상태: {snap['state']}")
    _emit(f"[{snap['banner']}] — 이 산출물은 실가전 데이터가 아니다")
    return 0


def _run_ble(appliance) -> int:
    binding = BleServerBinding(appliance)
    for line in binding.banner_lines():
        _emit(line)
    errs = binding.start()
    if errs:
        # 조용한 루프백 대체 금지 — 사유를 말하고 정직하게 실패한다
        for e in errs:
            _emit(f"[{SIMULATOR_BANNER}] BLE 기동 실패: {e}")
        _emit(f"[{SIMULATOR_BANNER}] 루프백으로 자동 대체하지 않는다. "
              f"루프백을 쓰려면 --transport loopback 을 명시할 것.")
        return 2
    for line in appliance.startup_lines():
        _emit(line)
    _emit(f"[{SIMULATOR_BANNER}] BLE 주변장치 기동됨: {binding.advertised_name()}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="appliance_sim",
        description=f"{SIMULATOR_BANNER} — 가전 시뮬레이터 (Story 2.1)")
    p.add_argument("--transport", choices=("loopback", "ble"), default="loopback",
                   help="전송 바인딩 (기본: loopback — BLE 아님)")
    p.add_argument("--device-ref", default="dev000", help="기기 참조 토큰")
    p.add_argument("--device-type", default="air_conditioner", help="기기 종류")
    args = p.parse_args(argv)

    appliance = ApplianceState(
        device_ref=args.device_ref,
        device_type=args.device_type,
        capabilities=["power", "target_temp", "mode", "fan_speed", "child_lock"],
    )
    if not appliance.capabilities:
        _emit(f"[{SIMULATOR_BANNER}] 유효한 capability가 없다 — 종료")
        return 1

    if args.transport == "ble":
        return _run_ble(appliance)
    return _run_self_demo(appliance)


if __name__ == "__main__":
    sys.exit(main())
