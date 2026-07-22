# -*- coding: utf-8 -*-
"""캐리어 중립 추상화 — 인터페이스·값 객체·참조 어댑터 (Story 1.3).

설계 근거: docs/planning-artifacts/epics.md#Story 1.3 (NFR3·NFR6)
       docs/implementation-artifacts/1-3-carrier-neutral-abstraction.md
       docs/CARRIER_INTERFACE.md (메서드 계약표·새 캐리어 추가 절차)

이 모듈이 답하는 질문: **"그 손목이 누구 손목이어도 되는가"**(NFR3).
캐리어 중립은 성능 요구가 아니라 전략 제약이다 — 삼성 갤럭시워치 폐쇄 진영에
대한 개방 생태계 전략이 처방 정의에 들어 있고, 벤더 API가 코어에 새면
발표의 주장 한 축이 코드 레벨에서 무너진다.

계약 (1.1·1.2 계승):
  1. **예외 금지** — put_records·get_records·erase·capabilities는 어떤 입력에도
     예외를 던지지 않는다. 내부 오류는 fail-closed로 오류 목록 반환.
  2. **불투명 바이트** — 인터페이스는 {이름: bytes} 레코드 맵만 다룬다.
     단일 키/섹션 분할, 평문/압축 어느 쪽도 강요하지 않는다 — 1.2의
     미결정(A 섹션분할 vs C zlib)을 인터페이스에 못 박지 않기 위해서다.
  3. **한계는 신고하고 강제한다** — capabilities()가 신고한 한계를 어댑터가
     실제로 집행한다. 신고만 하고 통과시키는 어댑터는 거짓말쟁이다.
  4. **오류에 페이로드 금지** — 오류 문구는 레코드 이름·바이트 수·한계값까지만.
     페이로드가 로그로 새는 순간 온바디 프라이버시 주장(FR7)이 자기 코드에서
     반증된다(1.1 리뷰 PII 누출 계승).

벤더 어댑터는 home_profile/carriers/ 하위에 둔다 — 경계가 디렉터리로도 보인다.
코어(schema·storage·이 파일)는 벤더 SDK를 import하지 않으며,
tests/test_carrier_neutrality.py가 AST 기반으로 이를 감시한다.
"""
import enum
from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable

from . import storage as _storage
# 리뷰 P5: v1은 capabilities() 안에서 지연 import를 했는데 try 밖이라
# "capabilities 포함 예외 금지" 계약이 코드로 보장되지 않았다. storage는
# carrier를 import하지 않으므로 순환이 없다 — 모듈 상단에서 한 번만 푼다.

__all__ = [
    "CapabilityValue",
    "Carrier",
    "CarrierCapabilities",
    "CarrierStatus",
    "MemoryCarrier",
]


class CarrierStatus(enum.Enum):
    """2값뿐이다. 3값 이상으로 늘리지 말 것 — 상태를 늘리면 '부분 동작'이라는
    회색지대가 생기고, 그게 AC4(미구현 정직 표기)가 막는 것이다."""
    SUPPORTED = "supported"
    UNIMPLEMENTED = "unimplemented"


@dataclass(frozen=True)
class CapabilityValue:
    """한계값 + 그 값의 출처 라벨.

    source 예: "측정", "벤더문서", "garmin_forum_2026-07-22", "설계값", "미확인".
    NFR6(근거 무결성): 모르는 것을 아는 것으로 세탁하지 않는다 — 포럼발 수치에
    '측정'이나 '벤더문서'를 붙이면 그 순간 거짓말이 된다.
    """
    value: int
    source: str


@dataclass(frozen=True)
class CarrierCapabilities:
    """어댑터가 **자기 한계를 스스로 신고**하는 값 객체.

    supports_decompression이 None이면 **미확인**이다. False가 아니다 —
    False로 적으면 "확인해서 없더라"가 되고, 그건 하지 않은 조사를 한 척하는 것.
    """
    max_record_bytes: CapabilityValue      # Storage 키 1개당 상한
    max_total_bytes: CapabilityValue       # 총 저장량 상한
    transfer_mtu: CapabilityValue          # 전송 단위 상한 (BLE 등)
    supports_decompression: Optional[bool] = None   # None = 미확인


