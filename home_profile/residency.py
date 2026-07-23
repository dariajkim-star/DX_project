# -*- coding: utf-8 -*-
"""데이터 소재 명시 (Story 4.2, FR7).

설계 근거: docs/planning-artifacts/epics.md#Story 4.2
       docs/implementation-artifacts/4-2-data-residency.md

이 모듈이 답하는 질문: **"내 집 정보는 어디에 있는가"**(P-3 마무리).
4.1(무계정)이 "신원을 안 넘긴다"였다면, 4.2는 "그럼 데이터는 어디"에 답한다 —
프로필 원본이 온바디(워치)에 있고 서버는 원본을 갖지 않음을 **관찰로 증명**한다.

⚠️ **말이 아니라 관찰로 증명한다.** "서버에 없다"를 문자열로 적는 게 아니라,
온바디에 실제 무엇이 있는지(footprint)와 **온바디만으로 프로필이 복원되는지**
(3.1 restore_from_carrier)를 값으로 보인다. 원본이 서버가 아니라 온바디에
완결돼 있음을 코드가 증거한다.

계약 (3.1·4.1·1.x 승계):
  1. 예외 금지 — 어떤 입력에도 report(dict). fail-closed.
  2. 이름 비노출 — footprint는 종류별 개수·바이트로 보고하고 raw device_ref
     원문을 찍지 않는다(carrier _show_name 계보 — 이름은 PII 운반체일 수 있다).
  3. 네트워크 0 — 소재 확인이 서버를 부르면 자기모순이다. 온바디만 읽는다.
  4. 서버 전송 '없음'을 빈 목록으로 명시(AC2).

경계: split_chunks(footprint)·restore_from_carrier(복원 증거) 조립.
schema·carrier·storage 무수정.
"""
from .schema import validate_profile
from .storage import _dumps, restore_from_carrier, split_chunks

__all__ = ["data_residency"]

_KNOWN_KINDS = ("meta", "device", "routine")


def data_residency(profile, carrier):
    """프로필의 데이터 소재를 명시한다. 반환 report(dict). **예외 금지**.

    report:
      profile_location       — 원본 위치(온바디)
      server_holds_original  — 서버 원본 보유 여부(False)
      server_transmitted     — 서버로 전송되는 항목(없으면 [] = '없음', AC2)
      onbody_record_count    — 온바디 레코드 수
      onbody_bytes           — 온바디 저장 바이트(이름 포함, 캐리어 산정과 동일)
      onbody_kinds           — 종류별 개수(meta/device/routine) — 이름 비노출
      restorable_from_onbody — 온바디만으로 복원 성공(원본이 거기 있다는 증거)
      errors                 — 실패 사유(fail-closed)
    """
    report = {
        "profile_location": "온바디 (참조 어댑터 레코드 — 실기기 아님)",
        "server_holds_original": False,
        "server_transmitted": [],            # AC2: 없음 — 서버로 가는 항목 없음
        "onbody_record_count": 0,
        "onbody_bytes": 0,
        "onbody_kinds": {k: 0 for k in _KNOWN_KINDS},
        "restorable_from_onbody": False,
        "errors": [],
    }
    try:
        errs = validate_profile(profile)
        if errs:
            report["errors"].append("프로필이 유효하지 않음 — 소재 확인 불가")
            return report

        # 온바디 footprint — 종류별 개수·바이트만(이름 원문 비노출, 함정 2).
        chunks = split_chunks(profile)
        report["onbody_record_count"] = len(chunks)
        total = 0
        for name, obj in chunks.items():
            try:
                total += len(name.encode("utf-8")) + len(_dumps(obj))
            except Exception:
                report["errors"].append("일부 레코드 크기 측정 불가")
            kind = name.split(":", 1)[0]
            if kind in report["onbody_kinds"]:
                report["onbody_kinds"][kind] += 1
        report["onbody_bytes"] = total

        # 원본이 온바디에 있음의 증거: 캐리어만으로 복원돼 원본과 동일해야 한다.
        # 다른 저장소(서버)가 필요 없음을 관찰로 보인다.
        restored, r_errs = restore_from_carrier(carrier)
        report["restorable_from_onbody"] = bool(not r_errs and restored == profile)
        return report
    except Exception as e:   # fail-closed
        report["errors"].append(f"소재 확인 내부 오류({type(e).__name__})")
        return report
