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
    MAX_DEVICES,
    MAX_ROUTINES,
    SCHEMA_VERSION,
    new_profile,
    validate_profile,
)

# ---------- 예산 기준 (결정 #1: 보수 단일값) ----------
# 파티 결정(2026-07-22): 예산 상수를 실기기 실측 전까지 **보수값 하나**로 고정한다.
# 4,096B = 포럼 8KB의 절반. 근거는 "포럼 8KB도 못 믿으니 그 절반을 하한으로" —
# 이 값 자체가 이미 마진이라 별도 MARGIN을 곱하지 않는다(그게 아까 없앤 병).
# 실기기 실측(결정 #2 실행계획, PROFILE_SCHEMA §5.4)이 오면 이 값을 교체한다.
BUDGET_PER_KEY = 4 * 1024           # 보수: Storage 키 1개당 상한
BUDGET_STORAGE_TOTAL = 128 * 1024   # Application.Storage 총량 (포럼발, 미확정)
BLE_MTU = 20                        # BLE 특성 read/write 상한, long write 미지원

# 저장 전략(파티 결정: 기기 단위 분할). 프로필을 다음 키들로 쪼갠다:
#   meta                 — schema_version, reserved_wellness, 기기/루틴 인덱스
#   device:<ref>         — 기기 1대 + 그 설정 (기기당 키 1개)
#   routine:<i>          — 루틴 1개 (루틴당 키 1개)
# 이렇게 하면 **최악 케이스에서도 조각 하나가 보수 예산에 들어간다**
# (실측: 기기 1대 최악 1,772B / 루틴 1개 최악 2,328B < 4,096B).
# 섹션 통째(routines 46KB)로는 안 들어가던 것을 조각으로 나눠 해결.
CHUNK_KINDS = ("meta", "device", "routine")

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


# ---------- 기기 단위 분할 (파티 결정) ----------
def split_chunks(profile) -> dict:
    """프로필을 저장 키 단위 조각으로 나눈다. 반환 {키이름: 파이썬 객체}.

    이것은 '저장 표현'이지 '전송 표현'이 아니다 — BLE 청킹(20B)은 Epic 2가
    이 조각들 위에 다시 얹는다. 여기서는 Storage 키 경계만 정한다.

    device 조각은 기기 정의 + 그 기기의 settings를 함께 담는다(복원 시 한 조각이
    한 기기를 완결). routines는 기기 참조를 넘나들므로 루틴 단위로 쪼갠다.
    """
    if not isinstance(profile, dict):
        return {}
    chunks = {"meta": {
        "schema_version": profile.get("schema_version"),
        "reserved_wellness": profile.get("reserved_wellness", {}),
        "device_refs": [d.get("device_ref") for d in profile.get("devices", [])
                        if isinstance(d, dict)],
        "routine_count": len(profile.get("routines", []))
        if isinstance(profile.get("routines"), list) else 0,
    }}
    settings = profile.get("settings") if isinstance(profile.get("settings"), dict) else {}
    for d in profile.get("devices", []):
        if not isinstance(d, dict):
            continue
        ref = d.get("device_ref")
        chunk = dict(d)
        if ref in settings:
            chunk["_settings"] = settings[ref]
        chunks[f"device:{ref}"] = chunk
    for i, r in enumerate(profile.get("routines", [])):
        chunks[f"routine:{i}"] = r
    return chunks


