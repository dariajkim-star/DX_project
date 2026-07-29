# -*- coding: utf-8 -*-
"""Quietly Home 데모 계약 고정 (spec-quietly-home-demo).

핵심 주장: '조용한 귀가' 설정이 이사를 건너 **각자의 값으로** 생존한다.
그리고 이 데모가 말하면 안 되는 것("알아서"·감지)이 실제로 없음을 고정한다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import demo_quietly  # noqa: E402


def _run(capsys):
    rc = demo_quietly.main([])
    return rc, capsys.readouterr().out


def test_runs_clean(capsys):
    rc, out = _run(capsys)
    assert rc == 0
    assert "시뮬레이터" in out                       # 배너
    assert "참조 어댑터" in out                      # NFR6


def test_preferences_survive_move_individually(capsys):
    """이사 후에도 26(귀가자)과 24(먼저 잔 사람)가 각자 생존 — 실측 출력."""
    rc, out = _run(capsys)
    assert rc == 0
    scene4 = out.split("장면 4")[1]
    assert "target_temp: 26" in scene4               # 귀가자의 값이 새 집에서 실행됨
    assert "24도" in scene4                          # 배우자 값도 따라옴 (표시)
    assert "재설정 0회" in out


def test_held_items_have_reasons(capsys):
    """보류는 조용히 버려지지 않는다 — 사유와 항등식."""
    rc, out = _run(capsys)
    assert "누락 0 항등식" in out
    assert "no_matching_type" in out                 # washer·cleaner 보류 사유
    assert "capability_unsupported" in out           # fan_speed 보류 사유


def test_one_touch_not_sensing(capsys):
    """교훈 9: '알아서'(감지·학습 함의) 부재, 원터치 명시."""
    rc, out = _run(capsys)
    assert "알아서" not in out
    assert "원터치" in out
    assert "감지" in out                             # "감지가 아니다" 명시 문구


def test_hypothesis_label_present(capsys):
    """T2 페르소나는 가설 라벨 병기 (PERSONA_LADDER §4)."""
    rc, out = _run(capsys)
    assert "가설(H3)" in out
    assert "설문 검증 대기" in out


def test_conflict_scope_honest(capsys):
    """멀티 프로필 충돌은 범위 밖임을 화면이 스스로 말한다."""
    rc, out = _run(capsys)
    assert "충돌" in out and "다음 단계" in out
