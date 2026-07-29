# -*- coding: utf-8 -*-
"""릴레이 공격 방어 데모 (Story 4.3, NFR1).

    python demo_relay.py

Epic 4 위협 모델. 근접 명령의 **재생(replay)**을 챌린지-응답 신선도로 막는다.
단 **실시간 relay는 못 막는다**(거리 바운딩 필요) — 완전 방어를 주장하지 않고
잔여 한계를 화면에 함께 표기한다(AC2 정직성). 상세: docs/THREAT_MODEL.md

⚠️ 이 데모가 "완전 방어"로 읽히면 안 된다. 막는 것(replay)과 못 막는 것
(실시간 relay·물리 근접 위조)을 나란히 보인다.
"""
import argparse
import sys

import demo_ui
from appliance_sim.core import SIMULATOR_BANNER, ApplianceState
from home_profile import ProximityGuard, make_proximity_token


_emit = demo_ui.emit


def _cmd():
    return {"device_ref": "ac1", "set": {"power": True}}


def main(argv=None) -> int:
    argparse.ArgumentParser(
        prog="demo_relay",
        description=f"{SIMULATOR_BANNER} — 릴레이 방어 (Story 4.3)").parse_args(argv)

    guard = ProximityGuard()
    appliance = ApplianceState("ac1", "air_conditioner", ["power", "target_temp"])

    # 경계 1: 기동 헤더 — 배너 1회
    demo_ui.title_block(
        SIMULATOR_BANNER,
        "릴레이 방어 — \"손목에 있으면 열린다\"의 공격 표면 축소 (NFR1)")

    # 장면 1: 정상 근접 명령 — 신선한 챌린지에 응답
    demo_ui.scene_header("장면 1: 정상 근접 명령", SIMULATOR_BANNER)
    nonce = guard.issue_challenge()
    _emit("  가전: 신선한 챌린지(nonce) 발급 — 근접한 워치만 제때 받는다")
    token = make_proximity_token(nonce)
    captured = dict(token)                       # 공격자가 이 명령을 캡처한다고 가정
    ok, reason = guard.verify(token)
    demo_ui.transition_row("워치: 챌린지에 응답", "ok" if ok else "blocked",
                           code_kv=reason,
                           job=f"근접 검증 {'통과' if ok else '실패'}")
    if ok:
        applied, errs = appliance.apply_command(_cmd())
        demo_ui.transition_row(
            "명령 반영", "ok" if applied else "blocked",
            code_kv=f"power -> {appliance.snapshot()['state']['power']}",
            job="성공" if applied else "실패")

    # 장면 2: 릴레이/재생 — 캡처한 명령을 나중에 재현
    demo_ui.scene_header("장면 2: 재생(replay) 공격", SIMULATOR_BANNER)
    guard.issue_challenge()                      # 가전이 새 챌린지로 회전
    _emit("  가전: 다음 명령을 위해 챌린지 회전")
    ok, reason = guard.verify(captured)          # 공격자가 캡처본 재생
    # ✗는 증거다 — 재생 거부가 바라던 결과
    demo_ui.transition_row("공격자: 캡처한 명령 재생",
                           "blocked" if not ok else "ok",
                           code_kv=reason,
                           job=f"근접 검증 {'거부' if not ok else '통과(!)'}")
    if not ok:
        _emit("  명령 반영: 게이트에서 차단됨 — 가전 상태 불변")
    else:
        # 재생이 통과하면 방어가 뚫린 것 — 데모를 성공(rc 0)으로 끝내면 거짓 그린
        _emit("  ⚠️ 재생 공격이 통과했다 — 방어 회귀. 이 데모는 실패로 종료한다")
        return 1

    # 경계: 막는 것 / 못 막는 것 — 같은 행 수·같은 서식·같은 무게 (boundary_table)
    demo_ui.scene_header("방어 범위 (정직 표기)", SIMULATOR_BANNER)
    demo_ui.boundary_table(
        blocks=[
            "캡처 명령 재생(replay)",
            "옛/위조 nonce",
            "챌린지 재사용",
        ],
        cannot_blocks=[
            "실시간 relay(신선도 창 안 실시간 중계) — 거리 바운딩 필요",
            "물리적 근접 위조",
            "손목 탈취 즉시 사용 → 폐기는 S7(4.4 영역)",
        ])

    # 경계 4: 종료 푸터 — 배너 1회. 확정 마이크로카피(S6) 유지.
    _emit()
    _emit("\"손목에 있으면 열린다\"를 \"신선한 챌린지에 실시간 응답해야\"로 좁혔다 (NFR1)")
    _emit("완전 제거가 아니라 표면 축소 — 완전 방어를 주장하지 않는다")
    demo_ui.honesty_footer([
        "※ 완전 방어 아님 — 실시간 relay 방어는 거리 바운딩 하드웨어 필요(범위 밖)",
        "상세 위협 모델: docs/THREAT_MODEL.md",
        f"[{SIMULATOR_BANNER}] 참조 어댑터 기반 — 실기기(가민) 시연 아님",
    ])
    return 0


if __name__ == "__main__":
    sys.exit(main())