# ---------- 저장 조각 병합 — split_chunks의 역함수 (Story 3.1) ----------
def merge_chunks(chunks):
    """저장 키 조각 {키이름: 객체} → 프로필. 반환 (profile | None, errors). **예외 금지**.

    split_chunks(위)가 접은 것을 정확히 되돌린다:
      - device:<ref> 조각의 `_settings`를 떼어 top-level settings[ref]로 편다
      - 순서는 meta.device_refs가 진실 원천(딕셔너리 키 순서에 기대지 않는다)
      - routine:<i>는 인덱스 순서대로 복원한다

    meta는 유실 탐지에 쓴다(조용한 누락 금지): device_refs에 있는데 조각이
    없거나 routine_count가 실제와 다르면 **거부** — 반쪽 프로필을 만들지 않는다.
    병합 직후 validate_profile()을 다시 돌린다(와이어 불신, 계약 2) — 조각이
    개별로 유효해도 합쳐서 유효하란 법은 없다.

    ⚠️ routine.reassemble(BLE 20B 전송 청크의 바이트 재조립)과 다른 관심사다.
    """
    try:
        if not isinstance(chunks, dict):
            return None, [f"조각 입력이 dict가 아님({type(chunks).__name__})"]
        meta = chunks.get("meta")
        if not isinstance(meta, dict):
            return None, ["meta 조각이 없거나 객체가 아님 — 복원 불가"]
        refs = meta.get("device_refs")
        if not isinstance(refs, list):
            return None, ["meta.device_refs가 목록이 아님 — 복원 불가"]
        routine_count = meta.get("routine_count")
        # bool은 int의 하위형이라 isinstance를 통과한다 — 명시 배제(True/False가
        # 개수로 둔갑하지 않게). 스키마 상한(MAX_DEVICES/MAX_ROUTINES)을 병합에도
        # 강제한다: 유효 프로필은 이미 이 상한 안이고, 상한 밖 meta는 와이어 위조다.
        if isinstance(routine_count, bool) or not isinstance(routine_count, int) \
                or routine_count < 0:
            return None, ["meta.routine_count가 음이 아닌 정수가 아님 — 복원 불가"]
        if len(refs) > MAX_DEVICES or routine_count > MAX_ROUTINES:
            return None, [f"복원 규모 초과: 기기 {len(refs)}/{MAX_DEVICES}, "
                          f"루틴 {routine_count}/{MAX_ROUTINES} — 거부"]

        errs = []
        profile = {
            "schema_version": meta.get("schema_version"),
            "reserved_wellness": meta.get("reserved_wellness", {}),
            "devices": [],
            "settings": {},
            "routines": [],
        }

        # 기기: meta.device_refs 순서대로. 결손은 거부(부분 복원 금지).
        for ref in refs:
            chunk = chunks.get(f"device:{ref}")
            if not isinstance(chunk, dict):
                errs.append(f"기기 조각 결손: device:{ref!s:.32} — 반쪽 복원 거부")
                continue
            device = dict(chunk)
            settings = device.pop("_settings", None)
            if settings is not None:
                profile["settings"][ref] = settings
            profile["devices"].append(device)

        # 루틴: 카운트 일치 강제 + 인덱스 순서 복원.
        routine_keys = [k for k in chunks if isinstance(k, str)
                        and k.startswith("routine:")]
        if len(routine_keys) != routine_count:
            errs.append(f"루틴 조각 {len(routine_keys)}개 ≠ meta.routine_count "
                        f"{routine_count} — 유실·과잉 거부")
        else:
            for i in range(routine_count):
                key = f"routine:{i}"
                if key not in chunks:
                    errs.append(f"루틴 조각 결번: {key} — 반쪽 복원 거부")
                    break
                profile["routines"].append(chunks[key])

        # meta가 참조하지 않는 조각은 조용히 버리지 않는다 — 미지 종류뿐 아니라
        # device_refs 밖의 잉여 device:* 조각까지 거부한다(그렇지 않으면 접두사만
        # 맞는 잉여 조각이 검사를 통과하고 편입도 안 된 채 소멸한다). consumed는
        # 상한(위)으로 이미 유계라 집합 구성이 폭발하지 않는다.
        consumed = ({"meta"}
                    | {f"device:{r}" for r in refs}
                    | {f"routine:{i}" for i in range(routine_count)})
        for k in chunks:
            if k not in consumed:
                errs.append(f"참조되지 않은/미지 조각 — 거부"
                            f"({type(k).__name__} len={len(str(k))})")

        if errs:
            return None, errs

        errs = validate_profile(profile)          # 와이어 불신 — 병합 후 재검증
        if errs:
            return None, errs
        return profile, []
    except Exception as e:   # fail-closed
        return None, [f"병합 내부 오류({type(e).__name__}) — 거부"]


