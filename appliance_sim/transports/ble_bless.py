# -*- coding: utf-8 -*-
"""BLE GATT 주변장치 바인딩 (Story 2.1, Task 3).

**이 파일이 유일하게 BLE 라이브러리에 의존하는 곳이다** — 경계의 정의.
core.py·wire.py·loopback.py는 표준 라이브러리만 쓰며 AST 테스트가 감시한다.

⚠️ **이 환경에서 bless는 설치 자체가 불가능하다 (2026-07-22 실측).**
리뷰 중 실제로 설치를 시도해 확인한 사실:

  - `pip install bless` → **0.2.6**이 설치됨. import 시
    `ModuleNotFoundError: No module named 'bleak_winrt'` —
    0.2.6의 WinRT 백엔드는 구 bleak(<0.22)의 `bleak_winrt` 모듈을 요구하는데
    최신 bleak(3.x)는 그 모듈을 제공하지 않는다(`winrt-*` 네임스페이스로 이전).
  - `pip install bless==0.3.0` → **ResolutionImpossible**. 0.3.0의 메타데이터가
    자기모순이다 (Python 3.12 + Windows):
        Requires-Dist: bleak>=1.1.1                        → winrt-runtime >= 3.x
        Requires-Dist: winrt-Windows.Bluetooth==2.0.0b1    → winrt-runtime == 2.0.0-beta.1
    같은 패키지가 winrt-runtime을 3.x와 2.0.0b1로 **동시에** 요구한다.
  - 결론: **상류 패키징 문제이며 이 저장소에서 해결할 수 없다.**
    설치 시도로 들어온 패키지들은 전부 제거해 환경을 원복했다.

그러므로:
  - import 실패·의존성 파손·어댑터 부재를 **사유별로 구분해** 오류 목록으로 보고한다
    (예외 금지). "미설치"와 "설치했는데 깨짐"은 사용자의 대응이 다르다
  - 실패해도 스토리는 완료다. 단 "안 떴다"와 **왜 안 떴는지**를 기록한다 —
    **뜬 척은 NFR6 위반**
  - 실동작 실증은 실기기 준비 시점(가민 연동, Epic 2 후속)에 한다. 그때
    Python 주변장치가 아니라 **가민 워치가 중앙 역할**을 하므로 이 경로 자체가
    필요 없을 가능성이 크다 — 재평가 대상
[Source: https://github.com/kevincar/bless]

BLE 20B MTU 청킹·재조립은 **이 스토리 밖**(2.2). 여기서는 완성된 bytes 1개를
받아 wire/core로 넘기는 바인딩 골격까지만 담당한다.
"""
import uuid

from ..core import SIMULATOR_BANNER

__all__ = ["check_available", "BleServerBinding", "BLE_UNAVAILABLE_NOTICE",
           "NOTICE_NOT_INSTALLED", "NOTICE_BROKEN_DEPS", "NOTICE_NOT_IMPLEMENTED"]

BLE_UNAVAILABLE_NOTICE = "BLE 사용 불가"

# 사유를 구분해 보고한다 — "미설치"와 "설치했는데 의존성이 깨짐"은 사용자가
# 취할 행동이 완전히 다르다. v1은 둘을 "미설치이거나 어댑터 미지원"으로
# 뭉뚱그렸는데, 실제로 설치해 보니 그 문구가 **거짓**이 됐다(아래 실측).
NOTICE_NOT_INSTALLED = (
    f"{BLE_UNAVAILABLE_NOTICE}: bless 미설치. "
    f"단, 설치해도 현재 환경에서는 동작하지 않는다 — {__name__} 상단 주석 참조")
NOTICE_BROKEN_DEPS = (
    f"{BLE_UNAVAILABLE_NOTICE}: bless는 설치돼 있으나 backend 의존성이 "
    f"해소되지 않았다 (winrt 스택 버전 충돌 — 상류 패키징 문제)")
NOTICE_NOT_IMPLEMENTED = (
    f"{BLE_UNAVAILABLE_NOTICE}: bless 사용 가능하나 주변장치 기동은 "
    f"실기기 검증 전까지 미구현 (동작한 척 금지 — NFR6)")

