# -*- coding: utf-8 -*-
"""무계정 로컬 전용 온보딩 (Story 4.1, FR6).

설계 근거: docs/planning-artifacts/epics.md#Story 4.1
       docs/implementation-artifacts/4-1-accountless-onboarding.md

이 모듈이 답하는 질문: **"신원을 넘기지 않고 집을 연결할 수 있는가"**(P-3 반박).
P-3(6.2%): "굳이 회원가입을 강요하는 이유가 뭡니까". 온보딩이 계정·로그인
**없이** 완결됨을 보인다.

⚠️ **무계정은 구조다 — 가짜 계정 시스템을 만들지 않는다.** `onboard_local`에는
username/password/token 같은 **인자 자체가 없고**, 경로에 네트워크 호출이 없다.
3.1 AC3("복원에 클라우드 조회 없음")와 같은 논리 — 참는 게 아니라 개입할 자리가
없다. `enforce_offline` 안에서 온보딩이 성공하는 것이 그 증명이다.

계약 (3.1·1.x 승계):
  1. 예외 금지 — 어떤 입력에도 (None|profile, report). fail-closed.
  2. 식별자 0(FR7 정합) — 결과 profile은 validate_profile() **및**
     find_identifier_violations() 둘 다 통과. 온보딩이 식별자 삽입 뒷문이 되지 않는다.
  3. 동의 정직성 — LOCAL_CONSENT_SCOPE는 최소이되 명시. 계정·로그인·이메일·위치·
     마케팅 항목이 없음을 코드로 감시(consent_scope_violations).
  4. 오류·리포트에 페이로드 값 금지.

경계: new_profile + persist_to_carrier(3.1) 조립. schema·carrier·storage 무수정.
"""
import copy

from .schema import (
    FORBIDDEN_KEY_FRAGMENTS,
    new_profile,
    validate_profile,
)
from .storage import persist_to_carrier

__all__ = [
    "LOCAL_CONSENT_SCOPE",
    "NOT_REQUIRED",
    "consent_scope_violations",
    "onboard_local",
]

# 로컬 동작에 **필요한** 동의 — 최소이되 명시(빈 목록으로 "동의 불요"를 위장하지
# 않는다). 각 항목에 목적 라벨. 여기에 계정·이메일·위치·마케팅은 없다.
LOCAL_CONSENT_SCOPE = (
    {"item": "ble_pairing", "purpose": "가전 로컬 제어를 위한 BLE 근접 페어링"},
    {"item": "onbody_storage", "purpose": "프로필을 워치(온바디)에 저장"},
)

# 온보딩이 **요구하지 않는** 것 — 대비로 보인다(AC2 문서화의 코드 원천).
NOT_REQUIRED = (
    {"item": "account", "why": "계정 생성 없이 동작"},
    {"item": "login", "why": "로그인·인증 없이 동작"},
    {"item": "email", "why": "이메일 수집 없음"},
    {"item": "phone", "why": "전화번호 수집 없음"},
    {"item": "location", "why": "위치·GPS 수집 없음"},
    {"item": "marketing", "why": "마케팅 동의 없음"},
    {"item": "cloud_backup", "why": "클라우드 백업 없음 — 원본은 온바디(FR7)"},
)

# 동의 범위 정직성 감시 어휘 — 스키마 방어를 승계하고 온보딩 특유의 항목을 더한다.
_CONSENT_FORBIDDEN = tuple(FORBIDDEN_KEY_FRAGMENTS) + (
    "login", "marketing", "password", "credential", "cloud", "token",
    "로그인", "마케팅", "비밀번호", "클라우드",
)


def consent_scope_violations(scope=LOCAL_CONSENT_SCOPE):
    """동의 범위에 계정·로그인성 항목이 섞였는지 검사. 빈 목록 = 정직.

    스키마의 식별자 방어(FORBIDDEN_KEY_FRAGMENTS)와 같은 어휘로 온보딩 동의를
    감시한다 — '필요한 동의' 목록에 계정성 항목이 slipping in 하는 것을 막는다."""
    violations = []
    if not scope:
        violations.append("동의 범위가 비어 있음 — 최소이되 명시여야 함(빈 목록 위장 금지)")
        return violations
    for entry in scope:
        item = str(entry.get("item", "")).lower()
        for frag in _CONSENT_FORBIDDEN:
            if frag in item:
                violations.append(f"동의 항목 '{item}'에 금지 문구('{frag}') — "
                                  f"로컬 동작 범위 초과")
                break
    return violations