# ---------- 캐리어 왕복 — 온바디 영속화·복원 (Story 3.1) ----------
# 캐리어는 인자로 주입받는다 — storage는 어떤 캐리어 구현도 import하지 않는다
# (1.3 경계: 벤더는 물론 참조 어댑터도 여기서 고정하지 않는다).
def persist_to_carrier(profile, carrier):
    """프로필을 저장 조각으로 나눠 캐리어에 새긴다. 반환 errors(빈 리스트 = 성공).

    조각은 개별 직렬화(JSON UTF-8 compact — 기준 표현)해 {키: bytes}로 넘긴다.
    캐리어 put_records가 원자적이므로(한계 초과 시 배치 전체 거부) 반쪽 저장은
    생기지 않는다.
    """
    try:
        errs = validate_profile(profile)          # 검증 안 거친 프로필은 와이어로 안 나간다
        if errs:
            return errs
        records = {}
        for name, obj in split_chunks(profile).items():
            try:
                records[name] = _dumps(obj)
            except Exception as e:
                errs.append(f"조각 {name!s:.32} 직렬화 실패({type(e).__name__})")
        if errs:
            return errs
        return carrier.put_records(records)
    except Exception as e:   # fail-closed
        return [f"영속화 내부 오류({type(e).__name__}) — 거부"]


def restore_from_carrier(carrier):
    """캐리어 레코드만으로 프로필을 복원한다. 반환 (profile | None, errors).

    **재등록 절차가 없다** — 이 함수는 캐리어를 읽고 병합·검증할 뿐, 기기를
    새로 등록하거나 device_ref를 발급하는 경로가 존재하지 않는다(FR4).
    서버·네트워크 코드도 없다 — AC3는 참은 게 아니라 개입할 자리가 없는 것이다.

    meta를 먼저 읽어 필요한 키 목록을 알아내고, 전부 모이면 merge_chunks로
    병합한다. 하나라도 없으면 (None, errors) — 캐리어 get_records 계약(반쪽
    결과 없음)을 그대로 잇는다.
    """
    try:
        got, errs = carrier.get_records(["meta"])
        if errs:
            return None, errs
        meta_obj, errs = _load_chunk(got["meta"], "meta")
        if errs:
            return None, errs
        refs = meta_obj.get("device_refs")
        count = meta_obj.get("routine_count")
        if not isinstance(refs, list) or isinstance(count, bool) \
                or not isinstance(count, int) or count < 0:
            return None, ["meta 조각이 병합 계약을 만족하지 않음 — 복원 불가"]
        # 상한을 name 생성 **전에** 강제한다 — 이 검사가 없으면 위조 meta의
        # routine_count(수십 바이트 payload로 MAX_WIRE_BYTES를 통과) 하나가
        # range(count)를 즉시 전개시켜 워치급 메모리를 고갈시킨다(정수 증폭 DoS).
        if len(refs) > MAX_DEVICES or count > MAX_ROUTINES:
            return None, [f"복원 규모 초과: 기기 {len(refs)}/{MAX_DEVICES}, "
                          f"루틴 {count}/{MAX_ROUTINES} — 파싱 전 거부"]

        names = ([f"device:{r}" for r in refs] +
                 [f"routine:{i}" for i in range(count)])
        chunks = {"meta": meta_obj}
        if names:
            got, errs = carrier.get_records(names)
            if errs:
                return None, errs                 # 반쪽 결과 없음 — 그대로 전파
            for name, payload in got.items():
                obj, errs = _load_chunk(payload, name)
                if errs:
                    return None, errs
                chunks[name] = obj
        return merge_chunks(chunks)
    except Exception as e:   # fail-closed
        return None, [f"복원 내부 오류({type(e).__name__}) — 거부"]


