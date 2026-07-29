# -*- coding: utf-8 -*-
"""이사 매핑 데모 — "이사했는데 집이 따라왔다" (Story 3.2, FR5).

    python demo_relocate.py

Epic 3의 마지막 장면. 3.1(재설치 복원)과 한 쌍으로 P-2를 반박한다:
3.1은 "같은 집, 폰만 초기화", 3.2는 "다른 집, 다른 기기". 옛 집에서 길들인
설정을 새 집의 기기들에 얹되, **안 맞는 건 버리지 않고 보류**한다.

⚠️ **매칭은 처방(설계 결정)이다.** VOC(P-2)가 "이사하면 다 없어짐"이라는 문제를
줬고, "device_type 매칭 + capability 교집합"은 우리의 선택이다.

⚠️ **H2는 미검증 가설이다.** "전세 거주자가 온바디를 더 원한다"는 다리아의
가설이고 설문으로만 검증된다(docs/SURVEY_PLAN.md). 페르소나에 인구통계를
붙이지 않는다(2.4 날조 기각 계보).

⚠️ **`home_profile/`을 수정하지 않는다.** 새 집 기기는 여기서 조립한다.
"""
import argparse
import sys

import demo_ui
from appliance_sim.core import SIMULATOR_BANNER
from home_profile import map_to_new_home
from home_profile.schema import new_profile, validate_profile

# H2 가설 라벨 — 발표 자료·화면에서 같은 문구를 쓴다.
H2_LABEL = "설문 검증 대기 가설(H2: 전세·이사예정 → 온바디 수용도↑, 미검증)"


_emit = demo_ui.emit


def _old_home():
    """옛 집 프로필 — 에어컨·청소기·조명 + 야간 루틴 하나."""
    p = new_profile()
    p["devices"] = [
        {"device_ref": "old_ac", "device_type": "air_conditioner",
         "capabilities": ["power", "target_temp", "fan_speed"]},
        {"device_ref": "old_cleaner", "device_type": "robot_cleaner",
         "capabilities": ["power"]},
        {"device_ref": "old_light", "device_type": "light",
         "capabilities": ["power"]},
    ]
    p["settings"] = {
        "old_ac": {"power": True, "target_temp": 24, "fan_speed": "low"},
        "old_cleaner": {"power": False},
        "old_light": {"power": True},
    }
    p["routines"] = [{
        "trigger": {"type": "time", "params": {"at": "22:30"}},
        "actions": [
            {"device_ref": "old_ac", "setting_key": "power", "value": True},
            {"device_ref": "old_light", "setting_key": "power", "value": False},
        ],
    }]
    return p


def _new_home_devices():
    """이사한 새 집 — 에어컨 있음(단 fan_speed 미지원), 청소기 없음,
    조명 있음, 스타일러 새로 생김. 일부러 옛 집과 어긋나게 조립한다."""
    return [
        {"device_ref": "new_ac", "device_type": "air_conditioner",
         "capabilities": ["power", "target_temp"]},          # fan_speed 없음
        {"device_ref": "new_light", "device_type": "light",
         "capabilities": ["power"]},
        {"device_ref": "new_styler", "device_type": "styler",
         "capabilities": ["power"]},                          # 옛 집에 없던 기기
    ]


def main(argv=None) -> int:
    argparse.ArgumentParser(
        prog="demo_relocate",
        description=f"{SIMULATOR_BANNER} — 이사 매핑 (Story 3.2)").parse_args(argv)

    old = _old_home()
    new_devices = _new_home_devices()

    # 경계 1: 기동 헤더 — 배너 1회
    demo_ui.title_block(
        SIMULATOR_BANNER,
        "이사 매핑 — P-2 반박(다른 집·다른 기기): 길들인 집이 따라온다")

    if validate_profile(old):
        _emit(f"[{SIMULATOR_BANNER}] 옛 프로필 조립 오류")
        return 1

    demo_ui.scene_header("옛 집", SIMULATOR_BANNER)
    for d in old["devices"]:
        keys = ", ".join(old["settings"].get(d["device_ref"], {}))
        _emit(f"  {d['device_type']}: 설정[{keys}]")
    _emit(f"  루틴 {len(old['routines'])}개")

    demo_ui.scene_header("이사한 새 집", SIMULATOR_BANNER)
    for d in new_devices:
        _emit(f"  {d['device_type']}: capability[{', '.join(d['capabilities'])}]")

    result, report = map_to_new_home(old, new_devices)
    if result is None:
        _emit(f"[{SIMULATOR_BANNER}] 매핑 실패: {report['errors'][0]}")
        return 1

    # 경계 2: 이전 결과 — 배너 1회
    demo_ui.scene_header("이전됨", SIMULATOR_BANNER)
    for old_ref, new_ref in report["transferred"]["devices"]:
        demo_ui.transition_row(f"{old_ref} -> {new_ref}", "ok", job="설정 이전")
    _emit(f"  설정 키 {report['transferred']['setting_keys']}개 · "
          f"루틴 {len(report['transferred']['routines'])}개 이전")

    # 경계 3: 보류 결과 — 배너 1회. 조용한 누락 금지가 이 장면의 정직성.
    # held_summary: 이전 n + 보류 m = 옛 전체 N 항등식 (전부 실측 — 값 조작 금지)
    demo_ui.scene_header("보류(손실 아님)", SIMULATOR_BANNER)
    total_old = (len(old["devices"])
                 + sum(len(kv) for kv in old["settings"].values())
                 + len(old["routines"]))
    transferred_n = (len(report["transferred"]["devices"])
                     + report["transferred"]["setting_keys"]
                     + len(report["transferred"]["routines"]))
    _KIND_LABEL = {
        "device": lambda h: f"기기 {h['device_type']}",
        "setting": lambda h: f"설정 {h['setting_key']}",
        "routine": lambda h: f"루틴 #{h['routine_index']}",
    }
    # 미지의 kind는 크래시 대신 실측 그대로 라벨 — 표시 계층이 데모를 죽이면 안 된다
    held_rows = [(_KIND_LABEL.get(h["kind"], lambda h, _k=h["kind"]: f"{_k}(미지 종류)")(h),
                  h["reason"]) for h in report["held"]]
    if not held_rows:
        _emit("  보류 없음 — 전부 이전됨")
    demo_ui.held_summary(transferred_n, held_rows, total_old)
    _emit("  조용히 버리지 않는다 — 보류에는 사유가 붙는다")
    if report["unmatched_new"]:
        _emit(f"  옛 기기와 매칭 안 된 새 기기: {', '.join(report['unmatched_new'])}")

    # 경계 4: 종료 푸터 — 배너 1회
    _emit()
    _emit("이사해도 길들인 집이 따라온다 — 안 맞는 건 버리지 않고 보류 (FR5)")
    demo_ui.honesty_footer([
        f"페르소나: 전세 거주 Night Keeper — {H2_LABEL}",
        f"[{SIMULATOR_BANNER}] 매핑 시뮬레이션 — 실기기 아님",
    ])
    return 0


if __name__ == "__main__":
    sys.exit(main())
