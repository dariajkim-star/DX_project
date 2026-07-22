# -*- coding: utf-8 -*-
"""홈 프로필 스키마 (v1.0.0) — Story 1.1, 리뷰 반영 v2.

설계 근거: docs/planning-artifacts/epics.md#Story 1.1
       docs/implementation-artifacts/1-1-home-profile-schema.md (리뷰 평결 포함)

2026-07-22 Code Review Crew 평결로 재작성됨. v1의 구멍:
키만 검사(값 PII 통과)·영어 금지어뿐·null이 검증 스킵·unhashable/재귀 크래시가
PII 스캔 선점·중첩 미지 키 자유·웰니스 옆문(settings). 전부 아래로 봉인.

불변 원칙:
  1. 식별자 차단은 **구조로** 한다 — 사람이 자유 문자열을 쓸 자리를 없앤다.
     스키마 통제 키는 전부 화이트리스트, device_ref·setting_key는 ASCII 토큰 형식,
     자유 텍스트가 남는 값에는 PII 패턴 스캔(이메일·전화·주민번호·한국어 조각).
     이것은 방어선의 총합이지 수학적 증명이 아니다 — 문서에도 그렇게만 적는다.
  2. 웰니스는 예약만 — reserved_wellness는 **필수이며 항상 빈 객체**(키를 빼는
     우회 봉쇄). settings의 웰니스성 키(sleep·hrv·bp_ 등)도 거부한다(옆문 봉쇄).
     해석·판단 코드는 이 모듈에 존재하지 않는다(NFR5, 의료 규제).
  3. 조용한 통과 금지 — 미지 키는 **모든 레벨**에서 거부. null은 스킵이 아니라
     위반. 모르는 버전 거부. 검증기 내부 오류도 통과가 아니라 거부(fail-closed).
  4. validate_profile()은 **어떤 입력에도 예외를 던지지 않는다.** 이 계약은
     장식이 아니다 — 호출자가 try/except로 감싸는 순간 PII 스캔이 통째로
     증발하는 사고(v1)를 막는 방어선이다.
  5. 포맷 중립 — 순수 dict. 표준 라이브러리만 사용(캐리어 중립 NFR3:
     이 표현은 워치급 Monkey C로 이식된다).

버전·마이그레이션: SUPPORTED_VERSIONS 밖은 전부 거부한다. 구버전 프로필을
"받아서 마이그레이션"할지 "거부"할지는 **미결정 설계 사항**이다(리뷰 F5) —
v1의 MIGRATIONS 빈 레지스트리는 아무도 읽지 않는 장식이라 삭제했다.
결정이 내려지면 is_supported의 허용 범위와 변환 경로를 그때 함께 설계한다.

전송 제약 (Story 1.2·Epic 2가 상속):
  Connect IQ Application.Storage 총 ~128KB / 키당 ~8KB
  Connect IQ BLE 특성 ~20바이트 MTU, long write 미지원
  → devices[]·routines[] 원소가 각각 독립 직렬화되는 평평한 구조 유지.
"""
import hashlib
import math
import re
import unicodedata

SCHEMA_VERSION = "1.0.0"
SUPPORTED_VERSIONS = frozenset({"1.0.0"})

TOP_LEVEL_KEYS = (
    "schema_version",
    "devices",
    "settings",
    "routines",
    "reserved_wellness",
)
# v2: reserved_wellness도 필수 — 키를 빼면 NFR5 검사가 스킵되던 우회(리뷰 F4) 봉쇄
REQUIRED_TOP_LEVEL_KEYS = TOP_LEVEL_KEYS

# 스키마 통제 키 화이트리스트 — 이 밖의 키는 어느 레벨에서든 거부(NFR6 전 레벨화)
DEVICE_KEYS = frozenset({"device_ref", "device_type", "capabilities"})
DEVICE_REQUIRED = ("device_ref", "device_type")
ROUTINE_KEYS = frozenset({"trigger", "actions"})
TRIGGER_KEYS = frozenset({"type", "params"})
ACTION_KEYS = frozenset({"device_ref", "setting_key", "value"})
ACTION_REQUIRED = ("device_ref", "setting_key", "value")

