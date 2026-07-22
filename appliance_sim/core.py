# -*- coding: utf-8 -*-
"""가전 상태 기계 — 전송 무관 코어 (Story 2.1).

설계 근거: docs/planning-artifacts/epics.md#Story 2.1 (FR8, NFR6)
       docs/implementation-artifacts/2-1-appliance-simulator-ble-peripheral.md

이 모듈이 답하는 질문: **"명령을 받으면 상태가 바뀌고 그게 보이는가"**(AC1·AC2).
BLE는 전송 바인딩 1개일 뿐이고 이 파일은 전파를 모른다 — Epic 1의 캐리어 경계와
같은 원리다. 전송 라이브러리 import는 tests/test_appliance_sim.py가 AST로 감시한다.

Epic 1 계승 계약:
  1. **예외 금지** — apply_command는 어떤 입력에도 예외를 던지지 않는다.
     크래시는 곧 검사 우회다(1.1 리뷰 F3).
  2. **와이어 불신** — BLE write로 들어오는 명령은 적대적 입력이다.
     화이트리스트(capability·타입·범위) 검증 후에만 반영.
  3. **원자성** — 한 항목이라도 거부되면 배치 전체 미반영(1.3 P1 계보).
  4. **오류에 값 금지** — 거부 메시지는 capability 이름·타입명까지만.
     수신 값 원문은 로그로 새면 안 된다(1.1 PII 누출·1.3 P2 계승).

정직 표기(NFR6): SIMULATOR_BANNER가 모든 출력 경로(기동 로그·이벤트·상태 응답·
BLE 광고명)에 실린다. 이 산출물이 실가전으로 인용되는 순간 프로젝트의 신뢰
서사가 무너진다 — 배너는 장식이 아니라 계보다.
"""
import re
import sys
import time

__all__ = [
    "ApplianceState",
    "SIMULATOR_BANNER",
    "KNOWN_CAPABILITIES",
    "KNOWN_DEVICE_TYPES",
    "RangeSpec",
    "console_safe",
]

SIMULATOR_BANNER = "시뮬레이터 — 실가전 아님"

# ---------- 어휘 (함정 3: 발명 금지) ----------
# home_profile.storage의 어휘와 **동기**여야 한다 — 프로필이 보낼 수 없는 명령을
# 받는 가전은 데모에서 거짓이 된다. storage._CAPABILITIES는 비공개 심볼이라
# 제품 코드에서 import하지 않고 여기 명시 선언하며, 동기 여부는 테스트가 감시한다
# (test_capability_vocabulary_is_in_sync_with_storage).
KNOWN_CAPABILITIES = (
    "power", "target_temp", "fan_speed", "mode", "timer_min",
    "child_lock", "eco_mode", "humidity", "filter_state", "schedule",
)
KNOWN_DEVICE_TYPES = (
    "air_conditioner", "washer", "dryer", "refrigerator", "air_purifier",
    "light", "styler", "dishwasher", "robot_cleaner", "oven",
)

# 값 도메인 — storage._sample_value가 만드는 값의 도메인을 **참고**하되
# 복사가 아니라 판단이다. 범위는 가전 상식선의 보수값이며 근거 문서는 없다
# (설계 판단 — 실기기·실가전 연동 시 교체 대상).
BOOL_CAPABILITIES = frozenset({"power", "child_lock", "eco_mode"})
ENUM_CAPABILITIES = {
    "fan_speed": ("low", "mid", "high"),
    "mode": ("cool", "heat", "dry", "auto"),
    "filter_state": ("on", "off", "standby"),
    "schedule": ("on", "off", "standby"),
}
class RangeSpec:
    """정수 범위 + **그 범위의 출처**.

    리뷰(2026-07-22, Mary): v1은 `{"target_temp": (16, 30)}`처럼 숫자만 있었다.
    주석에 "근거 없음"이라고 적는 것으로는 부족하다 — 값 자체가 판정을 하고
    있는데 출처가 값과 함께 다니지 않으면 그건 **결정된 척**이다.
    1.3에서 어댑터 한계값에 `CapabilityValue(value, source)`로 출처를 강제해놓고
    여기만 안 붙인 것은 같은 병을 한쪽만 고친 것이다(Winston 지적).

    Mary의 추가 경고: `target_temp` 하한 16은 실제 LG 에어컨 하한(18로 알려짐)
    보다 낮아, **실가전이 거부할 명령을 시뮬레이터가 승인**할 수 있다. 배너는
    "실측으로 인용하지 말라"는 표기이지 "틀려도 된다"는 면허가 아니다.
    → 현재는 넓게 잡아 **거부를 최소화**하는 쪽을 택하고(검증 책임을 실가전에
      넘김), 좁히는 것은 실가전 스펙 확인 이후로 미룬다. 그 판단도 source에 적는다.
    """
    __slots__ = ("lo", "hi", "source")

    def __init__(self, lo, hi, source):
        self.lo = lo
        self.hi = hi
        self.source = source

    def __repr__(self):
        return f"RangeSpec({self.lo}, {self.hi}, {self.source!r})"


