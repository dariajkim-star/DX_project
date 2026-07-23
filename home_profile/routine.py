# -*- coding: utf-8 -*-
"""루틴 실행 — 프로필 → 명령 → 청킹 → 전송 (Story 2.2).

설계 근거: docs/planning-artifacts/epics.md#Story 2.2 (FR2)
       docs/implementation-artifacts/2-2-profile-driven-ble-command.md

이 모듈이 답하는 질문: **"손목의 프로필이 앱·서버 없이 집을 움직이는가"**(FR2).
1.1~1.3이 "무엇을 담는가"를, 2.1이 "받는 쪽"을 세웠고, 여기가 그 사이의 배선이다.

⚠️ **방향은 언제나 프로필 → (명령 bytes) → 가전이다.**
이 모듈은 `appliance_sim`을 import하지 않는다 — 제품 코드가 시뮬레이터에
의존하면 실가전으로 갈 때 통째로 뜯어야 한다. 명령 형식은 양쪽이 공유하는
계약이므로 여기서 **재선언**하고, 동기 여부는 테스트가 감시한다
(`test_command_shape_matches_wire_contract` — 2.1의 어휘 동기 감시와 같은 방식).

계승 계약: 예외 금지(fail-closed), 와이어 불신, 오류에 값 원문 금지,
원자성(부분 적용 없음).
"""
import json
import re

__all__ = [
    "COMMAND_VERSION",
    "CHUNK_HEADER_BYTES",
    "MAX_CHUNKS",
    "PAYLOAD_PER_CHUNK",
    "chunk",
    "reassemble",
    "routine_to_commands",
    "execute_routine",
]

# 2.1 wire 계약과 동기 (appliance_sim.wire.COMMAND_VERSION).
# import하지 않고 재선언하는 이유는 모듈 docstring 참조.
COMMAND_VERSION = 1

# 재조립 후 크기 상한도 동기 (appliance_sim.wire.MAX_COMMAND_BYTES).
_MAX_COMMAND_BYTES = 1024

# 안전 표시 정규식 — 스키마의 device_ref 토큰 형식과 동일
# (^[a-z0-9][a-z0-9_-]{0,31}$, PROFILE_SCHEMA §3).
#
# ⚠️ 리뷰(2026-07-22, Mary): v1은 "ascii + 영숫자(밑줄·하이픈 제거 후)"라는
# **다른 규칙**을 썼고, 그 결과 대문자(`"A_B"`)·숫자 시작(`"9dev"`)이 2.1에서는
# 거부되는데 여기서는 원문 표시됐다. 같은 방어를 두 곳에 다르게 구현한 것이며,
# `appliance_sim`을 import할 수 없어 복사한 것이 드리프트로 이어졌다
# (역방향 의존 금지의 대가 — Winston). 패턴을 2.1과 문자 그대로 일치시키고,
# 드리프트는 테스트가 감시한다(capability 어휘 동기 감시와 같은 방식).
_SAFE_SHOW_RE = re.compile(r"[a-z0-9][a-z0-9_-]{0,31}")


def _show(v) -> str:
    """오류 문구용 표시 — 1.3 P2 / 2.1 계보. 신뢰 불가 값은 원문을 싣지 않는다."""
    if isinstance(v, str):
        if _SAFE_SHOW_RE.fullmatch(v):
            return repr(v)
        return f"<str len={len(v)}>"
    return f"<{type(v).__name__}>"