# device_ref: 생성된 불투명 토큰만 허용 — 사람이 "엄마 방 에어컨"이나 이메일을
# 쓸 수 있는 자유 문자열이 곧 PII 통로였다(리뷰 F1). 표시용 이름이 필요해지면
# 그것은 '프로필 밖'(기기 로컬)의 문제다.
TOKEN_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
# setting_key·device_type·capability·trigger type: ASCII 소문자 토큰 —
# 한국어 키·호모글리프 키(키릴 а 등)가 형식 단계에서 전부 죽는다(리뷰 F2)
KEY_RE = re.compile(r"^[a-z0-9][a-z0-9_]{0,31}$")

# 식별자성 키 조각 — 영어 + 한국어(리뷰 F2: 영어만으로는 한국어 제품에서 무의미)
FORBIDDEN_KEY_FRAGMENTS = (
    "name", "account", "email", "phone", "user_id", "userid",
    "birth", "address", "contact", "ssn", "gender", "owner",
    "resident", "alias", "nickname",
    "이름", "계정", "이메일", "메일주소", "전화", "연락처", "주소",
    "생년", "생일", "주민", "성별", "소유자",
)
# 가구 식별·위치 프리미티브 — ssid+좌표는 이메일보다 강한 식별자다(리뷰 Vex)
FORBIDDEN_EXACT_KEYS = frozenset({
    "ssid", "mac", "serial", "imei", "lat", "lon",
    "latitude", "longitude", "geo", "gps",
})
# 웰니스성 키 조각 — settings 옆문 봉쇄(리뷰 F4). NFR5: 진단·의료 판단 배제
WELLNESS_KEY_FRAGMENTS = (
    "sleep", "wellness", "health", "heart", "hrv", "blood", "spo2",
    "stress", "body_fat", "bp_", "calorie", "weight", "pulse", "glucose",
)

