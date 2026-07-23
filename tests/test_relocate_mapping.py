# -*- coding: utf-8 -*-
"""Story 3.2 — 이사 새 기기 집합 매핑 (FR5).

이 파일이 단언하는 것:
  1. 결정성: 같은 (old, new) → 같은 new_profile·같은 report.
  2. 매칭 이전(AC1): 같은 type 매칭 시 지원되는 설정만 새 device_ref로 이전,
     결과가 validate_profile 통과.
  3. 손실 없는 보류(AC1·AC2): type 불일치·미지원 설정·이전 불가 루틴이 각각
     사유와 함께 held에 등장. **누락 0 항등식**(old 전체 = transferred + held).
  4. 루틴 원자성: 액션 일부만 매핑 가능하면 통째로 held.
  5. 경계·예외 금지: 빈 새 집·같은 type 여러 대·garbage 입력.

구분: 3.1(device_ref 보존 복원)과 다르다 — 이사는 device_ref가 바뀐다.
"""
from home_profile import map_to_new_home
from home_profile.relocate import (
    REASON_CAPABILITY_UNSUPPORTED,
    REASON_NO_MATCHING_TYPE,
    REASON_ROUTINE_UNMAPPABLE,
)
from home_profile.schema import new_profile, validate_profile


def _dev(ref, dtype, caps):
    return {"device_ref": ref, "device_type": dtype, "capabilities": list(caps)}


def _old_home():
    """옛 집: 에어컨(설정 2)·청소기(설정 1)·루틴 1(에어컨만 건드림)."""
    p = new_profile()
    p["devices"] = [
        _dev("old_ac", "air_conditioner", ["power", "target_temp"]),
        _dev("old_cleaner", "robot_cleaner", ["power"]),
    ]
    p["settings"] = {
        "old_ac": {"power": True, "target_temp": 24},
        "old_cleaner": {"power": False},
    }
    p["routines"] = [{
        "trigger": {"type": "time", "params": {"at": "22:00"}},
        "actions": [{"device_ref": "old_ac", "setting_key": "power", "value": False}],
    }]
    assert validate_profile(p) == []
    return p


# ---------- AC1·AC2: 매칭 이전 + 유효 결과 ----------

def test_matched_device_transfers_supported_settings():
    old = _old_home()
    new_devices = [
        _dev("new_ac", "air_conditioner", ["power", "target_temp"]),
        _dev("new_cleaner", "robot_cleaner", ["power"]),
    ]
    result, report = map_to_new_home(old, new_devices)
    assert result is not None
    assert validate_profile(result) == []
    # 설정이 새 device_ref로 이전됨(정확한 값)
    assert result["settings"]["new_ac"] == {"power": True, "target_temp": 24}
    assert result["settings"]["new_cleaner"] == {"power": False}
    assert ("old_ac", "new_ac") in report["transferred"]["devices"]
    assert report["held"] == []


def test_routine_remapped_to_new_ref():
    old = _old_home()
    new_devices = [
        _dev("new_ac", "air_conditioner", ["power", "target_temp"]),
        _dev("new_cleaner", "robot_cleaner", ["power"]),
    ]
    result, report = map_to_new_home(old, new_devices)
    assert 0 in report["transferred"]["routines"]
    action = result["routines"][0]["actions"][0]
    assert action["device_ref"] == "new_ac"          # 새 ref로 재작성
    assert action["setting_key"] == "power"


# ---------- 손실 없는 보류 + 누락 0 항등식 ----------

def _identity_holds(old, report):
    held = report["held"]
    dev_ok = len(old["devices"]) == \
        len(report["transferred"]["devices"]) + \
        len([h for h in held if h["kind"] == "device"])
    n_old_keys = sum(len(v) for v in old["settings"].values())
    set_ok = n_old_keys == report["transferred"]["setting_keys"] + \
        len([h for h in held if h["kind"] == "setting"])
    rou_ok = len(old["routines"]) == \
        len(report["transferred"]["routines"]) + \
        len([h for h in held if h["kind"] == "routine"])
    return dev_ok and set_ok and rou_ok


