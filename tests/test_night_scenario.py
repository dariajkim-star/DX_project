# -*- coding: utf-8 -*-
"""Night Keeper 야간 모드 시나리오 회귀 테스트 (Story 2.4).

고정하는 것:
  1. 야간 루틴이 기존 어휘로 표현됨 — 새 capability 없음 (AC1)
  2. 야간 실행 → 여러 기기가 의도한 야간 값으로 전환 (AC1)
  3. 오프라인 강제 안에서 동일 결과 (2.3 종단 동등성 재사용)
  4. child_lock·소음원 off가 상태에 반영 (Task 2)
  5. 데모: 시나리오 성공, Job 문장 표시, 배너 규약 (AC1)
  6. 페르소나 정직 표기 — 미검증 라벨 + 인구통계 부재 (AC2·AC3)

Epic 1·2 교훈 승계: 정확한 값 단언, 관찰 가능성(이벤트 로그), 정직 표기.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import offline_guard  # noqa: E402
import demo_night  # noqa: E402
from appliance_sim.core import SIMULATOR_BANNER, ApplianceState  # noqa: E402
from appliance_sim.transports.loopback import LoopbackTransport  # noqa: E402
from home_profile import MemoryCarrier, serialize, validate_profile  # noqa: E402
from home_profile import routine as rt  # noqa: E402


# ---------- 1. 야간 루틴이 기존 어휘로 표현됨 (AC1) ----------

def test_night_profile_is_valid():
    """야간 프로필이 스키마를 통과한다 — 새 어휘를 발명하지 않았다는 증거."""
    profile = demo_night.build_night_profile()
    assert validate_profile(profile) == []


def test_night_routine_uses_only_known_capabilities():
    """야간 모드는 기존 capability 조합이다. night_mode 같은 신설 토큰이 없다
    (1.1 스키마 상한 = 보안 천장)."""
    from home_profile import storage as st
    known = set(st._CAPABILITIES)
    profile = demo_night.build_night_profile()
    for routine in profile["routines"]:
        for action in routine["actions"]:
            assert action["setting_key"] in known, action["setting_key"]


def test_night_routine_touches_multiple_devices():
    """야간 모드의 본질 = '여러 기기를 한 번에'. 단일 기기면 시나리오가 아니다."""
    profile = demo_night.build_night_profile()
    night = profile["routines"][demo_night.NIGHT_ROUTINE_INDEX]
    refs = {a["device_ref"] for a in night["actions"]}
    assert len(refs) >= 3


# ---------- 2·4. 야간 실행 → 의도한 값 전환 (AC1, Task 2) ----------

def _run_night(profile, guard=False):
    carrier = MemoryCarrier()
    data, errs = serialize(profile)
    assert errs == []
    assert carrier.put_records({"profile": data}) == []
    appliances = {d["device_ref"]: ApplianceState(
        d["device_ref"], d["device_type"], d["capabilities"])
        for d in profile["devices"]}
    transports = {ref: LoopbackTransport(a) for ref, a in appliances.items()}

    def _go():
        return rt.execute_routine(carrier, transports, "profile",
                                  demo_night.NIGHT_ROUTINE_INDEX)
    if guard:
        with offline_guard.enforce_offline():
            assert offline_guard.blocking_installed()
            result, rerrs = _go()
    else:
        result, rerrs = _go()
    states = {ref: a.snapshot()["state"] for ref, a in appliances.items()}
    return result, rerrs, states, appliances


def test_night_transition_sets_intended_values():
    """전환 후 각 기기가 야간 루틴이 의도한 값이다 (정확한 값 단언)."""
    profile = demo_night.build_night_profile()
    result, errs, states, _ = _run_night(profile)
    assert errs == []
    night = profile["routines"][demo_night.NIGHT_ROUTINE_INDEX]
    for action in night["actions"]:
        assert states[action["device_ref"]][action["setting_key"]] == action["value"]


def test_night_silences_noise_and_locks():
    """Job의 '아이를 깨우지 않고' — 소음원 off + child_lock on이 실제로 반영."""
    profile = demo_night.build_night_profile()
    _, errs, states, _ = _run_night(profile)
    assert errs == []
    # 로봇청소기(소음원)는 꺼진다
    assert states["dev_cleaner"]["power"] is False
    # 냉장고 child_lock은 켜진다
    assert states["dev_fridge"]["child_lock"] is True


def test_night_transition_observable_in_events():
    """관찰 가능성은 print가 아니라 이벤트 로그다 (2.1 규약)."""
    profile = demo_night.build_night_profile()
    _, errs, _, appliances = _run_night(profile)
    assert errs == []
    touched = {a["device_ref"]
               for a in profile["routines"][demo_night.NIGHT_ROUTINE_INDEX]["actions"]}
    for ref in touched:
        assert len(appliances[ref].events()) == 1


# ---------- 3. 오프라인 강제 안에서 동일 결과 (2.3 재사용) ----------

def test_night_identical_online_and_offline():
    """'잠들기 전, 네트워크 없이, 손목만으로' — 연결/차단 결과가 동일하다."""
    profile = demo_night.build_night_profile()
    _, on_errs, on_states, _ = _run_night(profile)
    _, off_errs, off_states, _ = _run_night(profile, guard=True)
    assert on_errs == [] and off_errs == []
    assert on_states == off_states                # 최종 상태 동일


# ---------- 5. 데모 (AC1) ----------

def test_demo_night_runs_and_shows_job(capsys):
    rc = demo_night.main([])
    out = capsys.readouterr().out
    assert rc == 0
    assert "잠든 뒤에도" in out                    # Job 문장이 화면에 선다
    assert "seq=" in out                          # 상태 전이가 보인다


def test_demo_night_offline_scene(capsys):
    """절정: 오프라인 + 야간이 한 화면에."""
    rc = demo_night.main(["--offline"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "차단" in out


def test_demo_night_banner_rule(capsys):
    """배너 규약(§4-b) 승계 — 경계마다 한 번, 스트림엔 생략."""
    demo_night.main([])
    lines = [ln for ln in capsys.readouterr().out.splitlines() if ln.strip()]
    stream = [ln for ln in lines if ln.lstrip().startswith(("dev_", "seq="))]
    assert len(stream) >= 3
    assert all(SIMULATOR_BANNER not in ln for ln in stream)


# ---------- 6. 페르소나 정직 표기 (AC2, AC3) ----------

def test_persona_doc_has_unverified_label():
    """AC3: '행동 프로파일 — 인구통계는 설문 검증 대기' 라벨 병기."""
    doc = (ROOT / "docs" / "PERSONA_NIGHT_KEEPER.md").read_text(encoding="utf-8")
    assert "설문 검증 대기" in doc
    assert "행동 프로파일" in doc


def test_persona_doc_has_no_fabricated_demographics():
    """⚠️ 이 프로젝트가 실제로 저지른 실수의 회귀 방지: MoA E가 만든
    인구통계 페르소나(김민수·김영희)는 날조로 기각됐다. 슬며시 돌아오는 것을 막는다.
    (1.2 '미측정 빈칸' 회귀 테스트와 같은 계보)"""
    doc = (ROOT / "docs" / "PERSONA_NIGHT_KEEPER.md").read_text(encoding="utf-8")
    import re
    # 기각된 날조 이름이 없다
    assert "김민수" not in doc and "김영희" not in doc
    # 인구통계 '값'이 없다 — 단어를 금지하면 "소득이 없다"는 정직한 설명까지
    # 걸린다(OFFLINE_EVIDENCE '모든' 자기참조 교훈). 날조의 서명은 **수치**다:
    assert not re.search(r"\d+\s*세", doc), "나이(N세) — 날조 위험"
    assert not re.search(r"(연봉|소득)\s*[:\s]*\d", doc), "소득 수치 — 날조 위험"
    assert not re.search(r"\d+\s*만\s*원", doc), "금액 — 날조 위험"


def test_persona_doc_maps_scenario_to_job():
    """AC2: 시나리오 ↔ Job 대응이 발표 자료에 명시."""
    doc = (ROOT / "docs" / "PERSONA_NIGHT_KEEPER.md").read_text(encoding="utf-8")
    assert "잠든 뒤에도" in doc                    # Job 문장
    assert "P-1" in doc                           # 겨냥 Pain 근거
