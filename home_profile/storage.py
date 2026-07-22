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

from .schema import SCHEMA_VERSION, new_profile, validate_profile

# ---------- 예산 상수 ----------
# 출처: Garmin Connect IQ 개발자 포럼 (2026-07-22 조사, PROFILE_SCHEMA.md §5)
#   https://forums.garmin.com/developer/connect-iq/f/discussion/2661/storage-available
#   https://forums.garmin.com/developer/connect-iq/f/discussion/196823/
# ⚠️ 포럼발 수치이며 공식 문서 보증이 아니다 — MARGIN을 두는 이유 중 하나.
BUDGET_STORAGE_TOTAL = 128 * 1024   # Application.Storage 총량 (약 128KB)
BUDGET_STORAGE_KEY = 8 * 1024       # Storage 키 1개당 (약 8KB)
BLE_MTU = 20                        # BLE 특성 read/write 상한, long write 미지원

# 설계 판단(근거 문서 없음): 예산의 80%를 실사용 상한으로 본다.
# 펌웨어별 편차 + 다른 CIQ 앱과의 공유 + 포럼 수치의 불확실성에 대한 마진.
MARGIN = 0.8

# ---------- 대표 가정 ----------
# ⚠️ 실측이 아니다. 설문 문6(보유 가전 수)이 실측되면 그 분포로 교체한다.
SAMPLE_ASSUMPTIONS_ARE_MEASURED = False
SAMPLE_ASSUMPTION_NOTE = (
    "기기·루틴 수는 설계 가정이며 실측이 아니다. "
    "설문 문6(보유 가전 수) 실측 후 분포로 교체할 것."
)
SMALL = (5, 3)      # (기기 수, 루틴 수)
TYPICAL = (12, 8)
LARGE = (30, 20)

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
    try:
        raw = bytes(data)
        if raw.startswith(b"\xef\xbb\xbf"):
            raw = raw[3:]          # BOM 허용(제거 후 파싱) — 조용히 실패시키지 않는다
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as e:
            return None, [f"UTF-8 디코딩 실패({e.reason})"]
        try:
            obj = json.loads(text)
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
            return None, [
                f"스키마 버전 불일치: {version!r} (기대 {SCHEMA_VERSION!r}) — "
                f"마이그레이션 미지원, 명시적 거부"]

        errs = validate_profile(obj)
        if errs:
            return None, errs
        return obj, []
    except Exception as e:   # fail-closed
        return None, [f"역직렬화 내부 오류({type(e).__name__}: {e}) — 거부"]


# ---------- 크기 리포트 ----------
def resolve_path(profile, path: str):
    """리포트의 기여 필드 경로를 실제 값으로 되짚는다(테스트·진단용).
    경로 문법: devices[3] / settings[dev003] / routines[2]. 없으면 None."""
    try:
        section, _, rest = path.partition("[")
        key = rest.rstrip("]")
        node = profile.get(section)
        if isinstance(node, list):
            i = int(key)
            return node[i] if 0 <= i < len(node) else None
        if isinstance(node, dict):
            return node.get(key)
    except Exception:
        return None
    return None


def _safe_len(obj) -> int:
    try:
        return len(_dumps(obj))
    except Exception:
        return 0


def size_report(profile) -> dict:
    """직렬화 크기 분석. 예외를 던지지 않는다 —
    **검증 미통과 프로필에도 리포트가 나와야 한다**. 예산 초과의 원인을 찾는 것이
    이 함수의 목적이고, 그때 프로필은 대개 정상이 아니기 때문이다.

    반환 키: total_bytes, sections, bytes_per_device, bytes_per_routine,
    key_budget_bytes, total_budget_bytes, pct_of_key_budget,
    within_key_budget, within_total_budget, ble_chunks, top_contributors
    """
    key_budget = int(BUDGET_STORAGE_KEY * MARGIN)
    total_budget = int(BUDGET_STORAGE_TOTAL * MARGIN)
    rep = {
        "total_bytes": 0,
        "sections": {"devices": 0, "settings": 0, "routines": 0},
        "bytes_per_device": None,
        "bytes_per_routine": None,
        "key_budget_bytes": key_budget,
        "total_budget_bytes": total_budget,
        "pct_of_key_budget": 0.0,
        "within_key_budget": True,
        "within_total_budget": True,
        "ble_chunks": 0,
        "top_contributors": [],
        "note": SAMPLE_ASSUMPTION_NOTE,
    }
    if not isinstance(profile, dict):
        rep["error"] = f"프로필이 객체가 아님({type(profile).__name__})"
        return rep
    try:
        total = _safe_len(profile)
        rep["total_bytes"] = total

        contributors = []
        for section in ("devices", "settings", "routines"):
            node = profile.get(section)
            rep["sections"][section] = _safe_len(node) if node is not None else 0
            if isinstance(node, list):
                for i, item in enumerate(node):
                    contributors.append({"path": f"{section}[{i}]",
                                         "bytes": _safe_len(item)})
            elif isinstance(node, dict):
                for k, v in node.items():
                    contributors.append({"path": f"{section}[{k}]",
                                         "bytes": _safe_len(v)})

        devices = profile.get("devices")
        if isinstance(devices, list) and devices:
            rep["bytes_per_device"] = rep["sections"]["devices"] / len(devices)
        routines = profile.get("routines")
        if isinstance(routines, list) and routines:
            rep["bytes_per_routine"] = rep["sections"]["routines"] / len(routines)

        rep["pct_of_key_budget"] = 100 * total / key_budget if key_budget else 0.0
        rep["within_key_budget"] = total <= key_budget
        rep["within_total_budget"] = total <= total_budget
        rep["ble_chunks"] = math.ceil(total / BLE_MTU) if BLE_MTU else 0
        contributors.sort(key=lambda c: c["bytes"], reverse=True)
        rep["top_contributors"] = contributors[:5]
    except Exception as e:   # fail-closed: 리포트는 나오되 사유를 남긴다
        rep["error"] = f"리포트 내부 오류({type(e).__name__}: {e})"
    return rep


def format_report(rep: dict) -> str:
    """사람이 읽는 한 줄 요약 — 실행 로그·문서 기록용."""
    verdict = "예산 내" if rep["within_key_budget"] else "키 예산 초과"
    return (f"{rep['total_bytes']:,}B "
            f"({rep['pct_of_key_budget']:.1f}% of {rep['key_budget_bytes']:,}B) "
            f"· BLE {rep['ble_chunks']:,}청크 · {verdict}")