@runtime_checkable
class Carrier(Protocol):
    """캐리어 인터페이스 — 어떤 어댑터든 이 모양이어야 한다 (Task 1, 리뷰 P9).

    죽은 심볼이 아니다: 공통 계약 스위트가 `isinstance(adapter, Carrier)`를
    단언하고(runtime_checkable), 새 어댑터 작성자의 타입 검사 기준점이다.
    메서드 계약의 전문은 docs/CARRIER_INTERFACE.md §2.
    """
    status: CarrierStatus
    is_device: bool
    label: str

    def capabilities(self) -> CarrierCapabilities: ...
    def put_records(self, records) -> list: ...
    def get_records(self, names): ...
    def erase(self, names) -> list: ...


# ---------- 입력 검증 (공통) ----------
_NAME_SHOW_MAX = 32


def _show_name(name) -> str:
    """오류 문구용 이름 표시. 리뷰 P2 — 이름 길이가 무제한이라 페이로드(PII)를
    이름에 담아 오류 문구로 밀수하는 채널이 있었다. 정상 이름(청크 키
    'device:dev000' 등)은 짧으니 그대로, 길면 storage._no_duplicate_keys와
    같은 계보로 길이만 말한다."""
    if isinstance(name, str) and len(name) <= _NAME_SHOW_MAX:
        return repr(name)
    if isinstance(name, str):
        return f"<str len={len(name)}>"
    return f"<{type(name).__name__}>"


def _check_records(records):
    """put_records 입력 검증. 오류 목록 반환(빈 리스트 = 통과).
    오류에 페이로드 값을 넣지 않는다 — 이름·타입명·크기만."""
    errs = []
    if not isinstance(records, dict):
        return [f"records는 dict여야 함({type(records).__name__})"]
    if not records:
        return ["records가 비어 있음 — 저장할 것이 없다"]
    for name, payload in records.items():
        if not isinstance(name, str) or not name:
            errs.append(f"레코드 이름이 비어 있거나 문자열이 아님({type(name).__name__})")
            continue
        if not isinstance(payload, (bytes, bytearray)):
            errs.append(f"레코드 {_show_name(name)}: 페이로드는 bytes여야 함"
                        f"({type(payload).__name__})")
    return errs


def _check_names(names):
    """get_records·erase의 이름 목록 검증."""
    if isinstance(names, (str, bytes)) or not hasattr(names, "__iter__"):
        return None, [f"names는 문자열 목록이어야 함({type(names).__name__})"]
    out = []
    errs = []
    try:
        for n in names:
            if not isinstance(n, str) or not n:
                errs.append(f"이름이 비어 있거나 문자열이 아님({type(n).__name__})")
            else:
                out.append(n)
    except Exception as e:   # fail-closed: 이터레이션 자체가 터지는 입력
        return None, [f"names 순회 실패({type(e).__name__})"]
    if errs:
        return None, errs
    return out, []


