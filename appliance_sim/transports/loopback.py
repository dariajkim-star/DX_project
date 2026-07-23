# -*- coding: utf-8 -*-
"""루프백 전송 — 참조 구현 (Story 2.1, Task 3).

**BLE가 아니다.** 함수 호출로 bytes를 상태 기계에 전달하는 참조 전송이며,
테스트·CI·BLE 불가 환경 리허설의 유일한 경로다. 1.3의 MemoryCarrier와 같은
지위: "전송 바인딩의 모양이 실재한다"는 증거이되 무전이 아니다.

표준 라이브러리만 사용한다 — AST 경계 테스트가 감시한다.
"""
import json

from ..core import SIMULATOR_BANNER
from ..wire import decode_command

__all__ = ["LoopbackTransport"]


class LoopbackTransport:
    """bytes를 받아 상태 기계에 전달. 예외 금지 계약 상속."""
    is_radio = False
    label = "루프백 — BLE 아님"

    def __init__(self, appliance):
        self.appliance = appliance

    def deliver(self, data) -> list:
        """명령 bytes(완성본) 전달. 오류 목록 반환(빈 리스트 = 반영됨).

        2.1 계약 — **삭제하지 않는다.** 청크를 못 받는 구형 전송의 폴백 경로이며
        `test_carrier_neutrality`·`test_appliance_sim`가 이를 지킨다."""
        try:
            cmd, errs = decode_command(data)
            if errs:
                return errs
            applied, errs = self.appliance.apply_command(cmd)
            if errs:
                return errs
            return [] if applied else ["명령이 반영되지 않음"]
        except Exception as e:   # fail-closed
            return [f"전달 내부 오류({type(e).__name__}) — 거부"]

    def deliver_chunks(self, chunks) -> list:
        """청크 목록을 받아 **수신 측에서** 재조립해 전달 (Story 2.3, R5 해소).

        v1(2.2)은 송신 측 `execute_routine`이 쪼갠 것을 그 자리에서 다시 붙여
        `deliver(bytes)`로 넘겼다 — 무선 구간이 시뮬레이션되지 않았다. 이제
        재조립이 여기서 일어난다. 이것이 실기기의 실제 구조다: 워치가 쪼개
        보내고 수신 측(가전/펌웨어)이 붙인다.

        적대적 청크(총개수 위조·결번·중복)를 받는 것도 이제 수신 측이며,
        `reassemble()`이 이미 그것을 예외 없이 거부한다."""
        try:
            from home_profile.routine import reassemble
            data, errs = reassemble(chunks)
            if errs:
                return errs
            return self.deliver(data)
        except Exception as e:   # fail-closed
            return [f"청크 전달 내부 오류({type(e).__name__}) — 거부"]

    def read_state(self):
        """상태 조회 페이로드(bytes). 반환 (bytes | None, errors).
        배너 상시 동봉 — snapshot()이 이미 싣는다(AC3)."""
        try:
            snap = self.appliance.snapshot()
            data = json.dumps(snap, ensure_ascii=False,
                              separators=(",", ":")).encode("utf-8")
            return data, []
        except Exception as e:   # fail-closed
            return None, [f"상태 직렬화 실패({type(e).__name__}) — 거부"]

    def banner_lines(self) -> list:
        return [f"[{SIMULATOR_BANNER}] 전송: {self.label}"]