# ---------- 루틴 → 명령 ----------
def routine_to_commands(profile, routine_index):
    """루틴 1개를 **기기별 명령 목록**으로 변환. 반환 (commands | None, errors).

    2.1의 명령 형식이 기기 단일(`{"v":1,"device_ref":…,"set":{…}}`)이므로,
    액션 3개가 기기 2대를 건드리면 명령은 2건이다.

    순서는 **결정적**이다(device_ref 정렬) — 같은 루틴이 같은 순서를 낸다.
    발표 재현성이 걸려 있고, 테스트가 순서를 단언할 수 있어야 한다.
    """
    try:
        if not isinstance(profile, dict):
            return None, [f"프로필이 객체가 아님({type(profile).__name__})"]
        routines = profile.get("routines")
        if not isinstance(routines, list):
            return None, [f"routines가 배열이 아님({type(routines).__name__})"]
        if not isinstance(routine_index, int) or isinstance(routine_index, bool):
            return None, [f"루틴 인덱스가 정수가 아님({type(routine_index).__name__})"]
        if not (0 <= routine_index < len(routines)):
            return None, [f"루틴 인덱스 {routine_index} 범위 밖 (0~{len(routines) - 1})"]

        routine = routines[routine_index]
        if not isinstance(routine, dict):
            return None, [f"루틴이 객체가 아님({type(routine).__name__})"]
        actions = routine.get("actions")
        if not isinstance(actions, list) or not actions:
            return None, ["루틴에 실행할 액션이 없음"]

        # 와이어 불신: 스키마가 이미 미등록 참조를 거부하지만, 와이어를 거친
        # 프로필은 다시 본다(deserialize가 재검증하는 것과 같은 이유).
        devices = profile.get("devices")
        if not isinstance(devices, list):
            return None, [f"devices가 배열이 아님({type(devices).__name__})"]
        known = {}
        for d in devices:
            if isinstance(d, dict) and isinstance(d.get("device_ref"), str):
                caps = d.get("capabilities")
                known[d["device_ref"]] = set(caps) if isinstance(caps, list) else set()

        errs = []
        grouped = {}
        for i, a in enumerate(actions):
            if not isinstance(a, dict):
                errs.append(f"액션 {i}: 객체가 아님({type(a).__name__})")
                continue
            ref, key = a.get("device_ref"), a.get("setting_key")
            if not isinstance(ref, str) or ref not in known:
                errs.append(f"액션 {i}: 미등록 기기 참조 {_show(ref)}")
                continue
            if not isinstance(key, str) or key not in known[ref]:
                # 기기가 선언하지 않은 capability로 명령을 만들면 시뮬레이터가
                # 거부한다 — 보내기 전에 잡는다
                errs.append(f"액션 {i}: 기기 {_show(ref)}에 없는 설정 {_show(key)}")
                continue
            if "value" not in a:
                errs.append(f"액션 {i}: value 누락")
                continue
            grouped.setdefault(ref, {})[key] = a["value"]

        if errs:
            return None, errs          # 원자성: 하나라도 틀리면 명령을 만들지 않는다

        commands = [{"v": COMMAND_VERSION, "device_ref": ref, "set": grouped[ref]}
                    for ref in sorted(grouped)]      # 결정적 순서
        return commands, []
    except Exception as e:   # fail-closed
        return None, [f"루틴 변환 내부 오류({type(e).__name__}) — 거부"]


# ---------- BLE 청킹 (20B MTU) ----------
# Connect IQ BLE 특성은 read/write 20바이트이며 long write 미지원(포럼발,
# PROFILE_SCHEMA §5). 명령 1건이 실측 50~72B이므로 **모든 명령이 청킹된다.**
#
# 헤더 2바이트: [seq(1)][total(1)]. 순번·총개수를 실어 순서 뒤바뀜·유실·중복을
# 탐지한다 — BLE는 순서를 보장하지 않는다.
CHUNK_HEADER_BYTES = 2
MAX_CHUNKS = 255                       # 헤더 1바이트의 한계 = 자연스러운 상한


def _payload_per_chunk(mtu: int) -> int:
    return mtu - CHUNK_HEADER_BYTES


PAYLOAD_PER_CHUNK = _payload_per_chunk(20)     # 18B — 헤더가 MTU를 먹는다