# 값 PII 패턴 — v1은 값을 한 번도 안 읽었다(리뷰 F1). 완전한 목록일 수 없는
# 방어선이며, 문서에는 '스캔'이라고만 적지 '증명'이라고 적지 않는다.
_PII_VALUE_RES = (
    ("이메일", re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")),
    ("전화번호", re.compile(r"01[016789][-\s]?\d{3,4}[-\s]?\d{4}")),
    ("주민등록번호", re.compile(r"\d{6}[-\s]?[1-4]\d{6}")),
)
_PII_VALUE_FRAGMENTS = ("이름", "전화번호", "주민등록", "성명", "연락처")

MAX_SCAN_DEPTH = 24   # json.loads는 ~2000, 재귀 스캔은 1000에서 죽는다(리뷰 F3·4)
_MAX_STR = 256        # 폭주 문자열 상한
# 2차 리뷰(Boundary F4): _MAX_STR이 정수로 우회됐다 — 4,000자리 정수(4,012B)가
# 값 하나로 통과. 수치 값의 자릿수도 제한한다.
_MAX_INT_DIGITS = 20  # int64 범위를 덮는다. 가전 설정값에 이보다 큰 수는 없다.
_VERSION_SHOW_RE = re.compile(r"[0-9A-Za-z.]{1,16}")


def _redact(v) -> str:
    """신뢰 불가 값을 위반 메시지에 넣지 않는다 (2차 리뷰 Vex F3).

    v1은 거부한 값을 그대로 메시지에 찍었다 —
    `device_type는 ... 현재 'hong.gildong@gmail.com'` 식으로. 이 목록은
    호출자가 로그에 남기는 물건이라, **게이트가 막은 PII를 로그가 흘렸다.**
    타입·길이·해시 앞 4자리만 남긴다(같은 값인지 대조는 가능, 복원은 불가).
    """
    if isinstance(v, str):
        h = hashlib.sha256(v.encode("utf-8", "surrogatepass")).hexdigest()[:4]
        return f"<str len={len(v)} #{h}>"
    if isinstance(v, (int, float, bool)):
        return f"<{type(v).__name__}>"
    return f"<{type(v).__name__}>"


def _bad_chars(text: str) -> str:
    """제로폭·서식 제어·서로게이트 검출 (2차 리뷰 Vex F1 / Boundary F2).

    NFKC는 전각은 접지만 Cf(format) 문자는 남긴다. 그런데 PII 정규식은
    문자가 인접해야 매치되므로 `hong﻿@gmail.com` 한 방에 죽는다.
    Cs(surrogate)는 UTF-8 인코딩 자체가 불가능해 통과 후 저장·측정이 깨진다.
    설정 키·값에 이런 문자가 필요한 경우는 없다 — 통째로 거부한다.
    """
    for ch in text:
        cat = unicodedata.category(ch)
        if cat in ("Cf", "Cs"):
            return f"U+{ord(ch):04X}({cat})"
    return ""


def new_profile() -> dict:
    """현재 스키마 버전이 각인된 빈 프로필. 호출마다 새 컨테이너."""
    return {
        "schema_version": SCHEMA_VERSION,
        "devices": [],
        "settings": {},
        "routines": [],
        "reserved_wellness": {},
    }


def is_supported(version) -> bool:
    """지원 버전 판정. 모르는 값·타입은 전부 False."""
    return isinstance(version, str) and version in SUPPORTED_VERSIONS


# ---------- 식별자 스캔 (FR7 방어선) ----------
# 스키마가 스스로 선언한 키 — 식별자·웰니스 스캔 면제 대상.
# reserved_wellness가 'wellness' 조각에 걸리는 자기모순 방지. 여기 넣을 수 있는
# 것은 이 파일의 화이트리스트 상수에 이미 존재하는 키뿐이다.
_SCHEMA_OWN_KEYS = frozenset(TOP_LEVEL_KEYS) | DEVICE_KEYS | ROUTINE_KEYS \
    | TRIGGER_KEYS | ACTION_KEYS


def _key_violations(key, path) -> list:
    if key in _SCHEMA_OWN_KEYS:
        return []
    errs = []
    raw = str(key)
    red = _redact(raw)          # 키 자체가 PII 운반체일 수 있다 — 그대로 찍지 않는다
    bad = _bad_chars(raw)
    if bad:
        errs.append(f"{path}.{red}: 키에 제어·서로게이트 문자 {bad} — 거부")
    k = unicodedata.normalize("NFKC", raw)
    if not k.isascii():
        # 한국어 키·호모글리프 키를 개별 단어 목록으로 쫓는 대신 통째로 거부.
        # 스키마 통제 키는 전부 ASCII다 — 비ASCII 키는 정의상 스키마 밖이다.
        errs.append(f"{path}.{red}: 비ASCII 키 — 스키마 통제 키가 아님(FR7 방어)")
    k_l = k.lower()
    # 보고되는 조각은 우리 상수 목록에서 온 것이라 안전하다 — 키 원문은 재작성.
    for frag in FORBIDDEN_KEY_FRAGMENTS:
        if frag in k_l:
            errs.append(f"{path}.{red}: 식별자성 키('{frag}') — FR7 위반")
            break
    if k_l in FORBIDDEN_EXACT_KEYS:
        errs.append(f"{path}.{red}: 가구 식별·위치 키('{k_l}') — FR7 위반")
    for frag in WELLNESS_KEY_FRAGMENTS:
        if frag in k_l:
            errs.append(f"{path}.{red}: 웰니스성 키('{frag}') — NFR5 위반")
            break
    return errs


def _value_violations(value, path) -> list:
    if not isinstance(value, str):
        return []
    bad = _bad_chars(value)
    errs = []
    if bad:
        # 제로폭 한 글자로 아래 PII 정규식이 전부 무력화된다(Vex F1) — 먼저 거부.
        errs.append(f"{path}: 값에 제어·서로게이트 문자 {bad} — 거부(PII 은닉 통로)")
    v = unicodedata.normalize("NFKC", value)
    if len(v) > _MAX_STR:
        errs.append(f"{path}: 문자열 {len(v)}자 — 상한 {_MAX_STR}자 초과")
    for label, rx in _PII_VALUE_RES:
        if rx.search(v):
            errs.append(f"{path}: 값에 {label} 패턴 — FR7 위반")
    for frag in _PII_VALUE_FRAGMENTS:
        if frag in v:
            errs.append(f"{path}: 값에 식별자성 문구('{frag}') — FR7 위반")
            break
    return errs


def find_identifier_violations(obj, _path="profile", _depth=0, _seen=None) -> list:
    """키와 **값**을 재귀 스캔해 식별자·웰니스 위반 위치 목록을 반환한다.

    빈 리스트 = 미검출. 예외를 던지지 않는다 — 깊이 초과·순환 참조도
    위반으로 보고한다(fail-closed). v1의 이름 assert_no_identifiers는
    raise하지 않으면서 assert_를 자칭하는 거짓 이름이라 개명했다(리뷰 Yui).
    """
    if _seen is None:
        _seen = set()
    if _depth > MAX_SCAN_DEPTH:
        return [f"{_path}: 중첩 깊이 {MAX_SCAN_DEPTH} 초과 — 스캔 불가, 프로필 거부"]
    found = []
    if isinstance(obj, dict):
        if id(obj) in _seen:
            return [f"{_path}: 순환 참조 — 스캔 불가, 프로필 거부"]
        _seen.add(id(obj))
        for k, v in obj.items():
            found += _key_violations(k, _path)
            found += _value_violations(v, f"{_path}.{k}")
            found += find_identifier_violations(v, f"{_path}.{k}", _depth + 1, _seen)
        _seen.discard(id(obj))
    elif isinstance(obj, list):
        if id(obj) in _seen:
            return [f"{_path}: 순환 참조 — 스캔 불가, 프로필 거부"]
        _seen.add(id(obj))
        for i, v in enumerate(obj):
            found += _value_violations(v, f"{_path}[{i}]")
            found += find_identifier_violations(v, f"{_path}[{i}]", _depth + 1, _seen)
        _seen.discard(id(obj))
    return found


# ---------- 구조 검증 헬퍼 (전부 목록 반환, 예외 없음) ----------
def _is_scalar(v) -> bool:
    if isinstance(v, bool) or isinstance(v, str):
        return True
    if isinstance(v, int):
        # 2차 리뷰 Boundary F4: _MAX_STR이 정수로 우회됐다.
        # 4,000자리 정수 하나가 4,012B — 키 예산의 61%.
        return len(str(abs(v))) <= _MAX_INT_DIGITS
    if isinstance(v, float):
        return math.isfinite(v)   # NaN·Inf는 JSON 밖 — 직렬화 게이트(리뷰 F6)
    return False


def _check_token(v, path, name) -> list:
    if not isinstance(v, str) or not TOKEN_RE.fullmatch(v):
        return [f"{path} {name}는 토큰 형식([a-z0-9_-] 1~32자) 문자열이어야 함 — "
                f"현재 {_redact(v)}"]
    return []


def _check_keyname(v, path, name) -> list:
    # v1은 거부한 값을 {v!r}로 그대로 찍었다 — device_type·setting_key는
    # 공격자 통제 문자열이라 거부 메시지가 곧 PII 유출이었다(2차 리뷰 Vex F3).
    if not isinstance(v, str) or not KEY_RE.fullmatch(v):
        return [f"{path} {name}는 ASCII 소문자 키 형식이어야 함 — "
                f"현재 {_redact(v)}"]
    return []


def _check_dict_shape(obj, allowed, required, path) -> list:
    """dict 여부 + 미지 키 + 필수 키. dict가 아니면 그 사유만 반환."""
    if not isinstance(obj, dict):
        return [f"{path}가 객체가 아님({type(obj).__name__})"]
    errs = [f"{path} 미지의 키: {_redact(k)} — 조용한 확장 금지(NFR6)"
            for k in obj if k not in allowed]
    errs += [f"{path} 필수 키 누락: {k}" for k in required if k not in obj]
    return errs


def _validate_top_level(profile) -> list:
    errs = [f"필수 최상위 키 누락: {k}"
            for k in REQUIRED_TOP_LEVEL_KEYS if k not in profile]
    errs += [f"미지의 최상위 키: {k} — 조용한 확장 금지(NFR6)"
             for k in profile if k not in TOP_LEVEL_KEYS]
    if "schema_version" in profile:
        v = profile["schema_version"]
        if not is_supported(v):
            # v1은 {v!r}로 무제한 에코했다 — 5MB 페이로드가 500만자 에러 문자열을
            # 만들었고, 이 문자열은 PII 스캔을 한 번도 안 거친다(2차 리뷰 Vex F4).
            # 버전처럼 생긴 것(숫자·영문·점)만 원문 노출. 하이픈이 섞이면
            # '010-1234-5678'이 버전 자리에 실려 그대로 로그로 나간다.
            shown = v if (isinstance(v, str) and _VERSION_SHOW_RE.fullmatch(v))                 else _redact(v)
            errs.append(f"지원하지 않는 스키마 버전: {shown} "
                        f"(지원: {sorted(SUPPORTED_VERSIONS)})")
    return errs


def _validate_devices(devices):
    """반환: (refs 또는 None, errs). refs가 None이면 참조 검사 불가 상태 —
    v1은 이때 조용히 스킵했지만(리뷰 Boundary F1) 이제 그 자체가 위반이다."""
    if devices is None:
        return None, ["devices가 null — 스킵이 아니라 위반(배열이어야 함)"]
    if not isinstance(devices, list):
        return None, [f"devices는 배열이어야 함({type(devices).__name__})"]
    errs, refs = [], set()
    for i, d in enumerate(devices):
        path = f"devices[{i}]"
        shape = _check_dict_shape(d, DEVICE_KEYS, DEVICE_REQUIRED, path)
        errs += shape
        if not isinstance(d, dict):
            continue
        ref = d.get("device_ref")
        tok = _check_token(ref, path, "device_ref")
        errs += tok
        if not tok:
            if ref in refs:
                errs.append(f"{path} device_ref 중복: {_redact(ref)} — "
                            f"복원 시 매칭이 비결정적이 됨")
            refs.add(ref)
        if "device_type" in d:
            errs += _check_keyname(d["device_type"], path, "device_type")
        caps = d.get("capabilities", [])
        if not isinstance(caps, list):
            errs.append(f"{path}.capabilities는 배열이어야 함")
        else:
            for j, c in enumerate(caps):
                errs += _check_keyname(c, f"{path}.capabilities[{j}]", "항목")
    return refs, errs


def _validate_settings(settings, refs) -> list:
    if settings is None:
        return ["settings가 null — 스킵이 아니라 위반(객체여야 함)"]
    if not isinstance(settings, dict):
        return [f"settings는 객체여야 함({type(settings).__name__})"]
    errs = []
    # 경로에 키 원문을 넣지 않는다 — settings 키는 사용자 통제 문자열이라
    # 거부 메시지가 곧 PII 유출이었다(2차 리뷰 Vex F3·F6). 서수로 지목하면
    # 진단은 되고 원문은 새지 않는다.
    for idx, (ref, kv) in enumerate(settings.items()):
        path = f"settings[#{idx}]"
        errs += _check_token(ref, path, "키(device_ref)")
        if refs is not None and isinstance(ref, str) and TOKEN_RE.fullmatch(ref) \
                and ref not in refs:
            errs.append(f"{path}의 device_ref {_redact(ref)}가 devices에 없음")
        if not isinstance(kv, dict):
            errs.append(f"{path}는 객체여야 함({type(kv).__name__})")
            continue
        for k, v in kv.items():
            errs += _check_keyname(k, path, "setting_key")
            if not _is_scalar(v):
                errs.append(f"{path}.{_redact(k)} 값은 스칼라(str/int/float/bool, "
                            f"유한값·자릿수 {_MAX_INT_DIGITS} 이내)여야 함 — "
                            f"현재 {type(v).__name__}")
    return errs


def _validate_action(a, refs, path) -> list:
    errs = _check_dict_shape(a, ACTION_KEYS, ACTION_REQUIRED, path)
    if not isinstance(a, dict):
        return errs
    ref = a.get("device_ref")
    tok = _check_token(ref, path, "device_ref")
    errs += tok
    if not tok and refs is not None and ref not in refs:
        errs.append(f"{path}가 미등록 기기 {ref!r}를 참조")
    if "setting_key" in a:
        errs += _check_keyname(a["setting_key"], path, "setting_key")
    if "value" in a and not _is_scalar(a["value"]):
        errs.append(f"{path}.value는 스칼라여야 함")
    return errs


def _validate_routines(routines, refs) -> list:
    if routines is None:
        return ["routines가 null — 스킵이 아니라 위반(배열이어야 함)"]
    if not isinstance(routines, list):
        return [f"routines는 배열이어야 함({type(routines).__name__})"]
    errs = []
    for i, r in enumerate(routines):
        path = f"routines[{i}]"
        errs += _check_dict_shape(r, ROUTINE_KEYS, ("trigger", "actions"), path)
        if not isinstance(r, dict):
            continue
        trigger = r.get("trigger")
        if "trigger" in r:
            errs += _check_dict_shape(trigger, TRIGGER_KEYS, ("type",),
                                      f"{path}.trigger")
            if isinstance(trigger, dict):
                if "type" in trigger:
                    errs += _check_keyname(trigger["type"], f"{path}.trigger", "type")
                params = trigger.get("params", {})
                if not isinstance(params, dict):
                    errs.append(f"{path}.trigger.params는 객체여야 함")
                else:
                    for k, v in params.items():
                        errs += _check_keyname(k, f"{path}.trigger.params", "키")
                        if not _is_scalar(v):
                            errs.append(f"{path}.trigger.params.{k} 값은 "
                                        f"스칼라여야 함")
        actions = r.get("actions")
        if "actions" in r:
            if not isinstance(actions, list) or not actions:
                errs.append(f"{path}.actions는 비어있지 않은 배열이어야 함")
            else:
                for j, a in enumerate(actions):
                    errs += _validate_action(a, refs, f"{path}.actions[{j}]")
    return errs


def _validate_reserved_wellness(profile) -> list:
    if "reserved_wellness" not in profile:
        return []   # 누락은 _validate_top_level이 이미 보고
    rw = profile["reserved_wellness"]
    if not isinstance(rw, dict):
        return [f"reserved_wellness는 객체여야 함({type(rw).__name__})"]
    if rw:
        return ["reserved_wellness는 예약 필드 — 값을 담을 수 없다"
                f"(NFR5: 진단·의료 판단 기능 배제). 발견된 키 {len(rw)}개: "
                f"{[_redact(k) for k in list(rw)[:3]]}"]
    return []


def validate_profile(profile) -> list:
    """프로필 검증. 위반 사유 목록 반환(빈 리스트 = 통과).

    계약: **어떤 입력에도 예외를 던지지 않는다.** v1은 unhashable ref·깊은
    중첩에서 크래시했고, 그 크래시가 마지막 줄의 PII 스캔을 선점했다(리뷰 F3) —
    try/except로 감싼 호출자에서 PII 미검사 프로필이 통과하는 경로였다.
    v2는 ① 식별자 스캔을 **먼저** 돌리고 ② 구조 검사를 전부 total function으로
    만들고 ③ 그래도 남는 내부 오류는 통과가 아니라 거부로 처리한다(fail-closed).
    """
    if not isinstance(profile, dict):
        return [f"프로필 최상위가 객체가 아님({type(profile).__name__})"]
    errs = []
    try:
        # ① FR7/NFR5 스캔 먼저 — 구조가 어떻게 깨져 있어도 이건 실행된다
        errs += find_identifier_violations(profile)
        # ② 구조 검증
        errs += _validate_top_level(profile)
        refs, dev_errs = _validate_devices(profile.get("devices")) \
            if "devices" in profile else (None, [])
        errs += dev_errs
        if "settings" in profile:
            errs += _validate_settings(profile["settings"], refs)
        if "routines" in profile:
            errs += _validate_routines(profile["routines"], refs)
        errs += _validate_reserved_wellness(profile)
    except Exception as e:   # 계약 방어: 내부 오류 = 거부, 통과 아님
        errs.append(f"검증기 내부 오류({type(e).__name__}: {e}) — "
                    f"프로필 거부(fail-closed)")
    return errs
