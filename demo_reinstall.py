# -*- coding: utf-8 -*-
"""재설치 후 무재등록 복원 데모 (Story 3.1).

    python demo_reinstall.py            # 재설치 복원 장면
    python demo_reinstall.py --offline  # 네트워크 없이 복원 — AC3 절정

Epic 3의 첫 장면: P-2를 구조로 반박한다 — 대표 리뷰(crawl_playstore_thinq.csv
원문): "핸드폰 초기화 하고 재설치 하니... 제품이 전부 없어짐 삼성껀 그대로 인데"
(경쟁 2.0배 열위 실측).
프로필 원본이 클라우드가 아니라 온바디에 있으므로, **폰이 잊어도 손목이
기억한다** — 재등록 절차 자체가 코드에 존재하지 않는다(FR4).

⚠️ **재설치를 정직하게 모델링한다(스토리 함정 3).** "앱 삭제"는 폰 로컬
상태의 소실이다. 캐리어(참조 어댑터=워치 대역)는 **살아남는다** — 같은
인스턴스를 유지하고 앱 측 변수만 버린다. 새 캐리어를 만들면 워치까지
교체한 다른 시나리오다.

⚠️ **`home_profile/`을 수정하지 않는다.** 복원 부품(persist/restore)은
storage가 제공하고, 여기서는 장면만 조립한다.
"""
import argparse
import sys

from appliance_sim.core import SIMULATOR_BANNER, console_safe
from home_profile import (
    MemoryCarrier,
    persist_to_carrier,
    restore_from_carrier,
)
from home_profile import storage as st

# P-2 대표 리뷰 — crawl_playstore_thinq.csv 원문 대조 완료(2026-07-23, 평점 2).
# 원문: "핸드폰 초기화 하고 재설치 하니... 제품이 전부 없어짐 삼성껀 그대로 인데"
PAIN = "핸드폰 초기화 하고 재설치 하니... 제품이 전부 없어짐"


def _emit(line=""):
    print(console_safe(line))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="demo_reinstall",
        description=f"{SIMULATOR_BANNER} — 재설치 후 무재등록 복원 (Story 3.1)")
    p.add_argument("--offline", action="store_true",
                   help="오프라인 강제 안에서 복원 (클라우드가 개입할 자리가 없다)")
    args = p.parse_args(argv)

    # 경계 1: 기동 헤더 — 배너 1회
    _emit("=" * 62)
    _emit(f"  {SIMULATOR_BANNER}")
    _emit(f"  재설치 복원 — P-2 반박: \"{PAIN}\"")
    _emit("=" * 62)

    # 장면 1: 등록 완료 상태 — 프로필을 워치(참조 어댑터)에 새긴다
    carrier = MemoryCarrier()                      # 워치 대역 — 실기기 아님
    app_state = {"profile": st.make_sample_profile(*st.ASSUMED_TYPICAL)}
    original_refs = [d["device_ref"] for d in app_state["profile"]["devices"]]
    errs = persist_to_carrier(app_state["profile"], carrier)
    if errs:
        _emit(f"[{SIMULATOR_BANNER}] 온바디 저장 실패: {errs[0]}")
        return 1
    stored = sum(len(v) for v in carrier._store.values())
    _emit()
    _emit(f"--- 장면 1: 등록 완료 · {SIMULATOR_BANNER} ---")
    _emit(f"  기기 {len(original_refs)}대·루틴 "
          f"{len(app_state['profile']['routines'])}개 -> "
          f"온바디 {stored:,}B ({len(carrier._store)}개 레코드, 참조 어댑터)")

    # 장면 2: 앱 삭제·재설치 — 폰이 잊는다. 워치는 남는다.
    app_state.clear()
    _emit()
    _emit(f"--- 장면 2: 앱 삭제·재설치 · {SIMULATOR_BANNER} ---")
    _emit("  폰 로컬 상태: 전부 소실 (앱이 아는 것 = 없음)")
    _emit("  온바디(참조 어댑터): 유지 — 프로필 원본은 손목에 있다")

    # 장면 3: 복원 — 재등록 절차 없이, (옵션) 네트워크 없이
    _emit()
    _emit(f"--- 장면 3: 복원 · {SIMULATOR_BANNER} ---")
    if args.offline:
        import offline_guard
        try:
            with offline_guard.enforce_offline():
                restored, errs = restore_from_carrier(carrier)
        except offline_guard.OfflineViolation as v:
            _emit(f"[{SIMULATOR_BANNER}] ⚠️ 복원이 네트워크를 건드렸다: {v}")
            return 1
        _emit("  오프라인 강제 활성 — 클라우드가 개입할 자리가 없음을 강제로 증명")
        _emit("  ※ 한계: 이 파이썬 프로세스 차단까지다. 장비 기내모드는 사람이 누른다")
    else:
        restored, errs = restore_from_carrier(carrier)
    if errs:
        _emit(f"[{SIMULATOR_BANNER}] 복원 실패: {errs[0]}")
        return 1

    restored_refs = [d["device_ref"] for d in restored["devices"]]
    if restored_refs != original_refs:
        _emit(f"[{SIMULATOR_BANNER}] ⚠️ 복원 불일치 — 기기 목록이 다르다")
        return 1
    _emit(f"  복원: 기기 {len(restored_refs)}대·루틴 "
          f"{len(restored['routines'])}개 — 삭제 전과 일치")
    _emit("  재등록 0회 — 복원 경로에 기기 등록·ref 발급 코드가 존재하지 않는다")

    # 경계 4: 종료 푸터 — 배너 1회
    _emit()
    _emit("폰은 잊었지만 손목이 기억한다 — 재등록 노동의 구조적 소멸 (FR4)")
    _emit("복원에 클라우드 조회 0회 — \"원본이 서버에 없다\"(FR7)의 예고편")
    _emit(f"[{SIMULATOR_BANNER}] 참조 어댑터 기반 — 실기기(가민) 시연 아님")
    return 0


if __name__ == "__main__":
    sys.exit(main())
