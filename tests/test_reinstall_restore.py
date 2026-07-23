# -*- coding: utf-8 -*-
"""Story 3.1 — 재설치 후 무재등록 복원 (FR4).

이 파일이 단언하는 것:
  1. 왕복 무손실(AC2): merge_chunks(split_chunks(p)) == p — 여러 크기에서.
  2. 재설치 복원(AC1): persist → 앱 상태 폐기 → restore == 원본,
     복원된 device_ref 집합이 원본과 동일(재등록으로 새 ref가 생기지 않음).
  3. 클라우드 조회 없음(AC3) — 두 겹:
     ① monkeypatch 감시("부르지 않았다", 2.2 패턴)
     ② enforce_offline 강제("부를 수 없다", 2.3 패턴)
  4. fail-closed 회귀: 결손 조각·카운트 불일치·손상 bytes → (None, errors),
     예외 아님. 부분 복원 금지.

혼동 금지: routine.reassemble(BLE 20B 바이트 청크)과 storage.merge_chunks
(저장 키 조각 meta/device:*/routine:*)는 다른 관심사다 — 스토리 함정 4.
"""
import copy

import pytest

from home_profile.carrier import MemoryCarrier
from home_profile.schema import SCHEMA_VERSION, validate_profile
from home_profile.storage import (
    ASSUMED_LARGE,
    ASSUMED_SMALL,
    ASSUMED_TYPICAL,
    make_sample_profile,
    merge_chunks,
    persist_to_carrier,
    restore_from_carrier,
    split_chunks,
)

# ---------- AC2: 왕복 무손실 (merge_chunks == split_chunks 역함수) ----------

@pytest.mark.parametrize("n_dev,n_rou", [ASSUMED_SMALL, ASSUMED_TYPICAL, ASSUMED_LARGE])
def test_roundtrip_lossless(n_dev, n_rou):
    """merge(split(p))가 원본과 의미적으로 동일 — 한 크기만 재면 왕복이 아니다."""
    p = make_sample_profile(n_dev, n_rou)
    restored, errs = merge_chunks(split_chunks(p))
    assert errs == []
    assert restored == p                       # 정확한 값 단언 — 단어 언급 금지


def test_roundtrip_preserves_device_order_and_settings():
    """_settings 접힘/펴짐이 정확히 역: settings가 top-level로 복원되고
    device 조각에 _settings 잔재가 남지 않으며, 순서는 meta.device_refs를 따른다."""
    p = make_sample_profile(*ASSUMED_TYPICAL)
    restored, errs = merge_chunks(split_chunks(p))
    assert errs == []
    assert [d["device_ref"] for d in restored["devices"]] == \
           [d["device_ref"] for d in p["devices"]]
    assert restored["settings"] == p["settings"]
    for d in restored["devices"]:
        assert "_settings" not in d
    assert [r["trigger"] for r in restored["routines"]] == \
           [r["trigger"] for r in p["routines"]]


def test_roundtrip_result_passes_validation():
    p = make_sample_profile(*ASSUMED_SMALL)
    restored, errs = merge_chunks(split_chunks(p))
    assert errs == []
    assert validate_profile(restored) == []


def test_empty_profile_roundtrip():
    """기기 0대·루틴 0개도 왕복된다(빈 프로필은 유효)."""
    p = make_sample_profile(0, 0)
    restored, errs = merge_chunks(split_chunks(p))
    assert errs == []
    assert restored == p


# ---------- fail-closed: merge_chunks는 반쪽 프로필을 만들지 않는다 ----------

def test_merge_rejects_missing_device_chunk():
    """meta.device_refs에 있는데 device:<ref> 조각이 없으면 거부 — 조용한 누락 금지."""
    chunks = split_chunks(make_sample_profile(3, 2))
    victim = next(k for k in chunks if k.startswith("device:"))
    del chunks[victim]
    restored, errs = merge_chunks(chunks)
    assert restored is None
    assert errs


def test_merge_rejects_routine_count_mismatch():
    chunks = split_chunks(make_sample_profile(3, 3))
    del chunks["routine:2"]
    restored, errs = merge_chunks(chunks)
    assert restored is None
    assert errs


def test_merge_rejects_missing_meta():
    chunks = split_chunks(make_sample_profile(2, 1))
    del chunks["meta"]
    restored, errs = merge_chunks(chunks)
    assert restored is None
    assert errs


def test_merge_never_raises_on_garbage():
    """예외 금지 계약(1.1 리뷰 F3 계보) — 어떤 입력에도 (None, errors)."""
    for garbage in (None, 42, "chunks", [], {"meta": None},
                    {"meta": {"device_refs": None, "routine_count": "x"}},
                    {"meta": {"schema_version": SCHEMA_VERSION,
                              "device_refs": ["a"], "routine_count": 0}}):
        restored, errs = merge_chunks(garbage)
        assert restored is None
        assert errs


def test_merge_revalidates_after_merge():
    """조각이 개별로 멀쩡해 보여도 병합 결과는 validate_profile을 다시 통과해야
    한다(와이어 불신, storage 계약 2). 금지 필드를 조각에 심어 확인한다."""
    chunks = split_chunks(make_sample_profile(2, 1))
    victim = next(k for k in chunks if k.startswith("device:"))
    chunks[victim] = dict(chunks[victim])
    chunks[victim]["owner_name"] = "kim"          # 식별자 필드 — 스키마가 거부
    restored, errs = merge_chunks(chunks)
    assert restored is None
    assert errs


# ---------- AC1·AC2: 캐리어 왕복 — 재설치 시나리오 ----------

