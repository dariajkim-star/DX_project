# -*- coding: utf-8 -*-
"""분실·양도 시 온바디 프로필 폐기 (Story 4.4, NFR2).

설계 근거: docs/planning-artifacts/epics.md#Story 4.4
       docs/implementation-artifacts/4-4-profile-revocation.md
       docs/REVOCATION.md

이 모듈이 답하는 질문: **"잃어버리면 어떻게 되나"**. 온바디 구조의 가장 날카로운
반박이며, 답이 없으면 프라이버시 셀링포인트가 통째로 무너진다.

폐기의 의미는 "레코드를 지웠다"가 아니라 **"그 프로필로는 더 이상 가전을 못
연다"**(AC1)이다. 그래서 이 모듈은 지운 뒤 **복원을 시도해 실패를 확인**한다 —
`carrier.erase`의 성공 보고만 믿지 않는다("지웠다고 생각했는데 남아 있음"이
온바디 프라이버시 최악의 실패, carrier.py:238).

🛡️ **서버 없이 폐기된다(AC2).** 폐기가 서버를 요구하면 P-1(SPOF) 반박이 자기
   발등을 찍는다 — "서버 없이 동작한다"면서 가장 중요한 보안 동작에 서버를
   요구하는 꼴. enforce_offline 안에서 폐기가 성공함으로 증명한다.
⚠️ **원격 소거가 아니다(잔여 한계).** 이 폐기는 **캐리어에 접근할 수 있을 때**
   성립한다 — 이미 남의 손에 있는 워치를 원격으로 지우는 기능은 이 구조에 없다
   (서버 없는 구조의 대가). 실기기에선 워치 PIN·자동 잠금이 1차 방어이고, 이
   폐기는 "회수했거나 양도 전"의 경로다. 4.3의 완전방어 주장 금지 규율 승계.

계약 (전 스토리 승계):
  1. 예외 금지 — 어떤 입력에도 (ok: bool, report). fail-closed.
  2. 검증된 폐기 — report의 restorable_after는 **실제 복원 시도 결과**다
     (측정 안 한 리터럴 금지 — 4.1 파티 리뷰 교훈).
  3. 오류·리포트에 레코드 이름 원문 금지.

경계: carrier.erase·restore_from_carrier 조립. carrier·schema·storage 무수정.
"""
from .storage import restore_from_carrier

__all__ = ["revoke_onbody"]


def _count_residue(carrier, names):
    """폐기 대상 이름 중 **아직 살아있는** 레코드 수. 반환 (count, ok).

    ok=False는 조회 자체가 불가해 잔류를 판정하지 못했다는 뜻이다(모르는 것을
    0으로 세탁하지 않는다 — NFR6). 이름은 원문으로 보고하지 않고 개수만 센다.

    `get_records`는 하나라도 없으면 (None, errors)를 주므로(반쪽 결과 없음),
    한 번에 묻지 않고 이름마다 개별 조회한다 — '전부 없음'과 '일부 남음'을
    구분해야 하기 때문이다.
    """
    if not names:
        return 0, True
    alive = 0
    for n in names:
        try:
            got, _errs = carrier.get_records([n])
        except Exception:
            return None, False
        if got:
            alive += 1
    return alive, True


