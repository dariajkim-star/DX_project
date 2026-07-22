# -*- coding: utf-8 -*-
"""home_profile — 온바디 홈 프로필 제품 코드 (Epic 1).

분석 파이프라인(`dx_pipeline_v2.2/`)과 계보가 다르다.
파이프라인은 VOC에서 Pain을 도출하는 '발견' 트랙이고,
이 패키지는 그 결과로 설계된 '처방' 트랙이다. 서로 import하지 않는다.

리뷰 반영(2026-07-22): MIGRATIONS(아무도 읽지 않는 가변 전역) 표면에서 제거,
SUPPORTED_VERSIONS(호출자가 읽을 정당한 이유가 있는 불변값) 추가, __all__ 명시.
"""
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
    "SCHEMA_VERSION",
    "SUPPORTED_VERSIONS",
    "TOP_LEVEL_KEYS",
    "find_identifier_violations",
    "is_supported",
    "new_profile",
    "validate_profile",
]
