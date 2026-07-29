# -*- coding: utf-8 -*-
"""Quietly Home 데모 — "설정은 한 번, 집은 계속 바뀌어도" (T2 Home Starter Couple).

    python demo_quietly.py

부부 두 사람, 두 워치, 두 프로필. 각자 '조용한 귀가'를 **한 번** 새겨두면,
이사를 해도(다른 집·다른 기기) 그 설정이 각자의 손목을 따라온다 — 재설정 0회.
이사가 이탈(churn)의 순간이 되지 않는 것, 그게 이 데모의 주장이다(P-2·H2·H3).

⚠️ **원터치다 — 감지가 아니다.** 늦게 귀가한 사람이 손목에서 스스로 누른다.
수면 감지·위치 추적·배우자 상태 공유는 없다(전부 서버·행태 수집을 요구한다).

⚠️ **멀티 프로필 충돌은 이 데모의 범위 밖이다.** 각자 자기 프로필을 자기
워치에서 실행하므로 충돌이 없다. "같은 기기를 두고 선호가 다를 때 누가
이기는가"는 열린 질문(DECISIONS.md 2026-07-28)으로 남는다.

⚠️ **Home Starter Couple은 가설이다** — 설문 검증 대기(H3, PERSONA_LADDER T2).
⚠️ **매칭은 처방(설계 결정)이다** — VOC가 알고리즘을 주지 않았다.
⚠️ **`home_profile/`을 수정하지 않는다.** 조립만 한다.
"""
import argparse
import sys

import demo_ui
from appliance_sim.core import SIMULATOR_BANNER, ApplianceState
from appliance_sim.transports.loopback import LoopbackTransport
from home_profile import MemoryCarrier, execute_routine, map_to_new_home, serialize
from home_profile.schema import new_profile, validate_profile

RECORD = "profile"
QUIET_ROUTINE_INDEX = 0

# T2 가설 라벨 — 발표 자료·화면에서 같은 문구를 쓴다 (PERSONA_LADDER §4).
H3_LABEL = "Home Starter Couple — 가설(H3), 설문 검증 대기(문4·7-1·7-2)"

# 옛 집 기기 — 부부가 함께 쓰는 물리 기기 (시뮬레이터).
_OLD_DEVICES = [
    ("old_ac", "air_conditioner", ["power", "target_temp", "fan_speed"]),
    ("old_cleaner", "robot_cleaner", ["power"]),
    ("old_light", "light", ["power"]),
    ("old_washer", "washer", ["power", "schedule"]),
]

# 새 집 기기 — 일부러 어긋나게: fan_speed 미지원, 청소기·세탁기 없음, 스타일러 신규.
_NEW_DEVICES = [
    {"device_ref": "new_ac", "device_type": "air_conditioner",
     "capabilities": ["power", "target_temp"]},
    {"device_ref": "new_light", "device_type": "light",
     "capabilities": ["power"]},
    {"device_ref": "new_styler", "device_type": "styler",
     "capabilities": ["power"]},
]

_emit = demo_ui.emit


def build_couple_profile(temp: int) -> dict:
    """한 사람의 프로필 — '조용한 귀가' 루틴 하나, 선호 온도만 다르다.

    루틴 액션은 새 집에도 존재하는 어휘(light.power, ac.target_temp)만 쓴다 —
    루틴 자체가 이사를 건너 생존하는 것이 이 데모의 핵심 실측이기 때문.
    fan_speed·washer 설정은 남겨서 **보류가 사유와 함께 계상되는 것**도 보인다.
    """
    p = new_profile()
    p["devices"] = [
        {"device_ref": ref, "device_type": dtype, "capabilities": list(caps)}
        for ref, dtype, caps in _OLD_DEVICES
    ]
    p["settings"] = {
        "old_ac": {"power": True, "target_temp": temp, "fan_speed": "low"},
        "old_cleaner": {"power": False},
        "old_light": {"power": True},
        "old_washer": {"schedule": "standby"},
    }
    p["routines"] = [{
        # 원터치 트리거 — 시간·감지가 아니라 사람이 누른다.
        "trigger": {"type": "touch", "params": {}},
        "actions": [
            {"device_ref": "old_light", "setting_key": "power", "value": False},
            {"device_ref": "old_ac", "setting_key": "target_temp", "value": temp},
        ],
    }]
    return p


