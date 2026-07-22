# -*- coding: utf-8 -*-
"""전송 바인딩 — 경계가 디렉터리로 보이는 곳 (Story 2.1).

BLE 라이브러리(bless 등) 의존은 `ble_bless.py` **안에서만** 허용된다.
core.py·wire.py·loopback.py는 표준 라이브러리만 쓰며,
tests/test_appliance_sim.py가 AST로 이를 감시한다(1.3 P3 반영판 검사기).

  loopback  — 참조 전송. 동작하지만 **BLE가 아니다**
  ble_bless — BLE GATT 주변장치. 이 머신에서의 동작은 **미확인**
"""