def chunk(data, mtu=20):
    """bytes → 청크 목록. 반환 **(chunks | None, errors)**. 예외 금지.

    청크당 유효 페이로드는 mtu - 2 바이트다.

    리뷰(2026-07-22, Amelia): v1은 실패 시 **빈 목록**을 반환했다. 이 저장소는
    1.1부터 전부 `(결과|None, errors)` 규약인데 여기만 예외였고, 그 결과
    호출자가 실패 사유 4종(비bytes·MTU 비정수·MTU가 헤더 이하·청크 수 초과)을
    구별하지 못해 `execute_routine`이 하나로 뭉개 보고했다 —
    2.1에서 BLE 오류 사유를 셋으로 쪼갠 것과 정확히 같은 병이다.
    """
    try:
        if not isinstance(data, (bytes, bytearray)):
            return None, [f"입력은 bytes여야 함({type(data).__name__})"]
        if not isinstance(mtu, int) or isinstance(mtu, bool):
            return None, [f"MTU는 정수여야 함({type(mtu).__name__})"]
        payload = _payload_per_chunk(mtu)
        if payload <= 0:
            return None, [f"MTU {mtu}B — 헤더 {CHUNK_HEADER_BYTES}B 이하라 "
                          f"실을 페이로드가 없음"]
        raw = bytes(data)
        total = max(1, (len(raw) + payload - 1) // payload)
        if total > MAX_CHUNKS:
            return None, [f"{len(raw):,}B는 청크 {total}개 — 헤더 표현 상한 "
                          f"{MAX_CHUNKS} 초과"]
        out = []
        for seq in range(total):
            body = raw[seq * payload:(seq + 1) * payload]
            out.append(bytes([seq, total]) + body)
        return out, []
    except Exception as e:   # fail-closed
        return None, [f"청킹 내부 오류({type(e).__name__}) — 거부"]


def reassemble(chunks):
    """청크 목록 → bytes. 반환 (bytes | None, errors). **예외 금지**.

    **적대적 입력을 가정한다** — BLE write는 누구나 보낼 수 있다:
      - 총개수 위조: 청크 1개가 "총 60000개"라 주장 → 수신 버퍼 고갈
      - 순번 결번·중복·범위 밖
      - 재조립 후 크기가 명령 상한 초과
    전부 예외 없이 거부한다. 완전 재조립 전에는 **아무것도 넘기지 않는다**
    (부분 적용 금지).
    """
    try:
        if not isinstance(chunks, (list, tuple)) or not chunks:
            return None, ["청크가 없음"]
        if len(chunks) > MAX_CHUNKS:
            return None, [f"청크 {len(chunks)}개 — 상한 {MAX_CHUNKS} 초과, 거부"]

        parts = {}
        total = None
        for i, c in enumerate(chunks):
            if not isinstance(c, (bytes, bytearray)):
                return None, [f"청크 {i}: bytes가 아님({type(c).__name__})"]
            if len(c) < CHUNK_HEADER_BYTES:
                return None, [f"청크 {i}: 헤더 부족({len(c)}B)"]
            seq, declared = c[0], c[1]
            if declared == 0:
                return None, [f"청크 {i}: 총개수 0 — 무효"]
            if total is None:
                total = declared
                # 총개수가 실제 청크 수보다 크면 유실이거나 위조다. 어느 쪽이든
                # 버퍼를 잡아두지 않고 즉시 거부한다(메모리 고갈 차단).
                if total != len(chunks):
                    return None, [f"총개수 {total} ≠ 수신 {len(chunks)} — 유실·위조 거부"]
            elif declared != total:
                return None, [f"청크 {i}: 총개수 불일치({declared} ≠ {total})"]
            if seq >= total:
                return None, [f"청크 {i}: 순번 {seq} 범위 밖(총 {total})"]
            if seq in parts:
                return None, [f"청크 순번 {seq} 중복 — 거부"]
            parts[seq] = bytes(c[CHUNK_HEADER_BYTES:])

        if len(parts) != total:
            missing = sorted(set(range(total)) - set(parts))
            return None, [f"청크 결번 {len(missing)}개 — 재조립 불가"]

        data = b"".join(parts[i] for i in range(total))
        if len(data) > _MAX_COMMAND_BYTES:
            return None, [f"재조립 {len(data):,}B — 명령 상한 {_MAX_COMMAND_BYTES:,}B 초과"]
        return data, []
    except Exception as e:   # fail-closed
        return None, [f"재조립 내부 오류({type(e).__name__}) — 거부"]


# ---------- 종단 실행 ----------
def _encode(cmd):
    """명령 → bytes. 2.1 wire와 같은 기준 표현(JSON UTF-8 compact)."""
    return json.dumps(cmd, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


def execute_routine(carrier, transports, record_name, routine_index, mtu=20):
    """프로필 조각 읽기 → 루틴 변환 → 청킹 → 전송. 반환 (result | None, errors).

    프로필은 **1.3의 캐리어 어댑터를 통해서만** 읽는다 — 저장 매체를 직접
    만지면 캐리어 중립(NFR3)이 이 스토리에서 무효화되고, Epic 3(재설치 복원)이
    저장 매체를 바꿀 때 이 경로가 죽는다.

    transports: {device_ref: 전송객체}. 전송객체가 `deliver_chunks(list[bytes])`를
    가지면 **청크를 그대로 넘겨 수신 측이 재조립**한다(2.3, 무선 구간의 실제
    구조). 없으면 `deliver(bytes)`(2.1 계약)로 폴백하되 **어느 경로였는지
    결과의 `reassembled_by`에 남긴다** — 조용한 분기 금지.
    루프백이든 BLE든 같은 코드가 돈다. 그게 2.3에서 네트워크를 끊어도 같은
    경로임을 보이는 근거다.
    """
    try:
        if carrier is None:
            return None, ["캐리어가 없음"]
        if not isinstance(transports, dict):
            return None, [f"transports가 객체가 아님({type(transports).__name__})"]

        got, errs = carrier.get_records([record_name])
        if errs:
            return None, errs
        from .storage import deserialize
        profile, errs = deserialize(got[record_name])
        if errs:
            return None, errs

        commands, errs = routine_to_commands(profile, routine_index)
        if errs:
            return None, errs

        # 전송 대상이 모두 준비됐는지 **먼저** 확인한다 — 절반만 보내고
        # 실패하면 집이 어중간한 상태로 남는다(부분 적용 금지)
        missing = [c["device_ref"] for c in commands
                   if c["device_ref"] not in transports]
        if missing:
            return None, [f"전송 대상 없음: 기기 {len(missing)}대"]

        chunks_sent = 0
        reassembled_by = None
        for cmd in commands:
            data = _encode(cmd)
            pieces, errs = chunk(data, mtu)
            if errs:
                return None, errs          # 사유를 그대로 전파(뭉개지 않는다)
            transport = transports[cmd["device_ref"]]
            if hasattr(transport, "deliver_chunks"):
                # 수신 측 재조립 — 무선 구간의 실제 구조 (2.3, R5 해소)
                errs = transport.deliver_chunks(pieces)
                by = "receiver"
            else:
                # 구형 전송 폴백: 송신 측이 붙여서 완성본을 넘긴다 (2.1 계약).
                # 무선 구간은 시뮬레이션되지 않는다 — 그 사실을 결과에 남긴다.
                restored, errs = reassemble(pieces)
                if errs:
                    return None, errs
                errs = transport.deliver(restored)
                by = "sender"
            if errs:
                return None, errs
            # 혼재는 조용히 넘기지 않는다 — 한 실행은 한 경로여야 한다
            if reassembled_by is not None and by != reassembled_by:
                return None, ["전송 경로 혼재 — 일부는 청크, 일부는 완성본"]
            reassembled_by = by
            chunks_sent += len(pieces)

        return {
            "commands": len(commands),
            # ⚠️ **"보낸" 기기 수이지 "바뀐" 기기 수가 아니다.**
            # 2.1 파티 리뷰 P4(applied vs unchanged)가 여기서 다시 만난다:
            # 같은 값을 재설정하면 시뮬레이터는 (applied=True, 이벤트 없음)을
            # 내므로 전송은 성공하지만 상태는 안 바뀐다. 실행기가 현재 필요한
            # 것은 "보냈는가"까지이므로 이름을 사실대로 붙이고 멈춘다 —
            # 진짜 변경 수가 필요해지는 것은 2.4(야간 모드 "전환됨" 표시)이며,
            # 그때 전송 계층이 무엇을 돌려줘야 하는지가 드러난다.
            # 지금 3값 열거형을 만들면 소비자 없이 인터페이스를 못 박는 것이다
            # (1.3 함정 7 · Winston 판단 유지).
            "devices_commanded": len(commands),
            "chunks_sent": chunks_sent,
            "mtu": mtu,
            # 수신 측 재조립(2.3)인지 송신 측 폴백(2.1 구형 전송)인지 —
            # 무선 구간이 시뮬레이션됐는지를 데모·발표가 정직하게 말하는 근거.
            "reassembled_by": reassembled_by,
        }, []
    except Exception as e:   # fail-closed
        return None, [f"루틴 실행 내부 오류({type(e).__name__}) — 거부"]
