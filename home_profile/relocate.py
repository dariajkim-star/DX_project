# -*- coding: utf-8 -*-
"""이사 — 옛 프로필을 새 집 기기 집합에 매핑 (Story 3.2, FR5).

설계 근거: docs/planning-artifacts/epics.md#Story 3.2
       docs/implementation-artifacts/3-2-relocate-mapping.md

이 모듈이 답하는 질문: **"이사해도 길들인 집이 따라오는가"**(P-2 반박).
3.1(재설치 복원)은 device_ref가 보존되는 왕복이었다. 이사는 **기기 집합 자체가
바뀐다** — 옛 dev000(에어컨)을 새 집의 newAC(에어컨)에 얹는다. 그래서 이건
복원이 아니라 **매핑**이다.

⚠️ 이것은 **처방(설계 결정)**이다. VOC(P-2)가 "이사하면 다 없어짐"이라는 문제를
줬고, "device_type으로 매칭하고 capability 교집합만 이전한다"는 해법은 **우리의
선택**이다. 매칭 알고리즘의 정당성을 VOC 수치로 포장하지 않는다.

계약 (3.1·1.x 승계):
  1. **예외 금지** — map_to_new_home은 어떤 입력에도 예외를 던지지 않는다.
     하드 실패는 (None, report)로 fail-closed.
  2. **손실 없는 보류(누락 0)** — 매칭 안 되는 기기·미지원 설정·이전 불가 루틴을
     **버리지 않는다.** 전부 held에 사유와 함께 남고, "옛 항목 = transferred + held"
     항등식이 성립한다. 3.1 merge_chunks의 "반쪽 금지"와 같은 계보 — 다만 여기선
     거부가 아니라 명시적 보류(이사는 부분 이전이 정상).
  3. **루틴 원자적 이전** — 액션이 전부 매핑되면 이전, 하나라도 안 되면 통째로
     보류. 부분 이전은 사용자 자동화의 조용한 변형이다.
  4. **결정적** — 같은 (옛 프로필, 새 기기 집합) → 같은 매핑·같은 리포트.
     device_type별 묶기 + 순서 기반 1:1 배정(딕셔너리 순서·난수 비의존).
  5. **오류·보류 사유에 페이로드 값 금지** — 사유는 열거 라벨, 항목은 type·키
     이름까지만(값은 PII 운반체일 수 있다, 1.x 리뷰 계승).
  6. **결과는 반드시 유효** — new_profile은 validate_profile()을 통과한다
     (새 refs·지원 키·비어있지 않은 actions). 통과 못 하면 (None, report).

경계: profile→profile 순수 변환이라 캐리어를 모른다. schema로 검증만 하고
schema·carrier·storage를 수정하지 않는다.
"""
import copy

from .schema import new_profile, validate_profile

__all__ = [
    "REASON_NO_MATCHING_TYPE",
    "REASON_CAPABILITY_UNSUPPORTED",
    "REASON_ROUTINE_UNMAPPABLE",
    "map_to_new_home",
]

# 보류 사유 — 열거 라벨(자유 문자열로 PII 운반 금지).
REASON_NO_MATCHING_TYPE = "no_matching_type"          # 같은 type의 새 기기 없음
REASON_CAPABILITY_UNSUPPORTED = "capability_unsupported"  # 설정 키를 새 기기가 미지원
REASON_ROUTINE_UNMAPPABLE = "routine_action_unmappable"   # 루틴 액션 이전 불가


def _empty_report():
    return {
        "transferred": {"devices": [], "setting_keys": 0, "routines": []},
        "held": [],                  # [{"kind", "reason", ...}]
        "unmatched_new": [],         # 설정을 못 받은 새 기기 device_ref
        "errors": [],
    }


