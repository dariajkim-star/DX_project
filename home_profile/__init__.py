# -*- coding: utf-8 -*-
"""home_profile — 온바디 홈 프로필 제품 코드 (Epic 1).

분석 파이프라인(`dx_pipeline_v2.2/`)과 계보가 다르다.
파이프라인은 VOC에서 Pain을 도출하는 '발견' 트랙이고,
이 패키지는 그 결과로 설계된 '처방' 트랙이다. 서로 import하지 않는다.

리뷰 반영(2026-07-22): MIGRATIONS(아무도 읽지 않는 가변 전역) 표면에서 제거,
SUPPORTED_VERSIONS(호출자가 읽을 정당한 이유가 있는 불변값) 추가, __all__ 명시.
2차 리뷰 반영: make_sample_profile은 테스트·문서 생성 전용이라 제품 표면에서
제외(home_profile.storage로 직접 접근). size_report는 (report, errors) 튜플 규약.
"""
from .carrier import (
    CapabilityValue,
    Carrier,
    CarrierCapabilities,
    CarrierStatus,
    MemoryCarrier,
)
from .onboard import (
    LOCAL_CONSENT_SCOPE,
    NOT_REQUIRED,
    consent_scope_violations,
    onboard_local,
)
from .relocate import (
    REASON_CAPABILITY_UNSUPPORTED,
    REASON_MAPPING_ABORTED,
    REASON_NO_MATCHING_TYPE,
    REASON_ROUTINE_UNMAPPABLE,
    map_to_new_home,
)
from .residency import data_residency
from .routine import (
    chunk,
    execute_routine,
    reassemble,
    routine_to_commands,
)
from .storage import (
    BLE_MTU,
    BUDGET_PER_KEY,
    BUDGET_STORAGE_TOTAL,
    CHUNK_KINDS,
    deserialize,
    merge_chunks,
    persist_to_carrier,
    restore_from_carrier,
    serialize,
    size_report,
    split_chunks,
)
from .schema import (
    SCHEMA_VERSION,
    SUPPORTED_VERSIONS,
    TOP_LEVEL_KEYS,
    find_identifier_violations,
    is_supported,
    new_profile,
    validate_profile,
)

__all__ = [
    "BLE_MTU",
    "CapabilityValue",
    "Carrier",
    "CarrierCapabilities",
    "CarrierStatus",
    "MemoryCarrier",
    "BUDGET_PER_KEY",
    "BUDGET_STORAGE_TOTAL",
    "CHUNK_KINDS",
    "SCHEMA_VERSION",
    "SUPPORTED_VERSIONS",
    "TOP_LEVEL_KEYS",
    "LOCAL_CONSENT_SCOPE",
    "NOT_REQUIRED",
    "REASON_CAPABILITY_UNSUPPORTED",
    "REASON_MAPPING_ABORTED",
    "REASON_NO_MATCHING_TYPE",
    "REASON_ROUTINE_UNMAPPABLE",
    "chunk",
    "consent_scope_violations",
    "data_residency",
    "execute_routine",
    "find_identifier_violations",
    "map_to_new_home",
    "onboard_local",
    "reassemble",
    "routine_to_commands",
    "is_supported",
    "deserialize",
    "merge_chunks",
    "new_profile",
    "persist_to_carrier",
    "restore_from_carrier",
    "serialize",
    "size_report",
    "split_chunks",
    "validate_profile",
]
