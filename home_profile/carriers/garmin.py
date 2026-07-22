# -*- coding: utf-8 -*-
"""Garmin Connect IQ 어댑터 — **미구현** (Story 1.3, AC4).

⚠️ 이 저장소에 벤더 SDK가 없고 설치할 수도 없다 — Connect IQ SDK는 Monkey C이며
Python 패키지가 아니다. 그러므로 이 어댑터는 **경계 설계와 용량 신고까지만**
담당한다. 모든 연산은 예외 없이 "미구현" 오류를 반환하며, 데이터를 반환하는
경로가 존재하지 않는다 — "동작하는 것처럼 시연되지 않는다"(AC4 문면).

팀이 가민 실기기를 보유하고 Epic 2 데모가 그 위에서 돌 예정이지만,
**이 파이썬 코드는 워치가 아니다**. 구조는 중립이어야 하고 실증은 가민
하나로만 가능하다 — 그 비대칭을 숨기지 않고 표기하는 것이 이 파일의 일이다.

신고하는 한계값의 출처 (전부 포럼발 — 공식 문서 보증 아님, PROFILE_SCHEMA §5):
  - Storage 총량 128KB: 포럼발, 기기별 상이 가능
    https://forums.garmin.com/developer/connect-iq/f/discussion/2661/storage-available
  - 키당 4,096B: 포럼 8KB의 보수 절반(파티 결정 2026-07-22) — 실측 시 교체
  - BLE MTU 20B, long write 미지원: 포럼발
    https://forums.garmin.com/developer/connect-iq/f/discussion/196823/...
  - zlib 해제 지원: **미확인**(None) — False도 True도 아니다(1.2 미해결 2번)
"""
from .. import storage as _storage
from ..carrier import (
    CapabilityValue,
    CarrierCapabilities,
    CarrierStatus,
)

__all__ = ["GarminConnectIQCarrier"]

_NOTICE = ("미구현: Garmin Connect IQ 어댑터는 Monkey C 런타임을 요구하며 "
           "이 저장소에 구현체가 없다")


class GarminConnectIQCarrier:
    """경계 설계 + 용량 신고 전용. 저장·조회·삭제는 전부 미구현 거부."""
    status = CarrierStatus.UNIMPLEMENTED
    is_device = False   # 실기기 보유 여부와 무관 — 이 코드는 워치가 아니다
    label = "Garmin Connect IQ — 미구현(경계·용량 신고만)"

    def capabilities(self) -> CarrierCapabilities:
        # 값은 코어의 가민 유래 상수(storage.BUDGET_* 계열)와 일치시킨다 —
        # "예산 상수는 가민 값"이라는 1.2 사실을 어댑터 신고로 이관하는 것.
        # 상수 자체는 1.2 테스트 호환을 위해 storage.py에 유지된다(스토리 규약).
        # 리뷰 P5: 지연 import 제거 — 모듈 상단 import로 예외 금지 계약을 보장.
        return CarrierCapabilities(
            max_record_bytes=CapabilityValue(
                _storage.BUDGET_PER_KEY,
                "설계보수값(garmin_forum 8KB의 절반, 미확인 — 실측 시 교체)"),
            max_total_bytes=CapabilityValue(
                _storage.BUDGET_STORAGE_TOTAL,
                "garmin_forum_2026-07-22(공식 문서 아님, 기기별 상이 가능)"),
            transfer_mtu=CapabilityValue(
                _storage.BLE_MTU,
                "garmin_forum_2026-07-22(long write 미지원 전제)"),
            supports_decompression=None,   # 미확인 — False로 세탁하지 않는다
        )

    def put_records(self, records) -> list:
        return [_NOTICE]

    def get_records(self, names):
        return None, [_NOTICE]

    def erase(self, names) -> list:
        return [_NOTICE]