def test_no_matching_type_device_is_held_not_dropped():
    old = _old_home()
    new_devices = [_dev("new_ac", "air_conditioner", ["power", "target_temp"])]
    result, report = map_to_new_home(old, new_devices)   # 청소기 없음
    assert result is not None
    held_devices = [h for h in report["held"] if h["kind"] == "device"]
    assert any(h["reason"] == REASON_NO_MATCHING_TYPE and
               h["device_type"] == "robot_cleaner" for h in held_devices)
    assert _identity_holds(old, report)


def test_unsupported_setting_key_is_held():
    old = _old_home()
    # 새 에어컨이 target_temp를 지원 안 함 → 그 설정만 보류
    new_devices = [
        _dev("new_ac", "air_conditioner", ["power"]),
        _dev("new_cleaner", "robot_cleaner", ["power"]),
    ]
    result, report = map_to_new_home(old, new_devices)
    assert result is not None
    assert result["settings"]["new_ac"] == {"power": True}   # target_temp 빠짐
    assert any(h["kind"] == "setting" and
               h["reason"] == REASON_CAPABILITY_UNSUPPORTED and
               h["setting_key"] == "target_temp" for h in report["held"])
    assert _identity_holds(old, report)


def test_routine_held_whole_when_any_action_unmappable():
    """루틴 원자성: 액션이 미지원 키를 참조하면 루틴 통째로 보류(부분 이전 금지)."""
    old = new_profile()
    old["devices"] = [_dev("old_ac", "air_conditioner", ["power", "target_temp"])]
    old["settings"] = {"old_ac": {"power": True, "target_temp": 24}}
    old["routines"] = [{
        "trigger": {"type": "time", "params": {"at": "07:00"}},
        "actions": [
            {"device_ref": "old_ac", "setting_key": "power", "value": True},
            {"device_ref": "old_ac", "setting_key": "target_temp", "value": 26},
        ],
    }]
    assert validate_profile(old) == []
    new_devices = [_dev("new_ac", "air_conditioner", ["power"])]   # target_temp 미지원
    result, report = map_to_new_home(old, new_devices)
    assert result is not None
    assert result["routines"] == []                  # 부분 이전 없음
    assert any(h["kind"] == "routine" and
               h["reason"] == REASON_ROUTINE_UNMAPPABLE for h in report["held"])
    assert _identity_holds(old, report)


# ---------- 결정성 ----------

def test_deterministic():
    old = _old_home()
    new_devices = [
        _dev("new_ac1", "air_conditioner", ["power", "target_temp"]),
        _dev("new_ac2", "air_conditioner", ["power", "target_temp"]),
        _dev("new_cleaner", "robot_cleaner", ["power"]),
    ]
    r1, rep1 = map_to_new_home(old, new_devices)
    r2, rep2 = map_to_new_home(old, new_devices)
    assert r1 == r2
    assert rep1 == rep2
    # 같은 type 여러 대: 첫 미사용(new_ac1)에 결정적 배정
    assert ("old_ac", "new_ac1") in rep1["transferred"]["devices"]


# ---------- 경계값 ----------

def test_empty_new_home_holds_everything():
    old = _old_home()
    result, report = map_to_new_home(old, [])
    assert result is not None
    assert result["devices"] == []
    assert report["transferred"]["devices"] == []
    assert len([h for h in report["held"] if h["kind"] == "device"]) == 2
    assert _identity_holds(old, report)


def test_empty_old_profile_transfers_nothing():
    old = new_profile()                              # 기기 0·설정 0·루틴 0
    new_devices = [_dev("new_ac", "air_conditioner", ["power"])]
    result, report = map_to_new_home(old, new_devices)
    assert result is not None
    assert report["transferred"]["devices"] == []
    assert "new_ac" in report["unmatched_new"]       # 설정 못 받은 새 기기 표기
    assert _identity_holds(old, report)


def test_unmatched_new_device_reported():
    old = _old_home()
    new_devices = [
        _dev("new_ac", "air_conditioner", ["power", "target_temp"]),
        _dev("new_cleaner", "robot_cleaner", ["power"]),
        _dev("new_styler", "styler", ["power"]),     # 옛 집에 없던 새 기기
    ]
    result, report = map_to_new_home(old, new_devices)
    assert "new_styler" in report["unmatched_new"]


# ---------- 예외 금지 / fail-closed ----------

def test_invalid_old_profile_rejected():
    result, report = map_to_new_home({"not": "a profile"}, [])
    assert result is None
    assert report["errors"]


