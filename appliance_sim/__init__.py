# -*- coding: utf-8 -*-
"""appliance_sim — 가전 시뮬레이터 (Epic 2, Story 2.1).

⚠️ **시뮬레이터 — 실가전 아님.** 이 패키지의 모든 산출물은 실가전 데이터로
인용될 수 없다(NFR6). 배너는 모든 출력 경로에 실린다.

구조:
  core.py                  — 가전 상태 기계 (전송 무관, 표준 라이브러리만)
  wire.py                  — 명령 인코딩/디코딩 (JSON UTF-8 compact)
  transports/loopback.py   — 참조 전송 (BLE 아님, 테스트·리허설용)
  transports/ble_bless.py  — BLE GATT 주변장치 바인딩 (bless 의존은 여기만)

home_profile 패키지는 **수정하지 않는다** — 시뮬레이터는 프로필의 소비자이지
소유자가 아니다. 분석 파이프라인(dx_pipeline*)과는 계보가 무관하며 import하지 않는다.
"""
from .core import (
    KNOWN_CAPABILITIES,
    KNOWN_DEVICE_TYPES,
    SIMULATOR_BANNER,
    ApplianceState,
)
from .wire import (
    COMMAND_VERSION,
    MAX_COMMAND_BYTES,
    decode_command,
    encode_command,
)

__all__ = [
    "COMMAND_VERSION",
    "KNOWN_CAPABILITIES",
    "KNOWN_DEVICE_TYPES",
    "MAX_COMMAND_BYTES",
    "SIMULATOR_BANNER",
    "ApplianceState",
    "decode_command",
    "encode_command",
]
