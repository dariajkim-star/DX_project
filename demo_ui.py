# -*- coding: utf-8 -*-
"""데모 프레젠테이션 층 — 7개 데모 스크립트의 출력 단일 출처 (순수 stdlib).

계약 (docs/implementation-artifacts/spec-demo-presentation-layer.md):
  - 색은 5 의미역만: fg / dim / success / blocked / held (장식색 금지)
  - 판정은 항상 기호+색 병기 — 색이 꺼져도 기호는 남는다 (색맹 대비)
  - 비TTY·NO_COLOR·VT enable 실패 시 자동 무색 (테스트 capsys는 무색 경로)
  - 이 층은 **표시만** 한다 — 값을 만들거나 기본값으로 채우지 않는다
    (REVIEW_PLAYBOOK 교훈 1·3). 모든 값은 호출자가 준 실측이다.
  - evidence_block은 결론 문자열을 합성하지 않는다 — "완료"류 배지 미출력
  - 모든 출력은 appliance_sim.core.console_safe 경유 (cp949 안전)
"""
import os
import sys

from appliance_sim.core import console_safe

_RESET = "\x1b[0m"
# 5 의미역만 (DESIGN.md colors.terminal). 장식색 없음.
_ROLES = {
    "fg": "\x1b[1m",          # 본문 강조(굵게) — 별색 아님
    "dim": "\x1b[2m",
    "success": "\x1b[32m",
    "blocked": "\x1b[31m",
    "held": "\x1b[33m",
}

# 판정 3값: 기호는 색과 무관하게 항상 출력된다.
_VERDICTS = {
    "ok": ("✓", "success"),
    "blocked": ("✗", "blocked"),
    "held": ("⏸", "held"),
}


def _enable_windows_vt() -> bool:
    """Windows 콘솔 VT 처리 활성화 시도. 실패하면 False (무색 폴백)."""
    if os.name != "nt":
        return True
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)            # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        new_mode = mode.value | 0x0004                 # ENABLE_VIRTUAL_TERMINAL_PROCESSING
        return bool(kernel32.SetConsoleMode(handle, new_mode))
    except Exception:
        return False


_vt_enabled = None  # VT enable 결과 캐시 — syscall은 프로세스당 1회면 충분


def _supports_color(stream=None) -> bool:
    """TTY이고 NO_COLOR가 없고 (Windows면) VT enable에 성공했을 때만 True.

    NO_COLOR는 규약(no-color.org)대로 값이 아니라 **존재**로 판정한다.
    """
    global _vt_enabled
    stream = stream if stream is not None else sys.stdout
    if "NO_COLOR" in os.environ:
        return False
    if not getattr(stream, "isatty", lambda: False)():
        return False
    if _vt_enabled is None:
        _vt_enabled = _enable_windows_vt()
    return _vt_enabled


def _paint(text: str, role: str) -> str:
    if role in _ROLES and _supports_color():
        return f"{_ROLES[role]}{text}{_RESET}"
    return text


def emit(line: str = ""):
    print(console_safe(line))


# cp949 등 좁은 인코딩용 폴백 — console_safe가 기호를 '?'로 뭉개면 판정 정보가
# 통째로 사라진다("색이 꺼져도 기호는 남는다" 계약 붕괴). 인코딩 가능 여부를
# 프로브해 안전 기호로 대체한다.
_SYMBOL_FALLBACK = {"✓": "[OK]", "✗": "[X]", "⏸": "[보류]",
                    "🛡️": "[방어]", "⚠️": "[!]"}


def _safe_symbol(symbol: str) -> str:
    enc = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        symbol.encode(enc)
        return symbol
    except (UnicodeEncodeError, LookupError):
        return _SYMBOL_FALLBACK.get(symbol, symbol)


def verdict(status: str) -> str:
    """'ok'|'blocked'|'held' → 기호(+색). 그 외 status는 만들어내지 않고 오류."""
    symbol, role = _VERDICTS[status]
    return _paint(_safe_symbol(symbol), role)


def scene_header(title: str, banner: str):
    """장면 경계 헤더 — 배너는 경계마다 1회 (§4-b 규약)."""
    emit()
    emit(_paint(f"--- {title} · {banner} ---", "fg"))


def title_block(banner: str, subtitle: str):
    """기동 헤더(경계 1) — 배너 1회 + 부제."""
    emit("=" * 62)
    emit(f"  {banner}")
    emit(f"  {_paint(subtitle, 'fg')}")
    emit("=" * 62)


def transition_row(label: str, status: str, code_kv: str = "", job: str = ""):
    """전이 1행: `  {장면표기} {기호} ({코드키: 값})  — {Job 대응}`.
    코드값은 괄호 보조 표기(코드가 진실 원천이라는 표시)."""
    line = f"  {label} {verdict(status)}"
    if code_kv:
        line += f" ({code_kv})"
    if job:
        line += f"  — {job}"
    emit(line)


def honesty_footer(lines):
    """장면 말미 고정 슬롯 — 시뮬레이터·미측정·범위 한계 (dim, 들여쓰기 2칸)."""
    for ln in lines:
        emit(_paint(f"  {ln}", "dim"))


def held_summary(transferred_n: int, held_rows, total_n: int):
    """이전 n + 보류 m = 옛 전체 N 항등식 표 (S3 전용).

    held_rows: (label, reason) 목록 — 보류 각 행에 사유 필수.
    값은 호출자의 실측 그대로 출력한다. 항등식이 깨져도 값을 조작하지 않고
    실측값 + 불일치 경고 행을 낸다 (교훈 3: 실패 경로에서도 리포트는 진실).
    """
    held_n = len(held_rows)
    emit(f"  이전 {transferred_n} + 보류 {held_n} = 옛 전체 {total_n} "
         f"{verdict('ok') if transferred_n + held_n == total_n else verdict('blocked')}"
         f" (누락 0 항등식)")
    if transferred_n + held_n != total_n:
        emit(_paint(f"  {_safe_symbol('⚠️')} 항등식 불일치 — 실측: 이전 {transferred_n}·"
                    f"보류 {held_n}·전체 {total_n}. 값 미조작, 원인 확인 필요", "held"))
    for label, reason in held_rows:
        emit(f"  {verdict('held')} 보류: {label} — 사유 {reason}")


def boundary_table(blocks, cannot_blocks):
    """막는 것 / 못 막는 것 병렬 표 (S6 전용) — 같은 서식, 같은 무게.

    빈 목록은 조용히 지나가지 않는다 — 누락은 명시한다.
    """
    if not blocks and not cannot_blocks:
        emit("  (항목 없음 — 호출자가 빈 경계를 넘김)")
        return
    for item in blocks:
        emit(f"  {_safe_symbol('🛡️')} 막는다   {verdict('ok')} {item}")
    for item in cannot_blocks:
        emit(f"  {_safe_symbol('⚠️')} 못 막는다 {verdict('blocked')} {item}")


def evidence_block(axes):
    """검증 증거 블록 (S7 전용). axes: (label, measured, ok) 목록.

    층은 결론 문자열을 합성하지 않는다 — 호출자가 준 실측(measured)만 표시.
    "완료"류 배지는 두 축이 모두 통과해도 출력하지 않는다: 증거 행 자체가 결론.
    빈 axes는 조용히 지나가지 않는다.
    """
    if not axes:
        emit("  (검증 축 없음 — 호출자가 빈 증거를 넘김)")
        return
    for i, (label, measured, ok) in enumerate(axes, start=1):
        emit(f"  축{i} {label} -> {verdict('ok' if ok else 'blocked')} {measured}")