def _load_chunk(payload, name):
    """조각 bytes → 객체. 반환 (obj | None, errors). deserialize와 같은 불신 계보 —
    단 조각은 프로필 전체가 아니라서 validate_profile 대신 구조 검사만 하고,
    전체 검증은 merge_chunks 이후 한 번에 한다."""
    if not isinstance(payload, (bytes, bytearray)):
        return None, [f"조각 {name!s:.32}: bytes가 아님({type(payload).__name__})"]
    if len(payload) > MAX_WIRE_BYTES:
        return None, [f"조각 {name!s:.32}: {len(payload):,}B 상한 초과 — 파싱 거부"]
    try:
        obj = json.loads(payload.decode("utf-8"),
                         object_pairs_hook=_no_duplicate_keys)
    except _DuplicateKey as e:
        return None, [f"조각 {name!s:.32}: 중복 키 {e.args[0]} — 거부"]
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as e:
        return None, [f"조각 {name!s:.32}: 파싱 실패({type(e).__name__})"]
    if not isinstance(obj, dict):
        return None, [f"조각 {name!s:.32}: 객체가 아님({type(obj).__name__})"]
    return obj, []


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

    파티 결정(2026-07-22): 판정 기준은 **기기 단위 분할된 조각**이다.
      per_key_ok = 모든 조각이 BUDGET_PER_KEY(보수 4,096B) 안에 들어가는가
      largest_chunk = 가장 큰 조각과 그 이름 (초과 시 원인 지목)
    전체 크기(total_bytes)도 참고로 낸다 — 총량 예산 대비 판정용.

    검증 미통과 프로필에도 리포트가 나온다(초과 원인 진단이 목적).
    측정 실패는 0이 아니라 None으로 전파하고 errors에 남긴다(fail-closed).
    """
    errors = []
    rep = {
        "total_bytes": None,
        "chunk_bytes": {},          # {키이름: 바이트}
        "largest_chunk": None,      # (키이름, 바이트)
        "largest_chunk_bytes": None,
        "budget_per_key": BUDGET_PER_KEY,
        "per_key_ok": None,         # 모든 조각이 예산 내인가
        "n_keys": None,
        "bytes_per_device": None,
        "bytes_per_routine": None,
        "total_within_budget": None,
        "ble_chunks": None,
    }
    if not isinstance(profile, dict):
        errors.append(f"프로필이 객체가 아님({type(profile).__name__})")
        return rep, errors
    try:
        total = _safe_len(profile)
        rep["total_bytes"] = total
        if total is None:
            errors.append("전체 직렬화 실패 — 크기 측정 불가(직렬화 불가 값 포함)")

        chunks = split_chunks(profile)
        rep["n_keys"] = len(chunks)
        sizes = {}
        for name, obj in chunks.items():
            b = _safe_len(obj)
            sizes[name] = b
            if b is None:
                errors.append(f"조각 {name!r} 직렬화 실패 — 크기 측정 불가")
        rep["chunk_bytes"] = sizes

        measured = {k: v for k, v in sizes.items() if v is not None}
        if measured:
            name = max(measured, key=measured.get)
            rep["largest_chunk"] = name
            rep["largest_chunk_bytes"] = measured[name]
            # 조각 하나라도 측정 실패면 per_key_ok는 단정하지 않는다(None).
            if len(measured) == len(sizes):
                rep["per_key_ok"] = all(v <= BUDGET_PER_KEY for v in measured.values())

        n_dev = len([d for d in profile.get("devices", [])
                     if isinstance(d, dict)]) if isinstance(
                        profile.get("devices"), list) else 0
        dev_chunks = [v for k, v in measured.items() if k.startswith("device:")]
        if n_dev and dev_chunks:
            rep["bytes_per_device"] = sum(dev_chunks) / n_dev
        rou_chunks = [v for k, v in measured.items() if k.startswith("routine:")]
        if rou_chunks:
            rep["bytes_per_routine"] = sum(rou_chunks) / len(rou_chunks)

        if total is not None:
            rep["total_within_budget"] = total <= BUDGET_STORAGE_TOTAL
            if BLE_MTU > 0:
                rep["ble_chunks"] = math.ceil(total / BLE_MTU)
    except Exception as e:   # fail-closed
        errors.append(f"리포트 내부 오류({type(e).__name__}: {e})")
    return rep, errors
