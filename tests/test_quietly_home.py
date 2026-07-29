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
    """이사 후 22(귀가자)·24(먼저 잔 사람) **둘 다 실행 실측**으로 생존 (GPT F3)."""
    rc, out = _run(capsys)
    assert rc == 0
    scene4 = out.split("장면 4")[1]
    assert "target_temp: 22" in scene4               # 귀가자의 원터치 실행 실측
    assert "target_temp: 24" in scene4               # 먼저 잔 사람도 실행 실측 (표시 아님)
    assert "재설정 0회" in out


def test_carrier_path_not_memory_bypass(capsys):
    """이사는 워치 복원 경유 — 메모리 원본 우회 금지 명시 (GPT F2)."""
    rc, out = _run(capsys)
    assert "워치에서 복원한 것" in out


def test_failed_transition_fails_process(capsys, monkeypatch):
    """전이 실측 불일치 시 rc 1 — 성공 결론 출력 금지 (GPT F1)."""
    import demo_quietly as dq

    def _noop_execute(carrier, transports, record, idx, mtu=20):
        return {"devices_commanded": 0, "reassembled_by": "noop"}, []

    monkeypatch.setattr(dq, "execute_routine", _noop_execute)
    rc = dq.main([])
    out = capsys.readouterr().out
    assert rc == 1
    assert "실측 불일치" in out
    assert "이사를 건넜고" not in out                # 성공 결론이 안 나와야 함


def test_held_items_have_reasons(capsys):
    """보류는 조용히 버려지지 않는다 — 사유와 항등식."""
    rc, out = _run(capsys)
    assert "누락 0 항등식" in out
    assert "no_matching_type" in out                 # washer·cleaner 보류 사유
    assert "capability_unsupported" in out           # fan_speed 보류 사유


def test_one_touch_not_sensing(capsys):
    """교훈 9: 긍정형 감지 문구까지 차단 (GPT F5 — '감지' 존재만으론 부족)."""
    rc, out = _run(capsys)
    assert "알아서" not in out
    assert "원터치" in out
    # 부정 문장은 정확히 존재해야 하고
    assert "수면 감지·위치·배우자 상태 공유 없음" in out
    # 긍정형 감지 회귀는 금지
    for banned in ("감지 후", "감지 완료", "자동 감지", "감지되"):
        assert banned not in out


def test_hypothesis_label_present(capsys):
    """T2 페르소나는 가설 라벨 병기 (PERSONA_LADDER §4)."""
    rc, out = _run(capsys)
    assert "가설(H3)" in out
    assert "설문 검증 대기" in out


def test_conflict_scope_honest(capsys):
    """멀티 프로필 충돌은 범위 밖임을 화면이 스스로 말한다."""
    rc, out = _run(capsys)
    assert "충돌" in out and "다음 단계" in out