# 광고·서비스 식별자. 이름에 시뮬레이터 표기가 실린다(AC3) —
# 스캐너 화면 캡처가 '실가전'으로 읽힐 여지를 남기지 않는다.
#
# ⚠️ 리뷰(2026-07-22, Paige): v1은 `a1b2c3d4-0001-4000-8000-thinqonme001`처럼
# **UUID가 아닌 문자열**이었다(t·h·i·n·q·o·m·e는 16진수가 아니고 마지막 그룹도
# 12자리가 아니다). bless에 넘기면 파싱 에러가 난다. BLE 실행이 불가능해서
# 이 상수가 한 번도 검증되지 않았고, 테스트는 "하드웨어 의존"으로 통째 면제돼
# 있었다 — 면제 범위를 너무 넓게 잡은 것이다. 형식 검증은 하드웨어가 없어도 된다.
#
# 교체 방식: uuid5(NAMESPACE_DNS, <이름>) — 결정적이라 재현 가능하고,
# 이름에 프로젝트 계보가 남는다. 값은 아래 이름에서 생성된 것이다.
_NS = uuid.NAMESPACE_DNS
SERVICE_UUID = str(uuid.uuid5(_NS, "thinq-onme.simulator.service"))
CHAR_COMMAND_UUID = str(uuid.uuid5(_NS, "thinq-onme.simulator.command"))
CHAR_STATE_UUID = str(uuid.uuid5(_NS, "thinq-onme.simulator.state"))


def check_available():
    """bless 가용성 확인. 반환 (available: bool, errors: list). **예외 금지**.

    하드웨어 없이 고정 가능한 유일한 BLE 계약이다(나머지는 하드웨어 의존이라
    단위 테스트 면제). 부재 환경에서 예외가 아니라 오류를 보고해야
    Task 5의 "조용한 루프백 대체 금지"가 성립한다.
    """
    try:
        import bless  # noqa: F401
        return True, []
    except ImportError as e:
        # 사유 구분: bless 자체가 없는가, 아니면 bless는 있는데 backend가 깨졌는가.
        # 후자는 상류 패키징 문제라 사용자가 `pip install bless`로 못 고친다.
        missing = getattr(e, "name", "") or ""
        if missing == "bless" or missing.startswith("bless."):
            return False, [f"{NOTICE_NOT_INSTALLED} ({type(e).__name__}: {missing})"]
        return False, [f"{NOTICE_BROKEN_DEPS} ({type(e).__name__}: {missing})"]
    except Exception as e:   # fail-closed
        return False, [f"{BLE_UNAVAILABLE_NOTICE}: 예상 밖 오류({type(e).__name__})"]


class BleServerBinding:
    """GATT 주변장치 바인딩 골격.

    상태 노출(read)·명령 수신(write) 특성을 서비스 1개로 묶는다.
    실행은 bless 가용 시에만 가능하며, 불가 시 start()가 오류를 반환한다.
    """
    is_radio = True
    label = "BLE GATT 주변장치 — 이 머신에서 동작 미확인"

    def __init__(self, appliance):
        self.appliance = appliance
        self._server = None

    def advertised_name(self) -> str:
        return self.appliance.advertised_name()

    def banner_lines(self) -> list:
        return [f"[{SIMULATOR_BANNER}] 전송: {self.label}",
                f"광고명: {self.advertised_name()}"]

    def start(self) -> list:
        """서버 기동 시도. 오류 목록 반환(빈 리스트 = 기동됨). 예외 금지.

        현재는 가용성 확인까지만 수행하고, 실제 기동은 하드웨어가 확인된
        시점에 완성한다 — "곧 되는 것처럼" 보이는 코드를 쓰지 않는다(NFR6).
        """
        available, errs = check_available()
        if not available:
            return errs
        return [NOTICE_NOT_IMPLEMENTED]

    def on_write(self, data) -> list:
        """명령 특성 write 콜백. 완성된 bytes 1개를 wire/core로 넘긴다.
        청킹·재조립은 2.2의 일이다."""
        try:
            from ..wire import decode_command
            cmd, errs = decode_command(data)
            if errs:
                return errs
            applied, errs = self.appliance.apply_command(cmd)
            if errs:
                return errs
            return [] if applied else ["명령이 반영되지 않음"]
        except Exception as e:   # fail-closed
            return [f"write 처리 내부 오류({type(e).__name__}) — 거부"]