def test_new_devices_not_list_rejected():
    result, report = map_to_new_home(_old_home(), "not a list")
    assert result is None
    assert report["errors"]


def test_never_raises_on_garbage():
    """예외 금지 계약 — 어떤 입력에도 (result|None, report) 튜플, 크래시 없음."""
    for bad_new in (None, 42, [None], [{"device_ref": 1}], [{"x": "y"}]):
        result, report = map_to_new_home(_old_home(), bad_new)
        assert isinstance(report, dict)
        if result is None:
            assert report["errors"]                  # 하드 실패엔 사유가 남는다


def test_result_has_no_aliasing_with_inputs():
    """3.1 리뷰 교훈: 결과를 변형해도 입력이 오염되지 않는다(deepcopy 격리)."""
    old = _old_home()
    new_devices = [
        _dev("new_ac", "air_conditioner", ["power", "target_temp"]),
        _dev("new_cleaner", "robot_cleaner", ["power"]),
    ]
    result, _ = map_to_new_home(old, new_devices)
    result["settings"]["new_ac"]["power"] = "MUTATED"
    result["devices"][0]["device_type"] = "MUTATED"
    assert old["settings"]["old_ac"]["power"] is True    # 원본 불변
    assert new_devices[0]["device_type"] == "air_conditioner"


# ---------- GPT code-review 회귀 (실패 경로 진실성) ----------

def test_invalid_new_devices_still_accounts_for_every_old_item():
    """[High-1] new_devices 무효(None)여도 옛 항목 전부가 held로 계상된다 —
    누락 0 항등식은 하드 실패 경로에서도 성립한다."""
    old = _old_home()
    result, report = map_to_new_home(old, None)
    assert result is None
    assert report["errors"]
    assert report["transferred"]["devices"] == []       # 팬텀 이전 없음
    assert _identity_holds(old, report)                  # old == 0 + held(전부)


def test_failed_result_validation_does_not_report_phantom_transfers():
    """[High-2] 최종 검증 실패 시 transferred가 남으면 리포트가 거짓말이 된다."""
    old = _old_home()
    new_devices = [
        _dev("bad ref!", "air_conditioner", ["power", "target_temp"]),  # 토큰 위반
        _dev("new_cleaner", "robot_cleaner", ["power"]),
    ]
    result, report = map_to_new_home(old, new_devices)
    assert result is None                                # 결과 무효로 거부
    assert report["transferred"]["devices"] == []        # 팬텀 이전 없음
    assert report["transferred"]["setting_keys"] == 0
    assert report["errors"]
    assert _identity_holds(old, report)


def test_matched_device_without_settings_is_not_unmatched_new():
    """[Med-3] 매칭됐지만 설정이 없는 새 기기는 unmatched_new가 아니다."""
    old = new_profile()
    old["devices"] = [_dev("old_light", "light", ["power"])]
    old["settings"] = {}                                 # 설정 없음
    assert validate_profile(old) == []
    new_devices = [_dev("new_light", "light", ["power"])]
    result, report = map_to_new_home(old, new_devices)
    assert result is not None
    assert ("old_light", "new_light") in report["transferred"]["devices"]
    assert "new_light" not in report["unmatched_new"]    # 매칭됨 → unmatched 아님


def test_new_device_count_over_limit_rejected_before_mapping():
    """[Med-4] 상한 초과 새 기기는 매핑·deepcopy 전에 거부(대량 작업 차단)."""
    from home_profile.schema import MAX_DEVICES
    old = _old_home()
    new_devices = [_dev(f"d{i}", "sensor", ["power"]) for i in range(MAX_DEVICES + 1)]
    result, report = map_to_new_home(old, new_devices)
    assert result is None
    assert report["errors"]
    assert _identity_holds(old, report)


# ---------- 데모 (Task 3 계약 최소 고정) ----------

def test_demo_relocate_output(capsys):
    import demo_relocate

    assert demo_relocate.main([]) == 0
    out = capsys.readouterr().out
    assert "보류" in out                             # 손실 없는 보류가 화면에
    assert "이전됨" in out                           # 이전 요약도 화면에(AC2)
    assert "설문 검증 대기" in out                    # H2 미검증 라벨(AC3)
    assert "실기기 아님" in out                       # NFR6 정직 표기(계약 9)
