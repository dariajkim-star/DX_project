# -*- coding: utf-8 -*-
"""명령 와이어 계약 — 인코딩·디코딩 (Story 2.1).

기준 표현은 **JSON UTF-8 compact** — 프로필(home_profile.storage)과 동일하다.
새 포맷을 발명하지 않는다: 이 표현은 워치급 Monkey C로 이식되며 파서를 직접
써야 하는 대상이다(PROFILE_SCHEMA §5).

형식: {"v": 1, "device_ref": "<ref>", "set": {capability: value, ...}}

⚠️ **BLE 청킹(20B MTU 재조립)은 이 모듈 밖**이다 — 전송 바인딩과 2.2의 일이다.
여기서는 '완성된 bytes 1개'만 다룬다.

계승 계약(deserialize와 동일 계보): 크기 상한을 파싱 **전에** 적용, BOM 허용,
중복 키 거부(파서 차이 공격), 버전 불일치는 명시 거부, 어떤 입력에도 예외 금지.
"""
import json

__all__ = ["COMMAND_VERSION", "MAX_COMMAND_BYTES",
           "encode_command", "decode_command"]

COMMAND_VERSION = 1

# 명령 1건의 크기 상한.
# ⚠️ storage.MAX_WIRE_BYTES(131,072B)를 쓰지 않는다 — 그건 **프로필 전체**의
# 상한이다. 명령 1건은 기기 참조 + 설정 몇 개라 수백 바이트 규모이며, 20B MTU로
# 재조립되는 입력에 128KB를 허용하면 6,500청크짜리 메모리 고갈 창구를 여는 것이다
# (1.2 2차 리뷰 Vex F5가 막았던 병의 재판).
# 근거: 최악 명령(ref 32자 + capability 10종 전부 + 열거값 최대 길이)을 실측해
# 그 위에 여유를 둔 값. test_max_command_bytes_covers_worst_case가 이 관계를 고정한다.
MAX_COMMAND_BYTES = 1024


class _DuplicateKey(ValueError):
    """JSON 객체에 중복 키가 있었다 (storage._no_duplicate_keys와 같은 방어)."""


def _no_duplicate_keys(pairs):
    seen = set()
    for k, _ in pairs:
        if k in seen:
            # 키 원문은 메시지에 넣지 않는다 — 그 자체가 PII 운반체일 수 있다
            raise _DuplicateKey(f"<str len={len(str(k))}>")
        seen.add(k)
    return dict(pairs)


def encode_command(cmd):
    """명령 객체 → bytes. 반환 (bytes | None, errors). 예외 금지."""
    try:
        if not isinstance(cmd, dict):
            return None, [f"명령은 객체여야 함({type(cmd).__name__})"]
        data = json.dumps(cmd, ensure_ascii=False,
                          separators=(",", ":")).encode("utf-8")
        return data, []
    except Exception as e:   # fail-closed (직렬화 불가 값 포함)
        return None, [f"인코딩 실패({type(e).__name__}) — 거부"]


def decode_command(data):
    """bytes → 명령 객체. 반환 (cmd | None, errors). 예외 금지.

    와이어 불신: 크기 → 디코딩 → 파싱 → 버전 → 구조 순으로 좁혀 간다.
    오류 문구에 수신 값 원문을 싣지 않는다.
    """
    if not isinstance(data, (bytes, bytearray)):
        return None, [f"입력은 bytes여야 함({type(data).__name__})"]
    if len(data) > MAX_COMMAND_BYTES:
        # 파싱 전에 자른다 — decode+loads가 메모리에 올라온 뒤 거부하면 늦다
        return None, [f"명령 {len(data):,}B — 상한 {MAX_COMMAND_BYTES:,}B 초과, 파싱 거부"]
    try:
        raw = bytes(data)
        if raw.startswith(b"\xef\xbb\xbf"):
            raw = raw[3:]              # BOM 허용(제거 후 파싱)
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as e:
            return None, [f"UTF-8 디코딩 실패({e.reason})"]
        try:
            obj = json.loads(text, object_pairs_hook=_no_duplicate_keys)
        except _DuplicateKey as e:
            return None, [f"중복 키 {e.args[0]} — 파서 차이 공격 방지로 거부"]
        except (json.JSONDecodeError, RecursionError) as e:
            return None, [f"JSON 파싱 실패({type(e).__name__})"]
        if not isinstance(obj, dict):
            return None, [f"최상위가 객체가 아님({type(obj).__name__})"]

        version = obj.get("v")
        if version != COMMAND_VERSION:
            # 버전 값 원문을 에코하지 않는다 — 검증 안 거친 문자열이 로그로 나간다
            shown = version if isinstance(version, int) else f"<{type(version).__name__}>"
            return None, [f"명령 버전 불일치: {shown} (기대 {COMMAND_VERSION}) — "
                          f"마이그레이션 미지원, 명시적 거부"]
        if not isinstance(obj.get("device_ref"), str):
            return None, ["device_ref 누락 또는 문자열 아님"]
        if not isinstance(obj.get("set"), dict):
            return None, ["set 누락 또는 객체 아님"]
        return obj, []
    except Exception as e:   # fail-closed
        return None, [f"디코딩 내부 오류({type(e).__name__}) — 거부"]