def test_persist_then_restore_roundtrip():
    p = make_sample_profile(*ASSUMED_TYPICAL)
    carrier = MemoryCarrier()
    errs = persist_to_carrier(p, carrier)
    assert errs == []
    restored, errs = restore_from_carrier(carrier)
    assert errs == []
    assert restored == p


def test_reinstall_scenario_no_reregistration():
    """재설치의 정확한 모델링(함정 3): 앱 측 상태는 통째로 버리고
    캐리어(워치 대역) 인스턴스는 유지한다. 복원엔 재등록 절차가 없다 —
    device_ref 집합이 원본과 동일해야 한다(새 ref 발급 경로 부재)."""
    carrier = MemoryCarrier()                     # 워치 — 살아남는다
    app_state = {"profile": make_sample_profile(5, 3)}
    original = copy.deepcopy(app_state["profile"])
    assert persist_to_carrier(app_state["profile"], carrier) == []

    app_state.clear()                             # 앱 삭제·재설치 — 폰이 잊는다

    restored, errs = restore_from_carrier(carrier)
    assert errs == []
    assert restored == original
    assert {d["device_ref"] for d in restored["devices"]} == \
           {d["device_ref"] for d in original["devices"]}


def test_restore_from_empty_carrier_fails_closed():
    """워치까지 교체(빈 캐리어)면 복원은 성립하지 않는다 — 정직한 실패."""
    restored, errs = restore_from_carrier(MemoryCarrier())
    assert restored is None
    assert errs


def test_restore_rejects_corrupted_record():
    """조각 bytes 손상(비UTF8) → 거부, 예외 아님."""
    p = make_sample_profile(3, 2)
    carrier = MemoryCarrier()
    assert persist_to_carrier(p, carrier) == []
    victim = next(k for k in carrier._store if k.startswith("device:"))
    carrier._store[victim] = b"\xff\xfe broken"
    restored, errs = restore_from_carrier(carrier)
    assert restored is None
    assert errs


def test_restore_rejects_partially_erased_store():
    """레코드 일부 소실 → 부분 복원 금지(반쪽 프로필이 통과하지 않음)."""
    p = make_sample_profile(3, 2)
    carrier = MemoryCarrier()
    assert persist_to_carrier(p, carrier) == []
    victim = next(k for k in list(carrier._store) if k.startswith("routine:"))
    assert carrier.erase([victim]) == []
    restored, errs = restore_from_carrier(carrier)
    assert restored is None
    assert errs


def test_persist_rejects_invalid_profile():
    """검증 안 거친 프로필이 와이어로 나가는 경로를 만들지 않는다."""
    carrier = MemoryCarrier()
    errs = persist_to_carrier({"not": "a profile"}, carrier)
    assert errs
    restored, r_errs = restore_from_carrier(carrier)
    assert restored is None                       # 아무것도 저장되지 않았다
    assert r_errs


# ---------- AC3: 복원에 클라우드 조회 없음 — 두 겹 ----------

def test_restore_makes_no_network_calls(monkeypatch):
    """겹 ① 감시(2.2 패턴): 복원 경로가 네트워크 함수를 부르면 즉시 실패."""
    import socket
    import urllib.request

    def _fail(*a, **k):                           # pragma: no cover - 호출 자체가 실패
        raise AssertionError("복원 경로가 네트워크를 호출했다 — AC3 위반")

    for mod, name in ((socket, "socket"), (socket, "create_connection"),
                      (socket, "getaddrinfo"), (urllib.request, "urlopen")):
        monkeypatch.setattr(mod, name, _fail)

    p = make_sample_profile(*ASSUMED_TYPICAL)
    carrier = MemoryCarrier()
    assert persist_to_carrier(p, carrier) == []
    restored, errs = restore_from_carrier(carrier)
    assert errs == []
    assert restored == p


def test_restore_succeeds_under_offline_enforcement():
    """겹 ② 강제(2.3 패턴): 차단 상태에서 성공해야 '부를 수 없다'가 증명된다."""
    from offline_guard import blocking_installed, enforce_offline

    p = make_sample_profile(*ASSUMED_TYPICAL)
    carrier = MemoryCarrier()
    assert persist_to_carrier(p, carrier) == []

    with enforce_offline():
        assert blocking_installed()               # 카운터가 아니라 차단 실체 확인
        restored, errs = restore_from_carrier(carrier)
    assert errs == []
    assert restored == p


def test_offline_and_online_restore_are_identical():
    """종단 동등성(2.3 패턴) — 오프라인 강제 유무가 결과를 바꾸지 않는다."""
    from offline_guard import enforce_offline

    p = make_sample_profile(*ASSUMED_SMALL)
    carrier = MemoryCarrier()
    assert persist_to_carrier(p, carrier) == []

    online, on_errs = restore_from_carrier(carrier)
    with enforce_offline():
        offline, off_errs = restore_from_carrier(carrier)
    assert on_errs == off_errs == []
    assert online == offline == p


# ---------- 데모 (Task 3에서 채워지는 계약의 최소 고정) ----------

def test_demo_reinstall_runs_offline(capsys):
    """데모가 오프라인 플래그로 성공 종료하고 정직 표기를 지킨다.
    (하우스 패턴: 2.4처럼 in-process 호출 — cp949 콘솔 인코딩 변수 제거)"""
    import demo_reinstall

    assert demo_reinstall.main(["--offline"]) == 0
    out = capsys.readouterr().out
    assert "참조 어댑터" in out                    # 정직 표기 — "가민에서 됨" 금지
    assert "재등록" in out                         # 무재등록 서사가 화면에 선다
    assert "실기기" in out                         # NFR6 — 실기기 시연 아님 표기
