# -*- coding: utf-8 -*-
"""온바디 저장 — 직렬화·역직렬화·크기 예산 (Story 1.2).

설계 근거: docs/planning-artifacts/epics.md#Story 1.2
       docs/implementation-artifacts/1-2-onbody-storage-size-budget.md

이 모듈이 답하는 질문: **"집 프로필이 정말 손목에 들어가는가"**(NFR4).
스키마(1.1)가 '무엇으로 담기는가'를 정의했다면, 여기서는 그게 워치급 예산 안에
들어가는지를 **수치로 판정**한다.

Story 1.1 리뷰(2026-07-22 Code Review Crew)에서 확립된 계승 계약:
  1. **예외 금지** — serialize·deserialize·size_report는 어떤 입력에도 예외를
     던지지 않는다. 크래시는 곧 검사 우회다(1.1 리뷰 F3: try/except 호출자에서
     PII 스캔이 통째로 증발했다). 내부 오류는 fail-closed 거부.
  2. **와이어 불신** — deserialize는 역직렬화 직후 validate_profile()을 다시
     돌린다. 직렬화 전 통과는 바이트가 오는 동안 아무것도 보증하지 않는다.
  3. **보증은 실측만** — 예산 판정 수치는 실행 결과만 문서에 옮긴다.
  4. **마이그레이션 미결정 유지** — 지원 밖 버전은 명시적 거부. 빈 훅을 만들지
     않는다(1.1 v1의 MIGRATIONS 재판 금지).

포맷: **JSON UTF-8 compact가 기준 표현**. CBOR·MessagePack은 서드파티라 쓰지
않는다 — 이 표현은 워치급 Monkey C로 이식되며, Python 전용 라이브러리 종속은
캐리어 중립(NFR3)을 코드 레벨에서 깬다. 예산 초과 시의 대안(키 축약·분할 저장·
zlib)은 수치와 함께 문서화하되 구현은 사람 결정 이후로 미룬다.
"""
import json
import math

from .schema import (
    _VERSION_SHOW_RE,
    SCHEMA_VERSION,
    new_profile,
    validate_profile,
)

# ---------- 예산 참조값 (결정 ③ C: 구간 표기) ----------
# v2까지는 BUDGET_STORAGE_KEY(8,192) × MARGIN(0.8) = 6,553B 하나로 판정했다.
# 2차 리뷰(Grumbal F4)에서 드러난 문제: MARGIN은 안전 마진이 아니라 **판정
# 결정 변수**였다(0.5면 TYPICAL이 뒤집힘). 근거 문서 없는 상수를 곱한 값을
# 0.1% 단위로 보고하는 것은 정밀도 착시다.
#
# 그래서 단일 판정을 버리고 **구간으로 보고**한다 — 어느 예산을 쓸지는
# 실기기 실측(결정 ②)으로 확정될 때까지 열어둔다.
#
#  · 보수(4,096B)  — 포럼 수치의 절반. 펌웨어 편차·타 CIQ 앱 공유를 감안한 하한
#  · 포럼(8,192B)  — 6년 전 포럼 글. 후속 스레드에서 이 값은 실제로는
#                    Application.Properties의 한계로 구분됨 (PROFILE_SCHEMA §5.3)
#  · 공식(32,768B) — Application.Storage 공식 문서 "values are limited to 32 KB".
#                    단 총량은 "기기별로 다름"이고 setValue System Error 버그 존재
BUDGET_REFERENCES = (
    ("보수", 4 * 1024),
    ("포럼", 8 * 1024),
    ("공식", 32 * 1024),
)
BUDGET_STORAGE_TOTAL = 128 * 1024   # Application.Storage 총량 (포럼발, 미확정)
BLE_MTU = 20                        # BLE 특성 read/write 상한, long write 미지원

# 저장 전략(결정 ⑤ A): **섹션 분할** — meta/devices/settings/routines를
# 각각 별도 Storage 키에 넣는다. 판정은 '전체가 한 키에 들어가는가'(single)와
# '가장 큰 섹션이 한 키에 들어가는가'(split) 둘 다 보고한다.
SECTION_KEYS = ("devices", "settings", "routines")

