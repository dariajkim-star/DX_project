# -*- coding: utf-8 -*-
"""홈 프로필 스키마 (v1.0.0) — Story 1.1.

설계 근거: docs/planning-artifacts/epics.md#Story 1.1
       docs/implementation-artifacts/1-1-home-profile-schema.md

이 스키마는 "집의 상태를 클라우드 계정이 아니라 사용자 몸에 귀속시킨다"는
처방(CX_DEFINITION §2.3)의 자료구조다.

불변 원칙:
  1. 식별자 없음 — 이름·계정·연락처가 **설계상 존재할 수 없다**(FR7 선행).
     "안 넣었다"가 아니라 assert_no_identifiers()로 기계 증명한다.
  2. 웰니스는 예약만 — reserved_wellness는 선언되어 있으나 값을 허용하지 않고,
     해석·판단하는 코드가 이 모듈에 존재하지 않는다(NFR5, 의료 규제).
  3. 조용한 통과 금지 — 미지 버전·미지 최상위 키는 거부한다(NFR6).
  4. 포맷 중립 — 순수 dict로 정의한다. JSON이 기본 표현이지만 크기 예산 측정
     (Story 1.2) 후 CBOR/MessagePack으로 바꿔도 스키마는 그대로여야 한다.

표준 라이브러리만 사용한다. pydantic·jsonschema를 쓰지 않는 이유:
이 표현은 최종적으로 워치급 환경(Monkey C)으로 이식된다 — 스키마 정의가
Python 전용 라이브러리에 종속되면 캐리어 중립(NFR3)이 코드 레벨에서 깨진다.

전송 제약 (2026-07-22 조사, Story 1.2·Epic 2가 상속):
  Connect IQ Application.Storage 총 ~128KB / 키당 ~8KB
  Connect IQ BLE 특성 ~20바이트 MTU, long write 미지원
  → 프로필 전체를 한 키·한 write로 보낼 수 없다. devices[]·routines[] 원소가
    각각 독립 직렬화되도록 평평하게 유지한 이유다. 청크 프로토콜 자체는
    이 스토리 범위가 아니다.
"""

SCHEMA_VERSION = "1.0.0"

# 지원 버전 집합. 새 버전을 추가할 때 MIGRATIONS도 함께 갱신한다.
SUPPORTED_VERSIONS = frozenset({"1.0.0"})

# 마이그레이션 레지스트리: {"출발버전": callable(profile) -> profile}
# 등록 규약 — 함수는 프로필 dict를 받아 다음 버전 dict를 반환하고, 부작용이 없어야
# 한다. 1.0.0은 최초 버전이라 등록분이 없다(빈 dict가 정상 상태).
MIGRATIONS = {}

TOP_LEVEL_KEYS = (
    "schema_version",
    "devices",
    "settings",
    "routines",
    "reserved_wellness",
)
REQUIRED_TOP_LEVEL_KEYS = (
    "schema_version",
    "devices",
    "settings",
    "routines",
)

DEVICE_REQUIRED_KEYS = ("device_ref", "device_type")
ROUTINE_REQUIRED_KEYS = ("trigger", "actions")
ACTION_REQUIRED_KEYS = ("device_ref", "setting_key", "value")

# 개인 식별 정보로 이어지는 키 조각. 부분 일치·대소문자 무시로 검사한다.
# 완전한 목록일 수 없다 — 방어선이지 증명이 아니다. 새 필드를 추가할 때
# 여기 걸리면 "우회할 이름을 찾는" 게 아니라 그 필드가 정말 필요한지 되묻는다.
FORBIDDEN_KEY_FRAGMENTS = (
    "name",
    "account",
    "email",
    "phone",
    "user_id",
    "userid",
    "birth",
    "address",
    "contact",
    "ssn",
    "gender",
    "owner",
)


def new_profile() -> dict:
    """현재 스키마 버전이 각인된 빈 프로필."""
    return {
        "schema_version": SCHEMA_VERSION,
        "devices": [],
        "settings": {},
        "routines": [],
        "reserved_wellness": {},
    }


def is_supported(version) -> bool:
    """지원 버전 판정. 모르는 값·형식 위반은 전부 False —
    호출자가 '아마 괜찮겠지'로 넘어갈 여지를 남기지 않는다."""
    if not isinstance(version, str):
        return False
    parts = version.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        return False
    return version in SUPPORTED_VERSIONS