_UNVERIFIED = "미확인(설계 판단 — 실가전 스펙 확인 전, 넓게 잡아 거부 최소화)"

INT_CAPABILITIES = {
    # 물리적으로 불가능한 값만 막는다. 기기별 실제 하한(예: LG 에어컨 18도)은
    # 여기서 판정하지 않는다 — 시뮬레이터가 실가전보다 엄격하면 프로필이
    # 이식 불가가 되고, 그 검증 책임은 실가전 어댑터의 것이다.
    "target_temp": RangeSpec(0, 40, _UNVERIFIED),
    "humidity": RangeSpec(0, 100, "물리 정의(상대습도 백분율)"),
    "timer_min": RangeSpec(0, 1440, "물리 정의(24시간 = 1,440분)"),
}

# 안전 표시 정규식 — 스키마의 device_ref 토큰 형식과 동일
# (^[a-z0-9][a-z0-9_-]{0,31}$, PROFILE_SCHEMA §3). 이 형식을 통과한 문자열만
# 오류 문구에 원문으로 실린다. storage._VERSION_SHOW_RE와 같은 방어 계보다:
# 검증을 안 거친 와이어 문자열은 PII 운반체일 수 있고, 오류 문구는 PII 스캔을
# 한 번도 거치지 않고 로그로 나간다(1.2 2차 리뷰 Vex F4).
_SAFE_SHOW_RE = re.compile(r"[a-z0-9][a-z0-9_-]{0,31}")


def _show(name) -> str:
    """오류 문구용 표시 — 1.3 P2 + 1.2 Vex F4 계보.

    안전 형식(소문자 토큰)만 원문 표시. 그 외 문자열은 길이만 말한다 —
    이메일·한글·긴 문자열이 그대로 로그로 나가는 경로를 막는다.
    """
    if isinstance(name, str):
        if _SAFE_SHOW_RE.fullmatch(name):
            return repr(name)
        return f"<str len={len(name)}>"
    return f"<{type(name).__name__}>"


def console_safe(text: str) -> str:
    """콘솔 인코딩으로 표현 불가한 문자를 대체 (DEV_PLAN Windows cp949 규약).

    배너의 em dash(—)는 cp949로 인코딩되지 않는다. 배너 문자열 자체는 AC3의
    문면이라 바꾸지 않고, **출력 경로에서** 안전화한다 — 표기가 인코딩 때문에
    통째로 사라지는 것이 최악이기 때문이다(표기 누락 = NFR6 위반).
    """
    enc = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        text.encode(enc)
        return text
    except (UnicodeEncodeError, LookupError):
        return text.encode(enc, errors="replace").decode(enc, errors="replace")