def map_to_new_home(old_profile, new_devices):
    """옛 프로필을 새 집 기기 집합에 매핑한다. 반환 (new_profile | None, report).

    old_profile: 유효한 홈 프로필. new_devices: 새 집 기기 dict 목록
    (device_ref·device_type·capabilities). 매칭 성공하되 보류 항목이 있어도
    **유효한 new_profile + report**를 낸다. new_profile이 None인 것은 하드
    실패(입력 무효·결과 검증 실패)뿐이다.
    """
    report = _empty_report()
    try:
        errs = validate_profile(old_profile)
        if errs:
            report["errors"].append("옛 프로필이 유효하지 않음 — 매핑 불가")
            return None, report
        if not isinstance(new_devices, list):
            report["errors"].append(
                f"new_devices는 목록이어야 함({type(new_devices).__name__})")
            return None, report

        # 새 기기를 device_type별로 묶는다(입력 순서 보존 — 결정성). 각 기기의
        # 사용 여부와 capability 집합을 함께 들고 다닌다.
        new_by_type = {}
        for dev in new_devices:
            if not isinstance(dev, dict):
                report["errors"].append(
                    f"새 기기 항목이 dict가 아님({type(dev).__name__})")
                return None, report
            dtype = dev.get("device_type")
            new_by_type.setdefault(dtype, []).append(
                {"dev": dev, "used": False,
                 "caps": set(dev.get("capabilities", []))
                         if isinstance(dev.get("capabilities"), list) else set()})

        old_settings = old_profile.get("settings", {})
        old_settings = old_settings if isinstance(old_settings, dict) else {}

        # 1) 기기 매칭 — 옛 기기 순서대로, 같은 type의 미사용 새 기기에 1:1 배정.
        mapping = {}                 # old_ref -> {"new_ref", "caps"}
        for dev in old_profile.get("devices", []):
            old_ref = dev.get("device_ref")
            dtype = dev.get("device_type")
            slot = _first_unused(new_by_type.get(dtype))
            if slot is None:
                report["held"].append({"kind": "device",
                                        "reason": REASON_NO_MATCHING_TYPE,
                                        "device_type": dtype})
                continue
            slot["used"] = True
            new_ref = slot["dev"].get("device_ref")
            mapping[old_ref] = {"new_ref": new_ref, "caps": slot["caps"]}
            report["transferred"]["devices"].append((old_ref, new_ref))

        # 2) 설정 이전 — 매칭된 기기의 (옛 설정 키 ∩ 새 capability)만.
        new_settings = {}
        for old_ref, kv in old_settings.items():
            m = mapping.get(old_ref)
            if not isinstance(kv, dict):
                # 유효 프로필이면 도달 불가(schema가 dict 강제)지만 방어적으로.
                continue
            for key, value in kv.items():
                if m is None:
                    # 매칭 안 된 기기의 설정 — 기기 보류에 딸린 설정 보류.
                    report["held"].append({"kind": "setting",
                                           "reason": REASON_NO_MATCHING_TYPE,
                                           "setting_key": key})
                elif key not in m["caps"]:
                    report["held"].append({"kind": "setting",
                                           "reason": REASON_CAPABILITY_UNSUPPORTED,
                                           "setting_key": key})
                else:
                    dst = new_settings.setdefault(m["new_ref"], {})
                    dst[key] = copy.deepcopy(value)      # aliasing 격리(3.1 교훈)
                    report["transferred"]["setting_keys"] += 1

        # 3) 루틴 이전 — 원자적. 모든 액션이 매핑되면 새 ref로 재작성, 아니면 보류.
        new_routines = []
        for idx, routine in enumerate(old_profile.get("routines", [])):
            actions = routine.get("actions", []) if isinstance(routine, dict) else []
            remapped, ok = _remap_actions(actions, mapping)
            if ok:
                new_routine = copy.deepcopy(routine)     # aliasing 격리
                new_routine["actions"] = remapped
                new_routines.append(new_routine)
                report["transferred"]["routines"].append(idx)
            else:
                report["held"].append({"kind": "routine",
                                       "reason": REASON_ROUTINE_UNMAPPABLE,
                                       "routine_index": idx})

        # 4) 새 프로필 조립 — 새 집의 물리적 기기 전부를 담고, 설정은 이전분만.
        result = new_profile()
        result["schema_version"] = old_profile.get("schema_version",
                                                   result["schema_version"])
        result["reserved_wellness"] = copy.deepcopy(
            old_profile.get("reserved_wellness", {}))
        result["devices"] = [copy.deepcopy(d) for d in new_devices]
        result["settings"] = new_settings
        result["routines"] = new_routines

        # 설정을 못 받은 새 기기는 침묵하지 않는다(역방향 누락 금지).
        for dev in new_devices:
            ref = dev.get("device_ref")
            if ref not in new_settings:
                report["unmatched_new"].append(ref)

        errs = validate_profile(result)              # 결과 유효성 강제
        if errs:
            report["errors"].append("매핑 결과가 유효하지 않음 — 거부")
            return None, report
        return result, report
    except Exception as e:   # fail-closed
        report["errors"].append(f"매핑 내부 오류({type(e).__name__}) — 거부")
        return None, report


def _first_unused(slots):
    """같은 type의 미사용 새 기기 슬롯을 순서대로 하나 찾는다(결정적)."""
    if not slots:
        return None
    for slot in slots:
        if not slot["used"]:
            return slot
    return None


def _remap_actions(actions, mapping):
    """루틴 액션들을 새 device_ref로 재작성. 반환 (remapped_actions, ok).

    모든 액션이 (매핑된 기기 + 지원되는 setting_key)여야 ok=True. 하나라도
    안 되면 ok=False로, 부분 결과를 쓰지 않는다(원자성)."""
    if not isinstance(actions, list) or not actions:
        return [], False
    out = []
    for a in actions:
        if not isinstance(a, dict):
            return [], False
        m = mapping.get(a.get("device_ref"))
        key = a.get("setting_key")
        if m is None or key not in m["caps"]:
            return [], False
        new_a = copy.deepcopy(a)
        new_a["device_ref"] = m["new_ref"]
        out.append(new_a)
    return out, True