def revoke_onbody(carrier):
    """온바디 프로필을 폐기한다. 반환 (ok: bool, report). **예외 금지**.

    절차: meta 조회 → 전체 레코드 이름 재구성 → erase → **복원 시도로 검증**.
    Carrier 프로토콜엔 '전체 나열'이 없으므로(capabilities/put/get/erase뿐)
    meta의 device_refs·routine_count로 이름을 재구성한다(3.1 복원과 같은 패턴).
    """
    # ⚠️ "복원 불가"와 "잔류 0"은 **다른 주장**이다(코드리뷰 파티 2026-07-23,
    # Grumbal 재현). 복원은 meta부터 읽으므로 meta만 지워지면 복원은 실패하지만
    # device/routine 레코드는 워치에 남을 수 있다 — 그 상태를 '폐기 성공'으로
    # 보고하면 프라이버시 스토리의 핵심 주장이 거짓이 된다(4.1 유령 레코드와
    # 같은 병). 두 축을 분리해 **둘 다** 만족해야 폐기를 선언한다.
    report = {
        "records_erased": 0,
        "restorable_after": None,     # 실측 — 폐기 후 복원 시도 결과(리터럴 아님)
        "residual_records": None,     # 실측 — 폐기 후 살아남은 레코드 **개수**
        "server_required": False,     # 구조적 사실: 이 경로에 네트워크 호출 없음
        "errors": [],
    }
    try:
        # 1) meta 조회 — 지울 이름을 알아내는 유일한 창.
        # ⚠️ 조회가 **터진 것**과 meta가 **없는 것**을 구분한다. 캐리어가 고장나
        # 조회 자체가 실패하면 캐리어 상태를 알 수 없으므로 '이미 폐기됨'으로
        # 결론낼 수 없다 — 폐기 못 했는데 폐기됐다고 보고하는 것이 이 스토리
        # 최악의 실패다(carrier.py:238 계보). fail-closed로 거부한다.
        try:
            got, errs = carrier.get_records(["meta"])
        except Exception as e:
            report["errors"].append(
                f"캐리어 조회 실패({type(e).__name__}) — 폐기 상태 판정 불가, 거부")
            return False, report
        if not got:
            # 이미 비어 있거나 meta가 없다 — 지울 프로필이 없다.
            # 폐기 대상이 없는 것은 '실패'가 아니라 '이미 폐기됨'이나,
            # 폐기를 선언하려면 복원 불가를 확인해야 한다(계약 2).
            restored, r_errs = restore_from_carrier(carrier)
            report["restorable_after"] = bool(not r_errs and restored is not None)
            if report["restorable_after"]:
                report["errors"].append("meta 없이 복원 가능 — 폐기 상태 판정 불가")
                return False, report
            # ⚠️ meta가 없으면 지울 이름을 재구성할 수 없다 — 고아 잔류(device:*가
            # 남았는데 meta는 없는 상태)를 이 경로에서는 **탐지도 삭제도 못 한다**.
            # Carrier 프로토콜에 '전체 나열'이 없는 것이 근본 원인이며(캐리어 중립
            # 계약이라 못 건드림), 그래서 잔류 수를 0이 아니라 **None(판정 불가)**로
            # 남긴다. 사용자 조치는 REVOCATION.md 잔여 한계 참조(수동 워치 초기화).
            report["residual_records"] = None
            report["errors"].append(
                "폐기할 프로필 없음(이미 폐기되었거나 빈 캐리어) — "
                "meta 부재로 고아 잔류는 판정 불가")
            return True, report

        import json
        try:
            meta = json.loads(bytes(got["meta"]).decode("utf-8"))
        except Exception:
            meta = None
        if not isinstance(meta, dict):
            report["errors"].append("meta 해석 불가 — 폐기 중단(부분 삭제 방지)")
            return False, report

        refs = meta.get("device_refs")
        count = meta.get("routine_count")
        refs = refs if isinstance(refs, list) else []
        count = count if isinstance(count, int) and not isinstance(count, bool) \
            and count >= 0 else 0

        # 2) 전체 레코드 이름 재구성 → 원자적 erase(부분 삭제 없음).
        names = ["meta"] + [f"device:{r}" for r in refs] + \
                [f"routine:{i}" for i in range(count)]
        errs = carrier.erase(names)
        if errs:
            report["errors"].append("삭제 실패 — 폐기 미완결(잔류 가능)")
            # 잔류 여부를 검증까지 하고 보고한다(아래 3단계로 계속).
        else:
            report["records_erased"] = len(names)

        # 3) **검증 — 두 축 모두.** erase 성공 보고만 믿지 않는다.
        #    ① 복원 불가: 그 프로필로 가전을 못 연다(AC1의 문면)
        #    ② 잔류 0: 워치에 개인 데이터가 남지 않았다(온바디 프라이버시)
        #    ①만 보면 meta만 지워진 부분 폐기를 성공으로 오보한다(파티 Grumbal).
        restored, r_errs = restore_from_carrier(carrier)
        report["restorable_after"] = bool(not r_errs and restored is not None)
        residue, measured = _count_residue(carrier, names)
        report["residual_records"] = residue      # 판정 불가면 None(0으로 세탁 금지)
        if report["restorable_after"]:
            report["errors"].append("폐기 후에도 복원 가능 — 폐기 실패(잔류)")
            return False, report
        if not measured:
            report["errors"].append("잔류 여부 판정 불가 — 폐기 미확인")
            return False, report
        if residue:
            report["errors"].append(
                f"복원은 불가하나 레코드 {residue}건 잔류 — 폐기 미완결")
            return False, report
        return (not report["errors"]), report
    except Exception as e:   # fail-closed
        report["errors"].append(f"폐기 내부 오류({type(e).__name__}) — 거부")
        return False, report