class ApplianceState:
    """가전 1대의 상태 + 변경 이벤트 로그.

    멀티 기기 오케스트레이션·페어링·인증은 이 스토리 밖이다(2.2~2.4, Epic 4).
    """

    def __init__(self, device_ref, device_type, capabilities):
        self.device_ref = str(device_ref)
        self.device_type = str(device_type)
        # 선언한 capability만 이 기기가 알아듣는다. 미지 토큰은 조용히 버리지 않고
        # 생성 시점에 걸러 상태에서 제외한다(그 뒤 명령은 '이 기기에 없음'으로 거부).
        self.capabilities = tuple(
            c for c in capabilities if c in KNOWN_CAPABILITIES)
        self._state = {c: None for c in self.capabilities}
        self._events = []
        self._seq = 0

    # ---------- 조회 ----------
    def snapshot(self) -> dict:
        """현재 상태. 배너 상시 동봉(AC3)."""
        return {
            "banner": SIMULATOR_BANNER,
            "device_ref": self.device_ref,
            "device_type": self.device_type,
            "state": dict(self._state),
        }

    def events(self) -> list:
        """변경 이벤트 목록 — **복사본**을 준다(호출자가 내부를 못 지우게).

        AC2의 '관찰 가능'은 print가 아니라 조회 가능한 자료다. print만 있으면
        테스트가 캡처 문자열 grep으로 전락한다(1.1 '단어 언급 단언 금지' 교훈).
        """
        return [dict(e, changes=[dict(c) for c in e["changes"]])
                for e in self._events]

    def startup_lines(self) -> list:
        """기동 로그 줄들. cp949 콘솔 안전 — 이모지 금지(DEV_PLAN Windows 규약)."""
        return [
            f"[{SIMULATOR_BANNER}]",
            f"기기: {self.device_ref} ({self.device_type})",
            f"capability: {', '.join(self.capabilities) or '(없음)'}",
        ]

    def advertised_name(self) -> str:
        """BLE 광고명 — 스캐너 화면 캡처가 '실가전'으로 읽히지 않게."""
        return f"SIM-NOT-REAL-{self.device_ref}"

    # ---------- 명령 반영 ----------
    def apply_command(self, cmd):
        """명령 반영. 반환 (applied: bool, errors: list[str]). **예외 금지**.

        원자적이다: 한 항목이라도 거부되면 아무것도 반영하지 않는다.
        """
        try:
            if not isinstance(cmd, dict):
                return False, [f"명령은 객체여야 함({type(cmd).__name__})"]
            ref = cmd.get("device_ref")
            if not isinstance(ref, str) or ref != self.device_ref:
                # 값 원문을 되뱉지 않는다 — ref는 신뢰 불가 입력이다
                return False, [f"device_ref 불일치({_show(ref)})"]
            sets = cmd.get("set")
            if not isinstance(sets, dict):
                return False, [f"set은 객체여야 함({type(sets).__name__})"]
            if not sets:
                return False, ["set이 비어 있음 — 반영할 것이 없다"]

            errs = []
            staged = {}
            for cap, value in sets.items():
                err = self._validate(cap, value)
                if err:
                    errs.append(err)
                else:
                    staged[cap] = value
            if errs:
                return False, errs          # 원자성: 아무것도 반영하지 않는다

            changes = [{"capability": c, "old": self._state[c], "new": v}
                       for c, v in staged.items() if self._state[c] != v]
            if not changes:
                return True, []             # 유효하지만 변화 없음 — 이벤트도 없음
            self._state.update(staged)
            self._seq += 1
            self._events.append({
                "banner": SIMULATOR_BANNER,
                "seq": self._seq,
                "at": time.time(),
                "device_ref": self.device_ref,
                "changes": changes,
            })
            return True, []
        except Exception as e:   # fail-closed
            return False, [f"명령 처리 내부 오류({type(e).__name__}) — 거부"]

    def _validate(self, cap, value):
        """단일 항목 검증. 통과면 None, 아니면 오류 문자열(값 원문 미포함)."""
        if not isinstance(cap, str) or cap not in KNOWN_CAPABILITIES:
            return f"미지 capability {_show(cap)}"
        if cap not in self._state:
            return f"이 기기에 없는 capability {_show(cap)}"
        if cap in BOOL_CAPABILITIES:
            if not isinstance(value, bool):
                return f"{cap}: bool이어야 함({type(value).__name__})"
            return None
        if cap in ENUM_CAPABILITIES:
            if not isinstance(value, str):
                return f"{cap}: 문자열이어야 함({type(value).__name__})"
            if value not in ENUM_CAPABILITIES[cap]:
                return (f"{cap}: 허용값 아님 "
                        f"(허용 {len(ENUM_CAPABILITIES[cap])}종)")
            return None
        if cap in INT_CAPABILITIES:
            # bool은 int의 서브클래스다 — 명시적으로 배제하지 않으면
            # {"target_temp": True}가 1로 통과한다
            if isinstance(value, bool) or not isinstance(value, int):
                return f"{cap}: 정수여야 함({type(value).__name__})"
            spec = INT_CAPABILITIES[cap]
            if not (spec.lo <= value <= spec.hi):
                return f"{cap}: 범위 밖 (허용 {spec.lo}~{spec.hi})"
            return None
        return f"검증 규칙 없는 capability {_show(cap)} — 거부"