def onboard_local(devices, carrier):
    """계정·로그인 없이 프로필 생성 + 기기 연결 + 온바디 저장.

    반환 (profile | None, report). devices: 연결할 기기 dict 목록
    (device_ref·device_type·capabilities). carrier: 온바디 저장소(워치 대역).

    **계정·로그인·서버 등록 단계가 경로에 없다** — 인자에 자격증명이 없고,
    네트워크 호출이 없다.

    report는 **관찰한 것만** 담는다(코드리뷰 2026-07-23, Vex+Yui): 무계정을
    'account_created=False' 같은 측정 안 한 리터럴로 주장하지 않는다(그건
    삭제된 SAMPLE_ASSUMPTIONS_ARE_MEASURED와 같은 장식·NFR6 위반). '계정을
    요구하지 않음'은 `not_required` 목록으로 명시하고, '네트워크를 안 부른다'는
    tests/test_onboarding.py의 enforce_offline·monkeypatch가 증명한다.
    """
    report = {
        "consent_scope": [dict(c) for c in LOCAL_CONSENT_SCOPE],
        "not_required": [dict(c) for c in NOT_REQUIRED],
        "devices_connected": 0,
        "errors": [],
    }
    try:
        # 동의 범위 자체가 정직한지 먼저 확인(계정성 항목 slip-in 차단).
        cv = consent_scope_violations()
        if cv:
            report["errors"].extend(cv)
            return None, report
        if not isinstance(devices, list):
            report["errors"].append(f"devices는 목록이어야 함({type(devices).__name__})")
            return None, report

        # 온보딩 = 최초 설치. 이미 프로필이 있는 캐리어에 다시 온보딩하면
        # put_records가 merge라 옛 레코드가 유령으로 잔류하고(데이터 최소화 위반),
        # data_residency의 footprint(현재 프로필 기준)가 실제 온바디 저장량을
        # 축소 보고한다(4.2 소재 명시가 자기반증). 그래서 **거부**한다 — 재설정은
        # 폐기(revocation, 4.4) 후 다시 온보딩하는 별도 흐름이다(코드리뷰 파티
        # 2026-07-23: Grumbal footprint divergence · Yui meta 감지 · 관심사 분리).
        # 빈 여부는 meta 레코드 존재로 판정한다 — 모든 프로필은 meta 하나를 갖고,
        # Carrier 프로토콜엔 '나열/비었나' 메서드가 없어 get_records가 유일한 창이다.
        try:
            existing, _ = carrier.get_records(["meta"])
        except Exception:
            existing = None                      # 조회 자체가 터지면 빈 것으로 보지 않는다
        if existing:
            report["errors"].append(
                "이미 온보딩된 캐리어 — 온보딩은 빈 워치 전제. "
                "재설정은 폐기(revocation) 후 다시 온보딩할 것")
            return None, report

        profile = new_profile()
        for d in devices:
            if not isinstance(d, dict):
                report["errors"].append(f"기기 항목이 dict가 아님({type(d).__name__})")
                return None, report
            # 기기 정의를 그대로 등록한다 — 식별자 키가 섞였으면 아래 검증이
            # 잡는다(조용히 떨궈 우회하지 않는다, 함정 3).
            profile["devices"].append(copy.deepcopy(d))

        # FR7 정합: 유효성 강제 — 식별자 스캔은 validate_profile이 **맨 먼저**
        # 돌린다(schema.py:481). 별도 find_identifier_violations 재호출은 죽은
        # 코드였다(validate 통과 = 식별자 0 이미 보장). 거짓 이중방어 제거
        # (코드리뷰 2026-07-23, Yui). 온보딩이 식별자 뒷문이 되지 않음은
        # validate_profile 하나로 성립하고, 결과 검증은 테스트가 독립 확인한다.
        errs = validate_profile(profile)
        if errs:
            report["errors"].append("온보딩 프로필이 유효하지 않음 — 거부(식별자 포함)")
            return None, report

        # 기기 연결 = 온바디 저장(3.1 persist_to_carrier). 네트워크 없음.
        errs = persist_to_carrier(profile, carrier)
        if errs:
            report["errors"].append("온바디 저장 실패 — 온보딩 미완결")
            return None, report

        report["devices_connected"] = len(profile["devices"])
        return profile, report
    except Exception as e:   # fail-closed
        report["errors"].append(f"온보딩 내부 오류({type(e).__name__}) — 거부")
        return None, report
