# -*- coding: utf-8 -*-
"""demo_ui(프레젠테이션 층) 계약 고정 테스트.

스펙 I/O 매트릭스 6케이스 + evidence_block "완료" 부재 + 무색 경로 스냅샷.
층은 표시만 한다 — 값 합성·조작이 없음을 여기서 고정한다.
"""
import io
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import demo_ui  # noqa: E402


class _FakeTTY(io.StringIO):
    def isatty(self):
        return True


# ---------- I/O 매트릭스 ----------

def test_matrix_1_tty_with_vt_emits_ansi(monkeypatch, capsys):
    """TTY+VT 지원 → ANSI 색 + 기호."""
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setattr(demo_ui, "_enable_windows_vt", lambda: True)
    monkeypatch.setattr(demo_ui.sys, "stdout", _FakeTTY())
    assert demo_ui._supports_color() is True
    v = demo_ui.verdict("ok")
    assert "\x1b[" in v and "✓" in v


def test_matrix_2_non_tty_is_colorless(capsys):
    """capsys/파이프(비TTY) → 무색, 기호만."""
    assert demo_ui._supports_color() is False
    for status, sym in [("ok", "✓"), ("blocked", "✗"), ("held", "⏸")]:
        v = demo_ui.verdict(status)
        assert "\x1b[" not in v and sym in v


def test_matrix_3_no_color_env_forces_colorless(monkeypatch):
    """NO_COLOR=1 → TTY여도 무색 강제."""
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setattr(demo_ui.sys, "stdout", _FakeTTY())
    assert demo_ui._supports_color() is False


def test_matrix_3b_vt_enable_failure_falls_back_colorless(monkeypatch):
    """Windows VT enable 실패 → 무색 폴백."""
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setattr(demo_ui, "_enable_windows_vt", lambda: False)
    monkeypatch.setattr(demo_ui, "_vt_enabled", None)   # VT 캐시 리셋 (2026-07-28 패치)
    monkeypatch.setattr(demo_ui.sys, "stdout", _FakeTTY())
    assert demo_ui._supports_color() is False


def test_matrix_4_held_summary_identity_mismatch_warns_without_fabrication(capsys):
    """S3 항등식: transferred+held ≠ 총계 → 실측값 그대로 + 경고 행. 값 조작 금지."""
    demo_ui.held_summary(4, [("fan_speed", "capability 미지원")], 9)
    out = capsys.readouterr().out
    assert "이전 4 + 보류 1 = 옛 전체 9" in out       # 실측 그대로
    assert "항등식 불일치" in out                     # 경고 행
    assert "값 미조작" in out


def test_matrix_4b_held_summary_identity_holds(capsys):
    demo_ui.held_summary(6, [("robot_cleaner", "매칭 없음"),
                             ("fan_speed", "capability 미지원"),
                             ("power", "매칭 없음")], 9)
    out = capsys.readouterr().out
    assert "이전 6 + 보류 3 = 옛 전체 9" in out
    assert "불일치" not in out
    assert out.count("사유") == 3                     # 보류 각 행에 사유 필수


def test_matrix_5_evidence_block_partial_revoke_no_badge(capsys):
    """S7 부분 폐기: residual>0 → 축2 ✗ + 실측 표기. '완료' 미출력."""
    demo_ui.evidence_block([
        ("복원 시도", "실패 — 프로필로 가전을 못 연다", False),
        ("잔류 스캔", "잔류 2건", False),
    ])
    out = capsys.readouterr().out
    assert "축1" in out and "축2" in out
    assert "잔류 2건" in out
    assert "완료" not in out


def test_matrix_5b_evidence_block_success_still_no_badge(capsys):
    """두 축이 모두 통과해도 '완료'를 합성하지 않는다 — 증거 행이 결론."""
    demo_ui.evidence_block([
        ("복원 시도", "실패(의도된 결과)", False),
        ("잔류 스캔", "0건", True),
    ])
    out = capsys.readouterr().out
    assert "완료" not in out
    assert "0건" in out


def test_matrix_6_boundary_table_equal_weight(capsys):
    """S6: 막는/못 막는 행 수·서식 동일 무게."""
    blocks = ["재생(replay)", "옛/위조 nonce", "챌린지 재사용"]
    cannot = ["실시간 relay", "근접 위조", "탈취 즉시 사용 → 폐기는 S7"]
    demo_ui.boundary_table(blocks, cannot)
    lines = [ln for ln in capsys.readouterr().out.splitlines() if ln.strip()]
    assert len(lines) == 6
    assert sum(1 for ln in lines if "막는다" in ln and "못" not in ln) == 3
    assert sum(1 for ln in lines if "못 막는다" in ln) == 3


# ---------- 무색 경로 스냅샷 ----------

def test_colorless_transition_row_snapshot(capsys):
    demo_ui.transition_row("에어컨 바람 약하게", "ok",
                           code_kv="fan_speed: low", job="소음↓")
    out = capsys.readouterr().out
    assert out == "  에어컨 바람 약하게 ✓ (fan_speed: low)  — 소음↓\n"
    assert "\x1b[" not in out


def test_colorless_scene_header_and_footer(capsys):
    demo_ui.scene_header("장면 1", "배너")
    demo_ui.honesty_footer(["시뮬레이터 — 실기기 아님"])
    out = capsys.readouterr().out
    assert "--- 장면 1 · 배너 ---" in out
    assert "  시뮬레이터 — 실기기 아님" in out
    assert "\x1b[" not in out


def test_verdict_rejects_unknown_status():
    """층이 판정값을 만들어내지 않는다 — 모르는 status는 오류."""
    with pytest.raises(KeyError):
        demo_ui.verdict("done")


# ---------- 리뷰 패치 고정 (2026-07-28 code review) ----------

def test_cp949_symbol_fallback(capsys, monkeypatch):
    """좁은 인코딩에서 판정 기호가 '?'로 소실되지 않고 폴백 기호로 남는다."""
    class _Cp949Out:
        encoding = "cp949"
        def isatty(self):
            return False
        def write(self, s):
            sys.__stdout__.write(s)
        def flush(self):
            pass
    monkeypatch.setattr(demo_ui.sys, "stdout", _Cp949Out())
    v = demo_ui.verdict("ok")
    assert v == "[OK]"          # ✓는 cp949 불가 → 폴백
    assert demo_ui.verdict("blocked") == "[X]"


def test_no_color_empty_value(capsys, monkeypatch):
    """NO_COLOR 규약: 값이 아니라 존재로 판정 — 빈 값도 무색."""
    monkeypatch.setenv("NO_COLOR", "")
    class _FakeTTY2:
        encoding = "utf-8"
        def isatty(self):
            return True
        def write(self, s):
            pass
        def flush(self):
            pass
    monkeypatch.setattr(demo_ui.sys, "stdout", _FakeTTY2())
    assert demo_ui._supports_color() is False


def test_empty_evidence_and_boundary_not_silent(capsys):
    """빈 증거/경계는 조용히 지나가지 않는다 — 누락을 명시한다."""
    demo_ui.evidence_block([])
    demo_ui.boundary_table([], [])
    out = capsys.readouterr().out
    assert "검증 축 없음" in out
    assert "항목 없음" in out