# 와이어 입력 하드 캡 (2차 리뷰 Vex F5). v1은 길이 검사가 전혀 없어
# 기기 20만대·15.6MB 프로필이 deserialize를 통과했다 — 예산의 1,900배이자
# 워치 대상 메모리 고갈 DoS. 파싱 전에 자른다.
MAX_WIRE_BYTES = BUDGET_STORAGE_TOTAL   # 131,072B — 총량 예산을 넘는 입력은 볼 필요가 없다

# ---------- 대표 가정 ----------
# ⚠️ 아래 (기기 수, 루틴 수)는 **실측이 아니라 설계 가정**이다.
# 설문 문6(보유 가전 수)이 실측되면 그 분포로 교체한다.
# 2차 리뷰(Grumbal F1·F2) 경고: 이 픽스처로 잰 크기는 **픽스처의 크기**이지
# 스키마가 허용하는 프로필의 크기가 아니다. 스키마에 개수 상한이 없어
# 같은 (12,8)로 23,395B(예산 357%)에 도달한다. 예산 판정에 쓸 때는
# 반드시 그 한계를 병기할 것 — docs/PROFILE_SCHEMA.md §5.2.
# (v1의 SAMPLE_ASSUMPTIONS_ARE_MEASURED 상수는 아무도 읽지 않고 테스트만
#  자기 자신을 단언해 삭제했다 — 1.1의 MIGRATIONS와 같은 종. Yui F5)
ASSUMED_SMALL = (5, 3)
ASSUMED_TYPICAL = (12, 8)
ASSUMED_LARGE = (30, 20)
SMALL, TYPICAL, LARGE = ASSUMED_SMALL, ASSUMED_TYPICAL, ASSUMED_LARGE

_DEVICE_TYPES = (
    "air_conditioner", "washer", "dryer", "refrigerator", "air_purifier",
    "light", "styler", "dishwasher", "robot_cleaner", "oven",
)
_CAPABILITIES = (
    "power", "target_temp", "fan_speed", "mode", "timer_min",
    "child_lock", "eco_mode", "humidity", "filter_state", "schedule",
)
_TRIGGER_TYPES = ("time", "arrive_home", "leave_home", "device_state")


def make_sample_profile(n_devices: int, n_routines: int) -> dict:
    """대표 가정 샘플. 결정적(같은 인자 → 같은 결과)이라 크기 실측이 재현된다.

    생성기의 계약: 산출물은 validate_profile()을 통과한다.
    문자열 길이는 최상 케이스가 아니라 실제에 가깝게 잡는다 —
    최상 케이스로 잰 예산은 예산이 아니다.
    """
    p = new_profile()
    for i in range(max(0, int(n_devices))):
        dtype = _DEVICE_TYPES[i % len(_DEVICE_TYPES)]
        # 기기당 capability 3~5개 (순환 선택 — 결정적)
        caps = [_CAPABILITIES[(i + j) % len(_CAPABILITIES)]
                for j in range(3 + i % 3)]
        ref = f"dev{i:03d}"
        p["devices"].append({
            "device_ref": ref, "device_type": dtype, "capabilities": caps,
        })
        p["settings"][ref] = {c: _sample_value(c, i) for c in caps}
    refs = [d["device_ref"] for d in p["devices"]]
    for r in range(max(0, int(n_routines))):
        if not refs:
            break
        ttype = _TRIGGER_TYPES[r % len(_TRIGGER_TYPES)]
        # 루틴당 액션 2~3개
        actions = []
        for a in range(2 + r % 2):
            ref = refs[(r + a) % len(refs)]
            key = p["devices"][(r + a) % len(refs)]["capabilities"][0]
            actions.append({"device_ref": ref, "setting_key": key,
                            "value": _sample_value(key, r + a)})
        p["routines"].append({
            "trigger": {"type": ttype,
                        "params": {"at": f"{(22 + r) % 24:02d}:{(r * 7) % 60:02d}"}},
            "actions": actions,
        })
    return p


def _sample_value(cap: str, seed: int):
    if cap in ("power", "child_lock", "eco_mode"):
        return bool(seed % 2)
    if cap in ("target_temp", "humidity"):
        return 20 + seed % 10
    if cap == "timer_min":
        return 10 * (1 + seed % 6)
    if cap == "fan_speed":
        return ("low", "mid", "high")[seed % 3]
    if cap == "mode":
        return ("cool", "heat", "dry", "auto")[seed % 4]
    return ("on", "off", "standby")[seed % 3]