class MemoryCarrier:
    """참조 어댑터 — **워치가 아니다**.

    "어댑터 모양이 실재한다"는 유일한 증거이며, Epic 2의 호스트 측 시연에도
    쓰인다. 로그·문서·발표 어디서도 "가민에서 됨"으로 읽히면 안 된다 —
    1.2의 시뮬레이터 표기 규약(NFR6)과 동일 계보.

    한계값은 코어의 보수 예산(storage.BUDGET_PER_KEY 계열)과 같은 수치를
    쓴다 — 참조 어댑터에서 통과한 조각이 실기기 예산 판정과 어긋나지 않게
    하기 위한 **설계값**이지 측정값이 아니다(source 라벨 참조).
    """
    status = CarrierStatus.SUPPORTED
    is_device = False
    label = "참조 어댑터 — 실기기 아님"

    def __init__(self):
        self._store = {}

    def capabilities(self) -> CarrierCapabilities:
        return CarrierCapabilities(
            max_record_bytes=CapabilityValue(
                _storage.BUDGET_PER_KEY, "설계값(코어 보수 예산과 동일 — 측정 아님)"),
            max_total_bytes=CapabilityValue(
                _storage.BUDGET_STORAGE_TOTAL, "설계값(코어 보수 예산과 동일 — 측정 아님)"),
            transfer_mtu=CapabilityValue(
                _storage.BLE_MTU, "설계값(코어 보수 예산과 동일 — 측정 아님)"),
            supports_decompression=True,   # 참조 어댑터는 호스트 파이썬 — zlib 존재
        )

    def put_records(self, records) -> list:
        """레코드 저장. 오류 목록 반환(빈 리스트 = 성공).

        **원자적이다**: 한 레코드라도 거부되면 배치 전체가 저장되지 않는다.
        부분 저장은 복원 시 반쪽 프로필을 만든다 — fail-closed.
        """
        try:
            errs = _check_records(records)
            if errs:
                return errs
            caps = self.capabilities()
            limit = caps.max_record_bytes.value
            total_limit = caps.max_total_bytes.value
            staged = {}
            for name, payload in records.items():
                size = len(payload)
                if size > limit:
                    errs.append(f"레코드 {_show_name(name)} {size:,}B > 한계 {limit:,}B")
                else:
                    staged[name] = bytes(payload)
            if errs:
                return errs   # 원자성: 아무것도 저장하지 않는다
            merged = dict(self._store)
            merged.update(staged)
            # 리뷰 P7: 이름 바이트도 산입 — 실기기 Storage는 키 문자열도 공간을
            # 차지한다. 페이로드만 세면 "참조에서 통과 → 실기기에서 초과"가 생긴다.
            new_total = sum(len(k.encode("utf-8")) + len(v)
                            for k, v in merged.items())
            if new_total > total_limit:
                return [f"총 저장량(이름 포함) {new_total:,}B > 한계 {total_limit:,}B — "
                        f"배치 {len(staged)}건 거부"]
            self._store = merged
            return []
        except Exception as e:   # fail-closed
            return [f"저장 내부 오류({type(e).__name__}) — 거부"]

    def get_records(self, names):
        """레코드 조회. 반환 (dict | None, errors).

        하나라도 없으면 (None, errors) — 반쪽 결과를 돌려주지 않는다.
        """
        try:
            clean, errs = _check_names(names)
            if errs:
                return None, errs
            out = {}
            for n in clean:
                if n not in self._store:
                    errs.append(f"레코드 {_show_name(n)} 없음")
                else:
                    out[n] = self._store[n]
            if errs:
                return None, errs
            return out, []
        except Exception as e:   # fail-closed
            return None, [f"조회 내부 오류({type(e).__name__}) — 거부"]

    def erase(self, names) -> list:
        """레코드 삭제. 오류 목록 반환. 없는 이름은 오류로 보고한다 —
        '지웠다고 생각했는데 남아 있음'이 온바디 프라이버시에서 최악의 실패다.

        **원자적이다**: put과 같은 단일 재바인딩. 리뷰 P1 — v1은 존재 검사 후
        del 루프였는데, 중복 이름(["a","a"])이 검사를 통과한 뒤 두 번째 del이
        KeyError를 내며 "거부"를 보고했지만 첫 삭제는 이미 반영돼 있었다 —
        "거부됐다고 보고했는데 지워져 있음". 이름은 순서 유지로 중복 제거한다.
        """
        try:
            clean, errs = _check_names(names)
            if errs:
                return errs
            clean = list(dict.fromkeys(clean))   # 순서 유지 dedup
            for n in clean:
                if n not in self._store:
                    errs.append(f"레코드 {_show_name(n)} 없음 — 삭제할 수 없음")
            if errs:
                return errs
            remaining = {k: v for k, v in self._store.items() if k not in set(clean)}
            self._store = remaining              # 단일 재바인딩 — 부분 삭제 없음
            return []
        except Exception as e:   # fail-closed
            return [f"삭제 내부 오류({type(e).__name__}) — 거부"]