def _persist(profile, label):
    """프로필 → 각자의 워치(캐리어). 반환 carrier | None."""
    data, errs = serialize(profile)
    if errs:
        _emit(f"[{SIMULATOR_BANNER}] {label} 프로필 직렬화 실패: {errs[0]}")
        return None
    carrier = MemoryCarrier()
    if carrier.put_records({RECORD: data}):
        _emit(f"[{SIMULATOR_BANNER}] {label} 캐리어 저장 실패")
        return None
    return carrier


def _one_touch(carrier, appliances, label, expected_temp) -> bool:
    """원터치 실행 + 실측 전이 표기. 반환 성공 여부."""
    transports = {ref: LoopbackTransport(a) for ref, a in appliances.items()}
    result, errs = execute_routine(carrier, transports, RECORD,
                                   QUIET_ROUTINE_INDEX)
    if errs:
        _emit(f"[{SIMULATOR_BANNER}] {label} 실행 실패: {errs[0]}")
        return False
    # 판정은 실측: 실행 후 스냅샷이 루틴 의도값과 일치하는지 대조 (교훈 1)
    for ref, a in sorted(appliances.items()):
        snap = a.snapshot()["state"]
        if a.device_type == "light":
            demo_ui.transition_row(
                "조명 끔", "ok" if snap.get("power") is False else "blocked",
                code_kv=f"{ref} power: {snap.get('power')}",
                job="자는 사람의 방은 어둡게 유지")
        if a.device_type == "air_conditioner":
            # 판정은 실측 — 실행 후 온도가 이 사람의 선호값과 일치할 때만 ✓ (교훈 1)
            demo_ui.transition_row(
                "에어컨 내 선호 온도로",
                "ok" if snap.get("target_temp") == expected_temp else "blocked",
                code_kv=f"{ref} target_temp: {snap.get('target_temp')}",
                job="내 값 — 배우자 값이 아니라")
    return True