def assert_no_identifiers(obj, _path="profile") -> list:
    """중첩 dict/list를 재귀 순회해 식별자성 키를 찾는다.

    반환: 발견된 위치 목록(빈 리스트 = 없음). 이름이 assert_인데 예외를 던지지
    않는 것은 의도다 — 여러 위반을 한 번에 사람에게 보여줘야 하고, 이 함수가
    AC4의 '증명 수단'이라 테스트에서 반환값을 검사하기 때문이다.
    """
    found = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            key_l = str(k).lower()
            for frag in FORBIDDEN_KEY_FRAGMENTS:
                if frag in key_l:
                    found.append(f"{_path}.{k}: 식별자성 키('{frag}') — FR7 위반")
                    break
            found += assert_no_identifiers(v, f"{_path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            found += assert_no_identifiers(v, f"{_path}[{i}]")
    return found


def validate_profile(profile) -> list:
    """프로필 검증. 위반 사유 목록을 반환한다(빈 리스트 = 통과).

    예외가 아니라 목록을 반환하는 이유: 여러 위반을 한 번에 보고해야 사람이
    판단할 수 있다. (synthetic_panel.validate_seg_bundle()은 '실패 시 사유
    문자열' 단일 반환인데, 그쪽은 게이트라 첫 실패에서 멈추는 게 맞고
    이쪽은 스키마 검사라 전수 보고가 맞다.)
    """
    errs = []
    if not isinstance(profile, dict):
        return [f"프로필 최상위가 객체가 아님({type(profile).__name__})"]

    for key in REQUIRED_TOP_LEVEL_KEYS:
        if key not in profile:
            errs.append(f"필수 최상위 키 누락: {key}")

    for key in profile:
        if key not in TOP_LEVEL_KEYS:
            errs.append(f"미지의 최상위 키: {key} — 조용한 확장 금지(NFR6)")

    version = profile.get("schema_version")
    if "schema_version" in profile and not is_supported(version):
        errs.append(f"지원하지 않는 스키마 버전: {version!r} "
                    f"(지원: {sorted(SUPPORTED_VERSIONS)})")

    # ── devices
    device_refs = set()
    devices = profile.get("devices")
    if devices is not None:
        if not isinstance(devices, list):
            errs.append("devices는 배열이어야 함")
        else:
            for i, d in enumerate(devices):
                if not isinstance(d, dict):
                    errs.append(f"devices[{i}]가 객체가 아님")
                    continue
                for k in DEVICE_REQUIRED_KEYS:
                    if k not in d:
                        errs.append(f"devices[{i}] 필수 키 누락: {k}")
                ref = d.get("device_ref")
                if ref is not None:
                    if ref in device_refs:
                        errs.append(f"devices[{i}] device_ref 중복: {ref!r} — "
                                    f"복원 시 매칭이 비결정적이 됨")
                    device_refs.add(ref)
                caps = d.get("capabilities", [])
                if not isinstance(caps, list):
                    errs.append(f"devices[{i}].capabilities는 배열이어야 함")

    # ── settings: {device_ref: {setting_key: value}}
    settings = profile.get("settings")
    if settings is not None:
        if not isinstance(settings, dict):
            errs.append("settings는 객체여야 함")
        else:
            for ref, kv in settings.items():
                if devices is not None and isinstance(devices, list) \
                        and ref not in device_refs:
                    errs.append(f"settings의 device_ref {ref!r}가 devices에 없음")
                if not isinstance(kv, dict):
                    errs.append(f"settings[{ref!r}]는 객체여야 함")

    # ── routines
    routines = profile.get("routines")
    if routines is not None:
        if not isinstance(routines, list):
            errs.append("routines는 배열이어야 함")
        else:
            for i, r in enumerate(routines):
                if not isinstance(r, dict):
                    errs.append(f"routines[{i}]가 객체가 아님")
                    continue
                for k in ROUTINE_REQUIRED_KEYS:
                    if k not in r:
                        errs.append(f"routines[{i}] 필수 키 누락: {k}")
                trigger = r.get("trigger")
                if trigger is not None and (not isinstance(trigger, dict)
                                            or "type" not in trigger):
                    errs.append(f"routines[{i}].trigger는 type을 가진 객체여야 함")
                actions = r.get("actions")
                if actions is not None:
                    if not isinstance(actions, list) or not actions:
                        errs.append(f"routines[{i}].actions는 비어있지 않은 배열이어야 함")
                    else:
                        for j, a in enumerate(actions):
                            if not isinstance(a, dict):
                                errs.append(f"routines[{i}].actions[{j}]가 객체가 아님")
                                continue
                            for k in ACTION_REQUIRED_KEYS:
                                if k not in a:
                                    errs.append(
                                        f"routines[{i}].actions[{j}] 필수 키 누락: {k}")
                            ref = a.get("device_ref")
                            # 존재하지 않는 기기를 가리키는 루틴은 조용히 통과하면
                            # 안 된다 — 이사(3.2)에서 '보류'로 다룰 대상이지만,
                            # 지금은 프로필 자체의 정합성 위반이다.
                            if ref is not None and devices is not None \
                                    and isinstance(devices, list) \
                                    and ref not in device_refs:
                                errs.append(
                                    f"routines[{i}].actions[{j}]가 미등록 기기 "
                                    f"{ref!r}를 참조")

    # ── reserved_wellness (NFR5)
    if "reserved_wellness" in profile:
        rw = profile["reserved_wellness"]
        if not isinstance(rw, dict):
            errs.append("reserved_wellness는 객체여야 함")
        elif rw:
            errs.append("reserved_wellness는 예약 필드 — 값을 담을 수 없다"
                        "(NFR5: 진단·의료 판단 기능 배제). "
                        f"발견된 키: {sorted(rw)}")

    # ── 식별자 부재 (FR7 선행). 별도 호출을 잊어도 여기서 막힌다.
    errs += assert_no_identifiers(profile)
    return errs