# ---------- 직렬화 ----------
class _DuplicateKey(ValueError):
    """JSON 객체에 중복 키가 있었다 (2차 리뷰 Vex F2)."""


def _no_duplicate_keys(pairs):
    seen = set()
    for k, _ in pairs:
        if k in seen:
            # 키 원문은 메시지에 넣지 않는다 — 그 자체가 PII 운반체일 수 있다
            raise _DuplicateKey(f"<str len={len(str(k))}>")
        seen.add(k)
    return dict(pairs)


def _dumps(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


def serialize(profile):
    """프로필 → bytes. 반환 (bytes | None, errors: list).

    직렬화 전 validate_profile()을 강제한다 — 검증을 안 거친 프로필이 와이어로
    나가는 경로를 만들지 않기 위해서다. 예외를 던지지 않는다.
    """
    try:
        errs = validate_profile(profile)
        if errs:
            return None, errs
        return _dumps(profile), []
    except Exception as e:   # fail-closed
        return None, [f"직렬화 내부 오류({type(e).__name__}: {e}) — 거부"]


def deserialize(data):
    """bytes → 프로필. 반환 (profile | None, errors: list).

    와이어에서 온 것은 신뢰하지 않는다 — 역직렬화 직후 validate_profile()을
    다시 돌린다. 어떤 입력(0바이트·잘림·비UTF8·깊이 폭탄·비객체)에도 예외를
    던지지 않는다.
    """
    if not isinstance(data, (bytes, bytearray)):
        return None, [f"입력은 bytes여야 함({type(data).__name__})"]
    if len(data) > MAX_WIRE_BYTES:
        # 파싱 전에 자른다 — decode+json.loads+검증기 자료구조가 전부
        # 메모리에 올라온 뒤에 거부하면 이미 늦다(2차 리뷰 Vex F5).
        return None, [f"입력 {len(data):,}B — 상한 {MAX_WIRE_BYTES:,}B 초과, 파싱 거부"]
    try:
        raw = bytes(data)
        if raw.startswith(b"\xef\xbb\xbf"):
            raw = raw[3:]          # BOM 허용(제거 후 파싱) — 조용히 실패시키지 않는다
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as e:
            return None, [f"UTF-8 디코딩 실패({e.reason})"]
        try:
            obj = json.loads(text, object_pairs_hook=_no_duplicate_keys)
        except _DuplicateKey as e:
            # 2차 리뷰 Vex F2: json.loads는 마지막 키가 이긴다. 공격자가
            # {"settings":{더러운 것},"settings":{깨끗한 것}}을 보내면 검증은
            # 깨끗한 사본을 보고 통과시키는데 **원본 바이트엔 PII가 남는다**.
            # 호출자가 원본 바이트를 저장하는 건 BLE 재조립 경로에서 가장
            # 자연스러운 선택이라, 이 차이 자체를 거부한다.
            return None, [f"중복 키 {e.args[0]} — 파서 차이 공격 방지로 거부"]
        except (json.JSONDecodeError, RecursionError) as e:
            # RecursionError: 깊이 폭탄. 크래시가 아니라 거부로 처리(1.1 리뷰 계승)
            return None, [f"JSON 파싱 실패({type(e).__name__})"]
        if not isinstance(obj, dict):
            return None, [f"최상위가 객체가 아님({type(obj).__name__})"]

        # AC4: 버전은 구조 검증보다 먼저 명시 처리한다.
        # 마이그레이션은 미결정(1.1 리뷰 F5) — 현재의 명시 처리는 '거부'이며,
        # 금지되는 것은 조용한 통과뿐이다.
        version = obj.get("schema_version")
        if version != SCHEMA_VERSION:
            # v1은 {version!r}로 무제한 에코했다 — 이 문자열은 PII 스캔을
            # 한 번도 안 거치고 로그로 나간다(2차 리뷰 Vex F4).
            shown = version if (isinstance(version, str)
                                and _VERSION_SHOW_RE.fullmatch(version))                 else f"<{type(version).__name__}>"
            return None, [
                f"스키마 버전 불일치: {shown} (기대 {SCHEMA_VERSION!r}) — "
                f"마이그레이션 미지원, 명시적 거부"]

        errs = validate_profile(obj)
        if errs:
            return None, errs
        return obj, []
    except Exception as e:   # fail-closed
        return None, [f"역직렬화 내부 오류({type(e).__name__}: {e}) — 거부"]


# ---------- 크기 리포트 ----------
def _safe_len(obj):
    """직렬화 길이. 실패 시 **None**(측정 불가) — 0이 아니다.

    2차 리뷰(Yui F2 / Boundary F1): v1은 실패 시 0을 반환했다. 그 결과
    직렬화 불가 프로필에서 total_bytes=0 → pct=0.0% → within_key_budget=True,
    즉 **예산 초과를 찾는 함수가 측정 실패한 프로필을 '예산 내'로 보고**했다.
    이 패키지의 나머지는 전부 fail-closed인데 여기만 fail-open이었다.
    """
    try:
        return len(_dumps(obj))
    except Exception:
        return None


def size_report(profile):
    """직렬화 크기 분석. 반환 **(report: dict, errors: list)**.

    결정 ③ C(구간 표기): 단일 예산·단일 판정을 내지 않는다. 실기기 실측(결정 ②)
    전까지 어느 값이 맞는지 모르므로 참조 예산 3종 각각에 대해 판정을 병기한다.
    결정 ⑤ A(섹션 분할): 판정은 두 축이다 —
      single = 프로필 전체가 Storage 키 하나에 들어가는가
      split  = 가장 큰 섹션이 Storage 키 하나에 들어가는가

    검증 미통과 프로필에도 리포트가 나온다(예산 초과 원인 진단이 목적).
    측정 실패는 0이 아니라 None으로 전파하고 errors에 남긴다(fail-closed).
    """
    errors = []
    rep = {
        "total_bytes": None,
        "sections": {k: None for k in SECTION_KEYS},
        "max_section_bytes": None,
        "max_section": None,
        "bytes_per_device": None,
        "bytes_per_routine": None,
        "budget_verdicts": {},
        "ble_chunks": None,
        "top_contributors": [],
    }
    if not isinstance(profile, dict):
        errors.append(f"프로필이 객체가 아님({type(profile).__name__})")
        return rep, errors
    try:
        total = _safe_len(profile)
        rep["total_bytes"] = total
        if total is None:
            errors.append("전체 직렬화 실패 — 크기 측정 불가(직렬화 불가 값 포함)")

        contributors = []
        for section in SECTION_KEYS:
            node = profile.get(section)
            if node is None:
                continue
            n = _safe_len(node)
            rep["sections"][section] = n
            if n is None:
                errors.append(f"{section} 직렬화 실패 — 섹션 크기 측정 불가")
            # 기여 필드는 **서수**로 지목한다 — settings 키는 사용자 통제
            # 문자열이라 경로에 넣으면 리포트가 PII를 흘린다(2차 리뷰 Vex F6).
            items = enumerate(node) if isinstance(node, list) else (
                enumerate(node.values()) if isinstance(node, dict) else ())
            for i, item in items:
                b = _safe_len(item)
                if b is not None:
                    contributors.append({"section": section, "index": i, "bytes": b})

        measured = {k: v for k, v in rep["sections"].items() if v is not None}
        if measured:
            rep["max_section"] = max(measured, key=measured.get)
            rep["max_section_bytes"] = measured[rep["max_section"]]

        devices = profile.get("devices")
        if isinstance(devices, list) and devices and rep["sections"]["devices"]:
            rep["bytes_per_device"] = rep["sections"]["devices"] / len(devices)
        routines = profile.get("routines")
        if isinstance(routines, list) and routines and rep["sections"]["routines"]:
            rep["bytes_per_routine"] = rep["sections"]["routines"] / len(routines)

        mx = rep["max_section_bytes"]
        for label, budget in BUDGET_REFERENCES:
            rep["budget_verdicts"][label] = {
                "budget_bytes": budget,
                "single": (total <= budget) if total is not None else None,
                "split": (mx <= budget) if mx is not None else None,
            }
        if total is not None and BLE_MTU > 0:
            rep["ble_chunks"] = math.ceil(total / BLE_MTU)
        contributors.sort(key=lambda c: c["bytes"], reverse=True)
        rep["top_contributors"] = contributors[:5]
    except Exception as e:   # fail-closed
        errors.append(f"리포트 내부 오류({type(e).__name__}: {e})")
    return rep, errors