def main(argv=None) -> int:
    argparse.ArgumentParser(
        prog="demo_quietly",
        description=f"{SIMULATOR_BANNER} — Quietly Home (T2 실물)").parse_args(argv)

    # 경계 1: 기동 헤더 — 배너 1회
    demo_ui.title_block(
        SIMULATOR_BANNER,
        "Quietly Home — 설정은 한 번, 집은 계속 바뀌어도")
    _emit(f"  {H3_LABEL}")
    _emit("  원터치 실행 — 수면 감지·위치·배우자 상태 공유 없음 (전부 서버를 요구한다)")

    # 장면 1: 옛 집 — 두 프로필, 한 번 새김
    asleep = build_couple_profile(temp=24)     # 먼저 잔 사람의 선호
    returner = build_couple_profile(temp=26)   # 늦게 귀가한 사람의 선호
    for p, who in ((asleep, "먼저 잔 사람"), (returner, "늦게 귀가한 사람")):
        if validate_profile(p):
            _emit(f"[{SIMULATOR_BANNER}] {who} 프로필 조립 오류")
            return 1
    demo_ui.scene_header("장면 1: 옛 집 — 한 번 새김", SIMULATOR_BANNER)
    c_asleep = _persist(asleep, "먼저 잔 사람")
    c_return = _persist(returner, "늦게 귀가한 사람")
    if c_asleep is None or c_return is None:
        return 1
    _emit(f"  먼저 잔 사람 워치: '조용한 귀가' 새김 (선호 24도) · "
          f"{len(serialize(asleep)[0]):,}B")
    _emit(f"  늦게 귀가한 사람 워치: 같은 루틴, 다른 값 (선호 26도) · "
          f"{len(serialize(returner)[0]):,}B")

    # 장면 2: 옛 집 — 늦게 귀가한 사람의 원터치
    demo_ui.scene_header("장면 2: 옛 집 — 늦게 귀가, 현관 앞 원터치", SIMULATOR_BANNER)
    old_appliances = {ref: ApplianceState(ref, dtype, caps)
                      for ref, dtype, caps in _OLD_DEVICES}
    if not _one_touch(c_return, old_appliances, "옛 집", expected_temp=26):
        return 1

    # 장면 3: 이사 — 각자의 프로필이 각자 새 집에 매핑된다
    demo_ui.scene_header("장면 3: 이사 — 다른 집, 다른 기기", SIMULATOR_BANNER)
    _emit("  매칭(device_type + capability 교집합)은 처방 — VOC가 준 근거 아님")
    mapped = {}
    for profile, who in ((asleep, "먼저 잔 사람"), (returner, "늦게 귀가한 사람")):
        result, report = map_to_new_home(profile, _NEW_DEVICES)
        if result is None:
            _emit(f"[{SIMULATOR_BANNER}] {who} 매핑 실패: {report['errors'][0]}")
            return 1
        mapped[who] = result
        total_old = (len(profile["devices"])
                     + sum(len(v) for v in profile["settings"].values())
                     + len(profile["routines"]))
        transferred_n = (len(report["transferred"]["devices"])
                         + report["transferred"]["setting_keys"]
                         + len(report["transferred"]["routines"]))
        _KIND = {
            "device": lambda h: f"기기 {h['device_type']}",
            "setting": lambda h: f"설정 {h['setting_key']}",
            "routine": lambda h: f"루틴 #{h['routine_index']}",
        }
        held_rows = [(_KIND.get(h["kind"], lambda h, _k=h["kind"]: f"{_k}(미지 종류)")(h),
                      h["reason"]) for h in report["held"]]
        _emit(f"  {who}:")
        demo_ui.held_summary(transferred_n, held_rows, total_old)

    # 장면 4: 새 집 — 재설정 0회, 같은 원터치, 각자의 값 그대로
    demo_ui.scene_header("장면 4: 새 집 — 재설정 0회, 같은 원터치", SIMULATOR_BANNER)
    c_new = _persist(mapped["늦게 귀가한 사람"], "새 집")
    if c_new is None:
        return 1
    new_appliances = {d["device_ref"]: ApplianceState(
        d["device_ref"], d["device_type"], d["capabilities"])
        for d in _NEW_DEVICES}
    if not _one_touch(c_new, new_appliances, "새 집", expected_temp=26):
        return 1
    # 배우자 값의 생존도 실측으로 — 매핑된 프로필의 설정에서 읽는다 (표시만).
    asleep_temp = None
    for _ref, kv in mapped["먼저 잔 사람"]["settings"].items():
        if "target_temp" in kv:
            asleep_temp = kv["target_temp"]
    _emit(f"  먼저 잔 사람의 프로필도 따라왔다 — 매핑된 설정의 선호 온도: "
          f"{asleep_temp}도 (각자의 값이 각자의 워치에)")

    # 경계 5: 종료 푸터 — 배너 1회
    _emit()
    _emit("설정은 한 번, 집은 계속 바뀌어도 — 이사가 이탈의 순간이 되지 않는다")
    demo_ui.honesty_footer([
        H3_LABEL,
        "매칭 알고리즘은 처방(설계 결정) — VOC 근거 아님",
        "멀티 프로필 충돌(같은 기기·다른 선호)은 다음 단계 — 여기선 각자 실행이라 충돌 없음",
        f"[{SIMULATOR_BANNER}] 참조 어댑터 기반 — 실기기(가민) 아님",
    ])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
