# -*- coding: utf-8 -*-
"""릴레이 공격 방어 — 근접 챌린지-응답 게이트 (Story 4.3, NFR1).

설계 근거: docs/planning-artifacts/epics.md#Story 4.3
       docs/implementation-artifacts/4-3-relay-defense.md
       docs/THREAT_MODEL.md

이 모듈이 답하는 질문: **"손목에 있으면 무조건 열린다를 막는가"**(NFR1).
온바디 프로필이 로컬에서 가전을 여는 구조는 근접성이 인증이 되므로, 공격자가
명령을 중계·재사용하면 원거리에서 문이 열린다. 이 게이트는 그 표면을 좁힌다.

🛡️ **막는 것 (replay/재생):** 공격자가 유효한 명령을 캡처해 **나중에** 재사용하는
   것. nonce 1회용 신선도로 거부한다.
⚠️ **못 막는 것 (실시간 relay/중계):** 공격자가 신선한 챌린지와 응답을 신선도 창
   안에서 **실시간으로** 중계하는 것. 이것은 거리 바운딩(왕복 시간 측정) 하드웨어가
   필요한데 이 시뮬레이터엔 없다. **완전 방어를 주장하지 않는다** — 잔여 한계로
   THREAT_MODEL.md에 명시(NFR1 AC2). 3.1 오프라인 한계 표기와 같은 규율.

즉 이 방어는 "손목에 있으면 열린다"를 "손목에 있고 + 신선한 챌린지에 실시간
응답해야 열린다"로 **좁힌다**. 완전 제거가 아니라 표면 축소.

계약 (전 스토리 승계):
  1. 예외 금지 — verify는 어떤 입력에도 (ok: bool, reason). fail-closed(의심 시 거부).
  2. 거부 사유에 토큰 원문·페이로드 금지(값은 신뢰 불가 입력, PII 가능).
  3. nonce 1회용 — 통과한 nonce는 소비되어 재사용 불가(재생 차단의 본질).

경계: 자족적 보안 primitive. apply_command를 수정하지 않고 앞단 게이트로 합성한다
(기존 명령 계약 보존 — 회귀 0). appliance_sim·schema·carrier를 import하지 않는다.
"""
import secrets

__all__ = ["ProximityGuard", "make_proximity_token"]

_NONCE_BYTES = 16          # 128비트 — 추측·충돌 저항


def make_proximity_token(nonce):
    """근접한 워치가 만드는 근접 토큰. 발급된 nonce에 바인딩된다.

    실기기에선 nonce를 (제때) 수신했다는 것 자체가 근접의 증거다 — 근접하지
    않으면 신선한 nonce를 신선도 창 안에 받지 못한다. 시뮬레이터에선 그 흐름만
    모델링한다(토큰 = 수신한 nonce의 응답).
    """
    return {"nonce": nonce}


class ProximityGuard:
    """가전 측 근접 게이트. 명령마다 신선한 nonce 챌린지-응답을 요구해 캡처된
    명령의 재생(replay)을 거부한다.

    ⚠️ replay는 막지만 실시간 relay는 못 막는다(모듈 docstring·THREAT_MODEL.md).
    """

    def __init__(self):
        self._current = None       # 현재 유효한(미소비) 챌린지 nonce
        self._used = set()         # 이미 소비된 nonce (재생 차단)

    def issue_challenge(self):
        """신선한 nonce 발급. 근접한 워치만 이 값을 제때 받는다.

        발급할 때마다 이전 미소비 챌린지는 무효가 된다 — 한 번에 하나의
        신선한 챌린지만 유효(옛 챌린지에 대한 응답을 뒤늦게 받지 않는다)."""
        self._current = secrets.token_hex(_NONCE_BYTES)
        return self._current

    def verify(self, token):
        """근접 토큰 검증. 반환 (ok: bool, reason: str). **예외 금지**.

        통과 조건: 토큰 nonce가 **현재 챌린지와 일치** + **미소비**.
        통과 시 nonce를 소비한다(1회용) → 같은 토큰 재생은 이후 거부.
        """
        try:
            if self._current is None:
                return False, "발급된 챌린지 없음 — 근접 증명 불가"
            if not isinstance(token, dict):
                return False, f"토큰은 객체여야 함({type(token).__name__})"
            nonce = token.get("nonce")
            if not isinstance(nonce, str):
                return False, "토큰 nonce 형식 위반"
            if nonce in self._used:
                # 재생: 이미 소비된 nonce의 토큰을 다시 냈다.
                return False, "소비된 nonce — 재생(replay) 거부"
            # 상수시간 비교: nonce 원문을 되뱉지 않고 일치만 본다.
            if not secrets.compare_digest(nonce, self._current):
                return False, "nonce 불일치 — 옛/위조 챌린지 거부"
            # 통과 — 소비 처리(1회용). 현재 챌린지를 닫는다.
            self._used.add(nonce)
            self._current = None
            return True, "근접 증명 통과"
        except Exception as e:   # fail-closed
            return False, f"근접 검증 내부 오류({type(e).__name__}) — 거부"
